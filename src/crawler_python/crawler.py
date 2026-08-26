import asyncio
import logging
import time
from fnmatch import fnmatch
from urllib.parse import urlparse

import aiohttp

from crawler_python.circuit_breaker import CircuitBreaker
from crawler_python.concurrency import SemaphoreManager
from crawler_python.errors import (
    CrawlerError,
    ErrorType,
    classify_exception,
)
from crawler_python.parser import HTMLParser
from crawler_python.queue import CrawlerQueue
from crawler_python.rate_limiter import RateLimiter
from crawler_python.retry import RetryStrategy
from crawler_python.robots import RobotsParser

logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(
        self,
        max_concurrent: int = 10,
        per_domain: int = 3,
        timeout: int = 10,
        max_depth: int = 3,
        requests_per_second: float = 5.0,
        min_delay: float = 0.0,
        jitter: float = 0.0,
        respect_robots: bool = True,
        user_agent: str = "AsyncCrawler/1.0",
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        circuit_breaker: bool = True,
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._max_depth = max_depth
        self._user_agent = user_agent
        self._respect_robots = respect_robots

        self._sem_manager = SemaphoreManager(
            global_limit=max_concurrent,
            per_domain_limit=per_domain,
        )
        self._queue = CrawlerQueue()
        self._rate_limiter = RateLimiter(
            requests_per_second=requests_per_second,
            per_domain=True,
            min_delay=min_delay,
            jitter=jitter,
        )
        self._robots = RobotsParser(user_agent=user_agent)
        self._retry_strategy = RetryStrategy(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
        )
        self._circuit_breaker = CircuitBreaker() if circuit_breaker else None

        self._results: dict[str, dict] = {}
        self._start_time: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
            )
        return self._session

    async def _ensure_robots(self, url: str) -> None:
        if not self._respect_robots:
            return
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots = await self._robots.fetch_robots(origin)
        delay = self._robots.get_crawl_delay(self._user_agent)
        if delay > 0:
            self._rate_limiter.set_domain_rate(parsed.netloc, 1.0 / delay)

    def _is_allowed(self, url: str) -> bool:
        if not self._respect_robots:
            return True
        allowed = self._robots.can_fetch(url, self._user_agent)
        if not allowed:
            logger.warning("Заблокировано robots.txt: %s", url)
            self._rate_limiter.record_blocked()
        return allowed

    async def _do_fetch(self, url: str) -> str:
        session = await self._get_session()
        logger.info("Загрузка %s", url)
        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()
            logger.info("Успешно: %s (%d)", url, response.status)
            return text

    async def _fetch(self, url: str) -> str:
        domain = urlparse(url).netloc

        await self._ensure_robots(url)
        if not self._is_allowed(url):
            raise PermissionError(f"Запрещено robots.txt: {url}")

        if self._circuit_breaker and self._circuit_breaker.is_open(domain):
            logger.warning("Circuit breaker открыт для %s, пропуск %s", domain, url)
            raise CrawlerError(
                f"Circuit breaker открыт: {domain}",
                ErrorType.NETWORK,
                url,
            )

        await self._rate_limiter.acquire(domain)
        await self._sem_manager.acquire(url)
        try:
            result = await self._retry_strategy.execute_with_retry(
                self._do_fetch, url
            )
            if self._circuit_breaker:
                self._circuit_breaker.record_success(domain)
            return result
        except Exception:
            if self._circuit_breaker:
                self._circuit_breaker.record_failure(domain)
            raise
        finally:
            await self._sem_manager.release(url)

    async def _process_url(
        self,
        url: str,
        depth: int,
        domain: str,
        same_domain_only: bool,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> None:
        try:
            html = await self._fetch(url)
            parser = HTMLParser()
            result = parser.parse_html(html, url)
            self._results[url] = result
            await self._queue.mark_processed(url)

            if depth < self._max_depth:
                for link in result["links"]:
                    if self._should_include(
                        link, domain, same_domain_only,
                        include_patterns, exclude_patterns,
                    ):
                        await self._queue.add_url(link, depth=depth + 1)
        except PermissionError:
            await self._queue.mark_failed(url, "blocked by robots.txt")
        except Exception as e:
            await self._queue.mark_failed(url, str(e))
            logger.error("Ошибка обработки %s: %s", url, e)

    def _should_include(
        self,
        url: str,
        base_domain: str,
        same_domain_only: bool,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> bool:
        parsed = urlparse(url)
        if same_domain_only and parsed.netloc != base_domain:
            return False
        for pattern in exclude_patterns:
            if fnmatch(url, pattern):
                return False
        if include_patterns:
            return any(fnmatch(url, p) for p in include_patterns)
        return True

    def _log_progress(self) -> None:
        queue_stats = self._queue.get_stats()
        rate_stats = self._rate_limiter.get_stats()
        retry_stats = self._retry_strategy.stats.get_summary()
        elapsed = time.perf_counter() - self._start_time
        speed = queue_stats["processed"] / elapsed if elapsed > 0 else 0
        logger.info(
            "Прогресс: %d обработано | %d в очереди | %d ошибок | "
            "%.1f стр/с | повторов: %d | постоянных: %d",
            queue_stats["processed"],
            queue_stats["in_queue"],
            queue_stats["failed"],
            speed,
            retry_stats["successful_retries"],
            retry_stats["permanent_failures"],
        )

    async def _worker(
        self,
        domain: str,
        same_domain_only: bool,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> None:
        while True:
            item = await self._queue.get_next()
            if item is None:
                break
            if item.depth > self._max_depth:
                await self._queue.mark_processed(item.url)
                continue
            await self._process_url(
                item.url, item.depth, domain, same_domain_only,
                include_patterns, exclude_patterns,
            )
            self._log_progress()

    async def crawl(
        self,
        start_urls: list[str],
        max_pages: int = 100,
        max_depth: int | None = None,
        same_domain_only: bool = False,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, dict]:
        if max_depth is not None:
            self._max_depth = max_depth

        include = include_patterns or []
        exclude = exclude_patterns or []
        domain = urlparse(start_urls[0]).netloc if start_urls else ""

        self._start_time = time.perf_counter()

        for url in start_urls:
            await self._queue.add_url(url, priority=0, depth=0)

        workers = []
        for _ in range(self._sem_manager._global_semaphore._value):
            workers.append(
                asyncio.create_task(
                    self._worker(
                        domain, same_domain_only, include, exclude,
                    )
                )
            )

        await asyncio.gather(*workers, return_exceptions=True)

        elapsed = time.perf_counter() - self._start_time
        queue_stats = self._queue.get_stats()
        rate_stats = self._rate_limiter.get_stats()
        retry_stats = self._retry_strategy.stats.get_summary()
        logger.info(
            "Краулинг завершён: %d страниц за %.2fс (%.1f стр/с) | "
            "robots блоков: %d | повторов: %d | ошибок: %d",
            queue_stats["processed"],
            elapsed,
            queue_stats["processed"] / elapsed if elapsed > 0 else 0,
            rate_stats["blocked_by_robots"],
            retry_stats["successful_retries"],
            retry_stats["permanent_failures"],
        )

        return self._results

    def get_error_stats(self) -> dict:
        return {
            "retry": self._retry_strategy.stats.get_summary(),
            "circuit_breaker": (
                self._circuit_breaker.get_stats()
                if self._circuit_breaker
                else None
            ),
            "queue": self._queue.get_stats(),
        }

    async def close(self) -> None:
        await self._robots.close()
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Сессия закрыта")

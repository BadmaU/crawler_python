import asyncio
import logging
import time
from datetime import datetime, timezone
from fnmatch import fnmatch
from urllib.parse import urlparse

import aiohttp

from crawler_python.circuit_breaker import CircuitBreaker
from crawler_python.config import CrawlerConfig
from crawler_python.concurrency import SemaphoreManager
from crawler_python.errors import (
    CrawlerError,
    ErrorType,
    classify_exception,
)
from crawler_python.logging_setup import setup_logging
from crawler_python.monitor import ProgressMonitor
from crawler_python.parser import HTMLParser
from crawler_python.queue import CrawlerQueue
from crawler_python.rate_limiter import RateLimiter
from crawler_python.retry import RetryStrategy
from crawler_python.robots import RobotsParser
from crawler_python.sitemap import SitemapParser
from crawler_python.stats import CrawlerStats
from crawler_python.storage import (
    CSVStorage,
    DataStorage,
    JSONStorage,
    SQLiteStorage,
)

logger = logging.getLogger(__name__)


class AsyncCrawler:
    """Единый класс-приложение асинхронного веб-краулера.

    Объединяет краулинг, парсинг, вежливость (robots/rate limit), повторы,
    circuit breaker, сохранение данных, sitemap, расширенную статистику,
    мониторинг в реальном времени и экспорт отчётов.
    """

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
        storage: DataStorage | None = None,
        config: CrawlerConfig | None = None,
    ) -> None:
        if config is not None:
            self._apply_config(config)
            return

        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._max_depth = max_depth
        self._user_agent = user_agent
        self._respect_robots = respect_robots

        self._config = CrawlerConfig(
            max_concurrent=max_concurrent,
            per_domain=per_domain,
            timeout=timeout,
            max_depth=max_depth,
            requests_per_second=requests_per_second,
            min_delay=min_delay,
            jitter=jitter,
            respect_robots=respect_robots,
            user_agent=user_agent,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            circuit_breaker=circuit_breaker,
        )

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
        self._storage = storage or self._build_storage(self._config)
        self._storage_errors = 0

        self._sitemap = SitemapParser(user_agent=user_agent, timeout=timeout)
        self._stats = CrawlerStats()
        self._monitor = ProgressMonitor(enabled=True)

        self._results: dict[str, dict] = {}
        self._start_time: float = 0

        self._max_pages: int | None = None
        self._pages_taken = 0
        self._pages_lock = asyncio.Lock()

    @classmethod
    def from_config(cls, path: str) -> "AsyncCrawler":
        """Создание краулера из конфигурационного файла (YAML/JSON)."""
        return cls(config=CrawlerConfig.from_file(path))

    @classmethod
    def from_dict(cls, data: dict) -> "AsyncCrawler":
        return cls(config=CrawlerConfig.from_dict(data))

    def _apply_config(self, config: CrawlerConfig) -> None:
        setup_logging(
            level=config.logging_level,
            log_file=config.log_file,
            rotation_backups=config.log_rotation,
            max_bytes=config.log_max_bytes,
        )

        self._config = config
        self._timeout = aiohttp.ClientTimeout(total=config.timeout)
        self._session = None
        self._max_depth = config.max_depth
        self._user_agent = config.user_agent
        self._respect_robots = config.respect_robots

        self._sem_manager = SemaphoreManager(
            global_limit=config.max_concurrent,
            per_domain_limit=config.per_domain,
        )
        self._queue = CrawlerQueue()
        self._rate_limiter = RateLimiter(
            requests_per_second=config.requests_per_second,
            per_domain=True,
            min_delay=config.min_delay,
            jitter=config.jitter,
        )
        self._robots = RobotsParser(user_agent=config.user_agent)
        self._retry_strategy = RetryStrategy(
            max_retries=config.max_retries,
            backoff_factor=config.backoff_factor,
        )
        self._circuit_breaker = (
            CircuitBreaker() if config.circuit_breaker else None
        )
        self._storage = self._build_storage(config)
        self._storage_errors = 0

        self._sitemap = SitemapParser(
            user_agent=config.user_agent, timeout=config.timeout
        )
        self._stats = CrawlerStats()
        self._monitor = ProgressMonitor(enabled=True)

        self._results = {}
        self._start_time = 0

        self._max_pages = None
        self._pages_taken = 0
        self._pages_lock = asyncio.Lock()

    @staticmethod
    def _build_storage(config: CrawlerConfig) -> DataStorage | None:
        if config.storage == "json":
            return JSONStorage(config.storage_path)
        if config.storage == "csv":
            return CSVStorage(config.storage_path)
        if config.storage == "sqlite":
            return SQLiteStorage(config.storage_path)
        if config.storage in ("none", "memory"):
            return None
        return JSONStorage(config.storage_path)

    @property
    def config(self) -> CrawlerConfig:
        return self._config

    @property
    def stats(self) -> CrawlerStats:
        return self._stats

    @property
    def results(self) -> dict[str, dict]:
        return self._results

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

    async def _do_fetch(self, url: str) -> dict:
        session = await self._get_session()
        logger.info("Загрузка %s", url)
        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()
            logger.info("Успешно: %s (%d)", url, response.status)
            return {
                "text": text,
                "status_code": response.status,
                "content_type": response.headers.get("Content-Type", ""),
            }

    async def fetch_url(self, url: str) -> str:
        """Загрузка одной страницы (публичный API дня 2)."""
        parsed = await self._fetch(url)
        return parsed["text"]

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        """Параллельная загрузка списка URL (публичный API дня 2)."""
        results: dict[str, str] = {}

        async def _one(u: str) -> None:
            try:
                results[u] = await self.fetch_url(u)
            except Exception as e:
                logger.error("Ошибка %s: %s", u, e)

        await asyncio.gather(*(_one(u) for u in urls))
        return results

    async def fetch_and_parse(self, url: str) -> dict:
        """Загрузка и парсинг одной страницы (публичный API дня 3).

        Возвращает словарь с полями url, title, text, links, metadata,
        а также status_code и content_type.
        """
        parsed = await self._fetch(url)
        html = parsed["text"]
        parser = HTMLParser()
        result = await parser.parse_html(html, url)
        result["status_code"] = parsed["status_code"]
        result["content_type"] = parsed["content_type"]
        return result

    async def _fetch(self, url: str) -> dict:
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
            if not await self._claim_page_slot():
                await self._queue.mark_processed(url)
                return
            fetched = await self._fetch(url)
            html = fetched["text"]
            parser = HTMLParser()
            result = await parser.parse_html(html, url)
            result["crawled_at"] = datetime.now(timezone.utc)
            result["status_code"] = fetched["status_code"]
            result["content_type"] = fetched["content_type"]
            self._results[url] = result
            await self._queue.mark_processed(url)
            self._stats.record_success(url, status=fetched["status_code"])

            if self._storage:
                try:
                    await self._storage.save(result)
                except Exception as e:
                    self._storage_errors += 1
                    logger.error("Ошибка сохранения %s: %s", url, e)

            if depth < self._max_depth:
                for link in result["links"]:
                    if self._should_include(
                        link, domain, same_domain_only,
                        include_patterns, exclude_patterns,
                    ):
                        await self._queue.add_url(link, depth=depth + 1)
        except PermissionError:
            await self._queue.mark_failed(url, "blocked by robots.txt")
            self._stats.record_failure(url)
        except Exception as e:
            await self._queue.mark_failed(url, str(e))
            self._stats.record_failure(url)
            logger.error("Ошибка обработки %s: %s", url, e)

    async def _claim_page_slot(self) -> bool:
        async with self._pages_lock:
            if self._max_pages is not None and self._pages_taken >= self._max_pages:
                return False
            self._pages_taken += 1
            return True

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
            item = await self._queue.get_next_or_wait()
            if item is None:
                break
            if item.depth > self._max_depth:
                await self._queue.mark_processed(item.url)
                continue
            self._queue.task_started()
            try:
                await self._process_url(
                    item.url, item.depth, domain, same_domain_only,
                    include_patterns, exclude_patterns,
                )
                self._log_progress()
            finally:
                self._queue.task_finished()

    async def _resolve_start_urls(self, start_urls: list[str]) -> list[str]:
        config = self._config
        urls = list(start_urls)

        sitemap_urls: list[str] = list(config.sitemap_urls)
        if config.use_sitemap and not sitemap_urls:
            for url in urls:
                found = await self._sitemap.fetch_robots_sitemaps(url)
                sitemap_urls.extend(found)

        sitemap_pages: list[str] = []
        for sm in sitemap_urls:
            sitemap_pages.extend(await self._sitemap.fetch_sitemap(sm))

        if sitemap_pages:
            logger.info("Добавлено %d URL из sitemap", len(sitemap_pages))
            urls = sitemap_pages

        return urls

    async def crawl(
        self,
        start_urls: list[str] | None = None,
        max_pages: int | None = None,
        max_depth: int | None = None,
        same_domain_only: bool | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> dict[str, dict]:
        config = self._config
        if start_urls is None:
            start_urls = config.start_urls
        if max_pages is None:
            max_pages = config.max_pages
        self._max_pages = max_pages
        self._pages_taken = 0
        if max_depth is None:
            max_depth = config.max_depth
            if max_depth is not None:
                self._max_depth = max_depth
        elif max_depth is not None:
            self._max_depth = max_depth
        if same_domain_only is None:
            same_domain_only = config.same_domain_only
        if include_patterns is None:
            include_patterns = config.include_patterns or []
        if exclude_patterns is None:
            exclude_patterns = config.exclude_patterns or []

        if not start_urls:
            logger.warning("Нет стартовых URL для краулинга")
            return {}

        start_urls = await self._resolve_start_urls(start_urls)
        limited_urls = start_urls[:max_pages]

        include = include_patterns or []
        exclude = exclude_patterns or []
        domain = urlparse(limited_urls[0]).netloc if limited_urls else ""

        if config.storage == "sqlite" and self._storage:
            await self._storage.init_db()

        self._start_time = time.perf_counter()
        self._stats.start()

        total = len(limited_urls)
        self._monitor.set_total(total)

        def progress() -> int:
            return self._stats.total_pages

        def marks() -> int:
            try:
                return self._sem_manager.get_stats()["active_tasks"]
            except Exception:
                return 0

        self._monitor.set_callbacks(progress=progress, marks=marks)
        await self._monitor.start()

        try:
            for url in limited_urls:
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
        finally:
            await self._monitor.stop()
            self._stats.stop()

        elapsed = time.perf_counter() - self._start_time
        queue_stats = self._queue.get_stats()
        rate_stats = self._rate_limiter.get_stats()
        retry_stats = self._retry_strategy.stats.get_summary()
        logger.info(
            "Краулинг завершён: %d страниц за %.2fс (%.1f стр/с) | "
            "robots блоков: %d | повторов: %d | ошибок: %d | "
            "ошибок сохранения: %d",
            queue_stats["processed"],
            elapsed,
            queue_stats["processed"] / elapsed if elapsed > 0 else 0,
            rate_stats["blocked_by_robots"],
            retry_stats["successful_retries"],
            retry_stats["permanent_failures"],
            self._storage_errors,
        )

        return self._results

    def get_stats(self) -> dict:
        stats = self._stats.snapshot()
        stats["errors"] = self.get_error_stats()
        return stats

    def export_to_json(self, filename: str | None = None) -> None:
        self._stats.export_to_json(filename or self._config.output_stats)

    def export_to_html_report(self, filename: str | None = None) -> None:
        self._stats.export_to_html_report(filename or self._config.output_report)

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
        await self._monitor.stop()
        await self._robots.close()
        await self._sitemap.close()
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Сессия закрыта")
        if self._storage:
            try:
                await self._storage.close()
            except Exception as e:
                logger.error("Ошибка закрытия storage: %s", e)

import asyncio
import logging
import re
import time
from fnmatch import fnmatch
from urllib.parse import urlparse

import aiohttp

from crawler_python.concurrency import SemaphoreManager
from crawler_python.parser import HTMLParser
from crawler_python.queue import CrawlerQueue

logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(
        self,
        max_concurrent: int = 10,
        per_domain: int = 3,
        timeout: int = 10,
        max_depth: int = 3,
    ) -> None:
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._max_depth = max_depth
        self._sem_manager = SemaphoreManager(
            global_limit=max_concurrent,
            per_domain_limit=per_domain,
        )
        self._queue = CrawlerQueue()
        self._results: dict[str, dict] = {}
        self._start_time: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def _fetch(self, url: str) -> str:
        session = await self._get_session()
        await self._sem_manager.acquire(url)
        try:
            logger.info("Загрузка %s", url)
            async with session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
                logger.info("Успешно: %s (%d)", url, response.status)
                return text
        except aiohttp.ClientResponseError as e:
            logger.error("HTTP ошибка %s: %s", url, e)
            raise
        except asyncio.TimeoutError:
            logger.error("Таймаут %s", url)
            raise
        except aiohttp.ClientError as e:
            logger.error("Сетевая ошибка %s: %s", url, e)
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
                        link, domain, same_domain_only, include_patterns, exclude_patterns
                    ):
                        await self._queue.add_url(link, depth=depth + 1)
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
        stats = self._queue.get_stats()
        elapsed = time.perf_counter() - self._start_time
        speed = stats["processed"] / elapsed if elapsed > 0 else 0
        logger.info(
            "Прогресс: %d обработано | %d в очереди | %d ошибок | %.1f стр/с",
            stats["processed"],
            stats["in_queue"],
            stats["failed"],
            speed,
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
                    self._worker(domain, same_domain_only, include, exclude)
                )
            )

        await asyncio.gather(*workers, return_exceptions=True)

        elapsed = time.perf_counter() - self._start_time
        stats = self._queue.get_stats()
        logger.info(
            "Краулинг завершён: %d страниц за %.2fс (%.1f стр/с)",
            stats["processed"],
            elapsed,
            stats["processed"] / elapsed if elapsed > 0 else 0,
        )

        return self._results

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Сессия закрыта")

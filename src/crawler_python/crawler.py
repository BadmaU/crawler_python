import asyncio
import logging

import aiohttp

from crawler_python.parser import HTMLParser

logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(self, max_concurrent: int = 10, timeout: int = 10) -> None:
        self._max_concurrent = max_concurrent
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def fetch_url(self, url: str) -> str:
        session = await self._get_session()
        async with self._semaphore:
            logger.info("Загрузка %s", url)
            try:
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

    async def fetch_and_parse(self, url: str) -> dict:
        html = await self.fetch_url(url)
        parser = HTMLParser()
        return parser.parse_html(html, url)

    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        tasks = [self.fetch_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            url: result if isinstance(result, str) else ""
            for url, result in zip(urls, results)
        }

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("Сессия закрыта")

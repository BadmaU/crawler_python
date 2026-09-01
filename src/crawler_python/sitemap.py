import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_RECURSION_DEPTH = 10


class SitemapParser:
    """Загрузка и разбор sitemap.xml (обычный, индексный, рекурсивный)."""

    def __init__(
        self,
        user_agent: str = "AsyncCrawler/1.0",
        timeout: int = 15,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                headers={"User-Agent": self._user_agent},
            )
        return self._session

    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        """Загрузка sitemap и извлечение всех URL из него."""
        return await self._process_sitemap(sitemap_url, depth=0)

    async def _process_sitemap(self, sitemap_url: str, depth: int) -> list[str]:
        if depth > MAX_RECURSION_DEPTH:
            logger.warning("Превышена глубина рекурсии sitemap: %s", sitemap_url)
            return []

        session = await self._get_session()
        try:
            async with session.get(sitemap_url) as response:
                response.raise_for_status()
                content = await response.read()
        except Exception as e:
            logger.error("Ошибка загрузки sitemap %s: %s", sitemap_url, e)
            return []

        return await self._parse_sitemap(content, sitemap_url, depth)

    async def _parse_sitemap(
        self, content: bytes, base_url: str, depth: int
    ) -> list[str]:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as e:
            logger.error("Некорректный XML sitemap %s: %s", base_url, e)
            return []

        urls: list[str] = []
        sitemap_indexes = root.findall(f"{SITEMAP_NS}sitemap")

        if sitemap_indexes:
            for sitemap in sitemap_indexes:
                loc = sitemap.findtext(f"{SITEMAP_NS}loc")
                if not loc:
                    continue
                nested_url = urljoin(base_url, loc.strip())
                urls.extend(await self._process_sitemap(nested_url, depth + 1))
            return urls

        for url_elem in root.findall(f"{SITEMAP_NS}url"):
            loc = url_elem.findtext(f"{SITEMAP_NS}loc")
            if loc and self._is_valid_url(loc):
                urls.append(loc.strip())

        # fallback: парсим любые <loc> вне пространства имён
        if not urls and not sitemap_indexes:
            for loc_elem in root.iter("loc"):
                if loc_elem.text and self._is_valid_url(loc_elem.text):
                    urls.append(loc_elem.text.strip())

        logger.info("Sitemap %s: извлечено %d URL", base_url, len(urls))
        return urls

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)

    async def fetch_robots_sitemaps(self, base_url: str) -> list[str]:
        """Достаём список sitemap из robots.txt по адресу origin."""
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        robots_url = f"{origin}/robots.txt"

        session = await self._get_session()
        try:
            async with session.get(robots_url) as response:
                response.raise_for_status()
                text = await response.text()
        except Exception as e:
            logger.debug("Нет robots.txt для %s: %s", origin, e)
            return []

        sitemaps: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("sitemap:"):
                value = stripped.split(":", 1)[1].strip()
                if value:
                    sitemaps.append(value)
        return sitemaps

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

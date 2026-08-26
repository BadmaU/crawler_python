import logging
from urllib.parse import urlparse, urljoin

import aiohttp

logger = logging.getLogger(__name__)


class RobotsParser:
    def __init__(self, user_agent: str = "*") -> None:
        self._user_agent = user_agent
        self._cache: dict[str, dict] = {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=5)
            )
        return self._session

    async def fetch_robots(self, base_url: str) -> dict:
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin in self._cache:
            return self._cache[origin]

        robots_url = urljoin(origin, "/robots.txt")
        result: dict = {"rules": {}, "crawl_delay": {}, "sitemaps": []}

        try:
            session = await self._get_session()
            async with session.get(robots_url) as resp:
                if resp.status != 200:
                    logger.info("robots.txt не найден для %s (HTTP %d)", origin, resp.status)
                    self._cache[origin] = result
                    return result
                text = await resp.text()
                result = self._parse_robots_text(text)
        except Exception as e:
            logger.warning("Ошибка загрузки robots.txt для %s: %s", origin, e)

        self._cache[origin] = result
        return result

    def _parse_robots_text(self, text: str) -> dict:
        rules: dict[str, list[str]] = {}
        crawl_delay: dict[str, float] = {}
        sitemaps: list[str] = []
        current_agents: list[str] = []

        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue

            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()

            if key == "user-agent":
                current_agents = [value]
            elif key == "disallow":
                for agent in current_agents:
                    rules.setdefault(agent, [])
                    if value:
                        rules[agent].append(value)
            elif key == "allow":
                for agent in current_agents:
                    rules.setdefault(agent, [])
                    rules[agent].append(f"+{value}")
            elif key == "crawl-delay":
                for agent in current_agents:
                    try:
                        crawl_delay[agent] = float(value)
                    except ValueError:
                        pass
            elif key == "sitemap":
                sitemaps.append(value)

        return {"rules": rules, "crawl_delay": crawl_delay, "sitemaps": sitemaps}

    def can_fetch(self, url: str, user_agent: str | None = None) -> bool:
        agent = user_agent or self._user_agent
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        robots = self._cache.get(origin)
        if not robots:
            return True

        rules = robots.get("rules", {})
        path = parsed.path or "/"

        patterns = rules.get(agent, []) or rules.get("*", [])
        allow_patterns = [p[1:] for p in patterns if p.startswith("+")]
        disallow_patterns = [p for p in patterns if not p.startswith("+")]

        for ap in allow_patterns:
            if path.startswith(ap):
                return True

        for dp in disallow_patterns:
            if path.startswith(dp):
                return False

        return True

    def get_crawl_delay(self, user_agent: str | None = None) -> float:
        agent = user_agent or self._user_agent
        for robots in self._cache.values():
            delays = robots.get("crawl_delay", {})
            if agent in delays:
                return delays[agent]
            if "*" in delays:
                return delays["*"]
        return 0.0

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

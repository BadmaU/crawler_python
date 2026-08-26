import asyncio
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SemaphoreManager:
    def __init__(
        self,
        global_limit: int = 10,
        per_domain_limit: int = 3,
    ) -> None:
        self._global_semaphore = asyncio.Semaphore(global_limit)
        self._per_domain_limit = per_domain_limit
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}
        self._active_tasks: int = 0
        self._domain_active: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc

    async def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        async with self._lock:
            if domain not in self._domain_semaphores:
                self._domain_semaphores[domain] = asyncio.Semaphore(
                    self._per_domain_limit
                )
            return self._domain_semaphores[domain]

    async def acquire(self, url: str) -> None:
        domain = self._get_domain(url)
        await self._global_semaphore.acquire()
        domain_sem = await self._get_domain_semaphore(domain)
        await domain_sem.acquire()
        async with self._lock:
            self._active_tasks += 1
            self._domain_active[domain] = self._domain_active.get(domain, 0) + 1

    async def release(self, url: str) -> None:
        domain = self._get_domain(url)
        domain_sem = await self._get_domain_semaphore(domain)
        domain_sem.release()
        self._global_semaphore.release()
        async with self._lock:
            self._active_tasks = max(0, self._active_tasks - 1)
            self._domain_active[domain] = max(
                0, self._domain_active.get(domain, 0) - 1
            )

    def get_stats(self) -> dict:
        return {
            "active_tasks": self._active_tasks,
            "domain_active": dict(self._domain_active),
            "tracked_domains": list(self._domain_semaphores.keys()),
        }

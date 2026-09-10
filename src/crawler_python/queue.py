import asyncio
import heapq
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(order=True)
class URLItem:
    priority: int
    url: str = field(compare=False)
    depth: int = field(default=0, compare=False)


class CrawlerQueue:
    def __init__(self) -> None:
        self._heap: list[URLItem] = []
        self._in_queue: set[str] = set()
        self._processed: set[str] = set()
        self._failed: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._item_event = asyncio.Event()
        self._active_tasks = 0

    async def add_url(self, url: str, priority: int = 0, depth: int = 0) -> bool:
        async with self._lock:
            if url in self._in_queue or url in self._processed:
                return False
            item = URLItem(priority=priority, url=url, depth=depth)
            heapq.heappush(self._heap, item)
            self._in_queue.add(url)
            self._item_event.set()
            return True

    async def get_next(self) -> URLItem | None:
        async with self._lock:
            while self._heap:
                item = heapq.heappop(self._heap)
                self._in_queue.discard(item.url)
                if item.url not in self._processed:
                    return item
        return None

    async def get_next_or_wait(self, timeout: float = 0.5) -> URLItem | None:
        while True:
            item = await self.get_next()
            if item is not None:
                return item
            if self._active_tasks == 0 and self.is_empty_sync():
                return None
            self._item_event.clear()
            try:
                await asyncio.wait_for(self._item_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue

    def is_empty_sync(self) -> bool:
        return len(self._heap) == 0

    async def mark_processed(self, url: str) -> None:
        async with self._lock:
            self._processed.add(url)

    async def mark_failed(self, url: str, error: str) -> None:
        async with self._lock:
            self._failed[url] = error
            self._processed.add(url)

    def task_started(self) -> None:
        self._active_tasks += 1

    def task_finished(self) -> None:
        self._active_tasks = max(0, self._active_tasks - 1)
        if self._active_tasks == 0 and len(self._heap) == 0:
            self._item_event.set()

    async def is_empty(self) -> bool:
        async with self._lock:
            return len(self._heap) == 0

    def get_stats(self) -> dict:
        return {
            "in_queue": len(self._heap),
            "processed": len(self._processed),
            "failed": len(self._failed),
            "failed_urls": dict(self._failed),
        }

import asyncio
import logging
import random
import time

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(
        self,
        requests_per_second: float = 1.0,
        per_domain: bool = True,
        min_delay: float = 0.0,
        jitter: float = 0.0,
    ) -> None:
        self._rps = requests_per_second
        self._per_domain = per_domain
        self._min_delay = min_delay
        self._jitter = jitter
        self._global_interval = 1.0 / requests_per_second
        self._global_last: float = 0.0
        self._domain_last: dict[str, float] = {}
        self._domain_intervals: dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._total_waits: int = 0
        self._total_wait_time: float = 0.0
        self._blocked_count: int = 0

    def set_domain_rate(self, domain: str, requests_per_second: float) -> None:
        self._domain_intervals[domain] = 1.0 / requests_per_second

    async def acquire(self, domain: str | None = None) -> None:
        now = time.monotonic()
        wait = 0.0

        async with self._lock:
            if self._per_domain and domain:
                interval = self._domain_intervals.get(
                    domain, self._global_interval
                )
                last = self._domain_last.get(domain, 0.0)
                elapsed = now - last
                if elapsed < interval:
                    wait = interval - elapsed
                self._domain_last[domain] = now + wait
            else:
                elapsed = now - self._global_last
                if elapsed < self._global_interval:
                    wait = self._global_interval - elapsed
                self._global_last = now + wait

            if self._min_delay > 0:
                wait = max(wait, self._min_delay)

            if self._jitter > 0:
                wait += random.uniform(0, self._jitter)

        if wait > 0:
            self._total_waits += 1
            self._total_wait_time += wait
            logger.debug("Ожидание %.3fс для %s", wait, domain or "global")
            await asyncio.sleep(wait)

    def record_blocked(self) -> None:
        self._blocked_count += 1

    def get_stats(self) -> dict:
        return {
            "total_waits": self._total_waits,
            "total_wait_time": round(self._total_wait_time, 3),
            "avg_wait": (
                round(self._total_wait_time / self._total_waits, 3)
                if self._total_waits
                else 0.0
            ),
            "blocked_by_robots": self._blocked_count,
        }

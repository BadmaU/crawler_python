import asyncio
import time

import pytest

from crawler_python.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limit_delay():
    rl = RateLimiter(requests_per_second=10.0, per_domain=False, min_delay=0.0)
    start = time.monotonic()
    await rl.acquire()
    await rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


@pytest.mark.asyncio
async def test_per_domain_separate():
    rl = RateLimiter(requests_per_second=10.0, per_domain=True, min_delay=0.0)
    start = time.monotonic()
    await rl.acquire("a.com")
    await rl.acquire("b.com")
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


@pytest.mark.asyncio
async def test_same_domain_throttled():
    rl = RateLimiter(requests_per_second=10.0, per_domain=True, min_delay=0.0)
    start = time.monotonic()
    await rl.acquire("a.com")
    await rl.acquire("a.com")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


@pytest.mark.asyncio
async def test_min_delay():
    rl = RateLimiter(
        requests_per_second=100.0, per_domain=False, min_delay=0.1
    )
    start = time.monotonic()
    await rl.acquire()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


@pytest.mark.asyncio
async def test_set_domain_rate():
    rl = RateLimiter(requests_per_second=10.0, per_domain=True)
    rl.set_domain_rate("slow.com", 1.0)
    start = time.monotonic()
    await rl.acquire("slow.com")
    await rl.acquire("slow.com")
    elapsed = time.monotonic() - start
    assert elapsed >= 0.9


@pytest.mark.asyncio
async def test_stats():
    rl = RateLimiter(requests_per_second=1.0, per_domain=False, min_delay=0.01)
    await rl.acquire()
    stats = rl.get_stats()
    assert stats["total_waits"] == 1
    assert stats["total_wait_time"] > 0


def test_record_blocked():
    rl = RateLimiter()
    rl.record_blocked()
    rl.record_blocked()
    assert rl.get_stats()["blocked_by_robots"] == 2

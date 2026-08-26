import asyncio
import time

import pytest

from crawler_python.concurrency import SemaphoreManager


@pytest.mark.asyncio
async def test_acquire_release():
    sm = SemaphoreManager(global_limit=2, per_domain_limit=1)
    await sm.acquire("https://a.com/1")
    stats = sm.get_stats()
    assert stats["active_tasks"] == 1
    assert "a.com" in stats["domain_active"]
    await sm.release("https://a.com/1")
    stats = sm.get_stats()
    assert stats["active_tasks"] == 0


@pytest.mark.asyncio
async def test_global_limit():
    sm = SemaphoreManager(global_limit=2, per_domain_limit=10)
    results = []

    async def task(i: int) -> None:
        await sm.acquire(f"https://host{i}.com/page")
        results.append(i)
        await asyncio.sleep(0.05)
        await sm.release(f"https://host{i}.com/page")

    tasks = [asyncio.create_task(task(i)) for i in range(4)]
    await asyncio.gather(*tasks)
    assert len(results) == 4


@pytest.mark.asyncio
async def test_per_domain_limit():
    sm = SemaphoreManager(global_limit=10, per_domain_limit=1)
    order = []

    async def task(url: str) -> None:
        await sm.acquire(url)
        order.append(url)
        await asyncio.sleep(0.01)
        await sm.release(url)

    tasks = [
        asyncio.create_task(task("https://a.com/1")),
        asyncio.create_task(task("https://a.com/2")),
    ]
    await asyncio.gather(*tasks)
    assert len(order) == 2


@pytest.mark.asyncio
async def test_domain_tracking():
    sm = SemaphoreManager(global_limit=10, per_domain_limit=5)
    await sm.acquire("https://a.com/1")
    await sm.acquire("https://b.com/1")
    stats = sm.get_stats()
    assert "a.com" in stats["domain_active"]
    assert "b.com" in stats["domain_active"]
    assert stats["active_tasks"] == 2
    await sm.release("https://a.com/1")
    await sm.release("https://b.com/1")

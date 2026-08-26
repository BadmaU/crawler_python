import asyncio

import pytest

from crawler_python.queue import CrawlerQueue


@pytest.mark.asyncio
async def test_add_and_get():
    q = CrawlerQueue()
    await q.add_url("https://a.com")
    item = await q.get_next()
    assert item is not None
    assert item.url == "https://a.com"


@pytest.mark.asyncio
async def test_priority_order():
    q = CrawlerQueue()
    await q.add_url("https://low.com", priority=10)
    await q.add_url("https://high.com", priority=1)
    first = await q.get_next()
    assert first.url == "https://high.com"


@pytest.mark.asyncio
async def test_no_duplicates():
    q = CrawlerQueue()
    added1 = await q.add_url("https://a.com")
    added2 = await q.add_url("https://a.com")
    assert added1 is True
    assert added2 is False
    item = await q.get_next()
    assert item.url == "https://a.com"
    assert await q.get_next() is None


@pytest.mark.asyncio
async def test_mark_processed():
    q = CrawlerQueue()
    await q.add_url("https://a.com")
    item = await q.get_next()
    await q.mark_processed(item.url)
    stats = q.get_stats()
    assert stats["processed"] == 1
    assert await q.get_next() is None


@pytest.mark.asyncio
async def test_mark_failed():
    q = CrawlerQueue()
    await q.add_url("https://a.com")
    item = await q.get_next()
    await q.mark_failed(item.url, "timeout")
    stats = q.get_stats()
    assert stats["failed"] == 1
    assert stats["failed_urls"]["https://a.com"] == "timeout"


@pytest.mark.asyncio
async def test_get_stats():
    q = CrawlerQueue()
    await q.add_url("https://a.com")
    await q.add_url("https://b.com")
    await q.get_next()
    stats = q.get_stats()
    assert stats["in_queue"] == 1
    assert stats["processed"] == 0


@pytest.mark.asyncio
async def test_is_empty():
    q = CrawlerQueue()
    assert await q.is_empty() is True
    await q.add_url("https://a.com")
    assert await q.is_empty() is False
    await q.get_next()
    assert await q.is_empty() is True


@pytest.mark.asyncio
async def test_depth_tracking():
    q = CrawlerQueue()
    await q.add_url("https://a.com", depth=0)
    await q.add_url("https://b.com", depth=2)
    item1 = await q.get_next()
    item2 = await q.get_next()
    assert item1.depth == 0
    assert item2.depth == 2

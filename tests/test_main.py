import asyncio
import time

import aiohttp
import pytest

from crawler_python.crawler import AsyncCrawler


@pytest.fixture
async def crawler():
    c = AsyncCrawler(max_concurrent=3, timeout=5)
    yield c
    await c.close()


@pytest.mark.asyncio
async def test_fetch_valid_url(crawler: AsyncCrawler):
    result = await crawler.fetch_url("https://example.com")
    assert "Example Domain" in result


@pytest.mark.asyncio
async def test_fetch_404(crawler: AsyncCrawler):
    with pytest.raises(aiohttp.ClientResponseError):
        await crawler.fetch_url("https://httpbin.org/status/404")


@pytest.mark.asyncio
async def test_fetch_500(crawler: AsyncCrawler):
    with pytest.raises(aiohttp.ClientResponseError):
        await crawler.fetch_url("https://httpbin.org/status/500")


@pytest.mark.asyncio
async def test_fetch_nonexistent_host(crawler: AsyncCrawler):
    with pytest.raises(aiohttp.ClientError):
        await crawler.fetch_url("https://this-host-does-not-exist-12345.com")


@pytest.mark.asyncio
async def test_fetch_timeout():
    c = AsyncCrawler(max_concurrent=1, timeout=1)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await c.fetch_url("https://httpbin.org/delay/5")
    finally:
        await c.close()


@pytest.mark.asyncio
async def test_fetch_urls_multiple(crawler: AsyncCrawler):
    urls = [
        "https://example.com",
        "https://httpbin.org/delay/1",
    ]
    results = await crawler.fetch_urls(urls)
    assert len(results) == 2
    assert "Example Domain" in results["https://example.com"]
    assert results["https://httpbin.org/delay/1"] != ""


@pytest.mark.asyncio
async def test_parallel_faster_than_sequential():
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]

    start = time.perf_counter()
    c = AsyncCrawler(max_concurrent=3, timeout=5)
    await c.fetch_urls(urls)
    await c.close()
    parallel_time = time.perf_counter() - start

    start = time.perf_counter()
    c2 = AsyncCrawler(max_concurrent=1, timeout=5)
    for url in urls:
        await c2.fetch_url(url)
    await c2.close()
    sequential_time = time.perf_counter() - start

    assert parallel_time < sequential_time

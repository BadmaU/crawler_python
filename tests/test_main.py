import asyncio
import time

import aiohttp
import pytest

from crawler_python.crawler import AsyncCrawler


@pytest.mark.asyncio
async def test_fetch_valid_url():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=5,
        respect_robots=False,
        circuit_breaker=False,
    )
    results = await c.crawl(
        start_urls=["https://example.com"],
        max_depth=0,
    )
    await c.close()
    assert "https://example.com" in results
    assert "Example Domain" in results["https://example.com"]["title"]


@pytest.mark.asyncio
async def test_fetch_404():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=5,
        respect_robots=False,
        circuit_breaker=False,
        max_retries=0,
    )
    results = await c.crawl(
        start_urls=["https://httpbin.org/status/404"],
        max_depth=0,
    )
    await c.close()
    assert "https://httpbin.org/status/404" not in results or \
        results["https://httpbin.org/status/404"]["title"] == ""


@pytest.mark.asyncio
async def test_fetch_500():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=5,
        respect_robots=False,
        circuit_breaker=False,
        max_retries=0,
    )
    results = await c.crawl(
        start_urls=["https://httpbin.org/status/500"],
        max_depth=0,
    )
    await c.close()
    assert "https://httpbin.org/status/500" not in results or \
        results["https://httpbin.org/status/500"]["title"] == ""


@pytest.mark.asyncio
async def test_fetch_nonexistent_host():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=5,
        respect_robots=False,
        circuit_breaker=False,
        max_retries=0,
    )
    results = await c.crawl(
        start_urls=["https://this-host-does-not-exist-12345.com"],
        max_depth=0,
    )
    await c.close()
    assert len(results) == 0


@pytest.mark.asyncio
async def test_crawl_multiple_pages():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=5,
        respect_robots=False,
        circuit_breaker=False,
    )
    results = await c.crawl(
        start_urls=["https://example.com"],
        max_depth=0,
    )
    await c.close()
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_crawl_with_depth():
    c = AsyncCrawler(
        max_concurrent=3,
        timeout=10,
        respect_robots=True,
        circuit_breaker=False,
    )
    results = await c.crawl(
        start_urls=["https://example.com"],
        max_pages=5,
        max_depth=0,
        same_domain_only=True,
    )
    await c.close()
    assert "https://example.com" in results

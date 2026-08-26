import pytest

from crawler_python import AsyncCrawler
from crawler_python.queue import CrawlerQueue


@pytest.mark.asyncio
async def test_crawl_example_com():
    crawler = AsyncCrawler(
        max_concurrent=3,
        per_domain=2,
        timeout=5,
        respect_robots=True,
        circuit_breaker=False,
    )
    results = await crawler.crawl(
        start_urls=["https://example.com"],
        max_pages=5,
        max_depth=0,
        same_domain_only=True,
    )
    await crawler.close()
    assert "https://example.com" in results
    assert results["https://example.com"]["title"] == "Example Domain"


@pytest.mark.asyncio
async def test_depth_limit():
    q = CrawlerQueue()
    await q.add_url("https://a.com", depth=0)
    await q.add_url("https://b.com", depth=3)
    item = await q.get_next()
    assert item.depth == 0
    item2 = await q.get_next()
    assert item2.depth == 3

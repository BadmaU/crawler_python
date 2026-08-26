import asyncio
import logging

from crawler_python import AsyncCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def main() -> None:
    crawler = AsyncCrawler(
        max_concurrent=3,
        per_domain=2,
        timeout=10,
        requests_per_second=2.0,
        min_delay=0.3,
        jitter=0.2,
        respect_robots=True,
        user_agent="MyBot/1.0",
    )
    results = await crawler.crawl(
        start_urls=["https://example.com"],
        max_pages=10,
        max_depth=1,
        same_domain_only=True,
    )
    await crawler.close()

    print(f"\nОбработано: {len(results)} страниц")
    for url, data in results.items():
        print(f"  {url} — {data['title']} ({len(data['text'])} символов)")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging
import time

from crawler_python import AsyncCrawler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


async def main() -> None:
    crawler = AsyncCrawler(max_concurrent=5, timeout=10)
    urls = [
        "https://example.com",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2",
        "https://httpbin.org/status/404",
        "https://httpbin.org/status/500",
    ]

    start = time.perf_counter()
    results = await crawler.fetch_urls(urls)
    elapsed = time.perf_counter() - start

    await crawler.close()

    print(f"\nЗагружено {sum(1 for v in results.values() if v)} из {len(urls)} страниц")
    print(f"Время: {elapsed:.2f}с")


if __name__ == "__main__":
    asyncio.run(main())


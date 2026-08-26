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
        "https://httpbin.org/html",
    ]

    start = time.perf_counter()
    tasks = [crawler.fetch_and_parse(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start

    await crawler.close()

    for result in results:
        if isinstance(result, Exception):
            print(f"Ошибка: {result}")
            continue
        print(f"\n--- {result['url']} ---")
        print(f"  Title: {result['title']}")
        print(f"  Text length: {len(result['text'])}")
        print(f"  Links: {len(result['links'])}")
        print(f"  Images: {len(result['images'])}")
        print(f"  Headings: {sum(len(v) for v in result['headings'].values())}")
        print(f"  Tables: {len(result['tables'])}")
        print(f"  Lists: {len(result['lists'])}")

    print(f"\nВремя: {elapsed:.2f}с")


if __name__ == "__main__":
    asyncio.run(main())


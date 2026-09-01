import asyncio
import logging
import os
import tempfile

from crawler_python.crawler import AsyncCrawler
from crawler_python.storage import CSVStorage, JSONStorage, SQLiteStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def demo_json_storage() -> None:
    logger.info("=== Демонстрация JSON Storage ===")
    filepath = os.path.join(tempfile.gettempdir(), "demo_results.json")
    storage = JSONStorage(filepath)
    crawler = AsyncCrawler(
        max_concurrent=2,
        per_domain=1,
        timeout=10,
        respect_robots=False,
        circuit_breaker=False,
        storage=storage,
    )
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=1,
            max_depth=0,
        )
        logger.info("Сохранено страниц в JSON: %d", len(results))
        data = await storage.read_all()
        logger.info("Прочитано из JSON: %d записей", len(data))
        for item in data:
            logger.info("  URL: %s, Title: %s", item.get("url"), item.get("title"))
    finally:
        await crawler.close()
    logger.info("JSON Storage stats: %s", storage.get_stats())


async def demo_csv_storage() -> None:
    logger.info("=== Демонстрация CSV Storage ===")
    filepath = os.path.join(tempfile.gettempdir(), "demo_results.csv")
    storage = CSVStorage(filepath)
    crawler = AsyncCrawler(
        max_concurrent=2,
        per_domain=1,
        timeout=10,
        respect_robots=False,
        circuit_breaker=False,
        storage=storage,
    )
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=1,
            max_depth=0,
        )
        logger.info("Сохранено страниц в CSV: %d", len(results))
        data = await storage.read_all()
        logger.info("Прочитано из CSV: %d записей", len(data))
        for item in data:
            logger.info("  URL: %s, Title: %s", item.get("url"), item.get("title"))
    finally:
        await crawler.close()
    logger.info("CSV Storage stats: %s", storage.get_stats())


async def demo_sqlite_storage() -> None:
    logger.info("=== Демонстрация SQLite Storage ===")
    db_path = os.path.join(tempfile.gettempdir(), "demo_results.db")
    storage = SQLiteStorage(db_path)
    crawler = AsyncCrawler(
        max_concurrent=2,
        per_domain=1,
        timeout=10,
        respect_robots=False,
        circuit_breaker=False,
        storage=storage,
    )
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=1,
            max_depth=0,
        )
        logger.info("Сохранено страниц в SQLite: %d", len(results))
        count = await storage.get_count()
        logger.info("Записей в БД: %d", count)
        data = await storage.read_all()
        for item in data:
            logger.info("  URL: %s, Title: %s", item.get("url"), item.get("title"))
    finally:
        await crawler.close()
    logger.info("SQLite Storage stats: %s", storage.get_stats())


async def demo_statistics() -> None:
    logger.info("=== Статистика по сохранённым данным ===")
    db_path = os.path.join(tempfile.gettempdir(), "demo_stats.db")
    storage = SQLiteStorage(db_path)
    crawler = AsyncCrawler(
        max_concurrent=2,
        per_domain=1,
        timeout=10,
        respect_robots=False,
        circuit_breaker=False,
        storage=storage,
    )
    try:
        results = await crawler.crawl(
            start_urls=["https://example.com"],
            max_pages=1,
            max_depth=0,
        )
        logger.info("--- Статистика ---")
        logger.info("Всего обработано страниц: %d", len(results))
        total_text_len = sum(len(r.get("text", "")) for r in results.values())
        total_links = sum(len(r.get("links", [])) for r in results.values())
        logger.info("Общий объём текста: %d символов", total_text_len)
        logger.info("Всего найдено ссылок: %d", total_links)
        count = await storage.get_count()
        logger.info("Записей в БД: %d", count)
    finally:
        await crawler.close()


async def main() -> None:
    logger.info("День 6 — Демонстрация сохранения данных")
    logger.info("")
    await demo_json_storage()
    logger.info("")
    await demo_csv_storage()
    logger.info("")
    await demo_sqlite_storage()
    logger.info("")
    await demo_statistics()
    logger.info("")
    logger.info("Все демонстрации завершены успешно!")


if __name__ == "__main__":
    asyncio.run(main())

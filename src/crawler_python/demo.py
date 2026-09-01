"""Полный пример использования AsyncCrawler.

Запуск:
    python -m crawler_python.demo
"""

import asyncio

from crawler_python import AsyncCrawler


async def main() -> None:
    # Создание из конфигурационного файла
    crawler = AsyncCrawler.from_config("config.yaml")

    await crawler.crawl()

    stats = crawler.get_stats()
    print(f"Обработано: {stats['total_pages']} страниц")
    print(f"Успешно: {stats['successful']}")
    print(f"Ошибок: {stats['failed']}")
    print(f"Средняя скорость: {stats['avg_speed']:.1f} стр/с")
    print(f"Время работы: {stats['runtime_seconds']:.2f} с")

    crawler.export_to_json()
    crawler.export_to_html_report()

    await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())

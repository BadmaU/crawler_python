"""Командная строка для crawler_python.

Примеры:
    python -m crawler_python --urls https://example.com --max-pages 100 --output results.json
    python -m crawler_python --config config.yaml
"""

import argparse
import asyncio
import json
import logging
import sys

from crawler_python.crawler import AsyncCrawler
from crawler_python.config import CrawlerConfig

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crawler_python",
        description="Асинхронный веб-краулер с расширенной статистикой и отчётами.",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        default=None,
        help="Один или несколько стартовых URL",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Максимальное количество обрабатываемых страниц",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Максимальная глубина обхода ссылок",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Файл для сохранения результатов (JSON)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Путь к конфигурационному файлу (YAML/JSON)",
    )
    parser.add_argument(
        "--respect-robots",
        action="store_true",
        default=None,
        help="Соблюдать robots.txt",
    )
    parser.add_argument(
        "--no-respect-robots",
        action="store_true",
        default=None,
        help="Игнорировать robots.txt",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=None,
        help="Лимит запросов в секунду",
    )
    parser.add_argument(
        "--output-report",
        default=None,
        help="Путь к HTML-отчёту (по умолчанию report.html)",
    )
    parser.add_argument(
        "--output-stats",
        default=None,
        help="Путь к JSON-файлу статистики (по умолчанию stats.json)",
    )
    parser.add_argument(
        "--storage",
        choices=["json", "csv", "sqlite", "none"],
        default=None,
        help="Тип хранилища для результатов",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Уровень логирования",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Файл логов",
    )
    return parser


def build_config(args: argparse.Namespace) -> CrawlerConfig:
    config = CrawlerConfig()

    if args.config:
        file_config = CrawlerConfig.from_file(args.config)
        config = file_config

    if args.urls:
        config.start_urls = args.urls
    if args.max_pages is not None:
        config.max_pages = args.max_pages
    if args.max_depth is not None:
        config.max_depth = args.max_depth
    if args.rate_limit is not None:
        config.requests_per_second = args.rate_limit
    if args.respect_robots:
        config.respect_robots = True
    if args.no_respect_robots:
        config.respect_robots = False
    if args.output:
        config.storage_path = args.output
    if args.output_report:
        config.output_report = args.output_report
    if args.output_stats:
        config.output_stats = args.output_stats
    if args.storage:
        config.storage = args.storage
    if args.log_level:
        config.logging_level = args.log_level
    if args.log_file:
        config.log_file = args.log_file

    return config


async def amain(args: argparse.Namespace) -> int:
    config = build_config(args)

    if not config.start_urls:
        print("Ошибка: не указаны стартовые URL (--urls или --config)", file=sys.stderr)
        return 2

    crawler = AsyncCrawler(config=config)

    try:
        await crawler.crawl()

        stats = crawler.get_stats()
        print(f"\nОбработано: {stats['total_pages']} страниц")
        print(f"Успешно: {stats['successful']}")
        print(f"Ошибок: {stats['failed']}")
        print(f"Средняя скорость: {stats['avg_speed']:.1f} стр/с")
        print(f"Время работы: {stats['runtime_seconds']:.2f} с")

        crawler.export_to_json()
        crawler.export_to_html_report()

        if config.output_stats:
            crawler.export_to_json(config.output_stats)

        report_file = config.output_report or "report.html"
        print(f"Отчёт сохранён: {report_file}")

        results_path = config.storage_path
        print(f"Результаты сохранены: {results_path}")
        return 0
    finally:
        await crawler.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    code = asyncio.run(amain(args))
    sys.exit(code)


if __name__ == "__main__":
    main()

# Асинхронный Веб-Краулер

Цель проекта — разработать высокопроизводительный асинхронный веб-краулер, способный эффективно собирать данные с множества веб-страниц параллельно, обрабатывать ошибки, соблюдать правила вежливости и сохранять результаты. Все части проекта должны быть реализованы с использованием асинхронного программирования на Python (asyncio, aiohttp).

Проект состоит из 7 этапов, соответствующих 7 дням разработки, и финальной интеграции.

## 📋 Общая концепция проекта

Вы разрабатываете модульный асинхронный краулер, поддерживающий:
- 🌐 параллельную загрузку множества веб-страниц
- 📄 парсинг HTML-контента с извлечением данных
- ⚡️ управление конкурентностью и ограничение скорости запросов
- 🔄 обработку ошибок и автоматические повторы
- 💾 сохранение данных в файлы и базы данных
- 🤖 соблюдение robots.txt и задержек между запросами
- 🔧 расширяемость для различных типов сайтов и данных

## 🏗️ Ключевые концепции

В проекте должны учитываться:
- ⚡️ асинхронное программирование (async/await)
- 🔄 конкурентность и параллелизм
- 💾 управление ресурсами (connection pooling)
- ⚠️ обработка исключений в асинхронном контексте
- 📝 структурированное логирование
- 🧪 тестирование асинхронного кода
- ⚡️ производительность и оптимизация

Каждый следующий этап усложняет предыдущий функционал и расширяет архитектуру.

## 🛠️ Технологический стек

- asyncio — базовая библиотека для асинхронного программирования
- aiohttp — асинхронный HTTP-клиент
- aiofiles — асинхронная работа с файлами
- BeautifulSoup4 или lxml — парсинг HTML
- aiosqlite или asyncpg — асинхронная работа с БД (опционально)

## 📋 Общие требования

1. ⚡️ Все сетевые операции должны быть асинхронными
2. 🔄 Использовать connection pooling для HTTP-запросов
3. 🚦 Реализовать rate limiting для соблюдения правил вежливости
4. ⚠️ Обрабатывать таймауты и сетевые ошибки
5. 📝 Логировать все важные события
6. 🏗️ Структурировать код в модули и классы
7. 🧪 Подготовить код к тестированию

## 🎉 Критерии успешного завершения

К концу 7 дней краулер должен уметь:
- 🌐 Загружать сотни страниц параллельно
- 📄 Парсить HTML и извлекать структурированные данные
- ⏰️ Соблюдать задержки между запросами
- 🔄 Обрабатывать ошибки и повторять неудачные запросы
- 💾 Сохранять результаты в файлы и/или БД
- 🤖 Работать с robots.txt
- 📊 Показывать статистику работы (успешные/неудачные запросы, скорость)

## Установка

```bash
uv sync
```

## Запуск

```bash
uv run python -m crawler_python --urls https://example.com
```

## Тесты

```bash
uv run pytest
```

---

# 📖 Мануал по использованию

Практическое руководство: установка, настройка и запуск краулера — через
командную строку, конфигурационный файл или как Python-библиотеку.

## 1. Установка

Требования: **Python 3.14+** и пакетный менеджер [uv](https://docs.astral.sh/uv/).

```bash
git clone <адрес-репозитория>
cd crawler_python
uv sync              # создать окружение и установить зависимости
```

Дальше все команды запускаются через `uv run`, чтобы работать в созданном окружении.

## 2. Быстрый старт (CLI)

Самый простой запуск:

```bash
uv run python -m crawler_python --urls https://example.com
```

С ограничениями по количеству страниц и глубине обхода:

```bash
uv run python -m crawler_python \
    --urls https://example.com https://docs.example.org \
    --max-pages 500 \
    --max-depth 3
```

После запуска в рабочей папке создаются:

- `results.json` — собранные данные (путь меняется флагом `--output`);
- `report.html` — HTML-отчёт со статистикой и графиками (`--output-report`);
- `stats.json` — статистика в машиночитаемом виде (`--output-stats`).

## 3. Параметры командной строки

Полный список выводит команда `uv run python -m crawler_python --help`.

| Параметр | Описание |
| --- | --- |
| `--urls URL [URL ...]` | Один или несколько стартовых URL |
| `--max-pages N` | Максимальное число обрабатываемых страниц |
| `--max-depth N` | Глубина перехода по ссылкам (`0` — только стартовые URL) |
| `--output FILE` | Файл для сохранения данных (JSON) |
| `--config FILE` | Путь к конфигурационному файлу YAML/JSON |
| `--respect-robots` | Соблюдать robots.txt |
| `--no-respect-robots` | Игнорировать robots.txt |
| `--rate-limit RPS` | Максимум запросов в секунду |
| `--output-report FILE` | Путь к HTML-отчёту |
| `--output-stats FILE` | Путь к JSON-файлу статистики |
| `--storage {json,csv,sqlite,none}` | Тип хранилища результатов |
| `--log-level LEVEL` | Уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--log-file FILE` | Файл для логов |

Все параметры необязательные: значения по умолчанию берутся из конфигурации.

## 4. Конфигурация через config.yaml

Конфигурационный файл задаёт все параметры и упрощает повторные запуски:

```bash
uv run python -m crawler_python --config config.yaml
```

Пример готового файла — `config.yaml` в корне проекта. Основные блоки:

```yaml
start_urls: [https://example.com]      # стартовые URL
max_pages: 100                         # максимум страниц
max_depth: 3                           # глубина обхода
same_domain_only: true                 # не выходить за пределы домена

exclude_patterns: ["*/admin/*", "*/login"]  # fnmatch-паттерны исключений
include_patterns: []                   # если непусто — краулить только эти URL

max_concurrent: 10                     # параллельных задач
per_domain: 3                          # задач на один домен
requests_per_second: 5.0               # общий лимит, запросов/сек
min_delay: 0.0                         # минимальная пауза между запросами
jitter: 0.0                            # случайная добавка к паузе

respect_robots: true                   # соблюдать robots.txt
user_agent: "MyCrawler/2.0"
max_retries: 3                         # повторы при временных ошибках
backoff_factor: 2.0                    # экспоненциальная задержка
circuit_breaker: true                  # защита от «падающего» домена

use_sitemap: false                     # брать стартовые URL из sitemap.xml
sitemap_urls: []

storage: json                          # json | csv | sqlite | none
storage_path: results.json
output_report: report.html
output_stats: stats.json

logging_level: INFO
log_file: crawler.log
```

Правило приоритета: **параметры командной строки переопределяют значения из файла**.
Например, `--config config.yaml --storage csv --rate-limit 2` сменит формат
сохранения и скорость, не трогая остальные настройки.

## 5. Программное использование (как библиотека)

Краулер можно подключать прямо из Python-кода:

```python
import asyncio
from crawler_python import AsyncCrawler

async def main():
    # 1. Создание из конфигурации (или передать параметры напрямую конструктору)
    crawler = AsyncCrawler.from_config("config.yaml")

    # 2. Запуск обхода (аргументы переопределяют конфигурацию)
    results = await crawler.crawl(start_urls=["https://example.com"], max_pages=100)

    # 3. Статистика
    stats = crawler.get_stats()
    print(f"Обработано: {stats['total_pages']}, успешно: {stats['successful']}")

    # 4. Экспорт отчётов
    crawler.export_to_html_report("report.html")
    crawler.export_to_json("stats.json")

    # 5. Закрыть сетевые ресурсы
    await crawler.close()

asyncio.run(main())
```

Доступ к данным: `crawler.results` — словарь `{url: результат_парсинга}`,
`crawler.config` — активный объект конфигурации.

## 6. Сохранение данных

| Формат | Значение `--storage` / `storage` | Куда пишется |
| --- | --- | --- |
| JSON | `json` | файл, список объектов (по умолчанию) |
| CSV | `csv` | таблица; вложенные структуры сериализуются в JSON-строку |
| SQLite | `sqlite` | БД с таблицей `pages`, колонка `url` уникальна |
| Без сохранения | `none` | только статистика и отчёты |

```bash
uv run python -m crawler_python --urls https://example.com --storage csv --output data.csv
uv run python -m crawler_python --urls https://example.com --storage sqlite --output crawler.db
```

## 7. Статистика и отчёты

`stats.json` содержит: обработано / успешно / ошибок, среднюю и текущую скорость,
распределение по HTTP-кодам, топ доменов, время работы.
`report.html` — человекочитаемая версия с графиками и таблицами.

```bash
uv run python -m crawler_python --urls https://example.com \
    --storage none --output-report report.html --output-stats stats.json
```

## 8. Повторы, ошибки и надёжность

- Сетевые сбои повторяются до `max_retries` раз с нарастающей паузой
  (`backoff_factor`), временные и постоянные ошибки различаются (`errors.py`).
- Circuit breaker останавливает запросы к «падающему» домену.
- URL, заблокированные `robots.txt`, не запрашиваются и попадают в статистику
  как ошибки.
- Сбой сохранения данных не останавливает краулинг: ошибка логируется и
  учитывается в финальной статистике.

## 9. Sitemap

При `use_sitemap: true` стартовые URL берутся из sitemap.xml (включая индексные
sitemap и адреса из robots.txt), а не из `start_urls`:

```bash
uv run python -m crawler_python --config config-with-sitemap.yaml
```

```yaml
use_sitemap: true
# sitemap_urls: ["https://example.com/sitemap.xml"]  # можно указать явно
```

## 10. Советы

- Начните с малого: `--max-pages 10 --max-depth 1 --no-respect-robots` — работает
  быстрее и не нагружает сайт при отладке.
- Для продакшена оставляйте `respect_robots: true` и разумный `--rate-limit`.
- Следите за логами: `--log-level DEBUG` покажет каждую загрузку и повторы.
- Все артефакты (`results.*`, `report.html`, `stats.json`, `crawler.log`) удобно
  вынести в отдельную папку и добавить в `.gitignore`.

---

# 📦 День 7 — Продвинутые возможности и финальная интеграция

## Обзор

В день 7 продвинутые возможности встроены в единый класс `AsyncCrawler`, который интегрирует все компоненты предыдущих дней: краулер, sitemap-парсер, расширенную статистику, экспорт отчётов, файл конфигурации, CLI, логирование и мониторинг. Нет отдельных «базового» и «продвинутого» классов — это одно приложение со всеми функциями.

## 🚀 Быстрый старт

Установка: `uv sync`

CLI-интерфейс:

```bash
# Базовый запуск
uv run python -m crawler_python --urls https://example.com --max-pages 100

# С конфигурационным файлом
uv run python -m crawler_python --config config.yaml

# Полное управление параметрами
uv run python -m crawler_python \
    --urls https://example.com https://docs.example.org \
    --max-pages 500 \
    --max-depth 3 \
    --output results.json \
    --respect-robots \
    --rate-limit 5 \
    --storage json \
    --output-report report.html
```

Программное использование:

```python
import asyncio
from crawler_python import AsyncCrawler

async def main():
    crawler = AsyncCrawler.from_config("config.yaml")
    await crawler.crawl()

    stats = crawler.get_stats()
    print(f"Обработано: {stats['total_pages']} страниц")
    print(f"Успешно: {stats['successful']}")
    print(f"Ошибок: {stats['failed']}")

    crawler.export_to_html_report("report.html")
    crawler.export_to_json("stats.json")
    await crawler.close()

asyncio.run(main())
```

## 🗂️ Новые модули

| Модуль | Назначение |
|--------|-----------|
| `crawler.py` | Единый класс `AsyncCrawler`, объединяющий все компоненты |
| `parser.py` | `HTMLParser` — парсинг HTML и извлечение контента |
| `sitemap.py` | `SitemapParser` — загрузка и разбор sitemap.xml |
| `stats.py` | `CrawlerStats` — расширенная статистика и экспорт отчётов |
| `config.py` | `CrawlerConfig` — загрузка конфигурации из YAML/JSON |
| `logging_setup.py` | `setup_logging` — структурированное логирование с ротацией |
| `monitor.py` | `ProgressMonitor` — мониторинг прогресса в реальном времени |
| `storage.py` | `DataStorage` / `JSONStorage` / `CSVStorage` / `SQLiteStorage` |

## ⚙️ Конфигурация (config.yaml)

Полный пример конфигурации находится в `config.yaml`. Основные разделы:

```yaml
start_urls:
  - https://example.com
max_pages: 100
max_depth: 3
same_domain_only: true

max_concurrent: 10
per_domain: 3
requests_per_second: 5.0
respect_robots: true
user_agent: "MyCrawler/2.0"
max_retries: 3
backoff_factor: 2.0
circuit_breaker: true

include_patterns: []
exclude_patterns: ["*/admin/*", "*/login"]

use_sitemap: false
sitemap_urls:
  - https://example.com/sitemap.xml

storage: json          # json | csv | sqlite | none
storage_path: results.json
output_report: report.html
output_stats: stats.json

logging_level: INFO
log_file: crawler.log
log_rotation: 5
log_max_bytes: 5000000
```

## 🕸️ Sitemap

`SitemapParser` поддерживает обычные и индексные sitemap, рекурсивно обрабатывает sitemapindex, а также умеет доставать адреса sitemap из robots.txt.

```python
from crawler_python import SitemapParser
import asyncio

async def main():
    parser = SitemapParser()
    urls = await parser.fetch_sitemap("https://example.com/sitemap.xml")
    print(len(urls), "URL из sitemap")
    await parser.close()

asyncio.run(main())
```

При `use_sitemap: true` в конфигурации URL из sitemap автоматически используются как источник стартовых URL.

## 📊 Статистика и отчёты

`CrawlerStats` собирает:
- количество обработанных/успешных/неудачных страниц
- среднюю и текущую скорость обработки
- распределение по статус-кодам
- топ доменов по количеству страниц
- время работы

Экспорт: `export_to_json(filename)` и `export_to_html_report(filename)` (визуализация с графиками и таблицами).

## 🖥️ CLI (argparse)

```
python crawler.py --urls URLS [URLS ...] [--max-pages N] [--max-depth N]
                  [--output FILE] [--config FILE] [--respect-robots]
                  [--no-respect-robots] [--rate-limit RPS]
                  [--output-report FILE] [--output-stats FILE]
                  [--storage {json,csv,sqlite,none}]
                  [--log-level LEVEL] [--log-file FILE]
```

Параметры командной строки переопределяют значения из конфигурационного файла.

## 📝 Логирование

`setup_logging(level, log_file, rotation_backups, max_bytes)` настраивает:
- запись в файл и консоль
- уровни DEBUG/INFO/WARNING/ERROR
- ротацию лог-файлов (`RotatingFileHandler`)
- форматирование с временными метками

## 📈 Мониторинг в реальном времени

`ProgressMonitor` выводит прогресс-бар с процентом выполнения, текущей скоростью (стр/с), оценкой оставшегося времени (ETA) и количеством активных задач.

## 📚 API `AsyncCrawler` (единый класс-приложение)

- `AsyncCrawler(...)` — параметры краулинга напрямую
- `AsyncCrawler.from_config(path)` / `AsyncCrawler.from_dict(dict)` — из конфигурации
- `await crawler.crawl(start_urls=None, max_pages=None, max_depth=None, ...)` — основной цикл краулинга
- `crawler.get_stats()` — словарь расширенной статистики
- `crawler.export_to_json(filename)` — экспорт статистики в JSON
- `crawler.export_to_html_report(filename)` — создание HTML-отчёта
- `await crawler.close()` — освобождение ресурсов
- `crawler.results` — словарь `{url: parsed_result}`
- `crawler.config` — объект `CrawlerConfig`

## ✅ Критерии успеха

- [x] Все компоненты интегрированы в единый `AsyncCrawler`
- [x] Краулер стабильно работает на больших объёмах
- [x] Конфигурация настраивается через YAML/JSON файл
- [x] Удобный CLI интерфейс
- [x] Информативные статистика и отчёты
- [x] Код документирован и протестирован


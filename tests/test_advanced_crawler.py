import os
import tempfile

from crawler_python import AsyncCrawler, CrawlerConfig
from crawler_python.crawler import AsyncCrawler as AC


def test_config_storage_json():
    cfg = CrawlerConfig(storage="json", storage_path="x.json", log_file=None)
    ac = AC(config=cfg)
    assert type(ac._storage).__name__ == "JSONStorage"
    import asyncio
    asyncio.run(ac.close())


def test_config_storage_none():
    cfg = CrawlerConfig(storage="none", log_file=None)
    ac = AC(config=cfg)
    assert ac._storage is None
    import asyncio
    asyncio.run(ac.close())


def test_config_storage_sqlite():
    cfg = CrawlerConfig(storage="sqlite", storage_path=":memory:", log_file=None)
    ac = AC(config=cfg)
    assert type(ac._storage).__name__ == "SQLiteStorage"
    import asyncio
    asyncio.run(ac.close())


def test_config_propagation_to_crawler():
    cfg = CrawlerConfig(
        max_concurrent=7,
        per_domain=2,
        timeout=12,
        requests_per_second=4.0,
        respect_robots=False,
        user_agent="UA-TEST",
        max_retries=5,
        storage="none",
        log_file=None,
    )
    ac = AC(config=cfg)
    assert ac._user_agent == "UA-TEST"
    assert ac._respect_robots is False
    assert ac._timeout.total == 12
    assert ac.config.max_concurrent == 7
    import asyncio
    asyncio.run(ac.close())


def test_from_dict():
    ac = AC.from_dict({"start_urls": ["https://example.com"], "max_pages": 5,
                       "storage": "none", "log_file": None})
    assert ac.config.max_pages == 5
    assert ac.config.start_urls == ["https://example.com"]
    import asyncio
    asyncio.run(ac.close())


def test_from_config_file(tmp_path):
    cfg_path = tmp_path / "c.yaml"
    cfg_path.write_text(
        "start_urls:\n  - https://example.com\nstorage: none\nlog_file: null\n"
    )
    ac = AsyncCrawler.from_config(str(cfg_path))
    assert ac.config.start_urls == ["https://example.com"]
    import asyncio
    asyncio.run(ac.close())

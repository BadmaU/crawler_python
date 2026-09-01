import os
import tempfile

import pytest

from crawler_python.config import CrawlerConfig

SAMPLE_YAML = """
start_urls:
  - https://example.com
max_pages: 50
max_depth: 2
max_concurrent: 5
requests_per_second: 3.0
respect_robots: false
storage: json
storage_path: out.json
"""

SAMPLE_JSON = """
{
  "start_urls": ["https://example.com"],
  "max_pages": 42,
  "exclude_patterns": ["*/admin/*"]
}
"""


def test_from_yaml_file():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(SAMPLE_YAML)
        path = f.name
    try:
        cfg = CrawlerConfig.from_file(path)
        assert cfg.start_urls == ["https://example.com"]
        assert cfg.max_pages == 50
        assert cfg.max_depth == 2
        assert cfg.max_concurrent == 5
        assert cfg.requests_per_second == 3.0
        assert cfg.respect_robots is False
        assert cfg.storage == "json"
        assert cfg.storage_path == "out.json"
    finally:
        os.unlink(path)


def test_from_json_file():
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(SAMPLE_JSON)
        path = f.name
    try:
        cfg = CrawlerConfig.from_file(path)
        assert cfg.max_pages == 42
        assert cfg.start_urls == ["https://example.com"]
        assert cfg.exclude_patterns == ["*/admin/*"]
    finally:
        os.unlink(path)


def test_from_dict_defaults():
    cfg = CrawlerConfig.from_dict({"start_urls": ["https://a.com"]})
    assert cfg.start_urls == ["https://a.com"]
    assert cfg.max_pages == 100
    assert cfg.max_depth == 3
    assert cfg.respect_robots is True


def test_unknown_keys_ignored():
    cfg = CrawlerConfig.from_dict({"unknown_key": 123, "max_pages": 7})
    assert cfg.max_pages == 7


def test_roundtrip_dict():
    cfg = CrawlerConfig()
    cfg.max_pages = 99
    d = cfg.to_dict()
    cfg2 = CrawlerConfig.from_dict(d)
    assert cfg2.max_pages == 99


def test_storage_kwargs():
    cfg = CrawlerConfig()
    assert cfg.storage_kwargs == {"filepath": cfg.storage_path}


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        CrawlerConfig.from_file("nonexistent-path.yaml")

import json
import os
import re
import tempfile

from crawler_python.stats import CrawlerStats


def test_counts_and_success_failure():
    s = CrawlerStats()
    s.start()
    for i in range(5):
        s.record_success(f"https://site{i % 2}.example/page")
    for i in range(3):
        s.record_failure("https://site1.example/error", status=404)
    s.stop()
    assert s.total_pages == 8
    assert s.successful == 5
    assert s.failed == 3


def test_status_distribution():
    s = CrawlerStats()
    s.record_request("https://a.com/x", status=200)
    s.record_request("https://a.com/y", status=200)
    s.record_request("https://a.com/z", status=404)
    dist = s.status_distribution()
    assert dist["200"] == 2
    assert dist["404"] == 1


def test_auto_success_on_status():
    s = CrawlerStats()
    s.record_request("https://a.com/x", status=200)
    s.record_request("https://a.com/y", status=500)
    assert s.successful == 1
    assert s.failed == 1


def test_top_domains():
    s = CrawlerStats()
    s.record_request("https://a.com/1")
    s.record_request("https://a.com/2")
    s.record_request("https://b.com/1")
    top = s.top_domains()
    assert top[0]["domain"] == "a.com"
    assert top[0]["pages"] == 2


def test_speed():
    import time
    s = CrawlerStats()
    s.start()
    for _ in range(10):
        s.record_request("https://a.com/x")
        time.sleep(0.01)
    s.stop()
    assert s.runtime_seconds > 0
    assert s.avg_speed > 0
    snap = s.snapshot()
    assert snap["runtime_seconds"] >= 0


def test_snapshot_keys():
    s = CrawlerStats()
    s.start()
    s.record_request("https://a.com/1", status=200)
    s.stop()
    snap = s.snapshot()
    for key in [
        "total_pages", "successful", "failed", "runtime_seconds",
        "avg_speed", "recent_speed", "status_codes", "top_domains",
        "started_at", "finished_at",
    ]:
        assert key in snap


def test_export_to_json():
    s = CrawlerStats()
    s.start()
    s.record_request("https://a.com/1", status=200)
    s.record_request("https://b.com/2", status=404)
    s.stop()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "sub", "stats.json")
        s.export_to_json(path)
        with open(path) as f:
            data = json.load(f)
        assert data["total_pages"] == 2
        assert data["status_codes"]["200"] == 1


def test_export_to_html_report():
    s = CrawlerStats()
    s.start()
    s.record_request("https://a.com/1", status=200)
    s.record_request("https://a.com/2", status=200)
    s.record_request("https://b.com/3", status=500)
    s.stop()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "report.html")
        s.export_to_html_report(path)
        with open(path) as f:
            content = f.read()
        assert "<html" in content
        assert "total" in content or "Всего" in content
        assert "status" in content
        assert "domain" in content


def test_empty_report():
    s = CrawlerStats()
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "r.html")
        s.export_to_html_report(path)
        with open(path) as f:
            assert "<html" in f.read()

import pytest

from crawler_python.robots import RobotsParser


ROBOTS_TXT = """
User-agent: *
Disallow: /private/
Disallow: /admin
Allow: /public/
Crawl-delay: 5

User-agent: BadBot
Disallow: /

Sitemap: https://example.com/sitemap.xml
"""


def test_parse_robots():
    rp = RobotsParser()
    result = rp._parse_robots_text(ROBOTS_TXT)
    assert "/private/" in result["rules"]["*"]
    assert "/admin" in result["rules"]["*"]
    assert result["rules"]["BadBot"] == ["/"]
    assert result["crawl_delay"]["*"] == 5.0
    assert "https://example.com/sitemap.xml" in result["sitemaps"]


def test_can_fetch_allowed():
    rp = RobotsParser()
    rp._cache["https://example.com"] = rp._parse_robots_text(ROBOTS_TXT)
    assert rp.can_fetch("https://example.com/public/page") is True


def test_can_fetch_disallowed():
    rp = RobotsParser()
    rp._cache["https://example.com"] = rp._parse_robots_text(ROBOTS_TXT)
    assert rp.can_fetch("https://example.com/private/data") is False
    assert rp.can_fetch("https://example.com/admin/settings") is False


def test_can_fetch_badbot():
    rp = RobotsParser(user_agent="BadBot")
    rp._cache["https://example.com"] = rp._parse_robots_text(ROBOTS_TXT)
    assert rp.can_fetch("https://example.com/anything") is False


def test_can_fetch_no_cache():
    rp = RobotsParser()
    assert rp.can_fetch("https://unknown.com/page") is True


def test_get_crawl_delay():
    rp = RobotsParser(user_agent="*")
    rp._cache["https://example.com"] = rp._parse_robots_text(ROBOTS_TXT)
    assert rp.get_crawl_delay() == 5.0


def test_get_crawl_delay_default():
    rp = RobotsParser()
    assert rp.get_crawl_delay() == 0.0


def test_empty_robots():
    rp = RobotsParser()
    result = rp._parse_robots_text("")
    assert result["rules"] == {}
    assert result["crawl_delay"] == {}

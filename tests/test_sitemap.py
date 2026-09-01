import pytest

from crawler_python.sitemap import MAX_RECURSION_DEPTH, SitemapParser

SIMPLE_SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/contact</loc></url>
  <url><loc>not-a-url</loc></url>
</urlset>
"""

INDEX_SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-2.xml</loc></sitemap>
</sitemapindex>
"""

CHILD_SITEMAP = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page</loc></url>
</urlset>
"""


def test_parse_simple_sitemap():
    parser = SitemapParser()
    import asyncio
    urls = asyncio.run(parser._parse_sitemap(SIMPLE_SITEMAP, "https://example.com/sitemap.xml", 0))
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/contact" in urls
    assert "not-a-url" not in urls


def test_parse_no_namespace_fallback():
    raw = b"""<urlset><url><loc>https://example.com/a</loc></url></urlset>"""
    parser = SitemapParser()
    import asyncio
    urls = asyncio.run(parser._parse_sitemap(raw, "https://example.com/sitemap.xml", 0))
    assert "https://example.com/a" in urls


def test_parse_broken_xml():
    parser = SitemapParser()
    import asyncio
    urls = asyncio.run(parser._parse_sitemap(b"<urlset><url>", "https://example.com/x", 0))
    assert urls == []


def test_is_valid_url():
    assert SitemapParser._is_valid_url("https://example.com/x")
    assert SitemapParser._is_valid_url("http://example.com")
    assert not SitemapParser._is_valid_url("not a url")
    assert not SitemapParser._is_valid_url("ftp://example.com")


def test_recursion_depth_limit():
    parser = SitemapParser()
    import asyncio
    result = asyncio.run(parser._process_sitemap("https://example.com/sitemap.xml", MAX_RECURSION_DEPTH + 1))
    assert result == []

import time

import pytest

from crawler_python.crawler import AsyncCrawler


@pytest.fixture
def crawler():
    return AsyncCrawler(max_concurrent=3, per_domain=2, timeout=5)


def test_should_include_same_domain(crawler: AsyncCrawler):
    assert crawler._should_include(
        "https://example.com/page", "example.com", True, [], []
    )
    assert not crawler._should_include(
        "https://other.com/page", "example.com", True, [], []
    )


def test_should_include_exclude_patterns(crawler: AsyncCrawler):
    assert not crawler._should_include(
        "https://example.com/admin",
        "example.com",
        False,
        [],
        ["*/admin*"],
    )
    assert crawler._should_include(
        "https://example.com/page",
        "example.com",
        False,
        [],
        ["*/admin*"],
    )


def test_should_include_include_patterns(crawler: AsyncCrawler):
    assert crawler._should_include(
        "https://example.com/blog/post",
        "example.com",
        False,
        ["*/blog/*"],
        [],
    )
    assert not crawler._should_include(
        "https://example.com/about",
        "example.com",
        False,
        ["*/blog/*"],
        [],
    )


def test_should_include_no_filters(crawler: AsyncCrawler):
    assert crawler._should_include(
        "https://any.com/page", "example.com", False, [], []
    )


def test_max_depth_stored(crawler: AsyncCrawler):
    assert crawler._max_depth == 3

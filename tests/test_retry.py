import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from crawler_python.errors import (
    CrawlerError,
    ErrorType,
    TransientError,
    PermanentError,
    NetworkError,
    classify_exception,
    classify_http_error,
)
from crawler_python.retry import RetryStrategy


def test_classify_http_429():
    error = classify_http_error(429, "https://a.com")
    assert error.error_type == ErrorType.TRANSIENT


def test_classify_http_503():
    error = classify_http_error(503, "https://a.com")
    assert error.error_type == ErrorType.TRANSIENT


def test_classify_http_404():
    error = classify_http_error(404, "https://a.com")
    assert error.error_type == ErrorType.PERMANENT


def test_classify_http_403():
    error = classify_http_error(403, "https://a.com")
    assert error.error_type == ErrorType.PERMANENT


def test_classify_http_500():
    error = classify_http_error(500, "https://a.com")
    assert error.error_type == ErrorType.TRANSIENT


def test_classify_timeout():
    error = classify_exception(asyncio.TimeoutError(), "https://a.com")
    assert error.error_type == ErrorType.TRANSIENT


@pytest.mark.asyncio
async def test_retry_success_on_second_attempt():
    rs = RetryStrategy(max_retries=2, backoff_factor=1.0, base_delay=0.01)
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TransientError("fail")
        return "ok"

    result = await rs.execute_with_retry(flaky)
    assert result == "ok"
    assert call_count == 2
    assert rs.stats.successful_retries == 1


@pytest.mark.asyncio
async def test_retry_exhausted():
    rs = RetryStrategy(max_retries=2, backoff_factor=1.0, base_delay=0.01)

    async def always_fail():
        raise TransientError("always fail")

    with pytest.raises(TransientError):
        await rs.execute_with_retry(always_fail)
    assert rs.stats.permanent_failures == 1


@pytest.mark.asyncio
async def test_no_retry_on_permanent():
    rs = RetryStrategy(max_retries=3, base_delay=0.01)
    call_count = 0

    async def perm_fail():
        nonlocal call_count
        call_count += 1
        raise PermanentError("not found")

    with pytest.raises(PermanentError):
        await rs.execute_with_retry(perm_fail)
    assert call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff():
    rs = RetryStrategy(
        max_retries=3, backoff_factor=2.0, base_delay=0.05
    )
    delays = []
    original_sleep = asyncio.sleep

    async def mock_sleep(d):
        delays.append(d)

    asyncio.sleep = mock_sleep

    async def fail_then_ok():
        if len(delays) < 3:
            raise TransientError("fail")
        return "ok"

    try:
        result = await rs.execute_with_retry(fail_then_ok)
    finally:
        asyncio.sleep = original_sleep

    assert result == "ok"
    assert len(delays) == 3
    assert delays[0] == 0.05
    assert delays[1] == 0.1
    assert delays[2] == 0.2


@pytest.mark.asyncio
async def test_retry_stats():
    rs = RetryStrategy(max_retries=1, base_delay=0.01)
    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TransientError("fail")
        return "ok"

    await rs.execute_with_retry(flaky)
    summary = rs.stats.get_summary()
    assert summary["total_attempts"] == 2
    assert summary["successful_retries"] == 1
    assert summary["errors_by_type"]["transient"] == 1

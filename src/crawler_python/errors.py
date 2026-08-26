import asyncio
import logging
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    NETWORK = "network"
    PARSE = "parse"


class CrawlerError(Exception):
    def __init__(self, message: str, error_type: ErrorType, url: str = "") -> None:
        super().__init__(message)
        self.error_type = error_type
        self.url = url


class TransientError(CrawlerError):
    def __init__(self, message: str, url: str = "") -> None:
        super().__init__(message, ErrorType.TRANSIENT, url)


class PermanentError(CrawlerError):
    def __init__(self, message: str, url: str = "") -> None:
        super().__init__(message, ErrorType.PERMANENT, url)


class NetworkError(CrawlerError):
    def __init__(self, message: str, url: str = "") -> None:
        super().__init__(message, ErrorType.NETWORK, url)


class ParseError(CrawlerError):
    def __init__(self, message: str, url: str = "") -> None:
        super().__init__(message, ErrorType.PARSE, url)


def classify_http_error(status: int, url: str) -> CrawlerError:
    if status == 429:
        return TransientError(f"Too Many Requests (429): {url}", url)
    if status == 503:
        return TransientError(f"Service Unavailable (503): {url}", url)
    if status == 500:
        return TransientError(f"Server Error (500): {url}", url)
    if status == 404:
        return PermanentError(f"Not Found (404): {url}", url)
    if status == 403:
        return PermanentError(f"Forbidden (403): {url}", url)
    if status == 401:
        return PermanentError(f"Unauthorized (401): {url}", url)
    if status >= 400:
        return PermanentError(f"HTTP {status}: {url}", url)
    return TransientError(f"HTTP {status}: {url}", url)


def classify_exception(exc: Exception, url: str) -> CrawlerError:
    if isinstance(exc, asyncio.TimeoutError):
        return TransientError(f"Timeout: {url}", url)
    if isinstance(exc, aiohttp.ClientResponseError):
        return classify_http_error(exc.status, url)
    if isinstance(exc, aiohttp.ClientError):
        return NetworkError(f"Network error: {exc}: {url}", url)
    if isinstance(exc, CrawlerError):
        return exc
    return CrawlerError(str(exc), ErrorType.TRANSIENT, url)

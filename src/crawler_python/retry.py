import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

from crawler_python.errors import (
    CrawlerError,
    ErrorType,
    classify_exception,
)

logger = logging.getLogger(__name__)


class RetryStats:
    def __init__(self) -> None:
        self.total_attempts: int = 0
        self.successful_retries: int = 0
        self.permanent_failures: int = 0
        self.errors_by_type: dict[str, int] = {}
        self.retry_times: list[float] = []

    def record_attempt(self) -> None:
        self.total_attempts += 1

    def record_success_after_retry(self, elapsed: float) -> None:
        self.successful_retries += 1
        self.retry_times.append(elapsed)

    def record_permanent_failure(self, error: CrawlerError) -> None:
        self.permanent_failures += 1
        key = error.error_type.value
        self.errors_by_type[key] = self.errors_by_type.get(key, 0) + 1

    def record_transient_error(self, error: CrawlerError) -> None:
        key = error.error_type.value
        self.errors_by_type[key] = self.errors_by_type.get(key, 0) + 1

    def get_summary(self) -> dict:
        avg_retry = (
            sum(self.retry_times) / len(self.retry_times)
            if self.retry_times
            else 0.0
        )
        return {
            "total_attempts": self.total_attempts,
            "successful_retries": self.successful_retries,
            "permanent_failures": self.permanent_failures,
            "errors_by_type": dict(self.errors_by_type),
            "avg_retry_time": round(avg_retry, 3),
        }


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_on: list[ErrorType] | None = None,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._retry_on = retry_on or [ErrorType.TRANSIENT, ErrorType.NETWORK]
        self._base_delay = base_delay
        self._max_delay = max_delay
        self.stats = RetryStats()

    def _should_retry(self, error: CrawlerError) -> bool:
        return error.error_type in self._retry_on

    def _get_delay(self, attempt: int) -> float:
        delay = self._base_delay * (self._backoff_factor ** attempt)
        return min(delay, self._max_delay)

    async def execute_with_retry(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        last_error: CrawlerError | None = None
        start_total = time.monotonic()

        for attempt in range(self._max_retries + 1):
            self.stats.record_attempt()
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    elapsed = time.monotonic() - start_total
                    self.stats.record_success_after_retry(elapsed)
                    logger.info(
                        "Успешно после %d попыток (%.2fс): %s",
                        attempt + 1,
                        elapsed,
                        args[0] if args else "?",
                    )
                return result
            except Exception as exc:
                error = classify_exception(exc, args[0] if args else "")
                last_error = error

                if not self._should_retry(error):
                    self.stats.record_permanent_failure(error)
                    logger.error(
                        "Постоянная ошибка (попытка %d/%d): %s",
                        attempt + 1,
                        self._max_retries + 1,
                        error,
                    )
                    raise

                self.stats.record_transient_error(error)

                if attempt < self._max_retries:
                    delay = self._get_delay(attempt)
                    logger.warning(
                        "Временная ошибка (попытка %d/%d), повтор через %.1fс: %s",
                        attempt + 1,
                        self._max_retries + 1,
                        delay,
                        error,
                    )
                    await asyncio.sleep(delay)
                else:
                    self.stats.record_permanent_failure(error)
                    logger.error(
                        "Исчерпаны попытки (попытка %d/%d): %s",
                        attempt + 1,
                        self._max_retries + 1,
                        error,
                    )

        if last_error:
            raise last_error

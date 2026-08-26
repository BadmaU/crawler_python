import logging
import time

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def is_open(self, domain: str) -> bool:
        open_until = self._open_until.get(domain, 0.0)
        if open_until > time.monotonic():
            return True
        if open_until > 0:
            self._open_until.pop(domain, None)
            self._failures.pop(domain, None)
            logger.info("Circuit breaker закрыт для %s", domain)
        return False

    def record_success(self, domain: str) -> None:
        self._failures.pop(domain, None)

    def record_failure(self, domain: str) -> None:
        count = self._failures.get(domain, 0) + 1
        self._failures[domain] = count
        if count >= self._failure_threshold:
            self._open_until[domain] = time.monotonic() + self._recovery_timeout
            logger.warning(
                "Circuit breaker открыт для %s на %.1fс (%d ошибок подряд)",
                domain,
                self._recovery_timeout,
                count,
            )

    def get_state(self, domain: str) -> str:
        if self.is_open(domain):
            return "open"
        if self._failures.get(domain, 0) > 0:
            return "half-open"
        return "closed"

    def get_stats(self) -> dict:
        return {
            "open_circuits": [
                d for d, t in self._open_until.items()
                if t > time.monotonic()
            ],
            "failure_counts": dict(self._failures),
        }

import time

from crawler_python.circuit_breaker import CircuitBreaker


def test_closed_by_default():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    assert cb.is_open("a.com") is False
    assert cb.get_state("a.com") == "closed"


def test_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    for _ in range(3):
        cb.record_failure("a.com")
    assert cb.is_open("a.com") is True
    assert cb.get_state("a.com") == "open"


def test_recovers_after_timeout():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
    cb.record_failure("a.com")
    cb.record_failure("a.com")
    assert cb.is_open("a.com") is True
    time.sleep(0.15)
    assert cb.is_open("a.com") is False
    assert cb.get_state("a.com") == "closed"


def test_success_resets_failures():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    cb.record_failure("a.com")
    cb.record_failure("a.com")
    cb.record_success("a.com")
    assert cb.is_open("a.com") is False
    assert cb.get_state("a.com") == "closed"


def test_half_open_state():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    cb.record_failure("a.com")
    assert cb.get_state("a.com") == "half-open"


def test_separate_domains():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    cb.record_failure("a.com")
    cb.record_failure("a.com")
    assert cb.is_open("a.com") is True
    assert cb.is_open("b.com") is False


def test_get_stats():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
    cb.record_failure("a.com")
    stats = cb.get_stats()
    assert "a.com" in stats["failure_counts"]
    assert stats["failure_counts"]["a.com"] == 1

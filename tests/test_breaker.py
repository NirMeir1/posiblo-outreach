import pytest

from outreach.breaker import CircuitBreaker


@pytest.mark.parametrize("n", [1, 2, 5, 10])
def test_trips_exactly_at_threshold(n: int) -> None:
    b = CircuitBreaker(n)
    for _ in range(n - 1):
        assert b.record_failure() is False
    assert b.tripped is False and b.consecutive_failures == n - 1  # N-1: still closed
    assert b.record_failure() is True                              # N: tripped
    assert b.tripped is True


def test_success_resets_the_consecutive_count() -> None:
    b = CircuitBreaker(3)
    b.record_failure()
    b.record_failure()
    b.record_success()
    assert b.consecutive_failures == 0
    b.record_failure()
    b.record_failure()
    assert b.tripped is False
    assert b.record_failure() is True


def test_trip_is_sticky() -> None:
    b = CircuitBreaker(2)
    b.record_failure()
    b.record_failure()
    b.record_success()
    assert b.tripped is True


def test_invalid_threshold() -> None:
    with pytest.raises(ValueError):
        CircuitBreaker(0)

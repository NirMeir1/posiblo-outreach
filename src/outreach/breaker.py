"""Circuit breaker: trips after `threshold` consecutive failures and stays tripped."""

from __future__ import annotations


class CircuitBreaker:
    def __init__(self, threshold: int):
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        self.threshold = threshold
        self.consecutive_failures = 0
        self.tripped = False

    def record_failure(self) -> bool:
        """Count one failure. Returns True if the breaker is (now) tripped."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.tripped = True
        return self.tripped

    def record_success(self) -> None:
        """A success resets the consecutive count. It does not un-trip a tripped breaker."""
        if not self.tripped:
            self.consecutive_failures = 0

    def state(self) -> dict[str, object]:
        return {"threshold": self.threshold, "consecutive_failures": self.consecutive_failures,
                "tripped": self.tripped}

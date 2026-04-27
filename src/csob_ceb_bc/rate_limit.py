from __future__ import annotations

import threading
import time


class TokenBucketRateLimiter:
    """Thread-safe token bucket for SOAP call budgeting."""

    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_per_second = refill_per_second
        self._last_refill = time.monotonic()
        self._consumed = 0
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_per_second)
            self._last_refill = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                self._consumed += tokens
                return True
            return False

    def consumed(self) -> int:
        with self._lock:
            return self._consumed

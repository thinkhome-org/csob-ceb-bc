"""Simple in-memory metrics collector for observability.

Collects counters and histograms for SOAP calls, REST transfers,
upload stages, and certificate health.  Thread-safe via locking.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Counter:
    value: int = 0


@dataclass
class _Histogram:
    values: list[float] = field(default_factory=list)


class MetricsCollector:
    """In-memory metrics store with locking.

    All methods are thread-safe.  Intended for short-lived batch jobs
    or embedded SDK usage.  For production scale, export to Prometheus
    or StatsD instead.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, _Counter] = defaultdict(_Counter)
        self._histograms: dict[str, _Histogram] = defaultdict(_Histogram)
        self._gauges: dict[str, float] = {}

    def inc(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name].value += value

    def record(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms[name].values.append(value)

    def gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def counter_value(self, name: str) -> int:
        with self._lock:
            return self._counters[name].value

    def histogram_values(self, name: str) -> list[float]:
        with self._lock:
            return list(self._histograms[name].values)

    def gauge_value(self, name: str) -> float | None:
        with self._lock:
            return self._gauges.get(name)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": {k: v.value for k, v in self._counters.items()},
                "histograms": {k: list(v.values) for k, v in self._histograms.items()},
                "gauges": dict(self._gauges),
            }

    def clear(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()


# Convenience timing context manager
class timed:
    """Context manager that records elapsed seconds to a histogram."""

    def __init__(self, collector: MetricsCollector, name: str) -> None:
        self.collector = collector
        self.name = name

    def __enter__(self) -> timed:
        self._start = time.monotonic()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        elapsed = time.monotonic() - self._start
        self.collector.record(self.name, elapsed)

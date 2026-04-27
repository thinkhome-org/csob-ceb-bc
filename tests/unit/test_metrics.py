"""Tests for MetricsCollector and timed context manager."""

import threading
import time

from csob_ceb_bc.metrics import MetricsCollector, timed


def test_counter_increment():
    m = MetricsCollector()
    m.inc("soap_calls")
    m.inc("soap_calls", 2)
    assert m.counter_value("soap_calls") == 3


def test_histogram_record():
    m = MetricsCollector()
    m.record("download_latency", 0.123)
    m.record("download_latency", 0.456)
    assert m.histogram_values("download_latency") == [0.123, 0.456]


def test_gauge():
    m = MetricsCollector()
    m.gauge("cert_days_left", 14.0)
    assert m.gauge_value("cert_days_left") == 14.0


def test_snapshot():
    m = MetricsCollector()
    m.inc("uploads", 5)
    m.record("latency", 1.0)
    m.gauge("queue_depth", 3.0)
    snap = m.snapshot()
    assert snap["counters"]["uploads"] == 5
    assert snap["histograms"]["latency"] == [1.0]
    assert snap["gauges"]["queue_depth"] == 3.0


def test_clear():
    m = MetricsCollector()
    m.inc("x")
    m.clear()
    assert m.counter_value("x") == 0


def test_thread_safety():
    m = MetricsCollector()
    threads = []
    for _ in range(10):
        t = threading.Thread(target=lambda: m.inc("counter", 100))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    assert m.counter_value("counter") == 1000


def test_timed_context_manager():
    m = MetricsCollector()
    with timed(m, "operation"):
        time.sleep(0.01)
    values = m.histogram_values("operation")
    assert len(values) == 1
    assert values[0] >= 0.01

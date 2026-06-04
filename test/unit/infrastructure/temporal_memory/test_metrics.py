"""Tests for temporal memory Prometheus metrics (TM-068)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aiecs.infrastructure.temporal_memory import metrics as metrics_mod


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    metrics_mod.reset_temporal_memory_metrics_for_tests()
    yield
    metrics_mod.reset_temporal_memory_metrics_for_tests()


def test_metrics_no_op_when_prometheus_unavailable() -> None:
    with patch.object(metrics_mod.TemporalMemoryMetrics, "_init_prometheus", return_value=None):
        m = metrics_mod.TemporalMemoryMetrics()
    m.available = False
    m.record_ingest("graphiti", ok=True)
    m.record_search_duration("graphiti", cache="hit", duration_seconds=0.01)
    m.set_backend_active("graphiti")
    m.set_plugin_enabled(True)
    m.record_search_cache(hit=True)
    m.set_ingest_queue_depth(3)


def test_metrics_record_ingest_and_search_when_prometheus_available() -> None:
    mock_counter = MagicMock()
    mock_counter.labels.return_value = mock_counter
    mock_gauge = MagicMock()
    mock_gauge.labels.return_value = mock_gauge
    mock_histogram = MagicMock()
    mock_histogram.labels.return_value = mock_histogram

    with patch.dict(
        "sys.modules",
        {
            "prometheus_client": MagicMock(
                Counter=lambda *a, **k: mock_counter,
                Gauge=lambda *a, **k: mock_gauge,
                Histogram=lambda *a, **k: mock_histogram,
            )
        },
    ):
        m = metrics_mod.TemporalMemoryMetrics()
        assert m.available is True

    m.record_ingest("noop", ok=False)
    mock_counter.labels.assert_called()
    mock_counter.inc.assert_called()

    m.record_search_duration("graphiti", cache="miss", duration_seconds=0.05)
    mock_histogram.labels.assert_called_with(backend="graphiti", cache="miss")
    mock_histogram.observe.assert_called_with(0.05)

    m.set_backend_active("graphiti")
    m.set_plugin_enabled(True)
    m.record_search_cache(hit=True)
    m.set_ingest_queue_depth(2)


def test_get_temporal_memory_metrics_singleton() -> None:
    a = metrics_mod.get_temporal_memory_metrics()
    b = metrics_mod.get_temporal_memory_metrics()
    assert a is b


def test_observe_search_sets_cache_label_in_context() -> None:
    mock_histogram = MagicMock()
    mock_histogram.labels.return_value = mock_histogram

    with patch.dict(
        "sys.modules",
        {
            "prometheus_client": MagicMock(
                Counter=lambda *a, **k: MagicMock(),
                Gauge=lambda *a, **k: MagicMock(),
                Histogram=lambda *a, **k: mock_histogram,
            )
        },
    ):
        m = metrics_mod.TemporalMemoryMetrics()

    with m.observe_search("graphiti") as obs:
        obs.set_cache("hit")

    mock_histogram.labels.assert_called_with(backend="graphiti", cache="hit")
    mock_histogram.observe.assert_called_once()
    assert mock_histogram.observe.call_args.args[0] >= 0

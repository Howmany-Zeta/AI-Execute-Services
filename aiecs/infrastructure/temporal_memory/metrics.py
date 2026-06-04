# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Prometheus metrics for L1 temporal memory (TM-068). No-op when prometheus_client is unavailable."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Literal

logger = logging.getLogger(__name__)

_TM_BACKENDS = ("none", "graphiti", "postgres")
CacheLabel = Literal["hit", "miss", "off"]

# prometheus_client Gauge/Counter/Histogram when installed, else _NoOpLabeled
_MetricHandle = Any


class _NoOpLabeled:
    def labels(self, **_kwargs: str) -> _NoOpLabeled:
        return self

    def inc(self, amount: float = 1) -> None:
        _ = amount

    def observe(self, value: float) -> None:
        _ = value

    def set(self, value: float) -> None:
        _ = value


class TemporalMemoryMetrics:
    """Lazy Prometheus metric registry; safe to call when client is missing."""

    def __init__(self) -> None:
        self.available = False
        self._backend_active: _MetricHandle = _NoOpLabeled()
        self._ingest_total: _MetricHandle = _NoOpLabeled()
        self._search_duration: _MetricHandle = _NoOpLabeled()
        self._ingest_queue_depth: _MetricHandle = _NoOpLabeled()
        self._plugin_enabled: _MetricHandle = _NoOpLabeled()
        self._search_cache_hits: _MetricHandle = _NoOpLabeled()
        self._search_cache_misses: _MetricHandle = _NoOpLabeled()
        self._init_prometheus()

    def _init_prometheus(self) -> None:
        try:
            from prometheus_client import Counter, Gauge, Histogram
        except ImportError:
            logger.debug("prometheus_client not installed; temporal memory metrics disabled")
            return

        try:
            self._backend_active = Gauge(
                "tm_backend_active",
                "Whether a temporal memory backend is active (1=active for label)",
                ["backend"],
            )
            self._ingest_total = Counter(
                "tm_ingest_total",
                "Temporal memory ingest operations",
                ["backend", "status"],
            )
            self._search_duration = Histogram(
                "tm_search_duration_seconds",
                "Temporal memory search latency",
                ["backend", "cache"],
            )
            self._ingest_queue_depth = Gauge(
                "tm_ingest_queue_depth",
                "Temporal memory async ingest queue depth",
            )
            self._plugin_enabled = Gauge(
                "tm_plugin_enabled",
                "Temporal memory plugin enabled on last init/shutdown (0/1)",
            )
            self._search_cache_hits = Counter(
                "tm_search_cache_hits_total",
                "Temporal memory search cache hits",
            )
            self._search_cache_misses = Counter(
                "tm_search_cache_misses_total",
                "Temporal memory search cache misses",
            )
            self.available = True
        except Exception as exc:
            logger.warning("Failed to register temporal memory metrics: %s", exc)

    def set_backend_active(self, active_backend: str) -> None:
        active = active_backend if active_backend in _TM_BACKENDS else "none"
        for backend in _TM_BACKENDS:
            self._backend_active.labels(backend=backend).set(1.0 if backend == active else 0.0)

    def set_plugin_enabled(self, enabled: bool) -> None:
        self._plugin_enabled.set(1.0 if enabled else 0.0)

    def record_ingest(self, backend: str, *, ok: bool) -> None:
        status = "ok" if ok else "error"
        self._ingest_total.labels(backend=backend, status=status).inc()

    def record_search_cache(self, *, hit: bool) -> None:
        if hit:
            self._search_cache_hits.inc()
        else:
            self._search_cache_misses.inc()

    def set_ingest_queue_depth(self, depth: int) -> None:
        self._ingest_queue_depth.set(float(max(0, depth)))

    def record_search_duration(
        self,
        backend: str,
        *,
        cache: CacheLabel,
        duration_seconds: float,
    ) -> None:
        """Record a completed search latency (used by :meth:`observe_search` and unit tests)."""
        self._search_duration.labels(backend=backend, cache=cache).observe(duration_seconds)

    @contextmanager
    def observe_search(
        self,
        backend: str,
        *,
        cache: CacheLabel = "miss",
    ) -> Generator[_SearchObserve, None, None]:
        """
        Time a search and record ``tm_search_duration_seconds``.

        Yielded helper supports a result-dependent cache label::

            with metrics.observe_search(backend) as obs:
                facts, hit = await ...
                obs.set_cache("hit" if hit else "miss")
        """
        state: dict[str, CacheLabel] = {"cache": cache}
        observer = _SearchObserve(state)
        start = time.perf_counter()
        try:
            yield observer
        finally:
            self.record_search_duration(
                backend,
                cache=state["cache"],
                duration_seconds=time.perf_counter() - start,
            )


class _SearchObserve:
    """Mutable cache label for :meth:`TemporalMemoryMetrics.observe_search`."""

    def __init__(self, state: dict[str, CacheLabel]) -> None:
        self._state = state

    def set_cache(self, cache: CacheLabel) -> None:
        self._state["cache"] = cache


_metrics: TemporalMemoryMetrics | None = None


def get_temporal_memory_metrics() -> TemporalMemoryMetrics:
    global _metrics
    if _metrics is None:
        _metrics = TemporalMemoryMetrics()
    return _metrics


def reset_temporal_memory_metrics_for_tests() -> None:
    """Reset singleton (unit tests only)."""
    global _metrics
    _metrics = None

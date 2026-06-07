# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Prometheus metrics for DAWP runs (D3-01). No-op when prometheus_client is unavailable."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Generator, Literal

logger = logging.getLogger(__name__)

TriggerLabel = Literal["config", "tool"]
SourceLabel = Literal["static", "dynamic"]

_MetricHandle = Any


class _NoOpLabeled:
    def labels(self, **_kwargs: str) -> _NoOpLabeled:
        return self

    def inc(self, amount: float = 1) -> None:
        _ = amount

    def observe(self, value: float) -> None:
        _ = value


class DawpMetrics:
    """Lazy Prometheus registry for DAWP observability (D3-01)."""

    def __init__(self) -> None:
        self.available = False
        self._run_total: _MetricHandle = _NoOpLabeled()
        self._run_failed_total: _MetricHandle = _NoOpLabeled()
        self._step_duration: _MetricHandle = _NoOpLabeled()
        self._init_prometheus()

    def _init_prometheus(self) -> None:
        try:
            from prometheus_client import Counter, Histogram
        except ImportError:
            logger.debug("prometheus_client not installed; DAWP metrics disabled")
            return

        try:
            self._run_total = Counter(
                "dawp_run_total",
                "Total DAWP workflow runs completed",
                ["workflow_id", "trigger", "workflow_source"],
            )
            self._run_failed_total = Counter(
                "dawp_run_failed_total",
                "DAWP workflow runs that did not complete successfully",
                ["workflow_id", "trigger", "workflow_source"],
            )
            self._step_duration = Histogram(
                "dawp_step_duration_seconds",
                "DAWP prompt-chain step duration in seconds",
                ["workflow_id", "trigger", "workflow_source"],
            )
            self.available = True
        except Exception as exc:
            logger.warning("Failed to register DAWP metrics: %s", exc)

    def record_run(
        self,
        *,
        workflow_id: str,
        trigger: TriggerLabel,
        workflow_source: SourceLabel,
        success: bool,
    ) -> None:
        """Record a completed DAWP run."""
        labels = {
            "workflow_id": workflow_id or "unknown",
            "trigger": trigger,
            "workflow_source": workflow_source,
        }
        self._run_total.labels(**labels).inc()
        if not success:
            self._run_failed_total.labels(**labels).inc()

    def record_step_duration(
        self,
        *,
        workflow_id: str,
        trigger: TriggerLabel,
        workflow_source: SourceLabel,
        duration_seconds: float,
    ) -> None:
        """Record elapsed time for one DAWP step."""
        self._step_duration.labels(
            workflow_id=workflow_id or "unknown",
            trigger=trigger,
            workflow_source=workflow_source,
        ).observe(duration_seconds)

    @contextmanager
    def observe_step_duration(
        self,
        *,
        workflow_id: str,
        trigger: TriggerLabel,
        workflow_source: SourceLabel,
    ) -> Generator[None, None, None]:
        """Time a DAWP step and record ``dawp_step_duration_seconds``."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self.record_step_duration(
                workflow_id=workflow_id,
                trigger=trigger,
                workflow_source=workflow_source,
                duration_seconds=time.perf_counter() - start,
            )


_metrics: DawpMetrics | None = None


def get_dawp_metrics() -> DawpMetrics:
    global _metrics
    if _metrics is None:
        _metrics = DawpMetrics()
    return _metrics


def reset_dawp_metrics_for_tests() -> None:
    """Reset singleton (unit tests only)."""
    global _metrics
    _metrics = None


def metrics_labels_from_plugin_state(plugin_state: dict[str, Any]) -> dict[str, str]:
    """Read run-level label dict stored by ``HybridAgent._drain_pending_dawp_runs``."""
    raw = plugin_state.get("dawp._metrics_run")
    if isinstance(raw, dict):
        return {
            "workflow_id": str(raw.get("workflow_id") or "unknown"),
            "trigger": str(raw.get("trigger") or "config"),
            "workflow_source": str(raw.get("workflow_source") or "static"),
        }
    return {"workflow_id": "unknown", "trigger": "config", "workflow_source": "static"}

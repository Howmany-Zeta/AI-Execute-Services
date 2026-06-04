"""
Temporal memory load / latency benchmarks (TM-076).

Default CI: skipped unless ``TM_LOAD_TEST=1``.
Optional FalkorDB: ``@pytest.mark.graphiti`` + ``TM_FALKORDB_URL``.
"""

from __future__ import annotations

import os
import statistics
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    TemporalFact,
)

_RUN_LOAD = os.environ.get("TM_LOAD_TEST", "").strip().lower() in ("1", "true", "yes")

pytestmark = [
    pytest.mark.performance,
    pytest.mark.slow,
    pytest.mark.skipif(not _RUN_LOAD, reason="Set TM_LOAD_TEST=1 to run temporal memory load tests"),
]


class _FastMockStore:
    store_id = "mock"

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        return IngestEpisodeResult(episode_id="ep-load", group_id=request.group_id)

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        _ = request, job_id
        return "job"

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: Any = None,
    ) -> list[TemporalFact]:
        _ = query, group_ids, limit, valid_at, filters
        return [
            TemporalFact(
                fact_id="f-load",
                text="load test fact",
                group_id="aiecs:load:session",
                valid_at=datetime.now(timezone.utc),
            )
        ]

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"ready": True}


def _make_ctx() -> AgentPluginContext:
    agent = MagicMock()
    agent.agent_id = "load-agent"
    return AgentPluginContext(
        agent=agent,
        task={"task_id": "load-1", "description": "load test query"},
        context={"session_id": "load-session"},
        task_description="load test query",
    )


def _percentile(samples: list[float], pct: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


@pytest.mark.asyncio
async def test_ingest_throughput_mock_store() -> None:
    """Record ingest QPS and failure rate on in-process mock store."""
    engine = TemporalMemoryEngine(
        _FastMockStore(),
        settings=Settings(TM_INGEST_ASYNC=False, TM_SEARCH_CACHE_ENABLED=False),
    )
    ctx = _make_ctx()
    iterations = 100
    failures = 0
    started = time.perf_counter()
    for _ in range(iterations):
        result = await engine.ingest_from_task(ctx, {"final_response": "ok"})
        if result is None:
            failures += 1
    elapsed = time.perf_counter() - started
    qps = iterations / elapsed if elapsed > 0 else 0.0
    failure_rate = failures / iterations

    assert failure_rate < 0.01, f"failure rate {failure_rate:.2%} exceeds 1%"
    assert qps > 10, f"unexpectedly low mock ingest QPS: {qps:.1f}"

    pytest.ingest_qps = qps  # type: ignore[attr-defined]
    pytest.ingest_failure_rate = failure_rate  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_search_p95_cache_on_vs_off_mock() -> None:
    """Compare search p95 with TTL cache enabled vs disabled (mock store)."""
    task = {"description": "load test query"}
    group_ids = ["aiecs:load-agent:load-session"]
    samples_off: list[float] = []
    samples_on_warm: list[float] = []

    engine_off = TemporalMemoryEngine(
        _FastMockStore(),
        settings=Settings(TM_SEARCH_CACHE_ENABLED=False),
    )
    for _ in range(30):
        t0 = time.perf_counter()
        await engine_off.search_for_task(task, group_ids)
        samples_off.append(time.perf_counter() - t0)

    engine_on = TemporalMemoryEngine(
        _FastMockStore(),
        settings=Settings(
            TM_SEARCH_CACHE_ENABLED=True,
            TM_SEARCH_CACHE_TTL_SECONDS=60,
            TM_SEARCH_CACHE_MAX_SIZE=256,
        ),
    )
    await engine_on.search_for_task(task, group_ids)
    for _ in range(30):
        t0 = time.perf_counter()
        await engine_on.search_for_task(task, group_ids)
        samples_on_warm.append(time.perf_counter() - t0)

    p95_off_ms = _percentile(samples_off, 95) * 1000
    p95_on_ms = _percentile(samples_on_warm, 95) * 1000

    pytest.search_p95_cache_off_ms = p95_off_ms  # type: ignore[attr-defined]
    pytest.search_p95_cache_on_ms = p95_on_ms  # type: ignore[attr-defined]

    assert p95_on_ms < 100.0, f"warm cache p95 {p95_on_ms:.2f}ms exceeds 100ms target on mock store"


@pytest.mark.graphiti
@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("TM_FALKORDB_URL", "").strip(),
    reason="Set TM_FALKORDB_URL for optional FalkorDB load sample",
)
async def test_ingest_sample_on_falkordb() -> None:
    """Optional: single ingest on real Graphiti/FalkorDB (not a CI gate)."""
    pytest.importorskip("graphiti_core")
    from aiecs.infrastructure.temporal_memory.graphiti.store import GraphitiTemporalMemoryStore

    settings = Settings(
        TM_ENABLED=True,
        TM_BACKEND="graphiti",
        TM_GRAPH_BACKEND="falkordb",
        TM_FALKORDB_URL=os.environ["TM_FALKORDB_URL"],
        TM_INGEST_ASYNC=False,
    )
    store = GraphitiTemporalMemoryStore(settings=settings)
    await store.initialize()
    try:
        engine = TemporalMemoryEngine(store, settings=settings)
        ctx = _make_ctx()
        result = await engine.ingest_from_task(ctx, {"final_response": "load sample ok"})
        assert result is not None
    finally:
        await store.close()

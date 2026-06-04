"""Tests for TemporalMemoryEngine."""

from __future__ import annotations

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


class _RecordingStore:
    def __init__(self) -> None:
        self.ingest_calls: list[IngestEpisodeRequest] = []
        self.search_calls: list[tuple[str, list[str]]] = []
        self.raise_on_ingest = False

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        if self.raise_on_ingest:
            raise RuntimeError("ingest failed")
        self.ingest_calls.append(request)
        return IngestEpisodeResult(
            episode_id="ep-1",
            group_id=request.group_id,
            facts_extracted=1,
        )

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        _ = job_id
        await self.ingest_episode(request)
        return "job-1"

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: Any = None,
    ) -> list[TemporalFact]:
        _ = limit, valid_at, filters
        self.search_calls.append((query, group_ids))
        return [
            TemporalFact(
                fact_id="f1",
                text="weather is sunny",
                group_id=group_ids[0],
                valid_at=datetime.now(timezone.utc),
            )
        ]

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"backend": "mock", "ready": True}


def _make_ctx(
    *,
    task_description: str = "What is the weather?",
    session_id: str = "sess-1",
    tenant_id: str | None = None,
) -> AgentPluginContext:
    agent = MagicMock()
    agent.agent_id = "agent-99"
    context: dict[str, Any] = {"session_id": session_id}
    if tenant_id:
        context["tenant_id"] = tenant_id
    return AgentPluginContext(
        agent=agent,
        task={"task_id": "t-1", "description": task_description},
        context=context,
        task_description=task_description,
    )


@pytest.mark.asyncio
async def test_ingest_from_task_calls_store() -> None:
    store = _RecordingStore()
    settings = Settings(TM_INGEST_ASYNC=False)
    engine = TemporalMemoryEngine(store, settings=settings)
    ctx = _make_ctx()
    result = await engine.ingest_from_task(ctx, {"final_response": "It is sunny."})

    assert result is not None
    assert len(store.ingest_calls) == 1
    req = store.ingest_calls[0]
    assert "user: What is the weather?" in req.body
    assert "assistant: It is sunny." in req.body
    assert req.group_id == "aiecs:agent-99:sess-1"


@pytest.mark.asyncio
async def test_ingest_from_task_swallows_store_errors() -> None:
    store = _RecordingStore()
    store.raise_on_ingest = True
    engine = TemporalMemoryEngine(store, settings=Settings(TM_INGEST_ASYNC=False))
    ctx = _make_ctx()

    out = await engine.ingest_from_task(ctx, {"output": "ok"})
    assert out is None


@pytest.mark.asyncio
async def test_search_for_task_delegates_to_store() -> None:
    store = _RecordingStore()
    engine = TemporalMemoryEngine(store, settings=Settings(TM_SEARCH_LIMIT=5))
    facts = await engine.search_for_task(
        {"description": "weather today"},
        ["aiecs:agent-99:sess-1"],
    )

    assert len(facts) == 1
    assert store.search_calls == [("weather today", ["aiecs:agent-99:sess-1"])]


@pytest.mark.asyncio
async def test_search_primary_group_only_passes_single_group_id() -> None:
    store = _RecordingStore()
    settings = Settings(TM_SEARCH_PRIMARY_GROUP_ONLY=True)
    engine = TemporalMemoryEngine(store, settings=settings)
    all_ids = ["aiecs:agent-99:sess-1", "aiecs:tenant:tenant-a"]
    await engine.search_for_task({"description": "weather"}, all_ids)

    assert store.search_calls == [("weather", ["aiecs:agent-99:sess-1"])]


@pytest.mark.asyncio
async def test_resolve_group_ids_includes_tenant() -> None:
    store = _RecordingStore()
    engine = TemporalMemoryEngine(store)
    ctx = _make_ctx(tenant_id="tenant-a")
    ids = engine.resolve_group_ids(ctx.agent, ctx)
    assert ids == ["aiecs:agent-99:sess-1", "aiecs:tenant:tenant-a"]


@pytest.mark.asyncio
async def test_ingest_uses_sync_episode_regardless_of_tm_ingest_async_setting() -> None:
    """TM_INGEST_ASYNC is enforced by the plugin ingest queue, not the engine."""
    store = _RecordingStore()
    engine = TemporalMemoryEngine(store, settings=Settings(TM_INGEST_ASYNC=True))
    ctx = _make_ctx()
    result = await engine.ingest_from_task(ctx, {"final_response": "done"})

    assert result is not None
    assert result.episode_id == "ep-1"
    assert len(store.ingest_calls) == 1

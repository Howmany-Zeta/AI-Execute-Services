"""Tenant-scoped group_id isolation and search/ingest selection (TM-066)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.group_id import (
    build_group_ids,
    select_ingest_group_ids,
    select_search_group_ids,
)
from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    TemporalFact,
)


class _TenantFactStore:
    """Returns facts only for group_ids requested in search."""

    def __init__(self) -> None:
        self.search_group_ids: list[str] = []
        self._facts: dict[str, list[TemporalFact]] = {
            "aiecs_agent-1_sess": [
                TemporalFact(
                    fact_id="sess-fact",
                    text="session scoped",
                    group_id="aiecs_agent-1_sess",
                    valid_at=datetime.now(timezone.utc),
                )
            ],
            "aiecs_tenant_tenant-a": [
                TemporalFact(
                    fact_id="tenant-a-fact",
                    text="tenant A secret",
                    group_id="aiecs_tenant_tenant-a",
                    valid_at=datetime.now(timezone.utc),
                )
            ],
            "aiecs_tenant_tenant-b": [
                TemporalFact(
                    fact_id="tenant-b-fact",
                    text="tenant B secret",
                    group_id="aiecs_tenant_tenant-b",
                    valid_at=datetime.now(timezone.utc),
                )
            ],
        }

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        return IngestEpisodeResult(episode_id="ep", group_id=request.group_id)

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
        _ = query, limit, valid_at, filters
        self.search_group_ids = list(group_ids)
        out: list[TemporalFact] = []
        for gid in group_ids:
            out.extend(self._facts.get(gid, []))
        return out

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"backend": "mock", "ready": True}


def _ctx(*, tenant_id: str) -> AgentPluginContext:
    from unittest.mock import MagicMock

    agent = MagicMock()
    agent.agent_id = "agent-1"
    return AgentPluginContext(
        agent=agent,
        task={"task_id": "t1", "description": "secret"},
        context={"session_id": "sess", "tenant_id": tenant_id},
        task_description="secret",
    )


@pytest.mark.asyncio
async def test_tenant_b_search_does_not_see_tenant_a_facts() -> None:
    store = _TenantFactStore()
    engine = TemporalMemoryEngine(store, settings=Settings())
    ctx_a = _ctx(tenant_id="tenant-a")
    ctx_b = _ctx(tenant_id="tenant-b")

    ids_a = engine.resolve_group_ids(ctx_a.agent, ctx_a)
    ids_b = engine.resolve_group_ids(ctx_b.agent, ctx_b)
    assert "aiecs_tenant_tenant-a" in ids_a
    assert "aiecs_tenant_tenant-b" in ids_b

    facts_a = await engine.search_for_task(ctx_a.task, ids_a)
    facts_b = await engine.search_for_task(ctx_b.task, ids_b)

    texts_a = {f.text for f in facts_a}
    texts_b = {f.text for f in facts_b}
    assert "tenant A secret" in texts_a
    assert "tenant A secret" not in texts_b
    assert "tenant B secret" in texts_b
    assert "tenant B secret" not in texts_a


def test_select_search_primary_group_only_omits_tenant_scope() -> None:
    settings = Settings(TM_SEARCH_PRIMARY_GROUP_ONLY=True)
    ids = build_group_ids("agent-1", "sess", "tenant-a", settings=settings)
    search_ids = select_search_group_ids(ids, settings=settings)
    assert search_ids == ["aiecs_agent-1_sess"]


def test_select_ingest_all_group_ids_duplicates_episode_targets() -> None:
    settings = Settings(TM_INGEST_ALL_GROUP_IDS=True)
    ids = build_group_ids("agent-1", "sess", "tenant-a", settings=settings)
    ingest_ids = select_ingest_group_ids(ids, settings=settings)
    assert ingest_ids == ids


@pytest.mark.asyncio
async def test_ingest_all_group_ids_writes_each_scope() -> None:
    class _IngestRecorder(_TenantFactStore):
        def __init__(self) -> None:
            super().__init__()
            self.ingest_group_ids: list[str] = []

        async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
            self.ingest_group_ids.append(request.group_id)
            return IngestEpisodeResult(episode_id="ep", group_id=request.group_id)

    store = _IngestRecorder()
    settings = Settings(TM_INGEST_ALL_GROUP_IDS=True, TM_INGEST_ASYNC=False)
    engine = TemporalMemoryEngine(store, settings=settings)
    ctx = _ctx(tenant_id="tenant-a")
    await engine.ingest_from_task(ctx, {"final_response": "ok"})

    assert store.ingest_group_ids == [
        "aiecs_agent-1_sess",
        "aiecs_tenant_tenant-a",
    ]

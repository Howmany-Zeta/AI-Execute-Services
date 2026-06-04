"""Tests for UnifiedMemoryRetriever (TM-071)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from aiecs.domain.memory.unified_retriever import merge_and_rerank, retrieve_for_task
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import TemporalFact
from aiecs.infrastructure.knowledge.noop_graph_store import NoOpGraphStore


class _TemporalStore:
    store_id = "mock"

    def __init__(self, facts: list[TemporalFact]) -> None:
        self._facts = facts

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: Any) -> Any:
        _ = request
        return None

    async def ingest_episode_async(self, request: Any, *, job_id: str | None = None) -> str:
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
        return self._facts

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"ready": True}


class _GraphStore:
    store_id = "mock_kg"

    def __init__(self, entities: list[Any]) -> None:
        self._entities = entities

    async def search(self, task: dict[str, Any], *, limit: int = 10) -> list[Any]:
        _ = task
        return self._entities[:limit]


@pytest.mark.asyncio
async def test_l1_only_without_graph_store() -> None:
    facts = [
        TemporalFact(
            fact_id="f1",
            text="sunny today",
            group_id="g1",
            valid_at=datetime.now(timezone.utc),
        )
    ]
    engine = TemporalMemoryEngine(_TemporalStore(facts))
    ctx = await retrieve_for_task(
        temporal_engine=engine,
        graph_store=None,
        task={"description": "weather"},
        group_ids=["g1"],
        limit=5,
    )

    assert len(ctx.temporal_facts) == 1
    assert ctx.knowledge_entities == []
    assert len(ctx.merged_items) == 1
    assert ctx.merged_items[0].source == "temporal"
    assert ctx.merged_items[0].score == 1.0


@pytest.mark.asyncio
async def test_l1_plus_l2_mock_entities() -> None:
    facts = [
        TemporalFact(
            fact_id="f1",
            text="temporal fact",
            group_id="g1",
            confidence=0.9,
            valid_at=datetime.now(timezone.utc),
        )
    ]
    entities = [
        SimpleNamespace(
            entity_type="Person",
            id="ent-1",
            properties={"name": "Ada"},
        )
    ]
    engine = TemporalMemoryEngine(_TemporalStore(facts))
    ctx = await retrieve_for_task(
        temporal_engine=engine,
        graph_store=_GraphStore(entities),
        task={"description": "who is Ada"},
        group_ids=["g1"],
        limit=10,
    )

    assert len(ctx.temporal_facts) == 1
    assert len(ctx.knowledge_entities) == 1
    assert len(ctx.merged_items) == 2
    sources = {item.source for item in ctx.merged_items}
    assert sources == {"temporal", "knowledge"}
    assert ctx.merged_items[0].source == "temporal"
    assert ctx.merged_items[0].score == 0.9
    assert ctx.merged_items[1].source == "knowledge"
    assert ctx.merged_items[1].score == 0.8


@pytest.mark.asyncio
async def test_l2_noop_returns_temporal_only() -> None:
    facts = [
        TemporalFact(
            fact_id="f1",
            text="only temporal",
            group_id="g1",
            valid_at=datetime.now(timezone.utc),
        )
    ]
    engine = TemporalMemoryEngine(_TemporalStore(facts))
    ctx = await retrieve_for_task(
        temporal_engine=engine,
        graph_store=NoOpGraphStore(),
        task={"description": "query"},
        group_ids=["g1"],
    )

    assert len(ctx.temporal_facts) == 1
    assert ctx.knowledge_entities == []
    assert all(item.source == "temporal" for item in ctx.merged_items)


def test_merge_tie_break_temporal_before_knowledge() -> None:
    facts = [
        TemporalFact(
            fact_id="f1",
            text="temporal tie",
            group_id="g1",
            confidence=0.8,
            valid_at=datetime.now(timezone.utc),
        )
    ]
    entities = [
        SimpleNamespace(entity_type="Doc", id="d1", properties={}),
    ]
    merged = merge_and_rerank(facts, entities, limit=10)

    assert len(merged) == 2
    assert merged[0].source == "temporal"
    assert merged[1].source == "knowledge"
    assert merged[0].score == 0.8
    assert merged[1].score == 0.8


def test_merge_truncates_to_limit() -> None:
    facts = [
        TemporalFact(
            fact_id=f"f{i}",
            text=f"t{i}",
            group_id="g",
            valid_at=datetime.now(timezone.utc),
        )
        for i in range(5)
    ]
    entities = [SimpleNamespace(entity_type="E", id=f"e{i}", properties={}) for i in range(5)]
    merged = merge_and_rerank(facts, entities, limit=3)
    assert len(merged) == 3


@pytest.mark.asyncio
async def test_null_temporal_engine_still_queries_l2() -> None:
    entities = [SimpleNamespace(entity_type="X", id="x1", properties={})]
    ctx = await retrieve_for_task(
        temporal_engine=None,
        graph_store=_GraphStore(entities),
        task={"description": "find x"},
        group_ids=["g1"],
        limit=5,
    )
    assert ctx.temporal_facts == []
    assert len(ctx.knowledge_entities) == 1
    assert ctx.merged_items[0].source == "knowledge"


@pytest.mark.asyncio
async def test_graph_store_without_search_skips_l2() -> None:
    store = MagicMock(spec=[])
    store.store_id = "broken"
    facts = [
        TemporalFact(
            fact_id="f1",
            text="t",
            group_id="g",
            valid_at=datetime.now(timezone.utc),
        )
    ]
    engine = TemporalMemoryEngine(_TemporalStore(facts))
    ctx = await retrieve_for_task(
        temporal_engine=engine,
        graph_store=store,
        task={"description": "q"},
        group_ids=["g"],
    )
    assert ctx.knowledge_entities == []
    assert len(ctx.merged_items) == 1

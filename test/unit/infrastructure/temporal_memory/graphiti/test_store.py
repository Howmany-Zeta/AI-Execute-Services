"""Unit tests for GraphitiTemporalMemoryStore (mocked Graphiti)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest, SearchFilters
from aiecs.infrastructure.temporal_memory.graphiti.store import GraphitiTemporalMemoryStore

pytestmark = pytest.mark.graphiti


def _make_request() -> IngestEpisodeRequest:
    return IngestEpisodeRequest(
        name="task-1",
        body="user: hi\nassistant: hello",
        source_description="test",
        reference_time=datetime.now(timezone.utc),
        group_id="aiecs:agent:sess",
        source=EpisodeSource.MESSAGE,
    )


@pytest.mark.asyncio
async def test_ingest_episode_maps_graphiti_result() -> None:
    settings = Settings(TM_GRAPH_BACKEND="falkordb", TM_FALKORDB_URL="redis://localhost:6379")
    store = GraphitiTemporalMemoryStore(settings=settings)

    mock_graphiti = MagicMock()
    mock_graphiti.add_episode = AsyncMock(
        return_value=SimpleNamespace(
            episode=SimpleNamespace(uuid="ep-uuid-1"),
            edges=[SimpleNamespace(uuid="e1"), SimpleNamespace(uuid="e2")],
            nodes=[SimpleNamespace(uuid="n1")],
        )
    )
    mock_graphiti.search = AsyncMock(return_value=[])
    mock_graphiti.build_indices_and_constraints = AsyncMock()

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        with patch(
            "aiecs.infrastructure.temporal_memory.graphiti.store._episode_type_for_source",
            return_value="message",
        ):
            result = await store.ingest_episode(_make_request())

    assert result.episode_id == "ep-uuid-1"
    assert result.group_id == "aiecs:agent:sess"
    assert result.facts_extracted == 2
    assert result.entity_count == 1
    mock_graphiti.add_episode.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_facts_maps_entity_edges() -> None:
    settings = Settings(TM_GRAPH_BACKEND="falkordb")
    store = GraphitiTemporalMemoryStore(settings=settings)

    edge = SimpleNamespace(
        uuid="fact-1",
        fact="The weather is sunny",
        group_id="aiecs:agent:sess",
        valid_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        invalid_at=None,
        confidence=0.9,
        episode_uuid="ep-1",
    )
    mock_graphiti = MagicMock()
    mock_graphiti.search = AsyncMock(return_value=[edge])

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        facts = await store.search_facts("weather", group_ids=["aiecs:agent:sess"], limit=3)

    assert len(facts) == 1
    assert facts[0].fact_id == "fact-1"
    assert facts[0].text == "The weather is sunny"
    assert facts[0].group_id == "aiecs:agent:sess"
    mock_graphiti.search.assert_awaited_once()
    call_kwargs = mock_graphiti.search.call_args.kwargs
    assert call_kwargs["group_ids"] == ["aiecs:agent:sess"]
    assert call_kwargs["num_results"] == 3
    assert call_kwargs["center_node_uuid"] is None
    assert call_kwargs.get("search_filter") is None


@pytest.mark.asyncio
async def test_ingest_episode_async_returns_job_id_without_awaiting_background() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings(TM_GRAPH_BACKEND="falkordb"))
    gate = asyncio.Event()

    async def blocked_background(_request: IngestEpisodeRequest, _job_id: str) -> None:
        gate.set()
        await asyncio.Event().wait()

    with patch.object(store, "_ingest_episode_background", side_effect=blocked_background):
        job_id = await store.ingest_episode_async(_make_request())

    assert job_id
    await asyncio.wait_for(gate.wait(), timeout=2.0)
    assert store._pending_ingest_tasks
    for task in list(store._pending_ingest_tasks):
        task.cancel()
    await store.close()


@pytest.mark.asyncio
async def test_search_facts_passes_valid_at_search_filter() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings(TM_GRAPH_BACKEND="falkordb"))
    valid_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    mock_filter = object()
    mock_graphiti = MagicMock()
    mock_graphiti.search = AsyncMock(return_value=[])

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        with patch(
            "aiecs.infrastructure.temporal_memory.graphiti.store.build_graphiti_search_filter",
            return_value=mock_filter,
        ) as build_mock:
            await store.search_facts(
                "weather",
                group_ids=["g1"],
                limit=5,
                valid_at=valid_at,
                filters=SearchFilters(entity_types=["Person"]),
            )

    build_mock.assert_called_once_with(valid_at, SearchFilters(entity_types=["Person"]))
    assert mock_graphiti.search.await_args.kwargs["search_filter"] is mock_filter


@pytest.mark.asyncio
async def test_search_facts_entity_types_maps_to_graphiti_filter() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings(TM_GRAPH_BACKEND="falkordb"))
    mock_graphiti = MagicMock()
    mock_graphiti.search = AsyncMock(return_value=[])
    captured: list[Any] = []

    def _capture(valid_at: datetime | None, filters: SearchFilters | None) -> object:
        captured.append((valid_at, filters))
        return object()

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        with patch(
            "aiecs.infrastructure.temporal_memory.graphiti.store.build_graphiti_search_filter",
            side_effect=_capture,
        ):
            await store.search_facts(
                "q",
                group_ids=["g1"],
                filters=SearchFilters(entity_types=["Organization"]),
            )

    assert captured[0][1] == SearchFilters(entity_types=["Organization"])


@pytest.mark.asyncio
async def test_get_fact_loads_edge_by_uuid() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings(TM_GRAPH_BACKEND="falkordb"))
    edge = SimpleNamespace(
        uuid="fact-uuid-9",
        fact="Exact fact",
        group_id="aiecs:agent:sess",
        valid_at=None,
        invalid_at=None,
    )
    mock_graphiti = MagicMock()
    mock_graphiti.driver = MagicMock()

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        with patch.object(
            store,
            "_fetch_entity_edge",
            new_callable=AsyncMock,
            return_value=edge,
        ):
            fact = await store.get_fact("fact-uuid-9", group_ids=["aiecs:agent:sess"])

    assert fact is not None
    assert fact.fact_id == "fact-uuid-9"
    assert fact.text == "Exact fact"


@pytest.mark.asyncio
async def test_health_check_ready_when_graphiti_loads() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings())
    with patch.object(store, "_ensure_graphiti", return_value=MagicMock()):
        health = await store.health_check()
    assert health["backend"] == "graphiti"
    assert health["ready"] is True


@pytest.mark.asyncio
async def test_health_check_not_ready_on_failure() -> None:
    store = GraphitiTemporalMemoryStore(settings=Settings())

    def _raise() -> MagicMock:
        raise ConnectionError("falkordb down")

    with patch.object(store, "_ensure_graphiti", side_effect=_raise):
        health = await store.health_check()
    assert health["ready"] is False
    assert "error" in health

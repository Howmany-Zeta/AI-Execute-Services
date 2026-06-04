"""Post-filter tests for SearchFilters.excluded_entity_types (Graphiti backend)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.temporal_memory.models import SearchFilters
from aiecs.infrastructure.temporal_memory.graphiti.search_filters import (
    extract_edge_entity_labels,
    filter_facts_by_excluded_entity_types,
)
from aiecs.infrastructure.temporal_memory.graphiti.store import GraphitiTemporalMemoryStore


def test_extract_edge_entity_labels_from_attributes() -> None:
    edge = SimpleNamespace(
        name="WORKS_AT",
        attributes={"source_label": "Person", "target_label": "Organization"},
    )
    assert extract_edge_entity_labels(edge) == ["Person", "Organization", "WORKS_AT"]


def test_filter_facts_by_excluded_entity_types() -> None:
    from aiecs.domain.temporal_memory.models import TemporalFact

    facts = [
        TemporalFact(
            fact_id="1",
            text="a",
            group_id="g",
            metadata={"entity_labels": ["Person"]},
        ),
        TemporalFact(
            fact_id="2",
            text="b",
            group_id="g",
            metadata={"entity_labels": ["Organization"]},
        ),
    ]
    filtered = filter_facts_by_excluded_entity_types(facts, ["Organization"])
    assert len(filtered) == 1
    assert filtered[0].fact_id == "1"


@pytest.mark.asyncio
async def test_search_facts_applies_excluded_entity_types_post_filter() -> None:
    from aiecs.config.config import Settings

    store = GraphitiTemporalMemoryStore(settings=Settings(TM_GRAPH_BACKEND="falkordb"))

    edge_keep = SimpleNamespace(
        uuid="f1",
        fact="Alice works here",
        group_id="g1",
        valid_at=None,
        invalid_at=None,
        confidence=None,
        episode_uuid="ep-1",
        name="REL",
        attributes={"source_label": "Person"},
    )
    edge_drop = SimpleNamespace(
        uuid="f2",
        fact="Acme Corp",
        group_id="g1",
        valid_at=None,
        invalid_at=None,
        confidence=None,
        episode_uuid="ep-1",
        name="REL",
        attributes={"source_label": "Organization"},
    )
    mock_graphiti = MagicMock()
    mock_graphiti.search = AsyncMock(return_value=[edge_keep, edge_drop])

    with patch.object(store, "_ensure_graphiti", return_value=mock_graphiti):
        with patch(
            "aiecs.infrastructure.temporal_memory.graphiti.store.build_graphiti_search_filter",
            return_value=None,
        ):
            facts = await store.search_facts(
                "work",
                group_ids=["g1"],
                limit=10,
                filters=SearchFilters(excluded_entity_types=["Organization"]),
            )

    assert len(facts) == 1
    assert facts[0].fact_id == "f1"

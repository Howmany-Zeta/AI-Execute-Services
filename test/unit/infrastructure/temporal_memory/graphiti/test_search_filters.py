"""Unit tests for Graphiti search filter mapping."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aiecs.domain.temporal_memory.models import SearchFilters
from aiecs.infrastructure.temporal_memory.graphiti.search_filters import (
    build_graphiti_search_filter,
)

pytestmark = pytest.mark.graphiti

graphiti_core = pytest.importorskip("graphiti_core")


@pytest.mark.unit
def test_build_graphiti_search_filter_maps_valid_at_and_entity_types() -> None:
    valid_at = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    filters = SearchFilters(entity_types=["Person"], center_node_uuid="node-1")

    result = build_graphiti_search_filter(valid_at, filters)

    assert result is not None
    assert result.node_labels == ["Person"]
    assert result.valid_at is not None
    assert result.invalid_at is not None


@pytest.mark.unit
def test_build_graphiti_search_filter_none_when_no_inputs() -> None:
    assert build_graphiti_search_filter(None, None) is None

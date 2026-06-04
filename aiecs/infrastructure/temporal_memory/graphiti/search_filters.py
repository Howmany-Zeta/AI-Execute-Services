# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Map AIECS SearchFilters + valid_at to graphiti-core SearchFilters (lazy import)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiecs.domain.temporal_memory.models import SearchFilters, TemporalFact

logger = logging.getLogger(__name__)


def build_graphiti_search_filter(
    valid_at: datetime | None,
    filters: SearchFilters | None,
) -> Any | None:
    """
    Build graphiti_core ``SearchFilters`` for ``Graphiti.search(search_filter=...)``.

    When ``valid_at`` is set, restricts facts that are valid at that instant:
    ``edge.valid_at <= T`` and (``invalid_at IS NULL`` OR ``invalid_at > T``).

    ``entity_types`` maps to Graphiti ``node_labels``. ``excluded_entity_types`` is applied
    after search via :func:`filter_facts_by_excluded_entity_types` (Graphiti has no exclude API).
    """
    if valid_at is None and filters is None:
        return None

    from graphiti_core.search.search_filters import ComparisonOperator, DateFilter
    from graphiti_core.search.search_filters import SearchFilters as GraphitiSearchFilters

    kwargs: dict[str, Any] = {}
    if filters is not None:
        if filters.entity_types:
            kwargs["node_labels"] = list(filters.entity_types)
        if filters.excluded_entity_types:
            logger.debug(
                "Post-filtering excluded entity types: %s",
                filters.excluded_entity_types,
            )

    graphiti_filter = GraphitiSearchFilters(**kwargs) if kwargs else GraphitiSearchFilters()

    if valid_at is not None:
        at = valid_at if valid_at.tzinfo is not None else valid_at.replace(tzinfo=timezone.utc)
        graphiti_filter.valid_at = [[DateFilter(date=at, comparison_operator=ComparisonOperator.less_than_equal)]]
        graphiti_filter.invalid_at = [
            [DateFilter(comparison_operator=ComparisonOperator.is_null)],
            [DateFilter(date=at, comparison_operator=ComparisonOperator.greater_than)],
        ]

    return graphiti_filter


def extract_edge_entity_labels(edge: Any) -> list[str]:
    """
    Best-effort entity labels from a Graphiti ``EntityEdge`` for post-filtering.

    Uses ``attributes`` keys when present; falls back to edge ``name`` (relation).
    """
    labels: list[str] = []
    attrs = getattr(edge, "attributes", None) or {}
    if isinstance(attrs, dict):
        for key in (
            "source_label",
            "target_label",
            "source_labels",
            "target_labels",
            "labels",
            "node_labels",
        ):
            val = attrs.get(key)
            if isinstance(val, str) and val.strip():
                labels.append(val.strip())
            elif isinstance(val, list):
                labels.extend(str(item).strip() for item in val if item)
    name = getattr(edge, "name", None)
    if name:
        labels.append(str(name))
    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        key = label.lower()
        if key not in seen:
            seen.add(key)
            unique.append(label)
    return unique


def filter_facts_by_excluded_entity_types(
    facts: list[TemporalFact],
    excluded_entity_types: list[str] | None,
) -> list[TemporalFact]:
    """Drop facts whose ``metadata['entity_labels']`` intersects ``excluded_entity_types``."""
    if not excluded_entity_types:
        return facts
    excluded = {item.strip().lower() for item in excluded_entity_types if item and str(item).strip()}
    if not excluded:
        return facts

    kept: list[TemporalFact] = []
    for fact in facts:
        raw = (fact.metadata or {}).get("entity_labels")
        labels = [str(x).lower() for x in raw] if isinstance(raw, list) else []
        if any(label in excluded for label in labels):
            continue
        kept.append(fact)
    return kept

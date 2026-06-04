# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Map AIECS SearchFilters + valid_at to graphiti-core SearchFilters (lazy import)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiecs.domain.temporal_memory.models import SearchFilters

logger = logging.getLogger(__name__)


def build_graphiti_search_filter(
    valid_at: datetime | None,
    filters: SearchFilters | None,
) -> Any | None:
    """
    Build graphiti_core ``SearchFilters`` for ``Graphiti.search(search_filter=...)``.

    When ``valid_at`` is set, restricts facts that are valid at that instant:
    ``edge.valid_at <= T`` and (``invalid_at IS NULL`` OR ``invalid_at > T``).

    ``entity_types`` maps to Graphiti ``node_labels``. ``excluded_entity_types`` is not
    supported by graphiti-core search (logged; Phase 3).
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
                "SearchFilters.excluded_entity_types=%r is not applied by Graphiti search " "(planned Phase 3); use entity_types or post-filter in application code",
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

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Temporal fact models for L1 search/retrieve."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """
    Optional filters for temporal fact search.

    - ``entity_types``: mapped to Graphiti ``node_labels`` when using Graphiti backend.
    - ``excluded_entity_types``: post-filter on Graphiti results (``metadata['entity_labels']``);
      ignored on Postgres backend.
    - ``center_node_uuid``: Graphiti rerank anchor (``center_node_uuid`` on ``search()``).
    """

    entity_types: list[str] | None = None
    excluded_entity_types: list[str] | None = None
    center_node_uuid: str | None = None


class TemporalFact(BaseModel):
    """A time-valid fact retrieved from temporal memory."""

    fact_id: str
    text: str
    group_id: str
    valid_at: datetime | None = None
    invalid_at: datetime | None = None
    confidence: float | None = None
    source_episode_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

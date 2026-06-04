# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Unified L1+L2 memory retrieval models (read-only merge, TM-070)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from aiecs.domain.temporal_memory.models import TemporalFact


class RetrievedItem(BaseModel):
    """Single merged retrieval row from L1 temporal or L2 knowledge search."""

    source: Literal["temporal", "knowledge"]
    text: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedMemoryContext(BaseModel):
    """Combined retrieval context for orchestrators / custom reasoning."""

    temporal_facts: list[TemporalFact] = Field(default_factory=list)
    knowledge_entities: list[Any] = Field(default_factory=list)
    merged_items: list[RetrievedItem] = Field(default_factory=list)

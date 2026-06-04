# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Episode ingest models for L1 temporal memory."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EpisodeSource(str, Enum):
    """Episode content type for Graphiti ``EpisodeType`` mapping."""

    MESSAGE = "message"
    DOCUMENT = "document"
    JSON = "json"


class IngestEpisodeRequest(BaseModel):
    """Request to ingest a conversation episode into temporal memory."""

    name: str
    body: str
    source_description: str
    reference_time: datetime
    group_id: str
    source: EpisodeSource = EpisodeSource.MESSAGE
    metadata: dict[str, Any] = Field(default_factory=dict)
    episode_uuid: str | None = None


class IngestEpisodeResult(BaseModel):
    """Result of a synchronous episode ingest."""

    episode_id: str
    group_id: str
    facts_extracted: int = Field(
        default=0,
        description="Graphiti ingest: count of entity edges returned (same as edge_count in L1 MVP)",
    )
    entity_count: int = 0
    edge_count: int = 0
    job_id: str | None = None

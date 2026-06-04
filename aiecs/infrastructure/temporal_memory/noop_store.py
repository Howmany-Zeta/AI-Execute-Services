# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""No-op temporal memory store when L1 is disabled or Graphiti is unavailable."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)


class NoOpTemporalMemoryStore:
    """Stub TemporalMemoryStore: safe defaults, no I/O, no graphiti import."""

    store_id: str = "noop"

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        episode_id = request.episode_uuid or str(uuid.uuid4())
        return IngestEpisodeResult(
            episode_id=episode_id,
            group_id=request.group_id,
            facts_extracted=0,
            entity_count=0,
            edge_count=0,
        )

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        """Port stub; production async ingest uses TemporalMemoryPlugin + ingest_queue."""
        await self.ingest_episode(request)
        return job_id or str(uuid.uuid4())

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]:
        _ = query, group_ids, limit, valid_at, filters
        return []

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"backend": "none", "ready": True}

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Temporal memory store port (L1)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)


@runtime_checkable
class TemporalMemoryStore(Protocol):
    """Port for L1 temporal episode/fact storage (ADR-003: no L2 GraphStore)."""

    store_id: str

    async def initialize(self) -> None: ...

    async def close(self) -> None: ...

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult: ...

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str: ...

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]: ...

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None: ...

    async def health_check(self) -> dict[str, Any]: ...

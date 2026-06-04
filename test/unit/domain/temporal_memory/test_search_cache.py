"""Tests for TemporalMemorySearchCache (TM-067)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)
from aiecs.domain.temporal_memory.search_cache import SearchCacheKey, TemporalMemorySearchCache


class _CountingStore:
    def __init__(self) -> None:
        self.search_count = 0

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        _ = request
        return IngestEpisodeResult(episode_id="ep", group_id="g")

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        _ = job_id
        return "job"

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]:
        _ = valid_at, filters
        self.search_count += 1
        return [
            TemporalFact(
                fact_id="f1",
                text=f"{query}:{limit}",
                group_id=group_ids[0],
                valid_at=datetime.now(timezone.utc),
            )
        ]

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        _ = fact_id, group_ids
        return None

    async def health_check(self) -> dict[str, Any]:
        return {"ready": True}


@pytest.mark.asyncio
async def test_cache_hit_skips_second_store_search() -> None:
    store = _CountingStore()
    cache = TemporalMemorySearchCache(maxsize=16, ttl_seconds=60.0)

    facts1, hit1 = await cache.get_or_search(
        store,
        "weather",
        group_ids=["g1"],
        limit=5,
        valid_at=None,
        filters=None,
    )
    facts2, hit2 = await cache.get_or_search(
        store,
        "weather",
        group_ids=["g1"],
        limit=5,
        valid_at=None,
        filters=None,
    )

    assert hit1 is False
    assert hit2 is True
    assert store.search_count == 1
    assert facts1[0].text == facts2[0].text


@pytest.mark.asyncio
async def test_different_limit_is_cache_miss() -> None:
    store = _CountingStore()
    cache = TemporalMemorySearchCache(maxsize=16, ttl_seconds=60.0)

    await cache.get_or_search(store, "q", group_ids=["g1"], limit=5, valid_at=None, filters=None)
    await cache.get_or_search(store, "q", group_ids=["g1"], limit=10, valid_at=None, filters=None)

    assert store.search_count == 2


def test_build_key_includes_filters_fingerprint() -> None:
    k1 = TemporalMemorySearchCache.build_key(
        "q",
        group_ids=["a"],
        limit=3,
        valid_at=None,
        filters=SearchFilters(entity_types=["Person"]),
    )
    k2 = TemporalMemorySearchCache.build_key(
        "q",
        group_ids=["a"],
        limit=3,
        valid_at=None,
        filters=SearchFilters(entity_types=["Organization"]),
    )
    assert k1 != k2
    assert isinstance(k1, SearchCacheKey)


@pytest.mark.asyncio
async def test_engine_with_cache_disabled_calls_store_each_time() -> None:
    store = _CountingStore()
    engine = TemporalMemoryEngine(
        store,
        settings=Settings(TM_SEARCH_CACHE_ENABLED=False),
    )
    task = {"description": "weather"}
    await engine.search_for_task(task, ["g1"])
    await engine.search_for_task(task, ["g1"])
    assert store.search_count == 2


@pytest.mark.asyncio
async def test_engine_with_cache_enabled_reuses_results() -> None:
    store = _CountingStore()
    engine = TemporalMemoryEngine(
        store,
        settings=Settings(TM_SEARCH_CACHE_ENABLED=True, TM_SEARCH_CACHE_TTL_SECONDS=60),
    )
    task = {"description": "weather"}
    await engine.search_for_task(task, ["g1"])
    await engine.search_for_task(task, ["g1"])
    assert store.search_count == 1

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Process-local TTL cache for temporal memory search (TM-067).

Mount point: option A — :meth:`TemporalMemoryEngine.search_for_task` wraps the store.
Uses ``cachetools.TTLCache`` (already a main dependency in pyproject.toml).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from cachetools import TTLCache

from aiecs.domain.temporal_memory.models import SearchFilters, TemporalFact
from aiecs.domain.temporal_memory.ports import TemporalMemoryStore


def _valid_at_iso(valid_at: datetime | None) -> str:
    if valid_at is None:
        return ""
    at = valid_at if valid_at.tzinfo is not None else valid_at.replace(tzinfo=timezone.utc)
    return at.isoformat()


def _filters_fingerprint(filters: SearchFilters | None) -> str:
    if filters is None:
        return ""
    payload = filters.model_dump(mode="json", exclude_none=True)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class SearchCacheKey:
    """Cache key for a temporal search request."""

    query: str
    group_ids: tuple[str, ...]
    valid_at_iso: str
    filters_fingerprint: str
    limit: int


class TemporalMemorySearchCache:
    """Async-safe wrapper around ``TTLCache`` for ``search_facts`` results."""

    def __init__(self, *, maxsize: int, ttl_seconds: float) -> None:
        self._cache: TTLCache[SearchCacheKey, list[TemporalFact]] = TTLCache(
            maxsize=maxsize,
            ttl=ttl_seconds,
        )
        self._lock = asyncio.Lock()

    @staticmethod
    def build_key(
        query: str,
        *,
        group_ids: list[str],
        limit: int,
        valid_at: datetime | None,
        filters: SearchFilters | None,
    ) -> SearchCacheKey:
        return SearchCacheKey(
            query=query,
            group_ids=tuple(group_ids),
            valid_at_iso=_valid_at_iso(valid_at),
            filters_fingerprint=_filters_fingerprint(filters),
            limit=limit,
        )

    async def get_or_search(
        self,
        store: TemporalMemoryStore,
        query: str,
        *,
        group_ids: list[str],
        limit: int,
        valid_at: datetime | None,
        filters: SearchFilters | None,
    ) -> tuple[list[TemporalFact], bool]:
        """
        Return cached facts on hit; otherwise call ``store.search_facts`` and cache.

        Returns ``(facts, cache_hit)``.
        """
        key = self.build_key(
            query,
            group_ids=group_ids,
            limit=limit,
            valid_at=valid_at,
            filters=filters,
        )
        async with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                return list(cached), True

        facts = await store.search_facts(
            query,
            group_ids=group_ids,
            limit=limit,
            valid_at=valid_at,
            filters=filters,
        )
        async with self._lock:
            self._cache[key] = facts
        return facts, False

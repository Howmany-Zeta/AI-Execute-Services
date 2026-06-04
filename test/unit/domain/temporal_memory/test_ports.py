"""Tests that infrastructure stores satisfy the TemporalMemoryStore port."""

from __future__ import annotations

import pytest

from aiecs.domain.temporal_memory.ports import TemporalMemoryStore
from aiecs.infrastructure.temporal_memory.noop_store import NoOpTemporalMemoryStore


@pytest.mark.asyncio
async def test_noop_isinstance_temporal_memory_store() -> None:
    store = NoOpTemporalMemoryStore()
    assert isinstance(store, TemporalMemoryStore)

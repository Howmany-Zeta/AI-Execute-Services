"""Tests for NoOpTemporalMemoryStore."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest
from aiecs.domain.temporal_memory.ports import TemporalMemoryStore
from aiecs.infrastructure.temporal_memory.noop_store import NoOpTemporalMemoryStore


@pytest.mark.asyncio
async def test_noop_satisfies_port_protocol() -> None:
    store = NoOpTemporalMemoryStore()
    assert isinstance(store, TemporalMemoryStore)


@pytest.mark.asyncio
async def test_noop_ingest_and_search() -> None:
    store = NoOpTemporalMemoryStore()
    await store.initialize()
    request = IngestEpisodeRequest(
        name="test",
        body="user: hi\nassistant: hello",
        source_description="unit test",
        reference_time=datetime.now(timezone.utc),
        group_id="aiecs:agent1:session1",
        source=EpisodeSource.MESSAGE,
    )
    result = await store.ingest_episode(request)
    assert result.group_id == "aiecs:agent1:session1"
    assert result.facts_extracted == 0

    facts = await store.search_facts("hello", group_ids=["aiecs:agent1:session1"])
    assert facts == []

    health = await store.health_check()
    assert health["backend"] == "none"
    assert health["ready"] is True
    await store.close()

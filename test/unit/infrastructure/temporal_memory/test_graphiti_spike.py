"""Optional Graphiti/FalkorDB spike test — not a default CI gate."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest

pytestmark = pytest.mark.graphiti


def _spike_enabled() -> bool:
    return os.environ.get("TM_RUN_GRAPHITI_SPIKE", "").lower() in ("1", "true", "yes")


@pytest.mark.asyncio
@pytest.mark.skipif(not _spike_enabled(), reason="Set TM_RUN_GRAPHITI_SPIKE=1 and run FalkorDB to execute")
async def test_graphiti_add_episode_and_search() -> None:
    from aiecs.infrastructure.temporal_memory.graphiti.store import GraphitiTemporalMemoryStore

    settings = Settings(
        TM_ENABLED=True,
        TM_BACKEND="graphiti",
        TM_GRAPH_BACKEND="falkordb",
        TM_FALKORDB_URL=os.environ.get("TM_FALKORDB_URL", "redis://localhost:6379"),
    )
    store = GraphitiTemporalMemoryStore(settings=settings)
    await store.initialize()

    group_id = "aiecs:spike_agent:spike_session"
    request = IngestEpisodeRequest(
        name="spike_episode",
        body="User asked about the weather. Assistant said it is sunny.",
        source_description="TM-020 spike",
        reference_time=datetime.now(timezone.utc),
        group_id=group_id,
        source=EpisodeSource.MESSAGE,
    )
    result = await store.ingest_episode(request)
    assert result.group_id == group_id

    facts = await store.search_facts("weather", group_ids=[group_id], limit=5)
    assert isinstance(facts, list)

    health = await store.health_check()
    assert health.get("backend") == "graphiti"
    await store.close()

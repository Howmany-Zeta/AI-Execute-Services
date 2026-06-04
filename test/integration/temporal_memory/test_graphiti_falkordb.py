"""Optional FalkorDB integration for Graphiti temporal memory."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest
from aiecs.infrastructure.temporal_memory.graphiti.store import GraphitiTemporalMemoryStore

pytestmark = pytest.mark.graphiti


def _falkordb_configured() -> bool:
    return bool(os.environ.get("TM_FALKORDB_URL", "").strip())


@pytest.mark.asyncio
@pytest.mark.skipif(not _falkordb_configured(), reason="Set TM_FALKORDB_URL to run FalkorDB integration")
async def test_graphiti_ingest_and_search_on_falkordb() -> None:
    graphiti_core = pytest.importorskip("graphiti_core")

    _ = graphiti_core

    settings = Settings(
        TM_ENABLED=True,
        TM_BACKEND="graphiti",
        TM_GRAPH_BACKEND="falkordb",
        TM_FALKORDB_URL=os.environ["TM_FALKORDB_URL"],
    )
    store = GraphitiTemporalMemoryStore(settings=settings)
    await store.initialize()

    group_id = "aiecs:integ:session"
    marker = "TM_INTEG_UNIQUE_PHRASE_ZEBRA42"
    request = IngestEpisodeRequest(
        name="integration_episode",
        body=f"user: recall {marker} assistant: The answer involves {marker}.",
        source_description="integration test",
        reference_time=datetime.now(timezone.utc),
        group_id=group_id,
        source=EpisodeSource.MESSAGE,
    )
    result = await store.ingest_episode(request)
    assert result.group_id == group_id
    assert result.episode_id

    facts = await store.search_facts(marker, group_ids=[group_id], limit=10)
    assert facts, f"expected search hit for marker {marker!r} in group {group_id}"
    texts = " ".join(f.text for f in facts if f.text).lower()
    assert marker.lower() in texts or "zebra42" in texts

    if facts[0].fact_id:
        loaded = await store.get_fact(facts[0].fact_id, group_ids=[group_id])
        assert loaded is not None
        assert loaded.fact_id == facts[0].fact_id

    await store.close()

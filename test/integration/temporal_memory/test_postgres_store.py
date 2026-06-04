"""Optional Postgres integration for L1 temporal memory."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest
from aiecs.infrastructure.temporal_memory.postgres.store import PostgresTemporalMemoryStore

pytestmark = pytest.mark.postgres


def _postgres_configured() -> bool:
    return bool(os.environ.get("TM_POSTGRES_URL", "").strip())


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _postgres_configured(),
    reason="Set TM_POSTGRES_URL to run Postgres temporal memory integration",
)
async def test_postgres_ingest_and_search() -> None:
    settings = Settings(
        TM_ENABLED=True,
        TM_BACKEND="postgres",
        TM_POSTGRES_URL=os.environ["TM_POSTGRES_URL"],
        TM_POSTGRES_AUTO_CREATE_TABLES=True,
    )
    store = PostgresTemporalMemoryStore(settings=settings)
    await store.initialize()

    group_id = "aiecs:integ:postgres"
    marker = "TM_POSTGRES_INTEG_ZEBRA42"
    request = IngestEpisodeRequest(
        name="integration_episode",
        body=f"user: recall {marker} assistant: noted {marker}.",
        source_description="postgres integration test",
        reference_time=datetime.now(timezone.utc),
        group_id=group_id,
        source=EpisodeSource.MESSAGE,
    )
    result = await store.ingest_episode(request)
    assert result.group_id == group_id
    assert result.episode_id
    assert result.facts_extracted >= 1

    facts = await store.search_facts(marker, group_ids=[group_id], limit=10)
    assert facts, f"expected search hit for marker {marker!r} in group {group_id}"
    texts = " ".join(f.text for f in facts if f.text).lower()
    assert marker.lower() in texts

    if facts[0].fact_id:
        loaded = await store.get_fact(facts[0].fact_id, group_ids=[group_id])
        assert loaded is not None
        assert loaded.fact_id == facts[0].fact_id

    health = await store.health_check()
    assert health.get("ready") is True

    await store.close()

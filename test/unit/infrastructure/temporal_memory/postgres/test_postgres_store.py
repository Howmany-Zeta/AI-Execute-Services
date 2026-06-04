"""Unit tests for PostgresTemporalMemoryStore with mocked asyncpg pool."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.temporal_memory.models import EpisodeSource, IngestEpisodeRequest
from aiecs.infrastructure.temporal_memory.postgres.store import (
    PostgresTemporalMemoryStore,
    _escape_ilike_pattern,
)


@pytest.fixture
def store() -> PostgresTemporalMemoryStore:
    return PostgresTemporalMemoryStore(
        settings=Settings(
            TM_ENABLED=True,
            TM_BACKEND="postgres",
            TM_POSTGRES_URL="postgresql://user:pass@localhost/testdb",
            TM_POSTGRES_AUTO_CREATE_TABLES=False,
        )
    )


def test_escape_ilike_pattern() -> None:
    assert _escape_ilike_pattern("a%b_c") == "a\\%b\\_c"


def test_resolve_dsn_requires_url() -> None:
    bad = PostgresTemporalMemoryStore(
        settings=SimpleNamespace(tm_postgres_url="", postgres_url="")
    )
    with pytest.raises(ValueError, match="TM_POSTGRES_URL"):
        bad._resolve_dsn()


@pytest.mark.asyncio
async def test_initialize_creates_pool_and_checks_schema(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire

    with patch(
        "aiecs.infrastructure.temporal_memory.postgres.store.asyncpg.create_pool",
        new=AsyncMock(return_value=mock_pool),
    ):
        await store.initialize()

    assert store._pool is mock_pool
    mock_conn.fetchval.assert_awaited()


@pytest.mark.asyncio
async def test_ingest_episode_inserts_episode_and_fact(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    @asynccontextmanager
    async def _transaction():
        yield None

    mock_conn.transaction = _transaction
    mock_pool.acquire = _acquire
    store._pool = mock_pool

    request = IngestEpisodeRequest(
        name="turn",
        body="user: hello assistant: hi",
        source_description="test",
        reference_time=datetime.now(timezone.utc),
        group_id="aiecs:unit:session",
        source=EpisodeSource.MESSAGE,
        episode_uuid="11111111-1111-4111-8111-111111111111",
    )
    result = await store.ingest_episode(request)

    assert result.episode_id == "11111111-1111-4111-8111-111111111111"
    assert result.group_id == "aiecs:unit:session"
    assert result.facts_extracted == 1
    assert mock_conn.execute.await_count == 2


@pytest.mark.asyncio
async def test_search_facts_returns_empty_without_query(store: PostgresTemporalMemoryStore) -> None:
    store._pool = MagicMock()
    facts = await store.search_facts("", group_ids=["g1"])
    assert facts == []


@pytest.mark.asyncio
async def test_search_facts_queries_tm_fact(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = MagicMock()
    now = datetime.now(timezone.utc)
    mock_pool.fetch = AsyncMock(
        return_value=[
            {
                "fact_id": "22222222-2222-4222-8222-222222222222",
                "group_id": "aiecs:unit:session",
                "text": "marker ZEBRA42",
                "valid_at": now,
                "invalid_at": None,
                "confidence": None,
                "source_episode_id": "11111111-1111-4111-8111-111111111111",
                "metadata": {},
            }
        ]
    )
    store._pool = mock_pool

    facts = await store.search_facts(
        "ZEBRA42",
        group_ids=["aiecs:unit:session"],
        limit=5,
        valid_at=now,
    )

    assert len(facts) == 1
    assert facts[0].fact_id == "22222222-2222-4222-8222-222222222222"
    assert "ZEBRA42" in facts[0].text
    mock_pool.fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_fact_respects_group_ids(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = MagicMock()
    mock_pool.fetchrow = AsyncMock(
        return_value={
            "fact_id": "22222222-2222-4222-8222-222222222222",
            "group_id": "other",
            "text": "x",
            "valid_at": None,
            "invalid_at": None,
            "confidence": None,
            "source_episode_id": None,
            "metadata": {},
        }
    )
    store._pool = mock_pool

    loaded = await store.get_fact(
        "22222222-2222-4222-8222-222222222222",
        group_ids=["aiecs:unit:session"],
    )
    assert loaded is None


@pytest.mark.asyncio
async def test_health_check_ready(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire
    store._pool = mock_pool

    status = await store.health_check()
    assert status["backend"] == "postgres"
    assert status["ready"] is True


@pytest.mark.asyncio
async def test_close_closes_pool(store: PostgresTemporalMemoryStore) -> None:
    mock_pool = AsyncMock()
    store._pool = mock_pool
    await store.close()
    mock_pool.close.assert_awaited_once()
    assert store._pool is None

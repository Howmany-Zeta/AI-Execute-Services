"""Unit tests for PostgresPermanentBackend with mocked asyncpg pool."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.infrastructure.persistence.postgres_permanent_backend import PostgresPermanentBackend


@pytest.fixture
def backend():
    return PostgresPermanentBackend(dsn="postgresql://user:pass@localhost/testdb", auto_create_tables=False)


@pytest.mark.asyncio
async def test_initialize_creates_pool():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire

    with patch(
        "aiecs.infrastructure.persistence.postgres_permanent_backend.asyncpg.create_pool",
        new=AsyncMock(return_value=mock_pool),
    ):
        backend_auto = PostgresPermanentBackend(dsn="postgresql://user:pass@localhost/testdb")
        ok = await backend_auto.initialize()

    assert ok is True
    assert backend_auto.is_available is True
    assert mock_conn.execute.await_count >= 1


@pytest.mark.asyncio
async def test_append_session_event_returns_false_without_pool(backend):
    assert await backend.append_session_event("s1", "u1", "create", {"k": "v"}) is False


@pytest.mark.asyncio
async def test_append_session_event_inserts_row(backend):
    mock_pool = MagicMock()
    mock_conn = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire
    backend._pool = mock_pool

    ok = await backend.append_session_event("session-1", "user-1", "create", {"status": "active"})

    assert ok is True
    mock_conn.execute.assert_awaited_once()
    sql = mock_conn.execute.await_args.args[0]
    assert "INSERT INTO context_sessions" in sql


@pytest.mark.asyncio
async def test_close_releases_pool(backend):
    mock_pool = AsyncMock()
    backend._pool = mock_pool
    await backend.close()
    mock_pool.close.assert_awaited_once()
    assert backend._pool is None

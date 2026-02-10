"""
Quick integration test for get_clickhouse_client convenience function.

Tests: initialize_clickhouse_client, get_clickhouse_client, insert, query, close_clickhouse_client.

Prerequisites:
- ClickHouse running (CLICKHOUSE_* in .env.test)
- CLICKHOUSE_ENABLED=true in .env.test

Run: poetry run pytest test/integration/context/test_get_clickhouse_client.py -v
"""

import os
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env.test before imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
os.environ["CLICKHOUSE_ENABLED"] = "true"

from aiecs.infrastructure.persistence import (
    get_clickhouse_client,
    initialize_clickhouse_client,
    close_clickhouse_client,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.fixture
async def clickhouse_client():
    """Initialize ClickHouse client for test, yield, then close."""
    ok = await initialize_clickhouse_client()
    if not ok:
        pytest.skip("ClickHouse not available (not installed or connection failed)")
    try:
        yield await get_clickhouse_client()
    finally:
        await close_clickhouse_client()


async def test_get_clickhouse_client_returns_same_instance(clickhouse_client):
    """get_clickhouse_client returns the same singleton instance."""
    client1 = await get_clickhouse_client()
    client2 = await get_clickhouse_client()
    assert client1 is client2
    assert client1.is_available


async def test_get_clickhouse_client_insert_and_query(clickhouse_client):
    """Insert and query via get_clickhouse_client works."""
    table = f"test_get_ch_{uuid.uuid4().hex[:12]}"
    client = await get_clickhouse_client()

    # Create table
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id String,
        value String,
        created_at DateTime64(3)
    ) ENGINE = MergeTree() ORDER BY (id, created_at)
    """
    assert await client.command(sql)

    # Insert
    row = {
        "id": "test-1",
        "value": "hello",
        "created_at": datetime.utcnow(),
    }
    assert await client.insert(table, [row])

    # Query
    result = await client.query(f"SELECT id, value FROM {table} WHERE id = 'test-1'")
    assert result is not None
    rows = getattr(result, "result_rows", result) if result else []
    assert len(rows) == 1
    assert rows[0][0] == "test-1"
    assert rows[0][1] == "hello"

    # Cleanup
    await client.command(f"DROP TABLE IF EXISTS {table}")


async def test_get_clickhouse_client_raises_when_not_initialized():
    """get_clickhouse_client raises RuntimeError when not initialized."""
    # Ensure we're in a clean state
    await close_clickhouse_client()

    with pytest.raises(RuntimeError, match="not initialized"):
        await get_clickhouse_client()

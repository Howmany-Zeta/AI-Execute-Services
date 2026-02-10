"""
ContextEngine ClickHouse Integration Tests

Tests all ContextEngine dual-write functions to ClickHouse:
- append_session_event (create, update, end)
- append_conversation_message
- append_task_context_snapshot
- append_checkpoint
- append_checkpoint_writes
- append_conversation_session

Uses FULL ContextEngine with Redis + ClickHouse, and real LLM response from
test/data/response.txt to verify large content can be stored in ClickHouse.

Prerequisites:
- Redis running (REDIS_* in .env.test)
- ClickHouse running (CLICKHOUSE_* in .env.test)
- CLICKHOUSE_ENABLED=true in .env.test
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env.test before imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
os.environ["CLICKHOUSE_ENABLED"] = "true"

from aiecs.infrastructure.persistence import (
    initialize_context_engine,
    close_context_engine,
    get_context_engine,
)
from aiecs.infrastructure.persistence.redis_client import (
    initialize_redis_client,
    close_redis_client,
)
from aiecs.domain.task.task_context import TaskContext

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def llm_response_content():
    """Load real LLM response from test/data/response.txt."""
    path = PROJECT_ROOT / "test" / "data" / "response.txt"
    if not path.exists():
        pytest.skip(f"LLM response file not found: {path}")
    return path.read_text(encoding="utf-8")


@pytest.fixture
async def context_engine():
    """Initialize full ContextEngine (Redis + ClickHouse) for each test."""
    engine = await _init_engine()
    try:
        yield engine
    finally:
        await _close_engine()


async def _init_engine():
    """Initialize Redis and ContextEngine with ClickHouse."""
    await initialize_redis_client()
    engine = await initialize_context_engine()
    if not engine:
        raise RuntimeError("ContextEngine failed to initialize (check Redis)")
    if not getattr(engine, "_permanent_backend", None):
        raise RuntimeError("ClickHouse not enabled - set CLICKHOUSE_ENABLED=true")
    if not engine._permanent_backend._client.is_available:
        raise RuntimeError("ClickHouse client not connected")
    return engine


async def _close_engine():
    """Close ContextEngine and Redis."""
    await close_context_engine()
    await close_redis_client()


def _get_ch_client():
    """Get ClickHouse client from ContextEngine for verification queries."""
    engine = get_context_engine()
    if not engine or not engine._permanent_backend:
        return None
    return engine._permanent_backend._client


async def _query_clickhouse(sql: str):
    """Run query against ClickHouse and return result rows."""
    client = _get_ch_client()
    if not client or not client.is_available:
        return None
    result = await client.query(sql)
    if result is None:
        return None
    return getattr(result, "result_rows", result) if result else None


# =============================================================================
# Tests
# =============================================================================


async def test_clickhouse_session_create_update_end(context_engine):
    """Test append_session_event: create, update, end."""
    engine = get_context_engine()
    session_id = "ce-ch-test-session-001"
    user_id = "test-user-001"

    # Create -> append_session_event(create)
    await engine.create_session(session_id, user_id, {"test": "clickhouse"})
    await engine.update_session(session_id, increment_requests=True)
    await engine.end_session(session_id, status="completed")

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT session_id, event_type FROM context_sessions WHERE session_id = '{session_id}' ORDER BY created_at"
    )
    assert rows is not None, "ClickHouse query failed"
    assert len(rows) >= 3
    event_types = [r[1] for r in rows]
    assert "create" in event_types
    assert "update" in event_types
    assert "end" in event_types


async def test_clickhouse_conversation_message_with_real_llm_response(
    context_engine, llm_response_content
):
    """Test append_conversation_message with real LLM response from response.txt."""
    engine = get_context_engine()
    session_id = "ce-ch-test-llm-001"
    user_id = "test-user-llm"

    await engine.create_session(session_id, user_id)

    # Add user message
    await engine.add_conversation_message(session_id, "user", "Why is Tesla so popular?")

    # Add assistant message with REAL LLM response (full content from response.txt)
    await engine.add_conversation_message(
        session_id,
        "assistant",
        llm_response_content,
        metadata={"source": "response.txt", "model": "test"},
    )

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT session_id, role, length(content), content FROM context_conversations "
        f"WHERE session_id = '{session_id}' ORDER BY created_at"
    )
    assert rows is not None, "ClickHouse query failed"
    assert len(rows) >= 2

    # Find assistant message with LLM response
    assistant_rows = [r for r in rows if r[1] == "assistant"]
    assert len(assistant_rows) >= 1
    content_len = assistant_rows[0][2]
    content = assistant_rows[0][3]
    assert content_len > 500, f"Expected large LLM response, got {content_len} chars"
    assert "Tesla" in content or "Intent Analysis" in content


async def test_clickhouse_task_context_snapshot(context_engine):
    """Test append_task_context_snapshot."""
    engine = get_context_engine()
    session_id = "ce-ch-test-ctx-001"
    user_id = "test-user-ctx"

    await engine.create_session(session_id, user_id)

    # Store task context
    context = TaskContext(
        {"user_id": user_id, "chat_id": session_id, "metadata": {"task": "analyze"}}
    )
    context.metadata["llm_response"] = "Partial analysis result"
    await engine.store_task_context(session_id, context)

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT session_id, length(context_data) FROM context_task_contexts "
        f"WHERE session_id = '{session_id}'"
    )
    assert rows is not None
    assert len(rows) >= 1
    assert rows[0][1] > 0


async def test_clickhouse_checkpoint(context_engine):
    """Test append_checkpoint."""
    engine = get_context_engine()
    thread_id = "ce-ch-test-thread-001"
    checkpoint_id = "ckpt-001"

    await engine.store_checkpoint(
        thread_id,
        checkpoint_id,
        {"state": {"messages": [{"role": "user", "content": "Hello"}]}},
        metadata={"step": 1},
    )

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT thread_id, checkpoint_id FROM context_checkpoints "
        f"WHERE thread_id = '{thread_id}' AND checkpoint_id = '{checkpoint_id}'"
    )
    assert rows is not None
    assert len(rows) >= 1


async def test_clickhouse_checkpoint_writes(context_engine):
    """Test append_checkpoint_writes."""
    engine = get_context_engine()
    thread_id = "ce-ch-test-writes-001"
    checkpoint_id = "ckpt-writes-001"
    task_id = "task-001"
    writes_data = [("messages", ("test",))]

    await engine.put_writes(thread_id, checkpoint_id, task_id, writes_data)

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT thread_id, checkpoint_id, task_id FROM context_checkpoint_writes "
        f"WHERE thread_id = '{thread_id}' AND checkpoint_id = '{checkpoint_id}'"
    )
    assert rows is not None
    assert len(rows) >= 1


async def test_clickhouse_conversation_session(context_engine):
    """Test append_conversation_session."""
    engine = get_context_engine()
    session_id = "ce-ch-test-cs-001"
    participants = [
        {"id": "user-1", "type": "user", "role": "user", "metadata": {}},
        {"id": "agent-1", "type": "agent", "role": "assistant", "metadata": {}},
    ]

    session_key = await engine.create_conversation_session(
        session_id, participants, "user_to_agent", {"test": "clickhouse"}
    )

    # Verify in ClickHouse
    rows = await _query_clickhouse(
        f"SELECT session_key, session_data FROM context_conversation_sessions "
        f"WHERE session_key = '{session_key}'"
    )
    assert rows is not None
    assert len(rows) >= 1
    assert session_key in str(rows[0])


async def test_clickhouse_all_tables_populated(context_engine, llm_response_content):
    """End-to-end: run all operations and verify all ClickHouse tables have data."""
    engine = get_context_engine()
    prefix = "ce-ch-e2e"

    # Session + conversation with LLM response
    await engine.create_session(f"{prefix}-session", "e2e-user")
    await engine.add_conversation_message(
        f"{prefix}-session", "assistant", llm_response_content[:2000]
    )
    await engine.update_session(f"{prefix}-session", increment_requests=True)

    # Task context
    ctx = TaskContext({"user_id": "e2e", "chat_id": f"{prefix}-session"})
    await engine.store_task_context(f"{prefix}-session", ctx)

    # Checkpoint + writes
    await engine.store_checkpoint(
        f"{prefix}-thread", "ckpt-e2e", {"data": "test"}, metadata={}
    )
    await engine.put_writes(f"{prefix}-thread", "ckpt-e2e", "task-e2e", [("x", ("y",))])

    # Conversation session (user_to_agent requires user + agent participants)
    await engine.create_conversation_session(
        f"{prefix}-session",
        [
            {"id": "p1", "type": "user", "role": "user"},
            {"id": "p2", "type": "agent", "role": "assistant"},
        ],
        "user_to_agent",
    )

    await engine.end_session(f"{prefix}-session")

    # Verify all tables
    tables = [
        "context_sessions",
        "context_conversations",
        "context_task_contexts",
        "context_checkpoints",
        "context_checkpoint_writes",
        "context_conversation_sessions",
    ]
    for table in tables:
        rows = await _query_clickhouse(f"SELECT count() FROM {table}")
        assert rows is not None, f"Query failed for {table}"
        assert rows[0][0] > 0, f"Table {table} is empty"

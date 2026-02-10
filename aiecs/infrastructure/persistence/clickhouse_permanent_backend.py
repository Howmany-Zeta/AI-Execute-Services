"""
ClickHouse permanent storage backend for ContextEngine dual-write.

Implements IPermanentStorageBackend for append-only disk persistence.
Used alongside Redis (hot cache) - writes are fire-and-forget, failures
do not block the primary path.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiecs.core.interface.storage_interface import IPermanentStorageBackend

from .clickhouse_client import ClickHouseClient, CLICKHOUSE_AVAILABLE

logger = logging.getLogger(__name__)


def _safe_json_dumps(obj: Any) -> str:
    """Serialize to JSON, handling datetime."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return json.dumps(obj, default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o))


class ClickHousePermanentBackend(IPermanentStorageBackend):
    """
    ClickHouse implementation of IPermanentStorageBackend.

    Append-only storage for sessions, conversations, checkpoints.
    Auto-creates tables on first use if auto_create_tables=True.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        auto_create_tables: bool = True,
    ) -> None:
        self._client = ClickHouseClient(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database or "default",
        )
        self._auto_create_tables = auto_create_tables
        self._tables_created = False

    async def initialize(self) -> bool:
        """Initialize ClickHouse connection and optionally create tables."""
        if not await self._client.initialize():
            return False

        if self._auto_create_tables and not self._tables_created:
            await self._ensure_tables()
            self._tables_created = True

        return True

    async def close(self) -> None:
        """Close ClickHouse connection."""
        await self._client.close()

    async def _ensure_tables(self) -> None:
        """Create tables if they do not exist."""
        tables_sql = [
            """CREATE TABLE IF NOT EXISTS context_sessions (
                session_id String,
                user_id String,
                event_type LowCardinality(String),
                payload String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (session_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS context_conversations (
                session_id String,
                role LowCardinality(String),
                content String,
                metadata String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (session_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS context_task_contexts (
                session_id String,
                context_data String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (session_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS context_checkpoints (
                thread_id String,
                checkpoint_id String,
                data String,
                metadata String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (thread_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS context_checkpoint_writes (
                thread_id String,
                checkpoint_id String,
                task_id String,
                writes_data String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (thread_id, created_at)""",
            """CREATE TABLE IF NOT EXISTS context_conversation_sessions (
                session_key String,
                session_data String,
                created_at DateTime64(3)
            ) ENGINE = MergeTree()
            ORDER BY (session_key, created_at)""",
        ]

        for sql in tables_sql:
            if not await self._client.command(sql):
                logger.warning(f"Table creation may have failed: {sql[:80]}...")

    def _parse_dt(self, value: Optional[str]) -> datetime:
        """Parse datetime from ISO string or return now."""
        if value:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return datetime.utcnow()

    async def append_session_event(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
        payload: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append session create/update/end event."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "session_id": session_id,
            "user_id": user_id,
            "event_type": event_type,
            "payload": _safe_json_dumps(payload),
            "created_at": dt,
        }
        return await self._client.insert("context_sessions", [row])

    async def append_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> bool:
        """Append conversation message."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": _safe_json_dumps(metadata or {}),
            "created_at": dt,
        }
        return await self._client.insert("context_conversations", [row])

    async def append_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
    ) -> bool:
        """Append checkpoint data."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "data": _safe_json_dumps(checkpoint_data),
            "metadata": _safe_json_dumps(metadata or {}),
            "created_at": dt,
        }
        return await self._client.insert("context_checkpoints", [row])

    async def append_checkpoint_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append checkpoint writes."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "writes_data": _safe_json_dumps(writes_data),
            "created_at": dt,
        }
        return await self._client.insert("context_checkpoint_writes", [row])

    async def append_conversation_session(
        self,
        session_key: str,
        session_data: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append conversation session metadata."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "session_key": session_key,
            "session_data": _safe_json_dumps(session_data),
            "created_at": dt,
        }
        return await self._client.insert("context_conversation_sessions", [row])

    async def append_task_context_snapshot(
        self,
        session_id: str,
        context_data: Dict[str, Any],
        created_at: Optional[str] = None,
    ) -> bool:
        """Append task context snapshot."""
        if not self._client.is_available:
            return False

        dt = self._parse_dt(created_at)
        row = {
            "session_id": session_id,
            "context_data": _safe_json_dumps(context_data),
            "created_at": dt,
        }
        return await self._client.insert("context_task_contexts", [row])

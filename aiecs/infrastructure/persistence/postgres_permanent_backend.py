# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
PostgreSQL permanent storage backend for ContextEngine dual-write.

Implements IPermanentStorageBackend for append-only disk persistence.
Used alongside Redis (hot cache) - writes are fire-and-forget, failures
do not block the primary path.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import asyncpg

from aiecs.config.config import get_settings
from aiecs.core.interface.storage_interface import IPermanentStorageBackend

from .permanent_backend_utils import parse_created_at, safe_json_dumps

logger = logging.getLogger(__name__)

_CONTEXT_TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS context_sessions (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_sessions_session_created ON context_sessions (session_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS context_conversations (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_conversations_session_created ON context_conversations (session_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS context_task_contexts (
        id BIGSERIAL PRIMARY KEY,
        session_id TEXT NOT NULL,
        context_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_task_contexts_session_created ON context_task_contexts (session_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS context_checkpoints (
        id BIGSERIAL PRIMARY KEY,
        thread_id TEXT NOT NULL,
        checkpoint_id TEXT NOT NULL,
        data JSONB NOT NULL DEFAULT '{}'::jsonb,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_checkpoints_thread_created ON context_checkpoints (thread_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS context_checkpoint_writes (
        id BIGSERIAL PRIMARY KEY,
        thread_id TEXT NOT NULL,
        checkpoint_id TEXT NOT NULL,
        task_id TEXT NOT NULL,
        writes_data JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_checkpoint_writes_thread_created ON context_checkpoint_writes (thread_id, created_at)",
    """
    CREATE TABLE IF NOT EXISTS context_conversation_sessions (
        id BIGSERIAL PRIMARY KEY,
        session_key TEXT NOT NULL,
        session_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_context_conversation_sessions_key_created ON context_conversation_sessions (session_key, created_at)",
]


class PostgresPermanentBackend(IPermanentStorageBackend):
    """
    PostgreSQL implementation of IPermanentStorageBackend.

    Append-only storage for sessions, conversations, checkpoints.
    Auto-creates tables on first use if auto_create_tables=True.
    """

    def __init__(
        self,
        dsn: str | None = None,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        auto_create_tables: bool = True,
        min_pool_size: int = 1,
        max_pool_size: int = 5,
    ) -> None:
        self._explicit_dsn = dsn
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._auto_create_tables = auto_create_tables
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool: asyncpg.Pool | None = None

    @property
    def is_available(self) -> bool:
        return self._pool is not None

    def _resolve_pool_kwargs(self) -> dict[str, Any]:
        if self._explicit_dsn:
            return {"dsn": self._explicit_dsn}

        env_dsn = os.getenv("CONTEXT_PG_URL") or os.getenv("POSTGRES_URL")
        if env_dsn:
            return {"dsn": env_dsn}

        settings = get_settings()
        config: dict[str, Any] = dict(settings.database_config)
        if self._host:
            config["host"] = self._host
        if self._port is not None:
            config["port"] = self._port
        if self._user:
            config["user"] = self._user
        if self._password is not None:
            config["password"] = self._password
        if self._database:
            config["database"] = self._database
        elif os.getenv("CONTEXT_PG_DATABASE"):
            config["database"] = os.environ["CONTEXT_PG_DATABASE"]
        return config

    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool and optionally create tables."""
        try:
            pool_kwargs = self._resolve_pool_kwargs()
            self._pool = await asyncpg.create_pool(
                **pool_kwargs,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
            )
            if self._auto_create_tables:
                async with self._pool.acquire() as conn:
                    await self._ensure_tables(conn)
            logger.info("PostgresPermanentBackend initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Postgres permanent backend: {e}")
            self._pool = None
            return False

    async def close(self) -> None:
        """Close PostgreSQL connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("PostgresPermanentBackend closed")

    async def _ensure_tables(self, conn: asyncpg.Connection) -> None:
        for ddl in _CONTEXT_TABLE_DDL:
            await conn.execute(ddl)

    async def append_session_event(
        self,
        session_id: str,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_sessions (session_id, user_id, event_type, payload, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    session_id,
                    user_id,
                    event_type,
                    safe_json_dumps(payload),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_session_event failed: {e}")
            return False

    async def append_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_conversations (session_id, role, content, metadata, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    session_id,
                    role,
                    content,
                    safe_json_dumps(metadata or {}),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_conversation_message failed: {e}")
            return False

    async def append_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_checkpoints (thread_id, checkpoint_id, data, metadata, created_at)
                    VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
                    """,
                    thread_id,
                    checkpoint_id,
                    safe_json_dumps(checkpoint_data),
                    safe_json_dumps(metadata or {}),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_checkpoint failed: {e}")
            return False

    async def append_checkpoint_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: list[tuple],
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_checkpoint_writes (thread_id, checkpoint_id, task_id, writes_data, created_at)
                    VALUES ($1, $2, $3, $4::jsonb, $5)
                    """,
                    thread_id,
                    checkpoint_id,
                    task_id,
                    safe_json_dumps(writes_data),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_checkpoint_writes failed: {e}")
            return False

    async def append_conversation_session(
        self,
        session_key: str,
        session_data: dict[str, Any],
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_conversation_sessions (session_key, session_data, created_at)
                    VALUES ($1, $2::jsonb, $3)
                    """,
                    session_key,
                    safe_json_dumps(session_data),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_conversation_session failed: {e}")
            return False

    async def append_task_context_snapshot(
        self,
        session_id: str,
        context_data: dict[str, Any],
        created_at: str | None = None,
    ) -> bool:
        if self._pool is None:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO context_task_contexts (session_id, context_data, created_at)
                    VALUES ($1, $2::jsonb, $3)
                    """,
                    session_id,
                    safe_json_dumps(context_data),
                    parse_created_at(created_at),
                )
            return True
        except Exception as e:
            logger.error(f"Postgres append_task_context_snapshot failed: {e}")
            return False

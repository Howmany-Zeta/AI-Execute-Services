# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Postgres-backed temporal memory store (L1 optional SQL audit backend).

No graphiti_core imports. Search MVP: ILIKE on tm_fact + validity window.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from aiecs.config.config import Settings, get_settings
from aiecs.domain.temporal_memory.models import (
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)
from aiecs.infrastructure.persistence.permanent_backend_utils import safe_json_dumps

logger = logging.getLogger(__name__)

_TM_TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS tm_episode (
        episode_id UUID PRIMARY KEY,
        group_id VARCHAR(256) NOT NULL,
        name VARCHAR(512) NOT NULL,
        body_redacted TEXT NOT NULL,
        source VARCHAR(32) NOT NULL,
        reference_time TIMESTAMPTZ NOT NULL,
        metadata JSONB DEFAULT '{}',
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tm_episode_group_id ON tm_episode (group_id)",
    """
    CREATE TABLE IF NOT EXISTS tm_fact (
        fact_id UUID PRIMARY KEY,
        group_id VARCHAR(256) NOT NULL,
        text TEXT NOT NULL,
        valid_at TIMESTAMPTZ,
        invalid_at TIMESTAMPTZ,
        confidence REAL,
        source_episode_id UUID REFERENCES tm_episode (episode_id),
        metadata JSONB DEFAULT '{}'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tm_fact_group_valid ON tm_fact (group_id, valid_at)",
]


def _escape_ilike_pattern(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _row_to_fact(row: asyncpg.Record) -> TemporalFact:
    meta = row["metadata"]
    if isinstance(meta, str):
        meta = {}
    elif meta is None:
        meta = {}
    return TemporalFact(
        fact_id=str(row["fact_id"]),
        text=str(row["text"] or ""),
        group_id=str(row["group_id"] or ""),
        valid_at=_ensure_utc(row["valid_at"]),
        invalid_at=_ensure_utc(row["invalid_at"]),
        confidence=row["confidence"],
        source_episode_id=str(row["source_episode_id"]) if row["source_episode_id"] else None,
        metadata=dict(meta) if isinstance(meta, dict) else {},
    )


class PostgresTemporalMemoryStore:
    """
    SQL audit backend for :class:`TemporalMemoryStore`.

    Requires ``TM_POSTGRES_URL`` (or ``POSTGRES_URL`` fallback) when ``TM_BACKEND=postgres``.
    """

    store_id: str = "postgres"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._pool: asyncpg.Pool | None = None
        self._pending_ingest_tasks: set[asyncio.Task[None]] = set()

    def _resolve_dsn(self) -> str:
        dsn = (self._settings.tm_postgres_url or self._settings.postgres_url or "").strip()
        if not dsn:
            raise ValueError("TM_BACKEND=postgres requires TM_POSTGRES_URL or POSTGRES_URL to be set")
        return dsn

    async def initialize(self) -> None:
        if self._pool is not None:
            return
        dsn = self._resolve_dsn()
        self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        if self._settings.tm_postgres_auto_create_tables:
            async with self._pool.acquire() as conn:
                await self._ensure_tables(conn)
        else:
            async with self._pool.acquire() as conn:
                exists = await conn.fetchval(
                    """
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'tm_episode'
                    """
                )
                if not exists:
                    raise RuntimeError("tm_episode table missing; apply " "aiecs/scripts/migrations/postgres/002_temporal_memory_tables.sql " "or set TM_POSTGRES_AUTO_CREATE_TABLES=true")
        logger.info("PostgresTemporalMemoryStore initialized")

    async def _ensure_tables(self, conn: asyncpg.Connection) -> None:
        for ddl in _TM_TABLE_DDL:
            await conn.execute(ddl)

    async def close(self) -> None:
        pending = list(self._pending_ingest_tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        self._pending_ingest_tasks.clear()

        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        logger.debug("PostgresTemporalMemoryStore closed")

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgresTemporalMemoryStore not initialized; call initialize() first")
        return self._pool

    async def ingest_episode(self, request: IngestEpisodeRequest) -> IngestEpisodeResult:
        pool = self._require_pool()
        episode_id = request.episode_uuid or str(uuid.uuid4())
        fact_id = str(uuid.uuid4())
        ref_time = _ensure_utc(request.reference_time) or datetime.now(timezone.utc)
        name = (request.name or "")[:512]
        source = request.source.value if hasattr(request.source, "value") else str(request.source)
        metadata_json = safe_json_dumps(request.metadata or {})

        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO tm_episode (
                        episode_id, group_id, name, body_redacted, source,
                        reference_time, metadata
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5, $6, $7::jsonb)
                    """,
                    episode_id,
                    request.group_id,
                    name,
                    request.body,
                    source,
                    ref_time,
                    metadata_json,
                )
                await conn.execute(
                    """
                    INSERT INTO tm_fact (
                        fact_id, group_id, text, valid_at, source_episode_id, metadata
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5::uuid, '{}'::jsonb)
                    """,
                    fact_id,
                    request.group_id,
                    request.body,
                    ref_time,
                    episode_id,
                )

        return IngestEpisodeResult(
            episode_id=str(episode_id),
            group_id=request.group_id,
            facts_extracted=1,
            entity_count=0,
            edge_count=0,
        )

    async def ingest_episode_async(
        self,
        request: IngestEpisodeRequest,
        *,
        job_id: str | None = None,
    ) -> str:
        job = job_id or str(uuid.uuid4())
        task = asyncio.create_task(
            self._ingest_episode_background(request, job),
            name=f"postgres-ingest-{job[:8]}",
        )
        self._pending_ingest_tasks.add(task)
        task.add_done_callback(self._on_ingest_task_done)
        return job

    def _on_ingest_task_done(self, task: asyncio.Task[None]) -> None:
        self._pending_ingest_tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.warning("Postgres background ingest failed: %s", exc, exc_info=exc)

    async def _ingest_episode_background(
        self,
        request: IngestEpisodeRequest,
        job_id: str,
    ) -> None:
        _ = job_id
        await self.ingest_episode(request)

    async def search_facts(
        self,
        query: str,
        *,
        group_ids: list[str],
        limit: int = 10,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]:
        if not group_ids:
            return []
        q = (query or "").strip()
        if not q:
            return []

        if filters:
            if filters.entity_types:
                logger.debug(
                    "Postgres search ignores SearchFilters.entity_types=%s",
                    filters.entity_types,
                )
            if filters.excluded_entity_types:
                logger.debug("Postgres search ignores SearchFilters.excluded_entity_types")
            if filters.center_node_uuid:
                logger.debug("Postgres search ignores SearchFilters.center_node_uuid")

        pool = self._require_pool()
        as_of = _ensure_utc(valid_at) or datetime.now(timezone.utc)
        pattern = f"%{_escape_ilike_pattern(q)}%"

        rows = await pool.fetch(
            """
            SELECT fact_id, group_id, text, valid_at, invalid_at, confidence,
                   source_episode_id, metadata
            FROM tm_fact
            WHERE group_id = ANY($1::varchar[])
              AND text ILIKE $2 ESCAPE '\\'
              AND (valid_at IS NULL OR valid_at <= $3)
              AND (invalid_at IS NULL OR invalid_at > $3)
            ORDER BY valid_at DESC NULLS LAST
            LIMIT $4
            """,
            group_ids,
            pattern,
            as_of,
            limit,
        )
        return [_row_to_fact(row) for row in rows]

    async def get_fact(self, fact_id: str, *, group_ids: list[str]) -> TemporalFact | None:
        pool = self._require_pool()
        row = await pool.fetchrow(
            """
            SELECT fact_id, group_id, text, valid_at, invalid_at, confidence,
                   source_episode_id, metadata
            FROM tm_fact
            WHERE fact_id = $1::uuid
            """,
            fact_id,
        )
        if row is None:
            return None
        if group_ids and str(row["group_id"]) not in group_ids:
            return None
        return _row_to_fact(row)

    async def health_check(self) -> dict[str, Any]:
        try:
            pool = self._require_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return {"backend": "postgres", "ready": True}
        except Exception as exc:
            logger.warning("Postgres temporal memory health_check failed: %s", exc)
            return {"backend": "postgres", "ready": False, "error": str(exc)}

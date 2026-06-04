# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Temporal memory engine — orchestrates Port calls for agent plugins (no Graphiti imports)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from aiecs.config.config import Settings, get_settings
from aiecs.domain.temporal_memory.pii import redact_episode_body
from aiecs.domain.temporal_memory.search_cache import TemporalMemorySearchCache
from aiecs.infrastructure.temporal_memory.metrics import get_temporal_memory_metrics
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.temporal_memory.group_id import (
    build_group_ids,
    select_ingest_group_ids,
    select_search_group_ids,
)
from aiecs.domain.temporal_memory.models import (
    EpisodeSource,
    IngestEpisodeRequest,
    IngestEpisodeResult,
    SearchFilters,
    TemporalFact,
)
from aiecs.domain.temporal_memory.ports import TemporalMemoryStore

logger = logging.getLogger(__name__)

_DEFAULT_SESSION_KEY = "session_id"


class TemporalMemoryEngine:
    """L1 temporal memory orchestration over :class:`TemporalMemoryStore`."""

    def __init__(
        self,
        store: TemporalMemoryStore,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._store = store
        self._settings = settings or get_settings()
        # TM-067 mount: option A — cache lives on the engine, not the plugin.
        self._search_cache: TemporalMemorySearchCache | None = None
        if self._settings.tm_search_cache_enabled:
            self._search_cache = TemporalMemorySearchCache(
                maxsize=self._settings.tm_search_cache_max_size,
                ttl_seconds=self._settings.tm_search_cache_ttl_seconds,
            )

    @property
    def store(self) -> TemporalMemoryStore:
        return self._store

    @property
    def _backend(self) -> str:
        return str(getattr(self._store, "store_id", "unknown"))

    def resolve_group_ids(self, agent: Any, ctx: AgentPluginContext) -> list[str]:
        """Resolve Graphiti group_ids from agent + task context."""
        agent_id = str(getattr(agent, "agent_id", "unknown"))
        session_id = self._resolve_session_id(ctx) or "default"
        tenant_id = self._resolve_tenant_id(ctx)
        return build_group_ids(agent_id, session_id, tenant_id, settings=self._settings)

    async def search_for_task(
        self,
        task: dict[str, Any],
        group_ids: list[str],
        *,
        limit: int | None = None,
        valid_at: datetime | None = None,
        filters: SearchFilters | None = None,
    ) -> list[TemporalFact]:
        """Search temporal facts for a task query."""
        query = self._extract_search_query(task)
        if not query.strip():
            return []
        effective_limit = limit if limit is not None else self._settings.tm_search_limit
        search_group_ids = select_search_group_ids(group_ids, settings=self._settings)
        metrics = get_temporal_memory_metrics()

        if self._search_cache is None:
            with metrics.observe_search(self._backend, cache="off"):
                return await self._store.search_facts(
                    query,
                    group_ids=search_group_ids,
                    limit=effective_limit,
                    valid_at=valid_at,
                    filters=filters,
                )

        with metrics.observe_search(self._backend) as search_obs:
            facts, cache_hit = await self._search_cache.get_or_search(
                self._store,
                query,
                group_ids=search_group_ids,
                limit=effective_limit,
                valid_at=valid_at,
                filters=filters,
            )
            search_obs.set_cache("hit" if cache_hit else "miss")
        metrics.record_search_cache(hit=cache_hit)
        return facts

    async def ingest_from_task(
        self,
        ctx: AgentPluginContext,
        result: dict[str, Any],
    ) -> IngestEpisodeResult | None:
        """
        Ingest user + assistant turn from POST_TASK context.

        Failures are logged and swallowed (never propagated to ``execute_task``).
        """
        try:
            group_ids = self.resolve_group_ids(ctx.agent, ctx)
            if not group_ids:
                return None

            user_content = str(ctx.task_description or "").strip()
            assistant_content = str(result.get("final_response") or result.get("output") or "").strip()
            if not user_content and not assistant_content:
                return None

            body = self._format_episode_body(user_content, assistant_content)
            body = redact_episode_body(
                body,
                store_raw=self._settings.tm_store_raw_episode,
                max_chars=self._settings.tm_episode_body_max_chars,
            )
            task_id = str(ctx.task.get("task_id") or ctx.task.get("id") or "unknown")
            ingest_group_ids = select_ingest_group_ids(group_ids, settings=self._settings)
            metadata = {
                "task_id": task_id,
                "agent_id": str(getattr(ctx.agent, "agent_id", "")),
                "session_id": self._resolve_session_id(ctx),
                "group_ids": group_ids,
            }

            # POST_TASK non-blocking ingest is owned by TemporalMemoryPlugin + ingest_queue
            # when TM_INGEST_ASYNC=true. Engine always uses synchronous Port ingest here.
            last_result: IngestEpisodeResult | None = None
            for group_id in ingest_group_ids:
                request = IngestEpisodeRequest(
                    name=f"task-{task_id}",
                    body=body,
                    source_description="aiecs agent post_task",
                    reference_time=datetime.now(timezone.utc),
                    group_id=group_id,
                    source=EpisodeSource.MESSAGE,
                    metadata=metadata,
                )
                last_result = await self._store.ingest_episode(request)
            get_temporal_memory_metrics().record_ingest(self._backend, ok=True)
            return last_result
        except Exception as exc:
            get_temporal_memory_metrics().record_ingest(self._backend, ok=False)
            logger.warning(
                "Temporal memory ingest failed for agent %s: %s",
                getattr(ctx.agent, "agent_id", "unknown"),
                exc,
                exc_info=True,
            )
            return None

    def _resolve_session_id(self, ctx: AgentPluginContext) -> str | None:
        session_id = ctx.context.get(_DEFAULT_SESSION_KEY) or ctx.context.get("sessionId")
        if session_id:
            return str(session_id)
        task_session = ctx.task.get(_DEFAULT_SESSION_KEY) or ctx.task.get("sessionId")
        if task_session:
            return str(task_session)
        plugin_session = ctx.plugin_state.get("memory.session_id")
        if plugin_session:
            return str(plugin_session)
        return None

    def _resolve_tenant_id(self, ctx: AgentPluginContext) -> str | None:
        tenant = ctx.context.get("tenant_id") or ctx.context.get("tenantId")
        if tenant:
            return str(tenant)
        metadata = ctx.context.get("metadata")
        if isinstance(metadata, dict):
            meta_tenant = metadata.get("tenant_id") or metadata.get("tenantId")
            if meta_tenant:
                return str(meta_tenant)
        return None

    @staticmethod
    def _extract_search_query(task: dict[str, Any]) -> str:
        for key in ("query", "description", "task_description", "input", "prompt"):
            value = task.get(key)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _format_episode_body(user_content: str, assistant_content: str) -> str:
        parts: list[str] = []
        if user_content:
            parts.append(f"user: {user_content}")
        if assistant_content:
            parts.append(f"assistant: {assistant_content}")
        return "\n".join(parts)

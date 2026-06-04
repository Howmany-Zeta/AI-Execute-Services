# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
TemporalMemoryPlugin — L1 temporal facts ingest and retrieval (§0.6).

Separate from MemoryPlugin (L0). POST_TASK priority 85 runs after memory (80).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, ClassVar, cast

from aiecs.config.config import get_settings
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginMetadata
from aiecs.domain.temporal_memory.constants import (
    PLUGIN_STATE_EPISODE_ID,
    PLUGIN_STATE_FACTS_KEY,
    PLUGIN_STATE_GROUP_ID,
    PLUGIN_STATE_INGEST_JOB_ID,
)
from aiecs.domain.temporal_memory.engine import TemporalMemoryEngine
from aiecs.domain.temporal_memory.models import TemporalFact
from aiecs.infrastructure.temporal_memory import NoOpTemporalMemoryStore, create_temporal_memory_store
from aiecs.infrastructure.temporal_memory.metrics import get_temporal_memory_metrics
from aiecs.infrastructure.temporal_memory.store_factory import resolve_temporal_memory_backend
from aiecs.infrastructure.temporal_memory.ingest_queue import (
    acquire_temporal_memory_ingest_queue,
    get_temporal_memory_ingest_queue,
    release_temporal_memory_ingest_queue,
)
from aiecs.llm import LLMMessage

logger = logging.getLogger(__name__)

FACTS_HEADER = "TEMPORAL MEMORY FACTS:"


def format_facts_for_prompt(facts: list[TemporalFact], *, max_items: int = 10) -> str:
    """Format retrieved temporal facts for LLM context injection."""
    if not facts:
        return ""
    lines = [f"- {fact.text}" for fact in facts[:max_items] if fact.text]
    if not lines:
        return ""
    return f"{FACTS_HEADER}\n" + "\n".join(lines)


def _config_requests_temporal_memory(agent: Any) -> bool:
    agent_config = getattr(agent, "_config", None)
    if agent_config is None:
        return False
    return bool(getattr(agent_config, "temporal_memory_enabled", False))


class TemporalMemoryPlugin(BaseAgentPlugin):
    """Builtin L1 temporal memory plugin (Graphiti optional)."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="temporal_memory",
        version="1.0.0",
        description="Temporal memory ingest and fact retrieval (L1)",
        priority=85,
        default_enabled=False,
    )

    def _engine(self) -> TemporalMemoryEngine | None:
        engine = self._agent.temporal_memory_engine
        if isinstance(engine, TemporalMemoryEngine):
            return engine
        return None

    def _is_active(self) -> bool:
        if not self._config.enabled:
            return False
        if not self._agent.temporal_memory_enabled:
            return False
        return self._engine() is not None

    async def on_agent_init(self, ctx: AgentPluginContext) -> None:
        _ = ctx
        agent = self._agent
        agent.temporal_memory_enabled = False
        agent.temporal_memory_engine = None

        metrics = get_temporal_memory_metrics()
        if not _config_requests_temporal_memory(agent):
            metrics.set_backend_active("none")
            metrics.set_plugin_enabled(False)
            return None

        store = create_temporal_memory_store()
        if isinstance(store, NoOpTemporalMemoryStore):
            logger.debug(
                "TemporalMemoryPlugin disabled for agent %s (NoOp store)",
                getattr(agent, "agent_id", "?"),
            )
            metrics.set_backend_active("none")
            metrics.set_plugin_enabled(False)
            return None

        try:
            await store.initialize()
        except Exception as exc:
            logger.warning(
                "TemporalMemoryPlugin init failed for agent %s: %s",
                getattr(agent, "agent_id", "?"),
                exc,
            )
            try:
                await store.close()
            except Exception as close_exc:
                logger.debug(
                    "TemporalMemoryPlugin close after init failure: %s",
                    close_exc,
                )
            metrics.set_backend_active("none")
            metrics.set_plugin_enabled(False)
            return None

        agent.temporal_memory_engine = TemporalMemoryEngine(store)
        agent.temporal_memory_enabled = True
        metrics.set_backend_active(str(getattr(store, "store_id", resolve_temporal_memory_backend())))
        metrics.set_plugin_enabled(True)

        if get_settings().tm_ingest_async:
            await acquire_temporal_memory_ingest_queue()

        logger.debug(
            "TemporalMemoryPlugin enabled for agent %s (backend=%s)",
            getattr(agent, "agent_id", "?"),
            store.store_id,
        )
        return None

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        if not self._is_active():
            ctx.plugin_state.pop(PLUGIN_STATE_FACTS_KEY, None)
            return None

        engine = cast(TemporalMemoryEngine, self._engine())
        group_ids = engine.resolve_group_ids(self._agent, ctx)
        facts = await engine.search_for_task(ctx.task, group_ids)
        ctx.plugin_state[PLUGIN_STATE_FACTS_KEY] = facts
        return None

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list[LLMMessage],
    ) -> list[LLMMessage]:
        if not self._is_active():
            return messages
        if not self._config.options.get("inject_facts", True):
            return messages

        facts = ctx.plugin_state.get(PLUGIN_STATE_FACTS_KEY)
        if not isinstance(facts, list) or not facts:
            return messages

        max_items = int(self._config.options.get("facts_limit", 10))
        block = format_facts_for_prompt(facts, max_items=max_items)
        if not block:
            return messages

        return [*messages, LLMMessage(role="user", content=f"\n\n{block}")]

    def _write_ingest_plugin_state(
        self,
        ctx: AgentPluginContext,
        *,
        ingest_job_id: str,
        ingest_result: Any | None,
    ) -> None:
        """
        Expose ingest identifiers for Phase 4 MemoryPlugin metadata (TM-072).

        ``ingest_job_id`` is always set before async worker runs; ``episode_id`` only after ingest.
        """
        ctx.plugin_state[PLUGIN_STATE_INGEST_JOB_ID] = ingest_job_id
        if ingest_result is not None:
            episode_id = getattr(ingest_result, "episode_id", None)
            group_id = getattr(ingest_result, "group_id", None)
            if episode_id:
                ctx.plugin_state[PLUGIN_STATE_EPISODE_ID] = str(episode_id)
            if group_id:
                ctx.plugin_state[PLUGIN_STATE_GROUP_ID] = str(group_id)

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        if not self._is_active():
            return result

        engine = cast(TemporalMemoryEngine, self._engine())
        settings = get_settings()
        ingest_job_id = str(uuid.uuid4())
        ctx.plugin_state[PLUGIN_STATE_INGEST_JOB_ID] = ingest_job_id

        if settings.tm_ingest_async:
            queue = get_temporal_memory_ingest_queue()

            async def _work() -> None:
                ingest_result = await engine.ingest_from_task(ctx, result)
                self._write_ingest_plugin_state(
                    ctx,
                    ingest_job_id=ingest_job_id,
                    ingest_result=ingest_result,
                )
                await self._flush_memory_episode_bridge(ctx)

            await queue.enqueue(_work)
            return result

        ingest_result = await engine.ingest_from_task(ctx, result)
        self._write_ingest_plugin_state(
            ctx,
            ingest_job_id=ingest_job_id,
            ingest_result=ingest_result,
        )
        await self._flush_memory_episode_bridge(ctx)
        return result

    async def _flush_memory_episode_bridge(self, ctx: AgentPluginContext) -> None:
        """Persist L0 assistant metadata after L1 ingest (memory POST_TASK runs at priority 80)."""
        from aiecs.domain.agent.plugins.builtin.memory_plugin import (
            flush_pending_assistant_turn,
        )

        await flush_pending_assistant_turn(self._agent, ctx)

    async def on_agent_shutdown(self, ctx: AgentPluginContext) -> None:
        await self._flush_memory_episode_bridge(ctx)
        engine = self._engine()
        if engine is not None:
            try:
                await engine.store.close()
            except Exception as exc:
                logger.warning(
                    "TemporalMemoryPlugin store close failed: %s",
                    exc,
                )
        self._agent.temporal_memory_engine = None
        self._agent.temporal_memory_enabled = False
        get_temporal_memory_metrics().set_plugin_enabled(False)

        if get_settings().tm_ingest_async:
            await release_temporal_memory_ingest_queue()
        return None

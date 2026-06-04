"""MemoryPlugin ↔ L1 temporal episode_bridge (TM-079)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.memory_plugin import (
    MemoryPlugin,
    flush_pending_assistant_turn,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.temporal_memory.constants import (
    METADATA_TEMPORAL_EPISODE_ID,
    METADATA_TEMPORAL_GROUP_ID,
    METADATA_TEMPORAL_INGEST_JOB_ID,
    PLUGIN_STATE_EPISODE_ID,
    PLUGIN_STATE_GROUP_ID,
    PLUGIN_STATE_INGEST_JOB_ID,
    PLUGIN_STATE_PENDING_ASSISTANT,
    build_l0_temporal_metadata,
)


class _Agent(BaseAIAgent):
    async def _initialize(self) -> None:
        return None

    async def _shutdown(self) -> None:
        return None

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "final_response": "assistant reply"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


class _ContextEngine:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def add_conversation_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        self.calls.append(
            {
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            }
        )
        return True

    async def get_conversation_history(self, session_id: str, limit: int | None = None) -> list:
        _ = session_id, limit
        return []


@pytest.mark.asyncio
async def test_post_task_without_l1_writes_assistant_immediately() -> None:
    engine = _ContextEngine()
    agent = _Agent(
        agent_id="a1",
        name="A",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="g", memory_enabled=True, temporal_memory_enabled=False),
        tools=[],
    )
    agent._context_engine = engine
    plugin = MemoryPlugin(PluginConfig(name="memory", enabled=True, options={"persist": True}), agent)
    await plugin.on_agent_init(AgentPluginContext(agent=agent, task={}, context={}, task_description=""))
    ctx = AgentPluginContext(
        agent=agent,
        task={"description": "user question"},
        context={"session_id": "sess-1"},
        task_description="user question",
    )
    await plugin.on_post_task(ctx, {"final_response": "answer"})

    assert PLUGIN_STATE_PENDING_ASSISTANT not in ctx.plugin_state
    roles = [c["role"] for c in engine.calls]
    assert roles == ["user", "assistant"]
    assert engine.calls[-1]["metadata"] == {}


@pytest.mark.asyncio
async def test_post_task_with_l1_defers_assistant_until_flush() -> None:
    engine = _ContextEngine()
    agent = _Agent(
        agent_id="a2",
        name="A2",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="g", memory_enabled=True, temporal_memory_enabled=True),
        tools=[],
    )
    agent._context_engine = engine
    plugin = MemoryPlugin(PluginConfig(name="memory", enabled=True, options={"persist": True}), agent)
    await plugin.on_agent_init(AgentPluginContext(agent=agent, task={}, context={}, task_description=""))
    ctx = AgentPluginContext(
        agent=agent,
        task={"description": "user question"},
        context={"session_id": "sess-2"},
        task_description="user question",
    )
    await plugin.on_post_task(ctx, {"final_response": "answer"})
    assert ctx.plugin_state[PLUGIN_STATE_PENDING_ASSISTANT] == "answer"
    assert [c["role"] for c in engine.calls] == ["user"]

    ctx.plugin_state[PLUGIN_STATE_EPISODE_ID] = "ep-99"
    ctx.plugin_state[PLUGIN_STATE_GROUP_ID] = "aiecs:a2:sess-2"
    ctx.plugin_state[PLUGIN_STATE_INGEST_JOB_ID] = "job-99"
    agent._plugin_manager = MagicMock()
    agent._plugin_manager._plugins = {"memory": plugin}

    await flush_pending_assistant_turn(agent, ctx)

    assert PLUGIN_STATE_PENDING_ASSISTANT not in ctx.plugin_state
    assert len(engine.calls) == 2
    meta = engine.calls[-1]["metadata"]
    assert meta[METADATA_TEMPORAL_EPISODE_ID] == "ep-99"
    assert meta[METADATA_TEMPORAL_GROUP_ID] == "aiecs:a2:sess-2"
    assert meta[METADATA_TEMPORAL_INGEST_JOB_ID] == "job-99"


def test_build_l0_temporal_metadata_empty_when_no_l1() -> None:
    assert build_l0_temporal_metadata({}) == {}

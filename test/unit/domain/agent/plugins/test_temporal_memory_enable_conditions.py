"""Misconfiguration tests for temporal_memory enable gates."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import TemporalMemoryPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.defaults import derive_default_plugins
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.infrastructure.temporal_memory import NoOpTemporalMemoryStore


class _Agent(BaseAIAgent):
    async def _initialize(self) -> None:
        return None

    async def _shutdown(self) -> None:
        return None

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


class _GraphitiStubStore:
    store_id = "graphiti"

    async def initialize(self) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
def agent() -> _Agent:
    return _Agent(
        agent_id="cfg-agent",
        name="Cfg",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="cfg"),
        tools=[],
    )


def test_derive_disables_temporal_memory_without_config_flag(agent: _Agent) -> None:
    agent._config = AgentConfiguration(
        goal="cfg",
        temporal_memory_enabled=False,
    )
    with patch(
        "aiecs.domain.agent.plugins.defaults.create_temporal_memory_store",
        return_value=_GraphitiStubStore(),
    ):
        tm = next(c for c in derive_default_plugins(agent._config, agent) if c.name == "temporal_memory")
    assert tm.enabled is False


def test_derive_disables_when_store_is_noop_even_if_flag_set(agent: _Agent) -> None:
    agent._config = AgentConfiguration(goal="cfg", temporal_memory_enabled=True)
    with patch(
        "aiecs.domain.agent.plugins.defaults.create_temporal_memory_store",
        return_value=NoOpTemporalMemoryStore(),
    ):
        tm = next(c for c in derive_default_plugins(agent._config, agent) if c.name == "temporal_memory")
    assert tm.enabled is False


@pytest.mark.asyncio
async def test_plugin_init_skips_when_config_flag_false_despite_graphiti_store(agent: _Agent) -> None:
    agent._config = AgentConfiguration(
        goal="cfg",
        temporal_memory_enabled=False,
        plugins=[PluginConfig(name="temporal_memory", enabled=True)],
    )
    plugin = TemporalMemoryPlugin(PluginConfig(name="temporal_memory", enabled=True), agent)
    ctx = AgentPluginContext(
        agent=agent,
        task={"description": "t"},
        context={},
        task_description="t",
    )

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=_GraphitiStubStore(),
    ):
        await plugin.on_agent_init(ctx)

    assert agent.temporal_memory_enabled is False
    assert agent.temporal_memory_engine is None


@pytest.mark.asyncio
async def test_plugin_init_failure_closes_store(agent: _Agent) -> None:
    store = _GraphitiStubStore()
    store.initialize = AsyncMock(side_effect=ConnectionError("refused"))
    store.close = AsyncMock()
    agent._config = AgentConfiguration(goal="cfg", temporal_memory_enabled=True)

    plugin = TemporalMemoryPlugin(PluginConfig(name="temporal_memory", enabled=True), agent)
    ctx = AgentPluginContext(agent=agent, task={}, context={}, task_description="t")

    with patch(
        "aiecs.domain.agent.plugins.builtin.temporal_memory_plugin.create_temporal_memory_store",
        return_value=store,
    ):
        await plugin.on_agent_init(ctx)

    store.close.assert_awaited_once()
    assert agent.temporal_memory_engine is None

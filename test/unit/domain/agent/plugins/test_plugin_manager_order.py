"""Plugin manager phase ordering tests."""

from __future__ import annotations

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.collaboration_plugin import CollaborationPlugin
from aiecs.domain.agent.plugins.builtin.memory_plugin import MemoryPlugin
from aiecs.domain.agent.plugins.builtin.temporal_memory_plugin import TemporalMemoryPlugin
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry


class OrderTestAgent(BaseAIAgent):
    async def _initialize(self) -> None:
        return None

    async def _shutdown(self) -> None:
        return None

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def test_post_task_plugins_sorted_by_priority_ascending() -> None:
    """POST_TASK runs lower priority first — memory(80) before temporal_memory(85)."""
    agent = OrderTestAgent(
        agent_id="order-agent",
        name="Order",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="order test"),
        tools=[],
    )
    configs = [
        PluginConfig(name="temporal_memory", enabled=True, priority=85),
        PluginConfig(name="memory", enabled=True, priority=80),
    ]
    manager = PluginManager(agent, configs, registry=PluginRegistry.default())
    manager._plugins = {
        "memory": MemoryPlugin(PluginConfig(name="memory", enabled=True), agent),
        "temporal_memory": TemporalMemoryPlugin(
            PluginConfig(name="temporal_memory", enabled=True),
            agent,
        ),
    }
    manager._plugin_configs = configs

    order = [plugin.metadata.name for plugin in manager._plugins_for_phase(PluginPhase.POST_TASK)]
    assert order == ["memory", "temporal_memory"]


def test_post_task_memory_before_temporal_when_collaboration_also_enabled() -> None:
    """memory(80) and collaboration(80) both run before temporal_memory(85) on POST_TASK."""
    agent = OrderTestAgent(
        agent_id="order-agent-2",
        name="Order2",
        agent_type=AgentType.DEVELOPER,
        config=AgentConfiguration(goal="order test"),
        tools=[],
    )
    agent._collaboration_enabled = True
    configs = [
        PluginConfig(name="memory", enabled=True),
        PluginConfig(name="collaboration", enabled=True),
        PluginConfig(name="temporal_memory", enabled=True),
    ]
    manager = PluginManager(agent, configs, registry=PluginRegistry.default())
    manager._plugins = {
        "memory": MemoryPlugin(PluginConfig(name="memory", enabled=True), agent),
        "collaboration": CollaborationPlugin(
            PluginConfig(name="collaboration", enabled=True),
            agent,
        ),
        "temporal_memory": TemporalMemoryPlugin(
            PluginConfig(name="temporal_memory", enabled=True),
            agent,
        ),
    }
    manager._plugin_configs = configs

    order = [plugin.metadata.name for plugin in manager._plugins_for_phase(PluginPhase.POST_TASK)]
    assert order.index("memory") < order.index("temporal_memory")
    assert order.index("collaboration") < order.index("temporal_memory")

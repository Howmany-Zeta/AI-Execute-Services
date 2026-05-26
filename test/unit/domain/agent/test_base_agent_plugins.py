"""
Unit tests for PluginManager wiring on BaseAIAgent (P2-05, §8.1).
"""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.defaults import derive_default_plugins, derive_plugin_configs
from aiecs.tools.base_tool import BaseTool


class ParityStubTool(BaseTool):
    """Minimal tool for schema generation in unit tests."""

    async def run_async(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        return {"status": "ok", "operation": operation}


class PluginWireTestAgent(BaseAIAgent):
    """Concrete BaseAIAgent for plugin lifecycle wiring tests."""

    async def _initialize(self, **kwargs) -> None:
        await super()._initialize(**kwargs)

    async def _shutdown(self) -> None:
        await super()._shutdown()

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def _by_name(plugins):
    return {plugin.name: plugin for plugin in plugins}


@pytest.fixture
def plugin_wire_config() -> AgentConfiguration:
    return AgentConfiguration(goal="Base agent plugin wiring test", skills_enabled=False)


@pytest.fixture
def agent_with_tools(plugin_wire_config: AgentConfiguration) -> PluginWireTestAgent:
    return PluginWireTestAgent(
        agent_id="base-agent-plugin-test",
        name="Base Agent Plugin Test",
        agent_type=AgentType.DEVELOPER,
        config=plugin_wire_config,
        tools={
            "parity_alpha": ParityStubTool(tool_name="parity_alpha"),
            "parity_beta": ParityStubTool(tool_name="parity_beta"),
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseAgentPluginWiring:
    """PluginManager is created in __init__ and initialized via agent.initialize()."""

    def test_plugin_manager_created_without_initialize(self, agent_with_tools: PluginWireTestAgent) -> None:
        assert agent_with_tools._plugin_manager is not None
        assert agent_with_tools._plugin_registry is not None
        assert agent_with_tools._plugin_manager.get_plugin("tool") is None

    async def test_initialize_with_tools_loads_tool_plugin(
        self, agent_with_tools: PluginWireTestAgent
    ) -> None:
        await agent_with_tools.initialize()

        tool_plugin = agent_with_tools._plugin_manager.get_plugin("tool")
        assert tool_plugin is not None
        assert len(agent_with_tools._tool_schemas) >= 2

        await agent_with_tools.shutdown()

    def test_plugins_empty_equals_full_derive(self, agent_with_tools: PluginWireTestAgent) -> None:
        """plugins=[] on config matches Phase 1 full derive via _resolve_plugin_configs."""
        config = agent_with_tools._config.model_copy(update={"plugins": []})
        merged, merge_log = agent_with_tools._resolve_plugin_configs()
        expected = derive_default_plugins(config, agent_with_tools)

        assert _by_name(merged) == _by_name(expected)
        assert any("plugins=[]" in entry for entry in merge_log)

        direct, _ = derive_plugin_configs(config, agent_with_tools)
        assert _by_name(merged) == _by_name(direct)

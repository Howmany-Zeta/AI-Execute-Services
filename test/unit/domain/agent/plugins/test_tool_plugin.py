"""
Unit tests for ToolPlugin business logic (§7.3, P2-01).
"""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.builtin.tool_plugin import (
    PLUGIN_STATE_SCHEMAS_KEY,
    ToolPlugin,
    filter_tool_schemas,
)
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.tools.base_tool import BaseTool


class ParityStubTool(BaseTool):
    """Minimal tool for schema generation in unit tests."""

    async def run_async(self, operation: str, **kwargs: Any) -> dict[str, Any]:
        return {"status": "ok", "operation": operation}


class ToolTestAgent(BaseAIAgent):
    """BaseAIAgent with tool dict input for ToolPlugin tests."""

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        return {"success": True, "output": "ok"}

    async def process_message(self, message: str, sender_id: str | None = None) -> dict:
        return {"response": "ok"}


def _make_ctx(agent: BaseAIAgent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=agent,
        task={"description": "tool plugin test"},
        context={},
        task_description="tool plugin test",
    )


@pytest.fixture
def tool_test_agent() -> ToolTestAgent:
    config = AgentConfiguration(goal="Tool plugin test")
    agent = ToolTestAgent(
        agent_id="tool-plugin-test",
        name="Tool Plugin Test",
        agent_type=AgentType.DEVELOPER,
        config=config,
        tools={
            "parity_alpha": ParityStubTool(tool_name="parity_alpha"),
            "parity_beta": ParityStubTool(tool_name="parity_beta"),
        },
    )
    agent._tool_schemas = []
    agent._tool_instances = {}
    return agent


@pytest.mark.unit
class TestFilterToolSchemas:
    def test_empty_allowed_tools_means_no_filter(self) -> None:
        schemas = [{"name": "a"}, {"name": "b"}]
        assert filter_tool_schemas(schemas, []) == schemas

    def test_underscore_tool_name_exact_match(self) -> None:
        schemas = [{"name": "parity_alpha"}, {"name": "parity_beta"}]
        assert filter_tool_schemas(schemas, ["parity_alpha"]) == [{"name": "parity_alpha"}]

    def test_tool_operation_suffix_match(self) -> None:
        schemas = [{"name": "search"}, {"name": "search_run"}]
        assert filter_tool_schemas(schemas, ["search"]) == schemas


@pytest.mark.unit
@pytest.mark.asyncio
class TestToolPluginAgentInit:
    async def test_agent_init_populates_tool_schemas(self, tool_test_agent: ToolTestAgent) -> None:
        registry = PluginRegistry()
        registry.register("tool", ToolPlugin, origin="registry")
        manager = PluginManager(
            tool_test_agent,
            [PluginConfig(name="tool", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        assert len(tool_test_agent._tool_schemas) >= 2
        assert len(tool_test_agent._tool_instances) == 2
        schema_names = {s.get("name") for s in tool_test_agent._tool_schemas}
        assert "parity_alpha" in schema_names
        assert "parity_beta" in schema_names


@pytest.mark.unit
@pytest.mark.asyncio
class TestToolPluginPreMainLoop:
    async def test_allowed_tools_subset_reduces_schemas(self, tool_test_agent: ToolTestAgent) -> None:
        registry = PluginRegistry()
        registry.register("tool", ToolPlugin, origin="registry")
        manager = PluginManager(
            tool_test_agent,
            [
                PluginConfig(
                    name="tool",
                    enabled=True,
                    options={"allowed_tools": ["parity_alpha"]},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()
        full_count = len(tool_test_agent._tool_schemas)
        assert full_count >= 2

        ctx = _make_ctx(tool_test_agent)
        await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert len(tool_test_agent._tool_schemas) < full_count
        assert len(tool_test_agent._tool_schemas) >= 1
        assert {s.get("name") for s in tool_test_agent._tool_schemas} == {"parity_alpha"}

        assert ctx.plugin_state[PLUGIN_STATE_SCHEMAS_KEY] == tool_test_agent._tool_schemas

    async def test_empty_allowed_tools_does_not_filter(self, tool_test_agent: ToolTestAgent) -> None:
        registry = PluginRegistry()
        registry.register("tool", ToolPlugin, origin="registry")
        manager = PluginManager(
            tool_test_agent,
            [
                PluginConfig(
                    name="tool",
                    enabled=True,
                    options={"allowed_tools": []},
                ),
            ],
            registry=registry,
        )
        await manager.initialize()
        before = list(tool_test_agent._tool_schemas)

        ctx = _make_ctx(tool_test_agent)
        await manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=ctx)

        assert tool_test_agent._tool_schemas == before

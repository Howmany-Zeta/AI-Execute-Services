"""
Unit tests for BaseAgentPlugin.
"""

import inspect

import pytest

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.protocols import AgentPlugin


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseAgentPlugin:
    """Test BaseAgentPlugin defaults and protocol compliance."""

    @pytest.fixture
    def plugin_config(self) -> PluginConfig:
        return PluginConfig(name="minimal", enabled=True)

    def test_subclass_with_single_hook_override(self, mock_agent, plugin_config):
        """Subclass overriding only on_pre_task can be instantiated."""

        class MinimalPlugin(BaseAgentPlugin):
            metadata: PluginMetadata = PluginMetadata(
                name="minimal",
                version="1.0.0",
                description="Minimal test plugin",
            )

            def __init__(self, config: PluginConfig, agent) -> None:
                super().__init__(config, agent)
                self.pre_task_called = False

            async def on_pre_task(self, ctx: AgentPluginContext) -> None:
                self.pre_task_called = True

        plugin = MinimalPlugin(plugin_config, mock_agent)
        assert plugin._config.name == "minimal"
        assert plugin._agent is mock_agent
        assert plugin.metadata.name == "minimal"

    def test_satisfies_agent_plugin_protocol(self, mock_agent, plugin_config):
        """Structural subtyping: instance is usable as AgentPlugin."""

        class MinimalPlugin(BaseAgentPlugin):
            metadata: PluginMetadata = PluginMetadata(
                name="minimal",
                version="1.0.0",
                description="Minimal test plugin",
            )

        plugin: AgentPlugin = MinimalPlugin(plugin_config, mock_agent)
        assert hasattr(plugin, "metadata")
        for hook in (
            "on_agent_init",
            "on_agent_shutdown",
            "on_pre_task",
            "on_build_messages",
            "on_pre_main_loop",
            "on_post_task",
            "on_iteration_start",
            "on_iteration_end",
        ):
            assert callable(getattr(plugin, hook))
            assert inspect.iscoroutinefunction(getattr(plugin, hook))

    async def test_default_hook_behaviors(self, mock_agent, plugin_config):
        """Default hooks are no-ops with pass-through where specified."""
        plugin = BaseAgentPlugin(plugin_config, mock_agent)
        ctx = AgentPluginContext(
            agent=mock_agent,
            task={"description": "test"},
            context={},
            task_description="test",
        )

        await plugin.on_agent_init(ctx)
        await plugin.on_pre_task(ctx)

        messages = [{"role": "user", "content": "hi"}]
        assert await plugin.on_build_messages(ctx, messages) is messages

        assert await plugin.on_pre_main_loop(ctx) is None

        result = {"final_response": "ok"}
        assert await plugin.on_post_task(ctx, result) is result

        await plugin.on_iteration_start(ctx, 0)
        await plugin.on_iteration_end(ctx, 0, {"type": "thought"})

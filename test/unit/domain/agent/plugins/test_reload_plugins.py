"""
Unit tests for BaseAIAgent.reload_plugins() (P2-06, §8.1, §9.7).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.models import AgentState
from aiecs.domain.agent.plugins.errors import PluginReloadErrorException
from aiecs.domain.agent.plugins.models import PluginConfig


@pytest.mark.unit
@pytest.mark.asyncio
class TestReloadPlugins:
    """Explicit reload with BUSY / in-flight task rejection."""

    async def test_busy_state_rejects_reload(self, mock_agent):
        await mock_agent.initialize()
        mock_agent._transition_state(AgentState.BUSY)

        with pytest.raises(PluginReloadErrorException) as exc_info:
            await mock_agent.reload_plugins()

        assert exc_info.value.error.type == "plugin_reload_error"
        assert mock_agent._state == AgentState.BUSY

    async def test_current_task_id_rejects_reload(self, mock_agent):
        await mock_agent.initialize()
        mock_agent._current_task_id = "task-in-flight"

        with pytest.raises(PluginReloadErrorException):
            await mock_agent.reload_plugins()

        assert mock_agent._current_task_id == "task-in-flight"

    async def test_active_reload_replaces_manager_and_reflects_config(self, mock_agent):
        await mock_agent.initialize()
        old_manager = mock_agent._plugin_manager
        assert old_manager.get_plugin("memory") is not None

        mock_agent._config = mock_agent._config.model_copy(
            update={"plugins": [PluginConfig(name="memory", enabled=False)]},
        )

        result = await mock_agent.reload_plugins()

        assert mock_agent._plugin_manager is not old_manager
        assert mock_agent._plugin_manager.get_plugin("memory") is None
        assert "memory@builtin" in result.disabled

    async def test_initialize_force_reload_delegates_to_reload_plugins(self, mock_agent):
        await mock_agent.initialize()
        old_manager = mock_agent._plugin_manager

        mock_agent._config = mock_agent._config.model_copy(
            update={"plugins": [PluginConfig(name="memory", enabled=False)]},
        )

        await mock_agent._initialize(force_reload_plugins=True)

        assert mock_agent._plugin_manager is not old_manager
        assert mock_agent._plugin_manager.get_plugin("memory") is None

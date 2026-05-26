"""
Unit tests for agent plugin context and short-circuit results.
"""

from unittest.mock import MagicMock

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult


@pytest.mark.unit
class TestAgentPluginContext:
    """Test AgentPluginContext lifecycle fields."""

    def test_plugin_state_is_distinct_per_context(self, mock_agent):
        """Each context gets its own plugin_state dict (§5.4)."""
        ctx_a = AgentPluginContext(
            agent=mock_agent,
            task={"task_id": "a"},
            context={},
            task_description="Task A",
        )
        ctx_b = AgentPluginContext(
            agent=mock_agent,
            task={"task_id": "b"},
            context={},
            task_description="Task B",
        )
        assert ctx_a.plugin_state is not ctx_b.plugin_state
        ctx_a.plugin_state["memory.history"] = [1]
        assert "memory.history" not in ctx_b.plugin_state

    def test_messages_list_is_distinct_per_context(self, mock_agent):
        """Each context gets its own messages list."""
        ctx_a = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="A",
        )
        ctx_b = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="B",
        )
        assert ctx_a.messages is not ctx_b.messages

    def test_get_plugin_delegates_to_plugin_manager(self, mock_agent):
        """get_plugin delegates to agent._plugin_manager.get_plugin."""
        plugin = object()
        manager = MagicMock()
        manager.get_plugin.return_value = plugin
        mock_agent._plugin_manager = manager

        ctx = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="delegate test",
        )
        assert ctx.get_plugin("memory") is plugin
        manager.get_plugin.assert_called_once_with("memory")

    def test_get_plugin_returns_none_without_manager(self, mock_agent):
        """Missing _plugin_manager yields None."""
        ctx = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="no manager",
        )
        assert ctx.get_plugin("memory") is None


@pytest.mark.unit
class TestPluginShortCircuitResult:
    """Test PluginShortCircuitResult fields (§4.4)."""

    def test_required_fields(self):
        """result and source_plugin_id are required."""
        short = PluginShortCircuitResult(
            result={"final_response": "done", "iterations": 0},
            source_plugin_id="knowledge@builtin",
        )
        assert short.result["final_response"] == "done"
        assert short.source_plugin_id == "knowledge@builtin"
        assert short.reason is None

    def test_optional_reason(self):
        """reason is optional."""
        short = PluginShortCircuitResult(
            result={"output": "graph answer"},
            source_plugin_id="knowledge@builtin",
            reason="high_confidence_graph_match",
        )
        assert short.reason == "high_confidence_graph_match"

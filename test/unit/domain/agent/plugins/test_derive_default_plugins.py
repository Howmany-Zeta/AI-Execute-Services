"""
Unit tests for derive_default_plugins (§6.3.2, §6.4).
"""

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.defaults import derive_default_plugins


def _by_name(plugins):
    return {plugin.name: plugin for plugin in plugins}


@pytest.mark.unit
class TestDeriveDefaultPlugins:
    """Test legacy configuration → default PluginConfig list."""

    def test_example_a_skills_disabled_tools_present(self, mock_agent, plugin_agent_config):
        """Example A: skills_enabled=False, tools non-empty → memory+tool on, skill off."""
        config = plugin_agent_config.model_copy(update={"skills_enabled": False})
        agent = mock_agent
        agent._tools_input = ["search"]

        plugins = derive_default_plugins(config, agent)
        by_name = _by_name(plugins)

        assert by_name["memory"].enabled is True
        assert by_name["skill"].enabled is False
        assert by_name["tool"].enabled is True
        assert by_name["custom_reasoning"].enabled is False
        assert by_name["knowledge"].enabled is False

        assert by_name["memory"].options["capacity"] == config.memory_capacity
        assert by_name["tool"].options["allowed_tools"] == []
        assert by_name["tool"].options["tool_selection_strategy"] == "llm_based"

    def test_example_b_skills_enabled_with_names(self, mock_agent):
        """Example B: skills_enabled + skill_names → memory, skill, tool enabled."""
        config = AgentConfiguration(
            goal="Plugin test agent",
            skills_enabled=True,
            skill_names=["python-testing"],
            skill_auto_register_tools=False,
            skill_inject_script_paths=True,
            skill_context_max_skills=3,
        )
        mock_agent._tools_input = ["search"]

        plugins = derive_default_plugins(config, mock_agent)
        by_name = _by_name(plugins)

        assert by_name["memory"].enabled is True
        assert by_name["skill"].enabled is True
        assert by_name["tool"].enabled is True

        assert by_name["skill"].options["skill_names"] == ["python-testing"]
        assert by_name["skill"].options["auto_register_tools"] is False
        assert by_name["skill"].options["inject_script_paths"] is True
        assert by_name["skill"].options["context_max_skills"] == 3

    def test_memory_disabled_when_memory_enabled_false(self, mock_agent, plugin_agent_config):
        config = plugin_agent_config.model_copy(update={"memory_enabled": False})
        mock_agent._tools_input = ["search"]

        by_name = _by_name(derive_default_plugins(config, mock_agent))
        assert by_name["memory"].enabled is False

    def test_tool_disabled_when_no_tools(self, mock_agent, plugin_agent_config):
        mock_agent._tools_input = None

        by_name = _by_name(derive_default_plugins(plugin_agent_config, mock_agent))
        assert by_name["tool"].enabled is False

    def test_skill_disabled_when_skill_names_empty(self, mock_agent, plugin_agent_config):
        config = plugin_agent_config.model_copy(
            update={"skills_enabled": True, "skill_names": []},
        )
        mock_agent._tools_input = ["search"]

        by_name = _by_name(derive_default_plugins(config, mock_agent))
        assert by_name["skill"].enabled is False

    def test_memory_ttl_in_options_when_set(self, mock_agent, plugin_agent_config):
        config = plugin_agent_config.model_copy(update={"memory_ttl_seconds": 3600})
        mock_agent._tools_input = ["search"]

        by_name = _by_name(derive_default_plugins(config, mock_agent))
        assert by_name["memory"].options["ttl_seconds"] == 3600

    def test_returns_all_builtin_plugin_names(self, mock_agent, plugin_agent_config):
        mock_agent._tools_input = ["search"]
        names = [p.name for p in derive_default_plugins(plugin_agent_config, mock_agent)]
        assert names == ["memory", "skill", "tool", "knowledge", "collaboration", "custom_reasoning"]

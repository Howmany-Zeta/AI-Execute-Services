"""
Unit tests for derive_plugin_configs (§6.3.1–§6.3.4).
"""

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.defaults import derive_default_plugins, derive_plugin_configs
from aiecs.domain.agent.plugins.models import PluginConfig


def _by_name(plugins):
    return {plugin.name: plugin for plugin in plugins}


@pytest.mark.unit
class TestDerivePluginConfigs:
    """Test config.plugins merge with derive_default_plugins."""

    @pytest.fixture
    def agent_with_tools(self, mock_agent):
        mock_agent._tools_input = ["search"]
        return mock_agent

    def test_empty_plugins_equals_full_derive(self, agent_with_tools, plugin_agent_config):
        """plugins=[] is equivalent to derive_default_plugins."""
        config = plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False})

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        expected = derive_default_plugins(config, agent_with_tools)

        assert _by_name(merged) == _by_name(expected)
        assert any("plugins=[]" in entry for entry in merge_log)

    def test_partial_memory_disabled_skill_tool_derived(self, agent_with_tools, plugin_agent_config):
        """Explicit memory disabled; skill and tool still derived."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [PluginConfig(name="memory", enabled=False)],
                "skills_enabled": False,
            },
        )

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        by_name = _by_name(merged)

        assert by_name["memory"].enabled is False
        assert by_name["skill"].enabled is False
        assert by_name["tool"].enabled is True
        assert any("filled missing 'tool'" in entry for entry in merge_log)
        assert any("explicit 'memory'" in entry for entry in merge_log)

    def test_explicit_skill_enabled_overrides_skills_enabled_false(
        self, agent_with_tools, plugin_agent_config
    ):
        """Explicit skill enabled wins over skills_enabled=False legacy flag."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [PluginConfig(name="skill", enabled=True)],
                "skills_enabled": False,
                "skill_names": [],
            },
        )

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        by_name = _by_name(merged)

        assert by_name["skill"].enabled is True
        assert any("explicit 'skill'" in entry for entry in merge_log)

    def test_merge_log_is_meaningful(self, agent_with_tools, plugin_agent_config):
        config = plugin_agent_config.model_copy(
            update={"plugins": [PluginConfig(name="memory", enabled=False)]},
        )

        _, merge_log = derive_plugin_configs(config, agent_with_tools)

        assert len(merge_log) >= 2
        assert all(isinstance(entry, str) and len(entry) > 0 for entry in merge_log)

    def test_stable_sort_order(self, agent_with_tools, plugin_agent_config):
        config = plugin_agent_config.model_copy(update={"plugins": []})
        mock_agent = agent_with_tools
        mock_agent._tools_input = ["search"]

        merged, _ = derive_plugin_configs(config, mock_agent)
        names = [p.name for p in merged]

        assert names.index("tool") < names.index("skill") < names.index("memory")
        assert names[-1] == "custom_reasoning"

    def test_explicit_replaces_derive_same_name(self, agent_with_tools, plugin_agent_config):
        """Explicit entry fully replaces derive entry for the same name."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="tool",
                        enabled=True,
                        options={"allowed_tools": ["search"], "tool_selection_strategy": "rule_based"},
                    ),
                ],
            },
        )

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        by_name = _by_name(merged)

        assert by_name["tool"].options["allowed_tools"] == ["search"]
        assert by_name["tool"].options["tool_selection_strategy"] == "rule_based"
        assert any("replaces derive" in entry or "explicit 'tool'" in entry for entry in merge_log)

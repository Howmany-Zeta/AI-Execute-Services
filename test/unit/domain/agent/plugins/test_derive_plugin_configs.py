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
        assert names.index("memory") < names.index("temporal_memory")
        assert "knowledge" in names

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


@pytest.mark.unit
class TestDerivePluginConfigsTaskContext:
    """Priority 3 task/context overlays (§6.3.1, P2-04)."""

    @pytest.fixture
    def agent_with_tools(self, mock_agent):
        mock_agent._tools_input = ["search"]
        return mock_agent

    def test_task_plugins_disables_skill_over_config_enabled(
        self, agent_with_tools, plugin_agent_config
    ):
        """Config enables skill; task.plugins disables skill for this request."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="skill",
                        enabled=True,
                        options={"skill_names": ["python-testing"]},
                    ),
                ],
                "skills_enabled": False,
            },
        )
        task = {"plugins": [PluginConfig(name="skill", enabled=False)]}

        merged, merge_log = derive_plugin_configs(
            config, agent_with_tools, task=task, context=None
        )
        by_name = _by_name(merged)

        assert by_name["skill"].enabled is False
        assert any("task.plugins" in entry and "skill" in entry for entry in merge_log)

    def test_task_plugins_enables_audit_plugin(
        self, agent_with_tools, plugin_agent_config
    ):
        """task.plugins can add a registered extension plugin for the current task."""
        config = plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False})
        task = {
            "plugins": [
                PluginConfig(name="audit", enabled=True, options={"mode": "strict"}),
            ],
        }

        merged, merge_log = derive_plugin_configs(
            config, agent_with_tools, task=task, context=None
        )
        by_name = _by_name(merged)

        assert "audit" in by_name
        assert by_name["audit"].enabled is True
        assert by_name["audit"].options["mode"] == "strict"
        assert any("task.plugins" in entry and "audit" in entry for entry in merge_log)

    def test_context_plugins_override_task_for_same_name(
        self, agent_with_tools, plugin_agent_config
    ):
        """context.plugins wins over task.plugins when both set the same name."""
        config = plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False})
        task = {"plugins": [PluginConfig(name="memory", enabled=False)]}
        context = {"plugins": [PluginConfig(name="memory", enabled=True)]}

        merged, merge_log = derive_plugin_configs(
            config, agent_with_tools, task=task, context=context
        )
        by_name = _by_name(merged)

        assert by_name["memory"].enabled is True
        assert any("task.plugins" in e for e in merge_log)
        assert any("context.plugins" in e for e in merge_log)

    def test_partial_config_list_still_works_with_task_overlay(
        self, agent_with_tools, plugin_agent_config
    ):
        """§6.3.3 partial config + task overlay: memory disabled at config, tool still derived."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [PluginConfig(name="memory", enabled=False)],
                "skills_enabled": False,
            },
        )
        task = {"plugins": [PluginConfig(name="tool", enabled=False)]}

        merged, merge_log = derive_plugin_configs(config, agent_with_tools, task=task)
        by_name = _by_name(merged)

        assert by_name["memory"].enabled is False
        assert by_name["tool"].enabled is False
        assert by_name["skill"].enabled is False
        assert any("filled missing 'tool'" in entry for entry in merge_log)
        assert any("task.plugins" in entry and "tool" in entry for entry in merge_log)


@pytest.mark.unit
class TestDerivePluginConfigsPolicy:
    """Priority 1 policy_plugins merge (§6.3.1, P3-04)."""

    @pytest.fixture
    def agent_with_tools(self, mock_agent):
        mock_agent._tools_input = ["search"]
        return mock_agent

    def test_policy_disables_memory_task_cannot_reenable(
        self, agent_with_tools, plugin_agent_config
    ):
        """Policy ``enabled=false`` on memory; task ``enabled=true`` stays disabled."""
        config = plugin_agent_config.model_copy(
            update={
                "memory_enabled": True,
                "plugins": [],
                "skills_enabled": False,
                "policy_plugins": [PluginConfig(name="memory", enabled=False)],
            },
        )
        task = {"plugins": [PluginConfig(name="memory", enabled=True)]}

        merged, merge_log = derive_plugin_configs(
            config, agent_with_tools, task=task, context=None
        )
        by_name = _by_name(merged)

        assert by_name["memory"].enabled is False
        assert any("policy.plugins" in entry for entry in merge_log)
        assert any(
            "task.plugins: rejected" in entry and "memory" in entry for entry in merge_log
        )

    def test_policy_locked_options_subset(
        self, agent_with_tools, plugin_agent_config
    ):
        """Policy locks ``allowed_tools``; config may set other tool options."""
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="tool",
                        enabled=True,
                        options={
                            "allowed_tools": ["calculator"],
                            "tool_selection_strategy": "rule_based",
                        },
                    ),
                ],
                "skills_enabled": False,
                "policy_plugins": [
                    PluginConfig(
                        name="tool",
                        enabled=True,
                        options={"allowed_tools": ["search"]},
                        locked_options=["allowed_tools"],
                    ),
                ],
            },
        )

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        by_name = _by_name(merged)

        assert by_name["tool"].options["allowed_tools"] == ["search"]
        assert by_name["tool"].options["tool_selection_strategy"] == "rule_based"
        assert any(
            "policy.plugins: locked options" in entry and "allowed_tools" in entry
            for entry in merge_log
        )

    def test_merge_log_contains_policy_source(
        self, agent_with_tools, plugin_agent_config
    ):
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [],
                "skills_enabled": False,
                "policy_plugins": [
                    PluginConfig(name="skill", enabled=False, policy_locked=True),
                ],
            },
        )
        task = {
            "plugins": [
                PluginConfig(
                    name="skill",
                    enabled=True,
                    options={"skill_names": ["python-testing"]},
                ),
            ],
        }

        _, merge_log = derive_plugin_configs(config, agent_with_tools, task=task)
        policy_entries = [entry for entry in merge_log if "policy.plugins" in entry]

        assert len(policy_entries) >= 1
        assert any("rejected" in entry and "policy.plugins" in entry for entry in merge_log)


@pytest.mark.unit
class TestDerivePluginConfigsKnowledge:
    """Knowledge legacy options and enabled derivation (§6.4, E-05)."""

    @pytest.fixture
    def agent_with_tools(self, mock_agent):
        mock_agent._tools_input = ["search"]
        return mock_agent

    def test_knowledge_disabled_without_graph_store(self, agent_with_tools, plugin_agent_config):
        config = plugin_agent_config.model_copy(
            update={
                "retrieval_strategy": "vector",
                "enable_knowledge_caching": False,
                "max_context_size": 12,
                "plugins": [],
                "skills_enabled": False,
            },
        )

        merged, _ = derive_plugin_configs(config, agent_with_tools)
        knowledge = _by_name(merged)["knowledge"]

        assert knowledge.enabled is False
        assert knowledge.options["retrieval_strategy"] == "vector"
        assert knowledge.options["enable_knowledge_caching"] is False
        assert knowledge.options["max_context_size"] == 12
        assert "graph_store_ref" not in knowledge.options

    def test_knowledge_enabled_when_graph_store_present(self, agent_with_tools, plugin_agent_config):
        agent_with_tools.graph_store = object()

        merged, _ = derive_plugin_configs(
            plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False}),
            agent_with_tools,
        )
        knowledge = _by_name(merged)["knowledge"]

        assert knowledge.enabled is True
        assert knowledge.options["graph_store_ref"] == "object"

    def test_knowledge_disabled_when_graph_reasoning_off(self, agent_with_tools, plugin_agent_config):
        agent_with_tools.graph_store = object()
        agent_with_tools.enable_graph_reasoning = False

        merged, _ = derive_plugin_configs(
            plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False}),
            agent_with_tools,
        )

        assert _by_name(merged)["knowledge"].enabled is False

    def test_knowledge_explicit_enabled_without_graph_store(self, agent_with_tools, plugin_agent_config):
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="knowledge",
                        enabled=True,
                        options={"retrieval_strategy": "graph"},
                    ),
                ],
                "skills_enabled": False,
            },
        )

        merged, merge_log = derive_plugin_configs(config, agent_with_tools)
        knowledge = _by_name(merged)["knowledge"]

        assert knowledge.enabled is True
        assert knowledge.options["retrieval_strategy"] == "graph"
        assert any("explicit 'knowledge'" in entry for entry in merge_log)

    def test_knowledge_graph_store_ref_uses_store_id(self, agent_with_tools, plugin_agent_config):
        class StubGraphStore:
            store_id = "kg-main"

        agent_with_tools.graph_store = StubGraphStore()

        merged, _ = derive_plugin_configs(
            plugin_agent_config.model_copy(update={"plugins": [], "skills_enabled": False}),
            agent_with_tools,
        )

        assert _by_name(merged)["knowledge"].options["graph_store_ref"] == "kg-main"

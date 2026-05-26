"""
Unit tests for builtin plugin stubs (P1-11).
"""

import pytest

from aiecs.domain.agent.plugins.builtin import MemoryPlugin, SkillPlugin, ToolPlugin
from aiecs.domain.agent.plugins.models import PluginConfig


@pytest.mark.unit
class TestBuiltinPluginStubs:
    """Verify builtin stubs instantiate with expected metadata."""

    @pytest.mark.parametrize(
        ("plugin_cls", "expected_name", "expected_priority"),
        [
            (SkillPlugin, "skill", 90),
            (MemoryPlugin, "memory", 80),
            (ToolPlugin, "tool", 100),
        ],
    )
    def test_stub_instantiates_with_metadata(
        self,
        mock_agent,
        plugin_cls,
        expected_name,
        expected_priority,
    ):
        config = PluginConfig(name=expected_name, enabled=True)
        plugin = plugin_cls(config, mock_agent)

        assert plugin.metadata.name == expected_name
        assert plugin.metadata.priority == expected_priority
        assert plugin._config.name == expected_name

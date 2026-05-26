"""
Unit tests for AgentConfiguration.plugins (§6.2, T-14).
"""

import json

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig


@pytest.mark.unit
class TestAgentConfigurationPlugins:
    """Test plugins field on AgentConfiguration."""

    def test_default_plugins_empty_list(self):
        """Default configuration has plugins=[] (derive defaults, not disable all)."""
        config = AgentConfiguration()
        assert config.plugins == []
        assert config.policy_plugins == []

    def test_existing_defaults_unchanged(self):
        """Legacy fields remain unchanged when plugins is omitted."""
        config = AgentConfiguration()
        assert config.memory_enabled is True
        assert config.skills_enabled is False
        assert config.temperature == 0.7

    def test_plugins_json_round_trip(self):
        """plugins array serializes and deserializes via JSON."""
        original = AgentConfiguration(
            goal="Test agent",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(
                    name="skill",
                    enabled=True,
                    priority=90,
                    options={"skill_names": ["python-testing"]},
                ),
            ],
        )
        payload = original.model_dump()
        restored = AgentConfiguration.model_validate(json.loads(json.dumps(payload)))

        assert len(restored.plugins) == 2
        assert restored.plugins[0].name == "memory"
        assert restored.plugins[0].enabled is False
        assert restored.plugins[1].name == "skill"
        assert restored.plugins[1].enabled is True
        assert restored.plugins[1].priority == 90
        assert restored.plugins[1].options["skill_names"] == ["python-testing"]

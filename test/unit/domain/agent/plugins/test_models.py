"""
Unit tests for agent plugin models.
"""

import json

import pytest
from pydantic import ValidationError

from aiecs.domain.agent.plugins.errors import PluginInitError
from aiecs.domain.agent.plugins.models import (
    PluginConfig,
    PluginLoadResult,
    PluginMetadata,
    PluginPhase,
)


@pytest.mark.unit
class TestPluginPhase:
    """Test PluginPhase enum."""

    EXPECTED_VALUES = {
        "agent_init",
        "agent_shutdown",
        "pre_task",
        "build_messages",
        "pre_main_loop",
        "on_iteration_start",
        "on_iteration_end",
        "post_task",
    }

    def test_all_phase_values_present(self):
        """All eight lifecycle phases are defined (§5.2)."""
        assert len(PluginPhase) == 8
        assert {phase.value for phase in PluginPhase} == self.EXPECTED_VALUES

    def test_phase_members(self):
        """Enum members map to design doc names."""
        assert PluginPhase.AGENT_INIT.value == "agent_init"
        assert PluginPhase.POST_TASK.value == "post_task"


@pytest.mark.unit
class TestPluginMetadata:
    """Test PluginMetadata frozen dataclass."""

    def test_defaults(self):
        """Default priority and default_enabled."""
        meta = PluginMetadata(
            name="skill",
            version="1.0.0",
            description="Skill plugin",
        )
        assert meta.priority == 100
        assert meta.default_enabled is True

    def test_frozen(self):
        """Metadata is immutable."""
        meta = PluginMetadata(name="tool", version="1.0.0", description="Tool plugin")
        with pytest.raises(AttributeError):
            meta.priority = 50  # type: ignore[misc]


@pytest.mark.unit
class TestPluginConfig:
    """Test PluginConfig Pydantic model."""

    def test_defaults(self):
        """Default enabled and options."""
        config = PluginConfig(name="memory")
        assert config.enabled is True
        assert config.priority is None
        assert config.options == {}

    def test_priority_optional(self):
        """Priority may be None or an override."""
        assert PluginConfig(name="tool", priority=None).priority is None
        assert PluginConfig(name="tool", priority=50).priority == 50

    def test_name_must_be_non_empty(self):
        """Reject empty or whitespace-only names."""
        with pytest.raises(ValidationError):
            PluginConfig(name="")
        with pytest.raises(ValidationError):
            PluginConfig(name="   ")

    def test_json_round_trip(self):
        """Serialize and deserialize via JSON."""
        original = PluginConfig(
            name="skill",
            enabled=False,
            priority=90,
            options={"skill_names": ["python-testing"]},
        )
        payload = original.model_dump()
        restored = PluginConfig.model_validate(json.loads(json.dumps(payload)))
        assert restored == original


@pytest.mark.unit
class TestPluginLoadResult:
    """Test PluginLoadResult."""

    def test_defaults(self):
        """Empty enabled/disabled/errors lists by default."""
        result = PluginLoadResult()
        assert result.enabled == []
        assert result.disabled == []
        assert result.errors == []

    def test_populated_lists(self):
        """Store plugin IDs and typed PluginError records."""
        result = PluginLoadResult(
            enabled=["skill@builtin", "tool@builtin"],
            disabled=["memory@builtin"],
            errors=[PluginInitError(message="failed", plugin_id="skill@builtin")],
        )
        assert len(result.enabled) == 2
        assert len(result.disabled) == 1
        assert len(result.errors) == 1
        assert result.errors[0].type == "plugin_init_error"

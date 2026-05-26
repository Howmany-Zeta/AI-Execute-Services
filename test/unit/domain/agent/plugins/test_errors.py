"""
Unit tests for typed plugin errors.
"""

import json

import pytest

from aiecs.domain.agent.plugins.errors import (
    PluginConfigError,
    PluginDependencyError,
    PluginError,
    PluginErrorException,
    PluginHookError,
    PluginInitError,
    get_plugin_error_message,
)
from aiecs.domain.agent.plugins.models import PluginPhase


@pytest.mark.unit
class TestPluginErrorTypes:
    """Each subclass exposes a unique discriminated type."""

    def test_init_error_type(self):
        error = PluginInitError(message="init failed", plugin_id="skill@builtin")
        assert error.type == "plugin_init_error"

    def test_config_error_type(self):
        error = PluginConfigError(message="bad config")
        assert error.type == "plugin_config_error"

    def test_hook_error_type_and_phase(self):
        error = PluginHookError(
            message="hook failed",
            phase=PluginPhase.BUILD_MESSAGES,
            plugin_id="audit@registry",
        )
        assert error.type == "plugin_hook_error"
        assert error.phase == PluginPhase.BUILD_MESSAGES

    def test_dependency_error_type(self):
        error = PluginDependencyError(message="missing dep", plugin_id="fmt@registry")
        assert error.type == "plugin_dependency_error"

    def test_types_are_unique(self):
        errors = [
            PluginInitError(message="a"),
            PluginConfigError(message="b"),
            PluginHookError(message="c", phase=PluginPhase.PRE_TASK),
            PluginDependencyError(message="d"),
        ]
        assert len({e.type for e in errors}) == 4


@pytest.mark.unit
class TestPluginErrorSerialization:
    """Errors serialize type for metrics / streaming."""

    def test_model_dump_includes_type(self):
        error = PluginConfigError(message="invalid id", plugin_id="@foo")
        payload = error.model_dump()
        assert payload["type"] == "plugin_config_error"
        assert payload["message"] == "invalid id"
        assert payload["plugin_id"] == "@foo"

    def test_json_round_trip_preserves_type(self):
        error = PluginHookError(
            message="timeout",
            phase=PluginPhase.ON_ITERATION_END,
        )
        restored = PluginHookError.model_validate(json.loads(json.dumps(error.model_dump())))
        assert restored.type == "plugin_hook_error"
        assert restored.phase == PluginPhase.ON_ITERATION_END


@pytest.mark.unit
class TestGetPluginErrorMessage:
    """Test get_plugin_error_message helper."""

    def test_includes_plugin_id_and_type(self):
        error = PluginInitError(message="boom", plugin_id="tool@builtin")
        text = get_plugin_error_message(error)
        assert "boom" in text
        assert "plugin_id=tool@builtin" in text
        assert "type=plugin_init_error" in text


@pytest.mark.unit
class TestPluginErrorException:
    """Test exception wrapper for raise semantics."""

    def test_wraps_config_error(self):
        with pytest.raises(PluginErrorException) as exc_info:
            raise PluginErrorException(PluginConfigError(message="bad"))
        assert isinstance(exc_info.value.error, PluginConfigError)
        assert exc_info.value.error.type == "plugin_config_error"

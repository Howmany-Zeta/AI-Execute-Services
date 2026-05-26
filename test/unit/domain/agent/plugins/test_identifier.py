"""
Unit tests for plugin identifier parsing and formatting.
"""

import pytest

from aiecs.domain.agent.plugins.errors import (
    PluginConfigError,
    PluginConfigErrorException,
)
from aiecs.domain.agent.plugins.identifier import (
    PluginIdentifier,
    PluginOrigin,
    format_plugin_id,
    parse_plugin_identifier,
)


@pytest.mark.unit
class TestFormatPluginId:
    """Test format_plugin_id."""

    def test_builtin(self):
        assert format_plugin_id("skill", PluginOrigin.BUILTIN) == "skill@builtin"

    def test_registry_default(self):
        assert format_plugin_id("audit") == "audit@registry"

    def test_registry_explicit(self):
        assert format_plugin_id("audit", "registry") == "audit@registry"

    def test_empty_name_raises(self):
        with pytest.raises(PluginConfigErrorException, match="name"):
            format_plugin_id("")


@pytest.mark.unit
class TestParsePluginIdentifier:
    """Test parse_plugin_identifier."""

    def test_full_id_builtin(self):
        ident = parse_plugin_identifier("skill@builtin")
        assert ident == PluginIdentifier(name="skill", origin=PluginOrigin.BUILTIN)
        assert ident.format() == "skill@builtin"

    def test_full_id_registry(self):
        ident = parse_plugin_identifier("audit@registry")
        assert ident == PluginIdentifier(name="audit", origin=PluginOrigin.REGISTRY)

    def test_short_name_defaults_to_registry(self):
        ident = parse_plugin_identifier("audit")
        assert ident == PluginIdentifier(name="audit", origin=PluginOrigin.REGISTRY)
        assert ident.format() == "audit@registry"

    def test_same_name_different_origin(self):
        builtin = parse_plugin_identifier("skill@builtin")
        config = parse_plugin_identifier("skill@config")
        assert builtin.name == config.name == "skill"
        assert builtin.origin != config.origin
        assert builtin.origin == PluginOrigin.BUILTIN
        assert config.origin == PluginOrigin.CONFIG

    @pytest.mark.parametrize(
        "invalid_id",
        ["@foo", "foo@", "foo@a@b", "", "   "],
    )
    def test_invalid_formats_raise(self, invalid_id: str):
        with pytest.raises(PluginConfigErrorException) as exc_info:
            parse_plugin_identifier(invalid_id)
        assert isinstance(exc_info.value.error, PluginConfigError)
        assert exc_info.value.error.type == "plugin_config_error"

    def test_unknown_origin_raises(self):
        with pytest.raises(PluginConfigErrorException) as exc_info:
            parse_plugin_identifier("skill@unknown")
        assert exc_info.value.error.type == "plugin_config_error"
        assert "unknown plugin origin" in exc_info.value.error.message

    def test_whitespace_trimmed(self):
        ident = parse_plugin_identifier("  skill@builtin  ")
        assert ident.name == "skill"
        assert ident.origin == PluginOrigin.BUILTIN

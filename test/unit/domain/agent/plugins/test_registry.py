"""
Unit tests for PluginRegistry (§5.5, §6.3.5).
"""

import pytest

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.defaults import derive_plugin_configs
from aiecs.domain.agent.plugins.errors import (
    PluginConfigError,
    PluginConfigErrorException,
    PluginErrorException,
    PluginInitError,
)
from aiecs.domain.agent.plugins.identifier import PluginOrigin
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.registry import PluginRegistry


class AuditPlugin(BaseAgentPlugin):
    """Test registry plugin."""

    metadata = PluginMetadata(
        name="audit",
        version="1.0.0",
        description="Audit test plugin",
    )


class BrokenPlugin(BaseAgentPlugin):
    """Plugin that fails construction."""

    metadata = PluginMetadata(
        name="broken",
        version="0.0.0",
        description="Broken plugin",
    )

    def __init__(self, config: PluginConfig, agent) -> None:
        raise RuntimeError("construction failed")


@pytest.mark.unit
class TestPluginRegistry:
    """T-01: register + create; unknown name; init errors."""

    def test_register_and_create_succeeds(self, mock_agent):
        registry = PluginRegistry()
        registry.register("audit", AuditPlugin)

        config = PluginConfig(name="audit", enabled=True)
        plugin = registry.create(config, mock_agent)

        assert isinstance(plugin, AuditPlugin)
        assert plugin._config is config
        assert plugin._agent is mock_agent

    def test_unknown_name_raises_plugin_config_error(self, mock_agent):
        registry = PluginRegistry()
        registry.register("audit", AuditPlugin)

        with pytest.raises(PluginConfigErrorException) as exc_info:
            registry.create(PluginConfig(name="missing", enabled=True), mock_agent)

        assert isinstance(exc_info.value.error, PluginConfigError)
        assert exc_info.value.error.type == "plugin_config_error"
        assert "unknown plugin" in exc_info.value.error.message

    def test_create_failure_raises_plugin_init_error(self, mock_agent):
        registry = PluginRegistry()
        registry.register("broken", BrokenPlugin)

        with pytest.raises(PluginErrorException) as exc_info:
            registry.create(PluginConfig(name="broken", enabled=True), mock_agent)

        assert isinstance(exc_info.value.error, PluginInitError)
        assert exc_info.value.error.plugin_id == "broken@registry"
        assert exc_info.value.error.type == "plugin_init_error"

    def test_duplicate_register_overwrites(self, mock_agent):
        class OtherAuditPlugin(BaseAgentPlugin):
            metadata = PluginMetadata(
                name="audit",
                version="2.0.0",
                description="Other audit",
            )

        registry = PluginRegistry()
        registry.register("audit", AuditPlugin)
        registry.register("audit", OtherAuditPlugin)

        plugin = registry.create(PluginConfig(name="audit", enabled=True), mock_agent)
        assert isinstance(plugin, OtherAuditPlugin)

    def test_list_registered_includes_origin(self):
        registry = PluginRegistry()
        registry.register("audit", AuditPlugin, origin=PluginOrigin.REGISTRY)

        identifiers = registry.list_registered()
        assert len(identifiers) == 1
        assert identifiers[0].name == "audit"
        assert identifiers[0].origin == PluginOrigin.REGISTRY
        assert identifiers[0].format() == "audit@registry"


@pytest.mark.unit
class TestPluginRegistryDefault:
    """T-13: PluginRegistry.default() builtin dual-track."""

    def test_default_lists_builtin_plugins(self):
        registry = PluginRegistry.default()
        formatted = {ident.format() for ident in registry.list_registered()}

        assert formatted == {
            "collaboration@builtin",
            "knowledge@builtin",
            "memory@builtin",
            "skill@builtin",
            "tool@builtin",
        }

    def test_default_builtin_metadata_default_enabled(self):
        registry = PluginRegistry.default()

        for name in ("skill", "memory", "tool"):
            entry = registry._entries[name]
            assert entry.origin == PluginOrigin.BUILTIN
            assert entry.metadata.default_enabled is True

        knowledge_entry = registry._entries["knowledge"]
        assert knowledge_entry.origin == PluginOrigin.BUILTIN
        assert knowledge_entry.metadata.default_enabled is False
        assert knowledge_entry.metadata.priority == 40

        collaboration_entry = registry._entries["collaboration"]
        assert collaboration_entry.origin == PluginOrigin.BUILTIN
        assert collaboration_entry.metadata.default_enabled is False
        assert collaboration_entry.metadata.priority == 80

    def test_default_registry_also_accepts_registry_origin(self, mock_agent):
        registry = PluginRegistry.default()
        registry.register("audit", AuditPlugin, origin=PluginOrigin.REGISTRY)

        formatted = {ident.format() for ident in registry.list_registered()}
        assert "audit@registry" in formatted
        assert "tool@builtin" in formatted

        plugin = registry.create(PluginConfig(name="audit", enabled=True), mock_agent)
        assert isinstance(plugin, AuditPlugin)


@pytest.mark.unit
class TestPluginRegistryEnablement:
    """T-02: register does not auto-enable plugins."""

    def test_register_only_without_config_entry_not_in_derived_configs(
        self, mock_agent, plugin_agent_config
    ):
        """Registry registration alone does not add plugin to derive_plugin_configs."""
        registry = PluginRegistry()
        registry.register("audit", AuditPlugin)
        assert registry.list_registered()

        mock_agent._tools_input = ["search"]
        merged, _ = derive_plugin_configs(plugin_agent_config, mock_agent)
        names = {plugin.name for plugin in merged}

        assert "audit" not in names
        assert "memory" in names
        assert "tool" in names

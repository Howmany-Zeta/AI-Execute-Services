"""
Unit tests for external plugin manifest loading (§9.1, P3-06).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.exceptions import AgentInitializationError
from aiecs.domain.agent.models import AgentConfiguration, AgentType
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.errors import (
    PluginDependencyError,
    PluginDependencyErrorException,
)
from aiecs.domain.agent.plugins.identifier import PluginOrigin
from aiecs.domain.agent.plugins.manifest_loader import (
    collect_manifests_from_config,
    load_manifest_from_path,
    sort_manifests_by_dependencies,
)
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.domain.agent.plugins.schema.manifest import PluginManifest
from test.unit.domain.agent.plugins.conftest import MockPluginAgent

_FIXTURES_DIR = Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "plugins"
_SAMPLE_MANIFEST = _FIXTURES_DIR / "sample_aiecs-plugin.yaml"


class SampleAuditPlugin(BaseAgentPlugin):
    """External plugin matching ``sample_aiecs-plugin.yaml``."""

    metadata = PluginMetadata(
        name="sample-audit",
        version="1.0.0",
        description="Sample audit plugin",
        priority=200,
    )

    async def on_pre_task(self, ctx) -> None:
        ctx.plugin_state["sample_audit"] = True


@pytest.mark.unit
class TestLoadManifestFromPath:
    def test_load_sample_yaml_fixture(self) -> None:
        manifest = load_manifest_from_path(_SAMPLE_MANIFEST)
        assert manifest.name == "sample-audit"
        assert manifest.version == "1.0.0"
        assert [dep.name for dep in manifest.dependencies] == ["memory@builtin"]
        assert manifest.phases == [PluginPhase.PRE_TASK, PluginPhase.POST_TASK]

    def test_load_from_directory(self) -> None:
        manifest = load_manifest_from_path(_FIXTURES_DIR / "sample-plugin-dir")
        assert manifest.name == "sample-audit"

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_manifest_from_path(_FIXTURES_DIR / "missing.yaml")


@pytest.mark.unit
class TestRegisterFromManifest:
    def test_register_and_create_with_enabled_config(self, mock_agent) -> None:
        manifest = load_manifest_from_path(_SAMPLE_MANIFEST)
        registry = PluginRegistry.default()
        registry.register_from_manifest(manifest, SampleAuditPlugin)

        entry = registry.get_entry("sample-audit")
        assert entry is not None
        assert entry.origin == PluginOrigin.CONFIG
        assert entry.metadata.default_enabled is False
        assert entry.manifest == manifest

        plugin = registry.create(
            PluginConfig(name="sample-audit", enabled=True, options={"tag": "test"}),
            mock_agent,
        )
        assert isinstance(plugin, SampleAuditPlugin)

    def test_manifest_default_enabled_false(self) -> None:
        manifest = load_manifest_from_path(_SAMPLE_MANIFEST)
        registry = PluginRegistry()
        registry.register_from_manifest(manifest, SampleAuditPlugin)
        assert registry.get_entry("sample-audit").metadata.default_enabled is False


@pytest.mark.unit
class TestManifestDependencies:
    def test_sort_resolves_against_registry(self) -> None:
        manifest = load_manifest_from_path(_SAMPLE_MANIFEST)
        registry = PluginRegistry.default()
        ordered = sort_manifests_by_dependencies([manifest], registry)
        assert ordered == [manifest]

    def test_missing_dependency_raises(self) -> None:
        manifest = PluginManifest.model_validate(
            {
                "name": "needs-missing",
                "dependencies": ["not-registered@registry"],
            }
        )
        with pytest.raises(PluginDependencyErrorException) as exc_info:
            sort_manifests_by_dependencies([manifest], PluginRegistry())
        assert isinstance(exc_info.value.error, PluginDependencyError)
        assert "not-registered" in exc_info.value.error.message


@pytest.mark.unit
@pytest.mark.asyncio
class TestAgentManifestInitialize:
    async def test_manifest_register_without_config_enable_not_initialized(
        self, plugin_agent_config: AgentConfiguration
    ) -> None:
        manifest = load_manifest_from_path(_SAMPLE_MANIFEST)
        registry = PluginRegistry.default()
        registry.register_from_manifest(manifest, SampleAuditPlugin)

        config = plugin_agent_config.model_copy(
            update={"plugin_manifest_paths": [str(_SAMPLE_MANIFEST)]},
        )
        agent = MockPluginAgent(
            agent_id="manifest-test-agent",
            name="Manifest Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            tools=[],
            plugin_registry=registry,
        )

        await agent.initialize()

        assert agent._loaded_plugin_manifests == [manifest]
        assert agent._plugin_manager is not None
        assert not agent._plugin_manager.is_enabled("sample-audit")
        assert agent._plugin_manager.get_plugin("sample-audit") is None

    async def test_manifest_paths_validate_dependencies_on_initialize(
        self, plugin_agent_config: AgentConfiguration
    ) -> None:
        orphan_path = _FIXTURES_DIR / "orphan_aiecs-plugin.yaml"
        orphan_path.write_text(
            "name: orphan\ndependencies:\n  - missing@registry\n",
            encoding="utf-8",
        )
        try:
            config = plugin_agent_config.model_copy(
                update={"plugin_manifest_paths": [str(orphan_path)]},
            )
            agent = MockPluginAgent(
                agent_id="manifest-dep-agent",
                name="Manifest Dep Agent",
                agent_type=AgentType.CONVERSATIONAL,
                config=config,
                tools=[],
            )
            with pytest.raises(AgentInitializationError, match="missing@registry"):
                await agent.initialize()
        finally:
            orphan_path.unlink(missing_ok=True)

    async def test_resolve_hook_registers_manifest_plugin(self, plugin_agent_config: AgentConfiguration) -> None:
        class ManifestHookAgent(MockPluginAgent):
            def _resolve_manifest_plugin_class(self, manifest: PluginManifest):
                if manifest.name == "sample-audit":
                    return SampleAuditPlugin
                return None

        config = plugin_agent_config.model_copy(
            update={
                "plugin_manifest_paths": [str(_SAMPLE_MANIFEST)],
                "plugins": [
                    PluginConfig(
                        name="sample-audit",
                        enabled=True,
                        options={"tag": "init"},
                    ),
                ],
            },
        )
        agent = ManifestHookAgent(
            agent_id="manifest-hook-agent",
            name="Manifest Hook Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            tools=[],
            plugin_registry=PluginRegistry.default(),
        )

        await agent.initialize()

        assert agent._plugin_manager is not None
        assert agent._plugin_manager.is_enabled("sample-audit")
        assert isinstance(agent._plugin_manager.get_plugin("sample-audit"), SampleAuditPlugin)


@pytest.mark.unit
class TestCollectManifestsFromConfig:
    def test_plugin_manifest_paths_and_extra_plugin_dirs(self, plugin_agent_config: AgentConfiguration) -> None:
        config = plugin_agent_config.model_copy(
            update={
                "plugin_manifest_paths": [str(_SAMPLE_MANIFEST)],
                "extra_plugin_dirs": [str(_FIXTURES_DIR)],
            },
        )
        manifests = collect_manifests_from_config(config)
        assert len(manifests) == 1
        assert manifests[0][0].name == "sample-audit"

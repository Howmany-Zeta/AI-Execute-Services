"""
Unit tests for manifest hook merge in derive_plugin_configs (H0-05).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.defaults import derive_plugin_configs
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.schema.manifest import PluginManifest


@pytest.mark.unit
class TestManifestHookMerge:
    def test_scenario_a_manifest_only_auto_enables_hook(self, mock_agent, plugin_agent_config) -> None:
        manifest = PluginManifest(
            name="security-pack",
            version="1.0.0",
            hooks="./hooks.json",
        )
        merged, merge_log = derive_plugin_configs(
            plugin_agent_config,
            mock_agent,
            manifests=[manifest],
            manifest_dirs={"security-pack": Path("/tmp/pack")},
        )
        hook = next(plugin for plugin in merged if plugin.name == "hook")
        assert hook.enabled is True
        assert any("auto-enabled hook" in entry for entry in merge_log)

    def test_scenario_b_appends_to_existing_hook_config(self, mock_agent, plugin_agent_config) -> None:
        manifest = PluginManifest(name="team-pack", hooks={"pre_tool_use": []})
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=True,
                        options={"paths": ["/existing/hooks.json"]},
                    )
                ]
            }
        )
        merged, merge_log = derive_plugin_configs(
            config,
            mock_agent,
            manifests=[manifest],
        )
        hook_configs = [plugin for plugin in merged if plugin.name == "hook"]
        assert len(hook_configs) == 1
        assert str(Path("/existing/hooks.json").resolve()) in hook_configs[0].options["paths"]
        assert "inline_hooks" in hook_configs[0].options
        assert any("merged into existing hook" in entry for entry in merge_log)

    def test_scenario_c_disabled_warns(self, mock_agent, plugin_agent_config) -> None:
        manifest = PluginManifest(name="security-pack", hooks="./hooks.json")
        config = plugin_agent_config.model_copy(
            update={"plugins": [PluginConfig(name="hook", enabled=False)]},
        )
        _, merge_log = derive_plugin_configs(
            config,
            mock_agent,
            manifests=[manifest],
            manifest_dirs={"security-pack": Path("/tmp/pack")},
        )
        assert any("disabled" in entry for entry in merge_log)

    def test_scenario_d_path_dedupe(self, mock_agent, plugin_agent_config) -> None:
        manifest = PluginManifest(name="pack", hooks="./hooks.json")
        config = plugin_agent_config.model_copy(
            update={
                "plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=True,
                        options={"paths": ["/tmp/pack/hooks.json"]},
                    )
                ]
            },
        )
        merged, _ = derive_plugin_configs(
            config,
            mock_agent,
            manifests=[manifest],
            manifest_dirs={"pack": Path("/tmp/pack")},
        )
        hook = next(plugin for plugin in merged if plugin.name == "hook")
        resolved = str(Path("/tmp/pack/hooks.json").resolve())
        assert hook.options["paths"].count(resolved) == 1

    def test_scenario_f_policy_prepend(self, mock_agent, plugin_agent_config) -> None:
        manifest = PluginManifest(name="pack", hooks="./team.json")
        config = plugin_agent_config.model_copy(
            update={
                "policy_plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=True,
                        policy_locked=True,
                        options={"paths": ["/policy/org.json"]},
                    )
                ],
                "plugins": [
                    PluginConfig(
                        name="hook",
                        enabled=False,
                        options={"paths": ["/agent/local.json"]},
                    )
                ],
            },
        )
        merged, _ = derive_plugin_configs(
            config,
            mock_agent,
            manifests=[manifest],
            manifest_dirs={"pack": Path("/tmp/pack")},
        )
        hook = next(plugin for plugin in merged if plugin.name == "hook")
        assert hook.enabled is True
        paths = hook.options["paths"]
        assert paths[0] == str(Path("/policy/org.json").resolve())

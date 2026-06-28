"""
Unit tests for HookPlugin and registry integration (H0-03, H0-08).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.prompt_client import AgentLLMHookPromptClient
from aiecs.domain.agent.plugins.manager import PluginManager
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse


@pytest.mark.unit
class TestHookPluginRegistry:
    def test_default_registry_resolves_hook_factory(self, mock_agent) -> None:
        registry = PluginRegistry.default()
        entry = registry.get_entry("hook")
        assert entry is not None
        assert entry.factory is HookPlugin
        assert entry.metadata.default_enabled is False

        plugin = registry.create(PluginConfig(name="hook", enabled=False), mock_agent)
        assert isinstance(plugin, HookPlugin)
        assert plugin.is_enabled is False

    @pytest.mark.asyncio
    async def test_disabled_plugin_dispatch_returns_empty(self, mock_agent) -> None:
        plugin = HookPlugin(PluginConfig(name="hook", enabled=False), mock_agent)
        result = await plugin.dispatch(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "x"})
        assert result.results == []
        assert plugin.registry is None

    @pytest.mark.asyncio
    async def test_enabled_plugin_builds_registry_from_inline_hooks(self, mock_agent) -> None:
        config = PluginConfig(
            name="hook",
            enabled=True,
            options={
                "allow_command_hooks": True,
                "inline_hooks": {
                    "pre_tool_use": [
                        {"type": "http", "url": "https://example.com/pre"},
                    ]
                },
            },
        )
        plugin = HookPlugin(config, mock_agent)
        from aiecs.domain.agent.plugins.context import AgentPluginContext

        ctx = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="hello",
        )
        await plugin.on_agent_init(ctx)
        assert plugin.registry is not None
        assert len(plugin.registry.get_hooks(AgentHookEvent.PRE_TOOL_USE)) == 1

    @pytest.mark.asyncio
    async def test_prompt_hook_uses_agent_llm_client_through_plugin(self, mock_agent) -> None:
        llm_client = AsyncMock()
        llm_client.generate_text = AsyncMock(
            return_value=LLMResponse(content='{"ok": true}', provider="test", model="parity-mock")
        )
        mock_agent.llm_client = llm_client

        config = PluginConfig(
            name="hook",
            enabled=True,
            options={
                "inline_hooks": {
                    "pre_tool_use": [
                        {"type": "prompt", "prompt": "Allow tool?", "block_on_failure": False},
                    ]
                },
            },
        )
        plugin = HookPlugin(config, mock_agent)
        ctx = AgentPluginContext(
            agent=mock_agent,
            task={},
            context={},
            task_description="hello",
        )
        await plugin.on_agent_init(ctx)

        result = await plugin.dispatch(
            AgentHookEvent.PRE_TOOL_USE,
            {"tool_name": "read_file", "task_description": "hello"},
        )

        assert result.results
        assert result.results[0].success is True
        llm_client.generate_text.assert_awaited_once()
        call_kwargs = llm_client.generate_text.await_args.kwargs
        assert call_kwargs["messages"] == [
            LLMMessage(role="user", content=call_kwargs["messages"][0].content)
        ]
        assert "Allow tool?" in call_kwargs["messages"][0].content

    @pytest.mark.asyncio
    async def test_prompt_hook_without_llm_client_fails(self, mock_agent) -> None:
        config = PluginConfig(
            name="hook",
            enabled=True,
            options={
                "inline_hooks": {
                    "pre_compact": [
                        {"type": "prompt", "prompt": "Check compact", "block_on_failure": True},
                    ]
                },
            },
        )
        plugin = HookPlugin(config, mock_agent)
        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="t")
        await plugin.on_agent_init(ctx)

        result = await plugin.dispatch(AgentHookEvent.PRE_COMPACT, {"layer": "L3"})

        assert result.results
        assert result.results[0].success is False
        assert "api_client" in (result.results[0].reason or "")


def _wire_hook_plugin_manager(mock_agent, plugin: HookPlugin) -> None:
    mock_agent._plugin_manager = type(
        "PM",
        (),
        {"get_plugin": lambda _self, name: plugin if name == "hook" else None},
    )()


@pytest.mark.unit
class TestHookPluginPhaseTelemetry:
    @pytest.mark.asyncio
    async def test_phase_callbacks_emit_agent_hook_events(self, mock_agent) -> None:
        telemetry: list[dict] = []

        async def event_sink(payload: dict) -> None:
            telemetry.append(payload)

        config = PluginConfig(
            name="hook",
            enabled=True,
            options={
                "inline_hooks": {
                    "session_start": [{"type": "http", "url": "https://example.com/ss"}],
                    "iteration_end": [{"type": "http", "url": "https://example.com/ie"}],
                }
            },
        )
        plugin = HookPlugin(config, mock_agent)
        _wire_hook_plugin_manager(mock_agent, plugin)
        ctx = AgentPluginContext(
            agent=mock_agent,
            task={"task_id": "t1"},
            context={},
            task_description="hello",
            event_sink=event_sink,
        )

        await plugin.on_agent_init(ctx)
        assert any(
            event.get("type") == "agent_hook" and event.get("event") == "session_start"
            for event in telemetry
        )

        telemetry.clear()
        await plugin.on_iteration_end(ctx, iteration=2, step={})
        assert any(
            event.get("type") == "agent_hook" and event.get("event") == "iteration_end"
            for event in telemetry
        )


@pytest.mark.unit
class TestHookPluginManagerInitialize:
    @pytest.mark.asyncio
    async def test_session_start_runs_during_plugin_manager_initialize(self, mock_agent) -> None:
        dispatched: list[str] = []
        original_dispatch = HookPlugin.dispatch

        async def tracking_dispatch(self, event, payload):
            dispatched.append(event.value)
            return await original_dispatch(self, event, payload)

        config = PluginConfig(
            name="hook",
            enabled=True,
            options={
                "inline_hooks": {
                    "session_start": [{"type": "http", "url": "https://example.com/ss"}],
                }
            },
        )

        with patch.object(HookPlugin, "dispatch", tracking_dispatch):
            manager = PluginManager(
                mock_agent,
                [config],
                registry=PluginRegistry.default(),
            )
            await manager.initialize()

        assert "session_start" in dispatched
        hook_plugin = manager.get_plugin("hook")
        assert isinstance(hook_plugin, HookPlugin)
        assert hook_plugin.registry is not None
        assert len(hook_plugin.registry.get_hooks(AgentHookEvent.SESSION_START)) == 1


@pytest.mark.unit
class TestHookPluginManifestPaths:
    def test_manifest_hooks_resolve_relative_to_agent_manifest_dir(
        self, mock_agent, tmp_path: Path
    ) -> None:
        from aiecs.domain.agent.plugins.schema.manifest import PluginManifest

        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()
        hooks_file = pack_dir / "hooks.json"
        hooks_file.write_text(
            '{"hooks": {"pre_tool_use": [{"type": "http", "url": "https://example.com/h"}]}}',
            encoding="utf-8",
        )

        manifest = PluginManifest(name="pack", hooks="./hooks.json")
        mock_agent._loaded_plugin_manifests = [manifest]
        mock_agent._manifest_dirs = {"pack": pack_dir}

        plugin = HookPlugin(PluginConfig(name="hook", enabled=True, options={}), mock_agent)
        sources = plugin._collect_static_sources()
        resolved_paths = [source for _label, source in sources if isinstance(source, Path)]

        assert hooks_file.resolve() in resolved_paths


@pytest.mark.unit
class TestHookPluginConfirmToolsApi:
    def test_tool_confirmation_reason_uses_confirm_tools_matcher(self, mock_agent) -> None:
        plugin = HookPlugin(
            PluginConfig(name="hook", enabled=True, options={"confirm_tools": "write_*"}),
            mock_agent,
        )
        assert plugin.confirm_tools_matcher() == "write_*"
        assert plugin.tool_confirmation_reason("write_file") is not None
        assert plugin.tool_confirmation_reason("read_file") is None


@pytest.mark.unit
class TestAgentLLMHookPromptClient:
    @pytest.mark.asyncio
    async def test_complete_hook_prompt_calls_generate_text(self) -> None:
        llm_client = AsyncMock()
        llm_client.generate_text = AsyncMock(
            return_value=LLMResponse(content='{"ok": true}', provider="test", model="m")
        )
        client = AgentLLMHookPromptClient(llm_client, default_model="hook-model")

        text = await client.complete_hook_prompt(prompt="validate", model=None, max_tokens=128)

        assert text == '{"ok": true}'
        llm_client.generate_text.assert_awaited_once_with(
            messages=[LLMMessage(role="user", content="validate")],
            model="hook-model",
            max_tokens=128,
            temperature=0.0,
        )

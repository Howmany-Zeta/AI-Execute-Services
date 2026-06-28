"""
Unit tests for dispatch_tool_with_hooks (H1).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.tool_dispatch import (
    dispatch_tool_with_hooks,
    resolve_tool_confirmation,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t1"},
        context={},
        task_description="do something",
    )


@pytest.mark.unit
class TestDispatchToolWithHooks:
    @pytest.mark.asyncio
    async def test_pre_tool_block_skips_execute_and_fires_h2(self, plugin_ctx) -> None:
        execute = AsyncMock(return_value="should-not-run")

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="http",
                            success=False,
                            blocked=True,
                            reason="blocked by policy",
                        )
                    ]
                )
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="read_file",
                tool_input={"path": "/etc/passwd"},
                tool_call_id="call_1",
                execute_tool=execute,
            )

        assert result.blocked is True
        assert result.executed is False
        execute.assert_not_called()
        assert result.tool_content == "blocked by policy"

    @pytest.mark.asyncio
    async def test_permission_deny_skips_h1(self, plugin_ctx) -> None:
        plugin_ctx.context["hook_permission_checker"] = AsyncMock(return_value=(True, "needs approval"))
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=False)
        h1_calls: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                h1_calls.append("h1")
            return AggregatedHookResult.empty()

        execute = AsyncMock()
        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "x"},
                tool_call_id="call_2",
                execute_tool=execute,
            )

        assert result.permission_denied is True
        assert result.h1_fired is False
        assert h1_calls == []
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_legacy_permission_checker_exception_denies(self, plugin_ctx) -> None:
        async def _boom(_tool_name: str, _tool_input: dict) -> tuple[bool, str]:
            raise RuntimeError("checker unavailable")

        plugin_ctx.context["hook_permission_checker"] = _boom
        h1_calls: list[str] = []
        execute = AsyncMock()

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                h1_calls.append("h1")
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "x"},
                tool_call_id="call_legacy_err",
                execute_tool=execute,
            )

        assert result.permission_denied is True
        assert result.h1_fired is False
        assert "hook_permission_checker raised an error" in (result.block_reason or "")
        assert h1_calls == []
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_success_executes_and_fires_h2(self, plugin_ctx) -> None:
        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            return AggregatedHookResult.empty()

        execute = AsyncMock(return_value={"ok": True})
        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="search",
                tool_input={"q": "hooks"},
                tool_call_id="call_3",
                execute_tool=execute,
                offload=False,
            )

        assert result.executed is True
        assert result.tool_output == {"ok": True}
        assert AgentHookEvent.PRE_TOOL_USE.value in events
        assert AgentHookEvent.POST_TOOL_USE.value in events
        execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_modified_output_last_wins(self, plugin_ctx) -> None:
        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.POST_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="prompt",
                            success=True,
                            modified_output="rewritten output",
                        )
                    ]
                )
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="search",
                tool_input={},
                tool_call_id="call_4",
                execute_tool=AsyncMock(return_value="original"),
                offload=False,
            )

        assert result.tool_content == "rewritten output"

    @pytest.mark.asyncio
    async def test_kernel_rejection_fires_h1_and_h2(self, plugin_ctx) -> None:
        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            rejection = {"status": "rejected", "reason": "D13"}
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="dawp_start",
                tool_input={},
                tool_call_id="call_5",
                kernel_rejection=rejection,
            )

        assert result.executed is False
        assert AgentHookEvent.PRE_TOOL_USE.value in events
        assert AgentHookEvent.POST_TOOL_USE.value in events
        assert "D13" in (result.tool_content or "")

    @pytest.mark.asyncio
    async def test_tool_failure_fires_h2(self, plugin_ctx) -> None:
        post_payloads: list[dict] = []

        async def fake_dispatch(_ctx, event, payload, *, nested=False):
            if event == AgentHookEvent.POST_TOOL_USE:
                post_payloads.append(payload)
            return AggregatedHookResult.empty()

        async def _boom() -> None:
            raise RuntimeError("tool broke")

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="search",
                tool_input={},
                tool_call_id="call_6",
                execute_tool=_boom,
            )

        assert result.error_message is not None
        assert post_payloads
        assert post_payloads[0]["tool_success"] is False

    @pytest.mark.asyncio
    async def test_confirm_tools_matcher(self, plugin_ctx, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        plugin = HookPlugin(
            PluginConfig(name="hook", enabled=True, options={"confirm_tools": "write_*"}),
            mock_agent,
        )
        plugin_ctx.agent._plugin_manager = type(
            "PM",
            (),
            {"get_plugin": lambda _self, name: plugin if name == "hook" else None},
        )()

        need = await resolve_tool_confirmation(plugin_ctx, "write_file", {})
        assert need is not None
        assert need.reason

        no_need = await resolve_tool_confirmation(plugin_ctx, "read_file", {})
        assert no_need is None

    @pytest.mark.asyncio
    async def test_confirm_tools_denies_without_permission_prompt(self, plugin_ctx, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        plugin = HookPlugin(
            PluginConfig(name="hook", enabled=True, options={"confirm_tools": "write_*"}),
            mock_agent,
        )
        plugin_ctx.agent._plugin_manager = type(
            "PM",
            (),
            {"get_plugin": lambda _self, name: plugin if name == "hook" else None},
        )()
        execute = AsyncMock()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            return_value=AggregatedHookResult.empty(),
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/tmp/x"},
                tool_call_id="call_confirm",
                execute_tool=execute,
                offload=False,
            )

        assert result.permission_denied is True
        assert "permission_prompt callback is not configured" in (result.block_reason or "")
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_h20_on_offload(self, plugin_ctx, monkeypatch) -> None:
        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            return AggregatedHookResult.empty()

        async def fake_offload(**kwargs):
            return "Tool output truncated\nFull output saved to: file:///tmp/out.txt"

        monkeypatch.setattr(
            "aiecs.domain.agent.tool_loop_core.apply_tool_output_management",
            fake_offload,
        )
        ctx = ToolLoopCompressionContext(enabled=True, session_id="s1")

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="search",
                tool_input={},
                tool_call_id="call_7",
                execute_tool=AsyncMock(return_value="x" * 5000),
                offload=True,
                compression_ctx=ctx,
            )

        assert result.offloaded is True
        assert AgentHookEvent.TOOL_OUTPUT_OFFLOAD.value in events

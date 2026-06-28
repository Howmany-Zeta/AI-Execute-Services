"""
V2 permission stack tests (PERM-01…04, PTUF-01, D-V2-06).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.permission import PermissionDecision
from aiecs.domain.agent.plugins.hooks.tool_dispatch import dispatch_tool_with_hooks
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t-v2"},
        context={},
        task_description="v2 permission test",
    )


def _event_counter():
    counts: dict[str, int] = {}

    async def fake_dispatch(_ctx, event, _payload, *, nested=False):
        counts[event.value] = counts.get(event.value, 0) + 1
        if event == AgentHookEvent.PRE_TOOL_USE:
            return AggregatedHookResult(
                results=[HookResult(hook_type="http", success=True, blocked=False)]
            )
        return AggregatedHookResult.empty()

    return counts, fake_dispatch


@pytest.mark.unit
class TestV2PermissionMatrix:
    @pytest.mark.asyncio
    async def test_perm_01_checker_allow_fires_h1_not_h22(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.allow()
        )
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock(return_value={"ok": True})

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="read_file",
                tool_input={"path": "/tmp/x"},
                tool_call_id="call_p1",
                execute_tool=execute,
                offload=False,
            )

        assert result.executed is True
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value) == 1
        assert counts.get(AgentHookEvent.PERMISSION_DENIED.value, 0) == 0
        assert counts.get(AgentHookEvent.PERMISSION_REQUEST.value, 0) == 0
        execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_perm_02_checker_ask_user_approve(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.ask("confirm write")
        )
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=True)
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock(return_value="ok")

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/tmp/x"},
                tool_call_id="call_p2",
                execute_tool=execute,
                offload=False,
            )

        assert result.executed is True
        assert counts.get(AgentHookEvent.PERMISSION_REQUEST.value) == 1
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value) == 1
        assert counts.get(AgentHookEvent.PERMISSION_DENIED.value, 0) == 0

    @pytest.mark.asyncio
    async def test_perm_03_checker_deny_skips_h1_fires_h22(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.deny("policy blocked")
        )
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="call_p3",
                execute_tool=execute,
                offload=False,
            )

        assert result.permission_denied is True
        assert result.h1_fired is False
        assert counts.get(AgentHookEvent.PERMISSION_DENIED.value) == 1
        assert counts.get(AgentHookEvent.POST_TOOL_USE.value) == 1
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value, 0) == 0
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_perm_03_user_deny_after_ask(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.ask("confirm")
        )
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=False)
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="call_p3b",
                execute_tool=execute,
                offload=False,
            )

        assert result.permission_denied is True
        assert result.h1_fired is False
        assert counts.get(AgentHookEvent.PERMISSION_REQUEST.value) == 1
        assert counts.get(AgentHookEvent.PERMISSION_DENIED.value) == 1
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value, 0) == 0
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_perm_04_h1_block_not_h22(self, plugin_ctx) -> None:
        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="http",
                            success=False,
                            blocked=True,
                            reason="hook blocked",
                        )
                    ]
                )
            return AggregatedHookResult.empty()

        execute = AsyncMock()
        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="read_file",
                tool_input={},
                tool_call_id="call_p4",
                execute_tool=execute,
                offload=False,
            )

        assert result.blocked is True
        assert result.permission_denied is False
        assert result.h1_fired is True
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_ptuf_01_execute_raises_ptuf_then_h2(self, plugin_ctx, mock_agent) -> None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin
        from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
        from aiecs.domain.agent.plugins.hooks.schemas import HttpHookDefinition
        from aiecs.domain.agent.plugins.models import PluginConfig

        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.POST_TOOL_USE_FAILURE,
            HttpHookDefinition(url="https://example.com/ptuf"),
        )
        plugin = HookPlugin(PluginConfig(name="hook", enabled=True), mock_agent)
        plugin._registry = registry  # type: ignore[attr-defined]
        plugin._executor = None
        plugin_ctx.agent._plugin_manager = type(
            "PM",
            (),
            {"get_plugin": lambda _self, name: plugin if name == "hook" else None},
        )()

        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="http", success=True)]
                )
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
                tool_call_id="call_ptuf",
                execute_tool=_boom,
                offload=False,
            )

        assert result.error_message is not None
        assert events.index(AgentHookEvent.POST_TOOL_USE_FAILURE.value) < events.index(
            AgentHookEvent.POST_TOOL_USE.value
        )
        assert events.count(AgentHookEvent.POST_TOOL_USE.value) == 1

    @pytest.mark.asyncio
    async def test_updated_input_merged_before_execute(self, plugin_ctx) -> None:
        captured: dict[str, dict] = {}

        async def fake_dispatch(_ctx, event, payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="prompt",
                            success=True,
                            updated_input={"path": "/safe/path"},
                        )
                    ]
                )
            if event == AgentHookEvent.POST_TOOL_USE:
                captured["post_input"] = dict(payload.get("tool_input") or {})
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="read_file",
                tool_input={"path": "/original"},
                tool_call_id="call_ui",
                execute_tool=AsyncMock(return_value="done"),
                offload=False,
            )

        assert captured["post_input"]["path"] == "/safe/path"

    @pytest.mark.asyncio
    async def test_mcp_tool_prefers_updated_mcp_output(self, plugin_ctx) -> None:
        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="http", success=True)]
                )
            if event == AgentHookEvent.POST_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="prompt",
                            success=True,
                            modified_output="generic",
                            updated_mcp_output="mcp rewritten",
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
                tool_name="mcp__filesystem__read",
                tool_input={},
                tool_call_id="call_mcp",
                execute_tool=AsyncMock(return_value={"text": "raw"}),
                offload=False,
            )

        assert result.tool_content == "mcp rewritten"

    @pytest.mark.asyncio
    async def test_non_mcp_ignores_updated_mcp_output(self, plugin_ctx) -> None:
        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="http", success=True)]
                )
            if event == AgentHookEvent.POST_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="prompt",
                            success=True,
                            modified_output="generic rewrite",
                            updated_mcp_output="ignored mcp",
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
                tool_input={},
                tool_call_id="call_non_mcp",
                execute_tool=AsyncMock(return_value="raw"),
                offload=False,
            )

        assert result.tool_content == "generic rewrite"

    @pytest.mark.asyncio
    async def test_h7_after_permission_request(self, plugin_ctx) -> None:
        call_order: list[str] = []
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.ask("needs approval")
        )
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=True)

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            call_order.append(event.value)
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="http", success=True)]
                )
            return AggregatedHookResult.empty()

        async def fake_notification(*args, **kwargs):
            call_order.append("h7")

        with (
            patch(
                "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
                side_effect=fake_dispatch,
            ),
            patch(
                "aiecs.domain.agent.plugins.hooks.notifications.dispatch_host_notification",
                side_effect=fake_notification,
            ),
        ):
            await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/tmp/x"},
                tool_call_id="call_order",
                execute_tool=AsyncMock(return_value="ok"),
                offload=False,
            )

        assert call_order.index(AgentHookEvent.PERMISSION_REQUEST.value) < call_order.index("h7")
        assert call_order.index("h7") < call_order.index(AgentHookEvent.PRE_TOOL_USE.value)

    @pytest.mark.asyncio
    async def test_perm_ask_permission_prompt_raises_denies(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.ask("confirm write")
        )

        async def _boom(_tool_name: str, _reason: str) -> bool:
            raise RuntimeError("ui unavailable")

        plugin_ctx.context["permission_prompt"] = _boom
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="call_prompt_err",
                execute_tool=execute,
                offload=False,
            )

        assert result.permission_denied is True
        assert result.h1_fired is False
        assert "permission_prompt raised an error" in (result.block_reason or "")
        assert counts.get(AgentHookEvent.PERMISSION_DENIED.value) == 1
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value, 0) == 0
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_perm_ask_missing_permission_prompt_denies(self, plugin_ctx) -> None:
        plugin_ctx.context["permission_checker"] = AsyncMock(
            return_value=PermissionDecision.ask("confirm write")
        )
        counts, fake_dispatch = _event_counter()
        execute = AsyncMock()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="call_prompt_missing",
                execute_tool=execute,
                offload=False,
            )

        assert result.permission_denied is True
        assert "permission_prompt callback is not configured" in (result.block_reason or "")
        assert counts.get(AgentHookEvent.PRE_TOOL_USE.value, 0) == 0
        execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_h1_permission_decision_deny_sets_blocked_not_permission_denied(
        self, plugin_ctx
    ) -> None:
        """PERM-04 / §7.6.2: post-H1 hook deny uses blocked only, not permission_denied."""
        post_payloads: list[dict] = []

        async def fake_dispatch(_ctx, event, payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="prompt",
                            success=True,
                            permission_decision="deny",
                        )
                    ]
                )
            if event == AgentHookEvent.POST_TOOL_USE:
                post_payloads.append(dict(payload))
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            result = await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="call_h1_deny",
                execute_tool=AsyncMock(),
                offload=False,
            )

        assert result.blocked is True
        assert result.permission_denied is False
        assert post_payloads
        assert post_payloads[0]["blocked"] is True
        assert "permission_denied" not in post_payloads[0]


@pytest.mark.unit
class TestV2LoaderEvents:
    def test_v2_events_register_from_json(self) -> None:
        from aiecs.domain.agent.plugins.hooks.loader import load_hooks_from_json
        from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry

        registry = AgentHookRegistry()
        load_hooks_from_json(
            {
                "hooks": {
                    "permission_request": [
                        {"type": "http", "url": "https://example.com/pr"}
                    ],
                    "permission_denied": [
                        {"type": "http", "url": "https://example.com/pd"}
                    ],
                    "post_tool_use_failure": [
                        {"type": "http", "url": "https://example.com/ptuf"}
                    ],
                    "PermissionDenied": [
                        {"type": "http", "url": "https://example.com/pd-cc"}
                    ],
                }
            },
            registry,
        )
        assert len(registry.get_hooks(AgentHookEvent.PERMISSION_REQUEST)) == 1
        assert len(registry.get_hooks(AgentHookEvent.PERMISSION_DENIED)) == 2
        assert len(registry.get_hooks(AgentHookEvent.POST_TOOL_USE_FAILURE)) == 1

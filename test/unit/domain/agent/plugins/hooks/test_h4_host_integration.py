"""
Phase H4 — host integration tests (§5).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.tool_dispatch import dispatch_tool_with_hooks
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.host.hooks import agent_hook_event_to_sse_payload


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t1"},
        context={},
        task_description="task",
    )


@pytest.mark.unit
class TestH7HostNotification:
    @pytest.mark.asyncio
    async def test_h7_fires_before_h1_on_confirmation_path(self, plugin_ctx) -> None:
        call_order: list[str] = []

        plugin_ctx.context["hook_permission_checker"] = AsyncMock(
            return_value=(True, "needs approval")
        )
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=True)

        async def fake_notification(*args, **kwargs):
            call_order.append("h7")
            return True

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                call_order.append("h1")
            elif event == AgentHookEvent.PERMISSION_REQUEST:
                call_order.append("permission_request")
            return AggregatedHookResult.empty()

        with (
            patch(
                "aiecs.domain.agent.plugins.hooks.notifications.dispatch_host_notification",
                side_effect=fake_notification,
            ),
            patch(
                "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
                side_effect=fake_dispatch,
            ),
        ):
            await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/tmp/x"},
                tool_call_id="call_h7",
                execute_tool=AsyncMock(return_value="ok"),
                offload=False,
            )

        assert call_order.index("h7") < call_order.index("h1")
        assert call_order.index("permission_request") < call_order.index("h7")

    @pytest.mark.asyncio
    async def test_h7_passes_tool_input_in_payload(self, plugin_ctx) -> None:
        plugin_ctx.context["hook_permission_checker"] = AsyncMock(return_value=(True, "confirm"))
        plugin_ctx.context["permission_prompt"] = AsyncMock(return_value=True)
        captured: dict = {}

        async def fake_notification(ctx, **kwargs):
            captured.update(kwargs)
            return True

        with (
            patch(
                "aiecs.domain.agent.plugins.hooks.notifications.dispatch_host_notification",
                side_effect=fake_notification,
            ),
            patch(
                "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
                AsyncMock(return_value=AggregatedHookResult.empty()),
            ),
        ):
            await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={"path": "/etc/hosts"},
                tool_call_id="call_in",
                execute_tool=AsyncMock(return_value="ok"),
                offload=False,
            )

        assert captured.get("tool_input") == {"path": "/etc/hosts"}


@pytest.mark.unit
class TestHostHooksSseBridge:
    def test_agent_hook_event_to_sse_payload(self) -> None:
        payload = agent_hook_event_to_sse_payload(
            {
                "type": "agent_hook",
                "event": "pre_tool_use",
                "blocked": True,
                "hook_count": 2,
                "duration_ms": 15.5,
            },
            session_id="sess-1",
            task_id="task-9",
        )
        assert payload["event"] == "agent_hook"
        assert payload["hook_event"] == "pre_tool_use"
        assert payload["blocked"] is True
        assert payload["session_id"] == "sess-1"
        assert payload["task_id"] == "task-9"

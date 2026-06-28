"""
Harness parity checklist tests (§13) — focused assertions for OpenHarness alignment.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.loader import load_hooks_from_json, normalize_event_key
from aiecs.domain.agent.plugins.hooks.registry import AgentHookRegistry
from aiecs.domain.agent.plugins.hooks.schemas import HttpHookDefinition
from aiecs.domain.agent.plugins.hooks.tool_dispatch import dispatch_tool_with_hooks
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t1"},
        context={},
        task_description="parity task",
    )


@pytest.mark.unit
class TestHarnessParityChecklist:
    @pytest.mark.asyncio
    async def test_pre_tool_block_returns_error_tool_result(self, plugin_ctx) -> None:
        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[
                        HookResult(
                            hook_type="http",
                            success=False,
                            blocked=True,
                            reason="policy block",
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
                tool_name="write_file",
                tool_input={},
                tool_call_id="c1",
                execute_tool=AsyncMock(),
            )

        assert result.blocked is True
        assert result.executed is False
        assert result.tool_content == "policy block"

    @pytest.mark.asyncio
    async def test_post_tool_audit_via_h2_on_block_path(self, plugin_ctx) -> None:
        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            if event == AgentHookEvent.PRE_TOOL_USE:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="http", success=False, blocked=True, reason="no")]
                )
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            await dispatch_tool_with_hooks(
                plugin_ctx,
                tool_name="write_file",
                tool_input={},
                tool_call_id="c2",
                execute_tool=AsyncMock(),
            )

        assert AgentHookEvent.PRE_TOOL_USE.value in events
        assert AgentHookEvent.POST_TOOL_USE.value in events

    @pytest.mark.asyncio
    async def test_parallel_batch_independent_pre_post_per_tool(self, plugin_ctx) -> None:
        seen: list[tuple[int, str, str]] = []

        async def fake_dispatch(_ctx, event, payload, *, nested=False):
            seen.append(
                (
                    payload.get("batch_index", -1),
                    payload.get("tool_name", ""),
                    event.value,
                )
            )
            return AggregatedHookResult.empty()

        execute = AsyncMock(return_value={"ok": True})
        with patch(
            "aiecs.domain.agent.plugins.hooks.dispatch.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            for index, name in enumerate(("read_file", "write_file")):
                await dispatch_tool_with_hooks(
                    plugin_ctx,
                    tool_name=name,
                    tool_input={"path": f"/tmp/{index}"},
                    tool_call_id=f"call_{index}",
                    batch_tool_call_count=2,
                    batch_index=index,
                    execute_tool=execute,
                )

        pre_only = [entry for entry in seen if entry[2] == AgentHookEvent.PRE_TOOL_USE.value]
        assert len(pre_only) == 2
        assert {entry[0] for entry in pre_only} == {0, 1}
        assert {entry[1] for entry in pre_only} == {"read_file", "write_file"}

    @pytest.mark.asyncio
    async def test_priority_descending_and_serial_all_hooks_run(self) -> None:
        from pathlib import Path

        from aiecs.domain.agent.plugins.hooks.executor import AgentHookExecutionContext, AgentHookExecutor

        calls: list[str] = []

        class SpyExecutor(AgentHookExecutor):
            async def _run_http_hook(  # type: ignore[override]
                self, hook, event, payload, *, timeout_seconds: float | None = None
            ):
                del event, payload, timeout_seconds
                calls.append(hook.url)
                blocked = "block" in hook.url
                return HookResult(
                    hook_type="http",
                    success=not blocked,
                    blocked=blocked,
                    reason="blocked" if blocked else "",
                )

        registry = AgentHookRegistry()
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/block", priority=10, block_on_failure=True),
        )
        registry.register(
            AgentHookEvent.PRE_TOOL_USE,
            HttpHookDefinition(url="https://example.com/audit", priority=0),
        )
        executor = SpyExecutor(registry, AgentHookExecutionContext(cwd=Path.cwd()))
        result = await executor.execute_event(AgentHookEvent.PRE_TOOL_USE, {"tool_name": "x"})
        assert result.blocked is True
        assert calls == ["https://example.com/block", "https://example.com/audit"]

    def test_subagent_stop_maps_to_dawp_run_end(self) -> None:
        from aiecs.domain.agent.plugins.hooks.loader import HookLoadOptions

        event = normalize_event_key("SubagentStop", options=HookLoadOptions())
        assert event == AgentHookEvent.DAWP_RUN_END

        registry = AgentHookRegistry()
        load_hooks_from_json(
            {"hooks": {"subagent_stop": [{"type": "http", "url": "https://example.com/end"}]}},
            registry,
        )
        assert len(registry.get_hooks(AgentHookEvent.DAWP_RUN_END)) == 1

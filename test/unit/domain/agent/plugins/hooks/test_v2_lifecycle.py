"""
V2.1 lifecycle hook tests (H5b, task rejection, preventContinuation, subagent, session).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.payload import (
    build_dawp_run_end_payload,
    build_session_end_payload,
    build_session_start_payload,
)
from aiecs.domain.agent.plugins.hooks.task_boundary import (
    apply_hook_additional_context,
    dispatch_stop_hook_for_outcome,
    dispatch_user_prompt_in_history_hook,
    task_rejection_from_hook_result,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult
from aiecs.domain.agent.tool_loop_core import ToolLoopIterationOutcome
from aiecs.llm import LLMMessage


@pytest.fixture
def plugin_ctx(mock_agent) -> AgentPluginContext:
    return AgentPluginContext(
        agent=mock_agent,
        task={"task_id": "t-lifecycle"},
        context={"session_id": "sess-1", "session_reason": "host_idle_resume"},
        task_description="lifecycle test",
    )


@pytest.mark.unit
class TestV2TaskRejection:
    def test_h5_continue_false_rejects(self) -> None:
        result = AggregatedHookResult(
            results=[HookResult(hook_type="command", success=True, continue_allowed=False, reason="blocked prompt")]
        )
        rejection = task_rejection_from_hook_result(result, source="user_prompt_submit")
        assert rejection is not None
        assert rejection["reason"] == "hook_task_rejected"
        assert rejection["hook_rejection_source"] == "user_prompt_submit"

    def test_h5b_additional_context_merged(self, plugin_ctx) -> None:
        messages = [
            LLMMessage(role="system", content="sys"),
            LLMMessage(role="user", content="Task: do work"),
        ]
        result = AggregatedHookResult(
            results=[HookResult(hook_type="command", success=True, additional_context="extra rules")]
        )
        apply_hook_additional_context(plugin_ctx, messages, result)
        assert plugin_ctx.plugin_state["hook.additional_context"] == "extra rules"
        assert messages[1].role == "system"
        assert "extra rules" in str(messages[1].content)


@pytest.mark.unit
class TestV2StopContinuation:
    @pytest.mark.asyncio
    async def test_prevent_continuation_returns_true(self, plugin_ctx) -> None:
        outcome = ToolLoopIterationOutcome(
            kind="final",
            result={"final_response": "done", "steps": [], "iterations": 1},
        )

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            assert event == AgentHookEvent.STOP
            return AggregatedHookResult(
                results=[HookResult(hook_type="command", success=True, prevent_continuation=True)]
            )

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration=0)
        assert prevent is True

    @pytest.mark.asyncio
    async def test_stop_failure_on_hook_error(self, plugin_ctx) -> None:
        outcome = ToolLoopIterationOutcome(
            kind="final",
            result={"final_response": "done", "steps": [], "iterations": 1},
        )
        events: list[str] = []

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            events.append(event.value)
            if event == AgentHookEvent.STOP:
                return AggregatedHookResult(
                    results=[HookResult(hook_type="command", success=False, reason="timeout")]
                )
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration=1)
        assert prevent is False
        assert AgentHookEvent.STOP.value in events
        assert AgentHookEvent.STOP_FAILURE.value in events


@pytest.mark.unit
class TestV2SessionPayloads:
    def test_session_start_includes_reason(self) -> None:
        payload = build_session_start_payload(
            agent_id="agent-1",
            session_id="sess-1",
            reason="host_idle_resume",
        )
        assert payload["session_id"] == "sess-1"
        assert payload["reason"] == "host_idle_resume"

    def test_session_end_includes_reason(self) -> None:
        payload = build_session_end_payload(
            agent_id="agent-1",
            session_id="sess-1",
            reason="timeout",
        )
        assert payload["reason"] == "timeout"


@pytest.mark.unit
class TestV2HookFieldExtraction:
    def test_executor_extracts_v21_fields(self) -> None:
        from aiecs.domain.agent.plugins.hooks.executor import _extract_hook_fields

        fields = _extract_hook_fields(
            {
                "additionalContext": "ctx",
                "continue": False,
                "preventContinuation": True,
            }
        )
        assert fields["additional_context"] == "ctx"
        assert fields["continue_allowed"] is False
        assert fields["prevent_continuation"] is True


@pytest.mark.unit
class TestV2H5bDispatch:
    @pytest.mark.asyncio
    async def test_user_prompt_in_history_payload(self, plugin_ctx) -> None:
        messages = [
            LLMMessage(role="system", content="sys"),
            LLMMessage(role="user", content="Task: x"),
        ]
        captured: dict[str, Any] = {}

        async def fake_dispatch(_ctx, event, payload, *, nested=False):
            captured["event"] = event
            captured["payload"] = payload
            return AggregatedHookResult.empty()

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            await dispatch_user_prompt_in_history_hook(plugin_ctx, messages)

        assert captured["event"] == AgentHookEvent.USER_PROMPT_IN_HISTORY
        assert captured["payload"]["message_count"] == 2
        assert captured["payload"]["session_id"] == "sess-1"


@pytest.mark.unit
class TestV2OnToolBatchEnd:
    @pytest.mark.asyncio
    async def test_plugin_phase_on_tool_batch_end(self, mock_agent) -> None:
        from aiecs.domain.agent.plugins.base import BaseAgentPlugin
        from aiecs.domain.agent.plugins.manager import PluginManager
        from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata, PluginPhase
        from aiecs.domain.agent.plugins.registry import PluginRegistry

        class BatchCapturePlugin(BaseAgentPlugin):
            metadata = PluginMetadata(name="batch_capture", version="0.0.1", description="test")

            async def on_tool_batch_end(self, ctx, iteration, messages) -> None:
                ctx.plugin_state.setdefault("batch_end_iterations", []).append(iteration)

        registry = PluginRegistry()
        registry.register("batch_capture", BatchCapturePlugin)
        manager = PluginManager(
            mock_agent,
            [PluginConfig(name="batch_capture", enabled=True)],
            registry=registry,
        )
        await manager.initialize()

        ctx = AgentPluginContext(agent=mock_agent, task={}, context={}, task_description="")
        messages = [LLMMessage(role="user", content="hi")]
        await manager.run_phase(
            PluginPhase.ON_TOOL_BATCH_END,
            ctx=ctx,
            iteration=2,
            messages=messages,
        )
        assert ctx.plugin_state["batch_end_iterations"] == [2]


@pytest.mark.unit
class TestV2SubagentPayload:
    def test_dawp_run_end_enriched_h10(self) -> None:
        payload = build_dawp_run_end_payload(
            agent_id="agent-1",
            workflow_id="wf-review",
            run_id="run-abc",
            status="success",
            abort_main=False,
            last_assistant_message="Review complete.",
            agent_transcript_path="/tmp/transcript.jsonl",
        )
        assert payload["event"] == AgentHookEvent.DAWP_RUN_END.value
        assert payload["last_assistant_message"] == "Review complete."
        assert payload["agent_transcript_path"] == "/tmp/transcript.jsonl"


@pytest.mark.unit
class TestV2H5b01H6Prevent:
    """V2-24 acceptance IDs: H5b-01, H6-prevent-01."""

    @pytest.mark.asyncio
    async def test_h5b_01_rejects_before_main_loop(self, plugin_ctx) -> None:
        result = AggregatedHookResult(
            results=[HookResult(hook_type="command", success=True, continue_allowed=False, reason="policy")]
        )
        rejection = task_rejection_from_hook_result(result, source="user_prompt_in_history")
        assert rejection is not None
        assert rejection["hook_rejection_source"] == "user_prompt_in_history"

    @pytest.mark.asyncio
    async def test_h6_prevent_01_reenters_loop_flag(self, plugin_ctx) -> None:
        outcome = ToolLoopIterationOutcome(
            kind="final",
            result={"final_response": "not yet", "steps": [], "iterations": 2},
        )

        async def fake_dispatch(_ctx, event, _payload, *, nested=False):
            return AggregatedHookResult(
                results=[HookResult(hook_type="command", success=True, prevent_continuation=True)]
            )

        with patch(
            "aiecs.domain.agent.plugins.hooks.task_boundary.dispatch_agent_hook",
            side_effect=fake_dispatch,
        ):
            prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration=1)
        assert prevent is True

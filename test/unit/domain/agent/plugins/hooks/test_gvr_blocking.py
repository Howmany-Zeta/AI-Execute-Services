"""
GVR hook blocking tests (A-8).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.hooks.gvr_blocking import (
    build_merged_blocking_message,
    format_blocking_user_message,
    resolve_blocking_from_hook,
    run_pre_exit_gvr_check,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult, HookResult
from aiecs.domain.agent.verification.gates.registry import build_gate_registry_from_config
from aiecs.domain.agent.verification.models import FeedbackItem
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestGvrBlockingMessage:
    def test_data_only_message_from_feedback_items(self) -> None:
        msg = format_blocking_user_message(
            "missing sections",
            [FeedbackItem(criterion_id="spec", gap="no GIVEN", fix="add GIVEN", severity="high")],
        )
        assert "GVR verification" in msg
        assert "no GIVEN" in msg
        assert "please reflect" not in msg.lower()

    def test_strips_reflect_template_from_feedback(self) -> None:
        msg = format_blocking_user_message("Please reflect on whether complete", [])
        assert "please reflect" not in msg.lower()


@pytest.mark.unit
class TestHookBlockSchema:
    def test_action_block_triggers_prevent(self) -> None:
        result = AggregatedHookResult(
            results=[
                HookResult(
                    hook_type="command",
                    success=True,
                    action="block",
                    feedback="gap list",
                    feedback_items=[{"criterion_id": "c1", "gap": "x", "fix": "y", "severity": "high"}],
                )
            ]
        )
        assert result.prevent_continuation is True
        block, message, items = resolve_blocking_from_hook(result)
        assert block is True
        assert items


@pytest.mark.unit
class TestPreExitGvrIntegration:
    @pytest.mark.asyncio
    async def test_spec_gate_fail_injects_message_and_continues(self) -> None:
        plugin_ctx = MagicMock()
        plugin_ctx.agent.agent_id = "a1"
        plugin_ctx.task = {"task_id": "t1"}
        plugin_ctx.context = {}

        messages = [LLMMessage(role="user", content="task")]
        loop_result = {"final_response": "unstructured output", "output": "unstructured output"}
        registry = build_gate_registry_from_config(["spec_gate"])

        with patch(
            "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
            new_callable=AsyncMock,
        ) as mock_hook:
            mock_hook.return_value = AggregatedHookResult.empty()
            should_continue = await run_pre_exit_gvr_check(
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=loop_result,
                gate_registry=registry,
                goal=None,
            )

        assert should_continue is True
        assert len(messages) == 2
        assert messages[-1].role == "user"
        assert "GVR verification" in messages[-1].content

    @pytest.mark.asyncio
    async def test_no_gates_no_hook_no_block(self) -> None:
        plugin_ctx = MagicMock()
        plugin_ctx.agent.agent_id = "a1"
        plugin_ctx.task = {}
        plugin_ctx.context = {}
        messages = [LLMMessage(role="user", content="task")]

        with patch(
            "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
            new_callable=AsyncMock,
        ) as mock_hook:
            mock_hook.return_value = AggregatedHookResult.empty()
            should_continue = await run_pre_exit_gvr_check(
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result={"output": "ok"},
                gate_registry=build_gate_registry_from_config(None),
            )

        assert should_continue is False
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_gate_and_hook_block_merge_feedback(self) -> None:
        """When both gate and hook block, inject one message with both feedback sources."""
        plugin_ctx = MagicMock()
        plugin_ctx.agent.agent_id = "a1"
        plugin_ctx.task = {"task_id": "t1"}
        plugin_ctx.context = {}

        messages = [LLMMessage(role="user", content="task")]
        loop_result = {"final_response": "unstructured output", "output": "unstructured output"}
        registry = build_gate_registry_from_config(["spec_gate"])

        with patch(
            "aiecs.domain.agent.plugins.hooks.gvr_blocking.dispatch_pre_exit_task_completed_hook",
            new_callable=AsyncMock,
        ) as mock_hook:
            mock_hook.return_value = AggregatedHookResult(
                results=[
                    HookResult(
                        hook_type="command",
                        success=True,
                        action="block",
                        feedback="hook-specific gap",
                        feedback_items=[
                            {
                                "criterion_id": "hook_c1",
                                "gap": "missing citation",
                                "fix": "add source URL",
                                "severity": "high",
                            }
                        ],
                    )
                ]
            )
            should_continue = await run_pre_exit_gvr_check(
                plugin_ctx=plugin_ctx,
                messages=messages,
                loop_result=loop_result,
                gate_registry=registry,
                goal=None,
            )

        assert should_continue is True
        assert len(messages) == 2
        combined = messages[-1].content or ""
        assert "GVR verification" in combined
        assert "Missing GIVEN" in combined or "GIVEN" in combined
        assert "missing citation" in combined
        assert "hook-specific gap" in combined

    def test_build_merged_blocking_message_combines_sources(self) -> None:
        from aiecs.domain.agent.verification.models import Verdict

        gate_verdict = Verdict(
            passed=False,
            kind="FAIL",
            feedback="gate feedback",
            feedback_items=[
                FeedbackItem(criterion_id="spec", gap="no GIVEN", fix="add GIVEN", severity="high"),
            ],
        )
        hook_result = AggregatedHookResult(
            results=[
                HookResult(
                    hook_type="command",
                    success=True,
                    action="block",
                    feedback="hook feedback",
                    feedback_items=[
                        {"criterion_id": "hook_c1", "gap": "no URL", "fix": "cite source", "severity": "medium"},
                    ],
                )
            ]
        )
        _, _, hook_items = resolve_blocking_from_hook(hook_result)
        message = build_merged_blocking_message(
            gate_verdict=gate_verdict,
            gate_block=True,
            hook_block=True,
            hook_result=hook_result,
            hook_items=hook_items,
        )
        assert "gate feedback" in message
        assert "hook feedback" in message
        assert "no GIVEN" in message
        assert "no URL" in message

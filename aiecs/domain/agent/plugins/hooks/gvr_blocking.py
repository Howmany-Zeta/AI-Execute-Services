# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""GVR pre-exit gate + hook blocking helpers (A-8)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Sequence

from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.domain.agent.verification.gates.conversion import gate_aggregate_to_verdict
from aiecs.domain.agent.verification.gvr_checkpoints import gates_already_run, mark_gates_run
from aiecs.domain.agent.verification.models import FeedbackItem, Verdict
from aiecs.llm import LLMMessage

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext
    from aiecs.domain.agent.verification.gates.registry import GateRegistry


REFLECT_TEMPLATE_MARKERS = (
    "please reflect on whether",
    "consider if you are done",
    "think about whether the task is complete",
)


def format_blocking_user_message(
    feedback: str | dict[str, Any] | None,
    feedback_items: Sequence[FeedbackItem | dict[str, Any]] | None,
) -> str:
    """Build data-only blocking user message (no reflect prose templates)."""
    lines: list[str] = ["[GVR verification — blocking feedback]"]
    if isinstance(feedback, dict):
        lines.append(json.dumps(feedback, ensure_ascii=False))
    elif feedback:
        text = str(feedback).strip()
        if text and not _contains_reflect_template(text):
            lines.append(text)

    for item in feedback_items or []:
        if isinstance(item, FeedbackItem):
            data = item.to_dict()
        elif isinstance(item, dict):
            data = item
        else:
            continue
        gap = data.get("gap", "")
        fix = data.get("fix", "")
        cid = data.get("criterion_id", "")
        if gap or fix:
            lines.append(f"- {cid}: gap={gap}; fix={fix}")

    if len(lines) == 1:
        lines.append("Verification failed. Address listed gaps and continue.")
    return "\n".join(lines)


def _contains_reflect_template(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in REFLECT_TEMPLATE_MARKERS)


def inject_blocking_user_message(messages: list[LLMMessage], content: str) -> None:
    """Append data-only user message to continue FC loop."""
    messages.append(LLMMessage(role="user", content=content))


def verdict_to_feedback_items(verdict: Verdict) -> list[dict[str, Any]]:
    return [item.to_dict() for item in verdict.feedback_items]


def hook_requests_block(result: AggregatedHookResult) -> bool:
    if result.gvr_action == "block":
        return True
    if result.prevent_continuation:
        return True
    return False


def build_pre_exit_task_completed_payload(
    *,
    agent_id: str,
    task_id: str | None,
    output_preview: str,
    goal_id: str | None = None,
    gate_scores: list[dict[str, Any]] | None = None,
    failed_criteria: list[str] | None = None,
    gate_passed: bool | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.TASK_COMPLETED.value,
        "agent_id": agent_id,
        "task_id": task_id,
        "success": True,
        "output_preview": output_preview[:500],
        "phase": "pre_exit",
    }
    if goal_id:
        payload["goal_id"] = goal_id
    if gate_scores is not None:
        payload["gate_scores"] = gate_scores
    if failed_criteria is not None:
        payload["failed_criteria"] = failed_criteria
    if gate_passed is not None:
        payload["gate_passed"] = gate_passed
    return payload


async def dispatch_pre_exit_task_completed_hook(
    plugin_ctx: AgentPluginContext,
    *,
    loop_result: dict[str, Any],
    goal_id: str | None,
    gate_scores: list[dict[str, Any]] | None,
    failed_criteria: list[str] | None,
    gate_passed: bool | None,
) -> AggregatedHookResult:
    """In-loop TASK_COMPLETED hook (pre-exit), distinct from post_task audit."""
    output = loop_result.get("output") or loop_result.get("final_response") or ""
    agent_id = str(getattr(plugin_ctx.agent, "agent_id", ""))
    task_id_raw = (plugin_ctx.task or {}).get("task_id")
    task_id = str(task_id_raw) if task_id_raw is not None else None
    return await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.TASK_COMPLETED,
        build_pre_exit_task_completed_payload(
            agent_id=agent_id,
            task_id=task_id,
            output_preview=str(output),
            goal_id=goal_id,
            gate_scores=gate_scores,
            failed_criteria=failed_criteria,
            gate_passed=gate_passed,
        ),
    )


def resolve_blocking_from_hook(result: AggregatedHookResult) -> tuple[bool, str, list[dict[str, Any]]]:
    """Extract block decision and feedback from hook aggregate."""
    if not hook_requests_block(result):
        return False, "", []
    feedback = result.gvr_feedback or result.reason or result.additional_context or ""
    items = result.gvr_feedback_items
    message = format_blocking_user_message(feedback, items)
    return True, message, items


def build_merged_blocking_message(
    *,
    gate_verdict: Verdict | None,
    gate_block: bool,
    hook_block: bool,
    hook_result: AggregatedHookResult,
    hook_items: list[dict[str, Any]],
) -> str:
    """Combine gate + hook blocking feedback into one data-only user message."""
    feedback_parts: list[str] = []
    merged_items: list[FeedbackItem | dict[str, Any]] = []

    if gate_block and gate_verdict is not None:
        if gate_verdict.feedback:
            feedback_parts.append(gate_verdict.feedback)
        merged_items.extend(gate_verdict.feedback_items)

    if hook_block:
        hook_feedback = hook_result.gvr_feedback or hook_result.reason or hook_result.additional_context or ""
        if hook_feedback and not _contains_reflect_template(str(hook_feedback)):
            feedback_parts.append(str(hook_feedback))
        merged_items.extend(hook_items)

    combined_feedback = "\n".join(feedback_parts) if feedback_parts else None
    return format_blocking_user_message(combined_feedback, merged_items)


async def run_pre_exit_gvr_check(
    *,
    plugin_ctx: AgentPluginContext | None,
    messages: list[LLMMessage],
    loop_result: dict[str, Any],
    gate_registry: GateRegistry | None,
    goal: Any = None,
    skip_threshold: float = 85.0,
    dispatch_task_completed_hook: bool = True,
    iteration: int = 0,
) -> bool:
    """
    Run L2 gates + optional TASK_COMPLETED pre-exit hook.

    When ``dispatch_task_completed_hook=False`` (STOP-path gate-only fallback),
    only deterministic gates run; STOP hook blocking is handled separately.

    Returns True when loop should continue (blocking refine).
    """
    if plugin_ctx is None:
        return False

    goal_id: str | None = None
    if goal is not None:
        goal_id = getattr(goal, "goal_id", None) or (goal.get("goal_id") if isinstance(goal, dict) else None)

    plugin_state = plugin_ctx.plugin_state if isinstance(getattr(plugin_ctx, "plugin_state", None), dict) else None

    gate_scores_payload: list[dict[str, Any]] | None = None
    failed_criteria: list[str] | None = None
    gate_passed: bool | None = None
    gate_verdict: Verdict | None = None

    if gate_registry is not None and gate_registry.gate_ids:
        if gates_already_run(plugin_state, goal_id, iteration):
            pass
        else:
            work_snapshot = {
                "text": loop_result.get("final_response") or loop_result.get("output") or "",
                "output": loop_result.get("output") or loop_result.get("final_response") or "",
            }
            aggregate = gate_registry.run_all(
                goal=goal,
                result=loop_result,
                work_snapshot=work_snapshot,
                skip_threshold=skip_threshold,
            )
            mark_gates_run(plugin_state, goal_id, iteration)
            gate_scores_payload = [gs.model_dump() for gs in aggregate.gate_scores]
            failed_criteria = list(aggregate.failed_criteria)
            gate_passed = aggregate.passed
            gate_verdict = gate_aggregate_to_verdict(aggregate, goal=goal)

    if dispatch_task_completed_hook:
        hook_result = await dispatch_pre_exit_task_completed_hook(
            plugin_ctx,
            loop_result=loop_result,
            goal_id=goal_id,
            gate_scores=gate_scores_payload,
            failed_criteria=failed_criteria,
            gate_passed=gate_passed,
        )
    else:
        hook_result = AggregatedHookResult.empty()

    hook_block, _hook_message, hook_items = resolve_blocking_from_hook(hook_result)

    gate_block = gate_verdict is not None and not gate_verdict.passed
    if gate_block or hook_block:
        message = build_merged_blocking_message(
            gate_verdict=gate_verdict,
            gate_block=gate_block,
            hook_block=hook_block,
            hook_result=hook_result,
            hook_items=hook_items,
        )
        inject_blocking_user_message(messages, message)
        return True

    return False

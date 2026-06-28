# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Task and loop boundary hook helpers (H2 — §5.2, §6.5, P0 timing)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook, has_registered_hooks
from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
from aiecs.domain.agent.plugins.hooks.payload import (
    build_build_messages_payload,
    build_iteration_start_payload,
    build_llm_error_payload,
    build_max_iterations_payload,
    build_post_task_payload,
    build_prompt_too_long_payload,
    build_stop_failure_payload,
    build_stop_payload,
    build_task_completed_payload,
    build_user_prompt_in_history_payload,
    build_user_prompt_submit_payload,
    message_roles_summary,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.domain.context.compression.ptl import is_prompt_too_long_error

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext
    from aiecs.domain.agent.plugins.manager import PluginManager
    from aiecs.domain.agent.tool_loop_core import ToolLoopIterationOutcome, ToolLoopRunState
    from aiecs.llm import LLMMessage


def _agent_id(ctx: AgentPluginContext) -> str:
    agent = ctx.agent
    return str(getattr(agent, "agent_id", ""))


def _task_id(ctx: AgentPluginContext) -> str | None:
    task = ctx.task or {}
    raw = task.get("task_id")
    return str(raw) if raw is not None else None


def hook_task_rejection_result(reason: str, *, source: str) -> dict[str, Any]:
    """Structured task rejection when H5/H5b returns continue:false (§17 v2.1)."""
    message = reason or "task rejected by hook"
    return {
        "success": False,
        "reason": "hook_task_rejected",
        "output": message,
        "final_response": message,
        "hook_rejection_source": source,
    }


def task_rejection_from_hook_result(
    result: AggregatedHookResult,
    *,
    source: str,
) -> dict[str, Any] | None:
    if not isinstance(result, AggregatedHookResult):
        return None
    if result.continue_rejected:
        return hook_task_rejection_result(result.reason or result.additional_context or "", source=source)
    return None


def prepare_hook_task_entry(
    plugin_ctx: AgentPluginContext,
    *,
    task_description: str,
) -> None:
    """H5 registry rebuild + task entry setup (§5.1.1). Sync; call before PRE_TASK."""
    from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

    plugin = plugin_ctx.get_plugin("hook")
    if isinstance(plugin, HookPlugin) and plugin.is_enabled:
        plugin.rebuild_registry_for_task(plugin_ctx)


async def dispatch_user_prompt_submit_hook(
    plugin_ctx: AgentPluginContext,
    *,
    task_description: str,
) -> AggregatedHookResult:
    """H5 — once before PRE_TASK (P0-1)."""
    return await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.USER_PROMPT_SUBMIT,
        build_user_prompt_submit_payload(
            prompt=task_description,
            agent_id=_agent_id(plugin_ctx),
            task_id=_task_id(plugin_ctx),
            session_id=plugin_ctx.context.get("session_id"),
            context=plugin_ctx.context,
        ),
    )


async def prepare_and_dispatch_task_entry_hooks(
    plugin_ctx: AgentPluginContext,
    *,
    task_description: str,
) -> AggregatedHookResult:
    """Task entry: registry rebuild then H5."""
    prepare_hook_task_entry(plugin_ctx, task_description=task_description)
    return await dispatch_user_prompt_submit_hook(plugin_ctx, task_description=task_description)


async def dispatch_build_messages_hook(
    plugin_ctx: AgentPluginContext,
    messages: list[LLMMessage],
) -> None:
    """H13 — after BUILD_MESSAGES phase, before task append (P0-5)."""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.BUILD_MESSAGES,
        build_build_messages_payload(
            agent_id=_agent_id(plugin_ctx),
            message_count=len(messages),
            message_roles=message_roles_summary(messages),
        ),
    )


async def dispatch_user_prompt_in_history_hook(
    plugin_ctx: AgentPluginContext,
    messages: list[LLMMessage],
) -> AggregatedHookResult:
    """H5b — after BUILD_MESSAGES when user task row is present (§17 v2.1)."""
    return await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.USER_PROMPT_IN_HISTORY,
        build_user_prompt_in_history_payload(
            agent_id=_agent_id(plugin_ctx),
            task_id=_task_id(plugin_ctx),
            session_id=plugin_ctx.context.get("session_id"),
            message_count=len(messages),
            message_roles=message_roles_summary(messages),
        ),
    )


def apply_hook_additional_context(
    plugin_ctx: AgentPluginContext,
    messages: list[LLMMessage],
    hook_result: AggregatedHookResult,
) -> None:
    """Merge H5b ``additionalContext`` into messages and plugin_state (§17 v2.1)."""
    from aiecs.llm import LLMMessage

    context_text = hook_result.additional_context
    if not context_text:
        return
    plugin_ctx.plugin_state["hook.additional_context"] = context_text
    insert_at = max(len(messages) - 1, 0)
    messages.insert(
        insert_at,
        LLMMessage(role="system", content=f"[Hook additional context]\n{context_text}"),
    )


async def dispatch_post_task_hook(
    plugin_ctx: AgentPluginContext,
    loop_result: dict[str, Any],
) -> None:
    """H12 — before POST_TASK phase (P0-5)."""
    output = loop_result.get("output") or loop_result.get("final_response") or ""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.POST_TASK,
        build_post_task_payload(
            agent_id=_agent_id(plugin_ctx),
            task_id=_task_id(plugin_ctx),
            success=bool(loop_result.get("success", True)),
            output_preview=str(output),
            reason=loop_result.get("reason"),
        ),
    )


async def dispatch_task_completed_hook(
    plugin_ctx: AgentPluginContext,
    loop_result: dict[str, Any],
) -> None:
    """Optional task-list audit adjacent to H12 (§17 v2.1)."""
    if not loop_result.get("success", True):
        return
    enabled = bool(plugin_ctx.context.get("enable_task_completed_hook"))
    if not enabled and not has_registered_hooks(plugin_ctx, AgentHookEvent.TASK_COMPLETED):
        return
    output = loop_result.get("output") or loop_result.get("final_response") or ""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.TASK_COMPLETED,
        build_task_completed_payload(
            agent_id=_agent_id(plugin_ctx),
            task_id=_task_id(plugin_ctx),
            success=True,
            output_preview=str(output),
        ),
    )


async def run_post_task_phase_with_hooks(
    plugin_manager: PluginManager | None,
    plugin_ctx: AgentPluginContext,
    loop_result: dict[str, Any],
) -> dict[str, Any]:
    """H12 hot-path then POST_TASK plugin phase."""
    await dispatch_post_task_hook(plugin_ctx, loop_result)
    if loop_result.get("success", True):
        await dispatch_task_completed_hook(plugin_ctx, loop_result)
    if plugin_manager is None:
        return loop_result
    from aiecs.domain.agent.plugins.models import PluginPhase

    post_result = await plugin_manager.run_phase(
        PluginPhase.POST_TASK,
        ctx=plugin_ctx,
        result=loop_result,
    )
    return dict(post_result) if isinstance(post_result, dict) else loop_result


async def dispatch_iteration_start_hook(
    plugin_ctx: AgentPluginContext,
    iteration: int,
) -> None:
    """H14 — after inject_iteration_knowledge_into_messages (P0-6)."""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.ITERATION_START,
        build_iteration_start_payload(agent_id=_agent_id(plugin_ctx), iteration=iteration),
    )


def canonical_stop_reason(outcome: ToolLoopIterationOutcome) -> str | None:
    """Map loop outcome to H6 stop_reason enum (H6-03)."""
    if outcome.kind == "final":
        return "tool_uses_empty"
    if outcome.kind == "stop_match":
        if outcome.result and outcome.result.get("stop_reason"):
            return str(outcome.result["stop_reason"])
        return "tool_result_matched"
    return None


def final_response_preview(outcome: ToolLoopIterationOutcome) -> str:
    if outcome.result:
        return str(outcome.result.get("final_response") or outcome.result.get("output") or "")
    return ""


def last_assistant_message_preview(messages: list[Any]) -> str | None:
    """Preview last assistant message content for subagent stop payloads."""
    return _last_assistant_message_preview(messages)


def _last_assistant_message_preview(messages: list[Any]) -> str | None:
    for message in reversed(messages):
        role = getattr(message, "role", None)
        if role == "assistant":
            content = getattr(message, "content", None)
            if content:
                return str(content)[:500]
    return None


async def dispatch_stop_failure_hook(
    plugin_ctx: AgentPluginContext,
    *,
    iteration: int,
    error: str,
    stop_reason: str | None = None,
) -> None:
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.STOP_FAILURE,
        build_stop_failure_payload(
            agent_id=_agent_id(plugin_ctx),
            iteration=iteration,
            error=error,
            stop_reason=stop_reason,
        ),
    )


async def dispatch_stop_hook_for_outcome(
    plugin_ctx: AgentPluginContext,
    outcome: ToolLoopIterationOutcome,
    iteration: int,
    *,
    messages: list[Any] | None = None,
) -> bool:
    """
    H6 — after H15 and both DAWP drains when loop is stopping.

    Returns True when hook aggregate requests preventContinuation (§17 v2.1).
    """
    stop_reason = canonical_stop_reason(outcome)
    if stop_reason is None:
        return False

    payload = build_stop_payload(
        stop_reason=stop_reason,
        iteration=iteration,
        final_response_preview=final_response_preview(outcome),
    )
    if messages is not None:
        preview = _last_assistant_message_preview(messages)
        if preview:
            payload["last_assistant_message"] = preview
        transcript_path = plugin_ctx.context.get("agent_transcript_path")
        if isinstance(transcript_path, str) and transcript_path:
            payload["agent_transcript_path"] = transcript_path

    try:
        result = await dispatch_agent_hook(
            plugin_ctx,
            AgentHookEvent.STOP,
            payload,
        )
    except Exception as exc:
        await dispatch_stop_failure_hook(
            plugin_ctx,
            iteration=iteration,
            error=str(exc),
            stop_reason=stop_reason,
        )
        return False

    if not isinstance(result, AggregatedHookResult):
        return False

    failed = [entry for entry in result.results if not entry.success]
    if failed:
        await dispatch_stop_failure_hook(
            plugin_ctx,
            iteration=iteration,
            error=failed[0].reason or failed[0].output or "stop hook failed",
            stop_reason=stop_reason,
        )
    return result.prevent_continuation


async def dispatch_max_iterations_hook(
    plugin_ctx: AgentPluginContext,
    state: ToolLoopRunState,
    *,
    iteration: int,
    max_iterations: int,
) -> None:
    """H18 — before max-iterations result is returned."""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.MAX_ITERATIONS,
        build_max_iterations_payload(
            agent_id=_agent_id(plugin_ctx),
            iteration=iteration,
            max_iterations=max_iterations,
            tool_calls_count=state.tool_calls_count,
        ),
    )


async def dispatch_prompt_too_long_hook(
    plugin_ctx: AgentPluginContext,
    exc: Exception,
    iteration: int,
) -> None:
    """H19 — when PTL is detected before reactive compact attempt."""
    if not is_prompt_too_long_error(exc):
        return
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.PROMPT_TOO_LONG,
        build_prompt_too_long_payload(
            agent_id=_agent_id(plugin_ctx),
            iteration=iteration,
            error=str(exc),
        ),
    )


async def dispatch_llm_error_hook(
    plugin_ctx: AgentPluginContext,
    exc: Exception,
    iteration: int,
) -> None:
    """H21 — when LLM error is not recovered."""
    await dispatch_agent_hook(
        plugin_ctx,
        AgentHookEvent.LLM_ERROR,
        build_llm_error_payload(
            agent_id=_agent_id(plugin_ctx),
            iteration=iteration,
            error=str(exc),
        ),
    )

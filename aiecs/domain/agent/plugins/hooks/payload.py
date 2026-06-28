# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Per-event hook payload builders (§5.2, §7.6)."""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent

_SECRET_KEY_DENYLIST = frozenset(
    {
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "password",
        "secret",
        "authorization",
        "auth",
        "credential",
        "private_key",
    }
)


def redact_context_keys(context: dict[str, Any]) -> list[str]:
    """Return safe context key names for H5 payload (§5.2)."""
    allowlist = context.get("hook_context_keys_allowlist")
    if isinstance(allowlist, list):
        return [str(key) for key in allowlist if isinstance(key, str)]

    keys: list[str] = []
    for key in context:
        if not isinstance(key, str):
            continue
        if key.startswith("_"):
            continue
        lowered = key.lower()
        if lowered in _SECRET_KEY_DENYLIST:
            continue
        if lowered.endswith(("_token", "_secret", "_password")):
            continue
        keys.append(key)
    return sorted(keys)


def build_user_prompt_submit_payload(
    *,
    prompt: str,
    agent_id: str,
    task_id: str | None,
    session_id: str | None,
    context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.USER_PROMPT_SUBMIT.value,
        "prompt": prompt,
        "task_id": task_id,
        "session_id": session_id,
        "agent_id": agent_id,
        "context_keys": redact_context_keys(context),
    }


def build_session_start_payload(
    *,
    agent_id: str,
    session_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.SESSION_START.value,
        "agent_id": agent_id,
        "session_id": session_id,
    }
    if reason is not None:
        payload["reason"] = reason
    return payload


def build_session_end_payload(
    *,
    agent_id: str,
    session_id: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.SESSION_END.value,
        "agent_id": agent_id,
        "session_id": session_id,
    }
    if reason is not None:
        payload["reason"] = reason
    return payload


def build_pre_tool_use_payload(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    batch_tool_call_count: int = 1,
    batch_index: int = 0,
    assistant_turn_committed: bool = True,
) -> dict[str, Any]:
    """Build H1 payload. ``tool_input`` is included verbatim (no secret redaction)."""
    return {
        "event": AgentHookEvent.PRE_TOOL_USE.value,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_call_id": tool_call_id,
        "iteration": iteration,
        "batch_tool_call_count": batch_tool_call_count,
        "batch_index": batch_index,
        "assistant_turn_committed": assistant_turn_committed,
    }


def build_post_tool_use_payload(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    tool_success: bool,
    result: Any | None = None,
    error: str | None = None,
    blocked: bool = False,
    block_reason: str | None = None,
    permission_denied: bool = False,
    rejection_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.POST_TOOL_USE.value,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_call_id": tool_call_id,
        "iteration": iteration,
        "tool_success": tool_success,
    }
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error
    if blocked:
        payload["blocked"] = True
        if block_reason:
            payload["block_reason"] = block_reason
    if permission_denied:
        payload["permission_denied"] = True
    if rejection_reason is not None:
        payload["rejection_reason"] = rejection_reason
    return payload


def build_permission_request_payload(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    reason: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.PERMISSION_REQUEST.value,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_call_id": tool_call_id,
        "iteration": iteration,
        "reason": reason,
        "task_id": task_id,
    }


def build_permission_denied_payload(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    reason: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.PERMISSION_DENIED.value,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_call_id": tool_call_id,
        "iteration": iteration,
        "reason": reason,
        "task_id": task_id,
    }


def build_post_tool_use_failure_payload(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    error: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.POST_TOOL_USE_FAILURE.value,
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_call_id": tool_call_id,
        "iteration": iteration,
        "error": error,
    }


def build_stop_payload(
    *,
    stop_reason: str,
    iteration: int,
    final_response_preview: str,
) -> dict[str, Any]:
    preview = final_response_preview[:500]
    return {
        "event": AgentHookEvent.STOP.value,
        "stop_reason": stop_reason,
        "iteration": iteration,
        "final_response_preview": preview,
    }


def build_pre_main_loop_payload(*, agent_id: str, task_id: str | None = None) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.PRE_MAIN_LOOP.value,
        "agent_id": agent_id,
        "task_id": task_id,
    }


def build_post_task_payload(
    *,
    agent_id: str,
    task_id: str | None,
    success: bool,
    output_preview: str,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.POST_TASK.value,
        "agent_id": agent_id,
        "task_id": task_id,
        "success": success,
        "output_preview": output_preview[:500],
    }
    if reason is not None:
        payload["reason"] = reason
    return payload


def build_build_messages_payload(
    *,
    agent_id: str,
    message_count: int,
    message_roles: list[str],
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.BUILD_MESSAGES.value,
        "agent_id": agent_id,
        "message_count": message_count,
        "message_roles": message_roles,
    }


def build_iteration_start_payload(*, agent_id: str, iteration: int) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.ITERATION_START.value,
        "agent_id": agent_id,
        "iteration": iteration,
    }


def build_iteration_end_payload(
    *,
    agent_id: str,
    iteration: int,
    pending_count: int = 0,
    pending_workflow_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.ITERATION_END.value,
        "agent_id": agent_id,
        "iteration": iteration,
        "pending_count": pending_count,
    }
    if pending_workflow_ids:
        payload["pending_workflow_ids"] = pending_workflow_ids
    return payload


def build_max_iterations_payload(
    *,
    agent_id: str,
    iteration: int,
    max_iterations: int,
    tool_calls_count: int,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.MAX_ITERATIONS.value,
        "agent_id": agent_id,
        "iteration": iteration,
        "max_iterations": max_iterations,
        "tool_calls_count": tool_calls_count,
    }


def build_prompt_too_long_payload(
    *,
    agent_id: str,
    iteration: int,
    error: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.PROMPT_TOO_LONG.value,
        "agent_id": agent_id,
        "iteration": iteration,
        "error": error[:500],
    }


def build_llm_error_payload(
    *,
    agent_id: str,
    iteration: int,
    error: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.LLM_ERROR.value,
        "agent_id": agent_id,
        "iteration": iteration,
        "error": error[:500],
    }


def build_pre_compact_payload(
    *,
    agent_id: str,
    trigger: str,
    message_count: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.PRE_COMPACT.value,
        "agent_id": agent_id,
        "trigger": trigger,
        "message_count": message_count,
    }
    if metadata:
        layer = metadata.get("layer")
        if layer is not None:
            payload["layer"] = layer
        if metadata.get("formatted_transcript"):
            payload["formatted_transcript"] = True
        session_id = metadata.get("session_id")
        if session_id:
            payload["session_id"] = session_id
        estimated = metadata.get("estimated_tokens")
        if estimated is not None:
            payload["estimated_tokens"] = estimated
    return payload


def build_post_compact_payload(
    *,
    agent_id: str,
    trigger: str,
    summary_preview: str,
    compact_kind: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.POST_COMPACT.value,
        "agent_id": agent_id,
        "trigger": trigger,
        "summary_preview": summary_preview[:500],
    }
    if compact_kind is not None:
        payload["compact_kind"] = compact_kind
    if metadata:
        layer = metadata.get("layer")
        if layer is not None:
            payload["layer"] = layer
        checkpoint = metadata.get("checkpoint")
        if checkpoint:
            payload["checkpoint"] = checkpoint
        estimated = metadata.get("estimated_tokens")
        if estimated is not None:
            payload["estimated_tokens"] = estimated
    return payload


def build_dawp_run_start_payload(
    *,
    agent_id: str,
    workflow_id: str,
    run_id: str,
    placement: str,
    trigger: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.DAWP_RUN_START.value,
        "agent_id": agent_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "placement": placement,
        "trigger": trigger,
    }


def build_dawp_run_end_payload(
    *,
    agent_id: str,
    workflow_id: str,
    run_id: str,
    status: str,
    abort_main: bool,
    last_assistant_message: str | None = None,
    agent_transcript_path: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.DAWP_RUN_END.value,
        "agent_id": agent_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "status": status,
        "abort_main": abort_main,
    }
    if last_assistant_message is not None:
        payload["last_assistant_message"] = last_assistant_message[:500]
    if agent_transcript_path is not None:
        payload["agent_transcript_path"] = agent_transcript_path
    return payload


def build_user_prompt_in_history_payload(
    *,
    agent_id: str,
    task_id: str | None,
    session_id: str | None,
    message_count: int,
    message_roles: list[str],
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.USER_PROMPT_IN_HISTORY.value,
        "agent_id": agent_id,
        "task_id": task_id,
        "session_id": session_id,
        "message_count": message_count,
        "message_roles": message_roles,
    }


def build_subagent_start_payload(
    *,
    agent_id: str,
    workflow_id: str,
    run_id: str,
    placement: str,
    trigger: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.SUBAGENT_START.value,
        "agent_id": agent_id,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "placement": placement,
        "trigger": trigger,
    }


def build_stop_failure_payload(
    *,
    agent_id: str,
    iteration: int,
    error: str,
    stop_reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": AgentHookEvent.STOP_FAILURE.value,
        "agent_id": agent_id,
        "iteration": iteration,
        "error": error[:500],
    }
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    return payload


def build_task_completed_payload(
    *,
    agent_id: str,
    task_id: str | None,
    success: bool,
    output_preview: str,
) -> dict[str, Any]:
    return {
        "event": AgentHookEvent.TASK_COMPLETED.value,
        "agent_id": agent_id,
        "task_id": task_id,
        "success": success,
        "output_preview": output_preview[:500],
    }


def message_roles_summary(messages: list[Any]) -> list[str]:
    roles: list[str] = []
    for message in messages:
        role = getattr(message, "role", None)
        if isinstance(role, str):
            roles.append(role)
    return roles


def with_event_field(event: AgentHookEvent, payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    merged.setdefault("event", event.value)
    return merged

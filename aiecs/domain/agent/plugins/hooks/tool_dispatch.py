# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Shared tool hook dispatch path for H1/H2/H7/H22 (§6.6.1, §7.2, D-V2-06)."""

from __future__ import annotations

import inspect
import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aiecs.domain.agent.plugins.hooks.permission import (
    PermissionOutcome,
    is_mcp_tool,
    parse_permission_decision,
    resolve_permission_decision,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext
    from aiecs.domain.agent.tool_loop_core import ToolLoopCompressionContext

logger = logging.getLogger(__name__)

ExecuteToolFn = Callable[[], Awaitable[Any]]


@dataclass
class ToolConfirmationNeed:
    """Host confirmation required before tool execution (§6.6.1)."""

    reason: str
    deny_immediately: bool = False


@dataclass
class ToolHookDispatchResult:
    """Result of dispatch_tool_with_hooks."""

    pre_result: AggregatedHookResult
    post_result: AggregatedHookResult
    blocked: bool
    block_reason: str
    permission_denied: bool = False
    h1_fired: bool = True
    executed: bool = False
    tool_output: Any | None = None
    tool_content: str | None = None
    error_message: str | None = None
    offloaded: bool = False
    artifact_path: str | None = None


async def resolve_tool_confirmation(
    ctx: AgentPluginContext,
    tool_name: str,
    tool_input: dict[str, Any],
) -> ToolConfirmationNeed | None:
    """Return confirmation need or None when no Host UI gate applies (§6.6.1)."""
    checker = ctx.context.get("hook_permission_checker")
    if callable(checker):
        try:
            result = checker(tool_name, tool_input)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, tuple) and len(result) >= 2:
                needs, reason = result[0], str(result[1] or "")
                if needs:
                    return ToolConfirmationNeed(reason=reason or f"confirmation required for {tool_name}")
        except Exception:
            logger.warning(
                "hook_permission_checker failed; denying %s",
                tool_name,
                exc_info=True,
            )
            return ToolConfirmationNeed(
                reason="hook_permission_checker raised an error",
                deny_immediately=True,
            )

    plugin = ctx.get_plugin("hook")
    if plugin is not None:
        from aiecs.domain.agent.plugins.builtin.hook_plugin import HookPlugin

        if isinstance(plugin, HookPlugin):
            confirmation_reason = plugin.tool_confirmation_reason(tool_name)
            if confirmation_reason:
                return ToolConfirmationNeed(reason=confirmation_reason)

    return None


async def _await_permission_response(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    reason: str,
) -> tuple[bool, str | None]:
    """Return (confirmed, deny_reason_override) after H7 notification (§6.6.1).

    Fail-closed when ``permission_prompt`` is missing or raises (aligned with
    ``permission_checker`` error handling).
    """
    permission_prompt = ctx.context.get("permission_prompt")
    if not callable(permission_prompt):
        logger.warning(
            "permission_prompt missing while ASK path active; denying %s",
            tool_name,
        )
        return False, "permission_prompt callback is not configured"

    try:
        result = permission_prompt(tool_name, reason)
        if inspect.isawaitable(result):
            result = await result
        if bool(result):
            return True, None
        return False, None
    except Exception:
        logger.warning(
            "permission_prompt failed; denying %s",
            tool_name,
            exc_info=True,
        )
        return False, "permission_prompt raised an error"


def _serialize_tool_output(tool_output: Any) -> str:
    if isinstance(tool_output, dict):
        return json.dumps(tool_output, ensure_ascii=False)
    return str(tool_output)


def _extract_artifact_path(content: str) -> str | None:
    match = re.search(r"Full output saved to:\s*(.+)", content)
    if match:
        return match.group(1).strip()
    return None


def _task_id(ctx: AgentPluginContext) -> str | None:
    task = ctx.task or {}
    raw = task.get("task_id")
    return str(raw) if raw is not None else None


async def _dispatch_permission_request(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    reason: str,
    nested: bool,
) -> None:
    from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
    from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
    from aiecs.domain.agent.plugins.hooks.payload import build_permission_request_payload

    payload = build_permission_request_payload(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        reason=reason,
        task_id=_task_id(ctx),
    )
    await dispatch_agent_hook(ctx, AgentHookEvent.PERMISSION_REQUEST, payload, nested=nested)


async def _finalize_permission_denied(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    reason: str,
    nested: bool,
    h1_fired: bool,
) -> ToolHookDispatchResult:
    from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
    from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
    from aiecs.domain.agent.plugins.hooks.payload import (
        build_permission_denied_payload,
        build_post_tool_use_payload,
    )

    denied_payload = build_permission_denied_payload(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        reason=reason,
        task_id=_task_id(ctx),
    )
    await dispatch_agent_hook(ctx, AgentHookEvent.PERMISSION_DENIED, denied_payload, nested=nested)

    post_payload = build_post_tool_use_payload(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        tool_success=False,
        blocked=True,
        block_reason=reason,
        permission_denied=True,
    )
    post_result = await dispatch_agent_hook(
        ctx,
        AgentHookEvent.POST_TOOL_USE,
        post_payload,
        nested=nested,
    )
    error_content = f"Tool execution denied: {reason}"
    return ToolHookDispatchResult(
        pre_result=AggregatedHookResult.empty(),
        post_result=post_result,
        blocked=True,
        block_reason=reason,
        permission_denied=True,
        h1_fired=h1_fired,
        executed=False,
        tool_content=error_content,
        error_message=error_content,
    )


async def _handle_permission_ask(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    reason: str,
    nested: bool,
    h1_fired: bool,
) -> ToolHookDispatchResult | None:
    """Run permission_request → H7 → permission_prompt. Return result on deny."""
    from aiecs.domain.agent.plugins.hooks.notifications import dispatch_host_notification

    await _dispatch_permission_request(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        reason=reason,
        nested=nested,
    )
    await dispatch_host_notification(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        notification_type="permission_prompt",
        reason=reason,
        iteration=iteration,
    )
    confirmed, deny_reason_override = await _await_permission_response(
        ctx,
        tool_name=tool_name,
        reason=reason,
    )
    if not confirmed:
        return await _finalize_permission_denied(
            ctx,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            reason=deny_reason_override or reason,
            nested=nested,
            h1_fired=h1_fired,
        )
    return None


async def _resolve_pre_h1_permission(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    nested: bool,
) -> ToolHookDispatchResult | None:
    """v2 permission_checker + legacy confirmation before H1."""
    decision = await resolve_permission_decision(ctx, tool_name=tool_name, tool_input=tool_input)
    if decision is not None:
        if decision.outcome == PermissionOutcome.DENY:
            return await _finalize_permission_denied(
                ctx,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                iteration=iteration,
                reason=decision.reason,
                nested=nested,
                h1_fired=False,
            )
        if decision.outcome == PermissionOutcome.ASK:
            denied = await _handle_permission_ask(
                ctx,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_call_id=tool_call_id,
                iteration=iteration,
                reason=decision.reason,
                nested=nested,
                h1_fired=False,
            )
            if denied is not None:
                return denied
        return None

    confirmation = await resolve_tool_confirmation(ctx, tool_name, tool_input)
    if confirmation is None:
        return None

    if confirmation.deny_immediately:
        return await _finalize_permission_denied(
            ctx,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            reason=confirmation.reason,
            nested=nested,
            h1_fired=False,
        )

    denied = await _handle_permission_ask(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        reason=confirmation.reason,
        nested=nested,
        h1_fired=False,
    )
    return denied


def _merge_tool_input(
    tool_input: dict[str, Any],
    pre_result: AggregatedHookResult,
) -> dict[str, Any]:
    merged = dict(tool_input)
    updated = pre_result.updated_input
    if isinstance(updated, dict):
        merged.update(updated)
    return merged


async def _apply_post_h1_permission_decision(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int,
    pre_result: AggregatedHookResult,
    nested: bool,
) -> ToolHookDispatchResult | None:
    """Apply ``permissionDecision`` from H1 aggregate before execute."""
    raw = pre_result.permission_decision
    decision = parse_permission_decision(raw)
    if decision is None:
        return None

    if decision.outcome == PermissionOutcome.DENY:
        from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
        from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
        from aiecs.domain.agent.plugins.hooks.payload import build_post_tool_use_payload

        post_payload = build_post_tool_use_payload(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            tool_success=False,
            blocked=True,
            block_reason=decision.reason,
        )
        post_result = await dispatch_agent_hook(
            ctx,
            AgentHookEvent.POST_TOOL_USE,
            post_payload,
            nested=nested,
        )
        error_content = decision.reason or f"pre_tool_use denied {tool_name}"
        return ToolHookDispatchResult(
            pre_result=pre_result,
            post_result=post_result,
            blocked=True,
            block_reason=error_content,
            executed=False,
            tool_content=error_content,
            error_message=error_content,
        )

    if decision.outcome == PermissionOutcome.ASK:
        return await _handle_permission_ask(
            ctx,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            reason=decision.reason,
            nested=nested,
            h1_fired=True,
        )

    return None


def _resolve_post_tool_content(
    *,
    tool_name: str,
    raw_content: str,
    post_result: AggregatedHookResult,
) -> str:
    if is_mcp_tool(tool_name):
        mcp_output = post_result.updated_mcp_output
        if mcp_output:
            return mcp_output
    modified = post_result.modified_output
    if modified:
        return modified
    return raw_content


async def dispatch_tool_with_hooks(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    tool_call_id: str,
    iteration: int = 0,
    batch_tool_call_count: int = 1,
    batch_index: int = 0,
    assistant_turn_committed: bool = True,
    offload: bool = True,
    nested: bool = False,
    compression_ctx: ToolLoopCompressionContext | None = None,
    execute_tool: ExecuteToolFn | None = None,
    kernel_rejection: dict[str, Any] | None = None,
) -> ToolHookDispatchResult:
    """
    Shared permission → H1 → execute → PTUF → H2 (+ H20) path (D-V2-06).

    Permission deny skips H1 and fires H22 + H2. H1 block fires H2 with
    ``blocked=true``. Tool exceptions fire PTUF (when registered) then H2.
    """
    from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook, has_registered_hooks
    from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
    from aiecs.domain.agent.plugins.hooks.payload import (
        build_post_tool_use_failure_payload,
        build_post_tool_use_payload,
        build_pre_tool_use_payload,
    )
    from aiecs.domain.agent.tool_loop_core import apply_tool_output_management

    empty_post = AggregatedHookResult.empty()

    if kernel_rejection is not None:
        pre_payload = build_pre_tool_use_payload(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            batch_tool_call_count=batch_tool_call_count,
            batch_index=batch_index,
            assistant_turn_committed=assistant_turn_committed,
        )
        pre_result = await dispatch_agent_hook(ctx, AgentHookEvent.PRE_TOOL_USE, pre_payload, nested=nested)
        rejection_reason = str(kernel_rejection.get("reason") or "kernel rejection")
        post_payload = build_post_tool_use_payload(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            tool_success=False,
            result=kernel_rejection,
            rejection_reason=rejection_reason,
        )
        post_result = await dispatch_agent_hook(ctx, AgentHookEvent.POST_TOOL_USE, post_payload, nested=nested)
        content = json.dumps(kernel_rejection, ensure_ascii=False)
        return ToolHookDispatchResult(
            pre_result=pre_result,
            post_result=post_result,
            blocked=False,
            block_reason="",
            executed=False,
            tool_content=content,
        )

    denied = await _resolve_pre_h1_permission(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        nested=nested,
    )
    if denied is not None:
        return denied

    pre_payload = build_pre_tool_use_payload(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        batch_tool_call_count=batch_tool_call_count,
        batch_index=batch_index,
        assistant_turn_committed=assistant_turn_committed,
    )
    pre_result = await dispatch_agent_hook(ctx, AgentHookEvent.PRE_TOOL_USE, pre_payload, nested=nested)

    if pre_result.blocked:
        post_payload = build_post_tool_use_payload(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            tool_success=False,
            blocked=True,
            block_reason=pre_result.reason,
        )
        post_result = await dispatch_agent_hook(
            ctx,
            AgentHookEvent.POST_TOOL_USE,
            post_payload,
            nested=nested,
        )
        error_content = pre_result.reason or f"pre_tool_use hook blocked {tool_name}"
        return ToolHookDispatchResult(
            pre_result=pre_result,
            post_result=post_result,
            blocked=True,
            block_reason=error_content,
            executed=False,
            tool_content=error_content,
            error_message=error_content,
        )

    post_h1_denied = await _apply_post_h1_permission_decision(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        pre_result=pre_result,
        nested=nested,
    )
    if post_h1_denied is not None:
        return post_h1_denied

    effective_input = _merge_tool_input(tool_input, pre_result)

    if execute_tool is None:
        return ToolHookDispatchResult(
            pre_result=pre_result,
            post_result=empty_post,
            blocked=False,
            block_reason="",
            executed=False,
        )

    try:
        tool_output = await execute_tool()
    except Exception as exc:
        error_message = f"Tool execution failed: {exc}"
        if has_registered_hooks(ctx, AgentHookEvent.POST_TOOL_USE_FAILURE):
            ptuf_payload = build_post_tool_use_failure_payload(
                tool_name=tool_name,
                tool_input=effective_input,
                tool_call_id=tool_call_id,
                iteration=iteration,
                error=error_message,
            )
            await dispatch_agent_hook(
                ctx,
                AgentHookEvent.POST_TOOL_USE_FAILURE,
                ptuf_payload,
                nested=nested,
            )
        post_payload = build_post_tool_use_payload(
            tool_name=tool_name,
            tool_input=effective_input,
            tool_call_id=tool_call_id,
            iteration=iteration,
            tool_success=False,
            error=error_message,
        )
        post_result = await dispatch_agent_hook(
            ctx,
            AgentHookEvent.POST_TOOL_USE,
            post_payload,
            nested=nested,
        )
        return ToolHookDispatchResult(
            pre_result=pre_result,
            post_result=post_result,
            blocked=False,
            block_reason="",
            executed=False,
            error_message=error_message,
            tool_content=error_message,
        )

    raw_content = _serialize_tool_output(tool_output)
    tool_content = raw_content
    offloaded = False
    artifact_path: str | None = None

    if offload and compression_ctx is not None and compression_ctx.enabled:
        managed = await apply_tool_output_management(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_output=raw_content,
            compression_ctx=compression_ctx,
        )
        if managed != raw_content:
            offloaded = True
            tool_content = managed
            artifact_path = _extract_artifact_path(managed)

    post_payload = build_post_tool_use_payload(
        tool_name=tool_name,
        tool_input=effective_input,
        tool_call_id=tool_call_id,
        iteration=iteration,
        tool_success=True,
        result=tool_output,
    )
    post_result = await dispatch_agent_hook(
        ctx,
        AgentHookEvent.POST_TOOL_USE,
        post_payload,
        nested=nested,
    )

    tool_content = _resolve_post_tool_content(
        tool_name=tool_name,
        raw_content=tool_content,
        post_result=post_result,
    )

    if offloaded:
        h20_payload = {
            "event": AgentHookEvent.TOOL_OUTPUT_OFFLOAD.value,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "iteration": iteration,
            "artifact_path": artifact_path,
            "original_size": len(raw_content),
        }
        await dispatch_agent_hook(ctx, AgentHookEvent.TOOL_OUTPUT_OFFLOAD, h20_payload, nested=nested)

    return ToolHookDispatchResult(
        pre_result=pre_result,
        post_result=post_result,
        blocked=False,
        block_reason="",
        executed=True,
        tool_output=tool_output,
        tool_content=tool_content,
        offloaded=offloaded,
        artifact_path=artifact_path,
    )

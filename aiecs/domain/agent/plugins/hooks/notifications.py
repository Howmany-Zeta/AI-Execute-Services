# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Host notification dispatch for H7 (§6.6, §6.8, v2 executable notification)."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext

logger = logging.getLogger(__name__)


def _build_notification_payload(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    notification_type: str,
    reason: str,
    iteration: int | None,
) -> dict[str, Any]:
    return {
        "event": "notification",
        "notification_type": notification_type,
        "tool_name": tool_name,
        "reason": reason,
        "tool_input": tool_input,
        "iteration": iteration,
        "task_id": ctx.task.get("task_id"),
    }


async def dispatch_host_notification(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    notification_type: str = "permission_prompt",
    reason: str = "",
    iteration: int | None = None,
) -> bool:
    """
    Invoke v2 hooks.json notification hooks then Host callbacks before H1 (§6.6.1).

    Order: registry ``notification`` hooks → ``hook_notification_callback`` →
    type-specific ``permission_prompt`` / ``ask_user_prompt``.
    """
    payload = _build_notification_payload(
        ctx,
        tool_name=tool_name,
        tool_input=tool_input,
        notification_type=notification_type,
        reason=reason,
        iteration=iteration,
    )

    invoked = False
    from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook, has_registered_hooks
    from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent

    if has_registered_hooks(ctx, AgentHookEvent.NOTIFICATION):
        await dispatch_agent_hook(ctx, AgentHookEvent.NOTIFICATION, payload)
        invoked = True

    hook_notification = ctx.context.get("hook_notification_callback")
    if callable(hook_notification):
        try:
            result = hook_notification(payload)
            if inspect.isawaitable(result):
                await result
            invoked = True
        except Exception:
            logger.debug("hook_notification_callback failed", exc_info=True)

    callback_name = {
        "permission_prompt": "permission_prompt",
        "ask_user_prompt": "ask_user_prompt",
    }.get(notification_type, notification_type)

    callback = ctx.context.get(callback_name)
    if callback is None:
        if not invoked:
            logger.debug("host notification skipped: no %s callback", callback_name)
        return invoked
    if not callable(callback):
        logger.debug("host notification skipped: %s is not callable", callback_name)
        return invoked

    try:
        if callback_name == "permission_prompt":
            result = callback(tool_name, reason or notification_type)
        else:
            result = callback(reason or tool_name)
        if inspect.isawaitable(result):
            await result
        return True
    except Exception:
        logger.debug("host notification callback failed", exc_info=True)
        return invoked

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Host context callbacks for HookPlugin H7 + v2 permission stack.

Wire these on ``execute_task(..., context={...})`` alongside HookPlugin config.
See ``docs/developer/HOST_MIGRATION_HOOKS.md``.
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.plugins.hooks.permission import PermissionDecision


async def permission_checker(
    tool_name: str,
    tool_input: dict[str, Any],
    context: dict[str, Any],
) -> PermissionDecision:
    """
    v2 ``permission_checker`` protocol (preferred over ``hook_permission_checker``).

    Return ``PermissionDecision.allow()``, ``.ask(reason)``, or ``.deny(reason)``.
    """
    del context
    if tool_name.startswith("write_") or tool_name.startswith("delete_"):
        path = tool_input.get("path") or tool_input.get("file") or ""
        return PermissionDecision.ask(f"Confirm write/delete on {path or tool_name}")
    return PermissionDecision.allow()


async def hook_permission_checker(tool_name: str, tool_input: dict[str, Any]) -> tuple[bool, str]:
    """
    Legacy v1 stub — maps to ``PermissionDecision.ask`` when confirmation is needed.

    Prefer ``permission_checker`` for new Host integrations.
    """
    decision = await permission_checker(tool_name, tool_input, {})
    if decision.outcome.value == "ask":
        return True, decision.reason
    if decision.outcome.value == "deny":
        return True, decision.reason
    return False, ""


async def permission_prompt(tool_name: str, reason: str) -> bool:
    """
    Host UI gate after ``permission_request`` + H7 ``dispatch_host_notification``.

    Return ``True`` to allow tool execution (proceed to H1); ``False`` to deny (H22 + H2).
    Replace with real modal / SSE round-trip in production.
    """
    del tool_name
    # Demo: auto-approve; production should block until user confirms.
    return bool(reason)


async def hook_notification_callback(payload: dict[str, Any]) -> None:
    """
    Unified H7 notification sink (preferred over legacy ``permission_prompt`` alone).

    Receives ``event``, ``notification_type``, ``tool_name``, ``tool_input``,
    ``reason``, ``iteration``, ``task_id``.
    """
    # Host: emit SSE, show toast, or enqueue approval workflow.
    _ = payload

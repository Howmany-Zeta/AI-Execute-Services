# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Permission checker protocol for v2 tool dispatch (ADR-002 P0, D-V2-01)."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from aiecs.domain.agent.plugins.context import AgentPluginContext

logger = logging.getLogger(__name__)


class PermissionOutcome(str, Enum):
    """Programmatic permission decision for a tool invocation."""

    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass(frozen=True)
class PermissionDecision:
    """Result from ``permission_checker`` on agent task context."""

    outcome: PermissionOutcome
    reason: str = ""

    @classmethod
    def allow(cls) -> PermissionDecision:
        return cls(PermissionOutcome.ALLOW)

    @classmethod
    def ask(cls, reason: str) -> PermissionDecision:
        return cls(PermissionOutcome.ASK, reason or "confirmation required")

    @classmethod
    def deny(cls, reason: str) -> PermissionDecision:
        return cls(PermissionOutcome.DENY, reason or "permission denied")


def parse_permission_decision(value: Any) -> PermissionDecision | None:
    """Parse hook ``permissionDecision`` field (string or object)."""
    if value is None:
        return None
    if isinstance(value, PermissionDecision):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == PermissionOutcome.ALLOW.value:
            return PermissionDecision.allow()
        if normalized == PermissionOutcome.ASK.value:
            return PermissionDecision.ask("confirmation required by hook")
        if normalized == PermissionOutcome.DENY.value:
            return PermissionDecision.deny("denied by hook")
        return None
    if isinstance(value, dict):
        raw = value.get("decision") or value.get("outcome") or value.get("permissionDecision")
        reason = str(value.get("reason") or "")
        parsed = parse_permission_decision(raw)
        if parsed is None:
            return None
        if reason:
            return PermissionDecision(outcome=parsed.outcome, reason=reason)
        return parsed
    return None


@runtime_checkable
class PermissionChecker(Protocol):
    """Host-injected async checker: ``context['permission_checker']``."""

    async def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any],
    ) -> PermissionDecision: ...


async def resolve_permission_decision(
    ctx: AgentPluginContext,
    *,
    tool_name: str,
    tool_input: dict[str, Any],
) -> PermissionDecision | None:
    """
    Resolve v2 ``permission_checker`` when present.

    Returns ``None`` when no checker is configured (legacy confirmation path applies).
    """
    checker = ctx.context.get("permission_checker")
    if not callable(checker):
        return None

    try:
        result = checker(tool_name, tool_input, ctx.context)
        if inspect.isawaitable(result):
            result = await result
    except Exception:
        logger.warning("permission_checker failed; denying %s", tool_name, exc_info=True)
        return PermissionDecision.deny("permission_checker raised an error")

    if isinstance(result, PermissionDecision):
        return result

    if isinstance(result, tuple) and len(result) >= 1:
        first = result[0]
        reason = str(result[1] or "") if len(result) >= 2 else ""
        if isinstance(first, bool):
            if first:
                return PermissionDecision.ask(reason or f"confirmation required for {tool_name}")
            return PermissionDecision.allow()
        if isinstance(first, str):
            parsed = parse_permission_decision(first)
            if parsed is not None:
                return PermissionDecision(outcome=parsed.outcome, reason=reason or parsed.reason)

    parsed = parse_permission_decision(result)
    if parsed is not None:
        return parsed

    logger.debug("permission_checker returned unsupported value: %r", result)
    return None


def is_mcp_tool(tool_name: str) -> bool:
    """MCP-class tools use ``mcp__`` prefix (§17 H2)."""
    return tool_name.startswith("mcp__")

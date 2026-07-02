# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Runtime hook result types (§5.1.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HookResult:
    """Result from a single hook execution."""

    hook_type: str
    success: bool
    output: str = ""
    blocked: bool = False
    reason: str = ""
    modified_output: str | None = None
    updated_input: dict[str, Any] | None = None
    permission_decision: str | None = None
    updated_mcp_output: str | None = None
    additional_context: str | None = None
    continue_allowed: bool | None = None
    prevent_continuation: bool | None = None
    action: str | None = None
    feedback: str | dict[str, Any] | None = None
    feedback_items: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AggregatedHookResult:
    """Aggregated result for a hook event.

    Merge semantics (serial execution order, highest ``priority`` first):

    - ``blocked`` / ``reason``: any hook blocked; first blocked hook's reason wins
    - ``modified_output`` / ``updated_mcp_output``: **last** non-empty value wins
    - ``updated_input``: shallow-merge all hooks in execution order (later keys win)
    - ``permission_decision`` / ``additional_context``: **last** hook with a value wins
      (reverse scan — lowest priority / last executed hook wins)
    - ``prevent_continuation``: last hook with explicit signal wins (reverse scan)
    """

    results: list[HookResult] = field(default_factory=list)

    @classmethod
    def empty(cls) -> AggregatedHookResult:
        return cls(results=[])

    @property
    def blocked(self) -> bool:
        return any(result.blocked for result in self.results)

    @property
    def reason(self) -> str:
        for result in self.results:
            if result.blocked:
                return result.reason or result.output
        return ""

    @property
    def modified_output(self) -> str | None:
        """Last non-empty ``modified_output`` in serial execution order."""
        value: str | None = None
        for result in self.results:
            if result.modified_output:
                value = result.modified_output
        return value

    @property
    def updated_input(self) -> dict[str, Any] | None:
        """Shallow-merge of all ``updated_input`` dicts; later hooks override keys."""
        merged: dict[str, Any] | None = None
        for result in self.results:
            if isinstance(result.updated_input, dict):
                merged = {**(merged or {}), **result.updated_input}
        return merged

    @property
    def permission_decision(self) -> str | None:
        """Last hook's ``permission_decision`` (reverse scan — lowest priority wins)."""
        for result in reversed(self.results):
            if result.permission_decision:
                return result.permission_decision
        return None

    @property
    def updated_mcp_output(self) -> str | None:
        value: str | None = None
        for result in self.results:
            if result.updated_mcp_output:
                value = result.updated_mcp_output
        return value

    @property
    def additional_context(self) -> str | None:
        for result in reversed(self.results):
            if result.additional_context:
                return result.additional_context
        return None

    @property
    def continue_rejected(self) -> bool:
        for result in self.results:
            if result.continue_allowed is False:
                return True
            if result.blocked:
                return True
        return False

    @property
    def prevent_continuation(self) -> bool:
        for result in reversed(self.results):
            if result.prevent_continuation is True:
                return True
            if result.action == "block":
                return True
            if result.continue_allowed is False:
                return True
        return False

    @property
    def gvr_action(self) -> str | None:
        for result in reversed(self.results):
            if result.action:
                return result.action
        return None

    @property
    def gvr_feedback(self) -> str | dict[str, Any] | None:
        for result in reversed(self.results):
            if result.feedback is not None:
                return result.feedback
        return None

    @property
    def gvr_feedback_items(self) -> list[dict[str, Any]]:
        for result in reversed(self.results):
            if result.feedback_items:
                return list(result.feedback_items)
        return []


@dataclass
class HookDispatchContext:
    """Context passed into hook dispatch helpers."""

    agent_id: str
    task_id: str | None = None
    session_id: str | None = None
    workspace: str | None = None
    nested_hooks_enabled: bool = False

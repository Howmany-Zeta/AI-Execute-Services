# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP LoopScope envelope and streaming event helpers.

:class:`LoopScope` is a frozen dataclass attached to every streaming event produced
inside a DAWP run, enabling consumers to distinguish ``kind=dawp`` events from
``kind=main`` events without changing event types (R3, §3.3, §8.1).

Usage::

    scope = LoopScope(
        kind="dawp",
        run_id="dawp-7f3a",
        workflow_id="sales-analysis",
        step_id="gather",
        step_index=0,
        prompt_index=0,
    )
    event = _with_loop_scope({"type": "token", "content": "hello"}, scope)
    # {"type": "token", "content": "hello", "loop_scope": {"kind": "dawp", ...}}

``kind=main`` scopes are backward-compatible: consumers that do not recognise
``loop_scope`` treat events as before (§3.3).

References: CUSTOM_REASONING_PLUGIN_DESIGN.md §3.3, §8.1, §8.1.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class LoopScope:
    """Immutable metadata attached to every streaming event from a main or DAWP loop.

    Attributes:
        kind:          ``"main"`` for the outer agent loop; ``"dawp"`` inside a DAWP run.
        run_id:        UUID string identifying the DAWP run (``None`` for ``kind=main``).
        workflow_id:   ``DAWPWorkflow.metadata.name`` (``None`` for ``kind=main``).
        step_id:       Slug id of the current ``DAWPStep`` (``None`` for ``kind=main``).
        step_index:    0-based index of the step within ``DAWPWorkflow.steps``.
        prompt_index:  ``N`` from the ``<Prompt N>`` source block (matches ``step_index``
                       when prompts are numbered sequentially from 0).
    """

    kind: Literal["main", "dawp"]
    run_id: str | None = None
    workflow_id: str | None = None
    step_id: str | None = None
    step_index: int | None = None
    prompt_index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict; ``None`` fields are omitted."""
        result: dict[str, Any] = {"kind": self.kind}
        if self.run_id is not None:
            result["run_id"] = self.run_id
        if self.workflow_id is not None:
            result["workflow_id"] = self.workflow_id
        if self.step_id is not None:
            result["step_id"] = self.step_id
        if self.step_index is not None:
            result["step_index"] = self.step_index
        if self.prompt_index is not None:
            result["prompt_index"] = self.prompt_index
        return result


# ---------------------------------------------------------------------------
# Singleton convenience scopes
# ---------------------------------------------------------------------------

MAIN_SCOPE = LoopScope(kind="main")
"""Pre-built main-loop scope; reuse to avoid allocation per event."""


# ---------------------------------------------------------------------------
# Event envelope helper
# ---------------------------------------------------------------------------


def _with_loop_scope(event: dict[str, Any], scope: LoopScope) -> dict[str, Any]:
    """Return a new event dict with ``loop_scope`` added; the input is never mutated.

    For ``kind=main`` the ``loop_scope`` key is still added (value ``{"kind": "main"}``).
    Consumers that follow the recommended pattern ``event.get("loop_scope") or {"kind": "main"}``
    (§8.2) handle both styles transparently.

    Args:
        event: Original streaming event dict (must not be modified).
        scope: :class:`LoopScope` to embed.

    Returns:
        Shallow copy of *event* with ``"loop_scope"`` set to ``scope.as_dict()``.
    """
    return {**event, "loop_scope": scope.as_dict()}


# ---------------------------------------------------------------------------
# Boundary event builders  (§3.3, §8.1.1)
# ---------------------------------------------------------------------------


def build_dawp_run_started(
    scope: LoopScope,
    *,
    placement: str,
    trigger: Literal["config", "tool"],
) -> dict[str, Any]:
    """Build a ``dawp_run_started`` boundary event (§3.3, §8.1.1).

    Emitted before the first DAWP step when ``stream_boundary_events=True``.
    Not required by baseworkflow validation; used for UI panel folding.

    Args:
        scope:     :class:`LoopScope` with ``kind="dawp"`` and ``run_id`` set.
        placement: Human-readable placement type string (``"pre_main_loop"`` /
                   ``"on_response_trigger"`` / ``"inline"``).
        trigger:   ``"config"`` or ``"tool"`` (D9).
    """
    return {
        "type": "dawp_run_started",
        "run_id": scope.run_id,
        "workflow_id": scope.workflow_id,
        "placement": placement,
        "trigger": trigger,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "loop_scope": scope.as_dict(),
    }


def build_dawp_run_completed(
    scope: LoopScope,
    *,
    success: bool,
    step_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a ``dawp_run_completed`` boundary event (§3.3, §8.1.1).

    Emitted after the last DAWP step (or on abort) when ``stream_boundary_events=True``.

    Args:
        scope:          :class:`LoopScope` with ``kind="dawp"`` and ``run_id`` set.
        success:        ``True`` if the run completed normally (DAWP Completion Marker seen).
        step_summaries: Per-step outcome dicts (``step_id``, ``success``, ``iterations``).
                        Defaults to an empty list when not provided.
    """
    return {
        "type": "dawp_run_completed",
        "run_id": scope.run_id,
        "step_summaries": step_summaries if step_summaries is not None else [],
        "success": success,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "loop_scope": scope.as_dict(),
    }


def build_dawp_step_started(scope: LoopScope) -> dict[str, Any]:
    """Build an optional ``dawp_step_started`` boundary event (§3.3, §8.1.1)."""
    return {
        "type": "dawp_step_started",
        "run_id": scope.run_id,
        "step_id": scope.step_id,
        "step_index": scope.step_index,
        "prompt_index": scope.prompt_index,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "loop_scope": scope.as_dict(),
    }


def build_dawp_step_completed(scope: LoopScope, *, success: bool) -> dict[str, Any]:
    """Build an optional ``dawp_step_completed`` boundary event (§3.3, §8.1.1)."""
    return {
        "type": "dawp_step_completed",
        "run_id": scope.run_id,
        "step_id": scope.step_id,
        "step_index": scope.step_index,
        "prompt_index": scope.prompt_index,
        "success": success,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "loop_scope": scope.as_dict(),
    }

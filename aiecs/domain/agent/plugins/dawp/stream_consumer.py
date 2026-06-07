# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP streaming consumer helpers for SDK / UI (§8.1.1, §8.2, §14).

When ``stream_boundary_events=True`` on :class:`~builtin.dawp_plugin.DawpPlugin`,
HybridAgent emits ``dawp_run_started`` / ``dawp_run_completed`` boundary events.
Production SDK/UI **must** subscribe to these for panel open/close and run-level
summaries; step content still renders via homomorphic ``token`` / ``tool_result``
events tagged with ``loop_scope.kind=dawp`` (R3).

Usage::

    from aiecs.domain.agent.plugins.dawp.stream_consumer import DawpStreamConsumer

    consumer = DawpStreamConsumer(
        on_run_started=lambda panel: ui.open_dawp_panel(panel.run_id),
        on_run_completed=lambda panel: ui.close_dawp_panel(panel.run_id),
    )

    async for event in agent.execute_task_streaming(task, context):
        consumer.consume(event)
        render_stream_event(event, scope=consumer.effective_scope(event))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

DAWP_RUN_STARTED = "dawp_run_started"
DAWP_RUN_COMPLETED = "dawp_run_completed"
DAWP_STEP_STARTED = "dawp_step_started"
DAWP_STEP_COMPLETED = "dawp_step_completed"
DAWP_BOUNDARY_EVENT_TYPES = frozenset({DAWP_RUN_STARTED, DAWP_RUN_COMPLETED, DAWP_STEP_STARTED, DAWP_STEP_COMPLETED})


@dataclass
class DawpRunPanel:
    """UI/SDK state for one DAWP run (opened on ``dawp_run_started``)."""

    run_id: str
    workflow_id: str | None = None
    placement: str | None = None
    trigger: Literal["config", "tool"] | None = None
    open: bool = True
    success: bool | None = None
    step_summaries: list[dict[str, Any]] = field(default_factory=list)
    active_step_id: str | None = None
    active_step_index: int | None = None


def effective_loop_scope(event: dict[str, Any]) -> dict[str, Any]:
    """Return ``loop_scope`` from *event*, defaulting to ``{"kind": "main"}`` (§8.2)."""
    scope = event.get("loop_scope")
    if isinstance(scope, dict) and scope.get("kind") in ("main", "dawp"):
        return scope
    return {"kind": "main"}


def is_dawp_boundary_event(event: dict[str, Any]) -> bool:
    """True when *event* is a DAWP run- or step-level boundary event."""
    return event.get("type") in DAWP_BOUNDARY_EVENT_TYPES


def is_dawp_scoped_event(event: dict[str, Any]) -> bool:
    """True when *event* belongs to a DAWP segment (boundary or ``loop_scope.kind=dawp``)."""
    if is_dawp_boundary_event(event):
        return True
    return effective_loop_scope(event).get("kind") == "dawp"


class DawpStreamConsumer:
    """Subscribe to optional ``dawp_run_*`` boundary events and track panel state.

    Args:
        on_run_started:   Called when ``dawp_run_started`` is received (open panel).
        on_run_completed: Called when ``dawp_run_completed`` is received (close panel).
        on_step_started:  Called when ``dawp_step_started`` is received (always emitted by runner).
        on_step_completed: Called when ``dawp_step_completed`` is received.
    """

    def __init__(
        self,
        *,
        on_run_started: Callable[[DawpRunPanel], Any] | None = None,
        on_run_completed: Callable[[DawpRunPanel], Any] | None = None,
        on_step_started: Callable[[DawpRunPanel, dict[str, Any]], Any] | None = None,
        on_step_completed: Callable[[DawpRunPanel, dict[str, Any]], Any] | None = None,
    ) -> None:
        self._on_run_started = on_run_started
        self._on_run_completed = on_run_completed
        self._on_step_started = on_step_started
        self._on_step_completed = on_step_completed
        self._panels: dict[str, DawpRunPanel] = {}
        self._order: list[str] = []

    @property
    def panels(self) -> dict[str, DawpRunPanel]:
        """All known runs keyed by ``run_id`` (includes closed runs)."""
        return dict(self._panels)

    @property
    def open_run_ids(self) -> list[str]:
        """``run_id`` values for runs whose panel is still open."""
        return [run_id for run_id in self._order if self._panels[run_id].open]

    def get_panel(self, run_id: str) -> DawpRunPanel | None:
        return self._panels.get(run_id)

    def effective_scope(self, event: dict[str, Any]) -> dict[str, Any]:
        """Shortcut for :func:`effective_loop_scope`."""
        return effective_loop_scope(event)

    def consume(self, event: dict[str, Any]) -> DawpRunPanel | None:
        """Handle one streaming event; returns updated :class:`DawpRunPanel` for boundary events."""
        event_type = event.get("type")
        if event_type == DAWP_RUN_STARTED:
            return self._handle_run_started(event)
        if event_type == DAWP_RUN_COMPLETED:
            return self._handle_run_completed(event)
        if event_type == DAWP_STEP_STARTED:
            return self._handle_step_started(event)
        if event_type == DAWP_STEP_COMPLETED:
            return self._handle_step_completed(event)
        return None

    def _handle_run_started(self, event: dict[str, Any]) -> DawpRunPanel:
        run_id = str(event.get("run_id") or "")
        if not run_id:
            scope = effective_loop_scope(event)
            run_id = str(scope.get("run_id") or "")
        panel = DawpRunPanel(
            run_id=run_id,
            workflow_id=event.get("workflow_id"),
            placement=event.get("placement"),
            trigger=event.get("trigger"),
            open=True,
        )
        self._panels[run_id] = panel
        if run_id not in self._order:
            self._order.append(run_id)
        if self._on_run_started is not None:
            self._on_run_started(panel)
        return panel

    def _handle_run_completed(self, event: dict[str, Any]) -> DawpRunPanel:
        run_id = str(event.get("run_id") or "")
        panel = self._panels.get(run_id)
        if panel is None:
            scope = effective_loop_scope(event)
            run_id = run_id or str(scope.get("run_id") or "")
            panel = DawpRunPanel(run_id=run_id)
            self._panels[run_id] = panel
            if run_id not in self._order:
                self._order.append(run_id)

        summaries = event.get("step_summaries")
        panel.step_summaries = list(summaries) if isinstance(summaries, list) else []
        panel.success = bool(event.get("success"))
        panel.open = False

        if self._on_run_completed is not None:
            self._on_run_completed(panel)
        return panel

    def _panel_for_step_event(self, event: dict[str, Any]) -> DawpRunPanel:
        run_id = str(event.get("run_id") or effective_loop_scope(event).get("run_id") or "")
        panel = self._panels.get(run_id)
        if panel is None:
            panel = DawpRunPanel(run_id=run_id, open=False)
            self._panels[run_id] = panel
            if run_id not in self._order:
                self._order.append(run_id)
        return panel

    def _handle_step_started(self, event: dict[str, Any]) -> DawpRunPanel:
        panel = self._panel_for_step_event(event)
        panel.active_step_id = event.get("step_id")
        step_index = event.get("step_index")
        panel.active_step_index = int(step_index) if step_index is not None else None
        if self._on_step_started is not None:
            self._on_step_started(panel, event)
        return panel

    def _handle_step_completed(self, event: dict[str, Any]) -> DawpRunPanel:
        panel = self._panel_for_step_event(event)
        if event.get("success") is True:
            panel.active_step_id = None
            panel.active_step_index = None
        if self._on_step_completed is not None:
            self._on_step_completed(panel, event)
        return panel

"""
Unit tests for D1-07 — run_scheduler.py (§6.2, §4.2).

Covers:
- pre_main_loop: matching activation enqueued
- pre_main_loop: on_response_trigger activation NOT matched (wrong phase)
- on_response_trigger: matching trigger text → enqueued
- on_response_trigger: token not in text → not enqueued
- on_response_trigger: token in fenced code block → not enqueued (§6.0.2.2)
- on_response_trigger: token in blockquote → not enqueued (§6.0.2.2)
- trigger_once=True: second match does not enqueue (R6 side-effect guard)
- trigger_once=False: second match does enqueue
- two activations same checkpoint → both enqueued (R6 FIFO)
- pre_main_loop phase with on_response_trigger activation → no match
- enqueue_guard blocks run
- enqueue_guard allows run
- plugin_state["dawp.pending"] auto-initialized
- returned list contains only newly enqueued runs
- DawpPendingRun fields: trigger="config", workflow_source="static", drain_mode="on_iteration_end"
- enqueued_at_iteration recorded correctly
"""

from __future__ import annotations

from typing import Any

import pytest

from aiecs.domain.agent.plugins.dawp.run_scheduler import schedule_at_checkpoint
from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    DawpPendingRun,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_TRIGGER = "<START_OODA_REVIEW>"
_TRIGGER2 = "<START_SECOND_REVIEW>"
_WF_ID = "ooda-strategic"


def _pre_main_activation(workflow_id: str = _WF_ID) -> tuple[str, Activation]:
    return (
        workflow_id,
        Activation(placement=PreMainLoopPlacement()),
    )


def _response_trigger_activation(
    trigger: str = _TRIGGER,
    trigger_once: bool = True,
    workflow_id: str = _WF_ID,
) -> tuple[str, Activation]:
    return (
        workflow_id,
        Activation(
            placement=OnResponseTriggerPlacement(
                dawp_trigger=trigger,
                trigger_once=trigger_once,
            ),
        ),
    )


def _plugin_state() -> dict[str, Any]:
    return {}


# ---------------------------------------------------------------------------
# pre_main_loop phase
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreMainLoop:
    def test_pre_main_loop_activation_enqueued(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert len(runs) == 1

    def test_pre_main_loop_run_fields(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
            iteration=0,
        )
        run = runs[0]
        assert run.trigger == "config"
        assert run.workflow_source == "static"
        assert run.workflow_id == _WF_ID
        assert run.drain_mode == "on_iteration_end"
        assert run.enqueued_at_iteration == 0

    def test_on_response_trigger_activation_skipped_at_pre_main_loop(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert runs == []

    def test_pre_main_loop_adds_to_pending_queue(self) -> None:
        state = _plugin_state()
        schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert len(state["dawp.pending"]) == 1

    def test_pending_queue_auto_initialized(self) -> None:
        state: dict[str, Any] = {}
        assert "dawp.pending" not in state
        schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert "dawp.pending" in state

    def test_iteration_recorded(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
            iteration=7,
        )
        assert runs[0].enqueued_at_iteration == 7


# ---------------------------------------------------------------------------
# on_iteration_end / on_response_trigger phase
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOnResponseTrigger:
    def test_trigger_in_text_enqueues(self) -> None:
        state = _plugin_state()
        text = f"I have finished.\n{_TRIGGER}"
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=text,
        )
        assert len(runs) == 1

    def test_trigger_not_in_text_no_enqueue(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text="No trigger here.",
        )
        assert runs == []

    def test_none_assistant_text_no_enqueue(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=None,
        )
        assert runs == []

    def test_trigger_in_fenced_code_not_matched(self) -> None:
        """Token inside ``` fence must not trigger (§6.0.2.2)."""
        state = _plugin_state()
        text = f"Example:\n```\n{_TRIGGER}\n```\nAll done."
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=text,
        )
        assert runs == []

    def test_trigger_in_blockquote_not_matched(self) -> None:
        """Token inside > blockquote must not trigger (§6.0.2.2)."""
        state = _plugin_state()
        text = f"> {_TRIGGER}\nSome other text."
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=text,
        )
        assert runs == []

    def test_run_fields_correct(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_response_trigger_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=f"Done.\n{_TRIGGER}",
            iteration=3,
        )
        run = runs[0]
        assert run.trigger == "config"
        assert run.workflow_source == "static"
        assert run.workflow_id == _WF_ID
        assert run.drain_mode == "on_iteration_end"
        assert run.enqueued_at_iteration == 3

    def test_pre_main_loop_activation_skipped_at_on_iteration_end(self) -> None:
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=f"text {_TRIGGER}",
        )
        assert runs == []


# ---------------------------------------------------------------------------
# trigger_once guard (§4.2.1)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTriggerOnce:
    def test_trigger_once_second_call_not_enqueued(self) -> None:
        """trigger_once=True: second match on same trigger → not enqueued."""
        state = _plugin_state()
        text = f"Done.\n{_TRIGGER}"
        activation_pair = _response_trigger_activation(trigger_once=True)

        first = schedule_at_checkpoint(
            [activation_pair], phase="on_iteration_end",
            plugin_state=state, assistant_text=text,
        )
        second = schedule_at_checkpoint(
            [activation_pair], phase="on_iteration_end",
            plugin_state=state, assistant_text=text,
        )

        assert len(first) == 1
        assert second == []
        assert len(state["dawp.pending"]) == 1  # only one run total

    def test_trigger_once_false_second_call_enqueued(self) -> None:
        """trigger_once=False: second match → also enqueued."""
        state = _plugin_state()
        text = f"Done.\n{_TRIGGER}"
        activation_pair = _response_trigger_activation(trigger_once=False)

        first = schedule_at_checkpoint(
            [activation_pair], phase="on_iteration_end",
            plugin_state=state, assistant_text=text,
        )
        second = schedule_at_checkpoint(
            [activation_pair], phase="on_iteration_end",
            plugin_state=state, assistant_text=text,
        )

        assert len(first) == 1
        assert len(second) == 1
        assert len(state["dawp.pending"]) == 2

    def test_trigger_once_flag_stored_in_plugin_state(self) -> None:
        state = _plugin_state()
        text = f"Done.\n{_TRIGGER}"
        schedule_at_checkpoint(
            [_response_trigger_activation(trigger_once=True)],
            phase="on_iteration_end",
            plugin_state=state,
            assistant_text=text,
        )
        assert state.get(f"dawp.triggered.{_TRIGGER}") is True

    def test_different_triggers_independent_once_guards(self) -> None:
        """Two different triggers each fire once independently."""
        state = _plugin_state()
        text = f"Done.\n{_TRIGGER}\n{_TRIGGER2}"
        pairs = [
            _response_trigger_activation(trigger=_TRIGGER, trigger_once=True, workflow_id="wf-a"),
            _response_trigger_activation(trigger=_TRIGGER2, trigger_once=True, workflow_id="wf-b"),
        ]

        first = schedule_at_checkpoint(
            pairs, phase="on_iteration_end", plugin_state=state, assistant_text=text,
        )
        second = schedule_at_checkpoint(
            pairs, phase="on_iteration_end", plugin_state=state, assistant_text=text,
        )

        assert len(first) == 2  # both fire on first call
        assert second == []     # both blocked on second call


# ---------------------------------------------------------------------------
# R6: Multiple activations same checkpoint → all enqueued (FIFO)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMultipleActivations:
    def test_two_pre_main_loop_activations_both_enqueued(self) -> None:
        """R6: Two pre_main_loop activations → both enqueued in order."""
        state = _plugin_state()
        runs = schedule_at_checkpoint(
            [_pre_main_activation("wf-a"), _pre_main_activation("wf-b")],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert len(runs) == 2
        assert runs[0].workflow_id == "wf-a"
        assert runs[1].workflow_id == "wf-b"

    def test_two_response_trigger_activations_both_enqueued(self) -> None:
        """R6: Two matching on_response_trigger activations → both enqueued."""
        state = _plugin_state()
        text = f"Done.\n{_TRIGGER}\n{_TRIGGER2}"
        pairs = [
            _response_trigger_activation(trigger=_TRIGGER, trigger_once=False, workflow_id="wf-a"),
            _response_trigger_activation(trigger=_TRIGGER2, trigger_once=False, workflow_id="wf-b"),
        ]
        runs = schedule_at_checkpoint(
            pairs, phase="on_iteration_end", plugin_state=state, assistant_text=text,
        )
        assert len(runs) == 2
        assert runs[0].workflow_id == "wf-a"
        assert runs[1].workflow_id == "wf-b"

    def test_fifo_order_in_pending_queue(self) -> None:
        """Runs are appended in workflow_activations order."""
        state = _plugin_state()
        # Pre-populate the queue with one existing run
        existing = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="existing",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        state["dawp.pending"] = [existing]

        schedule_at_checkpoint(
            [_pre_main_activation("wf-a"), _pre_main_activation("wf-b")],
            phase="pre_main_loop",
            plugin_state=state,
        )

        queue = state["dawp.pending"]
        assert queue[0].workflow_id == "existing"  # pre-existing preserved
        assert queue[1].workflow_id == "wf-a"
        assert queue[2].workflow_id == "wf-b"

    def test_only_newly_enqueued_returned(self) -> None:
        """Return value contains only NEW runs, not pre-existing queue contents."""
        state = _plugin_state()
        existing = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="pre-existing",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        state["dawp.pending"] = [existing]

        new_runs = schedule_at_checkpoint(
            [_pre_main_activation("wf-new")],
            phase="pre_main_loop",
            plugin_state=state,
        )
        assert len(new_runs) == 1
        assert new_runs[0].workflow_id == "wf-new"


# ---------------------------------------------------------------------------
# enqueue_guard (D11 hook)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnqueueGuard:
    def test_guard_blocks_run(self) -> None:
        state = _plugin_state()
        guard_called: list[bool] = []

        def blocking_guard(run: DawpPendingRun, ps: dict) -> bool:
            guard_called.append(True)
            return False

        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
            enqueue_guard=blocking_guard,
        )

        assert runs == []
        assert state.get("dawp.pending", []) == []
        assert guard_called == [True]

    def test_guard_allows_run(self) -> None:
        state = _plugin_state()

        def allowing_guard(run: DawpPendingRun, ps: dict) -> bool:
            return True

        runs = schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
            enqueue_guard=allowing_guard,
        )

        assert len(runs) == 1

    def test_guard_receives_pending_run_and_plugin_state(self) -> None:
        state = _plugin_state()
        captured: list[tuple[DawpPendingRun, dict]] = []

        def capturing_guard(run: DawpPendingRun, ps: dict) -> bool:
            captured.append((run, ps))
            return True

        schedule_at_checkpoint(
            [_pre_main_activation()],
            phase="pre_main_loop",
            plugin_state=state,
            enqueue_guard=capturing_guard,
        )

        assert len(captured) == 1
        run, ps = captured[0]
        assert isinstance(run, DawpPendingRun)
        assert ps is state

    def test_guard_blocks_some_allows_others(self) -> None:
        """Guard can selectively allow/block per workflow."""
        state = _plugin_state()

        def selective_guard(run: DawpPendingRun, ps: dict) -> bool:
            return run.workflow_id == "wf-allowed"

        runs = schedule_at_checkpoint(
            [_pre_main_activation("wf-blocked"), _pre_main_activation("wf-allowed")],
            phase="pre_main_loop",
            plugin_state=state,
            enqueue_guard=selective_guard,
        )

        assert len(runs) == 1
        assert runs[0].workflow_id == "wf-allowed"
        assert len(state["dawp.pending"]) == 1

"""
Unit tests for DAWP SDK stream consumer (§8.2, §14).

Verifies DawpStreamConsumer subscribes to dawp_run_started / dawp_run_completed
and tracks panel state for SDK/UI integration.
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.loop_scope import (
    LoopScope,
    build_dawp_run_completed,
    build_dawp_run_started,
    build_dawp_step_completed,
    build_dawp_step_started,
)
from aiecs.domain.agent.plugins.dawp.stream_consumer import (
    DAWP_BOUNDARY_EVENT_TYPES,
    DawpStreamConsumer,
    effective_loop_scope,
    is_dawp_boundary_event,
    is_dawp_scoped_event,
)


def _scope() -> LoopScope:
    return LoopScope(kind="dawp", run_id="run-abc", workflow_id="test-wf", step_index=0)


@pytest.mark.unit
class TestStreamConsumerHelpers:
    def test_effective_loop_scope_defaults_main(self) -> None:
        assert effective_loop_scope({"type": "token", "content": "hi"}) == {"kind": "main"}

    def test_effective_loop_scope_preserves_dawp(self) -> None:
        event = {"type": "token", "loop_scope": {"kind": "dawp", "run_id": "r1"}}
        assert effective_loop_scope(event)["kind"] == "dawp"
        assert effective_loop_scope(event)["run_id"] == "r1"

    def test_is_dawp_boundary_event(self) -> None:
        assert is_dawp_boundary_event({"type": "dawp_run_started"})
        assert is_dawp_boundary_event({"type": "dawp_run_completed"})
        assert not is_dawp_boundary_event({"type": "token"})

    def test_is_dawp_scoped_event(self) -> None:
        assert is_dawp_scoped_event({"type": "dawp_run_started"})
        assert is_dawp_scoped_event({"type": "token", "loop_scope": {"kind": "dawp"}})
        assert not is_dawp_scoped_event({"type": "token"})

    def test_boundary_event_types_frozen(self) -> None:
        assert "dawp_run_started" in DAWP_BOUNDARY_EVENT_TYPES
        assert "dawp_run_completed" in DAWP_BOUNDARY_EVENT_TYPES
        assert "dawp_step_started" in DAWP_BOUNDARY_EVENT_TYPES
        assert "dawp_step_completed" in DAWP_BOUNDARY_EVENT_TYPES

    def test_step_started_updates_active_step(self) -> None:
        consumer = DawpStreamConsumer()
        scope = LoopScope(
            kind="dawp", run_id="run-1", workflow_id="wf", step_id="gather", step_index=0
        )
        panel = consumer.consume(build_dawp_step_started(scope))
        assert panel is not None
        assert panel.active_step_id == "gather"
        assert panel.active_step_index == 0


@pytest.mark.unit
class TestDawpStreamConsumer:
    def test_run_started_opens_panel(self) -> None:
        started_calls: list[str] = []
        consumer = DawpStreamConsumer(
            on_run_started=lambda p: started_calls.append(p.run_id),
        )
        event = build_dawp_run_started(_scope(), placement="pre_main_loop", trigger="config")
        panel = consumer.consume(event)

        assert panel is not None
        assert panel.open is True
        assert panel.run_id == "run-abc"
        assert panel.workflow_id == "test-wf"
        assert panel.placement == "pre_main_loop"
        assert panel.trigger == "config"
        assert started_calls == ["run-abc"]
        assert consumer.open_run_ids == ["run-abc"]

    def test_run_completed_closes_panel(self) -> None:
        completed_calls: list[tuple[str, bool]] = []
        consumer = DawpStreamConsumer(
            on_run_completed=lambda p: completed_calls.append((p.run_id, bool(p.success))),
        )
        scope = _scope()
        consumer.consume(build_dawp_run_started(scope, placement="inline", trigger="tool"))
        panel = consumer.consume(build_dawp_run_completed(scope, success=True, step_summaries=[]))

        assert panel is not None
        assert panel.open is False
        assert panel.success is True
        assert completed_calls == [("run-abc", True)]
        assert consumer.open_run_ids == []

    def test_completed_without_started_creates_panel(self) -> None:
        consumer = DawpStreamConsumer()
        panel = consumer.consume(build_dawp_run_completed(_scope(), success=False))

        assert panel is not None
        assert panel.run_id == "run-abc"
        assert panel.open is False
        assert panel.success is False

    def test_multiple_runs_tracked_in_order(self) -> None:
        consumer = DawpStreamConsumer()
        s1 = LoopScope(kind="dawp", run_id="run-1", workflow_id="wf-a")
        s2 = LoopScope(kind="dawp", run_id="run-2", workflow_id="wf-b")

        consumer.consume(build_dawp_run_started(s1, placement="pre_main_loop", trigger="config"))
        consumer.consume(build_dawp_run_started(s2, placement="inline", trigger="tool"))
        assert consumer.open_run_ids == ["run-1", "run-2"]

        consumer.consume(build_dawp_run_completed(s1, success=True))
        assert consumer.open_run_ids == ["run-2"]

    def test_non_boundary_event_returns_none(self) -> None:
        consumer = DawpStreamConsumer()
        assert consumer.consume({"type": "token", "content": "x"}) is None
        assert consumer.consume({"type": "iteration_start", "iteration": 1}) is None

    def test_effective_scope_delegates(self) -> None:
        consumer = DawpStreamConsumer()
        event = {"type": "token", "loop_scope": {"kind": "dawp", "run_id": "r"}}
        assert consumer.effective_scope(event)["kind"] == "dawp"

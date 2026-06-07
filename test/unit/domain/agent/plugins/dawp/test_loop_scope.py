"""
Unit tests for aiecs/domain/agent/plugins/dawp/loop_scope.py (D0-02).

Covers:
- LoopScope construction and as_dict serialisation
- kind=dawp with all optional fields populated
- kind=main backward-compatible (omits None fields; envelope key still added)
- _with_loop_scope: immutability guarantee + correct output
- MAIN_SCOPE singleton
- Boundary event builders: dawp_run_started / dawp_run_completed /
  dawp_step_started / dawp_step_completed
"""

import pytest

from aiecs.domain.agent.plugins.dawp.loop_scope import (
    MAIN_SCOPE,
    LoopScope,
    _with_loop_scope,
    build_dawp_run_completed,
    build_dawp_run_started,
    build_dawp_step_completed,
    build_dawp_step_started,
)


# ---------------------------------------------------------------------------
# LoopScope — kind=dawp
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoopScopeDawp:
    def test_all_fields_set(self):
        scope = LoopScope(
            kind="dawp",
            run_id="dawp-7f3a",
            workflow_id="sales-analysis",
            step_id="gather",
            step_index=0,
            prompt_index=0,
        )
        assert scope.kind == "dawp"
        assert scope.run_id == "dawp-7f3a"
        assert scope.workflow_id == "sales-analysis"
        assert scope.step_id == "gather"
        assert scope.step_index == 0
        assert scope.prompt_index == 0

    def test_as_dict_includes_all_fields(self):
        scope = LoopScope(
            kind="dawp",
            run_id="dawp-7f3a",
            workflow_id="sales-analysis",
            step_id="gather",
            step_index=1,
            prompt_index=1,
        )
        d = scope.as_dict()
        assert d == {
            "kind": "dawp",
            "run_id": "dawp-7f3a",
            "workflow_id": "sales-analysis",
            "step_id": "gather",
            "step_index": 1,
            "prompt_index": 1,
        }

    def test_as_dict_omits_none_fields(self):
        scope = LoopScope(kind="dawp", run_id="dawp-abc")
        d = scope.as_dict()
        assert "workflow_id" not in d
        assert "step_id" not in d
        assert "step_index" not in d
        assert "prompt_index" not in d
        assert d["run_id"] == "dawp-abc"

    def test_frozen_immutable(self):
        scope = LoopScope(kind="dawp", run_id="x")
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            scope.run_id = "y"  # type: ignore[misc]

    def test_equality(self):
        a = LoopScope(kind="dawp", run_id="r", step_index=0, prompt_index=0)
        b = LoopScope(kind="dawp", run_id="r", step_index=0, prompt_index=0)
        assert a == b

    def test_inequality_different_step(self):
        a = LoopScope(kind="dawp", run_id="r", step_index=0, prompt_index=0)
        b = LoopScope(kind="dawp", run_id="r", step_index=1, prompt_index=1)
        assert a != b


# ---------------------------------------------------------------------------
# LoopScope — kind=main (backward compatibility)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoopScopeMain:
    def test_kind_main_minimal(self):
        scope = LoopScope(kind="main")
        assert scope.run_id is None
        assert scope.step_id is None

    def test_as_dict_main_only_has_kind(self):
        """Backward-compatible: consumers receive {"kind": "main"} with no extra noise."""
        d = LoopScope(kind="main").as_dict()
        assert d == {"kind": "main"}

    def test_main_scope_singleton(self):
        assert MAIN_SCOPE.kind == "main"
        assert MAIN_SCOPE.as_dict() == {"kind": "main"}

    def test_consumer_pattern_fallback(self):
        """§8.2 consumer pattern: event.get("loop_scope") or {"kind": "main"}."""
        event_without_scope: dict = {"type": "token", "content": "hello"}
        scope_dict = event_without_scope.get("loop_scope") or {"kind": "main"}
        assert scope_dict["kind"] == "main"


# ---------------------------------------------------------------------------
# _with_loop_scope
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWithLoopScope:
    def test_adds_loop_scope_key(self):
        scope = LoopScope(kind="dawp", run_id="r1", step_id="step-a", step_index=0, prompt_index=0)
        event = {"type": "token", "content": "hi"}
        result = _with_loop_scope(event, scope)
        assert "loop_scope" in result
        assert result["loop_scope"]["kind"] == "dawp"
        assert result["loop_scope"]["run_id"] == "r1"

    def test_does_not_mutate_input_event(self):
        scope = LoopScope(kind="dawp", run_id="r1")
        event = {"type": "token", "content": "hi"}
        original_keys = set(event.keys())
        _with_loop_scope(event, scope)
        assert set(event.keys()) == original_keys
        assert "loop_scope" not in event

    def test_preserves_all_original_keys(self):
        scope = LoopScope(kind="main")
        event = {"type": "tool_result", "result": "ok", "timestamp": "2026-01-01T00:00:00"}
        result = _with_loop_scope(event, scope)
        assert result["type"] == "tool_result"
        assert result["result"] == "ok"
        assert result["timestamp"] == "2026-01-01T00:00:00"

    def test_with_main_scope(self):
        result = _with_loop_scope({"type": "iteration_start"}, MAIN_SCOPE)
        assert result["loop_scope"] == {"kind": "main"}

    def test_overwrites_existing_loop_scope(self):
        """If event already had loop_scope, the new scope replaces it."""
        event = {"type": "token", "loop_scope": {"kind": "main"}}
        dawp_scope = LoopScope(kind="dawp", run_id="r2")
        result = _with_loop_scope(event, dawp_scope)
        assert result["loop_scope"]["kind"] == "dawp"
        assert result["loop_scope"]["run_id"] == "r2"

    def test_returns_new_dict_not_same_object(self):
        event = {"type": "token"}
        result = _with_loop_scope(event, MAIN_SCOPE)
        assert result is not event


# ---------------------------------------------------------------------------
# Boundary event builders
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBoundaryEvents:
    def _dawp_scope(self) -> LoopScope:
        return LoopScope(
            kind="dawp",
            run_id="dawp-abc",
            workflow_id="ooda",
            step_id="observe",
            step_index=0,
            prompt_index=0,
        )

    def test_run_started_structure(self):
        scope = self._dawp_scope()
        event = build_dawp_run_started(scope, placement="pre_main_loop", trigger="config")
        assert event["type"] == "dawp_run_started"
        assert event["run_id"] == "dawp-abc"
        assert event["workflow_id"] == "ooda"
        assert event["placement"] == "pre_main_loop"
        assert event["trigger"] == "config"
        assert "timestamp" in event
        assert event["loop_scope"]["kind"] == "dawp"

    def test_run_started_tool_trigger(self):
        scope = self._dawp_scope()
        event = build_dawp_run_started(scope, placement="inline", trigger="tool")
        assert event["trigger"] == "tool"

    def test_run_completed_success(self):
        scope = self._dawp_scope()
        summaries = [{"step_id": "observe", "success": True, "iterations": 2}]
        event = build_dawp_run_completed(scope, success=True, step_summaries=summaries)
        assert event["type"] == "dawp_run_completed"
        assert event["run_id"] == "dawp-abc"
        assert event["success"] is True
        assert event["step_summaries"] == summaries
        assert "timestamp" in event

    def test_run_completed_no_summaries_defaults_to_empty_list(self):
        scope = self._dawp_scope()
        event = build_dawp_run_completed(scope, success=False)
        assert event["step_summaries"] == []
        assert event["success"] is False

    def test_step_started_structure(self):
        scope = self._dawp_scope()
        event = build_dawp_step_started(scope)
        assert event["type"] == "dawp_step_started"
        assert event["run_id"] == "dawp-abc"
        assert event["step_id"] == "observe"
        assert event["step_index"] == 0
        assert event["prompt_index"] == 0
        assert "timestamp" in event

    def test_step_completed_structure(self):
        scope = self._dawp_scope()
        event = build_dawp_step_completed(scope, success=True)
        assert event["type"] == "dawp_step_completed"
        assert event["success"] is True
        assert event["step_id"] == "observe"

    def test_boundary_events_carry_loop_scope(self):
        """All boundary events embed loop_scope (§3.3)."""
        scope = self._dawp_scope()
        for event in [
            build_dawp_run_started(scope, placement="pre_main_loop", trigger="config"),
            build_dawp_run_completed(scope, success=True),
            build_dawp_step_started(scope),
            build_dawp_step_completed(scope, success=True),
        ]:
            assert "loop_scope" in event, f"Missing loop_scope in {event['type']}"
            assert event["loop_scope"]["kind"] == "dawp"

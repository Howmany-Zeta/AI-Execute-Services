"""
Unit tests for aiecs/domain/agent/plugins/dawp/schema.py (D0-01).

Covers valid construction and validation rejection for:
- PreMainLoopPlacement / OnResponseTriggerPlacement / Placement discriminated union
- Contract marker format and uniqueness rules
- MarkerCompletion / DAWPStep
- Activation with both placement types
- DAWPWorkflow composition
- DawpPendingRun trigger/drain_mode literals
- DawpDocumentError exception attributes
"""

import pytest
from pydantic import TypeAdapter, ValidationError

from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpDocumentError,
    DawpPendingRun,
    MarkerCompletion,
    OnResponseTriggerPlacement,
    Placement,
    PreMainLoopPlacement,
    WorkflowMetadata,
    WorkflowSpec,
)

_PLACEMENT_TA = TypeAdapter(Placement)


# ---------------------------------------------------------------------------
# Placement — PreMainLoop
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPreMainLoopPlacement:
    def test_default_type(self):
        p = PreMainLoopPlacement()
        assert p.type == "pre_main_loop"

    def test_via_discriminated_union(self):
        p = _PLACEMENT_TA.validate_python({"type": "pre_main_loop"})
        assert isinstance(p, PreMainLoopPlacement)


# ---------------------------------------------------------------------------
# Placement — OnResponseTrigger
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOnResponseTriggerPlacement:
    def test_valid_trigger(self):
        p = OnResponseTriggerPlacement(dawp_trigger="<START_OODA>")
        assert p.type == "on_response_trigger"
        assert p.dawp_trigger == "<START_OODA>"
        assert p.trigger_once is True

    def test_trigger_once_explicit_false(self):
        p = OnResponseTriggerPlacement(dawp_trigger="<START_X>", trigger_once=False)
        assert p.trigger_once is False

    def test_missing_dawp_trigger_raises(self):
        with pytest.raises(ValidationError):
            OnResponseTriggerPlacement()  # type: ignore[call-arg]

    def test_lowercase_trigger_rejected(self):
        with pytest.raises(ValidationError, match="must match"):
            OnResponseTriggerPlacement(dawp_trigger="<start_ooda>")

    def test_trigger_exceeds_25_chars_rejected(self):
        long_token = "<" + "A" * 24 + ">"  # 27 chars total
        with pytest.raises(ValidationError, match="exceeds 25 chars"):
            OnResponseTriggerPlacement(dawp_trigger=long_token)

    def test_trigger_exactly_25_chars_accepted(self):
        token = "<" + "A" * 23 + ">"  # 25 chars total
        p = OnResponseTriggerPlacement(dawp_trigger=token)
        assert p.dawp_trigger == token

    def test_no_angle_brackets_rejected(self):
        with pytest.raises(ValidationError, match="must match"):
            OnResponseTriggerPlacement(dawp_trigger="START_OODA")


# ---------------------------------------------------------------------------
# Placement — rejected legacy types
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRejectedPlacementTypes:
    def test_after_response_index_rejected(self):
        """after_response_index is not a valid Placement type (removed v2.3, §4.2)."""
        with pytest.raises(ValidationError):
            _PLACEMENT_TA.validate_python({"type": "after_response_index", "index": 2})

    def test_on_tool_result_trigger_rejected(self):
        """on_tool_result_trigger is not a valid Placement type (removed v2.3, §4.2)."""
        with pytest.raises(ValidationError):
            _PLACEMENT_TA.validate_python({"type": "on_tool_result_trigger"})

    def test_unknown_type_rejected(self):
        with pytest.raises(ValidationError):
            _PLACEMENT_TA.validate_python({"type": "runtime"})


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContract:
    def test_valid_contract(self):
        c = Contract(
            action="Follow the process.",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
        )
        assert c.prompt_marker == "<STEP_DONE>"
        assert c.dawp_marker == "<DAWP_HANDOFF>"

    def test_markers_must_differ(self):
        with pytest.raises(ValidationError, match="must differ"):
            Contract(action="x", prompt_marker="<SAME>", dawp_marker="<SAME>")

    def test_prompt_marker_missing_brackets_rejected(self):
        with pytest.raises(ValidationError, match="must match"):
            Contract(action="x", prompt_marker="STEP_DONE", dawp_marker="<DAWP_DONE>")

    def test_dawp_marker_exceeds_25_chars_rejected(self):
        long = "<" + "A" * 24 + ">"  # 27 chars
        with pytest.raises(ValidationError, match="exceeds 25 chars"):
            Contract(action="x", prompt_marker="<STEP_DONE>", dawp_marker=long)

    def test_prompt_marker_spaces_rejected(self):
        with pytest.raises(ValidationError, match="must match"):
            Contract(action="x", prompt_marker="<STEP DONE>", dawp_marker="<DAWP_DONE>")

    def test_lowercase_chars_in_dawp_marker_rejected(self):
        with pytest.raises(ValidationError, match="must match"):
            Contract(action="x", prompt_marker="<STEP_DONE>", dawp_marker="<dawp_done>")

    def test_ooda_naming_pattern(self):
        """Workflow-prefixed markers as recommended in §6.0.2.1."""
        c = Contract(
            action="Observe, Orient, Decide, Act.",
            prompt_marker="<OODA_STEP_DONE>",
            dawp_marker="<OODA_COMPLETE>",
        )
        assert c.prompt_marker == "<OODA_STEP_DONE>"
        assert c.dawp_marker == "<OODA_COMPLETE>"


# ---------------------------------------------------------------------------
# MarkerCompletion
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMarkerCompletion:
    def test_not_last(self):
        mc = MarkerCompletion(prompt_marker="<STEP_DONE>", dawp_marker="<DAWP_DONE>", is_last=False)
        assert mc.type == "marker"
        assert mc.is_last is False

    def test_is_last(self):
        mc = MarkerCompletion(prompt_marker="<STEP_DONE>", dawp_marker="<DAWP_DONE>", is_last=True)
        assert mc.is_last is True


# ---------------------------------------------------------------------------
# Activation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActivation:
    def test_pre_main_loop_activation(self):
        act = Activation(placement=PreMainLoopPlacement())
        assert act.placement.type == "pre_main_loop"
        assert act.merge_back == "append"
        assert act.trigger_instruction is None

    def test_on_response_trigger_activation(self):
        act = Activation(
            placement=OnResponseTriggerPlacement(dawp_trigger="<START_REVIEW>"),
            trigger_instruction="When ready, output <START_REVIEW>.",
            merge_back="inject_only",
            max_iterations_per_prompt=4,
        )
        assert act.placement.type == "on_response_trigger"
        assert act.placement.dawp_trigger == "<START_REVIEW>"
        assert act.merge_back == "inject_only"
        assert act.max_iterations_per_prompt == 4

    def test_invalid_merge_back_rejected(self):
        with pytest.raises(ValidationError):
            Activation(placement=PreMainLoopPlacement(), merge_back="overwrite")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# DawpPendingRun
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpPendingRun:
    def test_config_static_run(self):
        run = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="ooda",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        assert run.trigger == "config"
        assert run.drain_mode == "on_iteration_end"
        assert run.temp_document_path is None

    def test_tool_dynamic_run(self):
        run = DawpPendingRun(
            trigger="tool",
            workflow_source="dynamic",
            workflow_id="dynamic-abc123",
            enqueued_at_iteration=2,
            drain_mode="inline",
            temp_document_path="/tmp/task/dynamic-abc123.dawp.md",
        )
        assert run.drain_mode == "inline"
        assert run.temp_document_path == "/tmp/task/dynamic-abc123.dawp.md"

    def test_invalid_trigger_literal_rejected(self):
        """'runtime' was the old trigger type; only 'config' | 'tool' are valid (D9)."""
        with pytest.raises(ValidationError):
            DawpPendingRun(
                trigger="runtime",  # type: ignore[arg-type]
                workflow_source="static",
                workflow_id="x",
                enqueued_at_iteration=0,
                drain_mode="on_iteration_end",
            )

    def test_invalid_drain_mode_rejected(self):
        with pytest.raises(ValidationError):
            DawpPendingRun(
                trigger="config",
                workflow_source="static",
                workflow_id="x",
                enqueued_at_iteration=0,
                drain_mode="deferred",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# DawpDocumentError
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpDocumentError:
    def test_full_location(self):
        err = DawpDocumentError("missing contract", path="workflows/my.dawp.md", line=12)
        assert err.path == "workflows/my.dawp.md"
        assert err.line == 12
        assert err.reason == "missing contract"
        msg = str(err)
        assert "workflows/my.dawp.md" in msg
        assert "12" in msg
        assert "missing contract" in msg

    def test_path_only(self):
        err = DawpDocumentError("bad prompt block", path="my.dawp.md")
        assert "my.dawp.md" in str(err)
        assert err.line is None

    def test_no_location(self):
        err = DawpDocumentError("bad format")
        assert str(err) == "bad format"
        assert err.path is None
        assert err.line is None

    def test_is_exception(self):
        with pytest.raises(DawpDocumentError, match="test error"):
            raise DawpDocumentError("test error", path="foo.dawp.md", line=1)


# ---------------------------------------------------------------------------
# DAWPWorkflow integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDAWPWorkflow:
    def _two_step_workflow(self) -> DAWPWorkflow:
        contract = Contract(
            action="Follow steps carefully.",
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
        )
        completion_mid = MarkerCompletion(
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=False,
        )
        completion_last = MarkerCompletion(
            prompt_marker="<STEP_DONE>",
            dawp_marker="<DAWP_HANDOFF>",
            is_last=True,
        )
        return DAWPWorkflow(
            metadata=WorkflowMetadata(name="test-workflow", trigger_hint="When data is ready"),
            spec=WorkflowSpec(
                instruction="Analyze data.",
                contract=contract,
            ),
            steps=[
                DAWPStep(id="gather", instruction="Gather data.", completion=completion_mid),
                DAWPStep(id="analyze", instruction="Analyze data.", completion=completion_last),
            ],
            activations=[Activation(placement=PreMainLoopPlacement())],
        )

    def test_valid_two_step_workflow(self):
        wf = self._two_step_workflow()
        assert wf.metadata.name == "test-workflow"
        assert len(wf.steps) == 2
        assert wf.steps[0].id == "gather"
        assert wf.steps[0].completion.is_last is False
        assert wf.steps[1].id == "analyze"
        assert wf.steps[1].completion.is_last is True

    def test_empty_steps_allowed(self):
        wf = DAWPWorkflow(
            metadata=WorkflowMetadata(name="empty"),
            spec=WorkflowSpec(
                contract=Contract(action="x", prompt_marker="<STEP_DONE>", dawp_marker="<DONE>")
            ),
            steps=[],
        )
        assert wf.steps == []
        assert wf.activations == []

    def test_on_response_trigger_workflow(self):
        wf = DAWPWorkflow(
            metadata=WorkflowMetadata(name="ooda"),
            spec=WorkflowSpec(
                contract=Contract(
                    action="Observe, Orient, Decide, Act.",
                    prompt_marker="<OODA_STEP_DONE>",
                    dawp_marker="<OODA_COMPLETE>",
                )
            ),
            steps=[],
            activations=[
                Activation(
                    placement=OnResponseTriggerPlacement(
                        dawp_trigger="<START_OODA>",
                        trigger_once=True,
                    ),
                    trigger_instruction="Output <START_OODA> when ready.",
                )
            ],
        )
        act = wf.activations[0]
        assert act.placement.type == "on_response_trigger"
        assert act.placement.dawp_trigger == "<START_OODA>"  # type: ignore[union-attr]
        assert act.placement.trigger_once is True  # type: ignore[union-attr]

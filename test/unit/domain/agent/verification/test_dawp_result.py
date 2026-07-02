"""
Unit tests for DAWPResult (A-6).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)
from aiecs.domain.agent.verification.dawp_result import DAWPResult, build_dawp_result


def _sample_workflow(*, steps: int = 3) -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name="wf1"),
        spec=WorkflowSpec(
            contract=Contract(action="Act:", prompt_marker="<P>", dawp_marker="<D>"),
        ),
        steps=[
            DAWPStep(
                id=f"s{i}",
                instruction=f"step {i}",
                completion=MarkerCompletion(
                    prompt_marker="<P>",
                    dawp_marker="<D>",
                    is_last=(i == steps - 1),
                ),
            )
            for i in range(steps)
        ],
    )


@pytest.mark.unit
class TestDAWPResult:
    def test_partial_does_not_silent_pass(self) -> None:
        result = DAWPResult(
            status="partial",
            criteria_progress={"steps_completed": 1, "steps_total": 3},
            error="handoff",
        )
        assert result.passed is False
        round_trip = DAWPResult.from_dict(result.to_dict())
        assert round_trip.status == "partial"

    def test_failed_and_aborted_do_not_pass(self) -> None:
        assert DAWPResult(status="failed").passed is False
        assert DAWPResult(status="aborted").passed is False
        assert DAWPResult(status="completed").passed is True

    def test_build_completed(self) -> None:
        wf = _sample_workflow(steps=2)
        plugin_state = {"dawp._steps_completed": [0, 1]}
        result = build_dawp_result(
            workflow=wf,
            run_id="r1",
            run_success=True,
            plugin_state=plugin_state,
            handoff=None,
            abort_main=False,
        )
        assert result.status == "completed"
        assert result.passed is True

    def test_build_partial_from_handoff(self) -> None:
        wf = _sample_workflow(steps=3)
        plugin_state = {"dawp._steps_completed": [0], "dawp._failed_step_index": 1}
        result = build_dawp_result(
            workflow=wf,
            run_id="r1",
            run_success=False,
            plugin_state=plugin_state,
            handoff="budget exhausted",
            abort_main=False,
        )
        assert result.status == "partial"
        assert result.passed is False
        assert result.partial_artifacts

    def test_build_aborted_when_abort_main(self) -> None:
        wf = _sample_workflow()
        result = build_dawp_result(
            workflow=wf,
            run_id="r1",
            run_success=False,
            plugin_state={},
            handoff="failed",
            abort_main=True,
        )
        assert result.status == "aborted"
        assert result.passed is False

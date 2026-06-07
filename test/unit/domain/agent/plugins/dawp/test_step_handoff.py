"""Tests for DAWP step failure handoff messages."""

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
from aiecs.domain.agent.plugins.dawp.step_handoff import (
    build_dawp_handoff_message,
    step_display_title,
)


def _workflow() -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name="review-wf"),
        spec=WorkflowSpec(
            contract=Contract(
                action="Review.",
                prompt_marker="<S>",
                dawp_marker="<D>",
            )
        ),
        steps=[
            DAWPStep(
                id="gather",
                instruction="### Gather evidence\nCollect facts.",
                completion=MarkerCompletion(
                    prompt_marker="<S>", dawp_marker="<D>", is_last=False
                ),
            ),
            DAWPStep(
                id="analyze",
                instruction="Analyze findings.",
                completion=MarkerCompletion(
                    prompt_marker="<S>", dawp_marker="<D>", is_last=True
                ),
            ),
        ],
    )


@pytest.mark.unit
class TestStepHandoff:
    def test_step_display_title_includes_headline(self) -> None:
        step = _workflow().steps[0]
        title = step_display_title(step)
        assert "gather" in title
        assert "Gather evidence" in title

    def test_handoff_lists_incomplete_steps(self) -> None:
        msg = build_dawp_handoff_message(
            _workflow(),
            failed_step_index=0,
            reason="cap exhausted",
        )
        assert "[DAWP RUN INCOMPLETE: review-wf]" in msg
        assert "Incomplete steps:" in msg
        assert "gather" in msg
        assert "analyze" in msg
        assert "Completed steps:" not in msg

    def test_handoff_lists_completed_and_incomplete(self) -> None:
        msg = build_dawp_handoff_message(
            _workflow(),
            failed_step_index=1,
            reason="budget",
        )
        assert "Completed steps:" in msg
        assert "gather" in msg
        assert "Incomplete steps:" in msg
        assert "analyze" in msg

"""Tests for DAWP workflow registry and drain resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpPendingRun,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)
from aiecs.domain.agent.plugins.dawp.workflow_registry import (
    register_workflow,
    resolve_workflow_for_run,
)

_PROMPT = "<STEP_DONE>"
_DAWP = "<WF_DONE>"


def _workflow(name: str) -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Act.",
                prompt_marker=_PROMPT,
                dawp_marker=_DAWP,
            )
        ),
        steps=[
            DAWPStep(
                id="s1",
                instruction="Do it.",
                completion=MarkerCompletion(
                    prompt_marker=_PROMPT,
                    dawp_marker=_DAWP,
                    is_last=True,
                ),
            )
        ],
    )


@pytest.mark.unit
class TestWorkflowRegistry:
    def test_register_and_resolve(self) -> None:
        state: dict = {}
        wf = _workflow("wf-a")
        register_workflow(state, wf)
        run = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="wf-a",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        assert resolve_workflow_for_run(state, run) is wf

    def test_resolve_legacy_single_workflow(self) -> None:
        wf = _workflow("legacy")
        state = {"dawp.workflow": wf}
        run = DawpPendingRun(
            trigger="tool",
            workflow_source="static",
            workflow_id="legacy",
            enqueued_at_iteration=0,
            drain_mode="inline",
        )
        assert resolve_workflow_for_run(state, run) is wf

    def test_resolve_from_temp_document_path(self, tmp_path: Path) -> None:
        doc = f"""---
name: temp-wf
placement: pre_main_loop
---

## Instruction:
Test.

## Contract
### Action
Act.
### Prompt Completion Marker: `{_PROMPT}`
### DAWP Completion Marker: `{_DAWP}`

## Prompt
<Prompt 0>
Step.
</Prompt 0>
"""
        path = tmp_path / "dynamic.dawp.md"
        path.write_text(doc, encoding="utf-8")
        state: dict = {}
        run = DawpPendingRun(
            trigger="tool",
            workflow_source="dynamic",
            workflow_id="temp-wf",
            temp_document_path=str(path),
            enqueued_at_iteration=0,
            drain_mode="inline",
        )
        resolved = resolve_workflow_for_run(state, run)
        assert resolved is not None
        assert resolved.metadata.name == "temp-wf"
        assert state["dawp.workflows"]["temp-wf"] is resolved

    def test_unknown_workflow_returns_none(self) -> None:
        run = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id="missing",
            enqueued_at_iteration=0,
            drain_mode="on_iteration_end",
        )
        assert resolve_workflow_for_run({}, run) is None

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Structured DAWP terminal handoff (A-6)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from aiecs.domain.agent.plugins.dawp.schema import DAWPWorkflow

DAWPResultStatus = Literal["completed", "partial", "failed", "aborted"]


class DAWPResult(BaseModel):
    """Terminal structured result from an L2 DAWP prompt-chain run (A-6)."""

    status: DAWPResultStatus
    deliverable_refs: list[str] = Field(default_factory=list)
    partial_artifacts: list[dict[str, Any]] = Field(default_factory=list)
    criteria_progress: dict[str, Any] = Field(default_factory=dict)
    chain_state: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @property
    def passed(self) -> bool:
        """True only for fully completed runs — partial/failed/aborted MUST NOT silent-pass."""
        return self.status == "completed"

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DAWPResult":
        return cls.model_validate(data)


def build_dawp_result(
    *,
    workflow: DAWPWorkflow,
    run_id: str,
    run_success: bool,
    plugin_state: dict[str, Any],
    handoff: str | None,
    abort_main: bool,
) -> DAWPResult:
    """Build terminal DAWPResult from plugin_state accumulated during a run."""
    steps_completed: list[int] = list(plugin_state.get("dawp._steps_completed") or [])
    failed_step_index = plugin_state.get("dawp._failed_step_index")
    total_steps = len(workflow.steps)
    deliverable_refs: list[str] = list(plugin_state.get("dawp._deliverable_refs") or [])

    if abort_main and not run_success:
        status: DAWPResultStatus = "aborted"
        error = handoff or "DAWP run aborted (abort_main)"
    elif run_success:
        status = "completed"
        error = None
    elif steps_completed:
        status = "partial"
        error = handoff or "DAWP run ended before completion marker"
    else:
        status = "failed"
        error = handoff or "DAWP run failed before first step completed"

    partial_artifacts: list[dict[str, Any]] = []
    if handoff and status != "completed":
        partial_artifacts.append({"kind": "handoff_message", "content": handoff})

    criteria_progress = {
        "steps_completed": len(steps_completed),
        "steps_total": total_steps,
        "completed_step_indices": steps_completed,
    }
    if failed_step_index is not None:
        criteria_progress["failed_step_index"] = failed_step_index

    chain_state = {
        "run_id": run_id,
        "workflow_id": workflow.metadata.name,
        "steps_total": total_steps,
        "steps_completed": steps_completed,
        "failed_step_index": failed_step_index,
        "run_success_sentinel": run_success,
    }

    return DAWPResult(
        status=status,
        deliverable_refs=deliverable_refs,
        partial_artifacts=partial_artifacts,
        criteria_progress=criteria_progress,
        chain_state=chain_state,
        error=error,
    )


def dawp_result_terminal_event(result: DAWPResult) -> dict[str, Any]:
    """Streaming terminal event payload for ``execute_task_streaming`` consumers."""
    return {
        "type": "dawp_result",
        "success": result.passed,
        "dawp_result": result.to_dict(),
    }

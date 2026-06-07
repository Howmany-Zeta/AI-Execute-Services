"""Tests for runtime enqueue_guard from PluginConfig.options (§4.1.2)."""

from __future__ import annotations

import pytest

from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.enqueue_guard import build_enqueue_guard
from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpPendingRun,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)


def _workflow(name: str = "my-review") -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Act.",
                prompt_marker="<S>",
                dawp_marker="<D>",
            )
        ),
        steps=[
            DAWPStep(
                id="s1",
                instruction="Step.",
                completion=MarkerCompletion(
                    prompt_marker="<S>", dawp_marker="<D>", is_last=True
                ),
            )
        ],
    )


def _run(workflow_id: str = "wf-a") -> DawpPendingRun:
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode="on_iteration_end",
    )


@pytest.mark.unit
class TestBuildEnqueueGuard:
    def test_no_options_returns_none(self) -> None:
        assert build_enqueue_guard({}) is None

    def test_allowed_workflows_blocks_unknown(self) -> None:
        guard = build_enqueue_guard({"enqueue_guard": {"allowed_workflows": ["wf-a"]}})
        assert guard is not None
        state: dict = {"dawp.pending": []}
        assert guard(_run("wf-a"), state) is True
        assert guard(_run("wf-b"), state) is False

    def test_max_runs_per_task(self) -> None:
        guard = build_enqueue_guard({"enqueue_guard": {"max_runs_per_task": 2}})
        assert guard is not None
        state = {"dawp.pending": [_run()], "dawp._run_count": 1}
        assert guard(_run(), state) is False

    def test_require_remaining_budget(self) -> None:
        guard = build_enqueue_guard({"enqueue_guard": {"require_remaining_budget": 3}})
        assert guard is not None
        state = {"task.iteration_budget": TaskIterationBudget(limit=2)}
        assert guard(_run(), state) is False
        state["task.iteration_budget"] = TaskIterationBudget(limit=5)
        assert guard(_run(), state) is True


@pytest.mark.unit
class TestDawpStartEnqueueGuard:
    @pytest.mark.asyncio
    async def test_dawp_start_rejected_when_max_runs_per_task_exceeded(self) -> None:
        from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import handle_dawp_start

        wf = _workflow("my-review")
        state = {
            "dawp.workflow": wf,
            "dawp.pending": [_run()],
            "dawp._run_count": 1,
            "dawp.plugin_options": {"enqueue_guard": {"max_runs_per_task": 2}},
        }
        result = await handle_dawp_start(state, workflow_source="static")
        assert result["status"] == "rejected"
        assert "enqueue_guard" in result["reason"]
        assert len(state["dawp.pending"]) == 1

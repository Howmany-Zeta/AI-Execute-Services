"""Tests for DAWP Prometheus metrics (D3-01)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.dawp import metrics as metrics_mod


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    metrics_mod.reset_dawp_metrics_for_tests()
    yield
    metrics_mod.reset_dawp_metrics_for_tests()


def test_metrics_no_op_when_prometheus_unavailable() -> None:
    with patch.object(metrics_mod.DawpMetrics, "_init_prometheus", return_value=None):
        m = metrics_mod.DawpMetrics()
    m.available = False
    m.record_run(
        workflow_id="wf-a",
        trigger="config",
        workflow_source="static",
        success=True,
    )
    with m.observe_step_duration(
        workflow_id="wf-a",
        trigger="tool",
        workflow_source="dynamic",
    ):
        pass


def test_record_run_increments_total_and_failed() -> None:
    mock_run_total = MagicMock()
    mock_run_total.labels.return_value = mock_run_total
    mock_run_failed = MagicMock()
    mock_run_failed.labels.return_value = mock_run_failed
    mock_histogram = MagicMock()
    mock_histogram.labels.return_value = mock_histogram

    def _counter_factory(*args, **kwargs):
        name = args[0] if args else kwargs.get("name", "")
        if name == "dawp_run_failed_total":
            return mock_run_failed
        return mock_run_total

    with patch.dict(
        "sys.modules",
        {
            "prometheus_client": MagicMock(
                Counter=_counter_factory,
                Histogram=lambda *a, **k: mock_histogram,
            )
        },
    ):
        m = metrics_mod.DawpMetrics()
        assert m.available is True

    m.record_run(
        workflow_id="ooda",
        trigger="config",
        workflow_source="static",
        success=True,
    )
    mock_run_total.labels.assert_called_with(
        workflow_id="ooda", trigger="config", workflow_source="static"
    )
    mock_run_total.inc.assert_called_once()
    mock_run_failed.inc.assert_not_called()

    m.record_run(
        workflow_id="ooda",
        trigger="tool",
        workflow_source="dynamic",
        success=False,
    )
    mock_run_failed.labels.assert_called_with(
        workflow_id="ooda", trigger="tool", workflow_source="dynamic"
    )
    assert mock_run_failed.inc.call_count == 1


def test_observe_step_duration_records_histogram() -> None:
    mock_run_total = MagicMock()
    mock_run_total.labels.return_value = mock_run_total
    mock_run_failed = MagicMock()
    mock_run_failed.labels.return_value = mock_run_failed
    mock_histogram = MagicMock()
    mock_histogram.labels.return_value = mock_histogram

    with patch.dict(
        "sys.modules",
        {
            "prometheus_client": MagicMock(
                Counter=lambda *args, **kwargs: mock_run_failed
                if (args and args[0] == "dawp_run_failed_total")
                or kwargs.get("name") == "dawp_run_failed_total"
                else mock_run_total,
                Histogram=lambda *a, **k: mock_histogram,
            )
        },
    ):
        m = metrics_mod.DawpMetrics()

    with m.observe_step_duration(
        workflow_id="first-principles",
        trigger="config",
        workflow_source="static",
    ):
        pass

    mock_histogram.labels.assert_called_with(
        workflow_id="first-principles",
        trigger="config",
        workflow_source="static",
    )
    mock_histogram.observe.assert_called_once()
    assert mock_histogram.observe.call_args.args[0] >= 0


def test_get_dawp_metrics_singleton() -> None:
    a = metrics_mod.get_dawp_metrics()
    b = metrics_mod.get_dawp_metrics()
    assert a is b


def test_metrics_labels_from_plugin_state() -> None:
    labels = metrics_mod.metrics_labels_from_plugin_state(
        {
            "dawp._metrics_run": {
                "workflow_id": "wf-1",
                "trigger": "tool",
                "workflow_source": "dynamic",
            }
        }
    )
    assert labels == {
        "workflow_id": "wf-1",
        "trigger": "tool",
        "workflow_source": "dynamic",
    }


@pytest.mark.asyncio
async def test_mock_run_records_metrics_on_drain() -> None:
    """Integration-style: drain a mock run and verify metrics.record_run is called."""
    from unittest.mock import AsyncMock

    from aiecs.domain.agent.plugins.context import AgentPluginContext
    from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
    from aiecs.domain.agent.plugins.dawp.schema import (
        Activation,
        Contract,
        DAWPStep,
        DAWPWorkflow,
        DawpPendingRun,
        MarkerCompletion,
        PreMainLoopPlacement,
        WorkflowMetadata,
        WorkflowSpec,
    )

    workflow = DAWPWorkflow(
        metadata=WorkflowMetadata(name="metrics-wf"),
        spec=WorkflowSpec(
            contract=Contract(
                action="Act.",
                prompt_marker="<STEP_DONE>",
                dawp_marker="<DAWP_DONE>",
            )
        ),
        steps=[
            DAWPStep(
                id="only",
                instruction="Do it.",
                completion=MarkerCompletion(
                    prompt_marker="<STEP_DONE>",
                    dawp_marker="<DAWP_DONE>",
                    is_last=True,
                ),
            )
        ],
        activations=[
            Activation(
                placement=PreMainLoopPlacement(type="pre_main_loop"),
                merge_back="append",
            )
        ],
    )

    run = DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id="metrics-wf",
        enqueued_at_iteration=0,
        drain_mode="on_iteration_end",
    )

    plugin_ctx = AgentPluginContext(
        agent=MagicMock(),
        task={},
        context={},
        task_description="metrics test",
    )
    plugin_ctx.plugin_state = {
        "dawp.pending": [run],
        "dawp.workflow": workflow,
        "dawp._run_success": False,
    }
    budget = TaskIterationBudget(limit=5)

    agent = MagicMock()

    async def _fake_chain(_workflow, _messages, _context, plugin_ctx, _agent, **_kwargs):
        plugin_ctx.plugin_state["dawp._run_success"] = True
        if False:
            yield {}

    mock_metrics = MagicMock()
    with patch(
        "aiecs.domain.agent.plugins.dawp.metrics.get_dawp_metrics",
        return_value=mock_metrics,
    ), patch(
        "aiecs.domain.agent.plugins.dawp.prompt_chain_runner.run_prompt_chain",
        side_effect=_fake_chain,
    ):
        from aiecs.domain.agent.hybrid_agent import HybridAgent

        real_agent = HybridAgent.__new__(HybridAgent)
        events = []
        async for event in real_agent._drain_pending_dawp_runs(
            "on_iteration_end",
            [],
            {},
            plugin_ctx,
            budget,
        ):
            events.append(event)

    mock_metrics.record_run.assert_called_once_with(
        workflow_id="metrics-wf",
        trigger="config",
        workflow_source="static",
        success=True,
    )

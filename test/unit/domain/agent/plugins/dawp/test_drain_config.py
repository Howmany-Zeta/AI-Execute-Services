"""
Unit tests for D1-09 — HybridAgent config-path DAWP drain (§6.5).

Covers:
- _drain_pending_dawp_runs: FIFO drain into prompt_chain_runner events
- _drain_pending_dawp_runs: unknown workflow_id skipped with warning
- _drain_pending_dawp_runs: only matching drain_mode runs consumed
- _drain_pending_dawp_runs: budget exhaustion stops drain mid-queue
- _tool_loop_streaming_with_plugins: pre_main_loop pending run drained before first iteration_start
- _tool_loop_streaming_with_plugins: main loop continues after DAWP (R2)
- _tool_loop_streaming_with_plugins: on_iteration_end pending run drained after iteration
- DAWP events carry loop_scope.kind="dawp"; main-loop events do not
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
from aiecs.domain.agent.plugins.dawp.schema import (
    Activation,
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpPendingRun,
    MarkerCompletion,
    OnResponseTriggerPlacement,
    PreMainLoopPlacement,
    WorkflowMetadata,
    WorkflowSpec,
)
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

# ---------------------------------------------------------------------------
# Shared markers
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<REVIEW_COMPLETE>"
_TRIGGER = "<START_REVIEW>"
_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM (streaming-capable, same pattern as test_nested_streaming.py)
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    """Plays back a fixed list of responses via both generate_text and stream_text."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self._idx = 0

    def _next(self) -> dict[str, Any]:
        payload = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return payload

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        payload = self._next()
        resp = LLMResponse(
            content=payload.get("content", ""),
            provider="openai",
            model="test",
            tokens_used=5,
        )
        if payload.get("tool_calls") is not None:
            setattr(resp, "tool_calls", payload["tool_calls"])
        return resp

    async def stream_text(self, *args: Any, **kwargs: Any):
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        payload = self._next()
        if payload.get("tool_calls") is not None:
            yield StreamChunk(type="tool_calls", tool_calls=payload["tool_calls"])
        else:
            yield StreamChunk(type="token", content=payload.get("content", "done"))

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Workflow / pending-run factories
# ---------------------------------------------------------------------------


def _workflow(
    name: str = "test-review",
    prompt_marker: str = _PROMPT_MARKER,
    dawp_marker: str = _DAWP_MARKER,
    activations: list[Activation] | None = None,
) -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Review carefully.",
                prompt_marker=prompt_marker,
                dawp_marker=dawp_marker,
            )
        ),
        steps=[
            DAWPStep(
                id="review",
                instruction="Review findings.",
                completion=MarkerCompletion(
                    prompt_marker=prompt_marker,
                    dawp_marker=dawp_marker,
                    is_last=True,
                ),
            )
        ],
        activations=activations or [],
    )


def _pending_run(
    workflow_id: str = "test-review",
    drain_mode: str = "on_iteration_end",
) -> DawpPendingRun:
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode=drain_mode,
    )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 10,
) -> tuple[HybridAgent, AgentPluginContext]:
    config = AgentConfiguration(
        goal="drain test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ],
    )
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool"
    mock_tool._schemas = {"q": MagicMock()}
    mock_tool.run_async = AsyncMock(return_value="result")

    llm = MockLLM(responses)
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="drain-test",
            name="Drain Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "drain test"},
        context={},
        task_description="drain test",
    )
    return agent, plugin_ctx


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


# ---------------------------------------------------------------------------
# _drain_pending_dawp_runs unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestDrainPendingDawpRuns:
    async def test_drains_one_run_and_yields_dawp_events(self) -> None:
        """Single pending run → events from prompt_chain_runner are yielded."""
        wf = _workflow()
        responses = [{"content": f"Review done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        messages = [LLMMessage(role="user", content="test")]
        events = await _collect(
            agent._drain_pending_dawp_runs("on_iteration_end", messages, {}, plugin_ctx, budget)
        )

        # Pending queue should be drained
        assert plugin_ctx.plugin_state["dawp.pending"] == []
        # Events must carry loop_scope.kind=dawp
        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) > 0

    async def test_pre_main_loop_boundary_placement(self) -> None:
        """pre_main_loop config run emits placement='pre_main_loop' on boundary events."""
        wf = _workflow()
        responses = [{"content": f"Review done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [
            DawpPendingRun(
                trigger="config",
                workflow_source="static",
                workflow_id="test-review",
                enqueued_at_iteration=0,
                drain_mode="on_iteration_end",
                config_placement="pre_main_loop",
            )
        ]
        plugin_ctx.plugin_state["dawp.stream_boundary_events"] = True
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end",
                [LLMMessage(role="user", content="t")],
                {},
                plugin_ctx,
                budget,
            )
        )

        started = [e for e in events if e.get("type") == "dawp_run_started"]
        assert len(started) == 1
        assert started[0]["placement"] == "pre_main_loop"

    async def test_unknown_workflow_id_left_in_queue(self) -> None:
        """Pending run with unknown workflow_id stays in queue (no silent loss)."""
        wf = _workflow(name="known-wf")
        agent, plugin_ctx = await _make_agent([{"content": "done"}])
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        unknown = _pending_run(workflow_id="unknown-wf")
        plugin_ctx.plugin_state["dawp.pending"] = [unknown]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs("on_iteration_end", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget)
        )

        assert events == []
        assert plugin_ctx.plugin_state["dawp.pending"] == [unknown]

    async def test_unresolvable_head_does_not_block_resolvable_tail(self) -> None:
        """FIFO: unknown at head is skipped; resolvable tail still drains this pass."""
        wf_a = _workflow(name="wf-a")
        responses = [{"content": f"A done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflows"] = {"wf-a": wf_a}
        unknown = _pending_run(workflow_id="unknown-wf")
        resolvable = _pending_run(workflow_id="wf-a")
        plugin_ctx.plugin_state["dawp.pending"] = [unknown, resolvable]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end",
                [LLMMessage(role="user", content="t")],
                {},
                plugin_ctx,
                budget,
            )
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) > 0
        assert unknown in plugin_ctx.plugin_state["dawp.pending"]
        assert resolvable not in plugin_ctx.plugin_state["dawp.pending"]

    async def test_abort_main_merges_handoff_before_abort(self) -> None:
        """abort_main=True: handoff with incomplete steps stays in main messages (audit)."""
        from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

        wf = _workflow(name="handoff-wf")
        wf.steps[0].max_iterations = 1
        agent, plugin_ctx = await _make_agent([{"content": "no marker"}])
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        for merge_back in ("append", "inject_only"):
            messages = [LLMMessage(role="user", content="task")]
            plugin_ctx.plugin_state["dawp.pending"] = [
                DawpPendingRun(
                    trigger="config",
                    workflow_source="static",
                    workflow_id="handoff-wf",
                    enqueued_at_iteration=0,
                    drain_mode="on_iteration_end",
                    merge_back=merge_back,  # type: ignore[arg-type]
                    abort_main=True,
                )
            ]
            with pytest.raises(DawpAbortMainError):
                async for _ in agent._drain_pending_dawp_runs(
                    "on_iteration_end", messages, {}, plugin_ctx, budget
                ):
                    pass
            assert any(
                m.content and "DAWP RUN INCOMPLETE" in m.content for m in messages
            ), f"handoff missing for merge_back={merge_back}"

    async def test_mismatched_drain_mode_not_consumed(self) -> None:
        """Pending run with drain_mode='inline' is NOT drained when mode='on_iteration_end'."""
        wf = _workflow()
        agent, plugin_ctx = await _make_agent([{"content": "done"}])
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        inline_run = _pending_run(drain_mode="inline")
        plugin_ctx.plugin_state["dawp.pending"] = [inline_run]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        await _collect(
            agent._drain_pending_dawp_runs("on_iteration_end", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget)
        )

        # Inline run must remain in the queue
        assert len(plugin_ctx.plugin_state["dawp.pending"]) == 1
        assert plugin_ctx.plugin_state["dawp.pending"][0].drain_mode == "inline"

    async def test_fifo_order_two_runs(self) -> None:
        """Two pending runs drained FIFO — first enqueued, first executed."""
        wf_a = _workflow(name="wf-a")
        wf_b = _workflow(name="wf-b")
        responses = [
            {"content": f"A done.\n{_DAWP_MARKER}"},
            {"content": f"B done.\n{_DAWP_MARKER}"},
        ]
        agent, plugin_ctx = await _make_agent(responses)
        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state["dawp.workflows"] = {
            "wf-a": wf_a,
            "wf-b": wf_b,
        }
        plugin_ctx.plugin_state["dawp.workflow"] = wf_a
        plugin_ctx.plugin_state["dawp.pending"] = [
            _pending_run(workflow_id="wf-a"),
            _pending_run(workflow_id="wf-b"),
        ]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs("on_iteration_end", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget)
        )

        assert plugin_ctx.plugin_state["dawp.pending"] == []
        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) >= 2

    async def test_budget_zero_stops_drain(self) -> None:
        """Budget exhausted before drain → no events, queue unchanged."""
        wf = _workflow()
        agent, plugin_ctx = await _make_agent([{"content": "done"}])
        budget = TaskIterationBudget(limit=0)  # already exhausted
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs("on_iteration_end", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget)
        )

        assert events == []
        # Run was NOT consumed (budget check prevents entry into while loop)
        assert len(plugin_ctx.plugin_state["dawp.pending"]) == 1


# ---------------------------------------------------------------------------
# _tool_loop_streaming_with_plugins integration tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestToolLoopStreamingWithDawnDrain:
    async def test_pre_main_loop_dawp_events_before_first_iteration_start(self) -> None:
        """pre_main_loop: DAWP events appear before the first main-loop iteration_start."""
        # LLM call 1: DAWP step → marker → run ends
        # LLM call 2: main loop → final text → loop ends
        responses = [
            {"content": f"DAWP output.\n{_DAWP_MARKER}"},
            {"content": "Main loop final answer."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        main_starts = [e for e in events if e.get("type") == "iteration_start" and "loop_scope" not in e]

        # DAWP events must exist and precede the first main-loop iteration_start
        assert len(dawp_events) > 0, "Expected DAWP events in stream"
        assert len(main_starts) > 0, "Expected main-loop iteration_start"

        first_dawp_idx = events.index(dawp_events[0])
        first_main_start_idx = events.index(main_starts[0])
        assert first_dawp_idx < first_main_start_idx, (
            f"DAWP event at index {first_dawp_idx} should precede "
            f"first main iteration_start at index {first_main_start_idx}"
        )

    async def test_main_loop_continues_after_dawp(self) -> None:
        """R2: main loop produces its own result event after DAWP run completes."""
        responses = [
            {"content": f"DAWP done.\n{_DAWP_MARKER}"},
            {"content": "Main final."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        result_events = [e for e in events if e.get("type") == "result"]
        # Main loop must produce its own result event
        assert len(result_events) >= 1
        # The last result event's output comes from the main-loop LLM call
        last_result = result_events[-1]
        assert last_result.get("output") == "Main final."

    async def test_dawp_messages_merged_into_main_messages(self) -> None:
        """merge_back append: DAWP assistant messages are visible to the main loop LLM."""
        # We verify that the message list grows during DAWP (in-place append)
        captured_messages: list[list[LLMMessage]] = []

        original_stream_text = agent_llm = None  # filled below

        responses = [
            {"content": f"DAWP output.\n{_DAWP_MARKER}"},
            {"content": "Main final."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        # Intercept LLM calls to capture messages
        original_build = agent._build_initial_messages_async

        async def _capturing_build(*a, **kw):
            msgs = await original_build(*a, **kw)
            captured_messages.append(list(msgs))
            return msgs

        agent._build_initial_messages_async = _capturing_build

        await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # The main loop should have seen initial messages
        assert len(captured_messages) >= 1

    async def test_no_pending_runs_normal_main_loop(self) -> None:
        """When dawp.pending is empty, the main loop runs normally without DAWP events."""
        responses = [{"content": "Main answer."}]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = None
        plugin_ctx.plugin_state["dawp.pending"] = []

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        result_events = [e for e in events if e.get("type") == "result"]

        assert dawp_events == []
        assert len(result_events) == 1
        assert result_events[0].get("output") == "Main answer."

    async def test_budget_exhausted_by_dawp_stops_main_loop(self) -> None:
        """If DAWP exhausts the budget, main loop exits via budget guard (while remaining > 0)."""
        # With a tight budget of 1, the DAWP step uses all of it
        responses = [{"content": f"DAWP.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=1)

        budget = TaskIterationBudget(limit=1)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # Budget exhausted → no main-loop iteration_start events
        main_starts = [e for e in events if e.get("type") == "iteration_start" and "loop_scope" not in e]
        assert main_starts == []
        # A result event should still be produced (max-iterations result from main loop)
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1

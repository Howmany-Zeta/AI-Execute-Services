"""
Unit tests for D2-05 — inline DAWP drain after dawp_start (same iteration).

Covers:
- _drain_pending_dawp_runs("inline"): drains drain_mode='inline' runs and yields DAWP events
- _drain_pending_dawp_runs("inline"): does NOT consume drain_mode='on_iteration_end' runs
- _tool_loop_streaming_with_plugins: inline DAWP events appear in same main-loop iteration
  as the dawp_start call — i.e., BEFORE the next iteration_start
- _tool_loop_streaming_with_plugins: inline drain does NOT wait for next iteration
- Config-path (on_iteration_end) drain unaffected by inline drain
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    DawpPendingRun,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)
from aiecs.domain.agent.plugins.models import PluginConfig
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

# ---------------------------------------------------------------------------
# Shared markers
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<REVIEW_COMPLETE>"
_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM (streaming-capable)
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    """Plays back a fixed list of responses via both generate_text and stream_text."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self._idx = 0
        self.call_count = 0

    def _next(self) -> dict[str, Any]:
        payload = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        self.call_count += 1
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
# Factories
# ---------------------------------------------------------------------------


def _workflow(
    name: str = "test-review",
    prompt_marker: str = _PROMPT_MARKER,
    dawp_marker: str = _DAWP_MARKER,
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
        activations=[],
    )


def _inline_pending_run(workflow_id: str = "test-review") -> DawpPendingRun:
    """Simulates what dawp_start tool handler enqueues (drain_mode='inline')."""
    return DawpPendingRun(
        trigger="tool",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode="inline",
    )


def _config_pending_run(workflow_id: str = "test-review") -> DawpPendingRun:
    """Config-path pending run (drain_mode='on_iteration_end')."""
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode="on_iteration_end",
    )


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 10,
) -> tuple[HybridAgent, Any]:
    config = AgentConfiguration(
        goal="inline drain test",
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
            agent_id="inline-drain-test",
            name="Inline Drain Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "inline drain test"},
        context={},
        task_description="inline drain test",
    )
    return agent, plugin_ctx


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


# ---------------------------------------------------------------------------
# _drain_pending_dawp_runs unit tests (inline mode)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestDrainPendingDawpRunsInline:
    async def test_inline_drain_consumes_inline_run(self) -> None:
        """drain_mode='inline': inline pending run is consumed and yields DAWP events."""
        wf = _workflow()
        responses = [{"content": f"DAWP done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [_inline_pending_run()]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        messages = [LLMMessage(role="user", content="test")]
        events = await _collect(
            agent._drain_pending_dawp_runs("inline", messages, {}, plugin_ctx, budget)
        )

        assert plugin_ctx.plugin_state["dawp.pending"] == []
        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) > 0

    async def test_inline_drain_does_not_consume_config_run(self) -> None:
        """drain_mode='inline': config-path pending run (on_iteration_end) is NOT consumed."""
        wf = _workflow()
        agent, plugin_ctx = await _make_agent([{"content": "done"}])
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        config_run = _config_pending_run()
        plugin_ctx.plugin_state["dawp.pending"] = [config_run]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs(
                "inline", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget
            )
        )

        assert events == []
        assert len(plugin_ctx.plugin_state["dawp.pending"]) == 1
        assert plugin_ctx.plugin_state["dawp.pending"][0].drain_mode == "on_iteration_end"

    async def test_inline_drain_mixed_queue(self) -> None:
        """Mixed queue: inline drain consumes only inline runs; config runs remain."""
        wf = _workflow()
        responses = [{"content": f"DAWP done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)
        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [
            _inline_pending_run(),
            _config_pending_run(),
        ]
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        await _collect(
            agent._drain_pending_dawp_runs(
                "inline", [LLMMessage(role="user", content="t")], {}, plugin_ctx, budget
            )
        )

        remaining = plugin_ctx.plugin_state["dawp.pending"]
        assert len(remaining) == 1
        assert remaining[0].drain_mode == "on_iteration_end"


# ---------------------------------------------------------------------------
# _tool_loop_streaming_with_plugins integration tests (inline drain timing)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestInlineDrainTiming:
    async def test_inline_dawp_events_appear_before_next_iteration_start(self) -> None:
        """DAWP token events from inline drain appear BEFORE the next iteration_start.

        Timeline:
          [iter 1 start] → main LLM call (iter 1) → inline drain (DAWP events) →
          [iter 2 start] → main LLM call (iter 2, final answer)
        """
        # LLM call order: (0) main iter 1, (1) DAWP nested step, (2) main iter 2 (final)
        responses = [
            {"content": "First main response."},           # main iter 1
            {"content": f"DAWP output.\n{_DAWP_MARKER}"},  # DAWP nested step
            {"content": "Final answer."},                   # main iter 2
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_inline_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        main_starts = [
            e for e in events
            if e.get("type") == "iteration_start" and "loop_scope" not in e
        ]

        assert len(dawp_events) > 0, "Expected DAWP events in stream"
        assert len(main_starts) >= 2, (
            f"Expected at least 2 main-loop iteration_starts (got {len(main_starts)}); "
            "inline drain forces main loop to continue after DAWP"
        )

        first_dawp_idx = events.index(dawp_events[0])
        second_start_idx = events.index(main_starts[1])

        assert first_dawp_idx < second_start_idx, (
            f"DAWP event at index {first_dawp_idx} should precede "
            f"second iteration_start at index {second_start_idx} — "
            "inline drain must fire in iteration 1, not wait for iteration 2"
        )

    async def test_inline_drain_forces_main_loop_continue(self) -> None:
        """After inline drain, main loop continues even when the triggering response was 'final'."""
        # main iter 1 produces a final-looking response; inline drain forces continuation.
        responses = [
            {"content": "Triggering response (would be final)."},  # main iter 1
            {"content": f"DAWP done.\n{_DAWP_MARKER}"},            # DAWP nested step
            {"content": "Actual final answer."},                    # main iter 2
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_inline_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1
        last_result = result_events[-1]
        assert last_result.get("output") == "Actual final answer.", (
            "Main loop must continue after inline DAWP drain and produce the post-DAWP result"
        )

    async def test_config_path_drain_unaffected_by_inline_drain(self) -> None:
        """Config-path (on_iteration_end) pending run is NOT consumed by the inline drain point.

        The config run must survive the inline drain and be consumed at ON_ITERATION_END.
        """
        wf = _workflow()

        # LLM call order:
        # (0) main iter 1  — produces a continue outcome (tool call)
        # The config-path run should remain after the inline drain fires (nothing inline)
        # and be consumed after ON_ITERATION_END.
        # We verify by checking no inline DAWP events appear (no inline run in queue).
        responses = [
            {"content": "Main response without DAWP."},  # main iter 1
            {"content": f"Config DAWP done.\n{_DAWP_MARKER}"},  # config path DAWP step
            {"content": "Final answer."},                # main iter 2
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=5)

        budget = TaskIterationBudget(limit=5)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        # Only a config-path pending run — inline drain should leave it alone
        plugin_ctx.plugin_state["dawp.pending"] = [_config_pending_run()]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        # Config path DAWP should still have run (drained at ON_ITERATION_END), so events exist
        assert len(dawp_events) > 0, (
            "Config-path DAWP run should still be drained (just at ON_ITERATION_END, not inline)"
        )


def _minimal_dynamic_doc(name: str = "dynamic-inline") -> str:
    return f"""---
name: {name}
placement: pre_main_loop
---

## Instruction:
Dynamic inline test.

## Contract
### Action
Review.
### Prompt Completion Marker: `{_PROMPT_MARKER}`
### DAWP Completion Marker: `{_DAWP_MARKER}`

## Prompt
<Prompt 0>
Review.
</Prompt 0>
"""


@pytest.mark.unit
@pytest.mark.asyncio
class TestDynamicInlineDrainE2E:
    async def test_dynamic_dawp_start_inline_drain_yields_dawp_events(self) -> None:
        """Dynamic dawp_start → registry → inline drain produces loop_scope.kind=dawp events."""
        from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import handle_dawp_start

        responses = [{"content": f"Dynamic DAWP done.\n{_DAWP_MARKER}"}]
        agent, plugin_ctx = await _make_agent(responses)
        budget = TaskIterationBudget(limit=5)

        await handle_dawp_start(
            plugin_ctx.plugin_state,
            workflow_source="dynamic",
            document_content=_minimal_dynamic_doc(),
        )
        plugin_ctx.plugin_state["dawp.workflow"] = None
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        events = await _collect(
            agent._drain_pending_dawp_runs(
                "inline",
                [LLMMessage(role="user", content="test")],
                {},
                plugin_ctx,
                budget,
            )
        )

        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) > 0
        assert plugin_ctx.plugin_state["dawp.pending"] == []

"""
D2-07 — Failure modes and merge_back E2E tests (§7, D3).

Test matrix (§12 test plan rows):
1. TestStepFailureAbortMainFalse  — DAWP step fails (budget/cap) + abort_main=False
                                    → main task still succeeds (D3 safe default)
2. TestInjectOnly                 — merge_back=inject_only: main messages grows by
                                    exactly 1 summary; sub-loop detail not visible
3. TestAbortMainTrue              — abort_main=True + step failure → task result
                                    success=False (D3 explicit abort path)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.inject import _INJECT_ONLY_SUMMARY
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
# Markers
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<DAWP_COMPLETE>"
_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self.call_count = 0

    def _next(self) -> dict[str, Any]:
        payload = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        return payload

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        payload = self._next()
        return LLMResponse(
            content=payload.get("content", ""),
            provider="openai",
            model="test",
            tokens_used=1,
        )

    async def stream_text(self, *args: Any, **kwargs: Any):
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        payload = self._next()
        yield StreamChunk(type="token", content=payload.get("content", ""))

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Workflow factory
# ---------------------------------------------------------------------------


def _workflow(
    name: str = "test-wf",
    prompt_marker: str = _PROMPT_MARKER,
    dawp_marker: str = _DAWP_MARKER,
    max_iterations: int | None = 1,
) -> DAWPWorkflow:
    """Single-step workflow; max_iterations=1 forces step to fail unless marker seen."""
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Test action.",
                prompt_marker=prompt_marker,
                dawp_marker=dawp_marker,
            )
        ),
        steps=[
            DAWPStep(
                id="test-step",
                instruction="Test step instruction.",
                max_iterations=max_iterations,
                completion=MarkerCompletion(
                    prompt_marker=prompt_marker,
                    dawp_marker=dawp_marker,
                    is_last=True,
                ),
            )
        ],
        activations=[],
    )


def _pending_run(
    workflow_id: str = "test-wf",
    drain_mode: str = "on_iteration_end",
    merge_back: str = "append",
    abort_main: bool = False,
) -> DawpPendingRun:
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id=workflow_id,
        enqueued_at_iteration=0,
        drain_mode=drain_mode,
        merge_back=merge_back,
        abort_main=abort_main,
    )


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 10,
) -> tuple[HybridAgent, Any]:
    config = AgentConfiguration(
        goal="failure mode test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
        ],
    )
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "mock"
    mock_tool._schemas = {"q": MagicMock()}
    mock_tool.run_async = AsyncMock(return_value="ok")

    llm = MockLLM(responses)
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="failure-test",
            name="Failure Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "failure test"},
        context={},
        task_description="failure test",
    )
    return agent, plugin_ctx


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


# ===========================================================================
# 1. TestStepFailureAbortMainFalse
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStepFailureAbortMainFalse:
    """D3 safe default: DAWP step failure does NOT abort the main task."""

    async def _run_with_failing_dawp(self) -> tuple[list[dict], Any]:
        """DAWP step gets 1 iteration cap, LLM never produces the marker → step fails."""
        # LLM call order:
        # 0. Main iter 0: produces first response (not final, will get continue)
        # 1. DAWP step (cap=1): LLM responds WITHOUT the DAWP marker → step fails
        # 2. Main iter 1: final answer
        responses = [
            {"content": "Main first response."},  # main iter 0
            {"content": "DAWP output without marker."},  # DAWP step — no marker
            {"content": "Main final answer."},  # main iter 1 (after DAWP fails)
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        wf = _workflow(max_iterations=1)  # cap=1, step fails without marker
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=False)]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        return events, budget

    async def test_task_still_succeeds(self):
        """When DAWP step fails and abort_main=False, the main task still produces a result."""
        events, _ = await self._run_with_failing_dawp()
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1, "Expected at least one result event"

    async def test_final_result_success_true(self):
        """The final result event has success=True (D3: DAWP failure doesn't abort task)."""
        events, _ = await self._run_with_failing_dawp()
        result_events = [e for e in events if e.get("type") == "result"]
        # The FINAL result must be success=True (main task succeeded despite DAWP failure)
        # There may be intermediate result events from the DAWP sub-loop
        main_results = [
            e for e in result_events
            if e.get("loop_scope", {}).get("kind") != "dawp"
        ]
        assert len(main_results) >= 1
        assert main_results[-1].get("success") is True, (
            "Main task result must have success=True when abort_main=False"
        )

    async def test_main_loop_continues_after_dawp_failure(self):
        """Main loop continues after DAWP failure — produces its own result."""
        events, _ = await self._run_with_failing_dawp()
        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        result_events = [e for e in events if e.get("type") == "result"]

        # DAWP must have run (emitted some events)
        assert len(dawp_events) > 0, "Expected DAWP events in stream"
        # There must be a final result from the main loop (not from DAWP)
        main_results = [
            e for e in result_events
            if e.get("loop_scope", {}).get("kind") != "dawp"
        ]
        assert len(main_results) >= 1, "Main loop must produce its own result after DAWP failure"

    async def test_no_abort_main_false_result_event(self):
        """With abort_main=False, no failure result event with reason='dawp_abort_main' appears."""
        events, _ = await self._run_with_failing_dawp()
        abort_events = [
            e for e in events
            if e.get("type") == "result" and e.get("reason") == "dawp_abort_main"
        ]
        assert abort_events == [], (
            "abort_main=False must not produce a dawp_abort_main failure result"
        )


# ===========================================================================
# 2. TestInjectOnly
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestInjectOnly:
    """merge_back=inject_only: main messages grows by exactly 1 summary (§6.3, D1-12)."""

    async def _setup(self) -> tuple[HybridAgent, Any, list[LLMMessage], TaskIterationBudget]:
        """Set up agent + inject_only pending run; return (agent, plugin_ctx, messages, budget)."""
        responses = [
            {"content": f"DAWP output.\n{_DAWP_MARKER}"},  # DAWP step — success
            {"content": "Main answer."},                    # main iter 0
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)
        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=5)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(merge_back="inject_only")]
        messages = [LLMMessage(role="user", content="initial user message")]
        return agent, plugin_ctx, messages, budget

    async def test_inject_only_dawp_runs_successfully(self):
        """inject_only DAWP run completes and produces dawp-scoped events."""
        agent, plugin_ctx, messages, budget = await self._setup()
        events = await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )
        dawp_events = [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]
        assert len(dawp_events) > 0, "Expected DAWP events in inject_only run"

    async def test_inject_only_summary_in_main_messages(self):
        """With inject_only, only the run-complete summary is appended to main messages (§6.3)."""
        agent, plugin_ctx, messages, budget = await self._setup()
        initial_len = len(messages)

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        added = messages[initial_len:]
        assert len(added) == 1, (
            f"inject_only must add exactly 1 summary message to main messages; "
            f"got {len(added)}: {[m.content for m in added]}"
        )
        summary_expected = _INJECT_ONLY_SUMMARY.format(workflow_id="test-wf")
        assert added[0].content == summary_expected, (
            f"Summary content mismatch: expected '{summary_expected}', got '{added[0].content}'"
        )

    async def test_inject_only_no_dawp_detail_in_main_messages(self):
        """With inject_only, DAWP sub-loop assistant messages do NOT appear in main messages."""
        agent, plugin_ctx, messages, budget = await self._setup()
        initial_len = len(messages)

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        added_contents = [m.content or "" for m in messages[initial_len:]]
        assert not any("DAWP output." in c for c in added_contents), (
            "inject_only must NOT include DAWP sub-loop assistant text in main messages; "
            f"found: {added_contents}"
        )

    async def test_inject_only_main_messages_grew_by_one(self):
        """With inject_only, main messages grows by exactly 1 (the summary)."""
        agent, plugin_ctx, messages, budget = await self._setup()
        initial_len = len(messages)

        await _collect(
            agent._drain_pending_dawp_runs(
                "on_iteration_end", messages, {}, plugin_ctx, budget
            )
        )

        assert len(messages) == initial_len + 1, (
            f"Expected messages to grow by 1 (summary only), "
            f"grew by {len(messages) - initial_len}"
        )

    async def test_main_result_still_produced(self):
        """With inject_only, the main tool loop still produces its own final result."""
        responses = [
            {"content": f"DAWP output.\n{_DAWP_MARKER}"},
            {"content": "Main answer."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)
        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=5)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(merge_back="inject_only")]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        result_events = [
            e for e in events
            if e.get("type") == "result" and e.get("loop_scope", {}).get("kind") != "dawp"
        ]
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Main answer."


# ===========================================================================
# 3. TestAbortMainTrue
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestAbortMainTrue:
    """D3 explicit abort: abort_main=True + step failure → task result success=False."""

    async def _run_with_abort_main(self) -> list[dict]:
        """DAWP step fails (cap=1, no marker) and abort_main=True."""
        responses = [
            {"content": "Main first response."},      # main iter 0
            {"content": "DAWP output, no marker."},   # DAWP step (fails — no marker)
            {"content": "Should not reach here."},    # not reached
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        wf = _workflow(max_iterations=1)  # cap=1 → step fails without marker
        plugin_ctx.plugin_state["dawp.workflow"] = wf
        plugin_ctx.plugin_state["dawp.pending"] = [
            _pending_run(abort_main=True)
        ]

        return await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

    async def test_abort_main_produces_failure_result(self):
        """With abort_main=True and step failure, a failure result event is yielded."""
        events = await self._run_with_abort_main()
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1, "Expected at least one result event"

    async def test_abort_main_result_success_false(self):
        """With abort_main=True, the result event has success=False."""
        events = await self._run_with_abort_main()
        abort_result = next(
            (e for e in events if e.get("type") == "result" and e.get("reason") == "dawp_abort_main"),
            None,
        )
        assert abort_result is not None, (
            "Expected a result event with reason='dawp_abort_main'"
        )
        assert abort_result.get("success") is False, (
            "abort_main result must have success=False"
        )

    async def test_abort_main_stops_main_loop(self):
        """With abort_main=True, the main loop exits after the abort — no further LLM calls."""
        responses = [
            {"content": "Main first response."},
            {"content": "DAWP output, no marker."},
            {"content": "Should not reach here."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)
        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=1)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=True)]

        llm: MockLLM = agent._llm_client  # type: ignore[assignment]
        await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # Only 2 LLM calls expected: main iter 0 + DAWP step (abort fires, main stops)
        assert llm.call_count <= 2, (
            f"Expected at most 2 LLM calls (main iter 0 + DAWP step), "
            f"got {llm.call_count} — main loop should stop on abort_main"
        )

    async def test_abort_main_false_does_not_fail(self):
        """Sanity: with abort_main=False and same step failure, success=True."""
        responses = [
            {"content": "Main first response."},
            {"content": "DAWP output, no marker."},
            {"content": "Final answer after DAWP failure."},
        ]
        agent, plugin_ctx = await _make_agent(responses, max_iterations=10)
        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=1)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=False)]

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        main_results = [
            e for e in events
            if e.get("type") == "result"
            and e.get("loop_scope", {}).get("kind") != "dawp"
            and e.get("reason") != "dawp_abort_main"
        ]
        assert len(main_results) >= 1
        assert main_results[-1].get("success") is True, (
            "abort_main=False must keep main task success=True"
        )

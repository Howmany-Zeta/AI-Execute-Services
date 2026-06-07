"""
D2-08 — Non-streaming execute_task DAWP parity (§6.4).

Verifies that the non-streaming path (_tool_loop_with_plugins /
_run_tool_loop_with_iteration_hooks) performs the same DAWP drain calls as the
streaming path — "no behavioral fork" (D2-08 spec).

Tests:
1. pre_main_loop pending run is drained before main loop starts (LLM calls match)
2. Append merge_back: DAWP messages visible to main-loop LLM (shared message list)
3. inject_only merge_back: only summary in main messages, DAWP detail absent
4. abort_main=True + step failure → result has reason='dawp_abort_main', success=False
5. abort_main=False + step failure → main task still success=True
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.context import AgentPluginContext
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
# Shared markers
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<STEP_DONE>"
_DAWP_MARKER = "<DAWP_COMPLETE>"
_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM (generate_text only — non-streaming path)
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    """Fixed-response LLM mock for non-streaming execute_task tests."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self.call_count = 0
        self.received_messages: list[list[LLMMessage]] = []

    def _next(self) -> dict[str, Any]:
        payload = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        return payload

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        self.received_messages.append(list(messages))
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
# Workflow / pending-run factories
# ---------------------------------------------------------------------------


def _workflow(
    name: str = "test-wf",
    max_iterations: int | None = 5,
) -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name=name),
        spec=WorkflowSpec(
            contract=Contract(
                action="Test action.",
                prompt_marker=_PROMPT_MARKER,
                dawp_marker=_DAWP_MARKER,
            )
        ),
        steps=[
            DAWPStep(
                id="step",
                instruction="Test step.",
                max_iterations=max_iterations,
                completion=MarkerCompletion(
                    prompt_marker=_PROMPT_MARKER,
                    dawp_marker=_DAWP_MARKER,
                    is_last=True,
                ),
            )
        ],
        activations=[],
    )


def _pending_run(
    drain_mode: str = "on_iteration_end",
    merge_back: str = "append",
    abort_main: bool = False,
) -> DawpPendingRun:
    return DawpPendingRun(
        trigger="config",
        workflow_source="static",
        workflow_id="test-wf",
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
) -> tuple[HybridAgent, MockLLM]:
    config = AgentConfiguration(
        goal="DAWP non-streaming parity test",
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
            agent_id="non-streaming-dawp-test",
            name="Non-streaming DAWP Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    return agent, llm


async def _run_tool_loop(
    agent: HybridAgent,
    plugin_ctx: AgentPluginContext,
    responses_for_llm: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call _tool_loop_with_plugins directly (bypassing execute_task lifecycle)."""
    return await agent._tool_loop_with_plugins("test task", {}, plugin_ctx)


def _make_plugin_ctx(agent: HybridAgent) -> AgentPluginContext:
    return agent._make_plugin_context(
        task={"description": "test task"},
        context={},
        task_description="test task",
    )


# ===========================================================================
# Tests
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestNonStreamingDawpParity:
    """D2-08: non-streaming _tool_loop_with_plugins drains DAWP pending runs."""

    # ── Test 1: pre_main_loop drain fires before main loop ──────────────────

    async def test_pre_main_loop_dawp_drains_before_main_loop(self) -> None:
        """DAWP pending run (on_iteration_end) drained before main loop starts.

        LLM call 0: DAWP step (produces DAWP marker → success)
        LLM call 1: main loop → final answer
        """
        responses = [
            {"content": f"DAWP done.\n{_DAWP_MARKER}"},  # DAWP step
            {"content": "Main final answer."},             # main iter 0
        ]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        result = await _run_tool_loop(agent, plugin_ctx)

        assert llm.call_count >= 2, (
            f"Expected DAWP + main LLM calls (≥2), got {llm.call_count}"
        )
        assert result.get("output") == "Main final answer." or \
               result.get("final_response") == "Main final answer.", (
            f"Expected main final answer in result: {result}"
        )

    async def test_main_loop_result_success_after_dawp(self) -> None:
        """Non-streaming result has success=True after a successful DAWP run."""
        responses = [
            {"content": f"DAWP done.\n{_DAWP_MARKER}"},
            {"content": "Main answer."},
        ]
        agent, _ = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run()]

        result = await _run_tool_loop(agent, plugin_ctx)

        assert result.get("success") is not False, (
            "Non-streaming result must not be failure after normal DAWP run"
        )

    # ── Test 2: append merge_back — DAWP messages visible in main loop ──────

    async def test_append_dawp_messages_in_main_llm_call(self) -> None:
        """Append merge_back: the DAWP prompt injection (user message) is in the shared
        messages list seen by the main loop's LLM call.

        The DAWP step's final text response is not appended to messages (consistent with
        main loop behaviour — text-only final responses aren't stored in messages).
        What IS visible is the DAWP step prompt injection user message that
        prompt_chain_runner adds to the shared messages list before calling the LLM.
        """
        responses = [
            {"content": f"DAWP done.\n{_DAWP_MARKER}"},  # DAWP step
            {"content": "Main answer."},                  # main iter 0
        ]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(merge_back="append")]

        await _run_tool_loop(agent, plugin_ctx)

        assert llm.call_count >= 2
        # prompt_chain_runner appends the DAWP step injection user message to the shared list.
        # The main LLM call (index 1+) must see that user message in its messages.
        main_call_messages = llm.received_messages[-1]
        contents = [m.content or "" for m in main_call_messages]
        # "[DAWP prompt 0: step]" is the user injection format from build_step_injection
        assert any("[DAWP prompt" in c for c in contents), (
            "Append merge_back: main LLM must see the DAWP step prompt injection in messages; "
            f"found: {contents}"
        )

    # ── Test 3: inject_only — only summary in main messages ─────────────────

    async def test_inject_only_summary_in_main_llm_call(self) -> None:
        """inject_only: main loop LLM sees only the summary, not DAWP sub-loop detail."""
        responses = [
            {"content": f"DAWP output (should be hidden).\n{_DAWP_MARKER}"},  # DAWP step
            {"content": "Main answer."},                                        # main iter 0
        ]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow()
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(merge_back="inject_only")]

        await _run_tool_loop(agent, plugin_ctx)

        assert llm.call_count >= 2
        main_call_messages = llm.received_messages[-1]
        contents = [m.content or "" for m in main_call_messages]

        summary = _INJECT_ONLY_SUMMARY.format(workflow_id="test-wf")
        assert any(summary in c for c in contents), (
            f"inject_only: main LLM must see summary '{summary}'; found: {contents}"
        )
        assert not any("DAWP output (should be hidden)." in c for c in contents), (
            "inject_only: DAWP sub-loop detail must NOT appear in main LLM call; "
            f"found: {[c for c in contents if 'DAWP output' in c]}"
        )

    # ── Test 4: abort_main=True + failure → task fails ──────────────────────

    async def test_abort_main_true_returns_failure(self) -> None:
        """abort_main=True + DAWP step cap exhausted → result has reason=dawp_abort_main."""
        responses = [
            {"content": "DAWP no marker (fails cap=1)."},  # DAWP step — no marker
            {"content": "Should not be reached."},
        ]
        agent, _ = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        # cap=1 so step fails immediately without marker
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=1)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=True)]

        result = await _run_tool_loop(agent, plugin_ctx)

        assert result.get("reason") == "dawp_abort_main", (
            f"Expected reason='dawp_abort_main' in result; got: {result}"
        )
        assert result.get("success") is False, (
            f"abort_main=True must yield success=False; got: {result}"
        )

    async def test_abort_main_true_stops_main_loop(self) -> None:
        """abort_main=True + failure → main loop exits, no further LLM calls."""
        responses = [
            {"content": "DAWP no marker."},     # DAWP step — fails
            {"content": "Should not reach."},   # must NOT be called
        ]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=1)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=True)]

        await _run_tool_loop(agent, plugin_ctx)

        assert llm.call_count == 1, (
            f"abort_main=True must stop after DAWP failure; "
            f"expected 1 LLM call (DAWP step), got {llm.call_count}"
        )

    # ── Test 5: abort_main=False + failure → main task still succeeds ────────

    async def test_abort_main_false_task_succeeds_after_dawp_failure(self) -> None:
        """abort_main=False: DAWP step failure does not abort the main task (D3 safe default)."""
        responses = [
            {"content": "DAWP no marker (fails)."},  # DAWP step — fails
            {"content": "Main final answer."},        # main iter 0 — succeeds
        ]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = _workflow(max_iterations=1)
        plugin_ctx.plugin_state["dawp.pending"] = [_pending_run(abort_main=False)]

        result = await _run_tool_loop(agent, plugin_ctx)

        assert result.get("reason") != "dawp_abort_main", (
            "abort_main=False must NOT produce dawp_abort_main failure"
        )
        assert llm.call_count >= 2, (
            f"Main loop must run after DAWP failure; expected ≥2 LLM calls, got {llm.call_count}"
        )

    # ── Test 6: no-DAWP path unaffected ─────────────────────────────────────

    async def test_no_dawp_pending_normal_execution(self) -> None:
        """When dawp.pending is empty, non-streaming execute behaves as before D2-08."""
        responses = [{"content": "Simple answer."}]
        agent, llm = await _make_agent(responses)
        plugin_ctx = _make_plugin_ctx(agent)

        budget = TaskIterationBudget(limit=10)
        plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        plugin_ctx.plugin_state["dawp.workflow"] = None
        plugin_ctx.plugin_state["dawp.pending"] = []

        result = await _run_tool_loop(agent, plugin_ctx)

        assert llm.call_count == 1, f"No DAWP → exactly 1 LLM call; got {llm.call_count}"
        output = result.get("output") or result.get("final_response")
        assert output == "Simple answer."

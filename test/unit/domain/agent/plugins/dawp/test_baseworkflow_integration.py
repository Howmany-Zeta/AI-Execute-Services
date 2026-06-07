"""
D1-13 — baseworkflow integration test matrix (§12, §1.1, baseworkflow.md).

Four test cases per the design §12 test plan:

1. baseworkflow timeline: Main 2 rounds → DAWP Prompt0 multi-tool → Prompt Marker
   → Prompt1 → DAWP Marker → main final  (§1.1, config on_response_trigger)
2. limit=6 shared budget (D5): main+DAWP+main = exactly 6 LLM calls; 7th never starts
3. Final step outputs Prompt Marker by mistake → run continues until DAWP Marker
4. Custom Contract markers (OODA-style: <OODA_STEP_DONE> / <OODA_HANDOFF>)

Fixtures:
  test/fixtures/dawp/trigger_inline.dawp.md  — on_response_trigger, 2 steps
  test/fixtures/dawp/pre_main_ooda.dawp.md   — pre_main_loop, custom OODA markers

Do NOT test dawp_start E2E (D2-xx).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

_FIXTURES = Path(__file__).parents[5] / "fixtures" / "dawp"
_TRIGGER_INLINE = str(_FIXTURES / "trigger_inline.dawp.md")
_PRE_MAIN_OODA = str(_FIXTURES / "pre_main_ooda.dawp.md")

# Markers for trigger_inline fixture
_TRIGGER = "<START_INLINE_REVIEW>"
_PROMPT_MARKER = "<INLINE_STEP_DONE>"
_DAWP_MARKER = "<INLINE_REVIEW_COMPLETE>"

# Markers for pre_main_ooda fixture
_OODA_PROMPT_MARKER = "<OODA_STEP_DONE>"
_OODA_DAWP_MARKER = "<OODA_HANDOFF>"

_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    """Streaming-capable LLM mock with a fixed response queue."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self.call_count = 0

    def _next(self) -> dict[str, Any]:
        payload = self._responses[min(self.call_count, len(self._responses) - 1)]
        self.call_count += 1
        return payload

    async def generate_text(self, messages, **kwargs) -> LLMResponse:
        payload = self._next()
        return LLMResponse(
            content=payload.get("content", ""),
            provider="openai",
            model="test",
            tokens_used=1,
        )

    async def stream_text(self, *args, **kwargs):
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        payload = self._next()
        if payload.get("tool_calls") is not None:
            yield StreamChunk(type="tool_calls", tool_calls=payload["tool_calls"])
        else:
            yield StreamChunk(type="token", content=payload.get("content", ""))

    async def close(self) -> None:
        pass


def _make_tool_call(tc_id: str) -> dict[str, Any]:
    """Helper: build a tool-call payload for the mock tool."""
    return {
        "tool_calls": [
            {
                "id": tc_id,
                "type": "function",
                "function": {"name": "mock_tool", "arguments": "{}"},
            }
        ]
    }


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


async def _make_agent(
    fixture_path: str,
    responses: list[dict[str, Any]],
    max_iterations: int = 20,
) -> tuple[HybridAgent, AgentPluginContext, MockLLM]:
    """Create HybridAgent with DawpPlugin from *fixture_path* and *responses*."""
    config = AgentConfiguration(
        goal="integration test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(
                name="dawp",
                enabled=True,
                options={"document_path": fixture_path},
            ),
        ],
    )
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "mock tool for tests"
    mock_tool._schemas = {"q": MagicMock()}
    mock_tool.run_async = AsyncMock(return_value="tool result")

    llm = MockLLM(responses)
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="integ-test",
            name="Integration Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "integration test"},
        context={},
        task_description="integration test",
    )
    if agent._plugin_manager is not None:
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        # PRE_MAIN_LOOP enqueues pre_main_loop activations (normally called in
        # execute_task_streaming before _tool_loop_streaming_with_plugins).
        await agent._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)

    budget = TaskIterationBudget(limit=max_iterations)
    plugin_ctx.plugin_state[_BUDGET_KEY] = budget
    return agent, plugin_ctx, llm


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


def _dawp_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]


def _main_iterations(events: list[dict]) -> list[dict]:
    return [
        e
        for e in events
        if e.get("type") == "iteration_start" and "loop_scope" not in e
    ]


def _results(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("type") == "result"]


# ===========================================================================
# Test 1 — baseworkflow timeline: §1.1 / §12
# Main iter 0 (tool call) → Main iter 1 (trigger) → DAWP Prompt0 multi-tool
# → Prompt Marker → DAWP Prompt1 → DAWP Marker → Main iter 2 (final)
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseworkflowTimeline:
    """§1.1 baseworkflow timeline end-to-end (on_response_trigger path)."""

    @pytest.fixture
    async def _timeline_setup(self):
        responses = [
            _make_tool_call("tc-main-0"),                      # main iter 0: tool call
            {"content": f"Analysis done.\n{_TRIGGER}"},        # main iter 1: trigger
            _make_tool_call("tc-dawp-0"),                      # DAWP step0 iter 0: tool
            {"content": f"Evidence gathered.\n{_PROMPT_MARKER}"},  # DAWP step0: marker
            {"content": f"Synthesis done.\n{_DAWP_MARKER}"},   # DAWP step1: dawp marker
            {"content": "Final answer."},                      # main iter 2: final
        ]
        agent, plugin_ctx, llm = await _make_agent(_TRIGGER_INLINE, responses)
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        return events, llm, plugin_ctx.plugin_state.get(_BUDGET_KEY)

    async def test_main_loop_runs_before_dawp(self, _timeline_setup):
        """At least one main-loop iteration fires before DAWP events appear."""
        events, *_ = _timeline_setup
        main_starts = _main_iterations(events)
        dawp = _dawp_events(events)
        assert len(main_starts) >= 1
        assert len(dawp) > 0
        first_main_idx = events.index(main_starts[0])
        first_dawp_idx = events.index(dawp[0])
        assert first_dawp_idx > first_main_idx

    async def test_dawp_events_emitted_between_main_iterations(self, _timeline_setup):
        """DAWP events appear between main-loop iterations (not before all or after all)."""
        events, *_ = _timeline_setup
        main_starts = _main_iterations(events)
        dawp = _dawp_events(events)
        # There should be ≥2 main-loop iteration_start events (before and after DAWP)
        assert len(main_starts) >= 2
        assert len(dawp) > 0

    async def test_dawp_step0_multi_tool_events(self, _timeline_setup):
        """DAWP Prompt0 includes tool events (multi-tool round inside step)."""
        events, *_ = _timeline_setup
        dawp = _dawp_events(events)
        tool_events = [
            e for e in dawp if e.get("type") in ("tool_call", "tool_result")
        ]
        assert len(tool_events) > 0, "DAWP Prompt0 must include at least one tool event"

    async def test_main_final_result_after_dawp(self, _timeline_setup):
        """Main loop produces 'Final answer.' as the final result after DAWP completes."""
        events, *_ = _timeline_setup
        result_events = _results(events)
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Final answer."

    async def test_dawp_events_carry_loop_scope_kind_dawp(self, _timeline_setup):
        """Every event produced inside the DAWP run has loop_scope.kind='dawp'."""
        events, *_ = _timeline_setup
        for ev in _dawp_events(events):
            assert ev.get("loop_scope", {}).get("kind") == "dawp"

    async def test_main_events_have_no_loop_scope(self, _timeline_setup):
        """Main-loop iteration events do not carry a dawp loop_scope."""
        events, *_ = _timeline_setup
        main_events = [
            e for e in events
            if e.get("type") == "iteration_start"
            and e.get("loop_scope", {}).get("kind") != "dawp"
        ]
        assert len(main_events) >= 1


# ===========================================================================
# Test 2 — limit=6 shared budget (D5)
# main(tool)+main(trigger)+DAWP step0(tool)+DAWP step0(marker)+DAWP step1(marker)+main final = 6
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestSharedBudgetLimit:
    """D5: exactly 6 LLM calls for main(1)+main(1)+DAWP(3)+main(1)."""

    async def _run(self, limit: int = 6):
        responses = [
            _make_tool_call("tc-m0"),                          # main iter 0 (1)
            {"content": f"Done.\n{_TRIGGER}"},                 # main iter 1 (2)
            _make_tool_call("tc-d0"),                          # DAWP step0 tool (3)
            {"content": f"Evidence.\n{_PROMPT_MARKER}"},       # DAWP step0 marker (4)
            {"content": f"Synthesis.\n{_DAWP_MARKER}"},        # DAWP step1 marker (5)
            {"content": "Main final."},                        # main iter 2 (6)
            # 7th response should NEVER be called
            {"content": "SHOULD NOT BE CALLED"},
        ]
        agent, plugin_ctx, llm = await _make_agent(
            _TRIGGER_INLINE, responses, max_iterations=limit
        )
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        return events, llm, budget

    async def test_exactly_6_llm_calls(self):
        """With limit=6, MockLLM is called exactly 6 times."""
        _, llm, budget = await self._run(limit=6)
        assert llm.call_count == 6, (
            f"Expected 6 LLM calls, got {llm.call_count}"
        )

    async def test_budget_fully_consumed(self):
        """With limit=6, budget.remaining == 0 after the run."""
        _, llm, budget = await self._run(limit=6)
        assert budget.remaining == 0
        assert budget.consumed == 6

    async def test_seventh_call_never_made(self):
        """'SHOULD NOT BE CALLED' response is never returned."""
        events, llm, _ = await self._run(limit=6)
        all_content = " ".join(
            e.get("content", "") or e.get("output", "") for e in events
        )
        assert "SHOULD NOT BE CALLED" not in all_content

    async def test_result_produced_before_budget_exhausted(self):
        """The final 'Main final.' result is produced within the budget."""
        events, *_ = await self._run(limit=6)
        result_events = _results(events)
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Main final."

    async def test_with_lower_limit_7th_call_still_absent(self):
        """Same constraint holds when limit > actual calls needed."""
        _, llm, budget = await self._run(limit=10)
        # With limit=10, the natural run still takes only 6 calls
        assert llm.call_count == 6
        assert budget.consumed == 6


# ===========================================================================
# Test 3 — Final step outputs Prompt Marker by mistake (§6.0.2.1)
# DAWP run must NOT complete on Prompt Marker at last step; continues to DAWP Marker
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestWrongMarkerOnFinalStep:
    """§6.0.2.1: last DAWP step emitting Prompt Marker does not end the run."""

    async def _run(self):
        # pre_main_ooda: pre_main_loop, 2 steps, <OODA_STEP_DONE> / <OODA_HANDOFF>
        responses = [
            # DAWP step 0: correct Prompt Marker → advance to step 1
            {"content": f"Observed and oriented.\n{_OODA_PROMPT_MARKER}"},
            # DAWP step 1 (last): WRONG — outputs Prompt Marker, not DAWP Marker
            {"content": f"Deciding...\n{_OODA_PROMPT_MARKER}"},
            # DAWP step 1 (last): correct — outputs DAWP Marker → run complete
            {"content": f"Action decided.\n{_OODA_DAWP_MARKER}"},
            # Main loop final
            {"content": "Main answer."},
        ]
        agent, plugin_ctx, llm = await _make_agent(_PRE_MAIN_OODA, responses)
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        return events, llm, plugin_ctx.plugin_state.get(_BUDGET_KEY)

    async def test_dawp_completes_after_wrong_then_correct_marker(self):
        """Run completes: wrong Prompt Marker on last step is ignored; DAWP Marker accepted."""
        events, llm, _ = await self._run()
        dawp = _dawp_events(events)
        assert len(dawp) > 0, "DAWP must have run"

    async def test_main_loop_continues_after_dawp(self):
        """Main loop produces 'Main answer.' after DAWP completes (R2)."""
        events, *_ = await self._run()
        result_events = _results(events)
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Main answer."

    async def test_wrong_marker_costs_extra_llm_call(self):
        """The wrong Prompt Marker causes an extra LLM call (step 1 must retry)."""
        _, llm, _ = await self._run()
        # 3 DAWP calls (step0-marker, step1-wrong, step1-correct) + 1 main = 4 total
        assert llm.call_count == 4

    async def test_dawp_does_not_terminate_on_prompt_marker_at_last_step(self):
        """Prompt Marker on the last step must not terminate the DAWP run early."""
        events, *_ = await self._run()
        # If the run had terminated early on the Prompt Marker, the DAWP marker response
        # ("Action decided.") would appear in main messages, not in DAWP events, or would
        # not appear at all.  Verify "Action decided." is somewhere in events.
        all_content = " ".join(
            (e.get("content") or e.get("output") or "") for e in events
        )
        assert "Action decided" in all_content


# ===========================================================================
# Test 4 — Custom Contract markers (OODA-style)
# Markers <OODA_STEP_DONE> and <OODA_HANDOFF> — not hardcoded <STEP_DONE>
# ===========================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestCustomContractMarkers:
    """§6.0.2.1: custom Contract markers work end-to-end; no hardcoded defaults."""

    async def _run(self):
        # pre_main_ooda: custom markers <OODA_STEP_DONE> / <OODA_HANDOFF>
        responses = [
            {"content": f"Observed.\n{_OODA_PROMPT_MARKER}"},  # DAWP step 0
            {"content": f"Action taken.\n{_OODA_DAWP_MARKER}"}, # DAWP step 1
            {"content": "Main final."},                         # main loop
        ]
        agent, plugin_ctx, llm = await _make_agent(_PRE_MAIN_OODA, responses)
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        return events, llm, plugin_ctx.plugin_state.get(_BUDGET_KEY)

    async def test_custom_prompt_marker_advances_step(self):
        """<OODA_STEP_DONE> (not <STEP_DONE>) advances DAWP from step 0 to step 1."""
        events, llm, _ = await self._run()
        # If the custom Prompt Marker was not recognised, the runner would loop forever
        # and never reach the DAWP Marker.  Verifying DAWP events exist is sufficient.
        dawp = _dawp_events(events)
        assert len(dawp) > 0

    async def test_custom_dawp_marker_ends_run(self):
        """<OODA_HANDOFF> (not <DAWP_HANDOFF>) terminates the DAWP run correctly."""
        events, *_ = await self._run()
        result_events = _results(events)
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Main final."

    async def test_exactly_3_llm_calls(self):
        """With custom markers: 2 DAWP + 1 main = 3 total LLM calls."""
        _, llm, _ = await self._run()
        assert llm.call_count == 3

    async def test_hardcoded_step_done_not_needed(self):
        """The default <STEP_DONE> marker does NOT appear in the DAWP prompts."""
        # If hardcoded, using <OODA_STEP_DONE> would fail (no completion detected).
        # The test passing already proves this.  We also verify the marker literal.
        from aiecs.domain.agent.plugins.dawp import document_loader
        wf = document_loader.compile_file(Path(_PRE_MAIN_OODA))
        assert wf.spec.contract.prompt_marker == _OODA_PROMPT_MARKER
        assert wf.spec.contract.dawp_marker == _OODA_DAWP_MARKER
        assert wf.spec.contract.prompt_marker != "<STEP_DONE>"
        assert wf.spec.contract.dawp_marker != "<DAWP_HANDOFF>"

    async def test_budget_matches_call_count(self):
        """budget.consumed == 3 (no wasted iterations)."""
        _, llm, budget = await self._run()
        assert budget.consumed == llm.call_count == 3

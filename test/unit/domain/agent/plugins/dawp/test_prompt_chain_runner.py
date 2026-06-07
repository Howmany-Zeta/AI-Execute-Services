"""
Unit tests for D1-06 — prompt_chain_runner.py (§6.0 state machine).

Covers:
- build_step_injection: §6.0.5 format, correct marker for last/non-last step
- 1-step workflow: DAWP Completion Marker on first final text → run ends
- 2-step OODA-style workflow: Prompt0 marker advances, Prompt1 DAWP marker ends
- Prompt0 multi-tool rounds then marker (step_iteration_cap=1 loop behavior)
- Wrong marker on last step → runner continues (§6.0.2 末步规则)
- Budget exhaustion mid-step → run terminates without error (D3)
- Per-step cap exhausted → run exits with handoff (does not continue to next step)
- All yielded events are forwarded from nested runner
- Step injection is appended to messages before each step's nested runner call
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.completion import prompt_step_complete
from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
from aiecs.domain.agent.plugins.dawp.prompt_chain_runner import (
    build_step_injection,
    run_prompt_chain,
)
from aiecs.domain.agent.plugins.dawp.schema import (
    Contract,
    DAWPStep,
    DAWPWorkflow,
    MarkerCompletion,
    WorkflowMetadata,
    WorkflowSpec,
)
from aiecs.llm import LLMMessage

# ---------------------------------------------------------------------------
# Test fixtures / factories
# ---------------------------------------------------------------------------

_PROMPT_MARKER = "<OODA_STEP_DONE>"
_DAWP_MARKER = "<OODA_REVIEW_COMPLETE>"
_ACTION = "Follow OODA cycle for analysis."


def _contract() -> Contract:
    return Contract(
        action=_ACTION,
        prompt_marker=_PROMPT_MARKER,
        dawp_marker=_DAWP_MARKER,
    )


def _step(
    step_id: str,
    instruction: str,
    is_last: bool,
    max_iterations: int | None = None,
) -> DAWPStep:
    return DAWPStep(
        id=step_id,
        instruction=instruction,
        completion=MarkerCompletion(
            prompt_marker=_PROMPT_MARKER,
            dawp_marker=_DAWP_MARKER,
            is_last=is_last,
        ),
        max_iterations=max_iterations,
    )


def _workflow(steps: list[DAWPStep]) -> DAWPWorkflow:
    return DAWPWorkflow(
        metadata=WorkflowMetadata(name="ooda-test"),
        spec=WorkflowSpec(contract=_contract()),
        steps=steps,
    )


def _scope(run_id: str | None = None) -> LoopScope:
    return LoopScope(
        kind="dawp",
        run_id=run_id or f"run-{uuid.uuid4().hex[:8]}",
        workflow_id="ooda-test",
    )


def _plugin_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.plugin_state = {}
    return ctx


def _result_event(
    output: str,
    success: bool = True,
    reason: str | None = None,
    scope: LoopScope | None = None,
) -> dict[str, Any]:
    """Build a fake result event like _streaming_result_event_from_inner produces."""
    ev: dict[str, Any] = {
        "type": "result",
        "output": output,
        "success": success,
        "reason": reason,
        "loop_scope": (scope or LoopScope(kind="dawp", run_id="r")).as_dict(),
    }
    return ev


def _token_event(content: str, scope: LoopScope | None = None) -> dict[str, Any]:
    return {
        "type": "token",
        "content": content,
        "loop_scope": (scope or LoopScope(kind="dawp", run_id="r")).as_dict(),
    }


def _iter_start_event(scope: LoopScope | None = None) -> dict[str, Any]:
    return {
        "type": "iteration_start",
        "iteration": 1,
        "remaining": 5,
        "loop_scope": (scope or LoopScope(kind="dawp", run_id="r")).as_dict(),
    }


def _make_mock_agent(
    nested_responses: list[list[dict[str, Any]]],
) -> MagicMock:
    """
    Return a mock agent whose _run_tool_loop_nested_streaming yields successive
    response lists.  Each element of ``nested_responses`` is yielded for one call
    to the nested runner.  The last element is repeated for any additional calls.

    Each call also calls ``budget.consume(1)`` to mirror what the real nested runner
    does (D1-04 implementation).
    """
    call_count: list[int] = [0]

    async def _nested_runner(*args: Any, **kwargs: Any) -> AsyncGenerator[dict, None]:
        idx = min(call_count[0], len(nested_responses) - 1)
        call_count[0] += 1
        # Simulate the real nested runner consuming 1 budget unit per call
        budget_ref: TaskIterationBudget | None = kwargs.get("budget")
        if budget_ref is not None and budget_ref.remaining > 0:
            budget_ref.consume(1)
        for event in nested_responses[idx]:
            yield event

    agent = MagicMock()
    agent._run_tool_loop_nested_streaming = _nested_runner
    return agent


async def _collect(gen: AsyncGenerator[dict, None]) -> list[dict[str, Any]]:
    return [event async for event in gen]


# ---------------------------------------------------------------------------
# build_step_injection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBuildStepInjection:
    def test_contains_step_index_and_id(self) -> None:
        text = build_step_injection(
            step_index=0,
            step_id="observe",
            action=_ACTION,
            instruction="Gather evidence.",
            completion_marker=_PROMPT_MARKER,
        )
        assert "[DAWP prompt 0: observe]" in text

    def test_contains_action(self) -> None:
        text = build_step_injection(0, "s", _ACTION, "instr", _PROMPT_MARKER)
        assert _ACTION in text

    def test_contains_instruction(self) -> None:
        text = build_step_injection(0, "s", _ACTION, "Gather evidence.", _PROMPT_MARKER)
        assert "Gather evidence." in text

    def test_contains_prompt_marker_for_non_last(self) -> None:
        text = build_step_injection(0, "s", _ACTION, "instr", _PROMPT_MARKER)
        assert _PROMPT_MARKER in text
        assert _DAWP_MARKER not in text

    def test_contains_dawp_marker_for_last(self) -> None:
        text = build_step_injection(1, "s", _ACTION, "instr", _DAWP_MARKER)
        assert _DAWP_MARKER in text

    def test_includes_separator_and_instruction_prefix(self) -> None:
        text = build_step_injection(0, "s", _ACTION, "instr", _PROMPT_MARKER)
        assert "---" in text
        assert "Output the following line" in text


# ---------------------------------------------------------------------------
# 1-step workflow (is_last=True): DAWP Completion Marker → run ends
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSingleStepWorkflow:
    async def test_dawp_marker_ends_run(self) -> None:
        """Single step: DAWP marker in output → generator exits cleanly."""
        wf = _workflow([_step("review", "Review findings.", is_last=True)])
        text_with_marker = f"Here is the review.\n\n{_DAWP_MARKER}"
        agent = _make_mock_agent([[_token_event("Here is the review."), _result_event(text_with_marker)]])
        budget = TaskIterationBudget(limit=5)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 1

    async def test_budget_consumed_for_one_iteration(self) -> None:
        wf = _workflow([_step("review", "Review.", is_last=True)])
        text = f"Done.\n{_DAWP_MARKER}"
        agent = _make_mock_agent([[_result_event(text)]])
        budget = TaskIterationBudget(limit=5)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        assert budget.consumed == 1

    async def test_injection_appended_before_nested_call(self) -> None:
        """Step injection message is added to messages before calling nested runner."""
        wf = _workflow([_step("observe", "Observe.", is_last=True)])
        text = f"Observed.\n{_DAWP_MARKER}"
        agent = _make_mock_agent([[_result_event(text)]])
        budget = TaskIterationBudget(limit=5)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        # The injection must have been appended — msgs now has 2 messages
        assert len(msgs) == 2
        injection = msgs[1].content
        assert injection is not None
        assert "[DAWP prompt 0: observe]" in injection
        assert _DAWP_MARKER in injection  # last step uses dawp_marker


# ---------------------------------------------------------------------------
# 2-step OODA-style workflow
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestTwoStepWorkflow:
    async def test_prompt_marker_advances_step(self) -> None:
        """Prompt0 sees prompt_marker → runner injects Prompt1; Prompt1 sees dawp_marker → done."""
        steps = [
            _step("observe", "Observe.", is_last=False),
            _step("orient", "Orient.", is_last=True),
        ]
        wf = _workflow(steps)
        p0_text = f"Observations complete.\n{_PROMPT_MARKER}"
        p1_text = f"Orientation complete.\n{_DAWP_MARKER}"

        agent = _make_mock_agent([
            [_result_event(p0_text)],   # step 0 call
            [_result_event(p1_text)],   # step 1 call
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 2  # one per step

    async def test_two_steps_consume_two_budget_units(self) -> None:
        steps = [
            _step("observe", "Observe.", is_last=False),
            _step("orient", "Orient.", is_last=True),
        ]
        wf = _workflow(steps)
        agent = _make_mock_agent([
            [_result_event(f"Obs.\n{_PROMPT_MARKER}")],
            [_result_event(f"Orient.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        assert budget.consumed == 2

    async def test_step0_injection_uses_prompt_marker(self) -> None:
        steps = [
            _step("observe", "Observe.", is_last=False),
            _step("orient", "Orient.", is_last=True),
        ]
        wf = _workflow(steps)
        agent = _make_mock_agent([
            [_result_event(f"Obs.\n{_PROMPT_MARKER}")],
            [_result_event(f"Orient.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        # msgs[1] is step0 injection (non-last → prompt_marker)
        step0_injection = msgs[1].content
        assert step0_injection is not None
        assert _PROMPT_MARKER in step0_injection
        # step1 injection (last → dawp_marker) is at msgs[-1]
        step1_injection = msgs[-1].content
        assert step1_injection is not None
        assert _DAWP_MARKER in step1_injection


# ---------------------------------------------------------------------------
# Multi-tool rounds within a step (step_iteration_cap=1 looping)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestMultiToolRoundStep:
    async def test_tool_rounds_then_marker(self) -> None:
        """
        Prompt0: two tool-call iterations (success=False, cap=1 hit) then marker.
        Runner should call nested runner 3 times for the step.
        """
        steps = [
            _step("observe", "Observe.", is_last=False),
            _step("orient", "Orient.", is_last=True),
        ]
        wf = _workflow(steps)

        # Three calls for step 0:
        #   call 1: tool round (success=False, cap hit mid-way)
        #   call 2: tool round (success=False, cap hit mid-way)
        #   call 3: final text with prompt_marker
        # Then step 1:
        #   call 4: final text with dawp_marker
        agent = _make_mock_agent([
            [_token_event("calling tool"), _result_event("calling tool", success=False, reason="max_iterations_reached")],
            [_token_event("calling tool again"), _result_event("still working", success=False, reason="max_iterations_reached")],
            [_result_event(f"Observed.\n{_PROMPT_MARKER}")],
            [_result_event(f"Oriented.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        result_events = [e for e in events if e["type"] == "result"]
        # 4 result events: 3 for step0 (2 tool rounds + 1 natural) + 1 for step1
        assert len(result_events) == 4

    async def test_tool_rounds_consume_budget(self) -> None:
        """Each nested runner call consumes 1 budget unit."""
        wf = _workflow([_step("observe", "Obs.", is_last=True)])
        # 2 tool rounds then final
        agent = _make_mock_agent([
            [_result_event("tool 1", success=False, reason="max_iterations_reached")],
            [_result_event("tool 2", success=False, reason="max_iterations_reached")],
            [_result_event(f"Done.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        assert budget.consumed == 3


# ---------------------------------------------------------------------------
# Last step wrong marker → continue (§6.0.2 末步规则)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestLastStepWrongMarker:
    async def test_prompt_marker_on_last_step_continues(self) -> None:
        """
        Last step outputs prompt_marker instead of dawp_marker → runner continues.
        Second iteration produces dawp_marker → run ends.
        """
        wf = _workflow([_step("review", "Review.", is_last=True)])
        agent = _make_mock_agent([
            [_result_event(f"Reviewing...\n{_PROMPT_MARKER}")],  # wrong marker → continue
            [_result_event(f"Review done.\n{_DAWP_MARKER}")],    # correct marker → done
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 2
        assert budget.consumed == 2

    async def test_prompt_marker_on_last_step_does_not_advance(self) -> None:
        """After prompt_marker on last step the run must NOT terminate prematurely."""
        wf = _workflow([_step("review", "Review.", is_last=True)])
        agent = _make_mock_agent([
            [_result_event(f"Reviewing...\n{_PROMPT_MARKER}")],
            [_result_event(f"Done.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        # Should have consumed 2 iterations, not 1
        assert budget.consumed == 2


# ---------------------------------------------------------------------------
# Budget exhaustion (D3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestBudgetExhaustion:
    async def test_budget_exhausted_mid_step_terminates_run(self) -> None:
        """When budget hits 0, run_prompt_chain returns without error (D3)."""
        wf = _workflow([_step("observe", "Obs.", is_last=True)])
        # Mock: always returns tool-call result and exhausts the budget
        consumed_calls: list[int] = [0]

        async def _exhausting_runner(*args: Any, **kwargs: Any):
            budget_ref: TaskIterationBudget = kwargs["budget"]
            budget_ref.consume(budget_ref.remaining)  # exhaust all
            yield _result_event("no progress", success=False, reason="max_iterations_reached")
            consumed_calls[0] += 1

        agent = MagicMock()
        agent._run_tool_loop_nested_streaming = _exhausting_runner

        budget = TaskIterationBudget(limit=1)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]
        ctx = _plugin_ctx()

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, ctx, agent, scope=_scope(), budget=budget)
        )

        assert budget.is_exhausted
        assert consumed_calls[0] == 1
        assert ctx.plugin_state.get("dawp._handoff_message")
        assert any(e["type"] == "dawp_step_completed" and e.get("success") is False for e in events)

    async def test_budget_zero_at_step_start_skips_step(self) -> None:
        """Budget exhausted before any step → runner exits without calling nested runner."""
        steps = [
            _step("step0", "Step0.", is_last=False),
            _step("step1", "Step1.", is_last=True),
        ]
        wf = _workflow(steps)
        call_count: list[int] = [0]

        async def _counting_runner(*args: Any, **kwargs: Any):
            call_count[0] += 1
            yield _result_event(f"Done.\n{_DAWP_MARKER}")

        agent = MagicMock()
        agent._run_tool_loop_nested_streaming = _counting_runner

        # Start with budget=0 (already exhausted)
        budget = TaskIterationBudget(limit=0)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]
        ctx = _plugin_ctx()

        await _collect(
            run_prompt_chain(wf, msgs, {}, ctx, agent, scope=_scope(), budget=budget)
        )

        assert call_count[0] == 0
        assert ctx.plugin_state.get("dawp._handoff_message")


# ---------------------------------------------------------------------------
# Per-step cap
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestPerStepCap:
    async def test_step_cap_stops_step_without_marker(self) -> None:
        """With step_cap=2, failed step ends run with handoff; later steps do not run."""
        wf = _workflow([
            _step("observe", "Obs.", is_last=False, max_iterations=2),
            _step("orient", "Orient.", is_last=True),
        ])
        agent = _make_mock_agent([
            [_result_event("tool 1", success=False)],
            [_result_event("tool 2", success=False)],
            [_result_event(f"Oriented.\n{_DAWP_MARKER}")],
        ])
        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]
        ctx = _plugin_ctx()

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, ctx, agent, scope=_scope(), budget=budget)
        )

        result_events = [e for e in events if e["type"] == "result"]
        assert len(result_events) == 2
        assert any(e["type"] == "dawp_step_started" for e in events)
        assert any(
            e["type"] == "dawp_step_completed" and e.get("success") is False for e in events
        )
        handoff = ctx.plugin_state.get("dawp._handoff_message", "")
        assert "observe" in handoff
        assert "orient" in handoff
        assert any(m.content and "DAWP RUN INCOMPLETE" in m.content for m in msgs if m.content)

    async def test_default_step_cap_applied(self) -> None:
        """default_step_cap limits steps that have no explicit max_iterations."""
        wf = _workflow([_step("obs", "Obs.", is_last=True)])
        # Never sends marker → will loop until cap
        agent = _make_mock_agent([
            [_result_event("no marker", success=False)],
        ])
        budget = TaskIterationBudget(limit=100)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        ctx = _plugin_ctx()
        await _collect(
            run_prompt_chain(
                wf, msgs, {}, ctx, agent,
                scope=_scope(), budget=budget, default_step_cap=3,
            )
        )

        assert budget.consumed == 3
        assert ctx.plugin_state.get("dawp._handoff_message")


# ---------------------------------------------------------------------------
# Events forwarding
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestEventForwarding:
    async def test_all_events_forwarded(self) -> None:
        """run_prompt_chain yields every event from the nested runner unchanged."""
        wf = _workflow([_step("obs", "Obs.", is_last=True)])
        nested_events = [
            _iter_start_event(),
            _token_event("Thinking..."),
            _token_event(" analyzing."),
            _result_event(f"Done.\n{_DAWP_MARKER}"),
        ]
        agent = _make_mock_agent([nested_events])
        budget = TaskIterationBudget(limit=5)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        events = await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        nested_types = [
            e["type"]
            for e in events
            if e["type"] not in ("dawp_step_started", "dawp_step_completed")
        ]
        assert nested_types == ["iteration_start", "token", "token", "result"]
        assert any(e["type"] == "dawp_step_started" for e in events)
        assert any(
            e["type"] == "dawp_step_completed" and e.get("success") is True for e in events
        )

    async def test_step_scope_in_nested_calls(self) -> None:
        """The step_scope passed to the nested runner has correct step_index."""
        wf = _workflow([
            _step("obs", "Observe.", is_last=False),
            _step("orient", "Orient.", is_last=True),
        ])
        captured_scopes: list[dict[str, Any]] = []

        async def _capturing_runner(*args: Any, **kwargs: Any):
            captured_scopes.append({
                "step_index": kwargs["scope"].step_index,
                "step_id": kwargs["scope"].step_id,
            })
            text = f"p0.\n{_PROMPT_MARKER}" if len(captured_scopes) == 1 else f"p1.\n{_DAWP_MARKER}"
            yield _result_event(text)

        agent = MagicMock()
        agent._run_tool_loop_nested_streaming = _capturing_runner

        budget = TaskIterationBudget(limit=10)
        msgs: list[LLMMessage] = [LLMMessage(role="user", content="Start")]

        await _collect(
            run_prompt_chain(wf, msgs, {}, _plugin_ctx(), agent, scope=_scope(), budget=budget)
        )

        assert len(captured_scopes) == 2
        assert captured_scopes[0]["step_index"] == 0
        assert captured_scopes[0]["step_id"] == "obs"
        assert captured_scopes[1]["step_index"] == 1
        assert captured_scopes[1]["step_id"] == "orient"

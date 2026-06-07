"""
Unit tests for D1-10 — on_response_trigger mid-loop activation (§4.2.1, §6.0.2.2).

Fixture: test/fixtures/dawp/trigger_inline.dawp.md
  - name: trigger-inline
  - placement: on_response_trigger, dawp_trigger: <START_INLINE_REVIEW>, trigger_once: true
  - 2 prompts: gather-evidence → synthesise
  - prompt_marker: <INLINE_STEP_DONE>, dawp_marker: <INLINE_REVIEW_COMPLETE>

Tests:
- main loop response with exact trigger token on its own line → DAWP drains after that iteration
- same token inside fenced code block → scannable-lines rule prevents activation (§6.0.2.2)
- same token inside blockquote → scannable-lines rule prevents activation (§6.0.2.2)
- trigger_once=True: second iteration with trigger → NOT re-activated
- DAWP events carry loop_scope.kind="dawp"; main-loop events do not
- After DAWP, main loop continues and produces a result (R2)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

_FIXTURE_PATH = str(
    Path(__file__).parents[5] / "fixtures" / "dawp" / "trigger_inline.dawp.md"
)

_TRIGGER = "<START_INLINE_REVIEW>"
_PROMPT_MARKER = "<INLINE_STEP_DONE>"
_DAWP_MARKER = "<INLINE_REVIEW_COMPLETE>"
_BUDGET_KEY = "task.iteration_budget"


# ---------------------------------------------------------------------------
# MockLLM — streaming-capable, same pattern as test_drain_config.py
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
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
# Agent factory with DawpPlugin wired
# ---------------------------------------------------------------------------


async def _make_agent_with_dawp(
    responses: list[dict[str, Any]],
    max_iterations: int = 10,
) -> tuple[HybridAgent, AgentPluginContext]:
    """Create HybridAgent with DawpPlugin loaded from the trigger_inline fixture."""
    config = AgentConfiguration(
        goal="on_response_trigger test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(
                name="dawp",
                enabled=True,
                options={"document_path": _FIXTURE_PATH},
            ),
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
            agent_id="trigger-test",
            name="Trigger Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "trigger test"},
        context={},
        task_description="trigger test",
    )
    # Run PRE_TASK to load the workflow and build plugin_state["dawp.scheduler"]
    if agent._plugin_manager is not None:
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)

    # Ensure budget is initialised
    budget = TaskIterationBudget(limit=max_iterations)
    plugin_ctx.plugin_state[_BUDGET_KEY] = budget

    return agent, plugin_ctx


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


def _dawp_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]


def _main_starts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if e.get("type") == "iteration_start" and "loop_scope" not in e]


# ---------------------------------------------------------------------------
# Fixture file
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fixture_compiles() -> None:
    """Sanity: trigger_inline.dawp.md compiles into the expected workflow."""
    from aiecs.domain.agent.plugins.dawp import document_loader

    wf = document_loader.compile_file(Path(_FIXTURE_PATH))
    assert wf.metadata.name == "trigger-inline"
    assert len(wf.steps) == 2
    assert wf.steps[0].id == "gather-evidence"
    assert wf.steps[1].id == "synthesise"
    assert len(wf.activations) == 1
    placement = wf.activations[0].placement
    assert placement.type == "on_response_trigger"
    assert placement.dawp_trigger == _TRIGGER
    assert placement.trigger_once is True
    assert wf.spec.contract.prompt_marker == _PROMPT_MARKER
    assert wf.spec.contract.dawp_marker == _DAWP_MARKER


# ---------------------------------------------------------------------------
# Main test: trigger on scannable line → DAWP activated
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestTriggerOnScannableLine:
    async def test_trigger_activates_dawp_drain(self) -> None:
        """Exact trigger on a bare line → DAWP drains after that main-loop iteration."""
        responses = [
            # Main iteration 1: assistant output containing trigger on its own line
            {"content": f"Analysis complete.\n{_TRIGGER}"},
            # DAWP step 0 (gather-evidence)
            {"content": f"Evidence gathered.\n{_PROMPT_MARKER}"},
            # DAWP step 1 (synthesise)
            {"content": f"Synthesis complete.\n{_DAWP_MARKER}"},
            # Main iteration 2: final answer
            {"content": "Final answer."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp = _dawp_events(events)
        assert len(dawp) > 0, "Expected DAWP events when trigger fires"

    async def test_dawp_events_appear_after_triggering_iteration(self) -> None:
        """DAWP events appear after the main-loop iteration that contained the trigger."""
        responses = [
            {"content": f"Trigger iteration.\n{_TRIGGER}"},
            {"content": f"Evidence.\n{_PROMPT_MARKER}"},
            {"content": f"Synthesis.\n{_DAWP_MARKER}"},
            {"content": "Main final."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp = _dawp_events(events)
        main_starts = _main_starts(events)

        # First main-loop iteration_start must come before DAWP events
        # (DAWP drains at ON_ITERATION_END, which is AFTER the first iteration)
        assert len(dawp) > 0
        assert len(main_starts) >= 1
        first_dawp_idx = events.index(dawp[0])
        first_main_start_idx = events.index(main_starts[0])
        assert first_dawp_idx > first_main_start_idx, (
            "DAWP events should appear AFTER the first main iteration_start "
            "(trigger fires at ON_ITERATION_END, not pre_main_loop)"
        )

    async def test_main_loop_continues_after_trigger_dawp(self) -> None:
        """R2: main loop produces a final result after DAWP triggered by on_response_trigger."""
        responses = [
            {"content": f"Trigger.\n{_TRIGGER}"},
            {"content": f"Evidence.\n{_PROMPT_MARKER}"},
            {"content": f"Done.\n{_DAWP_MARKER}"},
            {"content": "Main final answer."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1
        last_result = result_events[-1]
        assert last_result.get("output") == "Main final answer."

    async def test_dawp_events_carry_loop_scope_kind_dawp(self) -> None:
        """All events produced inside the DAWP run have loop_scope.kind=dawp."""
        responses = [
            {"content": f"Trigger.\n{_TRIGGER}"},
            {"content": f"Evidence.\n{_PROMPT_MARKER}"},
            {"content": f"Done.\n{_DAWP_MARKER}"},
            {"content": "Final."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp = _dawp_events(events)
        assert len(dawp) > 0
        for event in dawp:
            assert event.get("loop_scope", {}).get("kind") == "dawp"


# ---------------------------------------------------------------------------
# Code-block test: trigger in fence → NOT activated (§6.0.2.2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestTriggerInCodeBlock:
    async def test_trigger_in_fenced_code_no_dawp(self) -> None:
        """Trigger inside ``` fence must NOT activate DAWP (§6.0.2.2)."""
        responses = [
            # Trigger appears inside a fenced code block — not a scannable line
            {"content": f"Example usage:\n```\n{_TRIGGER}\n```\nThat's all."},
            # Main loop final
            {"content": "Main final."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp = _dawp_events(events)
        assert dawp == [], (
            "Trigger inside ``` fence must NOT activate DAWP: "
            f"got {len(dawp)} DAWP events unexpectedly"
        )

    async def test_trigger_in_fenced_code_main_loop_ends_normally(self) -> None:
        """When trigger is in code fence, main loop exits normally on the first final response."""
        responses = [
            # No trigger detected → outcome.kind=final → main loop exits after 1 iteration
            {"content": f"See example:\n```\n{_TRIGGER}\n```\nNone triggered."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        result_events = [e for e in events if e.get("type") == "result"]
        # No DAWP drain → outcome.kind=final → main loop returns after 1 iteration
        assert len(result_events) == 1
        # No DAWP events confirms the fence prevented activation (separate test verifies this)
        assert _dawp_events(events) == []

    async def test_trigger_in_blockquote_no_dawp(self) -> None:
        """Trigger inside > blockquote must NOT activate DAWP (§6.0.2.2)."""
        responses = [
            {"content": f"Quote:\n> {_TRIGGER}\nDone."},
            {"content": "Main final."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawp = _dawp_events(events)
        assert dawp == [], (
            "Trigger inside blockquote must NOT activate DAWP: "
            f"got {len(dawp)} DAWP events"
        )


# ---------------------------------------------------------------------------
# trigger_once guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestTriggerOnce:
    async def test_trigger_once_prevents_second_activation(self) -> None:
        """trigger_once=True: second main-loop iteration with trigger does NOT re-enqueue."""
        responses = [
            # Iteration 1: trigger fires → DAWP activated
            {"content": f"First trigger.\n{_TRIGGER}"},
            # DAWP step 0
            {"content": f"Evidence.\n{_PROMPT_MARKER}"},
            # DAWP step 1
            {"content": f"Done.\n{_DAWP_MARKER}"},
            # Iteration 2: trigger appears again — must NOT fire a second time
            {"content": f"Second trigger.\n{_TRIGGER}"},
            # Main final
            {"content": "Final."},
        ]
        agent, plugin_ctx = await _make_agent_with_dawp(responses, max_iterations=10)

        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # Count distinct DAWP run_ids to confirm only one DAWP run occurred
        run_ids = {
            e.get("loop_scope", {}).get("run_id")
            for e in _dawp_events(events)
            if e.get("loop_scope", {}).get("run_id") is not None
        }
        assert len(run_ids) == 1, (
            f"Expected exactly 1 DAWP run (trigger_once), got run_ids={run_ids}"
        )

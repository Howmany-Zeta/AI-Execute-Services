"""
D2-06 — Homomorphic streaming E2E tests (R3, §8.1, §12).

Verifies that DAWP segment events are structurally identical to main-loop events
("homomorphic"), differing only by the presence of ``loop_scope.kind="dawp"``.

Test matrix:
1. TestHomomorphicEventSequence   — event sequence alternates main + dawp correctly
2. TestHomomorphicEventShapes     — iteration_start / token / tool_result shapes match main loop
3. TestStreamBoundaryEvents       — dawp_run_started / dawp_run_completed optional flag
4. TestBaseworkflowMinimalPath    — works without legacy dawp_run_* tools in schema
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.models import PluginConfig, PluginPhase
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FIXTURES = Path(__file__).parents[3] / "fixtures" / "dawp"
_TRIGGER_INLINE = str(_FIXTURES / "trigger_inline.dawp.md")

# Markers matching trigger_inline.dawp.md
_TRIGGER = "<START_INLINE_REVIEW>"
_PROMPT_MARKER = "<INLINE_STEP_DONE>"
_DAWP_MARKER = "<INLINE_REVIEW_COMPLETE>"

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
        if payload.get("tool_calls") is not None:
            yield StreamChunk(type="tool_calls", tool_calls=payload["tool_calls"])
        else:
            yield StreamChunk(type="token", content=payload.get("content", ""))

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 20,
    plugin_options: dict[str, Any] | None = None,
) -> tuple[HybridAgent, Any, MockLLM]:
    """Create HybridAgent with DawpPlugin from trigger_inline fixture."""
    options: dict[str, Any] = {"document_path": _TRIGGER_INLINE}
    if plugin_options:
        options.update(plugin_options)

    config = AgentConfiguration(
        goal="e2e streaming test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="dawp", enabled=True, options=options),
        ],
    )
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "mock tool"
    mock_tool._schemas = {"q": MagicMock()}
    mock_tool.run_async = AsyncMock(return_value="tool result")

    llm = MockLLM(responses)
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="e2e-dawp-test",
            name="E2E DAWP Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "e2e test"},
        context={},
        task_description="e2e test",
    )
    if agent._plugin_manager is not None:
        await agent._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
        await agent._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)

    budget = TaskIterationBudget(limit=max_iterations)
    plugin_ctx.plugin_state[_BUDGET_KEY] = budget
    return agent, plugin_ctx, llm


async def _collect(gen) -> list[dict[str, Any]]:
    return [e async for e in gen]


# ---------------------------------------------------------------------------
# Event filter helpers
# ---------------------------------------------------------------------------


def _dawp_events(events: list[dict]) -> list[dict]:
    return [e for e in events if e.get("loop_scope", {}).get("kind") == "dawp"]


def _main_starts(events: list[dict]) -> list[dict]:
    return [
        e for e in events
        if e.get("type") == "iteration_start" and "loop_scope" not in e
    ]


def _dawp_starts(events: list[dict]) -> list[dict]:
    return [
        e for e in events
        if e.get("type") == "iteration_start"
        and e.get("loop_scope", {}).get("kind") == "dawp"
    ]


def _standard_responses() -> list[dict[str, Any]]:
    """Responses for a full on_response_trigger run.

    LLM call order:
    0. main iter 0: produces trigger token
    1. DAWP step 0 (Prompt 0): emits Prompt Completion Marker
    2. DAWP step 1 (Prompt 1): emits DAWP Completion Marker
    3. main iter 1 (after DAWP): final answer
    """
    return [
        {"content": f"Analysis complete.\n{_TRIGGER}"},       # main iter 0 — trigger
        {"content": f"Evidence gathered.\n{_PROMPT_MARKER}"}, # DAWP Prompt 0
        {"content": f"Synthesis done.\n{_DAWP_MARKER}"},      # DAWP Prompt 1
        {"content": "Final answer."},                          # main iter 1
    ]


# ===========================================================================
# 1. TestHomomorphicEventSequence
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestHomomorphicEventSequence:
    """Event stream alternates main (no loop_scope) + DAWP (loop_scope.kind=dawp)."""

    @pytest.fixture
    async def _events(self):
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        return await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

    async def test_dawp_events_exist(self, _events):
        """DAWP segment produces events tagged with loop_scope.kind='dawp'."""
        assert len(_dawp_events(_events)) > 0

    async def test_main_events_precede_dawp(self, _events):
        """At least one main-loop event appears before the first DAWP event."""
        mains = _main_starts(_events)
        dawps = _dawp_events(_events)
        assert len(mains) >= 1
        assert events_index_of(_events, mains[0]) < events_index_of(_events, dawps[0])

    async def test_dawp_followed_by_main(self, _events):
        """Main loop resumes (at least one main iteration_start) after DAWP ends (R2)."""
        mains = _main_starts(_events)
        dawps = _dawp_events(_events)
        last_dawp_idx = max(events_index_of(_events, e) for e in dawps)
        after_dawp_mains = [
            m for m in mains if events_index_of(_events, m) > last_dawp_idx
        ]
        assert len(after_dawp_mains) >= 1, "Main loop must produce an iteration_start after DAWP"

    async def test_final_result_comes_from_main(self, _events):
        """Final result event content comes from the post-DAWP main LLM call."""
        result_events = [e for e in _events if e.get("type") == "result"]
        assert len(result_events) >= 1
        assert result_events[-1].get("output") == "Final answer."

    async def test_no_dawp_run_star_tools_in_main_schema(self, _events):
        """No legacy dawp_run / dawp_publish_workflow tool events appear in the stream."""
        legacy_tool_events = [
            e for e in _events
            if e.get("type") in ("tool_call", "tool_result")
            and e.get("tool_name") in ("dawp_run", "dawp_publish_workflow")
        ]
        assert legacy_tool_events == [], (
            "Legacy dawp_run_* tool calls must not appear in a standard baseworkflow run"
        )


def events_index_of(events: list[dict], event: dict) -> int:
    return events.index(event)


# ===========================================================================
# 2. TestHomomorphicEventShapes
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestHomomorphicEventShapes:
    """DAWP segment events are structurally identical to main-loop events (R3, §8.1)."""

    @pytest.fixture
    async def _all_events(self):
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        return await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

    async def test_dawp_iteration_start_has_remaining(self, _all_events):
        """DAWP iteration_start events include the 'remaining' budget field (§8.1)."""
        dawp_iter_starts = _dawp_starts(_all_events)
        assert len(dawp_iter_starts) > 0, "Expected iteration_start events inside DAWP segment"
        for ev in dawp_iter_starts:
            assert "remaining" in ev, (
                f"DAWP iteration_start must include 'remaining': {ev}"
            )
            assert "max_iterations" in ev, (
                f"DAWP iteration_start must include 'max_iterations': {ev}"
            )

    async def test_dawp_iteration_start_shape_matches_main(self, _all_events):
        """DAWP and main iteration_start events share the same required keys."""
        main_iter_starts = _main_starts(_all_events)
        dawp_iter_starts = _dawp_starts(_all_events)
        assert main_iter_starts, "Expected main-loop iteration_start events"
        assert dawp_iter_starts, "Expected DAWP iteration_start events"

        main_keys = set(main_iter_starts[0].keys()) - {"loop_scope"}
        dawp_keys = set(dawp_iter_starts[0].keys()) - {"loop_scope"}
        assert main_keys == dawp_keys, (
            f"DAWP iteration_start keys {dawp_keys} differ from main {main_keys}"
        )

    async def test_dawp_token_events_carry_loop_scope(self, _all_events):
        """Token events inside DAWP carry loop_scope.kind='dawp' (§8.1)."""
        dawp_tokens = [
            e for e in _all_events
            if e.get("type") == "token"
            and e.get("loop_scope", {}).get("kind") == "dawp"
        ]
        assert len(dawp_tokens) > 0, "Expected token events with loop_scope.kind=dawp"
        for ev in dawp_tokens:
            assert "content" in ev or "delta" in ev, (
                f"DAWP token event missing content/delta field: {ev}"
            )

    async def test_main_iteration_start_has_no_dawp_loop_scope(self, _all_events):
        """Main-loop iteration_start events must NOT carry loop_scope.kind='dawp'."""
        for ev in _main_starts(_all_events):
            scope = ev.get("loop_scope", {})
            assert scope.get("kind") != "dawp", (
                f"Main iteration_start should not have loop_scope.kind=dawp: {ev}"
            )

    async def test_dawp_events_consistently_scoped(self, _all_events):
        """Every event in the DAWP segment carries loop_scope.kind='dawp'."""
        for ev in _dawp_events(_all_events):
            assert ev.get("loop_scope", {}).get("kind") == "dawp", (
                f"DAWP event missing correct loop_scope: {ev}"
            )


# ===========================================================================
# 3. TestStreamBoundaryEvents
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStreamBoundaryEvents:
    """§8.1.1: dawp_run_started / dawp_run_completed are optional boundary events."""

    async def test_no_boundary_events_by_default(self):
        """Without stream_boundary_events=True, no dawp_run_started/completed events appear."""
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        boundary = [
            e for e in events
            if e.get("type") in ("dawp_run_started", "dawp_run_completed")
        ]
        assert boundary == [], (
            "Boundary events must NOT appear unless stream_boundary_events=True"
        )

    async def test_boundary_events_when_configured(self):
        """With stream_boundary_events=True, dawp_run_started and dawp_run_completed appear."""
        agent, plugin_ctx, _ = await _make_agent(
            _standard_responses(),
            plugin_options={"stream_boundary_events": True},
        )
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        started = [e for e in events if e.get("type") == "dawp_run_started"]
        completed = [e for e in events if e.get("type") == "dawp_run_completed"]
        assert len(started) >= 1, "Expected dawp_run_started when stream_boundary_events=True"
        assert len(completed) >= 1, "Expected dawp_run_completed when stream_boundary_events=True"

    async def test_boundary_event_shapes(self):
        """dawp_run_started and dawp_run_completed carry required fields (§8.1.1)."""
        agent, plugin_ctx, _ = await _make_agent(
            _standard_responses(),
            plugin_options={"stream_boundary_events": True},
        )
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        started = next((e for e in events if e.get("type") == "dawp_run_started"), None)
        completed = next((e for e in events if e.get("type") == "dawp_run_completed"), None)

        assert started is not None
        assert "run_id" in started
        assert "workflow_id" in started
        assert "trigger" in started
        assert started.get("loop_scope", {}).get("kind") == "dawp"

        assert completed is not None
        assert "run_id" in completed
        assert "success" in completed
        assert completed.get("loop_scope", {}).get("kind") == "dawp"

    async def test_boundary_events_wrap_dawp_segment(self):
        """dawp_run_started appears before, dawp_run_completed after, DAWP segment events."""
        agent, plugin_ctx, _ = await _make_agent(
            _standard_responses(),
            plugin_options={"stream_boundary_events": True},
        )
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )
        started_idx = next(
            (i for i, e in enumerate(events) if e.get("type") == "dawp_run_started"), None
        )
        completed_idx = next(
            (i for i, e in enumerate(events) if e.get("type") == "dawp_run_completed"), None
        )
        dawps = _dawp_events(events)
        assert started_idx is not None and completed_idx is not None
        assert started_idx < completed_idx
        if dawps:
            first_dawp_idx = events.index(dawps[0])
            assert started_idx <= first_dawp_idx


# ===========================================================================
# 4. TestBaseworkflowMinimalPath
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestBaseworkflowMinimalPath:
    """§12: baseworkflow minimal path works with DawpPlugin, without legacy tools."""

    async def test_baseworkflow_completes_without_legacy_tools(self):
        """Full DAWP run (on_response_trigger path) completes via loop_scope streaming.

        No dawp_run / dawp_publish_workflow tools are required in the agent schema.
        """
        agent, plugin_ctx, llm = await _make_agent(_standard_responses())
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) >= 1, "Expected a final result event from main loop"
        assert result_events[-1].get("output") == "Final answer."

        # Confirm legacy tools are absent from schema
        tool_schemas = getattr(agent, "_tool_schemas", [])
        schema_names = {s.get("name") for s in tool_schemas}
        assert "dawp_run" not in schema_names, (
            "dawp_run must not be in tool schemas for baseworkflow path"
        )
        assert "dawp_publish_workflow" not in schema_names, (
            "dawp_publish_workflow must not be in tool schemas for baseworkflow path"
        )

    async def test_dawp_segment_uses_shared_budget(self):
        """DAWP iterations consume the same budget pool as the main loop (D5)."""
        agent, plugin_ctx, llm = await _make_agent(_standard_responses(), max_iterations=10)
        budget = plugin_ctx.plugin_state[_BUDGET_KEY]
        initial_remaining = budget.remaining

        await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # 4 LLM calls consumed (main 0 + DAWP 2 + main 1)
        assert budget.remaining < initial_remaining, (
            "Budget must be consumed by both main and DAWP iterations"
        )
        assert llm.call_count >= 4, f"Expected at least 4 LLM calls, got {llm.call_count}"

    async def test_main_loop_continues_after_dawp(self):
        """R2: Main loop continues after DAWP run completes and produces its own result."""
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        dawps = _dawp_events(events)
        mains = _main_starts(events)
        assert len(dawps) > 0 and len(mains) >= 1

        last_dawp_idx = max(events.index(e) for e in dawps)
        post_dawp_mains = [m for m in mains if events.index(m) > last_dawp_idx]
        assert len(post_dawp_mains) >= 1, "Main loop must resume with a new iteration after DAWP"

    async def test_no_orphan_tool_calls_in_events(self):
        """No tool_call events appear without a paired tool_result (basic stream integrity)."""
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        # Every tool_call event should have a corresponding tool_result with the same tool_call_id
        tool_call_ids = {
            e.get("tool_call_id")
            for e in events
            if e.get("type") == "tool_call" and e.get("tool_call_id")
        }
        tool_result_ids = {
            e.get("tool_call_id")
            for e in events
            if e.get("type") == "tool_result" and e.get("tool_call_id")
        }
        orphans = tool_call_ids - tool_result_ids
        assert orphans == set(), f"Orphan tool_call events without tool_result: {orphans}"


# ===========================================================================
# 5. TestSdkStreamConsumer — SDK/UI subscription (§8.2, §14)
# ===========================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestSdkStreamConsumer:
    """DawpStreamConsumer tracks dawp_run_* boundary events from a live stream."""

    async def test_consumer_opens_and_closes_panel_on_boundary_events(self) -> None:
        from aiecs.domain.agent.plugins.dawp.stream_consumer import DawpStreamConsumer

        started: list[str] = []
        completed: list[tuple[str, bool]] = []
        consumer = DawpStreamConsumer(
            on_run_started=lambda p: started.append(p.run_id),
            on_run_completed=lambda p: completed.append((p.run_id, bool(p.success))),
        )

        agent, plugin_ctx, _ = await _make_agent(
            _standard_responses(),
            plugin_options={"stream_boundary_events": True},
        )
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        for event in events:
            consumer.consume(event)

        assert len(started) >= 1, "SDK must receive dawp_run_started callback"
        assert len(completed) >= 1, "SDK must receive dawp_run_completed callback"
        assert started[0] == completed[0][0], "started/completed must share run_id"
        assert completed[0][1] is True
        assert consumer.open_run_ids == [], "All panels closed after dawp_run_completed"

    async def test_consumer_ignores_run_boundary_when_flag_off(self) -> None:
        from aiecs.domain.agent.plugins.dawp.stream_consumer import DawpStreamConsumer

        consumer = DawpStreamConsumer()
        agent, plugin_ctx, _ = await _make_agent(_standard_responses())
        events = await _collect(
            agent._tool_loop_streaming_with_plugins("test task", {}, plugin_ctx)
        )

        run_boundary = [
            e for e in events if e.get("type") in ("dawp_run_started", "dawp_run_completed")
        ]
        assert run_boundary == [], "Run boundary events require stream_boundary_events=True"

        step_boundary = [
            e for e in events if e.get("type") in ("dawp_step_started", "dawp_step_completed")
        ]
        assert len(step_boundary) >= 2, "Step boundary events are always emitted"

        for event in events:
            consumer.consume(event)

        assert all(p.placement is None for p in consumer.panels.values())
        assert consumer.open_run_ids == []


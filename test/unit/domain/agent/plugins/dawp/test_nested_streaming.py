"""
Unit tests for D1-04 — _run_tool_loop_nested_streaming (§6.4).

Covers:
- Every yielded event has loop_scope.kind == "dawp"
- loop_scope carries the run_id, workflow_id, step_id from the scope
- budget.consume(1) fires per nested iteration
- Budget exhaustion terminates the DAWP run and yields a result event (D3)
- step_iteration_cap limits nested iterations even when budget has more
- dawp.active_run_id set on entry and cleared in finally
- dawp.active_run_id cleared even when the loop exits normally (stop_match / final)
- run_iteration_hooks=False (default) does NOT fire ON_ITERATION_START/END
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import PLUGIN_STATE_KEY, TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

_BUDGET_KEY = PLUGIN_STATE_KEY


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class HookAuditPlugin(BaseAgentPlugin):
    """Records every ON_ITERATION_START / ON_ITERATION_END call."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="hook_audit",
        version="1.0.0",
        description="Audit plugin for iteration hooks",
        priority=10,
    )

    async def on_iteration_start(self, ctx: AgentPluginContext, iteration: int) -> None:
        ctx.plugin_state.setdefault("hook_audit.starts", []).append(iteration)

    async def on_iteration_end(
        self, ctx: AgentPluginContext, iteration: int, step: dict[str, Any]
    ) -> None:
        ctx.plugin_state.setdefault("hook_audit.ends", []).append(iteration)


class MockLLM(BaseLLMClient):
    """Plays back a fixed list of responses (tool calls then text)."""

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
            content = payload.get("content", "DAWP step done.")
            yield StreamChunk(type="token", content=content)

    async def close(self) -> None:
        pass


def _text(content: str = "DAWP step done.") -> dict[str, Any]:
    return {"content": content, "tool_calls": None}


def _tool_call(name: str = "mock_tool") -> dict[str, Any]:
    return {
        "content": "Calling tool.",
        "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": name, "arguments": "{}"}}
        ],
    }


def _make_mock_tool(name: str = "mock_tool") -> Any:
    t = MagicMock()
    t.name = name
    t.description = "A mock tool"
    t._schemas = {"query": MagicMock()}
    t.run_async = AsyncMock(return_value="tool result")
    return t


def _make_scope(
    run_id: str | None = None,
    workflow_id: str = "test-workflow",
    step_id: str = "step-0",
    step_index: int = 0,
    prompt_index: int = 0,
) -> LoopScope:
    return LoopScope(
        kind="dawp",
        run_id=run_id or f"run-{uuid.uuid4().hex[:8]}",
        workflow_id=workflow_id,
        step_id=step_id,
        step_index=step_index,
        prompt_index=prompt_index,
    )


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 10,
    extra_plugins: list[PluginConfig] | None = None,
) -> tuple[HybridAgent, AgentPluginContext]:
    registry = PluginRegistry.default()
    registry.register("hook_audit", HookAuditPlugin, origin="registry")

    plugins = [
        PluginConfig(name="memory", enabled=False),
        PluginConfig(name="skill", enabled=False),
        PluginConfig(name="hook_audit", enabled=True),
    ] + (extra_plugins or [])

    config = AgentConfiguration(
        goal="nested runner test",
        llm_model="test-model",
        plugins=plugins,
    )
    mock_tool = _make_mock_tool()
    llm = MockLLM(responses)

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="nested-test",
            name="Nested Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
            plugin_registry=registry,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "nested test"},
        context={},
        task_description="nested test",
    )
    return agent, plugin_ctx


async def _run_nested(
    agent: HybridAgent,
    plugin_ctx: AgentPluginContext,
    scope: LoopScope,
    budget: TaskIterationBudget,
    step_iteration_cap: int | None = None,
    run_iteration_hooks: bool = False,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    messages = [LLMMessage(role="user", content="DAWP step prompt")]
    async for event in agent._run_tool_loop_nested_streaming(
        messages,
        {},
        plugin_ctx,
        scope=scope,
        budget=budget,
        step_iteration_cap=step_iteration_cap,
        run_iteration_hooks=run_iteration_hooks,
    ):
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Tests — loop_scope tagging
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestNestedStreamingScopeTagging:
    """Every event must carry loop_scope.kind == "dawp"."""

    async def test_all_events_have_dawp_scope(self) -> None:
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(agent, plugin_ctx, scope, budget)

        assert events, "Expected at least one event"
        for event in events:
            ls = event.get("loop_scope")
            assert ls is not None, f"Missing loop_scope on {event}"
            assert ls.get("kind") == "dawp", f"Expected kind=dawp, got {ls}"

    async def test_loop_scope_carries_run_id(self) -> None:
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope(run_id="run-abc123")
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(agent, plugin_ctx, scope, budget)

        for event in events:
            assert event["loop_scope"]["run_id"] == "run-abc123"

    async def test_loop_scope_carries_workflow_and_step_ids(self) -> None:
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope(workflow_id="sales-analysis", step_id="gather", step_index=2)
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(agent, plugin_ctx, scope, budget)

        for event in events:
            ls = event["loop_scope"]
            assert ls["workflow_id"] == "sales-analysis"
            assert ls["step_id"] == "gather"
            assert ls["step_index"] == 2

    async def test_multi_iteration_all_events_scoped(self) -> None:
        """Tool call followed by text — both iterations' events carry dawp scope."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(agent, plugin_ctx, scope, budget)

        assert len(events) > 1, "Expected events from multiple iterations"
        for event in events:
            assert event.get("loop_scope", {}).get("kind") == "dawp"


# ---------------------------------------------------------------------------
# Tests — budget consumption
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestNestedStreamingBudget:
    """Budget is consumed 1 per nested iteration."""

    async def test_single_text_iteration_consumes_one(self) -> None:
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget)

        assert budget.consumed == 1
        assert budget.remaining == 4

    async def test_tool_then_text_consumes_two(self) -> None:
        agent, plugin_ctx = await _make_agent([_tool_call(), _text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget)

        assert budget.consumed == 2
        assert budget.remaining == 3

    async def test_budget_exhaustion_terminates_run(self) -> None:
        """All responses are tool calls → budget=2 exhausts after 2 nested iterations (D3)."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _tool_call(), _tool_call()])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=2)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(agent, plugin_ctx, scope, budget)

        assert budget.is_exhausted
        # A result event must be yielded on exhaustion
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) == 1
        # The result event must also carry dawp scope
        assert result_events[0]["loop_scope"]["kind"] == "dawp"

    async def test_step_iteration_cap_limits_below_budget(self) -> None:
        """step_iteration_cap=1 stops after one iteration even with budget=5."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _tool_call()])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await _run_nested(
                agent, plugin_ctx, scope, budget, step_iteration_cap=1
            )

        assert budget.consumed == 1
        assert budget.remaining == 4
        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) == 1

    async def test_step_cap_larger_than_budget_stops_at_budget(self) -> None:
        """step_iteration_cap=10, budget=2 → stops after 2 (budget wins)."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _tool_call(), _tool_call()])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=2)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget, step_iteration_cap=10)

        assert budget.consumed == 2
        assert budget.is_exhausted

    async def test_none_step_cap_runs_until_natural_end(self) -> None:
        """step_iteration_cap=None → runs until final response (not budget)."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=10)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget, step_iteration_cap=None)

        assert budget.consumed == 2
        assert not budget.is_exhausted


# ---------------------------------------------------------------------------
# Tests — dawp.active_run_id lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestNestedStreamingActiveRunId:
    """plugin_state["dawp.active_run_id"] is managed by the nested runner."""

    async def test_active_run_id_set_during_run(self) -> None:
        """Verify active_run_id is present during iteration (observed via side effect)."""
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope(run_id="run-set-test")
        budget = TaskIterationBudget(limit=5)

        observed_ids: list[str | None] = []

        original_core = agent._run_tool_loop_core_iteration_streaming

        async def _spy_core(messages, context, iteration, state, **kwargs):
            observed_ids.append(plugin_ctx.plugin_state.get("dawp.active_run_id"))
            async for event in original_core(messages, context, iteration, state, **kwargs):
                yield event

        with patch.object(agent, "_run_tool_loop_core_iteration_streaming", _spy_core):
            with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
                await _run_nested(agent, plugin_ctx, scope, budget)

        assert observed_ids, "Core iteration was not called"
        assert all(rid == "run-set-test" for rid in observed_ids)

    async def test_active_run_id_cleared_after_normal_exit(self) -> None:
        """After normal completion, dawp.active_run_id is absent from plugin_state."""
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope(run_id="run-clear-normal")
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget)

        assert "dawp.active_run_id" not in plugin_ctx.plugin_state

    async def test_active_run_id_cleared_after_budget_exhaustion(self) -> None:
        """Even when budget is exhausted, active_run_id is cleared (finally block)."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _tool_call()])
        scope = _make_scope(run_id="run-exhaust")
        budget = TaskIterationBudget(limit=2)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget)

        assert "dawp.active_run_id" not in plugin_ctx.plugin_state


# ---------------------------------------------------------------------------
# Tests — run_iteration_hooks flag
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestNestedStreamingHooks:
    """ON_ITERATION_START/END are only fired when run_iteration_hooks=True."""

    async def test_hooks_not_fired_by_default(self) -> None:
        agent, plugin_ctx = await _make_agent([_text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(agent, plugin_ctx, scope, budget, run_iteration_hooks=False)

        assert "hook_audit.starts" not in plugin_ctx.plugin_state
        assert "hook_audit.ends" not in plugin_ctx.plugin_state

    async def test_hooks_fired_when_enabled(self) -> None:
        """run_iteration_hooks=True must invoke ON_ITERATION_START and ON_ITERATION_END."""
        agent, plugin_ctx = await _make_agent([_tool_call(), _text("Done.")])
        scope = _make_scope()
        budget = TaskIterationBudget(limit=5)

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await _run_nested(
                agent, plugin_ctx, scope, budget, run_iteration_hooks=True
            )

        starts = plugin_ctx.plugin_state.get("hook_audit.starts", [])
        ends = plugin_ctx.plugin_state.get("hook_audit.ends", [])
        assert len(starts) == 2, f"Expected 2 iteration_start hooks, got {starts}"
        assert len(ends) == 2, f"Expected 2 iteration_end hooks, got {ends}"

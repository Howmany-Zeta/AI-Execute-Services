"""
Unit tests for D1-03 — budget-driven main iteration loop (§4.4, D5).

Covers:
- Budget is created and stored in plugin_state on first call
- budget.consume(1) fires once per iteration
- Exhausted budget → loop exits, returns max-iterations result
- Streaming iteration_start carries budget.limit / budget.remaining (pre-consume)
- Pre-existing budget in plugin_state is reused (shared-pool wiring)
- plugin_ctx=None path creates a local budget without crashing
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import PLUGIN_STATE_KEY, TaskIterationBudget
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

_BUDGET_KEY = PLUGIN_STATE_KEY  # "task.iteration_budget"


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class MockLLM(BaseLLMClient):
    """Plays back a list of (content, tool_calls) pairs, cycling the last entry.

    Both ``generate_text`` and ``stream_text`` advance the same index so the
    two paths produce equivalent multi-iteration behaviour.
    """

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self._responses = responses
        self._idx = 0

    def _next_payload(self) -> dict[str, Any]:
        payload = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        return payload

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        payload = self._next_payload()
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

        payload = self._next_payload()
        if payload.get("tool_calls") is not None:
            # Emit the tool calls batch so the streaming core detects them
            yield StreamChunk(type="tool_calls", tool_calls=payload["tool_calls"])
        else:
            content = payload.get("content", "Final answer.")
            yield StreamChunk(type="token", content=content)

    async def close(self) -> None:
        pass


def _text_payload(content: str = "Final answer.") -> dict[str, Any]:
    return {"content": content, "tool_calls": None}


def _tool_call_payload(tool_name: str = "mock_tool") -> dict[str, Any]:
    return {
        "content": "Calling tool.",
        "tool_calls": [
            {
                "id": "call_0",
                "type": "function",
                "function": {"name": tool_name, "arguments": "{}"},
            }
        ],
    }


def _make_mock_tool(name: str = "mock_tool") -> Any:
    t = MagicMock()
    t.name = name
    t.description = "A mock tool"
    t._schemas = {"query": MagicMock()}
    t.run_async = AsyncMock(return_value="tool result")
    return t


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 5,
    extra_plugins: list[PluginConfig] | None = None,
) -> tuple[HybridAgent, AgentPluginContext]:
    registry = PluginRegistry.default()
    base_plugins = [
        PluginConfig(name="memory", enabled=False),
        PluginConfig(name="skill", enabled=False),
    ]
    config = AgentConfiguration(
        goal="budget loop test",
        llm_model="test-model",
        plugins=base_plugins + (extra_plugins or []),
    )
    mock_tool = _make_mock_tool()
    llm = MockLLM(responses)

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="budget-test",
            name="Budget Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
            plugin_registry=registry,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "budget test"},
        context={},
        task_description="budget test",
    )
    return agent, plugin_ctx


# ---------------------------------------------------------------------------
# Non-streaming path — _run_tool_loop_with_iteration_hooks
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestBudgetNonStreaming:
    """Budget-driven iteration loop — non-streaming path."""

    async def test_budget_created_and_stored_in_plugin_state(self) -> None:
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=5)
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        budget = plugin_ctx.plugin_state.get(_BUDGET_KEY)
        assert isinstance(budget, TaskIterationBudget)
        assert budget.limit == 5

    async def test_single_final_iteration_consumes_one(self) -> None:
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=5)
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        assert budget.consumed == 1
        assert budget.remaining == 4

    async def test_tool_then_text_consumes_two(self) -> None:
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")], max_iterations=5
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        assert budget.consumed == 2
        assert budget.remaining == 3

    async def test_budget_exhausted_returns_max_iterations_result(self) -> None:
        """When budget hits 0, loop exits with the max-iterations fallback."""
        # All responses are tool calls → loop never terminates naturally;
        # budget should stop it after max_iterations=2.
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _tool_call_payload(), _tool_call_payload()],
            max_iterations=2,
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            result = await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        assert budget.is_exhausted
        assert budget.consumed == 2
        # Result should be the max-iterations fallback (success may be False)
        assert "final_response" in result

    async def test_pre_existing_budget_is_reused(self) -> None:
        """A budget already in plugin_state is used instead of creating a new one."""
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=10)
        # Pre-seed a budget with limit=3, consumed=1 → only 2 remaining
        pre_budget = TaskIterationBudget(limit=3, consumed=1)
        plugin_ctx.plugin_state[_BUDGET_KEY] = pre_budget

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        # The SAME object must be mutated, limit preserved from pre-seed
        assert plugin_ctx.plugin_state[_BUDGET_KEY] is pre_budget
        assert pre_budget.limit == 3
        assert pre_budget.consumed == 2  # one more iteration consumed

    async def test_plugin_ctx_none_does_not_crash(self) -> None:
        """plugin_ctx=None path creates a local budget and completes without error."""
        config = AgentConfiguration(
            goal="null ctx test",
            llm_model="test-model",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
            ],
        )
        llm = MockLLM([_text_payload("Done.")])
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            agent = HybridAgent(
                agent_id="null-ctx-test",
                name="Null Ctx",
                llm_client=llm,
                tools=["mock_tool"],
                config=config,
                max_iterations=3,
            )
            await agent.initialize()
            messages = [LLMMessage(role="user", content="test")]
            result = await agent._run_tool_loop_with_iteration_hooks(
                messages, {}, plugin_ctx=None
            )

        assert "final_response" in result


# ---------------------------------------------------------------------------
# Streaming path — _tool_loop_streaming_with_plugins
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestBudgetStreaming:
    """Budget-driven iteration loop — streaming path."""

    async def _collect_events(
        self, agent: HybridAgent, plugin_ctx: AgentPluginContext, task: str = "test"
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        async for event in agent._tool_loop_streaming_with_plugins(task, {}, plugin_ctx):
            events.append(event)
        return events

    async def test_budget_created_and_stored_streaming(self) -> None:
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=5)
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await self._collect_events(agent, plugin_ctx)

        budget = plugin_ctx.plugin_state.get(_BUDGET_KEY)
        assert isinstance(budget, TaskIterationBudget)
        assert budget.limit == 5

    async def test_iteration_start_has_budget_limit(self) -> None:
        """iteration_start.max_iterations must equal budget.limit (not self._max_iterations)."""
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=7)
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await self._collect_events(agent, plugin_ctx)

        iter_starts = [e for e in events if e.get("type") == "iteration_start"]
        assert len(iter_starts) == 1
        assert iter_starts[0]["max_iterations"] == 7

    async def test_iteration_start_remaining_is_pre_consume(self) -> None:
        """iteration_start.remaining = budget.remaining BEFORE consume for that iteration."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")], max_iterations=5
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await self._collect_events(agent, plugin_ctx)

        iter_starts = [e for e in events if e.get("type") == "iteration_start"]
        # First iteration_start fires when remaining=5 (nothing consumed yet)
        assert iter_starts[0]["remaining"] == 5
        # Second iteration_start fires when remaining=4 (1 consumed)
        assert iter_starts[1]["remaining"] == 4

    async def test_streaming_budget_consumed_matches_iterations(self) -> None:
        """Consumed count equals the number of LLM+tool iterations completed."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _tool_call_payload(), _text_payload("Done.")],
            max_iterations=5,
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await self._collect_events(agent, plugin_ctx)

        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        assert budget.consumed == 3
        assert budget.remaining == 2

    async def test_budget_exhausted_streaming_yields_result(self) -> None:
        """Exhausted budget terminates the loop; a result event is still yielded."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _tool_call_payload()],
            max_iterations=2,
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await self._collect_events(agent, plugin_ctx)

        result_events = [e for e in events if e.get("type") == "result"]
        assert len(result_events) == 1
        budget: TaskIterationBudget = plugin_ctx.plugin_state[_BUDGET_KEY]
        assert budget.is_exhausted

    async def test_pre_existing_budget_reused_streaming(self) -> None:
        """A pre-seeded budget in plugin_state is used instead of creating a new one."""
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=10)
        pre_budget = TaskIterationBudget(limit=4, consumed=1)
        plugin_ctx.plugin_state[_BUDGET_KEY] = pre_budget

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await self._collect_events(agent, plugin_ctx)

        assert plugin_ctx.plugin_state[_BUDGET_KEY] is pre_budget
        assert pre_budget.limit == 4
        assert pre_budget.consumed == 2

    async def test_iteration_start_remaining_reflects_shared_pool(self) -> None:
        """When a pre-seeded budget is used, remaining in iteration_start is from that pool."""
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")], max_iterations=10)
        pre_budget = TaskIterationBudget(limit=6, consumed=3)  # remaining=3
        plugin_ctx.plugin_state[_BUDGET_KEY] = pre_budget

        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            events = await self._collect_events(agent, plugin_ctx)

        iter_starts = [e for e in events if e.get("type") == "iteration_start"]
        # Only 1 iteration runs (text payload → final); remaining before consume = 3
        assert iter_starts[0]["remaining"] == 3
        assert iter_starts[0]["max_iterations"] == 6

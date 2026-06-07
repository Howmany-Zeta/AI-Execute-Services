"""
Unit tests for task.response_index counter in HybridAgent (D1-02).

Covers:
- response_index increments on every iteration (pure tool AND pure text)
- response_index is 1-based (first iteration → 1)
- response_index exposed in ON_ITERATION_END step payload
- response_index tracks across multiple iterations
- plugins=[] path is unaffected (no regression)
"""

from __future__ import annotations

from typing import Any, ClassVar
from unittest.mock import patch

import pytest

from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginConfig, PluginMetadata
from aiecs.domain.agent.plugins.registry import PluginRegistry
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse

RESPONSE_INDEX_KEY = "task.response_index"
AUDIT_KEY = "response_index.audit"


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class ResponseIndexAuditPlugin(BaseAgentPlugin):
    """Records response_index from each ON_ITERATION_END step payload."""

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="ri_audit",
        version="1.0.0",
        description="response_index audit plugin",
        priority=10,
    )

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        audit = ctx.plugin_state.setdefault(AUDIT_KEY, [])
        audit.append(
            {
                "iteration": iteration,
                "response_index_in_step": step.get("response_index"),
                "response_index_in_state": ctx.plugin_state.get(RESPONSE_INDEX_KEY),
            }
        )


class MockLLM(BaseLLMClient):
    """Plays back a list of (content, tool_calls) pairs."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(provider_name="openai")
        self.responses = responses
        self._idx = 0

    async def generate_text(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        payload = self.responses[min(self._idx, len(self.responses) - 1)]
        self._idx += 1
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
        yield "token"

    async def close(self) -> None:
        pass


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


def _text_payload(content: str = "Final answer.") -> dict[str, Any]:
    return {"content": content, "tool_calls": None}


async def _make_agent(
    responses: list[dict[str, Any]],
    max_iterations: int = 5,
) -> tuple[HybridAgent, AgentPluginContext]:
    registry = PluginRegistry.default()
    registry.register("ri_audit", ResponseIndexAuditPlugin, origin="registry")

    config = AgentConfiguration(
        goal="response_index test",
        llm_model="test-model",
        plugins=[
            PluginConfig(name="memory", enabled=False),
            PluginConfig(name="skill", enabled=False),
            PluginConfig(name="ri_audit", enabled=True),
        ],
    )
    mock_tool = _make_mock_tool()
    llm = MockLLM(responses)

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        agent = HybridAgent(
            agent_id="ri-test",
            name="RI Test",
            llm_client=llm,
            tools=["mock_tool"],
            config=config,
            max_iterations=max_iterations,
            plugin_registry=registry,
        )
        await agent.initialize()

    plugin_ctx = agent._make_plugin_context(
        task={"description": "ri test"},
        context={},
        task_description="ri test",
    )
    return agent, plugin_ctx


def _make_mock_tool():
    from unittest.mock import AsyncMock, MagicMock

    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool"
    mock_tool._schemas = {"query": MagicMock()}

    async def _run(**kwargs: Any) -> str:
        return "tool result"

    mock_tool.run_async = AsyncMock(side_effect=_run)
    return mock_tool


# ---------------------------------------------------------------------------
# Tests — non-streaming path (_tool_loop_with_plugins)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestResponseIndexNonStreaming:
    """response_index increments in the non-streaming iteration loop."""

    async def test_text_only_iteration_increments_to_one(self) -> None:
        agent, plugin_ctx = await _make_agent([_text_payload("Done.")])
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        assert plugin_ctx.plugin_state.get(RESPONSE_INDEX_KEY) == 1

    async def test_tool_then_text_increments_twice(self) -> None:
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")]
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        assert plugin_ctx.plugin_state.get(RESPONSE_INDEX_KEY) == 2

    async def test_three_tool_iterations_increments_three_times(self) -> None:
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _tool_call_payload(), _text_payload("Done.")],
            max_iterations=5,
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        assert plugin_ctx.plugin_state.get(RESPONSE_INDEX_KEY) == 3

    async def test_response_index_in_step_payload_is_one_based(self) -> None:
        """ON_ITERATION_END step must carry response_index (1-based)."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")]
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        audit = plugin_ctx.plugin_state.get(AUDIT_KEY, [])
        assert len(audit) == 2
        assert audit[0]["response_index_in_step"] == 1  # first iteration
        assert audit[1]["response_index_in_step"] == 2  # second iteration

    async def test_step_response_index_matches_plugin_state(self) -> None:
        """Step payload response_index must equal plugin_state value at END time."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")]
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        audit = plugin_ctx.plugin_state.get(AUDIT_KEY, [])
        for record in audit:
            assert record["response_index_in_step"] == record["response_index_in_state"]

    async def test_pure_tool_iteration_also_increments(self) -> None:
        """Tool-only iterations (no final text yet) still count as a response."""
        agent, plugin_ctx = await _make_agent(
            [_tool_call_payload(), _text_payload("Done.")]
        )
        with patch("aiecs.tools.get_tool", return_value=_make_mock_tool()):
            await agent._tool_loop_with_plugins("test", {}, plugin_ctx)

        audit = plugin_ctx.plugin_state.get(AUDIT_KEY, [])
        # Iteration 0 was a tool call — response_index must still be 1
        assert audit[0]["response_index_in_step"] == 1
        assert audit[0]["iteration"] == 0


# ---------------------------------------------------------------------------
# Hybrid regression — plugins=[] must still pass (no response_index side-effects)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestResponseIndexNoRegression:
    """Existing behaviour with plugins=[] / no plugin_ctx is unaffected."""

    async def test_tool_loop_with_no_plugin_ctx_does_not_crash(self) -> None:
        """_run_tool_loop_with_iteration_hooks with plugin_ctx=None must not crash."""
        config = AgentConfiguration(
            goal="no plugin test",
            llm_model="test-model",
            plugins=[
                PluginConfig(name="memory", enabled=False),
                PluginConfig(name="skill", enabled=False),
            ],
        )
        mock_tool = _make_mock_tool()
        llm = MockLLM([_text_payload("Done.")])

        with patch("aiecs.tools.get_tool", return_value=mock_tool):
            agent = HybridAgent(
                agent_id="no-plugin-test",
                name="No Plugin Test",
                llm_client=llm,
                tools=["mock_tool"],
                config=config,
                max_iterations=3,
            )
            await agent.initialize()
            # Build a minimal message list directly — no plugin_ctx needed here.
            messages = [LLMMessage(role="user", content="test")]
            result = await agent._run_tool_loop_with_iteration_hooks(messages, {}, plugin_ctx=None)

        assert "final_response" in result

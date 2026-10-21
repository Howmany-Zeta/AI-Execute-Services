"""Callers see implicit-cache hits, and each tool-loop iteration resolves compression once."""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.agent.tool_loop_core import ToolLoopRunState
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.llm.clients.openai_compatible_mixin import StreamChunk


class _CacheLLM(BaseLLMClient):
    def __init__(self, response: LLMResponse):
        super().__init__(provider_name="openai")
        self.response = response
        self.stream_chunks: List[Any] = []

    async def generate_text(self, messages, **kwargs) -> LLMResponse:
        return self.response

    async def stream_text(self, **kwargs):
        for chunk in self.stream_chunks:
            yield chunk

    async def close(self):
        return None


def _mock_tool():
    tool = MagicMock()
    tool.name = "mock_tool"
    tool.description = "A mock tool"
    tool._schemas = {"query": MagicMock()}
    tool.run_async = AsyncMock(return_value="ok")
    return tool


async def _agent(client: _CacheLLM) -> HybridAgent:
    config = AgentConfiguration(
        llm_model="mock-model",
        system_prompt="You are a test agent.",
        enable_context_compression=True,
    )
    with patch("aiecs.tools.get_tool", return_value=_mock_tool()):
        agent = HybridAgent(
            agent_id="cache-hint",
            name="Cache",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=3,
        )
        await agent.initialize()
    return agent


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_result_reports_cache_hit():
    response = LLMResponse(
        content="done",
        provider="openai",
        model="mock-model",
        tokens_used=10,
        cache_read_tokens=40,
        cache_hit=True,
    )
    agent = await _agent(_CacheLLM(response))

    result = await agent._tool_loop("Analyze", {})

    assert result["cache_hit"] is True
    assert result["cache_read_tokens"] == 40
    assert agent._metrics.cache_hits == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_stream_usage_zero_is_a_cache_miss_event():
    client = _CacheLLM(LLMResponse(content="", provider="openai", model="mock-model"))
    client.stream_chunks = [
        StreamChunk(type="token", content="hi"),
        StreamChunk(type="usage", usage={"cache_read_tokens": 0, "prompt_tokens": 10}),
    ]
    agent = await _agent(client)
    state = ToolLoopRunState()

    events = []
    async for event in agent._run_tool_loop_core_iteration_streaming(
        [LLMMessage(role="user", content="task")],
        {},
        0,
        state,
    ):
        events.append(event)

    status = next(event for event in events if event["type"] == "cache_status")
    assert status["cache_hit"] is False
    assert status["cache_read_tokens"] == 0
    assert agent._metrics.cache_misses == 1
    assert agent._metrics.cache_hits == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_compression_context_is_built_once_per_iteration():
    response = LLMResponse(content="done", provider="openai", model="mock-model", tokens_used=1)
    agent = await _agent(_CacheLLM(response))
    calls = {"n": 0}
    original = agent._build_tool_loop_compression_context_async

    async def _counting(context: Dict[str, Any]):
        calls["n"] += 1
        return await original(context)

    agent._build_tool_loop_compression_context_async = _counting  # type: ignore[method-assign]

    await agent._tool_loop("Analyze", {"session_id": "sess-1"})

    assert calls["n"] == 1

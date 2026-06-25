"""HybridAgent W8/W11 compression integration tests (M2 rc1)."""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.context.compression.constants import TOOL_OUTPUT_TRUNCATED_HEADER
from aiecs.domain.context.compression.microcompact import microcompact_messages
from aiecs.domain.context.compression.tokens import estimate_message_tokens
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class _RecordingArtifactPort:
    def __init__(self, uri_prefix: str = "artifact://") -> None:
        self.uri_prefix = uri_prefix
        self.calls: list[tuple[str, str, str]] = []

    async def store_tool_output(
        self, *, session_id: str, tool_call_id: str, content: str
    ) -> str:
        self.calls.append((session_id, tool_call_id, content))
        return f"{self.uri_prefix}{session_id}/{tool_call_id}"


class MockLLMClientFunctionCalling(BaseLLMClient):
    def __init__(self, responses: List[Dict[str, Any]] | None = None) -> None:
        super().__init__(provider_name="openai")
        self.responses = responses or []
        self.call_count = 0
        self.all_messages: List[List[LLMMessage]] = []

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: List[Dict] | None = None,
        tool_choice: str | None = None,
        context: Dict | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.call_count += 1
        self.all_messages.append(list(messages))
        response_index = min(self.call_count - 1, len(self.responses) - 1)
        payload = self.responses[response_index]
        resp = LLMResponse(
            content=payload.get("content", ""),
            provider="openai",
            model=model or "gpt-4",
            tokens_used=10,
        )
        if payload.get("tool_calls") is not None:
            setattr(resp, "tool_calls", payload["tool_calls"])
        return resp

    async def stream_text(self, *args: Any, **kwargs: Any):
        raise NotImplementedError

    async def close(self) -> None:
        return None


def _large_output_tool() -> MagicMock:
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "Returns large output"
    mock_tool._schemas = {"run": MagicMock()}

    async def run_async(operation=None, **kwargs: Any) -> str:
        return "X" * 8_000

    mock_tool.run_async = AsyncMock(side_effect=run_async)
    return mock_tool


@pytest.fixture
async def compression_agent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AIECS_TOOL_OUTPUT_INLINE_CHARS", "256")
    mock_tool = _large_output_tool()
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="Test agent",
            enable_context_compression=True,
            context_window_limit=500_000,
        )
        client = MockLLMClientFunctionCalling(
            responses=[
                {
                    "content": "Calling tool",
                    "tool_calls": [
                        {
                            "id": "call_large",
                            "type": "function",
                            "function": {
                                "name": "mock_tool",
                                "arguments": '{"q":"big"}',
                            },
                        }
                    ],
                },
                {"content": "Done after tool", "tool_calls": None},
            ]
        )
        agent = HybridAgent(
            agent_id="compression_agent",
            name="CompressionTest",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()
        yield agent, client


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_offloads_large_tool_output_before_append(
    compression_agent,
) -> None:
    agent, client = compression_agent
    result = await agent._tool_loop("fetch large data", {})

    assert result["final_response"] == "Done after tool"
    assert client.call_count == 2
    second_call_tool_msgs = [
        msg for msg in client.all_messages[1] if msg.role == "tool"
    ]
    assert len(second_call_tool_msgs) == 1
    assert second_call_tool_msgs[0].content.startswith(TOOL_OUTPUT_TRUNCATED_HEADER)
    assert len(second_call_tool_msgs[0].content or "") < 8_000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_compression_disabled_keeps_full_tool_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIECS_TOOL_OUTPUT_INLINE_CHARS", "256")
    mock_tool = _large_output_tool()
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="Test agent",
            enable_context_compression=False,
        )
        client = MockLLMClientFunctionCalling(
            responses=[
                {
                    "content": "tool",
                    "tool_calls": [
                        {
                            "id": "call_full",
                            "type": "function",
                            "function": {
                                "name": "mock_tool",
                                "arguments": "{}",
                            },
                        }
                    ],
                },
                {"content": "ok", "tool_calls": None},
            ]
        )
        agent = HybridAgent(
            agent_id="no_compression",
            name="NoCompression",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
        )
        await agent.initialize()
        await agent._tool_loop("task", {})

    tool_msg = next(msg for msg in client.all_messages[1] if msg.role == "tool")
    assert tool_msg.content == "X" * 8_000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_compact_reduces_tokens_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _microcompact_only_orchestrator(messages, **kwargs: Any) -> tuple[list, bool]:
        compacted, _ = microcompact_messages(list(messages), keep_recent=1)
        return compacted, True

    monkeypatch.setenv("AIECS_TOOL_OUTPUT_INLINE_CHARS", "100000")

    call_count = {"n": 0}

    async def run_async(operation=None, **kwargs: Any) -> str:
        call_count["n"] += 1
        return f"payload-{call_count['n']}-" + ("Y" * 6_000)

    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "tool"
    mock_tool._schemas = {"run": MagicMock()}
    mock_tool.run_async = AsyncMock(side_effect=run_async)

    tool_responses: List[Dict[str, Any]] = []
    for index in range(3):
        tool_responses.append(
            {
                "content": f"step {index}",
                "tool_calls": [
                    {
                        "id": f"call_{index}",
                        "type": "function",
                        "function": {
                            "name": "mock_tool",
                            "arguments": "{}",
                        },
                    }
                ],
            }
        )
    tool_responses.append({"content": "finished", "tool_calls": None})

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="Test",
            enable_context_compression=True,
            context_window_limit=5_000,
        )
        client = MockLLMClientFunctionCalling(responses=tool_responses)
        agent = HybridAgent(
            agent_id="compact_agent",
            name="Compact",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=6,
        )
        await agent.initialize()

        with patch(
            "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
            new=AsyncMock(side_effect=_microcompact_only_orchestrator),
        ):
            await agent._tool_loop("long loop", {})

    last_pre_llm = client.all_messages[-1]
    tokens_after = estimate_message_tokens(last_pre_llm)
    assert tokens_after < 5_000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_preserves_tool_pairs_after_compact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _microcompact_only_orchestrator(messages, **kwargs: Any) -> tuple[list, bool]:
        return microcompact_messages(list(messages), keep_recent=1)[0], True

    monkeypatch.setenv("AIECS_TOOL_OUTPUT_INLINE_CHARS", "100000")

    mock_tool = _large_output_tool()
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            enable_context_compression=True,
            context_window_limit=4_000,
        )
        client = MockLLMClientFunctionCalling(
            responses=[
                {
                    "content": "t1",
                    "tool_calls": [
                        {
                            "id": "pair_a",
                            "type": "function",
                            "function": {"name": "mock_tool", "arguments": "{}"},
                        }
                    ],
                },
                {
                    "content": "t2",
                    "tool_calls": [
                        {
                            "id": "pair_b",
                            "type": "function",
                            "function": {"name": "mock_tool", "arguments": "{}"},
                        }
                    ],
                },
                {"content": "done", "tool_calls": None},
            ]
        )
        agent = HybridAgent(
            agent_id="pair_agent",
            name="PairAgent",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()

        with patch(
            "aiecs.domain.agent.tool_loop_core.auto_compact_if_needed",
            new=AsyncMock(side_effect=_microcompact_only_orchestrator),
        ):
            await agent._tool_loop("pairs", {})

    final_messages = client.all_messages[-1]
    for index, message in enumerate(final_messages):
        if message.role != "tool" or not message.tool_call_id:
            continue
        assert index > 0
        prior = final_messages[index - 1]
        assert prior.tool_calls
        tool_ids = [
            call.get("id")
            for call in (prior.tool_calls or [])
            if isinstance(call, dict)
        ]
        assert message.tool_call_id in tool_ids


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_wires_artifact_port_from_context(
    compression_agent,
) -> None:
    agent, _client = compression_agent
    port = _RecordingArtifactPort()
    ctx = agent._build_tool_loop_compression_context(
        {
            "session_id": "sess-artifact",
            "tool_artifact_port": port,
        }
    )
    assert ctx.artifact_port is port


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_wires_artifact_port_from_agent_attribute(
    compression_agent,
) -> None:
    agent, _client = compression_agent
    port = _RecordingArtifactPort()
    agent._tool_artifact_port = port
    ctx = agent._build_tool_loop_compression_context({"session_id": "sess-agent-port"})
    assert ctx.artifact_port is port


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_persists_large_tool_output_via_artifact_port(
    compression_agent,
) -> None:
    agent, client = compression_agent
    port = _RecordingArtifactPort()
    result = await agent._tool_loop(
        "fetch large data",
        {
            "session_id": "compression_agent",
            "tool_artifact_port": port,
        },
    )

    assert result["final_response"] == "Done after tool"
    assert len(port.calls) == 1
    session_id, tool_call_id, content = port.calls[0]
    assert session_id == "compression_agent"
    assert tool_call_id == "call_large"
    assert content == "X" * 8_000

    second_call_tool_msgs = [
        msg for msg in client.all_messages[1] if msg.role == "tool"
    ]
    assert len(second_call_tool_msgs) == 1
    tool_content = second_call_tool_msgs[0].content or ""
    assert tool_content.startswith(TOOL_OUTPUT_TRUNCATED_HEADER)
    assert "Full output saved to: artifact://compression_agent/call_large" in tool_content
    assert len(tool_content) < 8_000


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_wires_session_memory_port_on_compression_context(
    compression_agent,
) -> None:
    agent, _client = compression_agent
    ctx = agent._build_tool_loop_compression_context({"session_id": "sess-sm"})
    assert ctx.session_memory is not None
    from aiecs.domain.context.compression.types import InMemorySessionMemoryPort

    assert isinstance(ctx.session_memory, InMemorySessionMemoryPort)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_wires_default_hooks_and_progress(compression_agent) -> None:
    from aiecs.domain.context.compression.hooks import HookExecutor
    from aiecs.domain.context.compression.progress import CompactProgressEmitter

    agent, _client = compression_agent
    ctx = agent._build_tool_loop_compression_context({"session_id": "sess-default-o6"})
    assert isinstance(ctx.hooks, HookExecutor)
    assert isinstance(ctx.progress, CompactProgressEmitter)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_wires_hooks_and_progress_from_context(
    compression_agent,
) -> None:
    from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
    from aiecs.domain.context.compression.progress import CompactProgressEmitter

    agent, _client = compression_agent
    hooks = HookExecutor(HookRegistry())
    progress = CompactProgressEmitter()
    ctx = agent._build_tool_loop_compression_context(
        {
            "session_id": "sess-o6",
            "compression_hook_executor": hooks,
            "compression_progress_emitter": progress,
        }
    )
    assert ctx.hooks is hooks
    assert ctx.progress is progress


@pytest.mark.asyncio
@pytest.mark.unit
async def test_hybrid_agent_builds_progress_from_callback(compression_agent) -> None:
    agent, _client = compression_agent
    seen: list[str] = []

    ctx = agent._build_tool_loop_compression_context(
        {
            "session_id": "sess-o7",
            "on_compact_progress": lambda event: seen.append(event.phase),
        }
    )
    assert ctx.progress is not None
    ctx.progress.emit("microcompact_start")
    assert seen == ["microcompact_start"]

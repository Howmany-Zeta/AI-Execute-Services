"""
Unit tests for HybridAgent _tool_loop (BetaToolRunner-style).

Tests:
- Append-only messages (no rebuild, no iteration labels)
- Completion when response has no tool_calls
- No iteration labels in task or continuation messages
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from aiecs.domain.agent import HybridAgent, AgentConfiguration, AgentInitializationError
from aiecs.llm import BaseLLMClient, LLMResponse, LLMMessage


class MockLLMClientFunctionCalling(BaseLLMClient):
    """Mock LLM client that supports Function Calling for tool loop tests."""

    def __init__(self, responses: List[Dict[str, Any]] = None):
        super().__init__(provider_name="openai")
        self.responses = responses or []
        self.call_count = 0
        self.all_messages: List[List[LLMMessage]] = []

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
        context: Dict = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.all_messages.append([LLMMessage(role=m.role, content=m.content, tool_calls=getattr(m, "tool_calls", None)) for m in messages])

        if self.call_count <= len(self.responses):
            r = self.responses[self.call_count - 1]
        else:
            r = {"content": "Default response", "tool_calls": None}

        resp = LLMResponse(
            content=r.get("content", ""),
            provider="openai",
            model=model or "gpt-4",
            tokens_used=10,
        )
        if r.get("tool_calls") is not None:
            setattr(resp, "tool_calls", r["tool_calls"])
        return resp

    async def stream_text(self, *args, **kwargs):
        raise NotImplementedError

    async def close(self):
        pass


def create_mock_tool():
    mock_tool = MagicMock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool"
    mock_tool._schemas = {"query": MagicMock()}
    async def mock_run_async(operation=None, **kwargs):
        return f"Result for {operation}={kwargs}"
    mock_tool.run_async = AsyncMock(side_effect=mock_run_async)
    return mock_tool


@pytest.fixture
async def tool_loop_agent():
    """Create HybridAgent with Function Calling mock for _tool_loop tests."""
    mock_tool = create_mock_tool()
    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(llm_model="mock-model", system_prompt="You are a test agent.")
        client = MockLLMClientFunctionCalling()
        agent = HybridAgent(
            agent_id="test_tool_loop",
            name="Test",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()
        yield agent, client


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_completion_on_no_tool_calls(tool_loop_agent):
    """When response has no tool_calls, loop completes immediately (no iteration labels)."""
    agent, mock_client = tool_loop_agent
    mock_client.responses = [
        {"content": "I will analyze this.", "tool_calls": None},
    ]

    result = await agent._tool_loop("Analyze the data", {})

    assert result["final_response"] == "I will analyze this."
    assert result["iterations"] == 1
    assert mock_client.call_count == 1
    assert result.get("tool_calls_count", 0) == 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_append_only_messages(tool_loop_agent):
    """Messages are append-only: assistant + tool_result appended, no iteration labels in user messages."""
    agent, mock_client = tool_loop_agent
    mock_client.responses = [
        {"content": "I'll use the tool.", "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
        ]},
        {"content": "Based on the result, here is the answer.", "tool_calls": None},
    ]

    result = await agent._tool_loop("Do something", {})

    assert result["final_response"] == "Based on the result, here is the answer."
    assert result["iterations"] == 2
    assert result["tool_calls_count"] == 1
    assert mock_client.call_count == 2

    # First call: system + task (no [Iteration 1/max])
    msgs1 = mock_client.all_messages[0]
    user_msgs1 = [m for m in msgs1 if m.role == "user"]
    for m in user_msgs1:
        assert "[Iteration" not in (m.content or "")

    # Second call: should have assistant + tool appended (append-only)
    msgs2 = mock_client.all_messages[1]
    roles = [m.role for m in msgs2]
    assert "assistant" in roles
    assert "tool" in roles
    # No iteration labels in continuation
    for m in msgs2:
        if m.content and "[Iteration" in m.content:
            pytest.fail("Iteration labels should not appear in messages")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_no_iteration_labels_in_initial_task(tool_loop_agent):
    """First user message contains only task, no [Iteration 1/max]."""
    agent, mock_client = tool_loop_agent
    mock_client.responses = [{"content": "Done.", "tool_calls": None}]

    await agent._tool_loop("Simple task", {})

    msgs = mock_client.all_messages[0]
    task_msg = next((m for m in msgs if m.role == "user" and "Task:" in (m.content or "")), None)
    assert task_msg is not None
    assert "[Iteration" not in (task_msg.content or "")
    assert "Simple task" in (task_msg.content or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_max_iterations_reached(tool_loop_agent):
    """When max iterations reached without completion, returns success=False."""
    agent, mock_client = tool_loop_agent
    # Always return tool_calls to force continuation
    mock_client.responses = [
        {"content": "Thinking...", "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": "{}"}}
        ]},
    ] * 5  # 5 iterations

    result = await agent._tool_loop("Never ends", {})

    assert result.get("success") is False
    assert result.get("reason") == "max_iterations_reached"
    assert "Max iterations" in result.get("final_response", "")


# =============================================================================
# Task 5.2: Agent fails when Function Calling is not supported
# =============================================================================


class MockLLMClientNoFunctionCalling(BaseLLMClient):
    """Mock LLM client that does NOT support Function Calling."""

    def __init__(self):
        super().__init__(provider_name="legacy_unsupported")

    async def generate_text(self, *args, **kwargs):
        return LLMResponse(content="ok", provider="legacy", model="legacy", tokens_used=1)

    async def stream_text(self, *args, **kwargs):
        async def _gen():
            yield "ok"
        return _gen()

    async def close(self):
        pass


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_fails_when_function_calling_not_supported():
    """Agent with tools must fail at init when LLM does not support Function Calling."""
    config = AgentConfiguration(llm_model="legacy-model")
    client = MockLLMClientNoFunctionCalling()
    mock_tool = create_mock_tool()

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        with pytest.raises(AgentInitializationError) as exc_info:
            agent = HybridAgent(
                agent_id="test_no_fc",
                name="Test",
                llm_client=client,
                tools=["mock_tool"],
                config=config,
            )
            await agent.initialize()

    msg = str(exc_info.value)
    assert "Function Calling" in msg
    assert "does not support tools" in msg or "OpenAI-compatible" in msg


# =============================================================================
# Task 5.4: Streaming path with tool_calls
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_streaming_with_tool_calls(tool_loop_agent):
    """Verify _tool_loop_streaming yields tool_call and tool_result events when model returns tool_calls."""
    from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

    agent, mock_client = tool_loop_agent

    call_count = [0]

    async def mock_stream_first():
        yield StreamChunk(type="token", content="I'll use the tool. ")
        yield StreamChunk(type="tool_calls", tool_calls=[
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
        ])

    async def mock_stream_second():
        yield StreamChunk(type="token", content="Done.")

    def get_stream(**kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_stream_first()
        return mock_stream_second()

    with patch.object(agent.llm_client, "stream_text", new=get_stream):
        events = []
        async for event in agent._tool_loop_streaming("Do something", {}):
            events.append(event)

    tool_call_events = [e for e in events if e.get("type") == "tool_call"]
    tool_result_events = [e for e in events if e.get("type") == "tool_result"]
    token_events = [e for e in events if e.get("type") == "token"]
    result_events = [e for e in events if e.get("type") == "result"]

    assert len(tool_call_events) >= 1
    assert len(tool_result_events) >= 1
    assert len(token_events) >= 1
    assert len(result_events) == 1
    assert result_events[0].get("success") is True


# =============================================================================
# Task 5.5: Assistant message includes both content and tool_calls in history
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_assistant_message_includes_content_and_tool_calls(tool_loop_agent):
    """When model returns both text and tool_calls, assistant message in history SHALL include both."""
    agent, mock_client = tool_loop_agent
    mock_client.responses = [
        {"content": "I'll search for that.", "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
        ]},
        {"content": "Based on the result, here is the answer.", "tool_calls": None},
    ]

    await agent._tool_loop("Search for X", {})

    # Second LLM call receives messages from first iteration
    assert len(mock_client.all_messages) >= 2
    msgs_second_call = mock_client.all_messages[1]

    assistant_msgs = [m for m in msgs_second_call if m.role == "assistant"]
    assert len(assistant_msgs) >= 1

    # First assistant message should have BOTH content and tool_calls
    first_assistant = assistant_msgs[0]
    assert first_assistant.content is not None
    assert "search" in first_assistant.content.lower() or "I'll" in (first_assistant.content or "")
    assert first_assistant.tool_calls is not None
    assert len(first_assistant.tool_calls) >= 1


# =============================================================================
# Task 5.2 (continued)
# =============================================================================


# =============================================================================
# Task 5.6: Regression tests for preserved capabilities
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regression_user_images_in_task_message():
    """Regression: User images from task/context are attached to task message (preserved capability)."""
    config = AgentConfiguration(llm_model="mock-model")
    client = MockLLMClientFunctionCalling(responses=[{"content": "Done", "tool_calls": None}])
    agent = HybridAgent(
        agent_id="test_images",
        name="Test",
        llm_client=client,
        tools=[],
        config=config,
    )
    await agent.initialize()

    context = {"images": ["https://example.com/img.jpg"]}
    messages = agent._build_initial_messages("Describe image", context)
    task_msg = next((m for m in messages if m.role == "user" and "Task:" in (m.content or "")), None)
    assert task_msg is not None
    assert task_msg.images == ["https://example.com/img.jpg"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_regression_system_prompt_cache_control():
    """Regression: System prompt cache_control is set when enable_prompt_caching (preserved capability)."""
    config = AgentConfiguration(
        llm_model="mock-model",
        system_prompt="Test",
        enable_prompt_caching=True,
    )
    agent = HybridAgent(
        agent_id="test_cache",
        name="Test",
        llm_client=MockLLMClientFunctionCalling(responses=[{"content": "Ok", "tool_calls": None}]),
        tools=[],
        config=config,
    )
    await agent.initialize()

    messages = agent._build_initial_messages("Hi", {})
    system_msg = next((m for m in messages if m.role == "system"), None)
    assert system_msg is not None
    assert system_msg.cache_control is not None
    assert system_msg.cache_control.type == "ephemeral"


# =============================================================================
# Task 5.2 (continued)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_without_tools_initializes_without_function_calling():
    """Agent with tools=[] does not require Function Calling and initializes successfully."""
    config = AgentConfiguration(llm_model="legacy-model")
    client = MockLLMClientNoFunctionCalling()

    agent = HybridAgent(
        agent_id="test_no_tools",
        name="Test",
        llm_client=client,
        tools=[],
        config=config,
    )
    await agent.initialize()

    assert agent._use_function_calling is False


# =============================================================================
# Tool result stop conditions
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_stops_when_tool_result_matches_condition():
    """When tool result matches tool_result_stop_conditions, loop ends early without further LLM calls."""
    mock_tool = create_mock_tool()
    mock_tool.run_async = AsyncMock(return_value="<html><body>Done</body></html>")

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="You are a test agent.",
            tool_result_stop_conditions=["</html>"],
        )
        client = MockLLMClientFunctionCalling(responses=[
            {"content": "I'll fetch the page.", "tool_calls": [
                {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
            ]},
        ])
        agent = HybridAgent(
            agent_id="test_stop",
            name="Test",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()

    result = await agent._tool_loop("Fetch the page", {})

    assert result["final_response"] == "<html><body>Done</body></html>"
    assert result["stop_reason"] == "tool_result_matched"
    assert result["iterations"] == 1
    assert result["tool_calls_count"] == 1
    assert client.call_count == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_loop_streaming_stops_when_tool_result_matches_condition():
    """Streaming: when tool result matches stop condition, yields result and returns early."""
    from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

    mock_tool = create_mock_tool()
    mock_tool.run_async = AsyncMock(return_value="<html><body>Done</body></html>")

    with patch("aiecs.tools.get_tool", return_value=mock_tool):
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="You are a test agent.",
            tool_result_stop_conditions=["</html>"],
        )
        client = MockLLMClientFunctionCalling()
        agent = HybridAgent(
            agent_id="test_stop_stream",
            name="Test",
            llm_client=client,
            tools=["mock_tool"],
            config=config,
            max_iterations=5,
        )
        await agent.initialize()

    async def mock_stream():
        yield StreamChunk(type="token", content="Fetching. ")
        yield StreamChunk(type="tool_calls", tool_calls=[
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
        ])

    def get_stream(**kwargs):
        return mock_stream()

    with patch.object(agent.llm_client, "stream_text", new=get_stream):
        events = []
        async for event in agent._tool_loop_streaming("Fetch the page", {}):
            events.append(event)

    result_events = [e for e in events if e.get("type") == "result"]
    assert len(result_events) == 1
    assert result_events[0]["output"] == "<html><body>Done</body></html>"
    assert result_events[0]["stop_reason"] == "tool_result_matched"
    assert result_events[0]["success"] is True

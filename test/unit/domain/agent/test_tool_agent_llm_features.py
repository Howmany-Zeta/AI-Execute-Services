"""
Unit Tests for ToolAgent LLM + Function Calling Features

Tests the new LLM-powered tool selection and execution functionality.
"""

import json
import pytest
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

from aiecs.domain.agent import ToolAgent, AgentConfiguration
from aiecs.tools import BaseTool
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


# ==================== Mock Tools ====================


class MockCalculatorTool(BaseTool):
    """Mock calculator tool for testing."""

    def __init__(self):
        super().__init__()
        self.call_count = 0

    async def run_async(self, op: str = None, **kwargs) -> Any:
        """Execute calculator operation.

        Supports:
        - run_async(op="add", a=5, b=3)
        - run_async(a=5, b=3) for default add
        """
        self.call_count += 1

        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)

        if op == "multiply":
            return a * b
        else:
            # Default to add
            return a + b

    async def add(self, a: float, b: float) -> float:
        """Add two numbers."""
        return await self.run_async("add", a=a, b=b)

    async def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers."""
        return await self.run_async("multiply", a=a, b=b)


class MockSearchTool(BaseTool):
    """Mock search tool for testing."""

    def __init__(self):
        super().__init__()
        self.queries: List[str] = []

    async def run_async(self, op: str = None, **kwargs) -> Dict[str, Any]:
        """Execute search operation."""
        query = kwargs.get("query", "")
        self.queries.append(query)
        return {"query": query, "results": [f"Result for: {query}"]}

    async def search(self, query: str) -> Dict[str, Any]:
        """Search for information."""
        return await self.run_async("search", query=query)


# ==================== Mock LLM Client ====================


class MockLLMClientForToolAgent(BaseLLMClient):
    """Mock LLM client that simulates Function Calling responses."""

    def __init__(self, tool_calls: Optional[List[Dict]] = None):
        super().__init__(provider_name="mock")
        self.tool_calls_to_return = tool_calls or []
        self.call_count = 0
        self.last_messages: List[LLMMessage] = []
        self.last_tools: List[Dict] = []

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate mock response with optional tool calls."""
        self.call_count += 1
        self.last_messages = messages
        self.last_tools = tools or []

        response = LLMResponse(
            content="I'll help you with that.",
            provider="mock",
            model=model or "mock-model",
            tokens_used=50,
        )

        # Add tool_calls if configured
        if self.tool_calls_to_return:
            response.tool_calls = self.tool_calls_to_return

        return response

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
        return_chunks: bool = False,
        **kwargs,
    ) -> AsyncIterator:
        """Stream mock response with tool calls."""
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        self.call_count += 1
        self.last_messages = messages
        self.last_tools = tools or []

        # Yield content tokens
        for token in ["I'll ", "help ", "you."]:
            if return_chunks:
                yield StreamChunk(type="token", content=token)
            else:
                yield token

        # Yield tool calls if configured
        if self.tool_calls_to_return and return_chunks:
            yield StreamChunk(type="tool_calls", tool_calls=self.tool_calls_to_return)

    async def close(self):
        """Close the client."""
        pass


# ==================== Fixtures ====================


@pytest.fixture
def calculator_tool():
    """Create mock calculator tool."""
    return MockCalculatorTool()


@pytest.fixture
def search_tool():
    """Create mock search tool."""
    return MockSearchTool()


@pytest.fixture
def agent_config():
    """Create agent configuration."""
    return AgentConfiguration(
        goal="Test tool agent with LLM",
        llm_model="mock-model",
        temperature=0.7,
        max_tokens=1000,
    )


# ==================== Helpers ====================


def create_tool_call(name: str, arguments: Dict[str, Any], call_id: str = "call_0") -> Dict:
    """Helper to create a tool call dict."""
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments),
        },
    }


# ==================== Tests: Basic LLM Mode ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_with_llm_client(calculator_tool, search_tool, agent_config):
    """Test ToolAgent initialization with LLM client."""
    mock_client = MockLLMClientForToolAgent()

    agent = ToolAgent(
        agent_id="test_llm_agent",
        name="Test LLM Tool Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool, "search": search_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Verify agent is active
    assert agent.state.name == "ACTIVE"

    # Verify LLM client is set
    assert agent.llm_client is not None
    assert agent.llm_client.provider_name == "mock"

    # Verify tools are loaded
    available_tools = agent.get_available_tools()
    assert "calculator" in available_tools
    assert "search" in available_tools

    # Verify tool schemas are generated
    assert len(agent._tool_schemas) > 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_llm_mode_with_tool_call(calculator_tool, agent_config):
    """Test ToolAgent executes task via LLM Function Calling."""
    # Configure mock to return a tool call
    tool_call = create_tool_call("calculator", {"a": 5, "b": 3})
    mock_client = MockLLMClientForToolAgent(tool_calls=[tool_call])

    agent = ToolAgent(
        agent_id="test_llm_tool_call",
        name="Test LLM Tool Call Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Execute task with description (triggers LLM mode)
    result = await agent.execute_task(
        {"description": "Add 5 and 3"},
        {}
    )

    # Verify success
    assert result["success"] is True
    assert result["tool_calls_count"] == 1
    assert len(result["tool_results"]) == 1

    # Verify tool was called
    assert calculator_tool.call_count == 1

    # Verify LLM was called with tools
    assert mock_client.call_count == 1
    assert len(mock_client.last_tools) > 0


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_direct_mode_without_llm(calculator_tool, agent_config):
    """Test ToolAgent direct mode without LLM client."""
    agent = ToolAgent(
        agent_id="test_direct",
        name="Test Direct Agent",
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Execute task with explicit tool (direct mode)
    result = await agent.execute_task(
        {"tool": "calculator", "operation": "add", "parameters": {"a": 10, "b": 20}},
        {}
    )

    assert result["success"] is True
    assert result["output"] == 30
    assert result["tool_used"] == "calculator"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_direct_mode_with_llm_but_explicit_tool(calculator_tool, agent_config):
    """Test ToolAgent uses direct mode when explicit tool is specified, even with LLM."""
    mock_client = MockLLMClientForToolAgent()

    agent = ToolAgent(
        agent_id="test_explicit",
        name="Test Explicit Tool Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Execute with explicit tool - should bypass LLM
    result = await agent.execute_task(
        {"tool": "calculator", "operation": "multiply", "parameters": {"a": 4, "b": 5}},
        {}
    )

    assert result["success"] is True
    assert result["output"] == 20
    # LLM should NOT be called
    assert mock_client.call_count == 0


# ==================== Tests: Streaming ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_streaming_with_tool_calls(calculator_tool, agent_config):
    """Test ToolAgent streaming execution with tool calls."""
    tool_call = create_tool_call("calculator", {"a": 7, "b": 8})
    mock_client = MockLLMClientForToolAgent(tool_calls=[tool_call])

    agent = ToolAgent(
        agent_id="test_stream",
        name="Test Streaming Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Collect streaming events
    events = []
    async for event in agent.execute_task_streaming(
        {"description": "Add 7 and 8"},
        {}
    ):
        events.append(event)

    # Verify events
    event_types = [e["type"] for e in events]
    assert "status" in event_types
    assert "token" in event_types
    assert "tool_calls" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "result" in event_types

    # Verify final result
    result_event = next(e for e in events if e["type"] == "result")
    assert result_event["success"] is True
    assert result_event["tool_calls_count"] == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_streaming_direct_mode(calculator_tool, agent_config):
    """Test ToolAgent streaming in direct mode (no LLM)."""
    agent = ToolAgent(
        agent_id="test_stream_direct",
        name="Test Stream Direct Agent",
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Collect events
    events = []
    async for event in agent.execute_task_streaming(
        {"tool": "calculator", "operation": "add", "parameters": {"a": 1, "b": 2}},
        {}
    ):
        events.append(event)

    # Should have result event
    assert len(events) == 1
    assert events[0]["type"] == "result"
    assert events[0]["output"] == 3


# ==================== Tests: process_message ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_process_message_with_llm(calculator_tool, agent_config):
    """Test ToolAgent process_message with LLM client."""
    tool_call = create_tool_call("calculator", {"a": 2, "b": 3})
    mock_client = MockLLMClientForToolAgent(tool_calls=[tool_call])

    agent = ToolAgent(
        agent_id="test_msg",
        name="Test Message Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    response = await agent.process_message("Add 2 and 3")

    assert "response" in response
    assert "tool_results" in response
    assert len(response["tool_results"]) == 1


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_process_message_without_llm(calculator_tool, agent_config):
    """Test ToolAgent process_message without LLM returns tool info."""
    agent = ToolAgent(
        agent_id="test_msg_no_llm",
        name="Test Message No LLM Agent",
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    response = await agent.process_message("Add 2 and 3")

    assert "available_tools" in response
    assert "calculator" in response["available_tools"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_process_message_streaming(calculator_tool, agent_config):
    """Test ToolAgent process_message_streaming."""
    tool_call = create_tool_call("calculator", {"a": 9, "b": 1})
    mock_client = MockLLMClientForToolAgent(tool_calls=[tool_call])

    agent = ToolAgent(
        agent_id="test_msg_stream",
        name="Test Message Streaming Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    tokens = []
    async for token in agent.process_message_streaming("Add 9 and 1"):
        tokens.append(token)

    # Should have received tokens
    assert len(tokens) > 0


# ==================== Tests: Helper Methods ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_extract_task_description(agent_config):
    """Test _extract_task_description with various formats."""
    agent = ToolAgent(
        agent_id="test_extract",
        name="Test Extract Agent",
        tools=["search"],
        config=agent_config,
    )

    await agent.initialize()

    # Test various field names
    assert agent._extract_task_description({"description": "desc"}) == "desc"
    assert agent._extract_task_description({"prompt": "prompt"}) == "prompt"
    assert agent._extract_task_description({"task": "task"}) == "task"
    assert agent._extract_task_description({"query": "query"}) == "query"
    assert agent._extract_task_description({"message": "msg"}) == "msg"

    # Test missing description
    with pytest.raises(ValueError):
        agent._extract_task_description({})


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_parse_function_name(calculator_tool, agent_config):
    """Test _parse_function_name method."""
    agent = ToolAgent(
        agent_id="test_parse",
        name="Test Parse Agent",
        tools={"calculator": calculator_tool},
        config=agent_config,
    )

    await agent.initialize()

    # Test exact match
    tool_name, operation = agent._parse_function_name("calculator")
    assert tool_name == "calculator"
    assert operation is None

    # Test with underscore
    tool_name, operation = agent._parse_function_name("calculator_add")
    assert tool_name == "calculator"
    assert operation == "add"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_validate_llm_client(agent_config):
    """Test _validate_llm_client method."""
    from aiecs.domain.agent.exceptions import AgentInitializationError

    class InvalidLLMClient:
        """Client without generate_text method."""
        provider_name = "invalid"

    agent = ToolAgent(
        agent_id="test_validate",
        name="Test Validate Agent",
        llm_client=InvalidLLMClient(),  # type: ignore
        tools=["search"],
        config=agent_config,
    )

    # Raises AgentInitializationError which wraps the ValueError
    with pytest.raises(AgentInitializationError, match="generate_text"):
        await agent.initialize()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_agent_multiple_tool_calls(calculator_tool, search_tool, agent_config):
    """Test ToolAgent handles multiple tool calls in one response."""
    tool_calls = [
        create_tool_call("calculator", {"a": 1, "b": 2}, "call_1"),
        create_tool_call("search", {"query": "test"}, "call_2"),
    ]
    mock_client = MockLLMClientForToolAgent(tool_calls=tool_calls)

    agent = ToolAgent(
        agent_id="test_multi",
        name="Test Multi Tool Agent",
        llm_client=mock_client,
        tools={"calculator": calculator_tool, "search": search_tool},
        config=agent_config,
    )

    await agent.initialize()

    result = await agent.execute_task({"description": "Add and search"}, {})

    assert result["success"] is True
    assert result["tool_calls_count"] == 2
    assert len(result["tool_results"]) == 2
    assert calculator_tool.call_count == 1
    assert len(search_tool.queries) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

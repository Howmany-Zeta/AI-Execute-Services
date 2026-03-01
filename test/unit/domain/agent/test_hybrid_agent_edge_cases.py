"""
Edge Case Tests for HybridAgent (Function Calling mode)

Tests various edge cases for the BetaToolRunner-style tool loop.
ReAct text format is no longer supported.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMResponse, LLMMessage


class MockLLMClientFunctionCalling(BaseLLMClient):
    """Mock LLM client for Function Calling edge case tests."""

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
    mock_tool.description = "A mock tool for testing"
    mock_tool._schemas = {"query": MagicMock()}

    async def mock_run_async(operation=None, **kwargs):
        return f"Mock result for operation={operation}, params={kwargs}"

    mock_tool.run_async = AsyncMock(side_effect=mock_run_async)
    return mock_tool


@pytest.fixture
async def create_agent():
    """Factory fixture to create HybridAgent with Function Calling mock."""
    agents = []
    patchers = []

    async def _create_agent(responses: List[Dict[str, Any]], max_iterations: int = 5, with_tools: bool = True):
        mock_client = MockLLMClientFunctionCalling(responses=responses)
        config = AgentConfiguration(
            llm_model="mock-model",
            system_prompt="You are a test agent.",
        )

        tools = ["mock_tool"] if with_tools else []
        mock_tool = create_mock_tool()
        patcher = patch("aiecs.tools.get_tool", return_value=mock_tool)
        patcher.start()
        patchers.append(patcher)

        agent = HybridAgent(
            agent_id=f"test_edge_case_{len(agents)}",
            name="Test Edge Case Agent",
            llm_client=mock_client,
            tools=tools,
            config=config,
            max_iterations=max_iterations,
        )

        await agent.initialize()
        agents.append(agent)
        return agent, mock_client

    yield _create_agent

    for patcher in patchers:
        patcher.stop()
    for agent in agents:
        try:
            await agent.shutdown()
        except Exception:
            pass


# =============================================================================
# Function Calling: Tool call then final response
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_tool_call_then_final_response(create_agent):
    """Test: First response has tool_calls, second has final text. Both executed correctly."""
    responses = [
        {"content": "I'll use the tool.", "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"q": "test"}'}}
        ]},
        {"content": "Task completed successfully.", "tool_calls": None},
    ]

    agent, mock_client = await create_agent(responses)

    result = await agent.execute_task({"description": "Test task"}, {})

    assert result["success"] is True
    assert result["tool_calls_count"] >= 1
    assert mock_client.call_count >= 2
    assert "Task completed successfully" in result["output"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_immediate_final_response_no_tool_calls(create_agent):
    """Test: Response with no tool_calls completes immediately (no continuation)."""
    responses = [
        {"content": "I can answer directly: The answer is 42.", "tool_calls": None},
    ]

    agent, mock_client = await create_agent(responses)

    result = await agent.execute_task({"description": "What is 6*7?"}, {})

    assert result["success"] is True
    assert mock_client.call_count == 1
    assert result["iterations"] == 1
    assert "42" in result["output"]


# =============================================================================
# Max iterations
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_max_iterations_reached(create_agent):
    """Test: LLM keeps returning tool_calls, max iterations reached."""
    tool_call = {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": "{}"}}
    responses = [
        {"content": "Thinking...", "tool_calls": [tool_call]},
    ] * 5

    agent, mock_client = await create_agent(responses, max_iterations=3)

    result = await agent.execute_task({"description": "Never-ending task"}, {})

    assert result["success"] is False
    assert "Max iterations" in result["output"]
    assert result.get("reason") == "max_iterations_reached"


# =============================================================================
# Content preservation
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_unicode_content_preserved(create_agent):
    """Test: Unicode content in response is preserved."""
    responses = [
        {"content": "完成 🎉", "tool_calls": None},
    ]

    agent, mock_client = await create_agent(responses)

    result = await agent.execute_task({"description": "Unicode test"}, {})

    assert result["success"] is True
    assert "完成" in result["output"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_multiple_tool_calls_sequence(create_agent):
    """Test: Multiple tool calls across iterations."""
    responses = [
        {"content": "First tool.", "tool_calls": [
            {"id": "call_0", "type": "function", "function": {"name": "mock_tool", "arguments": '{"step": 1}'}}
        ]},
        {"content": "Second tool.", "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "mock_tool", "arguments": '{"step": 2}'}}
        ]},
        {"content": "Both tools executed.", "tool_calls": None},
    ]

    agent, mock_client = await create_agent(responses)

    result = await agent.execute_task({"description": "Multiple tools"}, {})

    assert result["success"] is True
    assert result["tool_calls_count"] >= 2


# =============================================================================
# Text-only mode (no tools)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_without_tools_completes_text_only(create_agent):
    """Test: Agent with tools=[] runs in text-only mode, completes on first response."""
    responses = [
        {"content": "Here is my answer.", "tool_calls": None},
    ]

    agent, mock_client = await create_agent(responses, with_tools=False)

    result = await agent.execute_task({"description": "Simple question"}, {})

    assert result["success"] is True
    assert mock_client.call_count == 1
    assert "Here is my answer" in result["output"]

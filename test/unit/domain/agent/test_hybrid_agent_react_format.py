"""
Tests for HybridAgent (Function Calling mode)

Tests message building, history, context, and images.
ReAct format (TOOL:/OPERATION:/PARAMETERS:, FINAL RESPONSE:) is no longer supported.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMResponse, LLMMessage


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self, responses: List[str] = None):
        super().__init__(provider_name="mock")
        self.responses = responses or []
        self.call_count = 0
        self.last_messages = None

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        tools: List[Dict] = None,
        tool_choice: str = None,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_messages = messages
        content = self.responses[self.call_count - 1] if self.call_count <= len(self.responses) else "Mock response"
        return LLMResponse(
            content=content,
            provider="mock",
            model=model or "mock-model",
            tokens_used=10,
        )

    async def stream_text(self, messages, model=None, temperature=None, max_tokens=None, tools=None, tool_choice=None, return_chunks=False):
        content = self.responses[0] if self.responses else "Mock streaming response"
        for token in content.split():
            yield token

    async def close(self):
        pass


@pytest.mark.asyncio
@pytest.mark.unit
async def test_system_prompt_includes_tool_instructions():
    """Test that system prompt includes tool-related instructions (Function Calling, no ReAct)."""
    config = AgentConfiguration(
        llm_model="mock-model",
        system_prompt="You are a data analyst.",
    )

    agent = HybridAgent(
        agent_id="test_system_prompt",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=["search"],
        config=config,
    )

    await agent.initialize()

    system_prompt = agent._system_prompt
    assert "You are a data analyst." in system_prompt
    assert "search" in system_prompt
    # ReAct tags no longer present
    assert "<THOUGHT>" not in system_prompt
    assert "<OBSERVATION>" not in system_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_single_system_message():
    """Test that only one system message is created (system prompt + context merged)."""
    config = AgentConfiguration(
        llm_model="mock-model",
        system_prompt="You are a helpful assistant.",
    )

    agent = HybridAgent(
        agent_id="test_single_system",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {"user_id": "user123", "session_id": "session456"}
    messages = agent._build_initial_messages("Test task", context)

    system_messages = [msg for msg in messages if msg.role == "system"]
    assert len(system_messages) >= 1
    assert "You are a helpful assistant." in system_messages[0].content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_messages_via_context():
    """Test that history messages passed via context are added as separate messages."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_history_context",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "history": [
            {"role": "user", "content": "What's the weather?"},
            {"role": "assistant", "content": "It's sunny today."},
            {"role": "user", "content": "What about tomorrow?"}
        ],
        "user_id": "user123"
    }

    messages = agent._build_initial_messages("Tell me the weather", context)

    user_messages = [msg for msg in messages if msg.role == "user"]
    assistant_messages = [msg for msg in messages if msg.role == "assistant"]

    assert len(user_messages) >= 2
    assert len(assistant_messages) >= 1

    history_contents = [msg.content for msg in messages]
    assert "What's the weather?" in history_contents
    assert "It's sunny today." in history_contents
    assert "What about tomorrow?" in history_contents

    user_contents = [msg.content for msg in messages if msg.role == "user"]
    assert any("Tell me the weather" in (c or "") for c in user_contents)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_with_llmmessage_instances():
    """Test that history can contain LLMMessage instances."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_history_llmmessage",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "history": [
            LLMMessage(role="user", content="Hello"),
            LLMMessage(role="assistant", content="Hi there!"),
        ]
    }

    messages = agent._build_initial_messages("Continue conversation", context)

    assert len(messages) >= 3
    assert any(msg.content == "Hello" for msg in messages)
    assert any(msg.content == "Hi there!" for msg in messages)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_function_calling_support_check():
    """Test that Function Calling support check exists and tool schemas are generated."""
    config = AgentConfiguration(llm_model="mock-model")

    mock_client = MockLLMClient()
    mock_client.provider_name = "openai"

    agent = HybridAgent(
        agent_id="test_function_calling",
        name="Test Agent",
        llm_client=mock_client,
        tools=["search"],
        config=config,
    )

    await agent.initialize()

    assert hasattr(agent, "_use_function_calling")
    assert hasattr(agent, "_check_function_calling_support")
    assert hasattr(agent, "_tool_schemas")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_context_without_history():
    """Test that context without history still works correctly."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_context_no_history",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "user_id": "user123",
        "session_id": "session456",
        "metadata": {"source": "web"}
    }

    messages = agent._build_initial_messages("Test task", context)

    user_messages = [msg for msg in messages if msg.role == "user"]
    context_message = [msg for msg in user_messages if msg.content and "Additional Context" in msg.content]

    assert len(context_message) > 0
    assert "user_id: user123" in context_message[0].content
    assert "session_id: session456" in context_message[0].content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_empty_context():
    """Test that empty context doesn't cause errors."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_empty_context",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    messages = agent._build_initial_messages("Test task", {})

    assert len(messages) >= 2
    assert any(msg.role == "system" for msg in messages)
    assert any(msg.role == "user" and "Test task" in (msg.content or "") for msg in messages)


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_in_context():
    """Test that images from context are added to task message."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_images_context",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "images": ["https://example.com/image.jpg"],
        "user_id": "user123"
    }

    messages = agent._build_initial_messages("Describe this image", context)

    task_messages = [msg for msg in messages if msg.role == "user" and "Task:" in (msg.content or "")]
    assert len(task_messages) == 1

    task_msg = task_messages[0]
    assert task_msg.images == ["https://example.com/image.jpg"]
    assert "Describe this image" in (task_msg.content or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_in_history():
    """Test that images from history messages are preserved."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_images_history",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "history": [
            {
                "role": "user",
                "content": "What's in this image?",
                "images": ["https://example.com/image1.jpg"]
            },
            {
                "role": "assistant",
                "content": "It's a cat."
            }
        ]
    }

    messages = agent._build_initial_messages("Tell me more", context)

    history_with_images = [
        msg for msg in messages
        if msg.role == "user" and msg.images
    ]
    assert len(history_with_images) == 1
    assert history_with_images[0].images == ["https://example.com/image1.jpg"]
    assert "What's in this image?" in (history_with_images[0].content or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_in_task_dict():
    """Test that images from task dict are passed through to messages."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_images_task",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    task = {
        "description": "Analyze this image",
        "images": ["https://example.com/task-image.jpg"]
    }

    context = {}
    context["images"] = task["images"]
    messages = agent._build_initial_messages(task["description"], context)

    task_messages = [msg for msg in messages if msg.role == "user" and "Task:" in (msg.content or "")]
    assert len(task_messages) == 1

    task_msg = task_messages[0]
    assert task_msg.images == ["https://example.com/task-image.jpg"]
    assert "Analyze this image" in (task_msg.content or "")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_multiple_images():
    """Test that multiple images are handled correctly."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_multiple_images",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "images": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "/path/to/local/image.png"
        ]
    }

    messages = agent._build_initial_messages("Compare these images", context)

    task_messages = [msg for msg in messages if msg.role == "user" and "Task:" in (msg.content or "")]
    assert len(task_messages) == 1

    task_msg = task_messages[0]
    assert len(task_msg.images) == 3
    assert "https://example.com/image1.jpg" in task_msg.images
    assert "https://example.com/image2.jpg" in task_msg.images
    assert "/path/to/local/image.png" in task_msg.images



@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_assistant_message_with_tool_calls_no_content():
    """Test that assistant history messages carrying tool_calls (content=None) are injected correctly."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_history_tool_calls",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    tool_calls = [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {"name": "get_weather", "arguments": '{"city": "Beijing"}'},
        }
    ]

    context = {
        "history": [
            {"role": "user", "content": "What's the weather in Beijing?"},
            # assistant message: content is None, only tool_calls
            {"role": "assistant", "content": None, "tool_calls": tool_calls},
        ]
    }

    messages = agent._build_initial_messages("Follow up question", context)

    assistant_msgs = [msg for msg in messages if msg.role == "assistant"]
    assert len(assistant_msgs) >= 1

    tool_call_msg = next(
        (msg for msg in assistant_msgs if msg.tool_calls is not None), None
    )
    assert tool_call_msg is not None, "Expected an assistant message with tool_calls"
    assert tool_call_msg.content is None
    assert tool_call_msg.tool_calls == tool_calls


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_tool_result_message_with_tool_call_id():
    """Test that tool-result history messages carrying tool_call_id are injected correctly."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_history_tool_call_id",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    context = {
        "history": [
            {"role": "user", "content": "What's the weather in Beijing?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city": "Beijing"}',
                        },
                    }
                ],
            },
            # tool result message
            {
                "role": "tool",
                "content": "Sunny, 28°C",
                "tool_call_id": "call_abc123",
            },
        ]
    }

    messages = agent._build_initial_messages("Tell me more", context)

    tool_result_msgs = [msg for msg in messages if msg.role == "tool"]
    assert len(tool_result_msgs) >= 1

    tool_result = tool_result_msgs[0]
    assert tool_result.content == "Sunny, 28°C"
    assert tool_result.tool_call_id == "call_abc123"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_history_mixed_full_tool_use_sequence():
    """Test a complete tool-use history sequence: user → assistant(tool_calls) → tool → assistant(text).

    Verifies that all fields (tool_calls, tool_call_id, images, content) are preserved
    faithfully on the resulting LLMMessage instances.
    """
    config = AgentConfiguration(llm_model="mock-model")

    agent = HybridAgent(
        agent_id="test_history_mixed_full",
        name="Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )

    await agent.initialize()

    tool_calls = [
        {
            "id": "call_xyz789",
            "type": "function",
            "function": {
                "name": "search_image",
                "arguments": '{"query": "cat"}',
            },
        }
    ]

    context = {
        "history": [
            # user message with an image attachment
            {
                "role": "user",
                "content": "Find me a cat picture.",
                "images": ["https://example.com/query.jpg"],
            },
            # assistant decides to call a tool (content is None)
            {
                "role": "assistant",
                "content": None,
                "tool_calls": tool_calls,
            },
            # tool returns the result
            {
                "role": "tool",
                "content": '{"url": "https://example.com/cat.jpg"}',
                "tool_call_id": "call_xyz789",
            },
            # assistant final text reply
            {
                "role": "assistant",
                "content": "Here is a cat picture for you.",
            },
        ]
    }

    messages = agent._build_initial_messages("Now find a dog picture.", context)

    # --- user message with image ---
    user_with_image = next(
        (
            msg
            for msg in messages
            if msg.role == "user" and msg.content == "Find me a cat picture."
        ),
        None,
    )
    assert user_with_image is not None
    assert "https://example.com/query.jpg" in user_with_image.images

    # --- assistant message with tool_calls ---
    assistant_tool_call_msg = next(
        (msg for msg in messages if msg.role == "assistant" and msg.tool_calls is not None),
        None,
    )
    assert assistant_tool_call_msg is not None
    assert assistant_tool_call_msg.content is None
    assert assistant_tool_call_msg.tool_calls == tool_calls

    # --- tool result message ---
    tool_result_msg = next(
        (msg for msg in messages if msg.role == "tool"),
        None,
    )
    assert tool_result_msg is not None
    assert tool_result_msg.tool_call_id == "call_xyz789"
    assert "cat.jpg" in (tool_result_msg.content or "")

    # --- final assistant text reply ---
    final_assistant_msg = next(
        (
            msg
            for msg in messages
            if msg.role == "assistant" and msg.content == "Here is a cat picture for you."
        ),
        None,
    )
    assert final_assistant_msg is not None
    assert final_assistant_msg.tool_calls is None

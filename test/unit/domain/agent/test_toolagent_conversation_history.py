"""
Test ToolAgent conversation history and image handling.

Tests that ToolAgent properly handles conversation history via context['history']
and images via context['images'], matching HybridAgent's implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from aiecs.domain.agent import ToolAgent, AgentConfiguration
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
from aiecs.tools import BaseTool


class MockTool(BaseTool):
    """Mock tool for testing."""
    
    def __init__(self):
        self.call_count = 0
    
    async def run_async(self, operation: str, **kwargs):
        self.call_count += 1
        return f"Mock result for {operation}"


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.provider_name = "mock"
    client.supports_function_calling = MagicMock(return_value=True)

    # Mock generate_text response
    response = LLMResponse(
        content="I'll help you with that.",
        model="mock-model",
        provider="mock",
        prompt_tokens=10,
        completion_tokens=5,
        tokens_used=15
    )
    client.generate_text = AsyncMock(return_value=response)
    client.close = AsyncMock()  # Mock async close method

    return client


@pytest.fixture
async def tool_agent(mock_llm_client):
    """Create a ToolAgent for testing."""
    config = AgentConfiguration(
        goal="Test agent",
        llm_model="mock-model",
        temperature=0.7
    )
    
    agent = ToolAgent(
        agent_id="test-agent",
        name="Test Agent",
        llm_client=mock_llm_client,
        tools={"mock_tool": MockTool()},
        config=config
    )
    
    await agent.initialize()
    yield agent
    await agent.shutdown()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_conversation_history_with_dict_format(tool_agent, mock_llm_client):
    """Test that conversation history is properly added to messages (dict format)."""
    
    # Execute task with conversation history
    result = await tool_agent.execute_task(
        {"description": "What did I say before?"},
        {
            "history": [
                {"role": "user", "content": "My name is Alice"},
                {"role": "assistant", "content": "Nice to meet you, Alice!"},
                {"role": "user", "content": "What's my name?"},
                {"role": "assistant", "content": "Your name is Alice."}
            ]
        }
    )
    
    # Verify LLM was called
    assert mock_llm_client.generate_text.called
    
    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    
    # Verify conversation history was included
    # Should have: system prompt + 4 history messages + user message
    assert len(messages) >= 5
    
    # Check history messages are present
    history_messages = [msg for msg in messages if msg.role in ("user", "assistant")]
    assert len(history_messages) >= 5  # 4 from history + 1 current
    
    print("\n✓ Conversation history (dict format) properly added to messages")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_conversation_history_with_llmmessage_format(tool_agent, mock_llm_client):
    """Test that conversation history works with LLMMessage instances."""
    
    # Execute task with LLMMessage instances
    result = await tool_agent.execute_task(
        {"description": "Continue the conversation"},
        {
            "history": [
                LLMMessage(role="user", content="Hello"),
                LLMMessage(role="assistant", content="Hi there!"),
            ]
        }
    )
    
    # Verify LLM was called
    assert mock_llm_client.generate_text.called
    
    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    
    # Verify history messages are included
    history_messages = [msg for msg in messages if msg.role in ("user", "assistant")]
    assert len(history_messages) >= 3  # 2 from history + 1 current
    
    print("\n✓ Conversation history (LLMMessage format) properly added to messages")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_in_conversation_history(tool_agent, mock_llm_client):
    """Test that images in conversation history are properly handled."""
    
    # Execute task with images in history
    result = await tool_agent.execute_task(
        {"description": "What's in the image I sent?"},
        {
            "history": [
                {
                    "role": "user",
                    "content": "Look at this image",
                    "images": ["https://example.com/image1.jpg"]
                },
                {
                    "role": "assistant",
                    "content": "I see a cat in the image."
                }
            ]
        }
    )
    
    # Verify LLM was called
    assert mock_llm_client.generate_text.called
    
    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]
    
    # Find the message with images
    messages_with_images = [msg for msg in messages if msg.images]
    assert len(messages_with_images) >= 1
    assert "https://example.com/image1.jpg" in messages_with_images[0].images
    
    print("\n✓ Images in conversation history properly handled")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_from_context(tool_agent, mock_llm_client):
    """Test that images from context are attached to user message."""

    # Execute task with images in context
    result = await tool_agent.execute_task(
        {"description": "Analyze this image"},
        {
            "images": ["https://example.com/image2.jpg"]
        }
    )

    # Verify LLM was called
    assert mock_llm_client.generate_text.called

    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]

    # Find the user message (should be last)
    user_messages = [msg for msg in messages if msg.role == "user"]
    assert len(user_messages) >= 1

    # Check that the last user message has images
    last_user_message = user_messages[-1]
    assert last_user_message.images
    assert "https://example.com/image2.jpg" in last_user_message.images

    print("\n✓ Images from context properly attached to user message")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_from_task_dict(tool_agent, mock_llm_client):
    """Test that images from task dict are merged into context."""

    # Execute task with images in task dict
    result = await tool_agent.execute_task(
        {
            "description": "Describe this image",
            "images": ["https://example.com/task-image.jpg"]
        },
        {}
    )

    # Verify LLM was called
    assert mock_llm_client.generate_text.called

    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]

    # Find the user message
    user_messages = [msg for msg in messages if msg.role == "user"]
    assert len(user_messages) >= 1

    # Check that images are present
    last_user_message = user_messages[-1]
    assert last_user_message.images
    assert "https://example.com/task-image.jpg" in last_user_message.images

    print("\n✓ Images from task dict properly merged into context")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_images_merged_from_task_and_context(tool_agent, mock_llm_client):
    """Test that images from both task and context are merged."""

    # Execute task with images in both task and context
    result = await tool_agent.execute_task(
        {
            "description": "Compare these images",
            "images": ["https://example.com/image1.jpg"]
        },
        {
            "images": ["https://example.com/image2.jpg"]
        }
    )

    # Verify LLM was called
    assert mock_llm_client.generate_text.called

    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]

    # Find the user message
    user_messages = [msg for msg in messages if msg.role == "user"]
    last_user_message = user_messages[-1]

    # Check that both images are present
    assert len(last_user_message.images) >= 2
    assert "https://example.com/image1.jpg" in last_user_message.images
    assert "https://example.com/image2.jpg" in last_user_message.images

    print("\n✓ Images from task and context properly merged")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_context_without_history_still_formatted(tool_agent, mock_llm_client):
    """Test that context fields (excluding history/images) are still formatted."""

    # Execute task with regular context fields
    result = await tool_agent.execute_task(
        {"description": "Process this"},
        {
            "user_id": "user-123",
            "session_id": "session-456",
            "metadata": {"key": "value"}
        }
    )

    # Verify LLM was called
    assert mock_llm_client.generate_text.called

    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]

    # Find system messages with context
    context_messages = [msg for msg in messages if msg.role == "system" and "Additional Context" in msg.content]
    assert len(context_messages) >= 1

    # Verify context fields are included
    context_content = context_messages[0].content
    assert "user_id" in context_content
    assert "session_id" in context_content

    print("\n✓ Context fields (excluding history/images) properly formatted")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_mixed_history_and_context(tool_agent, mock_llm_client):
    """Test handling of both history and regular context fields."""

    # Execute task with both history and context
    result = await tool_agent.execute_task(
        {"description": "Continue"},
        {
            "history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"}
            ],
            "user_id": "user-123",
            "images": ["https://example.com/image.jpg"]
        }
    )

    # Verify LLM was called
    assert mock_llm_client.generate_text.called

    # Get the messages passed to LLM
    call_args = mock_llm_client.generate_text.call_args
    messages = call_args.kwargs["messages"]

    # Verify history messages are present
    history_messages = [msg for msg in messages if msg.role in ("user", "assistant")]
    assert len(history_messages) >= 3  # 2 from history + 1 current

    # Verify context is formatted
    context_messages = [msg for msg in messages if msg.role == "system" and "Additional Context" in msg.content]
    assert len(context_messages) >= 1
    assert "user_id" in context_messages[0].content

    # Verify images are attached to user message
    user_messages = [msg for msg in messages if msg.role == "user"]
    last_user_message = user_messages[-1]
    assert last_user_message.images
    assert "https://example.com/image.jpg" in last_user_message.images

    print("\n✓ Mixed history and context properly handled")


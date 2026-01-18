"""
Tests for None messages handling in LLM client factory and callbacks.

This test suite verifies the fix for the bug reported in:
bug_report/AIECS_BUG_REPORT_CALLBACK_NONE_MESSAGES.md

Tests ensure that:
1. client_factory.py handles None messages gracefully
2. RedisTokenCallbackHandler handles None messages without crashing
3. DetailedRedisTokenCallbackHandler handles None messages without crashing
"""

import pytest
import sys
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add aiecs to path for direct import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
from aiecs.llm.client_factory import LLMClientManager, AIProvider
from aiecs.llm.callbacks.custom_callbacks import (
    RedisTokenCallbackHandler,
    DetailedRedisTokenCallbackHandler,
)


# =============================================================================
# Mock LLM Client for Testing
# =============================================================================

class MockLLMClient:
    """Mock LLM client that returns predictable responses."""
    
    def __init__(self):
        self.provider_name = "mock"
        self.closed = False
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Mock generate_text that returns a simple response."""
        return LLMResponse(
            content="Mock response",
            provider="mock",
            model=model or "mock-model",
            tokens_used=10,
            prompt_tokens=5,
            completion_tokens=5,
        )
    
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        **kwargs
    ):
        """Mock stream_text that yields simple chunks."""
        for chunk in ["Mock ", "streaming ", "response"]:
            yield chunk
    
    async def close(self):
        """Mock close method."""
        self.closed = True


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_client():
    """Create a mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def llm_manager():
    """Create an LLM manager instance."""
    return LLMClientManager()


@pytest.fixture
def redis_callback():
    """Create a RedisTokenCallbackHandler for testing."""
    return RedisTokenCallbackHandler(user_id="test-user-123")


@pytest.fixture
def detailed_callback():
    """Create a DetailedRedisTokenCallbackHandler for testing."""
    return DetailedRedisTokenCallbackHandler(user_id="test-user-456")


# =============================================================================
# Tests for RedisTokenCallbackHandler
# =============================================================================

@pytest.mark.asyncio
async def test_redis_callback_handles_none_messages(redis_callback):
    """Test that RedisTokenCallbackHandler handles None messages without crashing."""
    # This should not raise TypeError: object of type 'NoneType' has no len()
    await redis_callback.on_llm_start(None, provider="test", model="test-model")
    
    # Verify the callback completed successfully
    assert redis_callback.start_time is not None
    assert redis_callback.messages is None


@pytest.mark.asyncio
async def test_redis_callback_handles_empty_messages(redis_callback):
    """Test that RedisTokenCallbackHandler handles empty message list."""
    await redis_callback.on_llm_start([], provider="test", model="test-model")
    
    assert redis_callback.start_time is not None
    assert redis_callback.messages == []


@pytest.mark.asyncio
async def test_redis_callback_handles_valid_messages(redis_callback):
    """Test that RedisTokenCallbackHandler handles valid messages correctly."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    await redis_callback.on_llm_start(messages, provider="test", model="test-model")
    
    assert redis_callback.start_time is not None
    assert redis_callback.messages == messages


# =============================================================================
# Tests for DetailedRedisTokenCallbackHandler
# =============================================================================

@pytest.mark.asyncio
async def test_detailed_callback_handles_none_messages(detailed_callback):
    """Test that DetailedRedisTokenCallbackHandler handles None messages without crashing."""
    # This should not raise TypeError when calling _estimate_prompt_tokens
    await detailed_callback.on_llm_start(None, provider="test", model="test-model")
    
    # Verify the callback completed successfully
    assert detailed_callback.start_time is not None
    assert detailed_callback.messages is None
    assert detailed_callback.prompt_tokens == 0


@pytest.mark.asyncio
async def test_detailed_callback_handles_empty_messages(detailed_callback):
    """Test that DetailedRedisTokenCallbackHandler handles empty message list."""
    await detailed_callback.on_llm_start([], provider="test", model="test-model")

    assert detailed_callback.start_time is not None
    assert detailed_callback.messages == []
    assert detailed_callback.prompt_tokens == 0


@pytest.mark.asyncio
async def test_detailed_callback_handles_valid_messages(detailed_callback):
    """Test that DetailedRedisTokenCallbackHandler handles valid messages correctly."""
    messages = [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"}
    ]

    await detailed_callback.on_llm_start(messages, provider="test", model="test-model")

    assert detailed_callback.start_time is not None
    assert detailed_callback.messages == messages
    # Should estimate tokens based on content length
    assert detailed_callback.prompt_tokens > 0


@pytest.mark.asyncio
async def test_detailed_callback_estimate_prompt_tokens_none():
    """Test _estimate_prompt_tokens with None input."""
    callback = DetailedRedisTokenCallbackHandler(user_id="test-user")

    # Should return 0 for None
    tokens = callback._estimate_prompt_tokens(None)
    assert tokens == 0


@pytest.mark.asyncio
async def test_detailed_callback_estimate_prompt_tokens_empty():
    """Test _estimate_prompt_tokens with empty list."""
    callback = DetailedRedisTokenCallbackHandler(user_id="test-user")

    # Should return 0 for empty list
    tokens = callback._estimate_prompt_tokens([])
    assert tokens == 0


@pytest.mark.asyncio
async def test_detailed_callback_estimate_prompt_tokens_valid():
    """Test _estimate_prompt_tokens with valid messages."""
    callback = DetailedRedisTokenCallbackHandler(user_id="test-user")

    messages = [
        {"role": "user", "content": "Hello"},  # 5 chars
        {"role": "assistant", "content": "Hi!"}  # 3 chars
    ]

    # Should estimate ~2 tokens (8 chars / 4)
    tokens = callback._estimate_prompt_tokens(messages)
    assert tokens == 2


# =============================================================================
# Tests for LLMClientManager with None messages
# =============================================================================

@pytest.mark.asyncio
async def test_generate_text_with_none_messages(llm_manager, mock_client):
    """Test that generate_text handles None messages gracefully."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # This should not crash - None should be converted to empty list
        response = await llm_manager.generate_text(
            messages=None,
            provider="mock"
        )

        assert response is not None
        assert response.content == "Mock response"


@pytest.mark.asyncio
async def test_generate_text_with_none_messages_and_callbacks(llm_manager, mock_client, redis_callback):
    """Test that generate_text with None messages works with callbacks."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # This should not crash even with callbacks
        response = await llm_manager.generate_text(
            messages=None,
            provider="mock",
            callbacks=[redis_callback]
        )

        assert response is not None
        assert response.content == "Mock response"
        # Callback should have been called with empty messages
        assert redis_callback.start_time is not None


@pytest.mark.asyncio
async def test_stream_text_with_none_messages(llm_manager, mock_client):
    """Test that stream_text handles None messages gracefully."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # This should not crash - None should be converted to empty list
        chunks = []
        async for chunk in llm_manager.stream_text(
            messages=None,
            provider="mock"
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert "Mock" in chunks[0]


@pytest.mark.asyncio
async def test_stream_text_with_none_messages_and_callbacks(llm_manager, mock_client, detailed_callback):
    """Test that stream_text with None messages works with callbacks."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # This should not crash even with callbacks
        chunks = []
        async for chunk in llm_manager.stream_text(
            messages=None,
            provider="mock",
            callbacks=[detailed_callback]
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Callback should have been called with empty messages
        assert detailed_callback.start_time is not None
        assert detailed_callback.prompt_tokens == 0


# =============================================================================
# Tests for string messages conversion
# =============================================================================

@pytest.mark.asyncio
async def test_generate_text_with_string_messages(llm_manager, mock_client):
    """Test that string messages are converted to LLMMessage format."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        response = await llm_manager.generate_text(
            messages="Hello, world!",
            provider="mock"
        )

        assert response is not None
        assert response.content == "Mock response"


@pytest.mark.asyncio
async def test_stream_text_with_string_messages(llm_manager, mock_client):
    """Test that string messages work with stream_text."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        chunks = []
        async for chunk in llm_manager.stream_text(
            messages="Hello, world!",
            provider="mock"
        ):
            chunks.append(chunk)

        assert len(chunks) > 0


# =============================================================================
# Integration Tests
# =============================================================================

@pytest.mark.asyncio
async def test_full_workflow_with_none_messages(llm_manager, mock_client, redis_callback, detailed_callback):
    """Test complete workflow with None messages and multiple callbacks."""
    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # Test with both callbacks
        response = await llm_manager.generate_text(
            messages=None,
            provider="mock",
            callbacks=[redis_callback, detailed_callback]
        )

        # Response should be successful
        assert response is not None
        assert response.content == "Mock response"

        # Both callbacks should have been invoked
        assert redis_callback.start_time is not None
        assert detailed_callback.start_time is not None
        assert detailed_callback.prompt_tokens == 0


@pytest.mark.asyncio
async def test_callback_error_handling_with_none_messages(llm_manager, mock_client):
    """Test that callback errors are caught and logged properly."""
    # Create a callback that will raise an error
    class BrokenCallback(RedisTokenCallbackHandler):
        async def on_llm_start(self, messages, **kwargs):
            raise ValueError("Intentional error for testing")

    broken_callback = BrokenCallback(user_id="test-user")

    with patch.object(llm_manager.factory, 'get_client', return_value=mock_client):
        # Should not crash even if callback raises error
        response = await llm_manager.generate_text(
            messages=None,
            provider="mock",
            callbacks=[broken_callback]
        )

        # Response should still be successful
        assert response is not None
        assert response.content == "Mock response"


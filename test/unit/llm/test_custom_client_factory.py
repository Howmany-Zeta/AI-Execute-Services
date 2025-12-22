"""
Tests for custom LLM client factory registration.

Tests the ability to register and use custom LLM clients that implement
LLMClientProtocol without inheriting from BaseLLMClient.
"""

import pytest
import sys
from pathlib import Path
from typing import List, Optional, AsyncGenerator

# Add aiecs to path for direct import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from aiecs.llm.clients.base_client import LLMMessage, LLMResponse

# Import factory after setting up path
from aiecs.llm.client_factory import LLMClientFactory, AIProvider


class MockCustomLLMClient:
    """Mock custom LLM client for testing"""

    def __init__(self, provider_name: str = "mock-custom"):
        self.provider_name = provider_name
        self.closed = False

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Mock text generation"""
        return LLMResponse(
            content="Mock response from custom client",
            provider=self.provider_name,
            model=model or "mock-model",
            tokens_used=10,
        )

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Mock streaming text generation"""
        for token in ["Mock ", "streaming ", "response"]:
            yield token

    async def close(self):
        """Mock cleanup"""
        self.closed = True

    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Mock embeddings generation"""
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.fixture
def cleanup_factory():
    """Cleanup factory state after each test"""
    yield
    # Clear custom clients after test
    LLMClientFactory._custom_clients.clear()


@pytest.mark.asyncio
async def test_register_custom_provider(cleanup_factory):
    """Test registering a custom LLM provider"""
    custom_client = MockCustomLLMClient("test-provider")
    
    # Register custom provider
    LLMClientFactory.register_custom_provider("test-provider", custom_client)
    
    # Verify registration
    assert "test-provider" in LLMClientFactory._custom_clients
    assert LLMClientFactory._custom_clients["test-provider"] == custom_client


@pytest.mark.asyncio
async def test_get_custom_client(cleanup_factory):
    """Test retrieving a registered custom client"""
    custom_client = MockCustomLLMClient("my-llm")
    LLMClientFactory.register_custom_provider("my-llm", custom_client)
    
    # Get custom client
    retrieved_client = LLMClientFactory.get_client("my-llm")
    
    # Verify it's the same instance
    assert retrieved_client == custom_client
    assert retrieved_client.provider_name == "my-llm"


@pytest.mark.asyncio
async def test_custom_client_generate_text(cleanup_factory):
    """Test using custom client for text generation"""
    custom_client = MockCustomLLMClient("custom-gpt")
    LLMClientFactory.register_custom_provider("custom-gpt", custom_client)
    
    # Get and use client
    client = LLMClientFactory.get_client("custom-gpt")
    messages = [LLMMessage(role="user", content="Hello")]
    response = await client.generate_text(messages)
    
    # Verify response
    assert response.content == "Mock response from custom client"
    assert response.provider == "custom-gpt"


@pytest.mark.asyncio
async def test_custom_client_stream_text(cleanup_factory):
    """Test using custom client for streaming"""
    custom_client = MockCustomLLMClient("stream-llm")
    LLMClientFactory.register_custom_provider("stream-llm", custom_client)

    # Get and use client
    client = LLMClientFactory.get_client("stream-llm")
    messages = [LLMMessage(role="user", content="Hello")]

    # Collect streamed tokens
    tokens = []
    async for token in client.stream_text(messages):
        tokens.append(token)

    # Verify streaming
    assert tokens == ["Mock ", "streaming ", "response"]


@pytest.mark.asyncio
async def test_custom_client_embeddings(cleanup_factory):
    """Test using custom client for embeddings"""
    custom_client = MockCustomLLMClient("embed-llm")
    LLMClientFactory.register_custom_provider("embed-llm", custom_client)

    # Get and use client
    client = LLMClientFactory.get_client("embed-llm")
    embeddings = await client.get_embeddings(["text1", "text2"])

    # Verify embeddings
    assert len(embeddings) == 2
    assert embeddings[0] == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_register_invalid_client(cleanup_factory):
    """Test that registering invalid client raises error"""
    # Create object that doesn't implement protocol
    invalid_client = {"not": "a client"}

    # Should raise ValueError
    with pytest.raises(ValueError, match="must implement LLMClientProtocol"):
        LLMClientFactory.register_custom_provider("invalid", invalid_client)


@pytest.mark.asyncio
async def test_register_conflicting_name(cleanup_factory):
    """Test that registering with standard provider name raises error"""
    custom_client = MockCustomLLMClient("OpenAI")

    # Should raise ValueError for conflicting name
    with pytest.raises(ValueError, match="conflicts with standard AIProvider"):
        LLMClientFactory.register_custom_provider("OpenAI", custom_client)


@pytest.mark.asyncio
async def test_get_unknown_provider(cleanup_factory):
    """Test that getting unknown provider raises error"""
    # Should raise ValueError with helpful message
    with pytest.raises(ValueError, match="Unknown provider"):
        LLMClientFactory.get_client("nonexistent-provider")


@pytest.mark.asyncio
async def test_close_custom_client(cleanup_factory):
    """Test closing a custom client"""
    custom_client = MockCustomLLMClient("closable")
    LLMClientFactory.register_custom_provider("closable", custom_client)

    # Close the client
    await LLMClientFactory.close_client("closable")

    # Verify it was closed
    assert custom_client.closed
    assert "closable" not in LLMClientFactory._custom_clients


@pytest.mark.asyncio
async def test_close_all_includes_custom(cleanup_factory):
    """Test that close_all closes custom clients too"""
    custom_client1 = MockCustomLLMClient("custom1")
    custom_client2 = MockCustomLLMClient("custom2")

    LLMClientFactory.register_custom_provider("custom1", custom_client1)
    LLMClientFactory.register_custom_provider("custom2", custom_client2)

    # Close all clients
    await LLMClientFactory.close_all()

    # Verify all custom clients were closed
    assert custom_client1.closed
    assert custom_client2.closed
    assert len(LLMClientFactory._custom_clients) == 0


@pytest.mark.asyncio
async def test_custom_client_priority_over_standard(cleanup_factory):
    """Test that custom clients are checked before standard providers"""
    # Register a custom client with a name that could be confused
    custom_client = MockCustomLLMClient("my-openai")
    LLMClientFactory.register_custom_provider("my-openai", custom_client)

    # Get client - should return custom, not try to parse as standard
    client = LLMClientFactory.get_client("my-openai")

    # Verify it's the custom client
    assert client == custom_client
    assert client.provider_name == "my-openai"


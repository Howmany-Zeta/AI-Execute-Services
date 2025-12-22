"""
Tests for LLM Client Resolver

Tests the client resolution helper functions with caching support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiecs.llm.client_resolver import (
    resolve_llm_client,
    clear_client_cache,
    get_cached_providers,
)
from aiecs.llm.client_factory import LLMClientFactory, AIProvider
from aiecs.llm.protocols import LLMClientProtocol


class MockLLMClient:
    """Mock LLM client for testing"""

    def __init__(self, provider_name: str = "mock-provider"):
        self.provider_name = provider_name
        self.generate_text = AsyncMock()
        self.stream_text = AsyncMock()
        self.close = AsyncMock()
        self.get_embeddings = AsyncMock()


@pytest.fixture(autouse=True)
def clear_cache_before_test():
    """Clear cache before each test"""
    clear_client_cache()
    yield
    clear_client_cache()


@pytest.fixture
def mock_custom_client():
    """Create a mock custom LLM client"""
    return MockLLMClient(provider_name="custom-test-provider")


def test_resolve_llm_client_standard_provider():
    """Test resolving a standard provider"""
    # Resolve OpenAI client
    client = resolve_llm_client(AIProvider.OPENAI)

    # Verify client is returned
    assert client is not None
    assert hasattr(client, "generate_text")
    assert hasattr(client, "provider_name")


def test_resolve_llm_client_with_model_name():
    """Test resolving client with model name (for logging)"""
    # Resolve with model name
    client = resolve_llm_client(AIProvider.OPENAI, model="gpt-4")

    # Verify client is returned
    assert client is not None


def test_resolve_llm_client_custom_provider(mock_custom_client):
    """Test resolving a custom provider"""
    # Register custom provider
    LLMClientFactory.register_custom_provider("custom-test", mock_custom_client)

    # Resolve custom provider
    client = resolve_llm_client("custom-test")

    # Verify correct client is returned
    assert client is mock_custom_client
    assert client.provider_name == "custom-test-provider"


def test_resolve_llm_client_caching():
    """Test that client resolution uses caching"""
    # Clear cache first
    clear_client_cache()

    # Resolve client twice
    client1 = resolve_llm_client(AIProvider.OPENAI, use_cache=True)
    client2 = resolve_llm_client(AIProvider.OPENAI, use_cache=True)

    # Verify same instance is returned (cached)
    assert client1 is client2

    # Verify provider is in cache (enum converts to "AIProvider.OPENAI")
    cached = get_cached_providers()
    assert "AIProvider.OPENAI" in cached


def test_resolve_llm_client_without_caching():
    """Test that caching can be disabled"""
    # Clear cache first
    clear_client_cache()

    # Resolve client twice without caching
    client1 = resolve_llm_client(AIProvider.OPENAI, use_cache=False)
    client2 = resolve_llm_client(AIProvider.OPENAI, use_cache=False)

    # Note: For standard providers, LLMClientFactory also caches,
    # so we just verify that our cache is empty
    cached = get_cached_providers()
    assert len(cached) == 0


def test_resolve_llm_client_unknown_provider():
    """Test that unknown provider raises ValueError"""
    with pytest.raises(ValueError, match="Unknown provider"):
        resolve_llm_client("unknown-provider-xyz")


def test_clear_client_cache_all():
    """Test clearing entire cache"""
    # Resolve multiple clients
    resolve_llm_client(AIProvider.OPENAI, use_cache=True)
    resolve_llm_client(AIProvider.VERTEX, use_cache=True)

    # Verify cache has entries
    cached = get_cached_providers()
    assert len(cached) >= 2

    # Clear entire cache
    clear_client_cache()

    # Verify cache is empty
    cached = get_cached_providers()
    assert len(cached) == 0


def test_clear_client_cache_specific_provider():
    """Test clearing specific provider from cache"""
    # Resolve multiple clients
    resolve_llm_client(AIProvider.OPENAI, use_cache=True)
    resolve_llm_client(AIProvider.VERTEX, use_cache=True)

    # Clear only OpenAI
    clear_client_cache(AIProvider.OPENAI)

    # Verify OpenAI is removed but Vertex remains (enum converts to "AIProvider.X")
    cached = get_cached_providers()
    assert "AIProvider.OPENAI" not in cached
    assert "AIProvider.VERTEX" in cached


def test_clear_client_cache_nonexistent_provider():
    """Test clearing a provider that's not in cache (should not error)"""
    # Clear cache first
    clear_client_cache()

    # Try to clear a provider that's not cached (should not raise error)
    clear_client_cache("nonexistent-provider")

    # Verify cache is still empty
    cached = get_cached_providers()
    assert len(cached) == 0


def test_get_cached_providers_empty():
    """Test getting cached providers when cache is empty"""
    # Clear cache
    clear_client_cache()

    # Get cached providers
    cached = get_cached_providers()

    # Verify empty list
    assert cached == []


def test_get_cached_providers_multiple():
    """Test getting cached providers with multiple entries"""
    # Resolve multiple clients
    resolve_llm_client(AIProvider.OPENAI, use_cache=True)
    resolve_llm_client(AIProvider.VERTEX, use_cache=True)

    # Get cached providers
    cached = get_cached_providers()

    # Verify both are in cache (enum converts to "AIProvider.X")
    assert "AIProvider.OPENAI" in cached
    assert "AIProvider.VERTEX" in cached
    assert len(cached) >= 2


def test_resolve_llm_client_string_provider():
    """Test resolving client with string provider name"""
    # Resolve using string instead of enum
    client = resolve_llm_client("OpenAI")

    # Verify client is returned
    assert client is not None
    assert hasattr(client, "generate_text")


"""
Integration Test for OpenRouter Client

Tests OpenRouter client with real API calls to GPT-4o model.
Uses API key from .env.test file.

Requirements:
- OPENROUTER_API_KEY must be set in .env.test
- Real LLM calls will be made (costs may apply)
"""

import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from aiecs.llm.clients.openrouter_client import OpenRouterClient
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
from aiecs.llm.client_factory import LLMClientFactory, AIProvider


# Load test environment
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Go up from test/integration/llm/
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"✓ Loaded test environment from {env_test_path}")
else:
    print(f"⚠ Warning: .env.test not found at {env_test_path}")

# Handle both OPENROUTER_API_KEY and openrouter_KEY (backward compatibility)
if not os.getenv("OPENROUTER_API_KEY") and os.getenv("openrouter_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.getenv("openrouter_KEY")
    print("✓ Using openrouter_KEY as OPENROUTER_API_KEY")


@pytest.fixture
async def openrouter_client():
    """Create OpenRouter client instance"""
    client = OpenRouterClient()
    yield client
    # Cleanup
    await client.close()


@pytest.mark.asyncio
async def test_openrouter_basic_generation(openrouter_client):
    """Test basic text generation with GPT-4o"""
    print("\n=== Test: Basic Text Generation ===")
    
    messages = [
        LLMMessage(
            role="user",
            content="Say hello in one sentence."
        )
    ]
    
    response = await openrouter_client.generate_text(
        messages=messages,
        model="openai/gpt-4o"
    )
    
    assert response is not None
    assert isinstance(response, LLMResponse)
    assert response.content is not None
    assert len(response.content) > 0
    assert response.provider == "OpenRouter"
    assert response.model == "openai/gpt-4o"
    
    print(f"✓ Response: {response.content}")
    print(f"✓ Provider: {response.provider}")
    print(f"✓ Model: {response.model}")
    print(f"✓ Tokens used: {response.tokens_used}")
    if response.cost_estimate:
        print(f"✓ Cost estimate: ${response.cost_estimate:.6f}")


@pytest.mark.asyncio
async def test_openrouter_streaming(openrouter_client):
    """Test streaming text generation"""
    print("\n=== Test: Streaming Text Generation ===")
    
    messages = [
        LLMMessage(
            role="user",
            content="Count from 1 to 5, one number per line."
        )
    ]
    
    collected_chunks = []
    async for chunk in openrouter_client.stream_text(
        messages=messages,
        model="openai/gpt-4o"
    ):
        assert chunk is not None
        collected_chunks.append(chunk)
        print(chunk, end="", flush=True)
    
    print()  # New line after streaming
    full_response = "".join(collected_chunks)
    
    assert len(collected_chunks) > 0
    assert len(full_response) > 0
    print(f"✓ Received {len(collected_chunks)} chunks")
    print(f"✓ Full response length: {len(full_response)} characters")


@pytest.mark.asyncio
async def test_openrouter_with_extra_headers(openrouter_client):
    """Test with extra headers for OpenRouter rankings"""
    print("\n=== Test: With Extra Headers ===")
    
    messages = [
        LLMMessage(
            role="user",
            content="What is 2+2?"
        )
    ]
    
    response = await openrouter_client.generate_text(
        messages=messages,
        model="openai/gpt-4o",
        http_referer="https://test-app.com",
        x_title="Test App"
    )
    
    assert response is not None
    assert response.content is not None
    print(f"✓ Response with headers: {response.content}")


@pytest.mark.asyncio
async def test_openrouter_function_calling(openrouter_client):
    """Test function calling support"""
    print("\n=== Test: Function Calling ===")
    
    messages = [
        LLMMessage(
            role="user",
            content="What's the weather in San Francisco?"
        )
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    
    response = await openrouter_client.generate_text(
        messages=messages,
        model="openai/gpt-4o",
        tools=tools
    )
    
    assert response is not None
    print(f"✓ Response: {response.content}")
    if response.tool_calls:
        print(f"✓ Tool calls: {response.tool_calls}")
        assert len(response.tool_calls) > 0


@pytest.mark.asyncio
async def test_openrouter_vision(openrouter_client):
    """Test vision support with image URL"""
    print("\n=== Test: Vision Support ===")
    
    # Using a publicly accessible test image
    messages = [
        LLMMessage(
            role="user",
            content="What is in this image? Describe it briefly.",
            images=["https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"]
        )
    ]
    
    response = await openrouter_client.generate_text(
        messages=messages,
        model="openai/gpt-4o"  # Vision-capable model
    )
    
    assert response is not None
    assert response.content is not None
    print(f"✓ Vision response: {response.content}")


@pytest.mark.asyncio
async def test_openrouter_via_factory():
    """Test OpenRouter client via LLMClientFactory"""
    print("\n=== Test: Via Factory ===")
    
    client = LLMClientFactory.get_client(AIProvider.OPENROUTER)
    
    messages = [
        LLMMessage(
            role="user",
            content="Say 'Hello from OpenRouter!'"
        )
    ]
    
    response = await client.generate_text(
        messages=messages,
        model="openai/gpt-4o"
    )
    
    assert response is not None
    assert response.content is not None
    print(f"✓ Factory response: {response.content}")
    
    await client.close()


@pytest.mark.asyncio
async def test_openrouter_different_models(openrouter_client):
    """Test with different models available on OpenRouter"""
    print("\n=== Test: Different Models ===")
    
    models_to_test = [
        "openai/gpt-4o",
        # Add more models if needed
    ]
    
    messages = [
        LLMMessage(
            role="user",
            content="Say hello in one word."
        )
    ]
    
    for model in models_to_test:
        try:
            print(f"\nTesting model: {model}")
            response = await openrouter_client.generate_text(
                messages=messages,
                model=model
            )
            assert response is not None
            assert response.content is not None
            print(f"✓ {model}: {response.content}")
        except Exception as e:
            print(f"✗ {model} failed: {e}")
            raise


if __name__ == "__main__":
    """Run tests directly"""
    import sys
    
    # Check if API key is configured
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("openrouter_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in environment")
        print("   Please set it in .env.test file")
        sys.exit(1)
    
    print("=" * 60)
    print("OpenRouter Client Integration Tests")
    print("=" * 60)
    print(f"API Key: {api_key[:20]}...")
    print()
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])

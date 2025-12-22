#!/usr/bin/env python3
"""
Simple integration test for custom LLM client registration.
Run this script to verify the custom client factory implementation.
"""

import asyncio
import sys
from typing import List, Optional, AsyncGenerator
from pathlib import Path

# Add aiecs to path
sys.path.insert(0, str(Path(__file__).parent))

from aiecs.llm.clients.base_client import LLMMessage, LLMResponse
from aiecs.llm.client_factory import LLMClientFactory


class TestCustomLLMClient:
    """Test custom LLM client implementation"""

    def __init__(self, provider_name: str = "test-llm"):
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
        """Generate text"""
        return LLMResponse(
            content=f"Response from {self.provider_name}",
            provider=self.provider_name,
            model=model or "test-model",
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
        """Stream text"""
        for token in ["Hello ", "from ", self.provider_name]:
            yield token

    async def close(self):
        """Cleanup"""
        self.closed = True
        print(f"✓ Closed {self.provider_name}")

    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Get embeddings"""
        return [[0.1, 0.2, 0.3] for _ in texts]


async def test_custom_client_registration():
    """Test 1: Register and retrieve custom client"""
    print("\n=== Test 1: Custom Client Registration ===")
    
    # Create and register custom client
    custom_client = TestCustomLLMClient("my-custom-llm")
    LLMClientFactory.register_custom_provider("my-custom-llm", custom_client)
    print("✓ Registered custom provider: my-custom-llm")
    
    # Retrieve client
    retrieved = LLMClientFactory.get_client("my-custom-llm")
    assert retrieved == custom_client
    print("✓ Retrieved custom client successfully")
    
    return custom_client


async def test_generate_text(client):
    """Test 2: Generate text with custom client"""
    print("\n=== Test 2: Generate Text ===")
    
    messages = [LLMMessage(role="user", content="Hello")]
    response = await client.generate_text(messages)
    
    print(f"✓ Generated text: {response.content}")
    print(f"✓ Provider: {response.provider}")
    print(f"✓ Model: {response.model}")
    assert "my-custom-llm" in response.content


async def test_stream_text(client):
    """Test 3: Stream text with custom client"""
    print("\n=== Test 3: Stream Text ===")

    messages = [LLMMessage(role="user", content="Hello")]
    tokens = []

    async for token in client.stream_text(messages):
        tokens.append(token)
        print(f"  Token: {token}")

    full_text = "".join(tokens)
    print(f"✓ Streamed text: {full_text}")
    assert "my-custom-llm" in full_text


async def test_embeddings(client):
    """Test 4: Get embeddings with custom client"""
    print("\n=== Test 4: Get Embeddings ===")
    
    texts = ["text1", "text2", "text3"]
    embeddings = await client.get_embeddings(texts)
    
    print(f"✓ Generated {len(embeddings)} embeddings")
    print(f"✓ Embedding dimension: {len(embeddings[0])}")
    assert len(embeddings) == 3


async def test_error_cases():
    """Test 5: Error handling"""
    print("\n=== Test 5: Error Handling ===")
    
    # Test invalid client
    try:
        LLMClientFactory.register_custom_provider("invalid", {"not": "a client"})
        print("✗ Should have raised ValueError for invalid client")
    except ValueError as e:
        print(f"✓ Correctly rejected invalid client: {str(e)[:50]}...")
    
    # Test conflicting name
    try:
        valid_client = TestCustomLLMClient("OpenAI")
        LLMClientFactory.register_custom_provider("OpenAI", valid_client)
        print("✗ Should have raised ValueError for conflicting name")
    except ValueError as e:
        print(f"✓ Correctly rejected conflicting name: {str(e)[:50]}...")
    
    # Test unknown provider
    try:
        LLMClientFactory.get_client("nonexistent-provider")
        print("✗ Should have raised ValueError for unknown provider")
    except ValueError as e:
        print(f"✓ Correctly raised error for unknown provider")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Custom LLM Client Factory Registration")
    print("=" * 60)
    
    try:
        # Test 1: Registration
        client = await test_custom_client_registration()
        
        # Test 2: Generate text
        await test_generate_text(client)
        
        # Test 3: Stream text
        await test_stream_text(client)
        
        # Test 4: Embeddings
        await test_embeddings(client)
        
        # Test 5: Error cases
        await test_error_cases()
        
        # Cleanup
        await LLMClientFactory.close_all()
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


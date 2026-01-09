"""
Integration Test for Vision Support with Real Image

Tests xAI and OpenRouter clients with a real image file to verify vision capabilities.
Uses API keys from .env.test file.

Requirements:
- XAI_API_KEY or GROK_API_KEY must be set in .env.test (for xAI)
- OPENROUTER_API_KEY or openrouter_KEY must be set in .env.test (for OpenRouter)
- Real LLM calls will be made (costs may apply)
"""

import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from aiecs.llm.clients.openrouter_client import OpenRouterClient
from aiecs.llm.clients.xai_client import XAIClient
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse


# Load test environment
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    print(f"✓ Loaded test environment from {env_test_path}")
else:
    print(f"⚠ Warning: .env.test not found at {env_test_path}")

# Handle API key mappings
if not os.getenv("OPENROUTER_API_KEY") and os.getenv("openrouter_KEY"):
    os.environ["OPENROUTER_API_KEY"] = os.getenv("openrouter_KEY")
    print("✓ Using openrouter_KEY as OPENROUTER_API_KEY")

# Real image path
REAL_IMAGE_PATH = PROJECT_ROOT / "data" / "c6b1caaaee600f46c4a51495944d46e0.png"


@pytest.fixture
async def openrouter_client():
    """Create OpenRouter client instance"""
    client = OpenRouterClient()
    yield client
    await client.close()


@pytest.fixture
async def xai_client():
    """Create xAI client instance"""
    client = XAIClient()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_openrouter_vision_with_real_image(openrouter_client):
    """Test OpenRouter GPT-4o vision with real image file"""
    print("\n" + "=" * 60)
    print("Test: OpenRouter GPT-4o Vision with Real Image")
    print("=" * 60)
    
    # Verify image file exists
    assert REAL_IMAGE_PATH.exists(), f"Image file not found: {REAL_IMAGE_PATH}"
    print(f"✓ Image file found: {REAL_IMAGE_PATH}")
    print(f"✓ Image file size: {REAL_IMAGE_PATH.stat().st_size} bytes")
    
    messages = [
        LLMMessage(
            role="user",
            content="Describe this image in detail. What do you see?",
            images=[str(REAL_IMAGE_PATH)]  # Use absolute path
        )
    ]
    
    print(f"\nSending request to OpenRouter GPT-4o...")
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
    
    print(f"\n✓ Response received:")
    print(f"  Provider: {response.provider}")
    print(f"  Model: {response.model}")
    print(f"  Tokens used: {response.tokens_used}")
    if response.cost_estimate:
        print(f"  Cost estimate: ${response.cost_estimate:.6f}")
    print(f"\n  Image Description:")
    print(f"  {response.content}")
    
    # Verify the response contains meaningful content about the image
    assert len(response.content) > 20, "Response seems too short"
    print("\n✓ Vision test passed: Image was successfully analyzed")


@pytest.mark.asyncio
async def test_openrouter_vision_detailed_analysis(openrouter_client):
    """Test OpenRouter with more detailed image analysis questions"""
    print("\n" + "=" * 60)
    print("Test: OpenRouter Detailed Image Analysis")
    print("=" * 60)
    
    assert REAL_IMAGE_PATH.exists(), f"Image file not found: {REAL_IMAGE_PATH}"
    
    messages = [
        LLMMessage(
            role="user",
            content="Analyze this image and answer: 1) What is the main subject? 2) What colors are prominent? 3) What is the overall mood or atmosphere?",
            images=[str(REAL_IMAGE_PATH)]
        )
    ]
    
    response = await openrouter_client.generate_text(
        messages=messages,
        model="openai/gpt-4o"
    )
    
    assert response is not None
    assert response.content is not None
    assert len(response.content) > 50, "Response should contain detailed analysis"
    
    print(f"\n✓ Detailed Analysis:")
    print(f"{response.content}")
    print("\n✓ Detailed analysis test passed")


@pytest.mark.asyncio
async def test_xai_vision_with_real_image(xai_client):
    """Test xAI Grok vision with real image file"""
    print("\n" + "=" * 60)
    print("Test: xAI Grok Vision with Real Image")
    print("=" * 60)
    
    # Check if xAI API key is configured
    api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        pytest.skip("xAI API key not configured in .env.test")
    
    assert REAL_IMAGE_PATH.exists(), f"Image file not found: {REAL_IMAGE_PATH}"
    print(f"✓ Image file found: {REAL_IMAGE_PATH}")
    
    # Check if Grok 2 Vision model is available
    # Note: Only grok-2-vision supports vision, other Grok models don't
    messages = [
        LLMMessage(
            role="user",
            content="Describe this image. What do you see?",
            images=[str(REAL_IMAGE_PATH)]
        )
    ]
    
    print(f"\nSending request to xAI Grok-2-Vision...")
    try:
        response = await xai_client.generate_text(
            messages=messages,
            model="grok-2-vision"  # Only vision-capable Grok model
        )
        
        assert response is not None
        assert isinstance(response, LLMResponse)
        assert response.content is not None
        assert len(response.content) > 0
        
        print(f"\n✓ Response received:")
        print(f"  Provider: {response.provider}")
        print(f"  Model: {response.model}")
        print(f"  Tokens used: {response.tokens_used}")
        print(f"\n  Image Description:")
        print(f"  {response.content}")
        
        assert len(response.content) > 20, "Response seems too short"
        print("\n✓ xAI Vision test passed: Image was successfully analyzed")
        
    except Exception as e:
        # If grok-2-vision is not available or has issues, skip the test
        if "model" in str(e).lower() or "not found" in str(e).lower():
            pytest.skip(f"Grok-2-Vision model not available: {e}")
        else:
            raise


@pytest.mark.asyncio
async def test_vision_comparison():
    """Compare vision responses from both providers"""
    print("\n" + "=" * 60)
    print("Test: Vision Comparison (OpenRouter vs xAI)")
    print("=" * 60)
    
    assert REAL_IMAGE_PATH.exists(), f"Image file not found: {REAL_IMAGE_PATH}"
    
    messages = [
        LLMMessage(
            role="user",
            content="What is the main subject of this image? Answer in one sentence.",
            images=[str(REAL_IMAGE_PATH)]
        )
    ]
    
    # Test OpenRouter
    print("\n--- OpenRouter GPT-4o Response ---")
    openrouter_client = OpenRouterClient()
    try:
        openrouter_response = await openrouter_client.generate_text(
            messages=messages,
            model="openai/gpt-4o"
        )
        print(f"OpenRouter: {openrouter_response.content}")
    finally:
        await openrouter_client.close()
    
    # Test xAI (if available)
    api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    if api_key:
        print("\n--- xAI Grok-2-Vision Response ---")
        xai_client = XAIClient()
        try:
            xai_response = await xai_client.generate_text(
                messages=messages,
                model="grok-2-vision"
            )
            print(f"xAI: {xai_response.content}")
        except Exception as e:
            print(f"xAI test skipped: {e}")
        finally:
            await xai_client.close()
    else:
        print("\n--- xAI test skipped (no API key) ---")
    
    print("\n✓ Comparison test completed")


@pytest.mark.asyncio
async def test_vision_with_base64():
    """Test vision with base64 encoded image"""
    print("\n" + "=" * 60)
    print("Test: Vision with Base64 Encoded Image")
    print("=" * 60)
    
    assert REAL_IMAGE_PATH.exists(), f"Image file not found: {REAL_IMAGE_PATH}"
    
    # Read image and convert to base64
    import base64
    with open(REAL_IMAGE_PATH, "rb") as f:
        image_data = f.read()
        base64_data = base64.b64encode(image_data).decode("utf-8")
        data_uri = f"data:image/png;base64,{base64_data}"
    
    print(f"✓ Image encoded to base64 ({len(base64_data)} characters)")
    
    messages = [
        LLMMessage(
            role="user",
            content="What is in this image?",
            images=[data_uri]  # Use base64 data URI
        )
    ]
    
    openrouter_client = OpenRouterClient()
    try:
        response = await openrouter_client.generate_text(
            messages=messages,
            model="openai/gpt-4o"
        )
        
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0
        
        print(f"\n✓ Base64 image response:")
        print(f"{response.content}")
        print("\n✓ Base64 encoding test passed")
    finally:
        await openrouter_client.close()


if __name__ == "__main__":
    """Run tests directly"""
    import sys
    
    # Verify image file exists
    if not REAL_IMAGE_PATH.exists():
        print(f"❌ Error: Image file not found: {REAL_IMAGE_PATH}")
        sys.exit(1)
    
    # Check API keys
    openrouter_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("openrouter_KEY")
    xai_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
    
    print("=" * 60)
    print("Vision Support Integration Tests")
    print("=" * 60)
    print(f"Image file: {REAL_IMAGE_PATH}")
    print(f"Image exists: {REAL_IMAGE_PATH.exists()}")
    print(f"Image size: {REAL_IMAGE_PATH.stat().st_size if REAL_IMAGE_PATH.exists() else 0} bytes")
    print()
    print("API Keys:")
    print(f"  OpenRouter: {'✓ Configured' if openrouter_key else '✗ Not configured'}")
    print(f"  xAI: {'✓ Configured' if xai_key else '✗ Not configured'}")
    print()
    
    if not openrouter_key:
        print("⚠ Warning: OpenRouter API key not found")
    
    # Run tests
    pytest.main([__file__, "-v", "-s"])

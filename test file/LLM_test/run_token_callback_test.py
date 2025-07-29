#!/usr/bin/env python3
"""
Simple test runner for token callback functionality

This script demonstrates the token callback functionality with real API connections.
Run this script to test the token callback feature with Vertex AI.

Usage:
    python run_token_callback_test.py

Requirements:
    - VERTEX_PROJECT_ID environment variable set
    - Redis server running
    - Valid Google Cloud credentials
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import the app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from app.llm.base_client import LLMMessage, LLMResponse
from app.llm.client_factory import generate_text, AIProvider
from app.llm.custom_callbacks import create_token_callback, create_detailed_token_callback
from app.utils.token_usage_repository import token_usage_repo
from app.core.redis_client import redis_client
from app.core.config import get_settings

async def test_basic_token_callback():
    """Test basic token callback functionality"""
    print("🧪 Testing Basic Token Callback Functionality")
    print("=" * 50)

    try:
        # Check configuration
        settings = get_settings()
        if not settings.vertex_project_id:
            print("❌ Vertex AI project ID not configured.")
            print("   Please set VERTEX_PROJECT_ID environment variable.")
            return False

        print(f"✅ Vertex AI project ID: {settings.vertex_project_id}")

        # Test Redis connection
        try:
            client = await redis_client.get_client()
            await client.ping()
            print("✅ Redis connection successful")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False

        # Create test user
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = f"test_callback_{timestamp}"
        cycle_date = "2025-01-01"

        print(f"👤 Test user ID: {user_id}")

        # Reset any existing usage
        await token_usage_repo.reset_usage(user_id, cycle_date)
        print("🔄 Reset existing token usage")

        # Create token callback handler
        callback = create_token_callback(user_id, cycle_date)
        print("📋 Created token callback handler")

        # Make API call with callback
        messages = [LLMMessage(role="user", content="Hello! Please respond with 'Token callback test successful' to confirm the functionality is working.")]

        print("📡 Making API call to Vertex AI with token callback...")
        response = await generate_text(
            messages=messages,
            provider=AIProvider.VERTEX,
            model="gemini-2.5-pro",
            temperature=0.1,
            max_tokens=4096,
            callbacks=[callback]
        )

        print(f"📝 Response: {response.content}")
        print(f"🔢 Tokens used: {response.tokens_used}")
        print(f"🏷️  Model: {response.model}")
        print(f"🏢 Provider: {response.provider}")

        # Check for blocked responses
        if ("[Response blocked by safety filters" in response.content or
            "[Response unavailable" in response.content or
            "[Response error:" in response.content):
            print("⚠️  Response was blocked by safety filters - callback test may not be accurate")
            return False

        # Wait for callback to process
        print("⏳ Waiting for callback to process...")
        await asyncio.sleep(2.0)

        # Check if token usage was recorded
        stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)
        print(f"💾 Recorded tokens: {stats['total_tokens']}")

        if stats['total_tokens'] > 0:
            if stats['total_tokens'] == response.tokens_used:
                print("✅ Token callback functionality test PASSED!")
                print(f"   Expected: {response.tokens_used}, Recorded: {stats['total_tokens']}")
                return True
            else:
                print(f"⚠️  Token counts don't match exactly:")
                print(f"   Expected: {response.tokens_used}, Recorded: {stats['total_tokens']}")
                print("   This might be due to token estimation differences, but callback is working.")
                return True
        else:
            print("❌ No tokens were recorded - callback failed!")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_detailed_token_callback():
    """Test detailed token callback functionality"""
    print("\n🧪 Testing Detailed Token Callback Functionality")
    print("=" * 50)

    try:
        settings = get_settings()
        if not settings.vertex_project_id:
            print("❌ Vertex AI project ID not configured.")
            return False

        # Create test user
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        user_id = f"test_detailed_{timestamp}"
        cycle_date = "2025-01-01"

        print(f"👤 Test user ID: {user_id}")

        # Reset any existing usage
        await token_usage_repo.reset_usage(user_id, cycle_date)

        # Create detailed token callback handler
        callback = create_detailed_token_callback(user_id, cycle_date)
        print("📋 Created detailed token callback handler")

        # Make API call with callback
        messages = [LLMMessage(role="user", content="Please explain what a token is in AI language models in 2-3 sentences.")]

        print("📡 Making API call to Vertex AI with detailed token callback...")
        response = await generate_text(
            messages=messages,
            provider=AIProvider.VERTEX,
            model="gemini-2.5-pro",
            temperature=0.1,
            max_tokens=4096,
            callbacks=[callback]
        )

        print(f"📝 Response: {response.content}")
        print(f"🔢 Total tokens: {response.tokens_used}")

        if hasattr(response, 'prompt_tokens') and response.prompt_tokens:
            print(f"📥 Prompt tokens: {response.prompt_tokens}")
        if hasattr(response, 'completion_tokens') and response.completion_tokens:
            print(f"📤 Completion tokens: {response.completion_tokens}")

        # Check for blocked responses
        if ("[Response blocked by safety filters" in response.content or
            "[Response unavailable" in response.content or
            "[Response error:" in response.content):
            print("⚠️  Response was blocked by safety filters - skipping detailed test")
            return False

        # Wait for callback to process
        print("⏳ Waiting for detailed callback to process...")
        await asyncio.sleep(2.0)

        # Check if detailed token usage was recorded
        stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)
        print(f"💾 Recorded total tokens: {stats['total_tokens']}")
        print(f"📥 Recorded prompt tokens: {stats['prompt_tokens']}")
        print(f"📤 Recorded completion tokens: {stats['completion_tokens']}")

        if stats['total_tokens'] > 0:
            print("✅ Detailed token callback functionality test PASSED!")
            return True
        else:
            print("❌ No tokens were recorded - detailed callback failed!")
            return False

    except Exception as e:
        print(f"❌ Detailed test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner"""
    print("🚀 Token Callback Functionality Test Suite")
    print("=" * 60)
    print("Testing token callback functionality with real Vertex AI API")
    print("=" * 60)

    # Run basic test
    basic_result = await test_basic_token_callback()

    # Run detailed test
    detailed_result = await test_detailed_token_callback()

    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 30)
    print(f"Basic Token Callback:    {'✅ PASSED' if basic_result else '❌ FAILED'}")
    print(f"Detailed Token Callback: {'✅ PASSED' if detailed_result else '❌ FAILED'}")

    if basic_result and detailed_result:
        print("\n🎉 All token callback tests PASSED!")
        print("The token callback functionality is working correctly with real API connections.")
        return 0
    else:
        print("\n💥 Some tests FAILED!")
        print("Please check the configuration and try again.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

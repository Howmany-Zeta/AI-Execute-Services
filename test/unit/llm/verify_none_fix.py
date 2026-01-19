#!/usr/bin/env python3
"""
Quick verification script to test None messages handling fix.
This script tests the fix without requiring pytest.
"""

import asyncio
import sys
from pathlib import Path

# Add aiecs to path
sys.path.insert(0, str(Path(__file__).parent))

from aiecs.llm.callbacks.custom_callbacks import (
    RedisTokenCallbackHandler,
    DetailedRedisTokenCallbackHandler,
)


async def test_redis_callback_none():
    """Test RedisTokenCallbackHandler with None messages"""
    print("Testing RedisTokenCallbackHandler with None messages...")
    try:
        callback = RedisTokenCallbackHandler(user_id="test-user-123")
        await callback.on_llm_start(None, provider="test", model="test-model")
        print("✓ RedisTokenCallbackHandler handles None messages correctly")
        return True
    except TypeError as e:
        print(f"✗ RedisTokenCallbackHandler FAILED with None: {e}")
        return False


async def test_redis_callback_empty():
    """Test RedisTokenCallbackHandler with empty list"""
    print("Testing RedisTokenCallbackHandler with empty list...")
    try:
        callback = RedisTokenCallbackHandler(user_id="test-user-123")
        await callback.on_llm_start([], provider="test", model="test-model")
        print("✓ RedisTokenCallbackHandler handles empty list correctly")
        return True
    except Exception as e:
        print(f"✗ RedisTokenCallbackHandler FAILED with empty list: {e}")
        return False


async def test_detailed_callback_none():
    """Test DetailedRedisTokenCallbackHandler with None messages"""
    print("Testing DetailedRedisTokenCallbackHandler with None messages...")
    try:
        callback = DetailedRedisTokenCallbackHandler(user_id="test-user-456")
        await callback.on_llm_start(None, provider="test", model="test-model")
        assert callback.prompt_tokens == 0, "Expected prompt_tokens to be 0"
        print("✓ DetailedRedisTokenCallbackHandler handles None messages correctly")
        return True
    except (TypeError, AssertionError) as e:
        print(f"✗ DetailedRedisTokenCallbackHandler FAILED with None: {e}")
        return False


async def test_detailed_callback_empty():
    """Test DetailedRedisTokenCallbackHandler with empty list"""
    print("Testing DetailedRedisTokenCallbackHandler with empty list...")
    try:
        callback = DetailedRedisTokenCallbackHandler(user_id="test-user-456")
        await callback.on_llm_start([], provider="test", model="test-model")
        assert callback.prompt_tokens == 0, "Expected prompt_tokens to be 0"
        print("✓ DetailedRedisTokenCallbackHandler handles empty list correctly")
        return True
    except (TypeError, AssertionError) as e:
        print(f"✗ DetailedRedisTokenCallbackHandler FAILED with empty list: {e}")
        return False


async def test_detailed_callback_valid():
    """Test DetailedRedisTokenCallbackHandler with valid messages"""
    print("Testing DetailedRedisTokenCallbackHandler with valid messages...")
    try:
        callback = DetailedRedisTokenCallbackHandler(user_id="test-user-456")
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        await callback.on_llm_start(messages, provider="test", model="test-model")
        assert callback.prompt_tokens > 0, "Expected prompt_tokens to be > 0"
        print(f"✓ DetailedRedisTokenCallbackHandler handles valid messages correctly (tokens: {callback.prompt_tokens})")
        return True
    except (TypeError, AssertionError) as e:
        print(f"✗ DetailedRedisTokenCallbackHandler FAILED with valid messages: {e}")
        return False


async def test_estimate_prompt_tokens():
    """Test _estimate_prompt_tokens method directly"""
    print("Testing _estimate_prompt_tokens method...")
    try:
        callback = DetailedRedisTokenCallbackHandler(user_id="test-user")

        # Test with None
        tokens_none = callback._estimate_prompt_tokens(None)
        assert tokens_none == 0, f"Expected 0 tokens for None, got {tokens_none}"

        # Test with empty list
        tokens_empty = callback._estimate_prompt_tokens([])
        assert tokens_empty == 0, f"Expected 0 tokens for empty list, got {tokens_empty}"

        # Test with valid messages
        messages = [{"role": "user", "content": "Hello"}]  # 5 chars
        tokens_valid = callback._estimate_prompt_tokens(messages)
        assert tokens_valid == 1, f"Expected 1 token for 'Hello', got {tokens_valid}"

        print("✓ _estimate_prompt_tokens handles all cases correctly")
        return True
    except (TypeError, AssertionError) as e:
        print(f"✗ _estimate_prompt_tokens FAILED: {e}")
        return False


async def test_estimate_prompt_tokens_with_none_content():
    """Test _estimate_prompt_tokens with None content value"""
    print("Testing _estimate_prompt_tokens with None content value...")
    try:
        callback = DetailedRedisTokenCallbackHandler(user_id="test-user")

        # Test with message that has content=None
        messages = [{"role": "user", "content": None}]
        tokens = callback._estimate_prompt_tokens(messages)
        assert tokens == 0, f"Expected 0 tokens for None content, got {tokens}"

        # Test with mixed messages (some with None content)
        messages_mixed = [
            {"role": "user", "content": "Hello"},  # 5 chars
            {"role": "assistant", "content": None},  # None
            {"role": "user", "content": "World"}  # 5 chars
        ]
        tokens_mixed = callback._estimate_prompt_tokens(messages_mixed)
        assert tokens_mixed == 2, f"Expected 2 tokens for mixed, got {tokens_mixed}"

        # Test with message missing content key
        messages_no_content = [{"role": "user"}]
        tokens_no_content = callback._estimate_prompt_tokens(messages_no_content)
        assert tokens_no_content == 0, f"Expected 0 tokens for missing content, got {tokens_no_content}"

        print("✓ _estimate_prompt_tokens handles None content value correctly")
        return True
    except (TypeError, AssertionError) as e:
        print(f"✗ _estimate_prompt_tokens FAILED with None content: {e}")
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Verifying None Messages Handling Fix")
    print("=" * 60)
    print()
    
    results = []
    
    # Run all tests
    results.append(await test_redis_callback_none())
    results.append(await test_redis_callback_empty())
    results.append(await test_detailed_callback_none())
    results.append(await test_detailed_callback_empty())
    results.append(await test_detailed_callback_valid())
    results.append(await test_estimate_prompt_tokens())
    results.append(await test_estimate_prompt_tokens_with_none_content())
    
    print()
    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)
    
    if all(results):
        print("\n✓ All tests PASSED! The fix is working correctly.")
        return 0
    else:
        print("\n✗ Some tests FAILED! Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


"""
Token Callback Functionality Tests

This test file specifically validates the token callback functionality added to client_factory.py:
1. Basic token recording with RedisTokenCallbackHandler
2. Detailed token recording with DetailedRedisTokenCallbackHandler
3. Composite callback handling
4. Token accumulation across multiple calls
5. Error handling and resilience
6. Real API integration testing

Note: These tests require valid API keys and Redis to be configured.
"""

import asyncio
import pytest
import logging
from typing import List, Dict, Any
from datetime import datetime

# Import LLM components
from app.llm.base_client import LLMMessage, LLMResponse
from app.llm.client_factory import (
    LLMClientManager,
    LLMClientFactory,
    AIProvider,
    generate_text,
    stream_text,
    get_llm_manager
)
from app.core.config import get_settings

# Import token callback components
from app.llm.custom_callbacks import (
    RedisTokenCallbackHandler,
    DetailedRedisTokenCallbackHandler,
    CompositeCallbackHandler,
    create_token_callback,
    create_detailed_token_callback,
    create_composite_callback
)
from app.utils.token_usage_repository import token_usage_repo
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

class TestTokenCallbackCore:
    """Core token callback functionality tests"""

    @pytest.fixture
    async def setup_redis(self):
        """Setup Redis for testing"""
        try:
            # Test Redis connection
            client = await redis_client.get_client()
            await client.ping()
            logger.info("✅ Redis connection established for testing")
            yield
        except Exception as e:
            pytest.skip(f"Redis not available for testing: {str(e)}")

    @pytest.fixture
    def test_user_data(self):
        """Provide test user data"""
        return {
            "user_id": f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "cycle_date": "2025-01-01"
        }

    @pytest.mark.asyncio
    async def test_redis_token_callback_creation(self, test_user_data):
        """Test RedisTokenCallbackHandler creation and validation"""
        user_id = test_user_data["user_id"]
        cycle_date = test_user_data["cycle_date"]

        # Test valid creation
        callback = RedisTokenCallbackHandler(user_id, cycle_date)
        assert callback.user_id == user_id
        assert callback.cycle_start_date == cycle_date
        assert callback.start_time is None
        assert callback.messages is None

        # Test invalid creation (empty user_id)
        with pytest.raises(ValueError, match="user_id must be provided"):
            RedisTokenCallbackHandler("", cycle_date)

        # Test creation without cycle_date
        callback_no_cycle = RedisTokenCallbackHandler(user_id)
        assert callback_no_cycle.user_id == user_id
        assert callback_no_cycle.cycle_start_date is None

        logger.info("✅ RedisTokenCallbackHandler creation tests passed")

    @pytest.mark.asyncio
    async def test_detailed_token_callback_creation(self, test_user_data):
        """Test DetailedRedisTokenCallbackHandler creation and validation"""
        user_id = test_user_data["user_id"]
        cycle_date = test_user_data["cycle_date"]

        # Test valid creation
        callback = DetailedRedisTokenCallbackHandler(user_id, cycle_date)
        assert callback.user_id == user_id
        assert callback.cycle_start_date == cycle_date
        assert callback.start_time is None
        assert callback.messages is None
        assert callback.prompt_tokens == 0

        # Test invalid creation (empty user_id)
        with pytest.raises(ValueError, match="user_id must be provided"):
            DetailedRedisTokenCallbackHandler("", cycle_date)

        logger.info("✅ DetailedRedisTokenCallbackHandler creation tests passed")

    @pytest.mark.asyncio
    async def test_composite_callback_creation(self, test_user_data):
        """Test CompositeCallbackHandler creation and management"""
        user_id = test_user_data["user_id"]
        cycle_date = test_user_data["cycle_date"]

        # Create individual callbacks
        callback1 = create_token_callback(user_id + "_1", cycle_date)
        callback2 = create_detailed_token_callback(user_id + "_2", cycle_date)

        # Test composite creation
        composite = CompositeCallbackHandler([callback1, callback2])
        assert len(composite.handlers) == 2

        # Test adding handlers
        callback3 = create_token_callback(user_id + "_3", cycle_date)
        composite.add_handler(callback3)
        assert len(composite.handlers) == 3

        # Test empty composite
        empty_composite = CompositeCallbackHandler([])
        assert len(empty_composite.handlers) == 0

        # Test convenience function
        convenience_composite = create_composite_callback(callback1, callback2)
        assert len(convenience_composite.handlers) == 2

        logger.info("✅ CompositeCallbackHandler creation tests passed")


class TestTokenCallbackWithRealAPIs:
    """Test token callback functionality with real API calls"""

    @pytest.fixture
    async def setup_redis(self):
        """Setup Redis for testing"""
        try:
            client = await redis_client.get_client()
            await client.ping()
            yield
        except Exception as e:
            pytest.skip(f"Redis not available for testing: {str(e)}")

    @pytest.fixture
    def test_user_data(self):
        """Provide unique test user data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        return {
            "user_id": f"test_callback_{timestamp}",
            "cycle_date": "2025-01-01"
        }

    @pytest.mark.asyncio
    async def test_basic_token_callback_with_vertex_ai(self, setup_redis, test_user_data):
        """Test basic token callback functionality with Vertex AI"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create token callback handler
            callback = create_token_callback(user_id, cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Hello! Please respond with exactly 'Token test successful' to confirm.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0
            assert response.provider == "Vertex"

            # Skip test if response was blocked by safety filters
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content):
                pytest.skip("Vertex AI response was blocked - cannot test token callback")

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded"
            assert stats["total_tokens"] == response.tokens_used, f"Recorded tokens ({stats['total_tokens']}) should match response ({response.tokens_used})"

            logger.info(f"✅ Vertex AI basic token callback test successful. Recorded {stats['total_tokens']} tokens")
            print(f"✅ Vertex AI token callback working. Response: '{response.content[:50]}...', Tokens: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"Vertex AI token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_detailed_token_callback_with_vertex_ai(self, setup_redis, test_user_data):
        """Test detailed token callback functionality with Vertex AI"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create detailed token callback handler
            callback = create_detailed_token_callback(user_id, cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Please explain what a token is in the context of AI language models in one sentence.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0

            # Skip test if response was blocked by safety filters
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content):
                pytest.skip("Vertex AI response was blocked - cannot test token callback")

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if detailed token usage was recorded
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Total token usage should be recorded"
            assert stats["prompt_tokens"] >= 0, "Prompt tokens should be recorded"
            assert stats["completion_tokens"] >= 0, "Completion tokens should be recorded"

            # Verify the sum makes sense
            recorded_sum = stats["prompt_tokens"] + stats["completion_tokens"]
            assert recorded_sum > 0, "Sum of prompt and completion tokens should be positive"

            logger.info(f"✅ Vertex AI detailed token callback test successful. Total: {stats['total_tokens']}, Prompt: {stats['prompt_tokens']}, Completion: {stats['completion_tokens']}")
            print(f"✅ Vertex AI detailed token callback working. Total: {stats['total_tokens']}, Prompt: {stats['prompt_tokens']}, Completion: {stats['completion_tokens']}")

        except Exception as e:
            pytest.fail(f"Vertex AI detailed token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_callback_with_xai(self, setup_redis, test_user_data):
        """Test token callback functionality with xAI API"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create token callback handler
            callback = create_token_callback(user_id, cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Hello Grok! Please respond with 'xAI callback test successful' to confirm connectivity.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.XAI,
                model="grok-2",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0
            assert response.provider == "xAI"

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded"
            assert stats["total_tokens"] == response.tokens_used, f"Recorded tokens ({stats['total_tokens']}) should match response ({response.tokens_used})"

            logger.info(f"✅ xAI token callback test successful. Recorded {stats['total_tokens']} tokens")
            print(f"✅ xAI token callback working. Response: '{response.content[:50]}...', Tokens: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"xAI token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_callback_with_vertex_ai(self, setup_redis, test_user_data):
        """Test token callback functionality with Vertex AI"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create detailed token callback handler (better for Vertex AI)
            callback = create_detailed_token_callback(user_id, cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Hello Gemini! Please respond with a simple greeting to confirm connectivity.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0
            assert response.provider == "Vertex"

            # Skip test if response was blocked by safety filters
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content):
                pytest.skip("Vertex AI response was blocked - cannot test token callback")

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded"
            assert stats["prompt_tokens"] >= 0, "Prompt tokens should be recorded"
            assert stats["completion_tokens"] >= 0, "Completion tokens should be recorded"

            logger.info(f"✅ Vertex AI token callback test successful. Total: {stats['total_tokens']}, Prompt: {stats['prompt_tokens']}, Completion: {stats['completion_tokens']}")
            print(f"✅ Vertex AI token callback working. Response: '{response.content[:50]}...', Total: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"Vertex AI token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_streaming_with_token_callback(self, setup_redis, test_user_data):
        """Test token callback functionality with streaming responses"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create token callback handler
            callback = create_token_callback(user_id, cycle_date)

            # Make streaming LLM call with callback
            messages = [LLMMessage(role="user", content="Count from 1 to 5, one number per line.")]

            chunks = []
            async for chunk in stream_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            ):
                chunks.append(chunk)
                if len(chunks) > 30:  # Prevent infinite loops
                    break

            # Validate streaming response
            assert len(chunks) > 0, "Should receive streaming chunks"
            full_response = "".join(chunks)
            assert len(full_response) > 0

            # Skip test if response was blocked by safety filters
            if ("[Response blocked by safety filters" in full_response or
                "[Response unavailable" in full_response or
                "[Response error:" in full_response):
                pytest.skip("Vertex AI streaming response was blocked - cannot test token callback")

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded for streaming
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded for streaming"

            logger.info(f"✅ Vertex AI streaming token callback test successful. Received {len(chunks)} chunks, recorded {stats['total_tokens']} tokens")
            print(f"✅ Vertex AI streaming token callback working. Chunks: {len(chunks)}, Tokens: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"Vertex AI streaming token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_multiple_callbacks_composite(self, setup_redis, test_user_data):
        """Test multiple callbacks using CompositeCallbackHandler"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            base_user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Create test users
            user_id_1 = f"{base_user_id}_composite_1"
            user_id_2 = f"{base_user_id}_composite_2"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id_1, cycle_date)
            await token_usage_repo.reset_usage(user_id_2, cycle_date)

            # Create multiple callback handlers
            callback1 = create_token_callback(user_id_1, cycle_date)
            callback2 = create_detailed_token_callback(user_id_2, cycle_date)

            # Create composite callback
            composite_callback = create_composite_callback(callback1, callback2)

            # Make LLM call with composite callback
            messages = [LLMMessage(role="user", content="Hello! Please respond with 'Composite callback test successful'.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[composite_callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0

            # Wait for callbacks to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded for both users
            stats1 = await token_usage_repo.get_usage_stats(user_id_1, cycle_date)
            stats2 = await token_usage_repo.get_usage_stats(user_id_2, cycle_date)

            assert stats1["total_tokens"] > 0, "Token usage should be recorded for user 1"
            assert stats2["total_tokens"] > 0, "Token usage should be recorded for user 2"

            # Both should have the same total (same response)
            assert stats1["total_tokens"] == stats2["total_tokens"], f"Both users should have same token count: {stats1['total_tokens']} vs {stats2['total_tokens']}"

            logger.info(f"✅ Composite callback test successful. Both users recorded {stats1['total_tokens']} tokens")
            print(f"✅ Composite callback working. Both users recorded: {stats1['total_tokens']} tokens")

        except Exception as e:
            pytest.fail(f"Composite callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_accumulation_across_calls(self, setup_redis, test_user_data):
        """Test that token usage accumulates correctly across multiple calls"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create token callback handler
            callback = create_token_callback(user_id, cycle_date)

            # Make multiple LLM calls
            total_expected_tokens = 0
            num_calls = 3
            responses = []

            for i in range(num_calls):
                messages = [LLMMessage(role="user", content=f"Call {i+1}: Please respond with 'Call {i+1} successful'.")]

                response = await generate_text(
                    messages=messages,
                    provider=AIProvider.VERTEX,
                    model="gemini-2.5-pro",
                    temperature=0.1,
                    max_tokens=4096,
                    callbacks=[callback]
                )

                assert isinstance(response, LLMResponse)
                assert response.tokens_used > 0
                total_expected_tokens += response.tokens_used
                responses.append(response)

                # Small delay between calls
                await asyncio.sleep(0.5)

            # Wait for final callback to process
            await asyncio.sleep(1.0)

            # Check if token usage accumulated correctly
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] == total_expected_tokens, f"Expected {total_expected_tokens}, got {stats['total_tokens']}"

            logger.info(f"✅ Token accumulation test successful. {num_calls} calls, total: {stats['total_tokens']} tokens")
            print(f"✅ Token accumulation working. {num_calls} calls, individual tokens: {[r.tokens_used for r in responses]}, total: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"Token accumulation test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_callback_error_resilience(self, setup_redis, test_user_data):
        """Test that callback errors don't break LLM calls"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Test invalid callback creation
            with pytest.raises(ValueError, match="user_id must be provided"):
                RedisTokenCallbackHandler("")

            # Create valid callback
            callback = create_token_callback(user_id, cycle_date)

            # Make LLM call - should succeed even if callback has potential issues
            messages = [LLMMessage(role="user", content="Hello! Please respond with 'Error resilience test successful'.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # LLM call should succeed regardless of callback issues
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0

            logger.info("✅ Callback error resilience test successful")
            print(f"✅ Callback error resilience working. Response: '{response.content[:50]}...', Tokens: {response.tokens_used}")

        except Exception as e:
            pytest.fail(f"Callback error resilience test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_llm_manager_with_callbacks(self, setup_redis, test_user_data):
        """Test LLMClientManager with token callbacks"""
        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            user_id = test_user_data["user_id"]
            cycle_date = test_user_data["cycle_date"]

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Get LLM manager
            manager = await get_llm_manager()

            # Create token callback handler
            callback = create_token_callback(user_id, cycle_date)

            # Make LLM call through manager with callback
            messages = [LLMMessage(role="user", content="Hello LLM Manager! Please respond with 'Manager callback test successful'.")]

            response = await manager.generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=4096,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.tokens_used > 0

            # Wait for callback to process
            await asyncio.sleep(1.0)

            # Check if token usage was recorded
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded"
            assert stats["total_tokens"] == response.tokens_used, f"Recorded tokens should match response"

            logger.info(f"✅ LLM Manager callback test successful. Recorded {stats['total_tokens']} tokens")
            print(f"✅ LLM Manager callback working. Response: '{response.content[:50]}...', Tokens: {stats['total_tokens']}")

        except Exception as e:
            pytest.fail(f"LLM Manager callback test failed: {str(e)}")


class TestTokenCallbackIntegration:
    """Integration tests for token callback functionality"""

    @pytest.fixture
    async def setup_redis(self):
        """Setup Redis for testing"""
        try:
            client = await redis_client.get_client()
            await client.ping()
            yield
        except Exception as e:
            pytest.skip(f"Redis not available for testing: {str(e)}")

    @pytest.mark.asyncio
    async def test_end_to_end_token_callback_workflow(self, setup_redis):
        """Test complete end-to-end token callback workflow"""
        try:
            settings = get_settings()

            # Check available providers (prioritize Vertex AI)
            available_providers = []
            if settings.vertex_project_id:
                available_providers.append(("Vertex", AIProvider.VERTEX, "gemini-2.5-pro"))

            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)
            if xai_key:
                available_providers.append(("xAI", AIProvider.XAI, "grok-2"))

            if settings.openai_api_key:
                available_providers.append(("OpenAI", AIProvider.OPENAI, "gpt-4o-mini"))

            if not available_providers:
                pytest.skip("No API keys configured for end-to-end testing")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            base_user_id = f"e2e_test_{timestamp}"
            cycle_date = "2025-01-01"

            successful_tests = []

            for provider_name, provider_enum, model in available_providers:
                try:
                    user_id = f"{base_user_id}_{provider_name.lower()}"

                    # Reset usage
                    await token_usage_repo.reset_usage(user_id, cycle_date)

                    # Create callback
                    callback = create_detailed_token_callback(user_id, cycle_date)

                    # Make API call
                    messages = [LLMMessage(role="user", content=f"Hello {provider_name}! Please respond with 'E2E test successful for {provider_name}'.")]

                    response = await generate_text(
                        messages=messages,
                        provider=provider_enum,
                        model=model,
                        temperature=0.1,
                        max_tokens=4096,
                        callbacks=[callback]
                    )

                    # Validate response
                    assert isinstance(response, LLMResponse)
                    assert response.content is not None
                    assert len(response.content) > 0
                    assert response.tokens_used > 0
                    assert response.provider == provider_name

                    # Skip Vertex AI if response was blocked
                    if (provider_name == "Vertex" and
                        ("[Response blocked by safety filters" in response.content or
                         "[Response unavailable" in response.content or
                         "[Response error:" in response.content)):
                        logger.warning(f"Vertex AI response was blocked, skipping: {response.content}")
                        continue

                    # Wait for callback
                    await asyncio.sleep(1.0)

                    # Check token recording
                    stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)
                    assert stats["total_tokens"] > 0, f"Token usage should be recorded for {provider_name}"

                    successful_tests.append({
                        "provider": provider_name,
                        "tokens": stats["total_tokens"],
                        "response_preview": response.content[:50]
                    })

                    logger.info(f"✅ {provider_name} E2E test successful. Tokens: {stats['total_tokens']}")

                except Exception as e:
                    logger.warning(f"E2E test failed for {provider_name}: {str(e)}")
                    continue

            # At least one provider should work
            assert len(successful_tests) > 0, f"No providers worked in E2E test. Tried: {[p[0] for p in available_providers]}"

            print(f"✅ End-to-end token callback tests successful for {len(successful_tests)} providers:")
            for test in successful_tests:
                print(f"  - {test['provider']}: {test['tokens']} tokens, response: '{test['response_preview']}...'")

        except Exception as e:
            pytest.fail(f"End-to-end token callback test failed: {str(e)}")


# Standalone test runner
if __name__ == "__main__":
    async def run_basic_test():
        """Run a basic token callback test"""
        print("🧪 Running basic token callback functionality test...")

        try:
            settings = get_settings()
            if not settings.vertex_project_id:
                print("❌ Vertex AI project ID not configured. Set VERTEX_PROJECT_ID environment variable.")
                return

            # Test Redis connection
            try:
                client = await redis_client.get_client()
                await client.ping()
                print("✅ Redis connection successful")
            except Exception as e:
                print(f"❌ Redis connection failed: {e}")
                return

            # Create test user
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            user_id = f"standalone_test_{timestamp}"
            cycle_date = "2025-01-01"

            # Reset usage
            await token_usage_repo.reset_usage(user_id, cycle_date)

            # Create callback
            callback = create_token_callback(user_id, cycle_date)

            # Make API call
            messages = [LLMMessage(role="user", content="Hello! Please respond with 'Standalone test successful'.")]

            print("📡 Making API call with token callback...")
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

            # Wait for callback
            await asyncio.sleep(1.0)

            # Check recording
            stats = await token_usage_repo.get_usage_stats(user_id, cycle_date)
            print(f"💾 Recorded tokens: {stats['total_tokens']}")

            if stats['total_tokens'] == response.tokens_used:
                print("✅ Token callback functionality test PASSED!")
            else:
                print(f"❌ Token callback test FAILED! Expected {response.tokens_used}, got {stats['total_tokens']}")

        except Exception as e:
            print(f"❌ Standalone test failed: {e}")
            import traceback
            traceback.print_exc()

    # Run the test
    asyncio.run(run_basic_test())

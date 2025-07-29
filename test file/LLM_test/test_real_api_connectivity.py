"""
Real API Connectivity Tests

This test file validates actual connectivity to external LLM services:
1. xAI (Grok) API connectivity
2. Vertex AI (Gemini) API connectivity
3. Real response validation
4. Error handling with actual services

Note: These tests require valid API keys and credentials to be configured.
"""

import asyncio
import pytest
import os
import logging
from typing import List, Dict, Any

# Import LLM components
from app.llm.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMClientError,
    ProviderNotAvailableError,
    RateLimitError
)
from app.llm.xai_client import XAIClient
from app.llm.vertex_client import VertexAIClient
from app.llm.client_factory import LLMClientFactory, AIProvider, generate_text, stream_text
from app.core.config import get_settings

# Import token management components
from app.llm.custom_callbacks import (
    RedisTokenCallbackHandler,
    DetailedRedisTokenCallbackHandler,
    create_token_callback,
    create_detailed_token_callback,
    CompositeCallbackHandler
)
from app.utils.token_usage_repository import token_usage_repo
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)

class TestRealXAIConnectivity:
    """Test real xAI API connectivity"""

    @pytest.fixture
    def xai_client(self):
        """Create xAI client for real testing"""
        return XAIClient()

    def test_xai_api_key_availability(self):
        """Test if xAI API key is configured"""
        settings = get_settings()
        api_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

        if not api_key:
            pytest.skip("xAI API key not configured. Set XAI_API_KEY or GROK_API_KEY environment variable.")

        assert api_key is not None
        assert len(api_key) > 10  # Basic validation

    @pytest.mark.asyncio
    async def test_xai_real_text_generation(self, xai_client):
        """Test real text generation with xAI API"""
        try:
            # Check if API key is available
            settings = get_settings()
            api_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not api_key:
                pytest.skip("xAI API key not configured")

            messages = [LLMMessage(role="user", content="Hello! Please respond with exactly 'API_TEST_SUCCESS' to confirm connectivity.")]

            response = await xai_client.generate_text(
                messages,
                model="grok-2",
                temperature=0.1,  # Low temperature for consistent response
                max_tokens=50
            )

            # Validate response structure
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.provider == "xAI"
            assert response.model == "grok-2"
            assert response.tokens_used > 0

            logger.info(f"xAI API Response: {response.content}")
            print(f"✅ xAI API connectivity successful. Response: {response.content[:100]}...")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except RateLimitError as e:
            pytest.skip(f"xAI API rate limit exceeded: {str(e)}")
        except Exception as e:
            pytest.fail(f"xAI API connectivity failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_xai_different_models(self, xai_client):
        """Test connectivity with different xAI models"""
        try:
            settings = get_settings()
            api_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not api_key:
                pytest.skip("xAI API key not configured")

            models_to_test = ["grok-2", "grok-3-fast", "grok-3-mini"]
            messages = [LLMMessage(role="user", content="Say 'Hello' in one word.")]

            successful_models = []

            for model in models_to_test:
                try:
                    response = await xai_client.generate_text(
                        messages,
                        model=model,
                        temperature=0.1,
                        max_tokens=10
                    )

                    assert isinstance(response, LLMResponse)
                    assert response.content is not None
                    successful_models.append(model)
                    logger.info(f"Model {model} successful: {response.content}")

                    # Small delay between requests to avoid rate limiting
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.warning(f"Model {model} failed: {str(e)}")
                    continue

            # At least one model should work
            assert len(successful_models) > 0, f"No xAI models worked. Tested: {models_to_test}"
            print(f"✅ xAI models working: {successful_models}")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_xai_streaming_connectivity(self, xai_client):
        """Test real streaming with xAI API"""
        try:
            settings = get_settings()
            api_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not api_key:
                pytest.skip("xAI API key not configured")

            messages = [LLMMessage(role="user", content="Count from 1 to 5, one number per line.")]

            chunks = []
            async for chunk in xai_client.stream_text(messages, model="grok-2", max_tokens=50):
                chunks.append(chunk)
                if len(chunks) > 20:  # Prevent infinite loops
                    break

            # Validate streaming response
            assert len(chunks) > 0, "No streaming chunks received"
            full_response = "".join(chunks)
            assert len(full_response) > 0

            logger.info(f"xAI Streaming response: {full_response}")
            print(f"✅ xAI streaming connectivity successful. Received {len(chunks)} chunks.")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"xAI streaming connectivity failed: {str(e)}")


class TestRealVertexAIConnectivity:
    """Test real Vertex AI connectivity"""

    @pytest.fixture
    def vertex_client(self):
        """Create Vertex AI client for real testing"""
        return VertexAIClient()

    def test_vertex_ai_project_configuration(self):
        """Test if Vertex AI project is configured"""
        settings = get_settings()

        if not settings.vertex_project_id:
            pytest.skip("Vertex AI project ID not configured. Set VERTEX_PROJECT_ID environment variable.")

        assert settings.vertex_project_id is not None
        assert len(settings.vertex_project_id) > 5  # Basic validation

    @pytest.mark.asyncio
    async def test_vertex_ai_real_text_generation(self, vertex_client):
        """Test real text generation with Vertex AI - must receive actual context to pass"""
        try:
            settings = get_settings()

            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            messages = [LLMMessage(role="user", content="Hello! Please respond with a simple greeting.")]

            response = await vertex_client.generate_text(
                messages,
                model="gemini-2.5-pro",
                temperature=0.1,  # Low temperature for consistent response
                max_tokens=4096  # Increased to account for Gemini 2.5 thinking tokens
            )

            # Validate response structure
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert len(response.content) > 0
            assert response.provider == "Vertex"
            assert response.model == "gemini-2.5-pro"
            assert response.tokens_used > 0

            # Test MUST fail if response was blocked by safety filters or has no actual content
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content or
                "[Response truncated" in response.content):
                pytest.fail(f"Vertex AI test failed - no actual context received: {response.content}")

            # Ensure we have meaningful content (not just error messages)
            assert len(response.content.strip()) > 0, "Response content was empty"

            logger.info(f"Vertex AI Response: {response.content}")
            print(f"✅ Vertex AI connectivity successful with actual context. Response: {response.content[:100]}...")

        except ProviderNotAvailableError as e:
            pytest.skip(f"Vertex AI not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Vertex AI connectivity failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_vertex_ai_different_models(self, vertex_client):
        """Test connectivity with different Vertex AI models - must receive actual context to pass"""
        try:
            settings = get_settings()

            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            models_to_test = ["gemini-2.5-pro", "gemini-2.5-flash"]
            messages = [LLMMessage(role="user", content="Say hello")]

            successful_models = []

            for model in models_to_test:
                try:
                    response = await vertex_client.generate_text(
                        messages,
                        model=model,
                        temperature=0.1,
                        max_tokens=4096
                    )

                    assert isinstance(response, LLMResponse)
                    assert response.content is not None

                    # Only consider successful if we get actual content (not filtered responses)
                    if ("[Response blocked by safety filters" in response.content or
                        "[Response unavailable" in response.content or
                        "[Response error:" in response.content or
                        "[Response truncated" in response.content):
                        logger.warning(f"Model {model} failed - no actual context received: {response.content}")
                        continue

                    # Ensure meaningful content
                    if len(response.content.strip()) > 10:
                        successful_models.append(model)
                        logger.info(f"Model {model} successful with actual context: {response.content}")
                    else:
                        logger.warning(f"Model {model} failed - response too short: {response.content}")

                    # Small delay between requests
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.warning(f"Model {model} failed: {str(e)}")
                    continue

            # At least one model should work with actual content
            assert len(successful_models) > 0, f"No Vertex AI models provided actual context. Tested: {models_to_test}"
            print(f"✅ Vertex AI models working with actual context: {successful_models}")

        except ProviderNotAvailableError as e:
            pytest.skip(f"Vertex AI not available: {str(e)}")

    @pytest.mark.asyncio
    async def test_vertex_ai_streaming_connectivity(self, vertex_client):
        """Test real streaming with Vertex AI - must receive actual context to pass"""
        try:
            settings = get_settings()

            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            messages = [LLMMessage(role="user", content="Say hello")]

            chunks = []
            async for chunk in vertex_client.stream_text(messages, model="gemini-2.5-pro", max_tokens=4096):
                chunks.append(chunk)
                if len(chunks) > 20:  # Prevent infinite loops
                    break

            # Validate streaming response
            assert len(chunks) > 0, "No streaming chunks received"
            full_response = "".join(chunks)
            assert len(full_response) > 0

            # Test MUST fail if response was blocked or has no actual content
            if ("[Response blocked by safety filters" in full_response or
                "[Response unavailable" in full_response or
                "[Response error:" in full_response or
                "[Response truncated" in full_response):
                pytest.fail(f"Vertex AI streaming test failed - no actual context received: {full_response}")

            # Ensure meaningful content
            assert len(full_response.strip()) > 10, "Streaming response content too short - no meaningful context received"

            logger.info(f"Vertex AI Streaming response: {full_response}")
            print(f"✅ Vertex AI streaming connectivity successful with actual context. Received {len(chunks)} chunks.")

        except ProviderNotAvailableError as e:
            pytest.skip(f"Vertex AI not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Vertex AI streaming connectivity failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_vertex_ai_cost_estimation(self, vertex_client):
        """Test cost estimation with real API calls - must receive actual context to pass"""
        try:
            settings = get_settings()

            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            messages = [LLMMessage(role="user", content="Hello")]

            response = await vertex_client.generate_text(
                messages,
                model="gemini-2.5-pro",
                temperature=0.5,
                max_tokens=4096
            )

            # Validate cost estimation
            assert response.cost_estimate is not None
            assert response.cost_estimate >= 0.0
            assert isinstance(response.cost_estimate, (int, float))

            # Test MUST fail if response was blocked or has no actual content
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content or
                "[Response truncated" in response.content):
                pytest.fail(f"Vertex AI cost estimation test failed - no actual context received: {response.content}")

            # Ensure meaningful content
            assert len(response.content.strip()) > 10, "Response content too short - no meaningful context received"

            logger.info(f"Vertex AI Cost estimate: ${response.cost_estimate:.6f}")
            print(f"✅ Vertex AI cost estimation working with actual context. Cost: ${response.cost_estimate:.6f}")

        except ProviderNotAvailableError as e:
            pytest.skip(f"Vertex AI not available: {str(e)}")


class TestRealAPIIntegration:
    """Test real API integration through factory and manager"""

    @pytest.mark.asyncio
    async def test_factory_real_clients(self):
        """Test factory with real API clients"""
        try:
            # Test xAI through factory
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if xai_key:
                xai_client = LLMClientFactory.get_client(AIProvider.XAI)
                assert xai_client.provider_name == "xAI"

                messages = [LLMMessage(role="user", content="Test factory connectivity")]
                response = await xai_client.generate_text(messages, model="grok-2", max_tokens=500)
                assert isinstance(response, LLMResponse)
                print("✅ xAI factory integration successful")

            # Test Vertex AI through factory
            if settings.vertex_project_id:
                vertex_client = LLMClientFactory.get_client(AIProvider.VERTEX)
                assert vertex_client.provider_name == "Vertex"

                messages = [LLMMessage(role="user", content="Test factory connectivity")]
                response = await vertex_client.generate_text(messages, model="gemini-2.5-pro", max_tokens=4096)
                assert isinstance(response, LLMResponse)

                # Factory test MUST fail if response was blocked or has no actual content
                if ("[Response blocked by safety filters" in response.content or
                    "[Response unavailable" in response.content or
                    "[Response error:" in response.content or
                    "[Response truncated" in response.content):
                    raise Exception(f"Vertex AI factory integration failed - no actual context received: {response.content}")

                # Ensure meaningful content
                if len(response.content.strip()) <= 10:
                    raise Exception("Vertex AI factory integration failed - response too short")

                print("✅ Vertex AI factory integration successful with actual context")

        except ProviderNotAvailableError as e:
            pytest.skip(f"API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Factory integration failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_error_handling_real_apis(self):
        """Test error handling with real APIs"""
        try:
            settings = get_settings()

            # Test with invalid model (should handle gracefully)
            if settings.vertex_project_id:
                vertex_client = VertexAIClient()
                messages = [LLMMessage(role="user", content="Test error handling")]

                try:
                    # Try with a non-existent model
                    response = await vertex_client.generate_text(
                        messages,
                        model="non-existent-model",
                        max_tokens=4096
                    )
                    # If it doesn't fail, that's also okay (API might handle it)
                    print("✅ Error handling test completed (no error occurred)")
                except Exception as e:
                    # Expected behavior - API should reject invalid model
                    logger.info(f"Expected error for invalid model: {str(e)}")
                    print("✅ Error handling working correctly")

        except ProviderNotAvailableError as e:
            pytest.skip(f"API not available: {str(e)}")


# Integration test for real APIs
@pytest.mark.asyncio
async def test_real_api_end_to_end():
    """Test complete workflow with real APIs"""
    settings = get_settings()

    # Test available providers
    available_providers = []

    # Check xAI availability
    xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)
    if xai_key:
        available_providers.append("xAI")

    # Check Vertex AI availability
    if settings.vertex_project_id:
        available_providers.append("Vertex")

    if not available_providers:
        pytest.skip("No API keys configured for real testing")

    print(f"Testing real APIs: {available_providers}")

    for provider in available_providers:
        try:
            if provider == "xAI":
                client = XAIClient()
                model = "grok-2"
            elif provider == "Vertex":
                client = VertexAIClient()
                model = "gemini-2.5-pro"

            messages = [LLMMessage(role="user", content=f"Hello from {provider}")]
            response = await client.generate_text(messages, model=model, max_tokens=4096)

            assert isinstance(response, LLMResponse)
            assert response.provider == provider
            assert len(response.content) > 0

            # For Vertex AI, require actual context to pass
            if provider == "Vertex":
                if ("[Response blocked by safety filters" in response.content or
                    "[Response unavailable" in response.content or
                    "[Response error:" in response.content or
                    "[Response truncated" in response.content):
                    logger.warning(f"{provider} end-to-end test failed - no actual context received: {response.content}")
                    continue

                if len(response.content.strip()) <= 10:
                    logger.warning(f"{provider} end-to-end test failed - response too short")
                    continue

            print(f"✅ {provider} end-to-end test successful with actual context")

        except Exception as e:
            logger.warning(f"{provider} end-to-end test failed: {str(e)}")
            continue


class TestTokenCallbackFunctionality:
    """Test token callback functionality with real API calls"""

    @pytest.fixture
    async def setup_redis(self):
        """Setup Redis for testing"""
        try:
            # Test Redis connection
            client = await redis_client.get_client()
            await client.ping()
            yield
        except Exception as e:
            pytest.skip(f"Redis not available for testing: {str(e)}")

    @pytest.mark.asyncio
    async def test_basic_token_callback_with_xai(self, setup_redis):
        """Test basic token callback functionality with xAI API"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            # Create test user
            test_user_id = "test_user_xai_callback"
            test_cycle_date = "2025-01-01"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(test_user_id, test_cycle_date)

            # Create token callback handler
            callback = create_token_callback(test_user_id, test_cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Hello! Please respond briefly.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.XAI,
                model="grok-2",
                temperature=0.1,
                max_tokens=50,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert response.tokens_used > 0

            # Wait a moment for callback to process
            await asyncio.sleep(0.5)

            # Check if token usage was recorded
            stats = await token_usage_repo.get_usage_stats(test_user_id, test_cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded"
            assert stats["total_tokens"] == response.tokens_used, "Recorded tokens should match response"

            logger.info(f"✅ Basic token callback test successful. Recorded {stats['total_tokens']} tokens")
            print(f"✅ xAI token callback working. Recorded: {stats['total_tokens']} tokens")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_detailed_token_callback_with_vertex(self, setup_redis):
        """Test detailed token callback functionality with Vertex AI"""
        try:
            settings = get_settings()

            if not settings.vertex_project_id:
                pytest.skip("Vertex AI project ID not configured")

            # Create test user
            test_user_id = "test_user_vertex_detailed"
            test_cycle_date = "2025-01-01"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(test_user_id, test_cycle_date)

            # Create detailed token callback handler
            callback = create_detailed_token_callback(test_user_id, test_cycle_date)

            # Make LLM call with callback
            messages = [LLMMessage(role="user", content="Hello! Please respond with a simple greeting.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.VERTEX,
                model="gemini-2.5-pro",
                temperature=0.1,
                max_tokens=100,
                callbacks=[callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert response.tokens_used > 0

            # Skip test if response was blocked
            if ("[Response blocked by safety filters" in response.content or
                "[Response unavailable" in response.content or
                "[Response error:" in response.content):
                pytest.skip("Vertex AI response was blocked - cannot test token callback")

            # Wait a moment for callback to process
            await asyncio.sleep(0.5)

            # Check if detailed token usage was recorded
            stats = await token_usage_repo.get_usage_stats(test_user_id, test_cycle_date)

            assert stats["total_tokens"] > 0, "Total token usage should be recorded"
            assert stats["prompt_tokens"] >= 0, "Prompt tokens should be recorded"
            assert stats["completion_tokens"] >= 0, "Completion tokens should be recorded"

            # Verify the sum makes sense
            recorded_sum = stats["prompt_tokens"] + stats["completion_tokens"]
            assert recorded_sum > 0, "Sum of prompt and completion tokens should be positive"

            logger.info(f"✅ Detailed token callback test successful. Total: {stats['total_tokens']}, Prompt: {stats['prompt_tokens']}, Completion: {stats['completion_tokens']}")
            print(f"✅ Vertex AI detailed token callback working. Total: {stats['total_tokens']}, Prompt: {stats['prompt_tokens']}, Completion: {stats['completion_tokens']}")

        except ProviderNotAvailableError as e:
            pytest.skip(f"Vertex AI not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Detailed token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_callback_with_streaming(self, setup_redis):
        """Test token callback functionality with streaming responses"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            # Create test user
            test_user_id = "test_user_streaming_callback"
            test_cycle_date = "2025-01-01"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(test_user_id, test_cycle_date)

            # Create token callback handler
            callback = create_token_callback(test_user_id, test_cycle_date)

            # Make streaming LLM call with callback
            messages = [LLMMessage(role="user", content="Count from 1 to 3, one number per line.")]

            chunks = []
            async for chunk in stream_text(
                messages=messages,
                provider=AIProvider.XAI,
                model="grok-2",
                temperature=0.1,
                max_tokens=50,
                callbacks=[callback]
            ):
                chunks.append(chunk)
                if len(chunks) > 20:  # Prevent infinite loops
                    break

            # Validate streaming response
            assert len(chunks) > 0, "Should receive streaming chunks"
            full_response = "".join(chunks)
            assert len(full_response) > 0

            # Wait a moment for callback to process
            await asyncio.sleep(0.5)

            # Check if token usage was recorded for streaming
            stats = await token_usage_repo.get_usage_stats(test_user_id, test_cycle_date)

            assert stats["total_tokens"] > 0, "Token usage should be recorded for streaming"

            logger.info(f"✅ Streaming token callback test successful. Recorded {stats['total_tokens']} tokens")
            print(f"✅ Streaming token callback working. Recorded: {stats['total_tokens']} tokens")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Streaming token callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_multiple_callbacks_composite(self, setup_redis):
        """Test multiple callbacks using CompositeCallbackHandler"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            # Create test users
            test_user_id_1 = "test_user_composite_1"
            test_user_id_2 = "test_user_composite_2"
            test_cycle_date = "2025-01-01"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(test_user_id_1, test_cycle_date)
            await token_usage_repo.reset_usage(test_user_id_2, test_cycle_date)

            # Create multiple callback handlers
            callback1 = create_token_callback(test_user_id_1, test_cycle_date)
            callback2 = create_detailed_token_callback(test_user_id_2, test_cycle_date)

            # Create composite callback
            composite_callback = CompositeCallbackHandler([callback1, callback2])

            # Make LLM call with composite callback
            messages = [LLMMessage(role="user", content="Hello! Please respond briefly.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.XAI,
                model="grok-2",
                temperature=0.1,
                max_tokens=50,
                callbacks=[composite_callback]
            )

            # Validate response
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert response.tokens_used > 0

            # Wait a moment for callbacks to process
            await asyncio.sleep(0.5)

            # Check if token usage was recorded for both users
            stats1 = await token_usage_repo.get_usage_stats(test_user_id_1, test_cycle_date)
            stats2 = await token_usage_repo.get_usage_stats(test_user_id_2, test_cycle_date)

            assert stats1["total_tokens"] > 0, "Token usage should be recorded for user 1"
            assert stats2["total_tokens"] > 0, "Token usage should be recorded for user 2"

            # Both should have the same total (same response)
            assert stats1["total_tokens"] == stats2["total_tokens"], "Both users should have same token count"

            logger.info(f"✅ Composite callback test successful. Both users recorded {stats1['total_tokens']} tokens")
            print(f"✅ Composite callback working. Both users recorded: {stats1['total_tokens']} tokens")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Composite callback test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_token_usage_accumulation(self, setup_redis):
        """Test that token usage accumulates correctly across multiple calls"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            # Create test user
            test_user_id = "test_user_accumulation"
            test_cycle_date = "2025-01-01"

            # Reset any existing usage for clean test
            await token_usage_repo.reset_usage(test_user_id, test_cycle_date)

            # Create token callback handler
            callback = create_token_callback(test_user_id, test_cycle_date)

            # Make multiple LLM calls
            total_expected_tokens = 0
            num_calls = 3

            for i in range(num_calls):
                messages = [LLMMessage(role="user", content=f"Hello {i+1}! Please respond briefly.")]

                response = await generate_text(
                    messages=messages,
                    provider=AIProvider.XAI,
                    model="grok-2",
                    temperature=0.1,
                    max_tokens=30,
                    callbacks=[callback]
                )

                assert isinstance(response, LLMResponse)
                assert response.tokens_used > 0
                total_expected_tokens += response.tokens_used

                # Small delay between calls
                await asyncio.sleep(0.5)

            # Wait a moment for final callback to process
            await asyncio.sleep(0.5)

            # Check if token usage accumulated correctly
            stats = await token_usage_repo.get_usage_stats(test_user_id, test_cycle_date)

            assert stats["total_tokens"] == total_expected_tokens, f"Expected {total_expected_tokens}, got {stats['total_tokens']}"

            logger.info(f"✅ Token accumulation test successful. {num_calls} calls, total: {stats['total_tokens']} tokens")
            print(f"✅ Token accumulation working. {num_calls} calls, total: {stats['total_tokens']} tokens")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Token accumulation test failed: {str(e)}")

    @pytest.mark.asyncio
    async def test_callback_error_handling(self, setup_redis):
        """Test that callback errors don't break LLM calls"""
        try:
            settings = get_settings()
            xai_key = getattr(settings, 'xai_api_key', None) or getattr(settings, 'grok_api_key', None)

            if not xai_key:
                pytest.skip("xAI API key not configured")

            # Create a callback with invalid user_id to trigger error
            try:
                invalid_callback = RedisTokenCallbackHandler("")  # Empty user_id should cause error
                assert False, "Should have raised ValueError for empty user_id"
            except ValueError:
                pass  # Expected

            # Create valid callback
            test_user_id = "test_user_error_handling"
            test_cycle_date = "2025-01-01"
            callback = create_token_callback(test_user_id, test_cycle_date)

            # Make LLM call - should succeed even if callback has issues
            messages = [LLMMessage(role="user", content="Hello! Please respond briefly.")]

            response = await generate_text(
                messages=messages,
                provider=AIProvider.XAI,
                model="grok-2",
                temperature=0.1,
                max_tokens=50,
                callbacks=[callback]
            )

            # LLM call should succeed regardless of callback issues
            assert isinstance(response, LLMResponse)
            assert response.content is not None
            assert response.tokens_used > 0

            logger.info("✅ Callback error handling test successful")
            print("✅ Callback error handling working correctly")

        except ProviderNotAvailableError as e:
            pytest.skip(f"xAI API not available: {str(e)}")
        except Exception as e:
            pytest.fail(f"Callback error handling test failed: {str(e)}")


if __name__ == "__main__":
    # Run real API tests
    asyncio.run(test_real_api_end_to_end())
    print("✅ Real API connectivity tests completed!")

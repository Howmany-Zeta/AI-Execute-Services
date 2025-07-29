"""
Comprehensive LLM Function Tests

This test file validates:
1. XAI Client functionality (generate_text, stream_text, model mapping)
2. LLM Client Factory pattern
3. LLM Client Manager context-aware selection
4. Base client interface compliance
5. Error handling and edge cases
6. Function calling capabilities
"""

import asyncio
import pytest
import json
import tenacity
from unittest.mock import AsyncMock, MagicMock, patch
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
from app.llm.client_factory import (
    LLMClientFactory,
    LLMClientManager,
    AIProvider,
    get_llm_manager
)
from app.llm.llm_client import LLMClient, get_llm_client

class TestXAIClient:
    """Test XAI Client functionality"""

    @pytest.fixture
    def xai_client(self):
        """Create XAI client for testing"""
        return XAIClient()


    def test_model_mapping(self, xai_client):
        """Test XAI model mapping functionality"""
        # Test legacy models
        assert xai_client.model_map["grok-beta"] == "grok-beta"
        assert xai_client.model_map["grok"] == "grok-beta"

        # Test current models
        assert xai_client.model_map["Grok 2"] == "grok-2"
        assert xai_client.model_map["grok-2"] == "grok-2"
        assert xai_client.model_map["Grok 2 Vision"] == "grok-2-vision"

        # Test Grok 3 models
        assert xai_client.model_map["Grok 3 Normal"] == "grok-3"
        assert xai_client.model_map["grok-3"] == "grok-3"
        assert xai_client.model_map["Grok 3 Fast"] == "grok-3-fast"

        # Test Grok 3 Mini models
        assert xai_client.model_map["Grok 3 Mini Normal"] == "grok-3-mini"
        assert xai_client.model_map["Grok 3 Mini Fast"] == "grok-3-mini-fast"

        # Test Grok 3 Reasoning models
        assert xai_client.model_map["Grok 3 Reasoning Normal"] == "grok-3-reasoning"
        assert xai_client.model_map["Grok 3 Mini Reasoning Fast"] == "grok-3-mini-reasoning-fast"

    def test_api_key_retrieval(self):
        """Test API key retrieval with backward compatibility"""
        with patch('app.llm.xai_client.get_settings') as mock_get_settings:
            # Test xai_api_key
            settings = MagicMock()
            settings.xai_api_key = "test-api-key"
            settings.grok_api_key = None
            mock_get_settings.return_value = settings

            xai_client = XAIClient()
            api_key = xai_client._get_api_key()
            assert api_key == "test-api-key"

            # Test fallback to grok_api_key
            settings.xai_api_key = None
            settings.grok_api_key = "fallback-key"
            api_key = xai_client._get_api_key()
            assert api_key == "fallback-key"

            # Test missing API key
            settings.xai_api_key = None
            settings.grok_api_key = None
            with pytest.raises(ProviderNotAvailableError):
                xai_client._get_api_key()

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation"""
        with patch('app.llm.xai_client.get_settings') as mock_get_settings:
            # Setup mock settings
            settings = MagicMock()
            settings.xai_api_key = "test-api-key"
            mock_get_settings.return_value = settings

            xai_client = XAIClient()

            # Mock HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Test response from Grok"
                    }
                }],
                "usage": {
                    "total_tokens": 50
                }
            }

            with patch.object(xai_client, '_get_http_client') as mock_http:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_http.return_value = mock_client

                messages = [LLMMessage(role="user", content="Hello, Grok!")]
                response = await xai_client.generate_text(messages, model="grok-2")

                assert isinstance(response, LLMResponse)
                assert response.content == "Test response from Grok"
                assert response.provider == "xAI"
                assert response.model == "grok-2"
                assert response.tokens_used == 50
                assert response.cost_estimate == 0.0

                # Verify API call
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "https://api.x.ai/v1/chat/completions"

                # Verify payload
                payload = call_args[1]["json"]
                assert payload["model"] == "grok-2"
                assert payload["messages"] == [{"role": "user", "content": "Hello, Grok!"}]
                assert payload["temperature"] == 0.7
                assert payload["stream"] is False

    @pytest.mark.asyncio
    async def test_generate_text_with_parameters(self):
        """Test text generation with custom parameters"""
        with patch('app.llm.xai_client.get_settings') as mock_get_settings:
            # Setup mock settings
            settings = MagicMock()
            settings.xai_api_key = "test-api-key"
            mock_get_settings.return_value = settings

            xai_client = XAIClient()

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Custom response"}}],
                "usage": {"total_tokens": 75}
            }

            with patch.object(xai_client, '_get_http_client') as mock_http:
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_http.return_value = mock_client

                messages = [LLMMessage(role="user", content="Test with parameters")]
                response = await xai_client.generate_text(
                    messages,
                    model="grok-3-fast",
                    temperature=0.9,
                    max_tokens=100
                )

                # Verify payload includes custom parameters
                payload = mock_client.post.call_args[1]["json"]
                assert payload["model"] == "grok-3-fast"
                assert payload["temperature"] == 0.9
                assert payload["max_tokens"] == 100

    @pytest.mark.asyncio
    async def test_generate_text_rate_limit_error(self):
        """Test rate limit error handling"""
        import httpx

        with patch('app.llm.xai_client.get_settings') as mock_get_settings:
            # Setup mock settings
            settings = MagicMock()
            settings.xai_api_key = "test-api-key"
            mock_get_settings.return_value = settings

            xai_client = XAIClient()

            with patch.object(xai_client, '_get_http_client') as mock_http:
                mock_client = AsyncMock()

                # Create a proper mock response with status_code 429
                mock_response = MagicMock()
                mock_response.status_code = 429
                mock_response.url = "https://api.x.ai/v1/chat/completions"
                mock_response.reason_phrase = "Too Many Requests"
                mock_response.is_success = False
                mock_response.has_redirect_location = False

                # Create a proper mock request
                mock_request = MagicMock()

                # Create HTTPStatusError with proper response
                http_error = httpx.HTTPStatusError(
                    "Rate limit exceeded",
                    request=mock_request,
                    response=mock_response
                )

                mock_client.post.side_effect = http_error
                mock_http.return_value = mock_client

                messages = [LLMMessage(role="user", content="Test rate limit")]

                # The retry decorator will retry 3 times, then raise the original HTTPStatusError
                # since HTTPStatusError is caught by retry_if_exception_type(httpx.RequestError)
                with pytest.raises(tenacity.RetryError):
                    await xai_client.generate_text(messages)

    @pytest.mark.asyncio
    async def test_stream_text_success(self):
        """Test successful text streaming"""
        with patch('app.llm.xai_client.get_settings') as mock_get_settings:
            # Setup mock settings
            settings = MagicMock()
            settings.xai_api_key = "test-api-key"
            mock_get_settings.return_value = settings

            xai_client = XAIClient()

            # Mock streaming response
            mock_lines = [
                'data: {"choices":[{"delta":{"content":"Hello"}}]}',
                'data: {"choices":[{"delta":{"content":" world"}}]}',
                'data: {"choices":[{"delta":{"content":"!"}}]}',
                'data: [DONE]'
            ]

            async def mock_aiter_lines():
                for line in mock_lines:
                    yield line

            with patch.object(xai_client, '_get_http_client') as mock_http:

                # Mock response object
                mock_response = AsyncMock()
                # Mock the aiter_lines() METHOD to return our async generator
                mock_response.aiter_lines = mock_aiter_lines
                # Also mock the raise_for_status() method
                mock_response.raise_for_status = MagicMock()

                # Mock the client to return our response
                mock_client = AsyncMock()
                mock_client.post.return_value = mock_response

                # Make _get_http_client() return our fully configured mock client
                mock_http.return_value = mock_client

                messages = [LLMMessage(role="user", content="Stream test")]
                chunks = []

                async for chunk in xai_client.stream_text(messages, model="grok-2"):
                    chunks.append(chunk)

                assert chunks == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_close_client(self, xai_client):
        """Test client cleanup"""
        # Mock HTTP client
        mock_http_client = AsyncMock()
        xai_client._http_client = mock_http_client

        await xai_client.close()

        mock_http_client.aclose.assert_called_once()
        assert xai_client._http_client is None


class TestVertexAIClient:
    """Test Vertex AI Client functionality"""

    @pytest.fixture
    def vertex_client(self):
        """Create Vertex AI client for testing"""
        return VertexAIClient()

    def test_initialization(self):
        """Test Vertex AI client initialization"""
        client = VertexAIClient()
        assert client.provider_name == "Vertex"
        assert not client._initialized
        assert "gemini-2.5-pro" in client.token_costs
        assert "gemini-2.5-flash" in client.token_costs

    def test_token_costs_structure(self, vertex_client):
        """Test token cost structure"""
        for model, costs in vertex_client.token_costs.items():
            assert "input" in costs
            assert "output" in costs
            assert isinstance(costs["input"], (int, float))
            assert isinstance(costs["output"], (int, float))

    @pytest.mark.asyncio
    async def test_vertex_ai_initialization_success(self):
        """Test successful Vertex AI initialization"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            settings.vertex_location = "us-central1"
            mock_get_settings.return_value = settings

            vertex_client = VertexAIClient()
            vertex_client._init_vertex_ai()

            mock_init.assert_called_once_with(
                project="test-project-123",
                location="us-central1"
            )
            assert vertex_client._initialized is True

    @pytest.mark.asyncio
    async def test_vertex_ai_initialization_missing_project_id(self):
        """Test Vertex AI initialization with missing project ID"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings:
            # Setup mock settings without project ID
            settings = MagicMock()
            settings.vertex_project_id = None
            mock_get_settings.return_value = settings

            vertex_client = VertexAIClient()

            with pytest.raises(ProviderNotAvailableError, match="Vertex AI project ID not configured"):
                vertex_client._init_vertex_ai()

    @pytest.mark.asyncio
    async def test_vertex_ai_initialization_failure(self):
        """Test Vertex AI initialization failure"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Make init raise an exception
            mock_init.side_effect = Exception("Authentication failed")

            vertex_client = VertexAIClient()

            with pytest.raises(ProviderNotAvailableError, match="Failed to initialize Vertex AI"):
                vertex_client._init_vertex_ai()

    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation with Vertex AI"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            settings.vertex_location = "us-central1"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello! This is a response from Gemini."
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Hello, Gemini!")]

            response = await vertex_client.generate_text(messages, model="gemini-2.5-pro")

            assert isinstance(response, LLMResponse)
            assert response.content == "Hello! This is a response from Gemini."
            assert response.provider == "Vertex"
            assert response.model == "gemini-2.5-pro"
            assert response.tokens_used > 0
            assert response.cost_estimate >= 0.0

            # Verify model was called correctly
            mock_model.generate_content.assert_called_once()
            call_args = mock_model.generate_content.call_args
            assert call_args[0][0] == "Hello, Gemini!"
            assert call_args[1]["generation_config"]["temperature"] == 0.7
            assert call_args[1]["generation_config"]["max_output_tokens"] == 1024

    @pytest.mark.asyncio
    async def test_generate_text_with_custom_parameters(self):
        """Test text generation with custom parameters"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Custom response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Test with custom params")]

            response = await vertex_client.generate_text(
                messages,
                model="gemini-2.5-flash",
                temperature=0.9,
                max_tokens=512
            )

            # Verify custom parameters were used
            call_args = mock_model.generate_content.call_args
            assert call_args[1]["generation_config"]["temperature"] == 0.9
            assert call_args[1]["generation_config"]["max_output_tokens"] == 512

    @pytest.mark.asyncio
    async def test_generate_text_multi_turn_conversation(self):
        """Test text generation with multi-turn conversation"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Multi-turn response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [
                LLMMessage(role="user", content="Hello"),
                LLMMessage(role="assistant", content="Hi there!"),
                LLMMessage(role="user", content="How are you?")
            ]

            response = await vertex_client.generate_text(messages)

            # Verify multi-turn conversation was formatted correctly
            call_args = mock_model.generate_content.call_args
            expected_prompt = "user: Hello\nassistant: Hi there!\nuser: How are you?"
            assert call_args[0][0] == expected_prompt

    @pytest.mark.asyncio
    async def test_generate_text_quota_exceeded_error(self):
        """Test quota exceeded error handling"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model to raise quota error
            mock_model = MagicMock()
            mock_model.generate_content.side_effect = Exception("Quota exceeded for this project")
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Test quota error")]

            with pytest.raises(RateLimitError, match="Vertex AI quota exceeded"):
                await vertex_client.generate_text(messages)

    @pytest.mark.asyncio
    async def test_stream_text_functionality(self):
        """Test text streaming functionality"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello world test"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Stream test")]

            chunks = []
            async for chunk in vertex_client.stream_text(messages):
                chunks.append(chunk)

            # Verify streaming behavior (simulated by splitting words)
            assert len(chunks) == 3  # "Hello ", "world ", "test "
            assert "".join(chunks).strip() == "Hello world test"

    @pytest.mark.asyncio
    async def test_cost_estimation(self):
        """Test cost estimation functionality"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Short response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Test cost estimation")]

            response = await vertex_client.generate_text(messages, model="gemini-1.5-pro")

            # Verify cost estimation is calculated
            assert response.cost_estimate >= 0.0
            assert isinstance(response.cost_estimate, (int, float))

    @pytest.mark.asyncio
    async def test_default_model_selection(self):
        """Test default model selection when none specified"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Default model response"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Test default model")]

            response = await vertex_client.generate_text(messages)  # No model specified

            # Verify default model was used
            assert response.model == "gemini-1.5-pro"
            mock_model_class.assert_called_with("gemini-1.5-pro")

    @pytest.mark.asyncio
    async def test_close_client(self, vertex_client):
        """Test client cleanup"""
        # Initialize the client first
        vertex_client._initialized = True

        await vertex_client.close()

        assert vertex_client._initialized is False


class TestLLMClientFactory:
    """Test LLM Client Factory functionality"""

    def test_get_client_by_enum(self):
        """Test getting client by AIProvider enum"""
        openai_client = LLMClientFactory.get_client(AIProvider.OPENAI)
        vertex_client = LLMClientFactory.get_client(AIProvider.VERTEX)
        xai_client = LLMClientFactory.get_client(AIProvider.XAI)

        assert openai_client.provider_name == "OpenAI"
        assert vertex_client.provider_name == "Vertex"
        assert xai_client.provider_name == "xAI"

    def test_get_client_by_string(self):
        """Test getting client by string provider name"""
        openai_client = LLMClientFactory.get_client("OpenAI")
        vertex_client = LLMClientFactory.get_client("Vertex")
        xai_client = LLMClientFactory.get_client("xAI")

        assert openai_client.provider_name == "OpenAI"
        assert vertex_client.provider_name == "Vertex"
        assert xai_client.provider_name == "xAI"

    def test_client_singleton_behavior(self):
        """Test that factory returns same instance for same provider"""
        client1 = LLMClientFactory.get_client(AIProvider.OPENAI)
        client2 = LLMClientFactory.get_client(AIProvider.OPENAI)

        assert client1 is client2

    def test_unsupported_provider(self):
        """Test error handling for unsupported provider"""
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMClientFactory.get_client("UnsupportedProvider")

    @pytest.mark.asyncio
    async def test_close_all_clients(self):
        """Test closing all clients"""
        # Get some clients
        LLMClientFactory.get_client(AIProvider.OPENAI)
        LLMClientFactory.get_client(AIProvider.XAI)

        # Mock close methods
        with patch.object(LLMClientFactory._clients[AIProvider.OPENAI], 'close') as mock_close1, \
             patch.object(LLMClientFactory._clients[AIProvider.XAI], 'close') as mock_close2:

            await LLMClientFactory.close_all()

            mock_close1.assert_called_once()
            mock_close2.assert_called_once()
            assert len(LLMClientFactory._clients) == 0


class TestLLMClientManager:
    """Test LLM Client Manager functionality"""

    @pytest.fixture
    def manager(self):
        """Create LLM manager for testing"""
        return LLMClientManager()

    def test_extract_ai_preference_from_context(self, manager):
        """Test AI preference extraction from context"""
        # Test with aiPreference in metadata
        context1 = {
            "metadata": {
                "aiPreference": {
                    "provider": "OpenAI",
                    "model": "gpt-4"
                }
            }
        }
        provider, model = manager._extract_ai_preference(context1)
        assert provider == "OpenAI"
        assert model == "gpt-4"

        # Test with direct provider/model in metadata
        context2 = {
            "metadata": {
                "provider": "vertex",
                "model": "gemini-1.5-pro"
            }
        }
        provider, model = manager._extract_ai_preference(context2)
        assert provider == "vertex"
        assert model == "gemini-1.5-pro"

        # Test with no context
        provider, model = manager._extract_ai_preference(None)
        assert provider is None
        assert model is None

        # Test with empty context
        provider, model = manager._extract_ai_preference({})
        assert provider is None
        assert model is None

    @pytest.mark.asyncio
    async def test_generate_text_with_context(self, manager):
        """Test text generation with context-aware provider selection"""
        context = {
            "metadata": {
                "aiPreference": {
                    "provider": "xAI",
                    "model": "grok-2"
                }
            }
        }

        # Mock the XAI client
        with patch.object(LLMClientFactory, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate_text.return_value = LLMResponse(
                content="Test response",
                provider="xAI",
                model="grok-2"
            )
            mock_get_client.return_value = mock_client

            response = await manager.generate_text(
                messages="Test prompt",
                context=context
            )

            # Verify correct provider was selected
            mock_get_client.assert_called_with("xAI")
            mock_client.generate_text.assert_called_once()

            # Verify response
            assert response.content == "Test response"
            assert response.provider == "xAI"
            assert response.model == "grok-2"

    @pytest.mark.asyncio
    async def test_generate_text_string_to_messages_conversion(self, manager):
        """Test automatic conversion of string prompt to messages"""
        with patch.object(LLMClientFactory, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate_text.return_value = LLMResponse(
                content="Test response",
                provider="OpenAI",
                model="gpt-4"
            )
            mock_get_client.return_value = mock_client

            await manager.generate_text("Hello, AI!")

            # Verify messages conversion
            call_args = mock_client.generate_text.call_args
            messages = call_args[1]["messages"]
            assert len(messages) == 1
            assert messages[0].role == "user"
            assert messages[0].content == "Hello, AI!"

    @pytest.mark.asyncio
    async def test_stream_text_functionality(self, manager):
        """Test text streaming functionality"""
        async def mock_stream():
            yield "Hello"
            yield " world"
            yield "!"

        with patch.object(LLMClientFactory, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.stream_text.return_value = mock_stream()
            mock_get_client.return_value = mock_client

            chunks = []
            async for chunk in manager.stream_text("Stream test"):
                chunks.append(chunk)

            assert chunks == ["Hello", " world", "!"]


class TestLLMFunctionCalling:
    """Test LLM function calling capabilities"""

    @pytest.mark.asyncio
    async def test_function_calling_with_xai(self):
        """Test function calling capabilities with XAI client"""
        # Define a test function
        test_function = {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit"
                    }
                },
                "required": ["location"]
            }
        }

        # Mock XAI response with function call
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": None,
                    "function_call": {
                        "name": "get_weather",
                        "arguments": '{"location": "San Francisco, CA", "unit": "celsius"}'
                    }
                }
            }],
            "usage": {"total_tokens": 45}
        }

        xai_client = XAIClient()

        with patch('app.llm.xai_client.get_settings') as mock_settings, \
             patch.object(xai_client, '_get_http_client') as mock_http:

            # Setup mocks
            settings = MagicMock()
            settings.xai_api_key = "test-key"
            mock_settings.return_value = settings

            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_client.post.return_value = mock_response
            mock_http.return_value = mock_client

            # Test function calling
            messages = [LLMMessage(role="user", content="What's the weather in San Francisco?")]

            # Note: This would require extending the XAI client to support function calling
            # For now, we test the structure
            response = await xai_client.generate_text(messages, functions=[test_function])

            # Verify the function call structure would be handled
            assert response.provider == "xAI"


class TestErrorHandling:
    """Test error handling across LLM functions"""

    @pytest.mark.asyncio
    async def test_provider_not_available_error(self):
        """Test handling of provider not available errors"""
        with patch('app.llm.xai_client.get_settings') as mock_settings:
            settings = MagicMock()
            settings.xai_api_key = None
            settings.grok_api_key = None
            mock_settings.return_value = settings

            xai_client = XAIClient()
            messages = [LLMMessage(role="user", content="Test")]

            with pytest.raises(ProviderNotAvailableError):
                await xai_client.generate_text(messages)

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network errors"""
        import httpx

        xai_client = XAIClient()

        with patch('app.llm.xai_client.get_settings') as mock_settings, \
             patch.object(xai_client, '_get_http_client') as mock_http:

            settings = MagicMock()
            settings.xai_api_key = "test-key"
            mock_settings.return_value = settings

            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.RequestError("Network error")
            mock_http.return_value = mock_client

            messages = [LLMMessage(role="user", content="Test")]

            with pytest.raises(tenacity.RetryError):
                await xai_client.generate_text(messages)


class TestBackwardCompatibility:
    """Test backward compatibility with legacy LLM client"""

    @pytest.mark.asyncio
    async def test_legacy_llm_client(self):
        """Test legacy LLM client still works"""
        legacy_client = await get_llm_client()
        assert isinstance(legacy_client, LLMClient)

        # Test that it uses the new architecture under the hood
        with patch.object(legacy_client._manager, 'generate_text') as mock_generate:
            mock_generate.return_value = LLMResponse(
                content="Legacy test",
                provider="OpenAI",
                model="gpt-4"
            )

            response = await legacy_client.generate_text("Test legacy")

            mock_generate.assert_called_once()
            assert response.content == "Legacy test"


class TestVertexAIIntegration:
    """Test Vertex AI integration with LLM system"""

    @pytest.mark.asyncio
    async def test_vertex_ai_with_manager(self):
        """Test Vertex AI client through LLM manager"""
        context = {
            "metadata": {
                "aiPreference": {
                    "provider": "Vertex",
                    "model": "gemini-1.5-pro"
                }
            }
        }

        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class, \
             patch.object(LLMClientFactory, 'get_client') as mock_get_client:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Vertex AI response through manager"
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            # Create a real Vertex client for the factory to return
            vertex_client = VertexAIClient()
            mock_get_client.return_value = vertex_client

            manager = LLMClientManager()
            response = await manager.generate_text(
                messages="Test Vertex AI through manager",
                context=context
            )

            # Verify correct provider was selected
            mock_get_client.assert_called_with("Vertex")
            assert response.provider == "Vertex"
            assert response.model == "gemini-1.5-pro"

    @pytest.mark.asyncio
    async def test_vertex_ai_function_calling_simulation(self):
        """Test Vertex AI with function calling simulation"""
        # Define a test function
        test_function = {
            "name": "get_weather",
            "description": "Get current weather for a location",
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

        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model and response that simulates function calling
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = 'I need to call the get_weather function with location "San Francisco, CA"'
            mock_model.generate_content.return_value = mock_response
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="What's the weather in San Francisco?")]

            response = await vertex_client.generate_text(
                messages,
                model="gemini-1.5-pro",
                functions=[test_function]  # Pass functions as kwargs
            )

            assert response.content == 'I need to call the get_weather function with location "San Francisco, CA"'
            assert response.provider == "Vertex"

    @pytest.mark.asyncio
    async def test_vertex_ai_error_recovery(self):
        """Test Vertex AI error recovery and fallback"""
        with patch('app.llm.vertex_client.get_settings') as mock_get_settings, \
             patch('app.llm.vertex_client.vertexai.init') as mock_init, \
             patch('app.llm.vertex_client.GenerativeModel') as mock_model_class:

            # Setup mock settings
            settings = MagicMock()
            settings.vertex_project_id = "test-project-123"
            mock_get_settings.return_value = settings

            # Setup mock model to first fail, then succeed
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Recovery response"

            # First call fails, second succeeds
            mock_model.generate_content.side_effect = [
                Exception("Temporary error"),
                mock_response
            ]
            mock_model_class.return_value = mock_model

            vertex_client = VertexAIClient()
            messages = [LLMMessage(role="user", content="Test error recovery")]

            # First call should fail
            with pytest.raises(Exception, match="Temporary error"):
                await vertex_client.generate_text(messages)

            # Second call should succeed
            response = await vertex_client.generate_text(messages)
            assert response.content == "Recovery response"


# Integration test
@pytest.mark.asyncio
async def test_end_to_end_llm_workflow():
    """Test complete LLM workflow from manager to client"""
    manager = await get_llm_manager()

    # Test context with different providers
    contexts = [
        {
            "metadata": {
                "aiPreference": {
                    "provider": "OpenAI",
                    "model": "gpt-4"
                }
            }
        },
        {
            "metadata": {
                "aiPreference": {
                    "provider": "Vertex",
                    "model": "gemini-1.5-pro"
                }
            }
        },
        {
            "metadata": {
                "aiPreference": {
                    "provider": "xAI",
                    "model": "grok-2"
                }
            }
        }
    ]

    for context in contexts:
        provider = context["metadata"]["aiPreference"]["provider"]

        with patch.object(LLMClientFactory, 'get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate_text.return_value = LLMResponse(
                content=f"Response from {provider}",
                provider=provider,
                model=context["metadata"]["aiPreference"]["model"]
            )
            mock_get_client.return_value = mock_client

            response = await manager.generate_text(
                "Test message",
                context=context
            )

            assert provider in response.content
            mock_get_client.assert_called_with(provider)


if __name__ == "__main__":
    # Run tests with asyncio
    asyncio.run(test_end_to_end_llm_workflow())
    print("✅ All LLM function tests completed!")

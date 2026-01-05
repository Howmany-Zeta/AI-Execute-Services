import logging
import os
from typing import Optional, List, AsyncGenerator

from google import genai
from google.genai import types

from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


class GoogleAIClient(BaseLLMClient):
    """Google AI (Gemini) provider client using the new google.genai SDK"""

    def __init__(self):
        super().__init__("GoogleAI")
        self.settings = get_settings()
        self._initialized = False
        self._client: Optional[genai.Client] = None

    def _init_google_ai(self) -> genai.Client:
        """Lazy initialization of Google AI SDK and return the client"""
        if not self._initialized or self._client is None:
            api_key = self.settings.googleai_api_key or os.environ.get("GOOGLEAI_API_KEY")
            if not api_key:
                raise ProviderNotAvailableError("Google AI API key not configured. Set GOOGLEAI_API_KEY.")

            try:
                self._client = genai.Client(api_key=api_key)
                self._initialized = True
                self.logger.info("Google AI SDK (google.genai) initialized successfully.")
            except Exception as e:
                raise ProviderNotAvailableError(f"Failed to initialize Google AI SDK: {str(e)}")

        return self._client

    def _convert_messages_to_contents(
        self, messages: List[LLMMessage]
    ) -> List[types.Content]:
        """Convert LLMMessage list to Google GenAI Content objects."""
        contents = []
        for msg in messages:
            # Map 'assistant' role to 'model' for Google AI
            role = "model" if msg.role == "assistant" else msg.role
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.content)])
            )
        return contents

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using Google AI (google.genai SDK)"""
        client = self._init_google_ai()

        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"

        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Extract system message from messages if not provided
            system_msg = None
            user_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                else:
                    user_messages.append(msg)

            # Use provided system_instruction or extracted system message
            final_system_instruction = system_instruction or system_msg

            # Convert messages to Content objects
            contents = self._convert_messages_to_contents(user_messages)

            # Create GenerateContentConfig with all settings
            config = types.GenerateContentConfig(
                system_instruction=final_system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40),
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="OFF",
                    ),
                ],
            )

            # Use async client for async operations
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            content = response.text
            prompt_tokens = response.usage_metadata.prompt_token_count
            completion_tokens = response.usage_metadata.candidates_token_count
            total_tokens = response.usage_metadata.total_token_count

            # Extract cache metadata from Google AI response
            cache_read_tokens = None
            cache_hit = None
            if hasattr(response.usage_metadata, "cached_content_token_count"):
                cache_read_tokens = response.usage_metadata.cached_content_token_count
                cache_hit = cache_read_tokens is not None and cache_read_tokens > 0

            # Use config-based cost estimation
            cost = self._estimate_cost_from_config(model_name, prompt_tokens, completion_tokens)

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model_name,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_estimate=cost,
                cache_read_tokens=cache_read_tokens,
                cache_hit=cache_hit,
            )

        except Exception as e:
            if "quota" in str(e).lower():
                raise RateLimitError(f"Google AI quota exceeded: {str(e)}")
            self.logger.error(f"Error generating text with Google AI: {e}")
            raise

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using Google AI (google.genai SDK)"""
        client = self._init_google_ai()

        # Get model name from config if not provided
        model_name = model or self._get_default_model() or "gemini-2.5-pro"

        # Get model config for default parameters
        model_config = self._get_model_config(model_name)
        if model_config and max_tokens is None:
            max_tokens = model_config.default_params.max_tokens

        try:
            # Extract system message from messages if not provided
            system_msg = None
            user_messages = []
            for msg in messages:
                if msg.role == "system":
                    system_msg = msg.content
                else:
                    user_messages.append(msg)

            # Use provided system_instruction or extracted system message
            final_system_instruction = system_instruction or system_msg

            # Convert messages to Content objects
            contents = self._convert_messages_to_contents(user_messages)

            # Create GenerateContentConfig with all settings
            config = types.GenerateContentConfig(
                system_instruction=final_system_instruction,
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40),
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_HARASSMENT",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_HATE_SPEECH",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        threshold="OFF",
                    ),
                    types.SafetySetting(
                        category="HARM_CATEGORY_DANGEROUS_CONTENT",
                        threshold="OFF",
                    ),
                ],
            )

            # Use async streaming with the new SDK
            async for chunk in client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config,
            ):
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            self.logger.error(f"Error streaming text with Google AI: {e}")
            raise

    async def close(self):
        """Clean up resources"""
        # Google GenAI SDK does not require explicit closing of a client
        self._initialized = False
        self._client = None

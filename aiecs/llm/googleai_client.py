import asyncio
import logging
import os
from typing import Dict, Any, Optional, List, AsyncGenerator

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, SafetySetting, HarmCategory, HarmBlockThreshold

from aiecs.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)

class GoogleAIClient(BaseLLMClient):
    """Google AI (Gemini) provider client"""

    def __init__(self):
        super().__init__("GoogleAI")
        self.settings = get_settings()
        self._initialized = False
        self.client = None

        # Token cost estimates for Gemini 2.5 series
        self.token_costs = {
            "gemini-2.5-pro": {"input": 0.00125, "output": 0.00375},
            "gemini-2.5-flash": {"input": 0.000075, "output": 0.0003},
        }

    def _init_google_ai(self):
        """Lazy initialization of Google AI SDK"""
        if not self._initialized:
            api_key = self.settings.googleai_api_key or os.environ.get("GOOGLEAI_API_KEY")
            if not api_key:
                raise ProviderNotAvailableError("Google AI API key not configured. Set GOOGLEAI_API_KEY.")

            try:
                genai.configure(api_key=api_key)
                self._initialized = True
                self.logger.info("Google AI SDK initialized successfully.")
            except Exception as e:
                raise ProviderNotAvailableError(f"Failed to initialize Google AI SDK: {str(e)}")

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text using Google AI"""
        self._init_google_ai()
        model_name = model or "gemini-2.5-pro"

        try:
            model_instance = genai.GenerativeModel(model_name)
            
            # Convert messages to Google AI format
            history = [{"role": msg.role, "parts": [msg.content]} for msg in messages]

            # The last message is the prompt
            prompt = history.pop()
            
            # Create GenerationConfig
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40)
            )

            # Safety settings to match vertex_client
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response = await model_instance.generate_content_async(
                contents=prompt['parts'],
                generation_config=generation_config,
                safety_settings=safety_settings
            )

            content = response.text
            prompt_tokens = response.usage_metadata.prompt_token_count
            completion_tokens = response.usage_metadata.candidates_token_count
            total_tokens = response.usage_metadata.total_token_count

            cost = self._estimate_cost(
                model_name,
                prompt_tokens,
                completion_tokens,
                self.token_costs
            )

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=model_name,
                tokens_used=total_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_estimate=cost
            )

        except Exception as e:
            if "quota" in str(e).lower():
                raise RateLimitError(f"Google AI quota exceeded: {str(e)}")
            self.logger.error(f"Error generating text with Google AI: {e}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using Google AI"""
        self._init_google_ai()
        model_name = model or "gemini-2.5-pro"

        try:
            model_instance = genai.GenerativeModel(model_name)
            
            # Convert messages to Google AI format
            history = [{"role": msg.role, "parts": [msg.content]} for msg in messages]
            prompt = history.pop()

            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens or 8192,
                top_p=kwargs.get("top_p", 0.95),
                top_k=kwargs.get("top_k", 40)
            )
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response_stream = await model_instance.generate_content_async(
                contents=prompt['parts'],
                generation_config=generation_config,
                safety_settings=safety_settings,
                stream=True
            )

            async for chunk in response_stream:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            self.logger.error(f"Error streaming text with Google AI: {e}")
            raise

    async def close(self):
        """Clean up resources"""
        # Google AI SDK does not require explicit closing of a client
        self._initialized = False

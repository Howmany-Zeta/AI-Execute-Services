import json
import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)

class XAIClient(BaseLLMClient):
    """xAI (Grok) provider client"""

    def __init__(self):
        super().__init__("xAI")
        self.settings = get_settings()
        self._openai_client: Optional[AsyncOpenAI] = None

        # Enhanced model mapping for all Grok models
        self.model_map = {
            # Legacy Grok models
            "grok-beta": "grok-beta",
            "grok": "grok-beta",

            # Current Grok models
            "Grok 2": "grok-2",
            "grok-2": "grok-2",
            "Grok 2 Vision": "grok-2-vision",
            "grok-2-vision": "grok-2-vision",

            # Grok 3 models
            "Grok 3 Normal": "grok-3",
            "grok-3": "grok-3",
            "Grok 3 Fast": "grok-3-fast",
            "grok-3-fast": "grok-3-fast",

            # Grok 3 Mini models
            "Grok 3 Mini Normal": "grok-3-mini",
            "grok-3-mini": "grok-3-mini",
            "Grok 3 Mini Fast": "grok-3-mini-fast",
            "grok-3-mini-fast": "grok-3-mini-fast",

            # Grok 3 Reasoning models
            "Grok 3 Reasoning Normal": "grok-3-reasoning",
            "grok-3-reasoning": "grok-3-reasoning",
            "Grok 3 Reasoning Fast": "grok-3-reasoning-fast",
            "grok-3-reasoning-fast": "grok-3-reasoning-fast",

            # Grok 3 Mini Reasoning models
            "Grok 3 Mini Reasoning Normal": "grok-3-mini-reasoning",
            "grok-3-mini-reasoning": "grok-3-mini-reasoning",
            "Grok 3 Mini Reasoning Fast": "grok-3-mini-reasoning-fast",
            "grok-3-mini-reasoning-fast": "grok-3-mini-reasoning-fast",

            # Grok 4 models
            "Grok 4 Normal": "grok-4",
            "grok-4": "grok-4",
            "Grok 4 Fast": "grok-4-fast",
            "grok-4-fast": "grok-4-fast",
            "Grok 4 0709": "grok-4-0709",
            "grok-4-0709": "grok-4-0709",
        }

    def _get_openai_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client for XAI"""
        if not self._openai_client:
            api_key = self._get_api_key()
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1",
                timeout=360.0  # Override default timeout with longer timeout for reasoning models
            )
        return self._openai_client

    def _get_api_key(self) -> str:
        """Get API key with backward compatibility"""
        # Support both xai_api_key and grok_api_key for backward compatibility
        api_key = getattr(self.settings, 'xai_api_key', None) or getattr(self.settings, 'grok_api_key', None)
        if not api_key:
            raise ProviderNotAvailableError("xAI API key not configured")
        return api_key

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception, RateLimitError))
    )
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text using xAI API via OpenAI library (supports all Grok models)"""
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("xAI API key is not configured.")

        client = self._get_openai_client()

        selected_model = model or "grok-4"  # Default to grok-4 as in the example
        api_model = self.model_map.get(selected_model, selected_model)

        # Convert to OpenAI format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            completion = await client.chat.completions.create(
                model=api_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            content = completion.choices[0].message.content
            tokens_used = completion.usage.total_tokens if completion.usage else None

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=selected_model,
                tokens_used=tokens_used,
                cost_estimate=0.0  # xAI pricing not available yet
            )

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise RateLimitError(f"xAI rate limit exceeded: {str(e)}")
            logger.error(f"xAI API error: {str(e)}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text using xAI API via OpenAI library (supports all Grok models)"""
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("xAI API key is not configured.")

        client = self._get_openai_client()

        selected_model = model or "grok-4"  # Default to grok-4
        api_model = self.model_map.get(selected_model, selected_model)

        # Convert to OpenAI format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            stream = await client.chat.completions.create(
                model=api_model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise RateLimitError(f"xAI rate limit exceeded: {str(e)}")
            logger.error(f"xAI API streaming error: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        if self._openai_client:
            await self._openai_client.close()
            self._openai_client = None

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_client import BaseLLMClient, LLMMessage, LLMResponse, ProviderNotAvailableError, RateLimitError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class XAIClient(BaseLLMClient):
    """xAI (Grok) provider client"""

    def __init__(self):
        super().__init__("xAI")
        self.settings = get_settings()
        self._http_client: Optional[httpx.AsyncClient] = None

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
            "grok-3-mini-reasoning-fast": "grok-3-mini-reasoning-fast"
        }

    def _get_http_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client"""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=60.0)
        return self._http_client

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
        retry=retry_if_exception_type((httpx.RequestError, RateLimitError))
    )
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text using xAI API (supports all Grok models)"""
        api_key = self._get_api_key()
        http_client = self._get_http_client()

        selected_model = model or "grok-2"
        api_model = self.model_map.get(selected_model, selected_model)

        # Convert to xAI API format (OpenAI-compatible)
        xai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": xai_messages,
            "model": api_model,
            "temperature": temperature,
            "stream": False
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await http_client.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens")

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=selected_model,
                tokens_used=tokens_used,
                cost_estimate=0.0  # xAI pricing not available yet
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"xAI rate limit exceeded: {str(e)}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text using xAI API (supports all Grok models)"""
        api_key = self._get_api_key()
        http_client = self._get_http_client()

        selected_model = model or "grok-2"
        api_model = self.model_map.get(selected_model, selected_model)

        # Convert to xAI API format (OpenAI-compatible)
        xai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "messages": xai_messages,
            "model": api_model,
            "temperature": temperature,
            "stream": True
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with http_client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = httpx._content.json_loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta and delta["content"]:
                                    yield delta["content"]
                        except Exception as e:
                            self.logger.warning(f"Error parsing streaming response: {e}")
                            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError(f"xAI rate limit exceeded: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

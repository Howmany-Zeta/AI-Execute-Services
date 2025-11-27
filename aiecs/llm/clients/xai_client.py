from openai import AsyncOpenAI
from aiecs.config.config import get_settings
from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import logging
from typing import Dict, Optional, List, AsyncGenerator, cast, Any

# Lazy import to avoid circular dependency


def _get_config_loader():
    """Lazy import of config loader to avoid circular dependency"""
    from aiecs.llm.config import get_llm_config_loader

    return get_llm_config_loader()


logger = logging.getLogger(__name__)


class XAIClient(BaseLLMClient):
    """xAI (Grok) provider client"""

    def __init__(self) -> None:
        super().__init__("xAI")
        self.settings = get_settings()
        self._openai_client: Optional[AsyncOpenAI] = None
        self._model_map: Optional[Dict[str, str]] = None

    def _get_openai_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client for XAI"""
        if not self._openai_client:
            api_key = self._get_api_key()
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.x.ai/v1",
                timeout=360.0,  # Override default timeout with longer timeout for reasoning models
            )
        return self._openai_client

    def _get_api_key(self) -> str:
        """Get API key with backward compatibility"""
        # Support both xai_api_key and grok_api_key for backward compatibility
        api_key = getattr(self.settings, "xai_api_key", None) or getattr(self.settings, "grok_api_key", None)
        if not api_key:
            raise ProviderNotAvailableError("xAI API key not configured")
        return api_key

    def _get_model_map(self) -> Dict[str, str]:
        """Get model mappings from configuration"""
        if self._model_map is None:
            try:
                loader = _get_config_loader()
                provider_config = loader.get_provider_config("xAI")
                if provider_config and provider_config.model_mappings:
                    self._model_map = provider_config.model_mappings
                else:
                    self._model_map = {}
            except Exception as e:
                self.logger.warning(f"Failed to load model mappings from config: {e}")
                self._model_map = {}
        return self._model_map

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception, RateLimitError)),
    )
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using xAI API via OpenAI library (supports all Grok models)"""
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("xAI API key is not configured.")

        client = self._get_openai_client()

        # Get model name from config if not provided
        selected_model = model or self._get_default_model() or "grok-4"

        # Get model mappings from config
        model_map = self._get_model_map()
        api_model = model_map.get(selected_model, selected_model)

        # Convert to OpenAI format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            completion = await client.chat.completions.create(
                model=api_model,
                messages=cast(Any, openai_messages),  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            content = completion.choices[0].message.content
            if content is None:
                content = ""
            tokens_used = completion.usage.total_tokens if completion.usage else None

            return LLMResponse(
                content=content,
                provider=self.provider_name,
                model=selected_model,
                tokens_used=tokens_used,
                cost_estimate=0.0,  # xAI pricing not available yet
            )

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise RateLimitError(f"xAI rate limit exceeded: {str(e)}")
            logger.error(f"xAI API error: {str(e)}")
            raise

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream text using xAI API via OpenAI library (supports all Grok models)"""
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("xAI API key is not configured.")

        client = self._get_openai_client()

        # Get model name from config if not provided
        selected_model = model or self._get_default_model() or "grok-4"

        # Get model mappings from config
        model_map = self._get_model_map()
        api_model = model_map.get(selected_model, selected_model)

        # Convert to OpenAI format
        openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

        try:
            stream = await client.chat.completions.create(
                model=api_model,
                messages=cast(Any, openai_messages),  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            # Type narrowing: check if stream is async iterable
            if hasattr(stream, "__aiter__"):
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

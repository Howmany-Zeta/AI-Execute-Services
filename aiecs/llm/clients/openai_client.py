import logging
from typing import Optional, List, Dict, AsyncGenerator, cast, Any
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import httpx

from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from aiecs.llm.clients.openai_compatible_mixin import (
    OpenAICompatibleFunctionCallingMixin,
    StreamChunk,
)
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    """OpenAI provider client"""

    def __init__(self) -> None:
        super().__init__("OpenAI")
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None

    def _get_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client"""
        if not self._client:
            if not self.settings.openai_api_key:
                raise ProviderNotAvailableError("OpenAI API key not configured")
            self._client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, RateLimitError)),
    )
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using OpenAI API with optional function calling support.

        Args:
            messages: List of LLM messages
            model: Model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            **kwargs: Additional arguments passed to OpenAI API

        Returns:
            LLMResponse with content and optional function_call information
        """
        client = self._get_client()

        # Get model name from config if not provided
        model = model or self._get_default_model() or "gpt-4-turbo"

        try:
            # Use mixin method for Function Calling support
            return await self._generate_text_with_function_calling(
                client=client,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs,
            )

        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
            raise

    async def stream_text(  # type: ignore[override]
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        return_chunks: bool = False,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Stream text using OpenAI API with optional function calling support.

        Args:
            messages: List of LLM messages
            model: Model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            return_chunks: If True, returns StreamChunk objects with tool_calls info; if False, returns str tokens only
            **kwargs: Additional arguments passed to OpenAI API

        Yields:
            str or StreamChunk: Text tokens as they are generated, or StreamChunk objects if return_chunks=True
        """
        client = self._get_client()

        # Get model name from config if not provided
        model = model or self._get_default_model() or "gpt-4-turbo"

        try:
            # Use mixin method for Function Calling support
            async for chunk in self._stream_text_with_function_calling(
                client=client,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                return_chunks=return_chunks,
                **kwargs,
            ):
                yield chunk
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        if self._client:
            await self._client.close()
            self._client = None

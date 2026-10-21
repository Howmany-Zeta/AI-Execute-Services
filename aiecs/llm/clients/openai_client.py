# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
import logging
from typing import Optional, List, Dict, AsyncGenerator, Any
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
)
from aiecs.config.config import get_settings

logger = logging.getLogger(__name__)


def _session_prompt_cache_key(context: Optional[Dict[str, Any]]) -> Optional[str]:
    """OpenAI prompt-cache routing key. Only a non-empty session_id qualifies."""
    if not context:
        return None
    session_id = context.get("session_id")
    if session_id is None:
        return None
    key = str(session_id).strip()
    return key or None


def _prompt_cache_key_rejected(exc: BaseException) -> bool:
    return "prompt_cache_key" in str(exc).lower()


class OpenAIClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    """OpenAI provider client"""

    retries_generate_text = True

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
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        input_price: Optional[float] = None,
        output_price: Optional[float] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using OpenAI API with optional function calling support.

        Args:
            messages: List of LLM messages
            model: Model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            context: Optional context dictionary containing metadata such as:
                - user_id: User identifier for tracking/billing
                - tenant_id: Tenant identifier for multi-tenant setups
                - request_id: Request identifier for tracing
                - session_id: Session identifier
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
        call_kwargs = dict(kwargs)
        cache_key = _session_prompt_cache_key(context)
        if cache_key:
            call_kwargs["prompt_cache_key"] = cache_key

        try:
            return await self._generate_once(
                client=client,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                input_price=input_price,
                output_price=output_price,
                call_kwargs=call_kwargs,
                cache_key=cache_key,
            )
        except Exception as e:
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        return_chunks: bool = False,
        input_price: Optional[float] = None,
        output_price: Optional[float] = None,
        **kwargs,
    ) -> AsyncGenerator[Any, None]:
        """
        Stream text using OpenAI API with optional function calling support.

        Args:
            messages: List of LLM messages
            model: Model name (optional)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            context: Optional context dictionary containing metadata such as:
                - user_id: User identifier for tracking/billing
                - tenant_id: Tenant identifier for multi-tenant setups
                - request_id: Request identifier for tracing
                - session_id: Session identifier
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
        call_kwargs = dict(kwargs)
        cache_key = _session_prompt_cache_key(context)
        if cache_key:
            call_kwargs["prompt_cache_key"] = cache_key

        yielded = False
        try:
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
                **call_kwargs,
            ):
                yielded = True
                yield chunk
        except Exception as e:
            if cache_key and not yielded and _prompt_cache_key_rejected(e):
                call_kwargs.pop("prompt_cache_key", None)
                try:
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
                        **call_kwargs,
                    ):
                        yield chunk
                    return
                except Exception as retry_exc:
                    e = retry_exc
            if "rate_limit" in str(e).lower():
                raise RateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
            raise

    async def _generate_once(
        self,
        *,
        client: AsyncOpenAI,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        functions: Optional[List[Dict[str, Any]]],
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[Any],
        input_price: Optional[float],
        output_price: Optional[float],
        call_kwargs: Dict[str, Any],
        cache_key: Optional[str],
    ) -> LLMResponse:
        """One completion. If prompt_cache_key is rejected, retry once without it."""
        try:
            return await self._generate_text_with_function_calling(
                client=client,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                input_price=input_price,
                output_price=output_price,
                **call_kwargs,
            )
        except Exception as e:
            if not (cache_key and _prompt_cache_key_rejected(e)):
                raise
            call_kwargs.pop("prompt_cache_key", None)
            return await self._generate_text_with_function_calling(
                client=client,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                input_price=input_price,
                output_price=output_price,
                **call_kwargs,
            )

    async def close(self):
        """Clean up resources"""
        if self._client:
            await self._client.close()
            self._client = None

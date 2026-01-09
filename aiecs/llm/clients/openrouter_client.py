from openai import AsyncOpenAI
from aiecs.config.config import get_settings
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


class OpenRouterClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    """OpenRouter provider client using OpenAI-compatible API"""

    def __init__(self) -> None:
        super().__init__("OpenRouter")
        self.settings = get_settings()
        self._openai_client: Optional[AsyncOpenAI] = None
        self._model_map: Optional[Dict[str, str]] = None

    def _get_openai_client(self) -> AsyncOpenAI:
        """Lazy initialization of OpenAI client for OpenRouter"""
        if not self._openai_client:
            api_key = self._get_api_key()
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=360.0,
            )
        return self._openai_client

    def _get_api_key(self) -> str:
        """Get API key from settings"""
        api_key = getattr(self.settings, "openrouter_api_key", None)
        if not api_key:
            raise ProviderNotAvailableError("OpenRouter API key not configured. Set OPENROUTER_API_KEY.")
        return api_key

    def _get_model_map(self) -> Dict[str, str]:
        """Get model mappings from configuration"""
        if self._model_map is None:
            try:
                loader = _get_config_loader()
                provider_config = loader.get_provider_config("OpenRouter")
                if provider_config and provider_config.model_mappings:
                    self._model_map = provider_config.model_mappings
                else:
                    self._model_map = {}
            except Exception as e:
                self.logger.warning(f"Failed to load model mappings from config: {e}")
                self._model_map = {}
        return self._model_map

    def _get_extra_headers(self, **kwargs) -> Dict[str, str]:
        """
        Get extra headers for OpenRouter API.
        
        Supports HTTP-Referer and X-Title headers from kwargs or settings.
        
        Args:
            **kwargs: May contain http_referer and x_title
            
        Returns:
            Dictionary with extra headers
        """
        extra_headers: Dict[str, str] = {}
        
        # Get from kwargs first, then from settings
        http_referer = kwargs.get("http_referer") or getattr(self.settings, "openrouter_http_referer", None)
        x_title = kwargs.get("x_title") or getattr(self.settings, "openrouter_x_title", None)
        
        if http_referer:
            extra_headers["HTTP-Referer"] = http_referer
        if x_title:
            extra_headers["X-Title"] = x_title
            
        return extra_headers

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
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using OpenRouter API via OpenAI library.
        
        OpenRouter API is OpenAI-compatible, so it supports Function Calling and Vision.
        
        Args:
            messages: List of LLM messages
            model: Model name (optional, uses default from config if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            http_referer: Optional HTTP-Referer header for OpenRouter rankings
            x_title: Optional X-Title header for OpenRouter rankings
            **kwargs: Additional arguments passed to OpenRouter API
            
        Returns:
            LLMResponse with content and optional function_call information
        """
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("OpenRouter API key is not configured.")

        client = self._get_openai_client()

        # Get model name from config if not provided
        selected_model = model or self._get_default_model() or "openai/gpt-4o"

        # Get model mappings from config
        model_map = self._get_model_map()
        api_model = model_map.get(selected_model, selected_model)

        # Extract extra headers from kwargs
        extra_headers = self._get_extra_headers(**kwargs)
        
        # Remove extra header kwargs to avoid passing them to API
        kwargs_clean = {k: v for k, v in kwargs.items() if k not in ("http_referer", "x_title")}
        
        # Add extra_headers to kwargs if present
        if extra_headers:
            kwargs_clean["extra_headers"] = extra_headers

        try:
            # Use mixin method for Function Calling support
            response = await self._generate_text_with_function_calling(
                client=client,
                messages=messages,
                model=api_model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs_clean,
            )
            
            # Override provider and model name for OpenRouter
            response.provider = self.provider_name
            response.model = selected_model
            
            return response

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise RateLimitError(f"OpenRouter rate limit exceeded: {str(e)}")
            logger.error(f"OpenRouter API error: {str(e)}")
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
        Stream text using OpenRouter API via OpenAI library.
        
        OpenRouter API is OpenAI-compatible, so it supports Function Calling and Vision.
        
        Args:
            messages: List of LLM messages
            model: Model name (optional, uses default from config if not provided)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            functions: List of function schemas (legacy format)
            tools: List of tool schemas (new format, recommended)
            tool_choice: Tool choice strategy ("auto", "none", or specific tool)
            return_chunks: If True, returns StreamChunk objects with tool_calls info; if False, returns str tokens only
            http_referer: Optional HTTP-Referer header for OpenRouter rankings
            x_title: Optional X-Title header for OpenRouter rankings
            **kwargs: Additional arguments passed to OpenRouter API
            
        Yields:
            str or StreamChunk: Text tokens as they are generated, or StreamChunk objects if return_chunks=True
        """
        # Check API key availability
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotAvailableError("OpenRouter API key is not configured.")

        client = self._get_openai_client()

        # Get model name from config if not provided
        selected_model = model or self._get_default_model() or "openai/gpt-4o"

        # Get model mappings from config
        model_map = self._get_model_map()
        api_model = model_map.get(selected_model, selected_model)

        # Extract extra headers from kwargs
        extra_headers = self._get_extra_headers(**kwargs)
        
        # Remove extra header kwargs to avoid passing them to API
        kwargs_clean = {k: v for k, v in kwargs.items() if k not in ("http_referer", "x_title")}
        
        # Add extra_headers to kwargs if present
        if extra_headers:
            kwargs_clean["extra_headers"] = extra_headers

        try:
            # Use mixin method for Function Calling support
            async for chunk in self._stream_text_with_function_calling(
                client=client,
                messages=messages,
                model=api_model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                return_chunks=return_chunks,
                **kwargs_clean,
            ):
                yield chunk

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                raise RateLimitError(f"OpenRouter rate limit exceeded: {str(e)}")
            logger.error(f"OpenRouter API streaming error: {str(e)}")
            raise

    async def close(self):
        """Clean up resources"""
        if self._openai_client:
            await self._openai_client.close()
            self._openai_client = None

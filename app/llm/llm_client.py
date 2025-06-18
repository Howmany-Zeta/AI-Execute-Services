"""
LLM Client - Refactored modular architecture

This module provides a unified interface to multiple AI providers through
individual client implementations and a factory pattern.
"""

# Re-export main components for backward compatibility
from .base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMClientError,
    ProviderNotAvailableError,
    RateLimitError
)
from .client_factory import (
    AIProvider,
    LLMClientFactory,
    LLMClientManager,
    get_llm_manager,
    generate_text,
    stream_text
)
from .openai_client import OpenAIClient
from .vertex_client import VertexAIClient
from .xai_client import XAIClient

import logging

logger = logging.getLogger(__name__)

class LLMClient:
    """
    Legacy LLM client for backward compatibility

    This class now acts as a facade over the new modular architecture.
    New code should use LLMClientManager or the factory directly.
    """

    def __init__(self):
        self._manager = LLMClientManager()
        logger.warning("LLMClient is deprecated. Use LLMClientManager or factory methods instead.")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Clean up resources"""
        await self._manager.close()

    async def generate_text(
        self,
        messages,
        provider=AIProvider.OPENAI,
        model=None,
        context=None,
        temperature=0.7,
        max_tokens=None,
        **kwargs
    ) -> LLMResponse:
        """Generate text using the new modular architecture"""
        return await self._manager.generate_text(
            messages=messages,
            provider=provider,
            model=model,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

    async def stream_text(
        self,
        messages,
        provider=AIProvider.OPENAI,
        model=None,
        context=None,
        temperature=0.7,
        max_tokens=None,
        **kwargs
    ):
        """Stream text using the new modular architecture"""
        async for chunk in self._manager.stream_text(
            messages=messages,
            provider=provider,
            model=model,
            context=context,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk

# Legacy convenience functions for backward compatibility
async def get_llm_client() -> LLMClient:
    """Get a legacy LLM client instance (deprecated)"""
    logger.warning("get_llm_client() is deprecated. Use get_llm_manager() instead.")
    return LLMClient()

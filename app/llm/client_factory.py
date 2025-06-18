import logging
from typing import Dict, Any, Optional, Union
from enum import Enum

from .base_client import BaseLLMClient, LLMMessage, LLMResponse
from .openai_client import OpenAIClient
from .vertex_client import VertexAIClient
from .xai_client import XAIClient

logger = logging.getLogger(__name__)

class AIProvider(str, Enum):
    OPENAI = "OpenAI"
    VERTEX = "vertex"
    XAI = "xAI"

class LLMClientFactory:
    """Factory for creating and managing LLM provider clients"""

    _clients: Dict[AIProvider, BaseLLMClient] = {}

    @classmethod
    def get_client(cls, provider: Union[str, AIProvider]) -> BaseLLMClient:
        """Get or create a client for the specified provider"""
        if isinstance(provider, str):
            try:
                provider = AIProvider(provider)
            except ValueError:
                raise ValueError(f"Unsupported provider: {provider}")

        if provider not in cls._clients:
            cls._clients[provider] = cls._create_client(provider)

        return cls._clients[provider]

    @classmethod
    def _create_client(cls, provider: AIProvider) -> BaseLLMClient:
        """Create a new client instance for the provider"""
        if provider == AIProvider.OPENAI:
            return OpenAIClient()
        elif provider == AIProvider.VERTEX:
            return VertexAIClient()
        elif provider == AIProvider.XAI:
            return XAIClient()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @classmethod
    async def close_all(cls):
        """Close all active clients"""
        for client in cls._clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client {client.provider_name}: {e}")
        cls._clients.clear()

    @classmethod
    async def close_client(cls, provider: Union[str, AIProvider]):
        """Close a specific client"""
        if isinstance(provider, str):
            provider = AIProvider(provider)

        if provider in cls._clients:
            try:
                await cls._clients[provider].close()
                del cls._clients[provider]
            except Exception as e:
                logger.error(f"Error closing client {provider}: {e}")

class LLMClientManager:
    """High-level manager for LLM operations with context-aware provider selection"""

    def __init__(self):
        self.factory = LLMClientFactory()

    def _extract_ai_preference(self, context: Optional[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
        """Extract AI provider and model from context"""
        if not context:
            return None, None

        # Check for aiPreference in metadata
        metadata = context.get('metadata', {})
        ai_preference = metadata.get('aiPreference', {})

        if isinstance(ai_preference, dict):
            provider = ai_preference.get('provider')
            model = ai_preference.get('model')
            return provider, model

        # Fallback to direct provider/model in metadata
        provider = metadata.get('provider')
        model = metadata.get('model')
        return provider, model

    async def generate_text(
        self,
        messages: Union[str, list[LLMMessage]],
        provider: Optional[Union[str, AIProvider]] = None,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using context-aware provider selection

        Args:
            messages: Either a string prompt or list of LLMMessage objects
            provider: AI provider to use (can be overridden by context)
            model: Specific model to use (can be overridden by context)
            context: TaskContext or dict containing aiPreference
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse object with generated text and metadata
        """
        # Extract provider/model from context if available
        context_provider, context_model = self._extract_ai_preference(context)

        # Use context preferences if available, otherwise use provided values
        final_provider = context_provider or provider or AIProvider.OPENAI
        final_model = context_model or model

        # Convert string prompt to messages format
        if isinstance(messages, str):
            messages = [LLMMessage(role="user", content=messages)]

        # Get the appropriate client
        client = self.factory.get_client(final_provider)

        # Generate text
        response = await client.generate_text(
            messages=messages,
            model=final_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        logger.info(f"Generated text using {final_provider}/{response.model}")
        return response

    async def stream_text(
        self,
        messages: Union[str, list[LLMMessage]],
        provider: Optional[Union[str, AIProvider]] = None,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Stream text generation using context-aware provider selection

        Yields:
            str: Incremental text chunks
        """
        # Extract provider/model from context if available
        context_provider, context_model = self._extract_ai_preference(context)

        # Use context preferences if available, otherwise use provided values
        final_provider = context_provider or provider or AIProvider.OPENAI
        final_model = context_model or model

        # Convert string prompt to messages format
        if isinstance(messages, str):
            messages = [LLMMessage(role="user", content=messages)]

        # Get the appropriate client
        client = self.factory.get_client(final_provider)

        # Stream text
        async for chunk in client.stream_text(
            messages=messages,
            model=final_model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        ):
            yield chunk

    async def close(self):
        """Close all clients"""
        await self.factory.close_all()

# Global instance for easy access
_llm_manager = LLMClientManager()

async def get_llm_manager() -> LLMClientManager:
    """Get the global LLM manager instance"""
    return _llm_manager

# Convenience functions for backward compatibility
async def generate_text(
    messages: Union[str, list[LLMMessage]],
    provider: Optional[Union[str, AIProvider]] = None,
    model: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> LLMResponse:
    """Generate text using the global LLM manager"""
    manager = await get_llm_manager()
    return await manager.generate_text(messages, provider, model, context, **kwargs)

async def stream_text(
    messages: Union[str, list[LLMMessage]],
    provider: Optional[Union[str, AIProvider]] = None,
    model: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """Stream text using the global LLM manager"""
    manager = await get_llm_manager()
    async for chunk in manager.stream_text(messages, provider, model, context, **kwargs):
        yield chunk

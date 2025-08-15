"""
LLM Package - Modular AI Provider Architecture

This package provides a unified interface to multiple AI providers through
individual client implementations and a factory pattern.
"""

# Import all main components
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

__all__ = [
    # Base classes and types
    'BaseLLMClient',
    'LLMMessage',
    'LLMResponse',
    'LLMClientError',
    'ProviderNotAvailableError',
    'RateLimitError',
    'AIProvider',

    # Factory and manager
    'LLMClientFactory',
    'LLMClientManager',
    'get_llm_manager',

    # Individual clients
    'OpenAIClient',
    'VertexAIClient',
    'XAIClient',

    # Convenience functions
    'generate_text',
    'stream_text',
]

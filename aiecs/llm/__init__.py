"""
LLM Package - Modular AI Provider Architecture

This package provides a unified interface to multiple AI providers through
individual client implementations and a factory pattern.

Package Structure:
- clients/: LLM client implementations
- config/: Configuration management
- callbacks/: Callback handlers
- utils/: Utility functions and scripts
"""

# Import from organized subpackages
from .clients import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    LLMClientError,
    ProviderNotAvailableError,
    RateLimitError,
    OpenAIClient,
    VertexAIClient,
    GoogleAIClient,
    XAIClient,
)

from .protocols import LLMClientProtocol

from .client_factory import (
    AIProvider,
    LLMClientFactory,
    LLMClientManager,
    get_llm_manager,
    generate_text,
    stream_text,
)

from .config import (
    ModelCostConfig,
    ModelCapabilities,
    ModelDefaultParams,
    ModelConfig,
    ProviderConfig,
    LLMModelsConfig,
    LLMConfigLoader,
    get_llm_config_loader,
    get_llm_config,
    reload_llm_config,
)

from .callbacks import CustomAsyncCallbackHandler

from .client_resolver import (
    resolve_llm_client,
    clear_client_cache,
    get_cached_providers,
)

__all__ = [
    # Base classes and types
    "BaseLLMClient",
    "LLMMessage",
    "LLMResponse",
    "LLMClientError",
    "ProviderNotAvailableError",
    "RateLimitError",
    "AIProvider",
    # Protocols
    "LLMClientProtocol",
    # Factory and manager
    "LLMClientFactory",
    "LLMClientManager",
    "get_llm_manager",
    # Individual clients
    "OpenAIClient",
    "VertexAIClient",
    "GoogleAIClient",
    "XAIClient",
    # Convenience functions
    "generate_text",
    "stream_text",
    # Client resolution helpers
    "resolve_llm_client",
    "clear_client_cache",
    "get_cached_providers",
    # Configuration management
    "ModelCostConfig",
    "ModelCapabilities",
    "ModelDefaultParams",
    "ModelConfig",
    "ProviderConfig",
    "LLMModelsConfig",
    "LLMConfigLoader",
    "get_llm_config_loader",
    "get_llm_config",
    "reload_llm_config",
    # Callbacks
    "CustomAsyncCallbackHandler",
]

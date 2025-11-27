"""
LLM Client Resolution Helper

Provides convenient helper functions for resolving LLM clients from provider names
with caching support for improved performance.
"""

import logging
from typing import Optional, Union, Dict, TYPE_CHECKING
from aiecs.llm.client_factory import LLMClientFactory, AIProvider

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol

logger = logging.getLogger(__name__)


# Cache for resolved clients to avoid repeated factory calls
_client_cache: Dict[str, "LLMClientProtocol"] = {}


def resolve_llm_client(
    provider: Union[str, AIProvider],
    model: Optional[str] = None,
    use_cache: bool = True,
) -> "LLMClientProtocol":
    """
    Resolve an LLM client from a provider name with optional caching.

    This helper function provides a convenient interface for resolving LLM clients
    from provider names, supporting both standard AIProvider enum values and custom
    provider names registered via LLMClientFactory.register_custom_provider().

    The function includes built-in caching to avoid repeated factory calls for the
    same provider, improving performance when the same client is requested multiple times.

    Args:
        provider: AIProvider enum or custom provider name string
        model: Optional model name (for logging/debugging purposes)
        use_cache: Whether to use cached clients (default: True)

    Returns:
        LLM client implementing LLMClientProtocol

    Raises:
        ValueError: If provider is unknown (not standard and not registered)

    Example:
        ```python
        from aiecs.llm.client_resolver import resolve_llm_client
        from aiecs.llm.client_factory import LLMClientFactory

        # Resolve standard provider
        client = resolve_llm_client("OpenAI", model="gpt-4")

        # Register and resolve custom provider
        LLMClientFactory.register_custom_provider("my-llm", custom_client)
        client = resolve_llm_client("my-llm", model="custom-model")

        # Use the client
        response = await client.generate_text(messages, model="gpt-4")
        ```

    Note:
        - Caching is based on provider name only, not model name
        - Custom providers registered after caching will require cache clearing
        - Use `clear_client_cache()` to clear the cache if needed
    """
    # Convert provider to string for cache key
    cache_key = str(provider) if isinstance(provider, AIProvider) else provider

    # Check cache first if caching is enabled
    if use_cache and cache_key in _client_cache:
        logger.debug(f"Using cached client for provider: {cache_key}")
        return _client_cache[cache_key]

    # Resolve client from factory
    try:
        client = LLMClientFactory.get_client(provider)
        
        # Log resolution
        if model:
            logger.info(f"Resolved LLM client for provider: {cache_key}, model: {model}")
        else:
            logger.info(f"Resolved LLM client for provider: {cache_key}")

        # Cache the client if caching is enabled
        # Cast to LLMClientProtocol since BaseLLMClient implements the protocol
        if use_cache:
            from typing import cast
            _client_cache[cache_key] = cast("LLMClientProtocol", client)
            logger.debug(f"Cached client for provider: {cache_key}")

        # Cast return value to match return type annotation
        from typing import cast
        return cast("LLMClientProtocol", client)

    except ValueError as e:
        logger.error(f"Failed to resolve LLM client for provider: {cache_key}")
        raise


def clear_client_cache(provider: Optional[Union[str, AIProvider]] = None) -> None:
    """
    Clear the client resolution cache.

    Args:
        provider: Optional provider to clear from cache.
                 If None, clears entire cache.

    Example:
        ```python
        from aiecs.llm.client_resolver import clear_client_cache

        # Clear specific provider
        clear_client_cache("OpenAI")

        # Clear entire cache
        clear_client_cache()
        ```
    """
    global _client_cache

    if provider is None:
        # Clear entire cache
        count = len(_client_cache)
        _client_cache.clear()
        logger.info(f"Cleared entire client cache ({count} entries)")
    else:
        # Clear specific provider
        cache_key = str(provider) if isinstance(provider, AIProvider) else provider
        if cache_key in _client_cache:
            del _client_cache[cache_key]
            logger.info(f"Cleared cache for provider: {cache_key}")
        else:
            logger.debug(f"Provider not in cache: {cache_key}")


def get_cached_providers() -> list[str]:
    """
    Get list of providers currently in the cache.

    Returns:
        List of provider names that have cached clients

    Example:
        ```python
        from aiecs.llm.client_resolver import get_cached_providers

        providers = get_cached_providers()
        print(f"Cached providers: {providers}")
        ```
    """
    return list(_client_cache.keys())


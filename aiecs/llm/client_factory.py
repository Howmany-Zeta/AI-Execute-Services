import logging
from typing import Dict, Any, Optional, Union, List, TYPE_CHECKING
from enum import Enum

from .clients.base_client import BaseLLMClient, LLMMessage, LLMResponse
from .clients.openai_client import OpenAIClient
from .clients.vertex_client import VertexAIClient
from .clients.googleai_client import GoogleAIClient
from .clients.xai_client import XAIClient
from .callbacks.custom_callbacks import CustomAsyncCallbackHandler

if TYPE_CHECKING:
    from .protocols import LLMClientProtocol

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    OPENAI = "OpenAI"
    VERTEX = "Vertex"
    GOOGLEAI = "GoogleAI"
    XAI = "xAI"


class LLMClientFactory:
    """Factory for creating and managing LLM provider clients"""

    _clients: Dict[AIProvider, BaseLLMClient] = {}
    _custom_clients: Dict[str, "LLMClientProtocol"] = {}

    @classmethod
    def register_custom_provider(cls, name: str, client: "LLMClientProtocol") -> None:
        """
        Register a custom LLM client provider.

        This allows registration of custom LLM clients that implement the LLMClientProtocol
        without inheriting from BaseLLMClient. Custom providers can be retrieved by name
        using get_client().

        Args:
            name: Custom provider name (e.g., "my-llm", "llama-local", "custom-gpt")
            client: Client implementing LLMClientProtocol

        Raises:
            ValueError: If client doesn't implement LLMClientProtocol
            ValueError: If name conflicts with standard AIProvider enum values

        Example:
            ```python
            # Register custom LLM client
            custom_client = MyCustomLLMClient()
            LLMClientFactory.register_custom_provider("my-llm", custom_client)

            # Use custom client
            client = LLMClientFactory.get_client("my-llm")
            response = await client.generate_text(messages)
            ```
        """
        # Import here to avoid circular dependency
        from .protocols import LLMClientProtocol

        # Validate protocol compliance
        if not isinstance(client, LLMClientProtocol):
            raise ValueError(
                f"Client must implement LLMClientProtocol. "
                f"Required methods: generate_text, stream_text, close, get_embeddings. "
                f"Required attribute: provider_name"
            )

        # Prevent conflicts with standard provider names
        try:
            AIProvider(name)
            raise ValueError(
                f"Custom provider name '{name}' conflicts with standard AIProvider enum. "
                f"Please use a different name."
            )
        except ValueError as e:
            # If ValueError is raised because name is not in enum, that's good
            if "conflicts with standard AIProvider" in str(e):
                raise
            # Otherwise, name is not in enum, proceed with registration

        cls._custom_clients[name] = client
        logger.info(f"Registered custom LLM provider: {name}")

    @classmethod
    def get_client(cls, provider: Union[str, AIProvider]) -> Union[BaseLLMClient, "LLMClientProtocol"]:
        """
        Get or create a client for the specified provider.

        Supports both standard AIProvider enum values and custom provider names
        registered via register_custom_provider().

        Args:
            provider: AIProvider enum or custom provider name string

        Returns:
            LLM client (BaseLLMClient for standard providers, LLMClientProtocol for custom)

        Raises:
            ValueError: If provider is unknown (not standard and not registered)
        """
        # Check custom providers first
        if isinstance(provider, str) and provider in cls._custom_clients:
            return cls._custom_clients[provider]

        # Handle standard providers
        if isinstance(provider, str):
            try:
                provider = AIProvider(provider)
            except ValueError:
                raise ValueError(
                    f"Unknown provider: {provider}. "
                    f"Standard providers: {[p.value for p in AIProvider]}. "
                    f"Custom providers: {list(cls._custom_clients.keys())}. "
                    f"Register custom providers with LLMClientFactory.register_custom_provider()"
                )

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
        elif provider == AIProvider.GOOGLEAI:
            return GoogleAIClient()
        elif provider == AIProvider.XAI:
            return XAIClient()
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @classmethod
    async def close_all(cls):
        """Close all active clients (both standard and custom)"""
        # Close standard clients
        for client in cls._clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing client {client.provider_name}: {e}")
        cls._clients.clear()

        # Close custom clients
        for name, client in cls._custom_clients.items():
            try:
                await client.close()
            except Exception as e:
                logger.error(f"Error closing custom client {name}: {e}")
        cls._custom_clients.clear()

    @classmethod
    async def close_client(cls, provider: Union[str, AIProvider]):
        """Close a specific client (standard or custom)"""
        # Check if it's a custom provider
        if isinstance(provider, str) and provider in cls._custom_clients:
            try:
                await cls._custom_clients[provider].close()
                del cls._custom_clients[provider]
                logger.info(f"Closed custom client: {provider}")
            except Exception as e:
                logger.error(f"Error closing custom client {provider}: {e}")
            return

        # Handle standard providers
        if isinstance(provider, str):
            try:
                provider = AIProvider(provider)
            except ValueError:
                logger.warning(f"Unknown provider to close: {provider}")
                return

        if provider in cls._clients:
            try:
                await cls._clients[provider].close()
                del cls._clients[provider]
            except Exception as e:
                logger.error(f"Error closing client {provider}: {e}")

    @classmethod
    def reload_config(cls):
        """
        Reload LLM models configuration.

        This reloads the configuration from the YAML file, allowing for
        hot-reloading of model settings without restarting the application.
        """
        try:
            from aiecs.llm.config import reload_llm_config

            config = reload_llm_config()
            logger.info(f"Reloaded LLM configuration: {len(config.providers)} providers")
            return config
        except Exception as e:
            logger.error(f"Failed to reload LLM configuration: {e}")
            raise


class LLMClientManager:
    """High-level manager for LLM operations with context-aware provider selection"""

    def __init__(self):
        self.factory = LLMClientFactory()

    def _extract_ai_preference(self, context: Optional[Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
        """Extract AI provider and model from context"""
        if not context:
            return None, None

        metadata = context.get("metadata", {})

        # First, check for aiPreference in metadata
        ai_preference = metadata.get("aiPreference", {})
        if isinstance(ai_preference, dict):
            provider = ai_preference.get("provider")
            model = ai_preference.get("model")
            if provider is not None:
                return provider, model

        # Fallback to direct provider/model in metadata
        provider = metadata.get("provider")
        model = metadata.get("model")
        return provider, model

    async def generate_text(
        self,
        messages: Union[str, list[LLMMessage]],
        provider: Optional[Union[str, AIProvider]] = None,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[CustomAsyncCallbackHandler]] = None,
        **kwargs,
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
            callbacks: List of callback handlers to execute during LLM calls
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

        # Execute on_llm_start callbacks
        if callbacks:
            # Convert LLMMessage objects to dictionaries for callbacks
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
            for callback in callbacks:
                try:
                    await callback.on_llm_start(
                        messages_dict,
                        provider=final_provider,
                        model=final_model,
                        **kwargs,
                    )
                except Exception as e:
                    logger.error(f"Error in callback on_llm_start: {e}")

        try:
            # Get the appropriate client
            client = self.factory.get_client(final_provider)

            # Generate text
            response = await client.generate_text(
                messages=messages,
                model=final_model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            # Execute on_llm_end callbacks
            if callbacks:
                # Convert LLMResponse object to dictionary for callbacks
                response_dict = {
                    "content": response.content,
                    "provider": response.provider,
                    "model": response.model,
                    "tokens_used": response.tokens_used,
                    "prompt_tokens": response.prompt_tokens,
                    "completion_tokens": response.completion_tokens,
                    "cost_estimate": response.cost_estimate,
                    "response_time": response.response_time,
                }
                for callback in callbacks:
                    try:
                        await callback.on_llm_end(
                            response_dict,
                            provider=final_provider,
                            model=final_model,
                            **kwargs,
                        )
                    except Exception as e:
                        logger.error(f"Error in callback on_llm_end: {e}")

            logger.info(f"Generated text using {final_provider}/{response.model}")
            return response

        except Exception as e:
            # Execute on_llm_error callbacks
            if callbacks:
                for callback in callbacks:
                    try:
                        await callback.on_llm_error(
                            e,
                            provider=final_provider,
                            model=final_model,
                            **kwargs,
                        )
                    except Exception as callback_error:
                        logger.error(f"Error in callback on_llm_error: {callback_error}")

            # Re-raise the original exception
            raise

    async def stream_text(
        self,
        messages: Union[str, list[LLMMessage]],
        provider: Optional[Union[str, AIProvider]] = None,
        model: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[CustomAsyncCallbackHandler]] = None,
        **kwargs,
    ):
        """
        Stream text generation using context-aware provider selection

        Args:
            messages: Either a string prompt or list of LLMMessage objects
            provider: AI provider to use (can be overridden by context)
            model: Specific model to use (can be overridden by context)
            context: TaskContext or dict containing aiPreference
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            callbacks: List of callback handlers to execute during LLM calls
            **kwargs: Additional provider-specific parameters

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

        # Execute on_llm_start callbacks
        if callbacks:
            # Convert LLMMessage objects to dictionaries for callbacks
            messages_dict = [{"role": msg.role, "content": msg.content} for msg in messages]
            for callback in callbacks:
                try:
                    await callback.on_llm_start(
                        messages_dict,
                        provider=final_provider,
                        model=final_model,
                        **kwargs,
                    )
                except Exception as e:
                    logger.error(f"Error in callback on_llm_start: {e}")

        try:
            # Get the appropriate client
            client = self.factory.get_client(final_provider)

            # Collect streamed content for token counting
            collected_content = ""

            # Stream text
            # Note: stream_text is an async generator, not a coroutine,
            # so we iterate directly without await
            async for chunk in client.stream_text(
                messages=messages,
                model=final_model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ):
                collected_content += chunk
                yield chunk

            # Create a response object for callbacks (streaming doesn't return LLMResponse directly)
            # We need to estimate token usage for streaming responses
            estimated_tokens = len(collected_content) // 4  # Rough estimation
            stream_response = LLMResponse(
                content=collected_content,
                provider=str(final_provider),
                model=final_model or "unknown",
                tokens_used=estimated_tokens,
            )

            # Execute on_llm_end callbacks
            if callbacks:
                # Convert LLMResponse object to dictionary for callbacks
                response_dict = {
                    "content": stream_response.content,
                    "provider": stream_response.provider,
                    "model": stream_response.model,
                    "tokens_used": stream_response.tokens_used,
                    "prompt_tokens": stream_response.prompt_tokens,
                    "completion_tokens": stream_response.completion_tokens,
                    "cost_estimate": stream_response.cost_estimate,
                    "response_time": stream_response.response_time,
                }
                for callback in callbacks:
                    try:
                        await callback.on_llm_end(
                            response_dict,
                            provider=final_provider,
                            model=final_model,
                            **kwargs,
                        )
                    except Exception as e:
                        logger.error(f"Error in callback on_llm_end: {e}")

        except Exception as e:
            # Execute on_llm_error callbacks
            if callbacks:
                for callback in callbacks:
                    try:
                        await callback.on_llm_error(
                            e,
                            provider=final_provider,
                            model=final_model,
                            **kwargs,
                        )
                    except Exception as callback_error:
                        logger.error(f"Error in callback on_llm_error: {callback_error}")

            # Re-raise the original exception
            raise

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
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    callbacks: Optional[List[CustomAsyncCallbackHandler]] = None,
    **kwargs,
) -> LLMResponse:
    """Generate text using the global LLM manager"""
    manager = await get_llm_manager()
    return await manager.generate_text(
        messages,
        provider,
        model,
        context,
        temperature,
        max_tokens,
        callbacks,
        **kwargs,
    )


async def stream_text(
    messages: Union[str, list[LLMMessage]],
    provider: Optional[Union[str, AIProvider]] = None,
    model: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    callbacks: Optional[List[CustomAsyncCallbackHandler]] = None,
    **kwargs,
):
    """Stream text using the global LLM manager"""
    manager = await get_llm_manager()
    async for chunk in manager.stream_text(
        messages,
        provider,
        model,
        context,
        temperature,
        max_tokens,
        callbacks,
        **kwargs,
    ):
        yield chunk

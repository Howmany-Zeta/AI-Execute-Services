"""
LLM Client Protocols

Defines Protocol interfaces for LLM clients to enable duck typing and flexible integration.
"""

from typing import Protocol, List, Optional, AsyncGenerator, runtime_checkable
from aiecs.llm.clients.base_client import LLMMessage, LLMResponse


@runtime_checkable
class LLMClientProtocol(Protocol):
    """
    Protocol for LLM clients.

    This protocol defines the interface that any LLM client must implement
    to be compatible with AIECS agents. It uses duck typing (Protocol) rather
    than inheritance, allowing custom LLM clients to work without inheriting
    from BaseLLMClient.

    Example:
        ```python
        # Custom LLM client that implements the protocol
        class CustomLLMClient:
            def __init__(self):
                self.provider_name = "custom"

            async def generate_text(
                self,
                messages: List[LLMMessage],
                model: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: Optional[int] = None,
                **kwargs
            ) -> LLMResponse:
                # Custom implementation
                pass

            async def stream_text(
                self,
                messages: List[LLMMessage],
                model: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: Optional[int] = None,
                **kwargs
            ) -> AsyncGenerator[str, None]:
                # Custom implementation
                yield "token"

            async def close(self):
                # Cleanup
                pass

        # Use with agents
        agent = HybridAgent(
            llm_client=CustomLLMClient(),  # Works without BaseLLMClient inheritance!
            ...
        )
        ```
    """

    provider_name: str

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate text using the LLM provider's API.

        Args:
            messages: List of conversation messages
            model: Model name (optional, uses default if not provided)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        ...

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text generation using the LLM provider's API.

        Args:
            messages: List of conversation messages
            model: Model name (optional, uses default if not provided)
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            Text tokens as they are generated
        """
        ...

    async def close(self):
        """
        Clean up resources (connections, sessions, etc.).

        This method should be called when the client is no longer needed.
        """
        ...

    async def get_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """
        Get embeddings for a list of texts.

        This method is used for semantic compression and similarity analysis.
        Implementations should return normalized embeddings for cosine similarity.

        Args:
            texts: List of texts to embed
            model: Embedding model name (optional, uses default if not provided)
            **kwargs: Additional provider-specific parameters

        Returns:
            List of embedding vectors (one per input text)

        Example:
            ```python
            texts = ["Hello world", "Goodbye world"]
            embeddings = await llm_client.get_embeddings(texts)
            # embeddings = [[0.1, 0.2, ...], [0.15, 0.25, ...]]
            ```

        Note:
            Not all LLM clients support embeddings. If not supported,
            this method should raise NotImplementedError.
        """
        ...

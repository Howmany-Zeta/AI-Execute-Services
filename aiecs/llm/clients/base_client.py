from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependency


def _get_config_loader():
    """Lazy import of config loader to avoid circular dependency"""
    from aiecs.llm.config import get_llm_config_loader

    return get_llm_config_loader()


@dataclass
class CacheControl:
    """
    Cache control marker for message content.

    Used to indicate that a message or message block should be cached
    by providers that support prompt caching (e.g., Anthropic, Google).
    """

    type: str = "ephemeral"  # Cache type - "ephemeral" for session-scoped caching


@dataclass
class LLMMessage:
    """
    Represents a message in an LLM conversation.

    Attributes:
        role: Message role - "system", "user", "assistant", or "tool"
        content: Text content of the message (None when using tool calls)
        tool_calls: Tool call information for assistant messages
        tool_call_id: Tool call ID for tool response messages
        cache_control: Cache control marker for prompt caching support
    """

    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = None  # None when using tool calls
    tool_calls: Optional[List[Dict[str, Any]]] = None  # For assistant messages with tool calls
    tool_call_id: Optional[str] = None  # For tool messages
    cache_control: Optional[CacheControl] = None  # Cache control for prompt caching


@dataclass
class LLMResponse:
    """
    Response from an LLM provider.

    Attributes:
        content: Generated text content
        provider: Name of the LLM provider (e.g., "openai", "google", "vertex")
        model: Model name used for generation
        tokens_used: Total tokens used (prompt + completion)
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        cost_estimate: Estimated cost in USD
        response_time: Response time in seconds
        metadata: Additional provider-specific metadata
        cache_creation_tokens: Tokens used to create a new cache entry
        cache_read_tokens: Tokens read from cache (indicates cache hit)
        cache_hit: Whether the request hit a cached prompt prefix
    """

    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_estimate: Optional[float] = None
    response_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    # Cache metadata for prompt caching observability
    cache_creation_tokens: Optional[int] = None
    cache_read_tokens: Optional[int] = None
    cache_hit: Optional[bool] = None

    def __post_init__(self):
        """Ensure consistency of token data"""
        # If there are detailed token information but no total, calculate the
        # total
        if self.prompt_tokens is not None and self.completion_tokens is not None and self.tokens_used is None:
            self.tokens_used = self.prompt_tokens + self.completion_tokens

        # If only total is available but no detailed information, try to
        # estimate (cannot accurately allocate in this case)
        elif self.tokens_used is not None and self.prompt_tokens is None and self.completion_tokens is None:
            # In this case we cannot accurately allocate, keep as is
            pass


class LLMClientError(Exception):
    """Base exception for LLM client errors"""


class ProviderNotAvailableError(LLMClientError):
    """Raised when a provider is not available or misconfigured"""


class RateLimitError(LLMClientError):
    """Raised when rate limit is exceeded"""


class SafetyBlockError(LLMClientError):
    """Raised when content is blocked by safety filters"""
    
    def __init__(
        self,
        message: str,
        block_reason: Optional[str] = None,
        block_type: Optional[str] = None,  # "prompt" or "response"
        safety_ratings: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize SafetyBlockError with detailed information.
        
        Args:
            message: Error message
            block_reason: Reason for blocking (e.g., SAFETY, RECITATION, JAILBREAK)
            block_type: Type of block - "prompt" if input was blocked, "response" if output was blocked
            safety_ratings: List of safety ratings with category, severity, etc.
        """
        super().__init__(message)
        self.block_reason = block_reason
        self.block_type = block_type
        self.safety_ratings = safety_ratings or []
    
    def __str__(self) -> str:
        """Return detailed error message"""
        msg = super().__str__()
        if self.block_reason:
            msg += f" (Block reason: {self.block_reason})"
        if self.block_type:
            msg += f" (Block type: {self.block_type})"
        if self.safety_ratings:
            # Safely extract categories, handling potential non-dict elements
            categories = []
            for r in self.safety_ratings:
                if isinstance(r, dict) and r.get("blocked"):
                    categories.append(r.get("category", "UNKNOWN"))
            if categories:
                msg += f" (Categories: {', '.join(categories)})"
        return msg


class BaseLLMClient(ABC):
    """Abstract base class for all LLM provider clients"""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")

    @abstractmethod
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using the provider's API"""

    @abstractmethod
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using the provider's API"""

    @abstractmethod
    async def close(self):
        """Clean up resources"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _count_tokens_estimate(self, text: str) -> int:
        """Rough token count estimation (4 chars ≈ 1 token for English)"""
        return len(text) // 4

    def _apply_cache_control(
        self,
        messages: List[LLMMessage],
        enable_caching: bool = True,
    ) -> List[LLMMessage]:
        """
        Apply cache control markers to cacheable messages.

        Marks system messages and the first message in the conversation
        with cache_control for providers that support prompt caching.

        Args:
            messages: List of LLM messages
            enable_caching: Whether to enable caching (default: True)

        Returns:
            List of messages with cache_control applied where appropriate
        """
        if not enable_caching:
            return messages

        result = []
        for msg in messages:
            if msg.role == "system" and msg.cache_control is None:
                # Mark system messages as cacheable
                result.append(
                    LLMMessage(
                        role=msg.role,
                        content=msg.content,
                        tool_calls=msg.tool_calls,
                        tool_call_id=msg.tool_call_id,
                        cache_control=CacheControl(type="ephemeral"),
                    )
                )
            else:
                result.append(msg)
        return result

    def _extract_cache_metadata(
        self,
        usage: Any,
    ) -> Dict[str, Any]:
        """
        Extract cache metadata from provider response usage data.

        Override in subclasses for provider-specific extraction.

        Args:
            usage: Usage data from provider response

        Returns:
            Dictionary with cache_creation_tokens, cache_read_tokens, cache_hit
        """
        return {
            "cache_creation_tokens": None,
            "cache_read_tokens": None,
            "cache_hit": None,
        }

    def _estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        token_costs: Dict,
    ) -> float:
        """
        Estimate the cost of the API call.

        DEPRECATED: Use _estimate_cost_from_config instead for config-based cost estimation.
        This method is kept for backward compatibility.
        """
        if model in token_costs:
            costs = token_costs[model]
            return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
        return 0.0

    def _estimate_cost_from_config(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate the cost using configuration-based pricing.

        Args:
            model_name: Name of the model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        try:
            loader = _get_config_loader()
            model_config = loader.get_model_config(self.provider_name, model_name)

            if model_config and model_config.costs:
                input_cost = (input_tokens * model_config.costs.input) / 1000
                output_cost = (output_tokens * model_config.costs.output) / 1000
                return input_cost + output_cost
            else:
                self.logger.warning(f"No cost configuration found for model {model_name} " f"in provider {self.provider_name}")
                return 0.0
        except Exception as e:
            self.logger.warning(f"Failed to estimate cost from config: {e}")
            return 0.0

    def _get_model_config(self, model_name: str):
        """
        Get model configuration from the config loader.

        Args:
            model_name: Name of the model

        Returns:
            ModelConfig if found, None otherwise
        """
        try:
            loader = _get_config_loader()
            return loader.get_model_config(self.provider_name, model_name)
        except Exception as e:
            self.logger.warning(f"Failed to get model config: {e}")
            return None

    def _get_default_model(self) -> Optional[str]:
        """
        Get the default model for this provider from configuration.

        Returns:
            Default model name if configured, None otherwise
        """
        try:
            loader = _get_config_loader()
            return loader.get_default_model(self.provider_name)
        except Exception as e:
            self.logger.warning(f"Failed to get default model: {e}")
            return None

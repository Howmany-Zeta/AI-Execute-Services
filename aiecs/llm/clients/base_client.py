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
class LLMMessage:
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_estimate: Optional[float] = None
    response_time: Optional[float] = None
    # Added for backward compatibility
    metadata: Optional[Dict[str, Any]] = None

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

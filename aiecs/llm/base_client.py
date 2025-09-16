from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)

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

    def __post_init__(self):
        """Ensure consistency of token data"""
        # If there are detailed token information but no total, calculate the total
        if self.prompt_tokens is not None and self.completion_tokens is not None and self.tokens_used is None:
            self.tokens_used = self.prompt_tokens + self.completion_tokens

        # If only total is available but no detailed information, try to estimate (cannot accurately allocate in this case)
        elif self.tokens_used is not None and self.prompt_tokens is None and self.completion_tokens is None:
            # In this case we cannot accurately allocate, keep as is
            pass

class LLMClientError(Exception):
    """Base exception for LLM client errors"""
    pass

class ProviderNotAvailableError(LLMClientError):
    """Raised when a provider is not available or misconfigured"""
    pass

class RateLimitError(LLMClientError):
    """Raised when rate limit is exceeded"""
    pass

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
        **kwargs
    ) -> LLMResponse:
        """Generate text using the provider's API"""
        pass

    @abstractmethod
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using the provider's API"""
        pass

    @abstractmethod
    async def close(self):
        """Clean up resources"""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _count_tokens_estimate(self, text: str) -> int:
        """Rough token count estimation (4 chars ≈ 1 token for English)"""
        return len(text) // 4

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int, token_costs: Dict) -> float:
        """Estimate the cost of the API call"""
        if model in token_costs:
            costs = token_costs[model]
            return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
        return 0.0

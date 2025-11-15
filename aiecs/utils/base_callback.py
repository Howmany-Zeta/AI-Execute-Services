from typing import Any, List
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CustomAsyncCallbackHandler(ABC):
    """
    Abstract base class for asynchronous callback handlers

    This is an abstract base class that defines the callback interface for LLM calls.
    All concrete callback handlers should inherit from this class and implement its abstract methods.

    Uses generic data structures (Dict[str, Any]) instead of specific LLM types
    to avoid circular import issues and maintain clean architecture.
    """

    @abstractmethod
    async def on_llm_start(self, messages: List[dict], **kwargs: Any) -> None:
        """
        Callback triggered when LLM call starts

        Args:
            messages: List of message dictionaries, each containing 'role' and 'content' keys
            **kwargs: Additional parameters such as provider, model, etc.
        """

    @abstractmethod
    async def on_llm_end(self, response: dict, **kwargs: Any) -> None:
        """
        Callback triggered when LLM call ends successfully

        Args:
            response: Response dictionary containing 'content', 'tokens_used', 'model', etc.
            **kwargs: Additional parameters such as provider, model, etc.
        """

    @abstractmethod
    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """
        Callback triggered when LLM call encounters an error

        Args:
            error: The exception that occurred during the LLM call
            **kwargs: Additional parameters such as provider, model, etc.
        """

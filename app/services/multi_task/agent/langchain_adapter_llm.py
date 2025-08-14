"""
LangChain Adapter for LLM Integration

This module provides a smart adapter that bridges LangChain agents with the LLM integration system.
It can operate in two modes:
1. Context-aware: Uses context to determine LLM provider and model
2. Static: Uses predefined provider and model from configuration
"""

import logging
import asyncio
from typing import Any, List, Optional, Dict, Union, TYPE_CHECKING
from langchain.llms.base import LLM
from langchain.schema import LLMResult, Generation
from langchain.callbacks.manager import CallbackManagerForLLMRun
from pydantic import ConfigDict, Field

# Use TYPE_CHECKING to avoid circular imports and runtime validation issues
if TYPE_CHECKING:
    from app.services.llm_integration import LLMIntegrationManager
else:
    # Import for runtime use
    from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class LangChainAdapterLLM(LLM):
    """
    A smart adapter that can decide between context-aware and static LLM configuration.

    This adapter serves as a bridge between LangChain agents and the LLM integration system,
    providing intelligent routing based on whether static configuration is provided.
    """

    # Declare Pydantic fields with relaxed validation for llm_integration_manager
    llm_integration_manager: Any = Field(...)
    context: Dict[str, Any] = Field(...)
    static_provider: Optional[str] = Field(default=None)
    static_model: Optional[str] = Field(default=None)

    def __init__(
        self,
        manager: Any,  # Changed from LLMIntegrationManager to Any
        context: Dict[str, Any],
        static_provider: Optional[str] = None,
        static_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the LangChain adapter.

        Args:
            manager: LLM integration manager instance
            context: Runtime context containing user preferences and task information
            static_provider: Optional static LLM provider (overrides context)
            static_model: Optional static LLM model (overrides context)
        """
        # Runtime validation to ensure manager has required methods
        if not hasattr(manager, 'generate_with_context'):
            raise TypeError(
                f"manager must be an LLMIntegrationManager instance with generate_with_context method. "
                f"Got: {type(manager)}"
            )

        super().__init__(
            llm_integration_manager=manager,
            context=context,
            static_provider=static_provider,
            static_model=static_model,
            **kwargs
        )

        # Log the adapter configuration for debugging
        if self.static_provider:
            logger.debug(
                f"LangChain adapter initialized with static configuration: "
                f"provider={self.static_provider}, model={self.static_model}"
            )
        else:
            logger.debug("LangChain adapter initialized in context-aware mode")

        # Additional debug logging for type validation
        logger.debug(f"LLM manager type: {type(manager)}, module: {manager.__class__.__module__}")

    @property
    def _llm_type(self) -> str:
        """Return the LLM type identifier."""
        return "langchain_smart_adapter"

    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Implement async call method. This is the core logic for LLM routing.

        Args:
            prompt: The prompt to send to the LLM
            stop: Optional stop sequences
            run_manager: Callback manager for the run
            **kwargs: Additional arguments

        Returns:
            The LLM response content
        """
        try:
            # Logic decision: if static configuration exists, use it as priority
            if self.static_provider:
                logger.debug(
                    f"Using static LLM configuration: {self.static_provider}/{self.static_model}"
                )

                # Convert string provider to AIProvider enum if needed
                from app.llm import AIProvider
                provider_mapping = {
                    'OpenAI': AIProvider.OPENAI,
                    'openai': AIProvider.OPENAI,
                    'Vertex AI': AIProvider.VERTEX,
                    'Vertex': AIProvider.VERTEX,
                    'vertex': AIProvider.VERTEX,
                    'Google': AIProvider.VERTEX,
                    'xAI': AIProvider.XAI,
                    'Grok': AIProvider.XAI,
                }

                # Convert string to enum, fallback to original if not found
                if isinstance(self.static_provider, str):
                    mapped_provider = provider_mapping.get(self.static_provider, self.static_provider)
                else:
                    mapped_provider = self.static_provider

                try:
                    # For internal agents, use static configuration as fallback
                    # This will override context preferences
                    response = await self.llm_integration_manager.generate_with_context(
                        messages=prompt,
                        context=self.context,
                        fallback_provider=mapped_provider,
                        fallback_model=self.static_model,
                        **kwargs
                    )
                except Exception as static_error:
                    logger.warning(
                        f"Static LLM provider {self.static_provider} failed: {static_error}. "
                        f"Falling back to context-aware selection."
                    )
                    # Fallback to context-aware selection if static provider fails
                    response = await self.llm_integration_manager.generate_with_context(
                        messages=prompt,
                        context=self.context,
                        **kwargs
                    )
            else:
                logger.debug("Using context-aware LLM selection")
                # For agents like IntentParserAgent, completely rely on context
                response = await self.llm_integration_manager.generate_with_context(
                    messages=prompt,
                    context=self.context,
                    **kwargs
                )

            return response.content

        except Exception as e:
            logger.error(f"LangChain adapter LLM call failed: {e}")
            raise

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> str:
        """
        Implement synchronous call method with similar logic to async version.

        Args:
            prompt: The prompt to send to the LLM
            stop: Optional stop sequences
            run_manager: Callback manager for the run
            **kwargs: Additional arguments

        Returns:
            The LLM response content
        """
        try:
            # Check if there's already a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, we need to handle this differently
                # Create a task and run it in the existing loop
                import concurrent.futures
                import threading

                # Create a new thread to run the async operation
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._acall(prompt, stop, run_manager, **kwargs))
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    result = future.result()
                    return result

            except RuntimeError:
                # No running loop, safe to create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(self._acall(prompt, stop, run_manager, **kwargs))
                    return result
                finally:
                    loop.close()

        except Exception as e:
            logger.error(f"LangChain adapter sync LLM call failed: {e}")
            raise

    def _generate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """
        Generate responses for multiple prompts.

        Args:
            prompts: List of prompts to process
            stop: Optional stop sequences
            run_manager: Callback manager for the run
            **kwargs: Additional arguments

        Returns:
            LLMResult with generations
        """
        generations = []
        for prompt in prompts:
            try:
                response = self._call(prompt, stop, run_manager, **kwargs)
                generations.append([Generation(text=response)])
            except Exception as e:
                logger.error(f"Failed to generate response for prompt: {e}")
                generations.append([Generation(text=f"Error: {str(e)}")])

        return LLMResult(generations=generations)

    async def _agenerate(
        self,
        prompts: List[str],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """
        Async generate responses for multiple prompts.

        Args:
            prompts: List of prompts to process
            stop: Optional stop sequences
            run_manager: Callback manager for the run
            **kwargs: Additional arguments

        Returns:
            LLMResult with generations
        """
        generations = []
        for prompt in prompts:
            try:
                response = await self._acall(prompt, stop, run_manager, **kwargs)
                generations.append([Generation(text=response)])
            except Exception as e:
                logger.error(f"Failed to generate async response for prompt: {e}")
                generations.append([Generation(text=f"Error: {str(e)}")])

        return LLMResult(generations=generations)

    def get_num_tokens(self, text: str) -> int:
        """
        Get the number of tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Estimated number of tokens
        """
        # Simple estimation: roughly 4 characters per token
        return len(text) // 4

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """
        Get identifying parameters for the LLM.

        Returns:
            Dictionary of identifying parameters
        """
        return {
            "adapter_type": "langchain_smart_adapter",
            "static_provider": self.static_provider,
            "static_model": self.static_model,
            "context_aware": self.static_provider is None
        }
    model_config = ConfigDict(arbitrary_types_allowed=True)

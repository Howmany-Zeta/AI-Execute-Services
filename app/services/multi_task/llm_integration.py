"""
LLM Integration for Multi-Task Services

This module provides integration between the multi-task services and the new
modular LLM client architecture, ensuring proper context-aware AI provider selection.
"""

import logging
from typing import Dict, Any, Optional, List, Union
from app.llm import get_llm_manager, LLMMessage, LLMResponse, AIProvider
from app.core.task_context import TaskContext

logger = logging.getLogger(__name__)

class LLMIntegrationManager:
    """
    Manager for integrating LLM operations with task context and AI preferences
    """

    def __init__(self):
        self._llm_manager = None

    async def _get_llm_manager(self):
        """Get or create LLM manager instance"""
        if not self._llm_manager:
            self._llm_manager = await get_llm_manager()
        return self._llm_manager

    def _extract_ai_preference_from_context(self, context: Union[TaskContext, Dict[str, Any]]) -> tuple[Optional[str], Optional[str]]:
        """
        Extract AI provider and model preferences from context

        Args:
            context: TaskContext instance or context dictionary

        Returns:
            tuple: (provider, model) extracted from context
        """
        if isinstance(context, TaskContext):
            # Extract from TaskContext instance
            metadata = context.get_active_metadata()
            ai_preference = metadata.get('aiPreference', {})
        elif isinstance(context, dict):
            # Extract from dictionary context
            metadata = context.get('metadata', {})
            ai_preference = metadata.get('aiPreference', {})
        else:
            return None, None

        if isinstance(ai_preference, dict):
            provider = ai_preference.get('provider')
            model = ai_preference.get('model')

            # Map frontend provider names to backend enum values
            provider_mapping = {
                'OpenAI': AIProvider.OPENAI,
                'openai': AIProvider.OPENAI,
                'Vertex AI': AIProvider.VERTEX,
                'vertex': AIProvider.VERTEX,
                'Google': AIProvider.VERTEX,
                'xAI': AIProvider.XAI,
                'Grok': AIProvider.XAI,
            }

            mapped_provider = provider_mapping.get(provider, provider)
            return mapped_provider, model

        return None, None

    async def generate_with_context(
        self,
        messages: Union[str, List[LLMMessage]],
        context: Union[TaskContext, Dict[str, Any]],
        fallback_provider: Optional[AIProvider] = None,
        fallback_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate text using context-aware provider selection

        Args:
            messages: Text prompt or list of messages
            context: TaskContext or context dictionary containing AI preferences
            fallback_provider: Provider to use if none specified in context
            fallback_model: Model to use if none specified in context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated text and metadata
        """
        llm_manager = await self._get_llm_manager()

        # Extract AI preferences from context
        context_provider, context_model = self._extract_ai_preference_from_context(context)

        # Use context preferences or fallbacks
        final_provider = context_provider or fallback_provider or AIProvider.OPENAI
        final_model = context_model or fallback_model

        # Track model usage in context if it's a TaskContext
        if isinstance(context, TaskContext):
            context.track_model_usage(
                model_id=final_model or "default",
                provider_id=str(final_provider),
                mode="generate"
            )

        # Convert context to dictionary format for LLM manager
        context_dict = context.to_dict() if isinstance(context, TaskContext) else context

        try:
            response = await llm_manager.generate_text(
                messages=messages,
                provider=final_provider,
                model=final_model,
                context=context_dict,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            # Add context update for successful generation
            if isinstance(context, TaskContext):
                context.add_context_update(
                    "llm_generation",
                    {
                        "provider": response.provider,
                        "model": response.model,
                        "tokens_used": response.tokens_used,
                        "cost_estimate": response.cost_estimate
                    },
                    {"success": True}
                )

            logger.info(f"Generated text using {response.provider}/{response.model} with {response.tokens_used} tokens")
            return response

        except Exception as e:
            # Add context update for failed generation
            if isinstance(context, TaskContext):
                context.add_context_update(
                    "llm_generation_error",
                    {"error": str(e), "provider": str(final_provider), "model": final_model},
                    {"success": False}
                )

            logger.error(f"Failed to generate text with {final_provider}: {e}")
            raise

    async def stream_with_context(
        self,
        messages: Union[str, List[LLMMessage]],
        context: Union[TaskContext, Dict[str, Any]],
        fallback_provider: Optional[AIProvider] = None,
        fallback_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Stream text generation using context-aware provider selection

        Args:
            messages: Text prompt or list of messages
            context: TaskContext or context dictionary containing AI preferences
            fallback_provider: Provider to use if none specified in context
            fallback_model: Model to use if none specified in context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            str: Incremental text chunks
        """
        llm_manager = await self._get_llm_manager()

        # Extract AI preferences from context
        context_provider, context_model = self._extract_ai_preference_from_context(context)

        # Use context preferences or fallbacks
        final_provider = context_provider or fallback_provider or AIProvider.OPENAI
        final_model = context_model or fallback_model

        # Track model usage in context if it's a TaskContext
        if isinstance(context, TaskContext):
            context.track_model_usage(
                model_id=final_model or "default",
                provider_id=str(final_provider),
                mode="stream"
            )

        # Convert context to dictionary format for LLM manager
        context_dict = context.to_dict() if isinstance(context, TaskContext) else context

        try:
            async for chunk in llm_manager.stream_text(
                messages=messages,
                provider=final_provider,
                model=final_model,
                context=context_dict,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield chunk

        except Exception as e:
            # Add context update for failed streaming
            if isinstance(context, TaskContext):
                context.add_context_update(
                    "llm_streaming_error",
                    {"error": str(e), "provider": str(final_provider), "model": final_model},
                    {"success": False}
                )

            logger.error(f"Failed to stream text with {final_provider}: {e}")
            raise

    async def close(self):
        """Clean up resources"""
        if self._llm_manager:
            await self._llm_manager.close()

# Global instance for easy access
_integration_manager = LLMIntegrationManager()

async def get_llm_integration_manager() -> LLMIntegrationManager:
    """Get the global LLM integration manager instance"""
    return _integration_manager

# Convenience functions for services
async def generate_with_context(
    messages: Union[str, List[LLMMessage]],
    context: Union[TaskContext, Dict[str, Any]],
    **kwargs
) -> LLMResponse:
    """Generate text using context-aware provider selection"""
    manager = await get_llm_integration_manager()
    return await manager.generate_with_context(messages, context, **kwargs)

async def stream_with_context(
    messages: Union[str, List[LLMMessage]],
    context: Union[TaskContext, Dict[str, Any]],
    **kwargs
):
    """Stream text using context-aware provider selection"""
    manager = await get_llm_integration_manager()
    async for chunk in manager.stream_with_context(messages, context, **kwargs):
        yield chunk

from typing import Any, List, Optional
import logging
import time

# Import the base callback handler from utils
from aiecs.utils.base_callback import CustomAsyncCallbackHandler

# Import LLM types for internal use only
# Import token usage repository
from aiecs.utils.token_usage_repository import token_usage_repo

logger = logging.getLogger(__name__)


class RedisTokenCallbackHandler(CustomAsyncCallbackHandler):
    """
    Concrete token recording callback handler.
    Responsible for recording token usage after LLM calls by delegating to the repository.
    """

    def __init__(self, user_id: str, cycle_start_date: Optional[str] = None):
        if not user_id:
            raise ValueError("user_id must be provided for RedisTokenCallbackHandler")
        self.user_id = user_id
        self.cycle_start_date = cycle_start_date
        self.start_time: Optional[float] = None
        self.messages: Optional[List[dict]] = None

    async def on_llm_start(self, messages: List[dict], **kwargs: Any) -> None:
        """Triggered when LLM call starts"""
        import time

        self.start_time = time.time()
        self.messages = messages

        logger.info(f"[Callback] LLM call started for user '{self.user_id}' with {len(messages)} messages")

    async def on_llm_end(self, response: dict, **kwargs: Any) -> None:
        """Triggered when LLM call ends successfully"""
        try:
            # Record call duration
            if self.start_time:
                import time

                call_duration = time.time() - self.start_time
                logger.info(f"[Callback] LLM call completed for user '{self.user_id}' in {call_duration:.2f}s")

            # Extract token usage from response dictionary
            tokens_used = response.get("tokens_used")

            if tokens_used and tokens_used > 0:
                # Delegate recording work to repository
                await token_usage_repo.increment_total_usage(self.user_id, tokens_used, self.cycle_start_date)

                logger.info(f"[Callback] Recorded {tokens_used} tokens for user '{self.user_id}'")
            else:
                logger.warning(f"[Callback] No token usage data available for user '{self.user_id}'")

        except Exception as e:
            logger.error(f"[Callback] Failed to record token usage for user '{self.user_id}': {e}")
            # Don't re-raise exception to avoid affecting main LLM call flow

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Triggered when LLM call encounters an error"""
        if self.start_time:
            import time

            call_duration = time.time() - self.start_time
            logger.error(f"[Callback] LLM call failed for user '{self.user_id}' after {call_duration:.2f}s: {error}")
        else:
            logger.error(f"[Callback] LLM call failed for user '{self.user_id}': {error}")


class DetailedRedisTokenCallbackHandler(CustomAsyncCallbackHandler):
    """
    Detailed token recording callback handler.
    Records separate prompt and completion token usage in addition to total usage.
    """

    def __init__(self, user_id: str, cycle_start_date: Optional[str] = None):
        if not user_id:
            raise ValueError("user_id must be provided for DetailedRedisTokenCallbackHandler")
        self.user_id = user_id
        self.cycle_start_date = cycle_start_date
        self.start_time: Optional[float] = None
        self.messages: Optional[List[dict]] = None
        self.prompt_tokens = 0

    async def on_llm_start(self, messages: List[dict], **kwargs: Any) -> None:
        """Triggered when LLM call starts"""
        import time

        self.start_time = time.time()
        self.messages = messages

        # Estimate input token count
        self.prompt_tokens = self._estimate_prompt_tokens(messages)

        logger.info(f"[DetailedCallback] LLM call started for user '{self.user_id}' with estimated {self.prompt_tokens} prompt tokens")

    async def on_llm_end(self, response: dict, **kwargs: Any) -> None:
        """Triggered when LLM call ends successfully"""
        try:
            # Record call duration
            if self.start_time:
                import time

                call_duration = time.time() - self.start_time
                logger.info(f"[DetailedCallback] LLM call completed for user '{self.user_id}' in {call_duration:.2f}s")

            # Extract detailed token information from response
            prompt_tokens, completion_tokens = self._extract_detailed_tokens(response)

            # Ensure we have valid integers (not None)
            prompt_tokens = prompt_tokens or 0
            completion_tokens = completion_tokens or 0

            if prompt_tokens > 0 or completion_tokens > 0:
                # Use detailed token recording method
                await token_usage_repo.increment_detailed_usage(
                    self.user_id,
                    prompt_tokens,
                    completion_tokens,
                    self.cycle_start_date,
                )

                logger.info(f"[DetailedCallback] Recorded detailed tokens for user '{self.user_id}': prompt={prompt_tokens}, completion={completion_tokens}")
            else:
                logger.warning(f"[DetailedCallback] No detailed token usage data available for user '{self.user_id}'")

        except Exception as e:
            logger.error(f"[DetailedCallback] Failed to record detailed token usage for user '{self.user_id}': {e}")
            # Don't re-raise exception to avoid affecting main LLM call flow

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Triggered when LLM call encounters an error"""
        if self.start_time:
            import time

            call_duration = time.time() - self.start_time
            logger.error(f"[DetailedCallback] LLM call failed for user '{self.user_id}' after {call_duration:.2f}s: {error}")
        else:
            logger.error(f"[DetailedCallback] LLM call failed for user '{self.user_id}': {error}")

    def _estimate_prompt_tokens(self, messages: List[dict]) -> int:
        """Estimate token count for input messages"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        # Rough estimation: 4 characters ≈ 1 token
        return total_chars // 4

    def _extract_detailed_tokens(self, response: dict) -> tuple[int, int]:
        """
        Extract detailed token information from response dictionary

        Returns:
            tuple: (prompt_tokens, completion_tokens)
        """
        # If response has detailed token information, use it first
        prompt_tokens = response.get("prompt_tokens") or 0
        completion_tokens = response.get("completion_tokens") or 0

        if prompt_tokens > 0 and completion_tokens > 0:
            return prompt_tokens, completion_tokens

        # If only total token count is available, try to allocate
        tokens_used = response.get("tokens_used") or 0
        if tokens_used > 0:
            # Use previously estimated prompt tokens
            prompt_tokens = self.prompt_tokens
            completion_tokens = max(0, tokens_used - prompt_tokens)
            return prompt_tokens, completion_tokens

        # If no token information, try to estimate from response content
        content = response.get("content", "")
        if content:
            completion_tokens = len(content) // 4
            prompt_tokens = self.prompt_tokens
            return prompt_tokens, completion_tokens

        return 0, 0


class CompositeCallbackHandler(CustomAsyncCallbackHandler):
    """
    Composite callback handler that can execute multiple callback handlers simultaneously
    """

    def __init__(self, handlers: List[CustomAsyncCallbackHandler]):
        self.handlers = handlers or []

    def add_handler(self, handler: CustomAsyncCallbackHandler):
        """Add a callback handler"""
        self.handlers.append(handler)

    async def on_llm_start(self, messages: List[dict], **kwargs: Any) -> None:
        """Execute start callbacks for all handlers"""
        for handler in self.handlers:
            try:
                await handler.on_llm_start(messages, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback handler {type(handler).__name__}.on_llm_start: {e}")

    async def on_llm_end(self, response: dict, **kwargs: Any) -> None:
        """Execute end callbacks for all handlers"""
        for handler in self.handlers:
            try:
                await handler.on_llm_end(response, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback handler {type(handler).__name__}.on_llm_end: {e}")

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """Execute error callbacks for all handlers"""
        for handler in self.handlers:
            try:
                await handler.on_llm_error(error, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback handler {type(handler).__name__}.on_llm_error: {e}")


# Convenience functions for creating common callback handlers
def create_token_callback(user_id: str, cycle_start_date: Optional[str] = None) -> RedisTokenCallbackHandler:
    """Create a basic token recording callback handler"""
    return RedisTokenCallbackHandler(user_id, cycle_start_date)


def create_detailed_token_callback(user_id: str, cycle_start_date: Optional[str] = None) -> DetailedRedisTokenCallbackHandler:
    """Create a detailed token recording callback handler"""
    return DetailedRedisTokenCallbackHandler(user_id, cycle_start_date)


def create_composite_callback(
    *handlers: CustomAsyncCallbackHandler,
) -> CompositeCallbackHandler:
    """Create a composite callback handler"""
    return CompositeCallbackHandler(list(handlers))

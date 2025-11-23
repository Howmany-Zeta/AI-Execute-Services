"""
Enhanced Retry Policy

Sophisticated retry logic with exponential backoff and error classification.
"""

import asyncio
import random
import logging
from typing import Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Error types for classification."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """Classifies errors for retry strategy."""

    @staticmethod
    def classify(error: Exception) -> ErrorType:
        """
        Classify error type.

        Args:
            error: Exception to classify

        Returns:
            ErrorType
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # Rate limit errors
        if "rate limit" in error_str or "429" in error_str:
            return ErrorType.RATE_LIMIT

        # Timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorType.TIMEOUT

        # Server errors (5xx)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return ErrorType.SERVER_ERROR

        # Client errors (4xx)
        if any(code in error_str for code in ["400", "401", "403", "404"]):
            return ErrorType.CLIENT_ERROR

        # Network errors
        if any(term in error_type_name for term in ["connection", "network", "socket"]):
            return ErrorType.NETWORK_ERROR

        return ErrorType.UNKNOWN

    @staticmethod
    def is_retryable(error_type: ErrorType) -> bool:
        """
        Determine if error type should be retried.

        Args:
            error_type: Error type

        Returns:
            True if retryable
        """
        retryable_types = {
            ErrorType.RATE_LIMIT,
            ErrorType.TIMEOUT,
            ErrorType.SERVER_ERROR,
            ErrorType.NETWORK_ERROR,
        }
        return error_type in retryable_types


class EnhancedRetryPolicy:
    """
    Enhanced retry policy with exponential backoff and jitter.

    Example:
        policy = EnhancedRetryPolicy(max_retries=5, base_delay=1.0)
        result = await policy.execute_with_retry(my_async_function, arg1, arg2)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """
        Calculate delay for retry attempt.

        Args:
            attempt: Retry attempt number (0-indexed)
            error_type: Type of error

        Returns:
            Delay in seconds
        """
        # Base exponential backoff
        delay = min(self.base_delay * (self.exponential_base**attempt), self.max_delay)

        # Adjust for error type
        if error_type == ErrorType.RATE_LIMIT:
            # Longer delay for rate limits
            delay *= 2

        # Add jitter to prevent thundering herd
        if self.jitter:
            delay *= 0.5 + random.random()

        return delay

    async def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)

                # Log success after retries
                if attempt > 0:
                    logger.info(f"Succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_error = e

                # Classify error
                error_type = ErrorClassifier.classify(e)

                # Check if we should retry
                if attempt >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exhausted")
                    break

                if not ErrorClassifier.is_retryable(error_type):
                    logger.error(f"Non-retryable error: {error_type.value}")
                    break

                # Calculate delay and wait
                delay = self.calculate_delay(attempt, error_type)
                logger.warning(f"Attempt {attempt + 1} failed ({error_type.value}). " f"Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

        # All retries exhausted
        if last_error is None:
            raise RuntimeError("Retry failed but no error was captured")
        raise last_error


async def with_retry(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs,
) -> Any:
    """
    Convenience function for executing with retry.

    Args:
        func: Async function to execute
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result
    """
    policy = EnhancedRetryPolicy(max_retries=max_retries, base_delay=base_delay)
    return await policy.execute_with_retry(func, *args, **kwargs)

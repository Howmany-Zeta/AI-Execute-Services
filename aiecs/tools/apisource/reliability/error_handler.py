"""
Smart Error Handler for API Providers

Provides intelligent error handling with:
- Classification of retryable vs non-retryable errors
- Exponential backoff retry strategy
- Agent-friendly error messages with recovery suggestions
- Detailed error context and history
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class SmartErrorHandler:
    """
    Intelligent error handler with retry logic and recovery suggestions.

    Automatically classifies errors, applies appropriate retry strategies,
    and provides actionable recovery suggestions for AI agents.
    """

    # Error types that can be retried
    RETRYABLE_ERRORS = [
        "timeout",
        "connection",
        "rate limit",
        "rate_limit",
        "429",  # Too Many Requests
        "500",  # Internal Server Error
        "502",  # Bad Gateway
        "503",  # Service Unavailable
        "504",  # Gateway Timeout
        "temporary",
        "transient",
    ]

    # Error types that should not be retried
    NON_RETRYABLE_ERRORS = [
        "authentication",
        "auth",
        "api key",
        "unauthorized",
        "401",  # Unauthorized
        "403",  # Forbidden
        "invalid",
        "not found",
        "404",  # Not Found
        "bad request",
        "400",  # Bad Request
    ]

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        """
        Initialize error handler.

        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Multiplier for exponential backoff
            initial_delay: Initial delay in seconds before first retry
            max_delay: Maximum delay between retries in seconds
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.initial_delay = initial_delay
        self.max_delay = max_delay

    def execute_with_retry(
        self,
        operation_func: Callable[[], Any],
        operation_name: str = "operation",
        provider_name: str = "provider",
    ) -> Dict[str, Any]:
        """
        Execute an operation with intelligent retry logic.

        Args:
            operation_func: Function to execute (should take no arguments)
            operation_name: Name of the operation for logging
            provider_name: Name of the provider for logging

        Returns:
            Dictionary with:
                - success: bool
                - data: result data if successful
                - error: error details if failed
                - retry_info: retry attempt information
        """
        last_error = None
        retry_info: Dict[str, Any] = {"attempts": 0, "errors": [], "recovery_suggestions": []}

        for attempt in range(self.max_retries):
            retry_info["attempts"] = attempt + 1

            try:
                # Execute the operation
                result = operation_func()

                # Success!
                if attempt > 0:
                    logger.info(f"{provider_name}.{operation_name} succeeded after " f"{attempt + 1} attempts")

                return {
                    "success": True,
                    "data": result,
                    "retry_info": retry_info,
                }

            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                error_type = self._classify_error(e, error_msg)

                # Record this error
                retry_info["errors"].append(
                    {
                        "attempt": attempt + 1,
                        "error": str(e),
                        "error_type": error_type,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                # Determine if we should retry
                is_retryable = self._is_retryable(error_msg, error_type)
                is_last_attempt = attempt == self.max_retries - 1

                if not is_retryable:
                    logger.warning(f"{provider_name}.{operation_name} failed with non-retryable " f"error: {error_type}")
                    break

                if is_last_attempt:
                    logger.error(f"{provider_name}.{operation_name} failed after " f"{self.max_retries} attempts")
                    break

                # Calculate wait time with exponential backoff
                wait_time = min(
                    self.initial_delay * (self.backoff_factor**attempt),
                    self.max_delay,
                )

                logger.info(f"{provider_name}.{operation_name} attempt {attempt + 1} failed " f"({error_type}), retrying in {wait_time:.1f}s...")

                time.sleep(wait_time)

        # All retries exhausted or non-retryable error
        if last_error is None:
            # This should never happen, but handle it gracefully
            last_error = Exception("Unknown error occurred")

        retry_info["recovery_suggestions"] = self._generate_recovery_suggestions(last_error, operation_name, provider_name)

        return {
            "success": False,
            "error": {
                "type": type(last_error).__name__,
                "message": str(last_error),
                "details": self._parse_error_details(last_error),
                "is_retryable": self._is_retryable(
                    str(last_error).lower(),
                    self._classify_error(last_error, str(last_error).lower()),
                ),
            },
            "retry_info": retry_info,
        }

    def _classify_error(self, error: Exception, error_msg: str) -> str:
        """
        Classify error type.

        Args:
            error: The exception object
            error_msg: Error message in lowercase

        Returns:
            Error classification string
        """
        # Check exception type
        error_class = type(error).__name__.lower()

        if "timeout" in error_class or "timeout" in error_msg:
            return "timeout"
        elif "connection" in error_class or "connection" in error_msg:
            return "connection"
        elif "rate" in error_msg and "limit" in error_msg:
            return "rate_limit"
        elif "429" in error_msg:
            return "rate_limit"
        elif "auth" in error_msg or "401" in error_msg or "403" in error_msg:
            return "authentication"
        elif "not found" in error_msg or "404" in error_msg:
            return "not_found"
        elif "bad request" in error_msg or "400" in error_msg:
            return "invalid_parameter"
        elif "500" in error_msg or "502" in error_msg or "503" in error_msg or "504" in error_msg:
            return "server_error"
        elif "invalid" in error_msg:
            return "invalid_parameter"
        else:
            return "unknown"

    def _is_retryable(self, error_msg: str, error_type: str) -> bool:
        """
        Determine if an error is retryable.

        Args:
            error_msg: Error message in lowercase
            error_type: Classified error type

        Returns:
            True if error is retryable
        """
        # Check non-retryable first (higher priority)
        for non_retryable in self.NON_RETRYABLE_ERRORS:
            if non_retryable in error_msg or non_retryable in error_type:
                return False

        # Check retryable
        for retryable in self.RETRYABLE_ERRORS:
            if retryable in error_msg or retryable in error_type:
                return True

        # Default: retry server errors and unknown errors
        return error_type in [
            "server_error",
            "timeout",
            "connection",
            "rate_limit",
        ]

    def _parse_error_details(self, error: Exception) -> Dict[str, Any]:
        """
        Extract detailed information from error.

        Args:
            error: The exception object

        Returns:
            Dictionary with error details
        """
        details = {"class": type(error).__name__, "message": str(error)}

        # Extract HTTP status code if available
        if hasattr(error, "response") and hasattr(error.response, "status_code"):
            details["status_code"] = error.response.status_code
            if hasattr(error.response, "text"):
                # Limit size
                details["response_body"] = error.response.text[:500]

        # Extract additional context
        if hasattr(error, "__cause__") and error.__cause__:
            details["cause"] = str(error.__cause__)

        return details

    def _generate_recovery_suggestions(self, error: Exception, operation_name: str, provider_name: str) -> List[str]:
        """
        Generate actionable recovery suggestions for the error.

        Args:
            error: The exception object
            operation_name: Name of the failed operation
            provider_name: Name of the provider

        Returns:
            List of recovery suggestion strings
        """
        suggestions = []
        error_msg = str(error).lower()
        error_type = self._classify_error(error, error_msg)

        if error_type == "authentication":
            suggestions.extend(
                [
                    f"Check that your {provider_name.upper()} API key is valid and properly configured",
                    f"Verify the API key environment variable {provider_name.upper()}_API_KEY is set",
                    "Confirm the API key has not expired or been revoked",
                    f"Ensure you have the necessary permissions for the {operation_name} operation",
                ]
            )

        elif error_type == "rate_limit":
            suggestions.extend(
                [
                    "Wait before making more requests (rate limit exceeded)",
                    "Consider using a different provider if available",
                    "Reduce the frequency of requests or implement request batching",
                    "Check if you can upgrade your API plan for higher rate limits",
                    "Enable caching to reduce API calls",
                ]
            )

        elif error_type == "not_found":
            suggestions.extend(
                [
                    f"Verify the resource ID or parameter values are correct for {provider_name}",
                    "Use the search or list operations to find valid resource IDs",
                    "Check that the resource exists and is accessible with your credentials",
                    f"Review the {provider_name} API documentation for correct resource identifiers",
                ]
            )

        elif error_type == "invalid_parameter":
            suggestions.extend(
                [
                    f"Check the operation schema for {operation_name} to see required parameters",
                    "Review parameter types and value formats",
                    f"Use get_operation_schema('{operation_name}') to see valid parameters and examples",
                    "Verify parameter names are spelled correctly",
                ]
            )

        elif error_type == "timeout":
            suggestions.extend(
                [
                    "Try again with a smaller date range or result limit",
                    "Increase the timeout setting in the provider configuration",
                    "Check your network connection",
                    "The API service may be experiencing high load, try again later",
                ]
            )

        elif error_type == "connection":
            suggestions.extend(
                [
                    "Check your internet connection",
                    "Verify the API endpoint is accessible",
                    "Check if there are any firewall or proxy issues",
                    "The API service may be temporarily unavailable",
                ]
            )

        elif error_type == "server_error":
            suggestions.extend(
                [
                    "The API service is experiencing issues, try again later",
                    "Check the API status page for known outages",
                    "Try a different provider if available",
                    "Reduce the complexity of your request",
                ]
            )

        else:
            suggestions.extend(
                [
                    "Review the error message for specific details",
                    f"Check the {provider_name} API documentation for {operation_name}",
                    "Verify all required parameters are provided",
                    "Try a simpler query to isolate the issue",
                ]
            )

        return suggestions

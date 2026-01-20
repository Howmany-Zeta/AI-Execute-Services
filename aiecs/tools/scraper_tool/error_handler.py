"""Agent-friendly error handling for ScraperTool."""

from typing import Any, Dict, List, Optional

from .constants import (
    BlockedError,
    CircuitBreakerOpenError,
    HttpError,
    ParsingError,
    RateLimitError,
    RenderingError,
)


class ErrorHandler:
    """Formats exceptions into agent-friendly error responses."""

    def format_error(
        self, error: Exception, context: Dict = None
    ) -> Dict[str, Any]:
        """
        Format an exception into a structured error response.

        Args:
            error: The exception to format
            context: Optional context about the operation

        Returns:
            Dict with error_type, message, severity, can_retry,
            retry_after, and suggested_actions
        """
        context = context or {}

        if isinstance(error, RateLimitError):
            return self._handle_rate_limit(error, context)
        elif isinstance(error, CircuitBreakerOpenError):
            return self._handle_circuit_breaker(error, context)
        elif isinstance(error, BlockedError):
            return self._handle_blocked(error, context)
        elif isinstance(error, HttpError):
            return self._handle_http_error(error, context)
        elif isinstance(error, ParsingError):
            return self._handle_parsing(error, context)
        elif isinstance(error, RenderingError):
            return self._handle_rendering(error, context)
        else:
            return self._handle_unknown(error, context)

    def _handle_http_error(
        self, error: HttpError, context: Dict
    ) -> Dict[str, Any]:
        status = error.status_code or 0
        is_server_error = 500 <= status < 600
        is_client_error = 400 <= status < 500

        if is_server_error:
            return {
                "error_type": "http_error",
                "message": f"Server error ({status}): The target server encountered an issue",
                "severity": "medium",
                "can_retry": True,
                "retry_after": 30,
                "suggested_actions": [
                    "Wait and retry the request",
                    "Try a different URL if available",
                ],
            }
        elif is_client_error:
            return {
                "error_type": "http_error",
                "message": f"Client error ({status}): {error.message}",
                "severity": "high" if status in (401, 403, 404) else "medium",
                "can_retry": status in (408, 429),
                "retry_after": 60 if status == 429 else None,
                "suggested_actions": self._get_client_error_actions(status),
            }
        return {
            "error_type": "http_error",
            "message": f"HTTP error: {error.message}",
            "severity": "medium",
            "can_retry": True,
            "retry_after": 10,
            "suggested_actions": ["Retry the request"],
        }

    def _get_client_error_actions(self, status: int) -> List[str]:
        actions = {
            401: ["Check if authentication is required", "Verify credentials"],
            403: ["Access forbidden - try a different approach", "Check robots.txt"],
            404: ["URL not found - verify the URL is correct", "Search for alternative URLs"],
            429: ["Rate limited - wait before retrying", "Reduce request frequency"],
        }
        return actions.get(status, ["Check the URL and try again"])

    def _handle_rate_limit(
        self, error: RateLimitError, context: Dict
    ) -> Dict[str, Any]:
        retry_after = error.retry_after or 60
        return {
            "error_type": "rate_limit",
            "message": f"Rate limit exceeded: {error.message}",
            "severity": "low",
            "can_retry": True,
            "retry_after": retry_after,
            "suggested_actions": [
                f"Wait {retry_after} seconds before retrying",
                "Consider reducing request frequency",
            ],
        }

    def _handle_circuit_breaker(
        self, error: CircuitBreakerOpenError, context: Dict
    ) -> Dict[str, Any]:
        return {
            "error_type": "circuit_breaker",
            "message": f"Domain temporarily unavailable: {error.message}",
            "severity": "medium",
            "can_retry": True,
            "retry_after": 120,
            "suggested_actions": [
                "Wait for the circuit breaker to reset",
                "Try a different domain if possible",
            ],
        }

    def _handle_blocked(
        self, error: BlockedError, context: Dict
    ) -> Dict[str, Any]:
        return {
            "error_type": "blocked",
            "message": f"Bot detection triggered: {error.message}",
            "severity": "high",
            "can_retry": False,
            "retry_after": None,
            "suggested_actions": [
                "This site has bot protection",
                "Try a different source for this information",
                "Consider if this content is publicly accessible",
            ],
        }

    def _handle_parsing(
        self, error: ParsingError, context: Dict
    ) -> Dict[str, Any]:
        return {
            "error_type": "parsing_error",
            "message": f"Content parsing failed: {error.message}",
            "severity": "medium",
            "can_retry": False,
            "retry_after": None,
            "suggested_actions": [
                "The page content could not be parsed",
                "Try fetching raw HTML instead",
                "Check if the URL returns valid content",
            ],
        }

    def _handle_rendering(
        self, error: RenderingError, context: Dict
    ) -> Dict[str, Any]:
        return {
            "error_type": "rendering_error",
            "message": f"JavaScript rendering failed: {error.message}",
            "severity": "medium",
            "can_retry": True,
            "retry_after": 10,
            "suggested_actions": [
                "Page requires JavaScript that failed to execute",
                "Retry with increased timeout",
                "Try fetching without JS rendering",
            ],
        }

    def _handle_unknown(
        self, error: Exception, context: Dict
    ) -> Dict[str, Any]:
        return {
            "error_type": "unknown_error",
            "message": f"Unexpected error: {str(error)}",
            "severity": "high",
            "can_retry": True,
            "retry_after": 30,
            "suggested_actions": [
                "An unexpected error occurred",
                "Retry the operation",
                "If the error persists, try a different approach",
            ],
        }


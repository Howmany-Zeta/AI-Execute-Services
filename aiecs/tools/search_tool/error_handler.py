"""
Agent-Friendly Error Handling

This module formats errors in an agent-friendly way with clear messages,
suggested actions, and alternative approaches.
"""

from typing import Any, Dict

from .constants import (
    QuotaExceededError,
    AuthenticationError,
    RateLimitError,
    CircuitBreakerOpenError,
    ValidationError,
)


class AgentFriendlyErrorHandler:
    """Formats errors for agent consumption with actionable suggestions"""

    def format_error_for_agent(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format error for agent-friendly consumption.

        Args:
            error: The exception that occurred
            context: Context information (circuit breaker timeout, etc.)

        Returns:
            Structured error information dictionary
        """
        error_response = {
            "error_type": "unknown",
            "severity": "medium",
            "user_message": "",
            "technical_details": str(error),
            "suggested_actions": [],
            "alternative_approaches": [],
            "can_retry": False,
            "estimated_recovery_time": None,
        }

        error_str = str(error).lower()
        error_type = type(error).__name__

        # Handle specific error types
        if isinstance(error, QuotaExceededError) or "quota" in error_str or "rate limit" in error_str:
            self._handle_quota_exceeded(error_response)

        elif isinstance(error, AuthenticationError) or "auth" in error_str or "credential" in error_str:
            self._handle_authentication_error(error_response)

        elif isinstance(error, RateLimitError):
            self._handle_rate_limit_error(error_response)

        elif isinstance(error, CircuitBreakerOpenError) or "circuit breaker" in error_str:
            self._handle_circuit_breaker_error(error_response, context)

        elif isinstance(error, ValidationError) or "invalid" in error_str or "validation" in error_str:
            self._handle_validation_error(error_response)

        elif "timeout" in error_str or "connection" in error_str or "network" in error_str:
            self._handle_network_error(error_response)

        elif "no results" in error_str or "not found" in error_str:
            self._handle_no_results(error_response)

        else:
            # Generic error handling
            error_response.update(
                {
                    "error_type": error_type,
                    "severity": "medium",
                    "user_message": f"An unexpected error occurred: {str(error)}",
                    "suggested_actions": [
                        "Check your query parameters",
                        "Try simplifying the query",
                        "Retry the operation",
                    ],
                    "can_retry": True,
                }
            )

        return error_response

    def _handle_quota_exceeded(self, response: Dict[str, Any]):
        """Handle quota exceeded errors"""
        response.update(
            {
                "error_type": "quota_exceeded",
                "severity": "high",
                "user_message": ("Search API quota has been exceeded. " "The service has temporarily reached its usage limit."),
                "suggested_actions": [
                    "Wait 60-120 seconds before retrying",
                    "Reduce the number of results requested",
                    "Use more specific queries to get better results with fewer searches",
                    "Check if cached results are available",
                ],
                "alternative_approaches": [
                    "Use the scraper tool to extract information from known URLs",
                    "Query specific authoritative domains using site: operator",
                    "Defer non-urgent searches to later",
                ],
                "can_retry": True,
                "estimated_recovery_time": "1-2 minutes",
            }
        )

    def _handle_authentication_error(self, response: Dict[str, Any]):
        """Handle authentication errors"""
        response.update(
            {
                "error_type": "authentication_failed",
                "severity": "high",
                "user_message": ("Search API authentication failed. " "The API credentials may be invalid or expired."),
                "suggested_actions": [
                    "Verify that GOOGLE_API_KEY is set correctly in environment",
                    "Check that GOOGLE_CSE_ID is valid",
                    "Ensure API key has not expired",
                    "Verify API key has Custom Search API enabled",
                ],
                "alternative_approaches": [
                    "Use alternative data sources (apisource_tool)",
                    "Request manual search from user",
                ],
                "can_retry": False,
                "estimated_recovery_time": None,
            }
        )

    def _handle_rate_limit_error(self, response: Dict[str, Any]):
        """Handle rate limit errors"""
        response.update(
            {
                "error_type": "rate_limit_exceeded",
                "severity": "medium",
                "user_message": ("Rate limit has been exceeded. " "Too many requests in a short time period."),
                "suggested_actions": [
                    "Wait for the suggested time before retrying",
                    "Reduce request frequency",
                    "Use cached results when available",
                    "Batch similar queries together",
                ],
                "alternative_approaches": [
                    "Use cached or historical data",
                    "Prioritize critical searches",
                ],
                "can_retry": True,
                "estimated_recovery_time": "As indicated in error message",
            }
        )

    def _handle_circuit_breaker_error(self, response: Dict[str, Any], context: Dict[str, Any]):
        """Handle circuit breaker open errors"""
        timeout = context.get("circuit_breaker_timeout", 60)

        response.update(
            {
                "error_type": "circuit_breaker_open",
                "severity": "high",
                "user_message": ("Search service is temporarily unavailable due to repeated failures. " "The circuit breaker has been triggered for protection."),
                "suggested_actions": [
                    f"Wait {timeout} seconds for circuit to reset",
                    "Check search service status",
                    "Review recent error logs",
                ],
                "alternative_approaches": [
                    "Use alternative data sources",
                    "Defer search to later",
                    "Use cached or historical data",
                ],
                "can_retry": True,
                "estimated_recovery_time": f"{timeout} seconds",
            }
        )

    def _handle_validation_error(self, response: Dict[str, Any]):
        """Handle validation errors"""
        response.update(
            {
                "error_type": "invalid_query",
                "severity": "low",
                "user_message": ("The search query or parameters are invalid. " "Please check the query format."),
                "suggested_actions": [
                    "Simplify the query - remove special characters",
                    "Check that all parameters are within valid ranges",
                    "Ensure query is not empty",
                    "Review query syntax for search operators",
                ],
                "alternative_approaches": [
                    "Break complex query into simpler parts",
                    "Use basic search without advanced operators",
                ],
                "can_retry": True,
                "estimated_recovery_time": "immediate (after fixing query)",
            }
        )

    def _handle_network_error(self, response: Dict[str, Any]):
        """Handle network-related errors"""
        response.update(
            {
                "error_type": "network_error",
                "severity": "medium",
                "user_message": ("Network connection to search API failed. " "This is usually a temporary issue."),
                "suggested_actions": [
                    "Retry the search in 5-10 seconds",
                    "Check internet connectivity",
                    "Try with a shorter timeout if query is complex",
                ],
                "alternative_approaches": [
                    "Use cached results if available",
                    "Try alternative search parameters",
                ],
                "can_retry": True,
                "estimated_recovery_time": "10-30 seconds",
            }
        )

    def _handle_no_results(self, response: Dict[str, Any]):
        """Handle no results found"""
        response.update(
            {
                "error_type": "no_results",
                "severity": "low",
                "user_message": ("No search results found for the query. " "Try broadening your search terms."),
                "suggested_actions": [
                    "Remove overly specific terms",
                    "Try synonyms or related terms",
                    "Remove date restrictions",
                    "Broaden the search scope",
                ],
                "alternative_approaches": [
                    "Search for related topics",
                    "Try different search engines or sources",
                    "Break down into sub-queries",
                ],
                "can_retry": True,
                "estimated_recovery_time": "immediate (with modified query)",
            }
        )

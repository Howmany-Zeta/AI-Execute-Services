"""
Simplified constants and exceptions for Scraper Tool.
"""

from enum import Enum


class ContentType(str, Enum):
    """Content types for responses"""
    HTML = "html"
    JSON = "json"
    TEXT = "text"


class OutputFormat(str, Enum):
    """Output format options"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ============================================================================
# Exceptions
# ============================================================================

class ScraperToolError(Exception):
    """Base exception for ScraperTool errors"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class HttpError(ScraperToolError):
    """HTTP request/response errors"""
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message, details)
        self.status_code = status_code


class RateLimitError(ScraperToolError):
    """Rate limit exceeded"""
    def __init__(self, message: str, retry_after: int = None, details: dict = None):
        super().__init__(message, details)
        self.retry_after = retry_after


class CircuitBreakerOpenError(ScraperToolError):
    """Circuit breaker is open"""
    pass


class ParsingError(ScraperToolError):
    """Content parsing errors"""
    pass


class RenderingError(ScraperToolError):
    """Page rendering errors"""
    pass


class BlockedError(ScraperToolError):
    """Bot detection block errors"""
    def __init__(self, message: str, block_type: str = None, details: dict = None):
        super().__init__(message, details)
        self.block_type = block_type


# ============================================================================
# Constants
# ============================================================================

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


__all__ = [
    "ContentType",
    "OutputFormat", 
    "CircuitState",
    "ScraperToolError",
    "HttpError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    "ParsingError",
    "RenderingError",
    "BlockedError",
    "DEFAULT_TIMEOUT",
    "MAX_RETRIES",
]


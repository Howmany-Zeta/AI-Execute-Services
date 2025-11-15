"""
Constants, Enums, and Exception Classes for Search Tool

This module contains all the shared constants, enumeration types, and
custom exception classes used across the search tool package.
"""

from enum import Enum


# ============================================================================
# Enums
# ============================================================================


class SearchType(str, Enum):
    """Supported search types"""

    WEB = "web"
    IMAGE = "image"
    NEWS = "news"
    VIDEO = "video"


class SafeSearch(str, Enum):
    """Safe search levels"""

    OFF = "off"
    MEDIUM = "medium"
    HIGH = "high"


class ImageSize(str, Enum):
    """Image size filters"""

    ICON = "icon"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"
    XXLARGE = "xxlarge"
    HUGE = "huge"


class ImageType(str, Enum):
    """Image type filters"""

    CLIPART = "clipart"
    FACE = "face"
    LINEART = "lineart"
    STOCK = "stock"
    PHOTO = "photo"
    ANIMATED = "animated"


class ImageColorType(str, Enum):
    """Image color type filters"""

    COLOR = "color"
    GRAY = "gray"
    MONO = "mono"
    TRANS = "trans"


class CircuitState(str, Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class QueryIntentType(str, Enum):
    """Query intent types"""

    DEFINITION = "definition"
    HOW_TO = "how_to"
    COMPARISON = "comparison"
    FACTUAL = "factual"
    RECENT_NEWS = "recent_news"
    ACADEMIC = "academic"
    PRODUCT = "product"
    GENERAL = "general"


class CredibilityLevel(str, Enum):
    """Result credibility levels"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ============================================================================
# Exception Hierarchy
# ============================================================================


class SearchToolError(Exception):
    """Base exception for SearchTool errors"""


class AuthenticationError(SearchToolError):
    """Authentication-related errors"""


class QuotaExceededError(SearchToolError):
    """API quota exceeded"""


class RateLimitError(SearchToolError):
    """Rate limit exceeded"""


class CircuitBreakerOpenError(SearchToolError):
    """Circuit breaker is open"""


class SearchAPIError(SearchToolError):
    """Search API errors"""


class ValidationError(SearchToolError):
    """Input validation errors"""


class CacheError(SearchToolError):
    """Cache-related errors"""

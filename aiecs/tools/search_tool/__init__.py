"""
Enhanced Search Tool Package

A comprehensive, production-ready web search tool that integrates Google Custom Search API
with advanced features including:

- Result quality scoring and ranking
- Query intent analysis and optimization
- Result deduplication
- Context-aware search with history tracking
- Intelligent Redis caching with intent-aware TTL
- Comprehensive metrics and monitoring
- Agent-friendly error handling

Features:
- Multiple search types: web, image, news, video
- Dual authentication: API key and service account
- Rate limiting with token bucket algorithm
- Circuit breaker pattern for API resilience
- Intelligent caching with Redis backend
- Quality analysis with authority, relevance, and freshness scoring
- Query enhancement based on detected intent
- Structured result summaries
- Search context tracking and preference learning
- Enhanced metrics and health scoring
- Agent-optimized error messages with actionable suggestions

Usage:
    from aiecs.tools.search_tool import SearchTool

    # Create search tool instance
    search_tool = SearchTool()

    # Perform enhanced web search
    results = search_tool.search_web(
        query="machine learning tutorial",
        auto_enhance=True,
        return_summary=True
    )

    # Access results and quality analysis
    for result in results['results']:
        print(f"Title: {result['title']}")
        print(f"Quality: {result['_quality_summary']['score']:.2f}")
        print(f"Credibility: {result['_quality_summary']['level']}")

    # Check metrics
    print(search_tool.get_metrics_report())
"""

from aiecs.tools import register_tool
from .core import SearchTool
from .constants import (
    SearchType,
    SafeSearch,
    ImageSize,
    ImageType,
    ImageColorType,
    QueryIntentType,
    CredibilityLevel,
    CircuitState,
    # Exceptions
    SearchToolError,
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    CircuitBreakerOpenError,
    SearchAPIError,
    ValidationError,
    CacheError,
)

# Register the tool with the AIECS tool registry
# Note: Tool is registered as "search" (not "search_tool") for consistency
register_tool("search")(SearchTool)

__all__ = [
    # Main class
    "SearchTool",
    # Enums
    "SearchType",
    "SafeSearch",
    "ImageSize",
    "ImageType",
    "ImageColorType",
    "QueryIntentType",
    "CredibilityLevel",
    "CircuitState",
    # Exceptions
    "SearchToolError",
    "AuthenticationError",
    "QuotaExceededError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    "SearchAPIError",
    "ValidationError",
    "CacheError",
]

__version__ = "2.0.0"

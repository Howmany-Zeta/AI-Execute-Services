"""
Scraper Tool - Simplified web scraper for AI agents.

AI agents only need to call: fetch(url, requirements)
All configuration is handled via environment variables with SCRAPER_TOOL_ prefix.

Example:
    >>> from aiecs.tools.scraper_tool import ScraperTool
    >>> tool = ScraperTool()
    >>> result = await tool.fetch("https://example.com", "提取文章标题")

Configuration (environment variables):
    SCRAPER_TOOL_TIMEOUT=30
    SCRAPER_TOOL_IMPERSONATE=chrome120
    SCRAPER_TOOL_PROXY=http://proxy:8080
    SCRAPER_TOOL_REQUESTS_PER_MINUTE=30
    SCRAPER_TOOL_ENABLE_CACHE=true
    SCRAPER_TOOL_ENABLE_JS_RENDER=false
"""

__version__ = "2.0.0"

from .constants import (
    ContentType,
    OutputFormat,
    CircuitState,
    ScraperToolError,
    HttpError,
    RateLimitError,
    CircuitBreakerOpenError,
    ParsingError,
    RenderingError,
    BlockedError,
)

from .schemas import FetchSchema

from .core import ScraperTool, ScraperToolConfig

__all__ = [
    # Version
    "__version__",
    # Main class
    "ScraperTool",
    "ScraperToolConfig",
    # Schema
    "FetchSchema",
    # Enums
    "ContentType",
    "OutputFormat",
    "CircuitState",
    # Exceptions
    "ScraperToolError",
    "HttpError",
    "RateLimitError",
    "CircuitBreakerOpenError",
    "ParsingError",
    "RenderingError",
    "BlockedError",
]


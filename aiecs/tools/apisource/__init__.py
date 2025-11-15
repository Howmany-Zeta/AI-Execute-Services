"""
APISource Tool - Unified API Data Source Interface

A comprehensive tool for querying external API data sources with advanced features:
- Multi-provider support (FRED, World Bank, News API, Census Bureau)
- Intelligent query understanding and parameter enhancement
- Cross-provider data fusion
- Automatic fallback and retry logic
- Advanced search with relevance ranking
- Comprehensive metrics and health monitoring

Usage:
    from aiecs.tools.apisource import APISourceTool

    tool = APISourceTool({
        'fred_api_key': 'YOUR_KEY',
        'enable_fallback': True,
        'enable_query_enhancement': True
    })

    # Query with natural language
    result = tool.query(
        provider='fred',
        operation='get_series_observations',
        params={'series_id': 'GDP'},
        query_text="Get GDP data for last 5 years"
    )

    # Multi-provider search with fusion
    results = tool.search(
        query="unemployment trends",
        enable_fusion=True
    )
"""

from aiecs.tools.apisource.tool import (
    APISourceTool,
    APISourceError,
    ProviderNotFoundError,
    APIRateLimitError,
    APIAuthenticationError,
)

# Import providers for convenience
from aiecs.tools.apisource.providers import (
    BaseAPIProvider,
    get_provider,
    list_providers,
    PROVIDER_REGISTRY,
)

# Import intelligence components
from aiecs.tools.apisource.intelligence import (
    QueryIntentAnalyzer,
    QueryEnhancer,
    DataFusionEngine,
    SearchEnhancer,
)

# Import reliability components
from aiecs.tools.apisource.reliability import (
    SmartErrorHandler,
    FallbackStrategy,
)

# Import monitoring components
from aiecs.tools.apisource.monitoring import DetailedMetrics

# Import utilities
from aiecs.tools.apisource.utils import DataValidator

__version__ = "2.0.0"

__all__ = [
    # Main tool
    "APISourceTool",
    # Exceptions
    "APISourceError",
    "ProviderNotFoundError",
    "APIRateLimitError",
    "APIAuthenticationError",
    # Providers
    "BaseAPIProvider",
    "get_provider",
    "list_providers",
    "PROVIDER_REGISTRY",
    # Intelligence
    "QueryIntentAnalyzer",
    "QueryEnhancer",
    "DataFusionEngine",
    "SearchEnhancer",
    # Reliability
    "SmartErrorHandler",
    "FallbackStrategy",
    # Monitoring
    "DetailedMetrics",
    # Utils
    "DataValidator",
]

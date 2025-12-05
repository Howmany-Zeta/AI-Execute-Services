"""
API Source Tool

Unified interface for querying various external real-time API data sources including
economic indicators, news, public databases, and custom APIs with plugin architecture.

Enhanced Features:
- Auto-discovery of API providers
- Unified query interface with intelligent parameter enhancement
- Intelligent caching with TTL strategies
- Cross-provider data fusion
- Automatic fallback to alternative providers
- Advanced search with relevance scoring
- Comprehensive error handling with recovery suggestions
- Detailed metrics and health monitoring
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import (
    cache_result_with_strategy,
    cache_result,
    measure_execution_time,
)
from aiecs.tools.apisource.providers import (
    get_provider,
    list_providers,
    PROVIDER_REGISTRY,
)
from aiecs.tools.apisource.intelligence import (
    QueryIntentAnalyzer,
    QueryEnhancer,
    DataFusionEngine,
    SearchEnhancer,
)
from aiecs.tools.apisource.reliability import FallbackStrategy

logger = logging.getLogger(__name__)


# Custom exceptions
class APISourceError(Exception):
    """Base exception for API Source Tool errors"""


class ProviderNotFoundError(APISourceError):
    """Raised when requested provider is not found"""


class APIRateLimitError(APISourceError):
    """Raised when API rate limit is exceeded"""


class APIAuthenticationError(APISourceError):
    """Raised when API authentication fails"""


@register_tool("apisource")
class APISourceTool(BaseTool):
    """
    Query external real-time API data sources including economic indicators, news, public databases, and custom APIs.

    Supports multiple data providers through a plugin architecture:
    - FRED: Federal Reserve Economic Data (US economic indicators)
    - World Bank: Global development indicators
    - News API: News articles and headlines
    - Census: US Census Bureau demographic and economic data

    Provides unified interface with automatic rate limiting, caching, and error handling.
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the API Source Tool
        
        Automatically reads from environment variables with APISOURCE_TOOL_ prefix.
        Example: APISOURCE_TOOL_FRED_API_KEY -> fred_api_key
        
        Sensitive fields (API keys) are loaded from .env files via dotenv.
        """

        model_config = SettingsConfigDict(env_prefix="APISOURCE_TOOL_")

        cache_ttl: int = Field(
            default=300,
            description="Cache time-to-live in seconds for API responses",
        )
        default_timeout: int = Field(
            default=30,
            description="Default timeout in seconds for API requests",
        )
        max_retries: int = Field(
            default=3,
            description="Maximum number of retries for failed requests",
        )
        enable_rate_limiting: bool = Field(
            default=True,
            description="Whether to enable rate limiting for API requests",
        )
        enable_fallback: bool = Field(
            default=True,
            description="Enable automatic fallback to alternative providers",
        )
        enable_data_fusion: bool = Field(
            default=True,
            description="Enable cross-provider data fusion in search",
        )
        enable_query_enhancement: bool = Field(
            default=True,
            description="Enable intelligent query parameter enhancement",
        )
        fred_api_key: Optional[str] = Field(
            default=None,
            description="API key for Federal Reserve Economic Data (FRED)",
        )
        newsapi_api_key: Optional[str] = Field(default=None, description="API key for News API")
        census_api_key: Optional[str] = Field(default=None, description="API key for US Census Bureau")

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize API Source Tool with enhanced intelligence features.

        Args:
            config: Configuration dictionary with API keys and settings
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/apisource.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Sensitive fields (API keys) are loaded from .env files.
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            self.logger.addHandler(handler)

        # Initialize intelligence components
        self.query_analyzer = QueryIntentAnalyzer()
        self.query_enhancer = QueryEnhancer(self.query_analyzer)
        self.data_fusion = DataFusionEngine()
        self.fallback_strategy = FallbackStrategy()
        self.search_enhancer = SearchEnhancer(relevance_weight=0.5, popularity_weight=0.3, recency_weight=0.2)

        # Load providers (they auto-discover on import)
        self._providers: Dict[str, Any] = {}
        self._load_providers()

    def _load_providers(self):
        """Load and cache provider instances"""
        for provider_name in PROVIDER_REGISTRY.keys():
            try:
                # Create provider config from tool config
                provider_config = {
                    "timeout": self.config.default_timeout,
                }

                # Add provider-specific API key if available
                api_key_attr = f"{provider_name}_api_key"
                if hasattr(self.config, api_key_attr):
                    api_key = getattr(self.config, api_key_attr)
                    if api_key:
                        provider_config["api_key"] = api_key

                provider = get_provider(provider_name, provider_config)
                self._providers[provider_name] = provider
                self.logger.debug(f"Loaded provider: {provider_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load provider {provider_name}: {e}")

    @classmethod
    def _discover_provider_operations(cls) -> List[Dict[str, Any]]:
        """
        Discover all exposed operations from all registered providers.

        This method enables the LangChain adapter to automatically create individual
        tools for each provider operation, giving AI agents fine-grained visibility
        into provider capabilities.

        Returns:
            List of operation dictionaries, each containing:
                - name: Full operation name (e.g., 'fred_get_series_observations')
                - schema: Pydantic schema for the operation
                - description: Operation description
                - method: Callable method to execute the operation
        """
        operations = []

        for provider_name, provider_class in PROVIDER_REGISTRY.items():
            try:
                # Get exposed operations from provider
                exposed_ops = provider_class.get_exposed_operations()

                for op in exposed_ops:
                    # Convert Dict-based schema to Pydantic schema
                    pydantic_schema = cls._convert_dict_schema_to_pydantic(op["schema"], f"{provider_name}_{op['name']}") if op["schema"] else None

                    # Create operation info
                    operation_info = {
                        "name": f"{provider_name}_{op['name']}",
                        "schema": pydantic_schema,
                        "description": op["description"],
                        # Store original operation name
                        "method_name": op["name"],
                        "provider_name": provider_name,  # Store provider name
                    }

                    operations.append(operation_info)
                    logger.debug(f"Discovered provider operation: {operation_info['name']}")

            except Exception as e:
                logger.warning(f"Error discovering operations for provider {provider_name}: {e}")

        logger.info(f"Discovered {len(operations)} provider operations across {len(PROVIDER_REGISTRY)} providers")
        return operations

    @staticmethod
    def _convert_dict_schema_to_pydantic(dict_schema: Optional[Dict[str, Any]], schema_name: str) -> Optional[type[BaseModel]]:
        """
        Convert Dict-based provider schema to Pydantic BaseModel schema.

        This enables provider operation schemas to be used by the LangChain adapter
        and exposed to AI agents with full type information.

        Args:
            dict_schema: Dictionary schema from provider.get_operation_schema()
            schema_name: Name for the generated Pydantic schema class

        Returns:
            Pydantic BaseModel class or None if schema is invalid
        """
        if not dict_schema or "parameters" not in dict_schema:
            return None

        try:
            from pydantic import create_model

            fields = {}
            parameters = dict_schema.get("parameters", {})

            for param_name, param_info in parameters.items():
                # Determine field type from schema
                param_type_str = param_info.get("type", "string")

                # Map schema types to Python types
                type_mapping = {
                    "string": str,
                    "integer": int,
                    "number": float,
                    "boolean": bool,
                    "array": List[Any],
                    "object": Dict[str, Any],
                }

                field_type = type_mapping.get(param_type_str, str)

                # Make optional if not required
                is_required = param_info.get("required", False)
                if not is_required:
                    field_type = Optional[field_type]  # type: ignore[assignment]

                # Build field description
                description_parts = [param_info.get("description", "")]

                # Add examples if available
                if "examples" in param_info and param_info["examples"]:
                    examples_str = ", ".join(str(ex) for ex in param_info["examples"][:3])
                    description_parts.append(f"Examples: {examples_str}")

                # Add validation info if available
                if "validation" in param_info:
                    validation = param_info["validation"]
                    if "pattern" in validation:
                        description_parts.append(f"Pattern: {validation['pattern']}")
                    if "min" in validation or "max" in validation:
                        range_str = f"Range: {validation.get('min', 'any')}-{validation.get('max', 'any')}"
                        description_parts.append(range_str)

                full_description = ". ".join(filter(None, description_parts))

                # Create field with default value if not required
                if is_required:
                    fields[param_name] = (
                        field_type,
                        Field(description=full_description),
                    )
                else:
                    fields[param_name] = (
                        field_type,
                        Field(default=None, description=full_description),
                    )

            # Create the Pydantic model
            # Dynamic model creation - use type ignore for create_model overload issues
            schema_class = create_model(  # type: ignore[call-overload]
                f"{schema_name.replace('_', '').title()}Schema",
                __doc__=dict_schema.get("description", ""),
                **fields,
            )

            logger.debug(f"Created Pydantic schema: {schema_class.__name__} with {len(fields)} fields")
            return schema_class

        except Exception as e:
            logger.error(f"Error converting schema {schema_name}: {e}")
            return None

    def _create_query_ttl_strategy(self):
        """
        Create intelligent TTL strategy for API query results.

        This strategy calculates TTL based on:
        1. Data type (historical vs real-time)
        2. Provider characteristics
        3. Operation type
        4. Data quality and freshness

        Returns:
            Callable: TTL strategy function compatible with cache_result_with_strategy
        """

        def calculate_query_ttl(result: Any, args: tuple, kwargs: dict) -> int:
            """
            Calculate intelligent TTL for API query results.

            Args:
                result: The query result dictionary
                args: Positional arguments (not used)
                kwargs: Keyword arguments containing provider, operation, params

            Returns:
                int: TTL in seconds
            """
            kwargs.get("provider", "")
            operation = kwargs.get("operation", "")

            # Default TTL
            default_ttl = 600  # 10 minutes

            # Extract metadata if available
            metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
            quality = metadata.get("quality", {})
            freshness_hours = quality.get("freshness_hours", 24)

            # Historical time series data - cache longer
            if operation in [
                "get_series_observations",
                "get_indicator",
                "get_series",
            ]:
                # Check if data is historical (older than 24 hours)
                if freshness_hours > 24:
                    # Historical data: cache for 7 days
                    ttl = 86400 * 7
                    self.logger.debug(f"Historical data detected, TTL: {ttl}s (7 days)")
                    return ttl
                else:
                    # Recent data: cache for 1 hour
                    ttl = 3600
                    self.logger.debug(f"Recent time series data, TTL: {ttl}s (1 hour)")
                    return ttl

            # News data - cache very short time
            elif operation in [
                "get_top_headlines",
                "search_everything",
                "get_everything",
            ]:
                ttl = 300  # 5 minutes
                self.logger.debug(f"News data, TTL: {ttl}s (5 minutes)")
                return ttl

            # Metadata operations - cache longer
            elif operation in [
                "list_countries",
                "list_indicators",
                "get_sources",
                "get_categories",
                "get_releases",
                "list_sources",
            ]:
                ttl = 86400  # 1 day
                self.logger.debug(f"Metadata operation, TTL: {ttl}s (1 day)")
                return ttl

            # Search operations - moderate cache time
            elif operation in ["search_series", "search_indicators", "search"]:
                ttl = 600  # 10 minutes
                self.logger.debug(f"Search operation, TTL: {ttl}s (10 minutes)")
                return ttl

            # Info operations - cache longer
            elif operation in ["get_series_info", "get_indicator_info"]:
                ttl = 3600  # 1 hour
                self.logger.debug(f"Info operation, TTL: {ttl}s (1 hour)")
                return ttl

            # Default
            self.logger.debug(f"Default TTL: {default_ttl}s (10 minutes)")
            return default_ttl

        return calculate_query_ttl

    def _create_search_ttl_strategy(self):
        """
        Create intelligent TTL strategy for multi-provider search results.

        This strategy calculates TTL based on:
        1. Query intent type
        2. Number of providers queried
        3. Whether data fusion was applied

        Returns:
            Callable: TTL strategy function compatible with cache_result_with_strategy
        """

        def calculate_search_ttl(result: Any, args: tuple, kwargs: dict) -> int:
            """
            Calculate intelligent TTL for search results.

            Args:
                result: The search result dictionary
                args: Positional arguments (not used)
                kwargs: Keyword arguments containing query, providers, etc.

            Returns:
                int: TTL in seconds
            """
            # Default TTL for search results
            default_ttl = 300  # 5 minutes

            if not isinstance(result, dict):
                return default_ttl

            # Extract metadata
            metadata = result.get("metadata", {})
            intent_analysis = metadata.get("intent_analysis", {})
            intent_type = intent_analysis.get("intent_type", "general")

            # Adjust TTL based on intent type
            if intent_type in ["metadata", "definition"]:
                # Metadata and definitions change rarely
                ttl = 3600  # 1 hour
                self.logger.debug(f"Search intent: {intent_type}, TTL: {ttl}s (1 hour)")
                return ttl

            elif intent_type in ["time_series", "comparison"]:
                # Time series and comparisons - moderate cache
                ttl = 600  # 10 minutes
                self.logger.debug(f"Search intent: {intent_type}, TTL: {ttl}s (10 minutes)")
                return ttl

            elif intent_type == "search":
                # General search - short cache
                ttl = 300  # 5 minutes
                self.logger.debug(f"Search intent: {intent_type}, TTL: {ttl}s (5 minutes)")
                return ttl

            # Default
            self.logger.debug(f"Search default TTL: {default_ttl}s (5 minutes)")
            return default_ttl

        return calculate_search_ttl

    # Schema definitions
    class QuerySchema(BaseModel):
        """Schema for query operation"""

        provider: str = Field(description="API provider name (e.g., 'fred', 'worldbank', 'newsapi', 'census')")
        operation: str = Field(description="Provider-specific operation to perform (e.g., 'get_series', 'search_indicators')")
        params: Dict[str, Any] = Field(description="Operation-specific parameters as key-value pairs")

    class ListProvidersSchema(BaseModel):
        """Schema for list_providers operation (no parameters required)"""

    class GetProviderInfoSchema(BaseModel):
        """Schema for get_provider_info operation"""

        provider: str = Field(description="API provider name to get information about")

    class SearchSchema(BaseModel):
        """Schema for search operation"""

        query: str = Field(description="Search query text to find across providers")
        providers: Optional[List[str]] = Field(
            default=None,
            description="List of provider names to search (searches all if not specified)",
        )
        limit: int = Field(
            default=10,
            description="Maximum number of results to return per provider",
        )

    @cache_result_with_strategy(ttl_strategy=lambda self, result, args, kwargs: self._create_query_ttl_strategy()(result, args, kwargs))
    @measure_execution_time
    def query(
        self,
        provider: str,
        operation: str,
        params: Dict[str, Any],
        query_text: Optional[str] = None,
        enable_fallback: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Query a specific API provider with intelligent parameter enhancement and automatic fallback.

        Args:
            provider: API provider name (e.g., 'fred', 'worldbank', 'newsapi', 'census')
            operation: Provider-specific operation (e.g., 'get_series', 'search_indicators')
            params: Operation-specific parameters as dictionary
            query_text: Optional natural language query for intelligent parameter enhancement
            enable_fallback: Override config setting for fallback (defaults to config value)

        Returns:
            Dictionary containing response data with enhanced metadata

        Raises:
            ProviderNotFoundError: If the specified provider is not available
            ValueError: If operation or parameters are invalid
            APISourceError: If the API request fails after all retries and fallbacks
        """
        if provider not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ProviderNotFoundError(f"Provider '{provider}' not found. Available providers: {available}")

        # Apply query enhancement if enabled
        enhanced_params = params
        if self.config.enable_query_enhancement and query_text:
            try:
                enhanced_params = self.query_enhancer.auto_complete_params(provider, operation, params, query_text)
                if enhanced_params != params:
                    self.logger.debug(f"Enhanced parameters from {params} to {enhanced_params}")
            except Exception as e:
                self.logger.warning(f"Parameter enhancement failed: {e}")
                enhanced_params = params

        # Determine if fallback should be used
        use_fallback = enable_fallback if enable_fallback is not None else self.config.enable_fallback

        if use_fallback:
            # Use fallback strategy
            def provider_executor(prov: str, op: str, par: Dict[str, Any]) -> Dict[str, Any]:
                """Execute provider operation"""
                return self._providers[prov].execute(op, par)

            result = self.fallback_strategy.execute_with_fallback(
                primary_provider=provider,
                operation=operation,
                params=enhanced_params,
                provider_executor=provider_executor,
                providers_available=list(self._providers.keys()),
            )

            if result["success"]:
                return result["data"]
            else:
                # Build comprehensive error message
                error_msg = f"Failed to execute {provider}.{operation}"
                if result["attempts"]:
                    error_msg += f" after {len(result['attempts'])} attempts"
                if result.get("fallback_used"):
                    error_msg += " (including fallback providers)"

                raise APISourceError(error_msg)
        else:
            # Direct execution without fallback
            try:
                provider_instance = self._providers[provider]
                result = provider_instance.execute(operation, enhanced_params)
                return result
            except Exception as e:
                self.logger.error(f"Error querying {provider}.{operation}: {e}")
                raise APISourceError(f"Failed to query {provider}: {str(e)}")

    @cache_result(ttl=3600)  # Cache provider list for 1 hour
    @measure_execution_time
    def list_providers(self) -> List[Dict[str, Any]]:
        """
        List all available API providers with their metadata.

        Returns:
            List of provider metadata dictionaries containing name, description, supported operations, and statistics
        """
        return list_providers()

    @cache_result(ttl=1800)  # Cache provider info for 30 minutes
    @measure_execution_time
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific API provider.

        Args:
            provider: API provider name to get information about

        Returns:
            Dictionary with provider metadata including name, description, operations, and configuration

        Raises:
            ProviderNotFoundError: If the specified provider is not found
        """
        if provider not in self._providers:
            available = ", ".join(self._providers.keys())
            raise ProviderNotFoundError(f"Provider '{provider}' not found. Available providers: {available}")

        provider_instance = self._providers[provider]
        return provider_instance.get_metadata()

    @cache_result_with_strategy(ttl_strategy=lambda self, result, args, kwargs: self._create_search_ttl_strategy()(result, args, kwargs))
    @measure_execution_time
    def search(
        self,
        query: str,
        providers: Optional[List[str]] = None,
        limit: int = 10,
        enable_fusion: Optional[bool] = None,
        enable_enhancement: Optional[bool] = None,
        fusion_strategy: str = "best_quality",
        search_options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Search across multiple API providers with intelligent fusion and enhancement.

        Args:
            query: Search query text to find relevant data
            providers: List of provider names to search (searches all if not specified)
            limit: Maximum number of results to return per provider
            enable_fusion: Override config for data fusion (defaults to config value)
            enable_enhancement: Override config for search enhancement (defaults to config value)
            fusion_strategy: Strategy for data fusion ('best_quality', 'merge_all', 'consensus')
            search_options: Options for search enhancement:
                - relevance_threshold: Minimum relevance score (0-1)
                - sort_by: Sort method ('relevance', 'popularity', 'recency', 'composite')
                - max_results: Maximum results after enhancement

        Returns:
            Dictionary with:
                - results: Enhanced and potentially fused search results
                - metadata: Search metadata including fusion info and query analysis
                - providers_queried: List of providers that were queried
        """
        if providers is None:
            providers = list(self._providers.keys())

        # Analyze query intent
        intent_analysis = self.query_analyzer.analyze_intent(query)
        self.logger.info(f"Query intent: {intent_analysis['intent_type']} " f"(confidence: {intent_analysis['confidence']:.2f})")

        # Get provider suggestions from intent analysis
        if intent_analysis.get("suggested_providers"):
            suggested = [p for p in intent_analysis["suggested_providers"] if p in self._providers]
            if suggested:
                providers = suggested
                self.logger.debug(f"Using suggested providers: {providers}")

        results = []
        providers_queried = []

        for provider_name in providers:
            if provider_name not in self._providers:
                self.logger.warning(f"Skipping unknown provider: {provider_name}")
                continue

            try:
                provider_instance = self._providers[provider_name]

                # Enhance query for provider if enabled
                enhanced_query = query
                if self.config.enable_query_enhancement:
                    enhanced_query = self.query_enhancer.enhance_query_text(query, provider_name)

                # Try provider-specific search operations
                if provider_name == "fred":
                    result = provider_instance.execute(
                        "search_series",
                        {"search_text": enhanced_query, "limit": limit},
                    )
                elif provider_name == "worldbank":
                    result = provider_instance.execute(
                        "search_indicators",
                        {"search_text": enhanced_query, "limit": limit},
                    )
                elif provider_name == "newsapi":
                    result = provider_instance.execute(
                        "search_everything",
                        {"q": enhanced_query, "page_size": limit},
                    )
                else:
                    # Skip providers without search capability
                    continue

                results.append(result)
                providers_queried.append(provider_name)

            except Exception as e:
                self.logger.warning(f"Search failed for provider {provider_name}: {e}")
                # Continue with other providers

        if not results:
            return {
                "results": [],
                "metadata": {
                    "query": query,
                    "intent_analysis": intent_analysis,
                    "providers_queried": providers_queried,
                    "total_results": 0,
                },
                "providers_queried": providers_queried,
            }

        # Apply data fusion if enabled
        use_fusion = enable_fusion if enable_fusion is not None else self.config.enable_data_fusion

        if use_fusion and len(results) > 1:
            fused_result = self.data_fusion.fuse_multi_provider_results(results, fusion_strategy)
            final_data = fused_result.get("data", []) if fused_result else []
        else:
            # Use single result or merge without fusion logic
            if len(results) == 1:
                final_data = results[0].get("data", [])
            else:
                # Simple merge
                final_data = []
                for result in results:
                    data = result.get("data", [])
                    if isinstance(data, list):
                        final_data.extend(data)

        # Apply search enhancement if enabled
        use_enhancement = enable_enhancement if enable_enhancement is not None else True  # Always enhance search results

        if use_enhancement and isinstance(final_data, list):
            search_opts = search_options or {}
            enhanced_results = self.search_enhancer.enhance_search_results(query, final_data, search_opts)
            final_data = enhanced_results

        # Build response
        return {
            "results": final_data,
            "metadata": {
                "query": query,
                "intent_analysis": intent_analysis,
                "providers_queried": providers_queried,
                "total_results": (len(final_data) if isinstance(final_data, list) else 1),
                "fusion_applied": use_fusion and len(results) > 1,
                "fusion_strategy": fusion_strategy if use_fusion else None,
                "enhancement_applied": use_enhancement,
            },
            "providers_queried": providers_queried,
        }

    def get_metrics_report(self) -> Dict[str, Any]:
        """
        Get comprehensive metrics report from all providers.

        Returns:
            Dictionary with metrics from all providers and fallback statistics
        """
        report: Dict[str, Any] = {
            "providers": {},
            "fallback_stats": self.fallback_strategy.get_fallback_stats(),
            "total_providers": len(self._providers),
            "healthy_providers": 0,
            "degraded_providers": 0,
        }

        for provider_name, provider_instance in self._providers.items():
            try:
                provider_metadata = provider_instance.get_metadata()
                health_score = provider_metadata.get("health", {}).get("score", 0)

                report["providers"][provider_name] = {
                    "health": provider_metadata.get("health", {}),
                    "stats": provider_metadata.get("stats", {}),
                    "config": provider_metadata.get("config", {}),
                }

                if health_score > 0.7:
                    healthy = report.get("healthy_providers", 0)
                    if isinstance(healthy, (int, float)):
                        report["healthy_providers"] = healthy + 1
                else:
                    degraded = report.get("degraded_providers", 0)
                    if isinstance(degraded, (int, float)):
                        report["degraded_providers"] = degraded + 1

            except Exception as e:
                self.logger.warning(f"Failed to get metrics for {provider_name}: {e}")
                report["providers"][provider_name] = {
                    "error": str(e),
                    "status": "unavailable",
                }

        # Add overall health assessment
        total = report.get("total_providers", 0)
        healthy = report.get("healthy_providers", 0)
        if isinstance(total, (int, float)) and isinstance(healthy, (int, float)) and total > 0:
            health_ratio = healthy / total
            if health_ratio >= 0.8:
                report["overall_status"] = "healthy"
            elif health_ratio >= 0.5:
                report["overall_status"] = "degraded"
            else:
                report["overall_status"] = "unhealthy"
        else:
            report["overall_status"] = "no_providers"

        return report


# Register the tool (done via decorator)

"""
Core SearchTool Implementation

Enhanced Google Custom Search Tool with quality analysis, intent understanding,
intelligent caching, and comprehensive metrics.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import cache_result_with_strategy

# Import Google API with graceful fallback
try:
    from googleapiclient.discovery import build  # type: ignore[import-untyped]
    from googleapiclient.errors import HttpError  # type: ignore[import-untyped]
    from google.auth.exceptions import GoogleAuthError
    from google.oauth2 import service_account

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    HttpError = Exception  # type: ignore[assignment,misc]
    GoogleAuthError = Exception  # type: ignore[assignment,misc]

# Import search tool components
from .constants import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    CircuitBreakerOpenError,
    SearchAPIError,
    ValidationError,
)
from .rate_limiter import RateLimiter, CircuitBreaker
from .analyzers import (
    ResultQualityAnalyzer,
    QueryIntentAnalyzer,
    ResultSummarizer,
)
from .deduplicator import ResultDeduplicator
from .context import SearchContext
from .cache import IntelligentCache
from .metrics import EnhancedMetrics
from .error_handler import AgentFriendlyErrorHandler
from .schemas import (
    SearchWebSchema,
    SearchImagesSchema,
    SearchNewsSchema,
    SearchVideosSchema,
    SearchPaginatedSchema,
    SearchBatchSchema,
    ValidateCredentialsSchema,
    GetQuotaStatusSchema,
    GetMetricsSchema,
    GetMetricsReportSchema,
    GetHealthScoreSchema,
    GetSearchContextSchema,
)


class SearchTool(BaseTool):
    """
    Enhanced web search tool using Google Custom Search API.

    Provides intelligent search with:
    - Quality scoring and ranking
    - Query intent analysis
    - Result deduplication
    - Context-aware search
    - Intelligent Redis caching
    - Comprehensive metrics
    - Agent-friendly error handling
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the search tool
        
        Automatically reads from environment variables with SEARCH_TOOL_ prefix.
        Example: SEARCH_TOOL_GOOGLE_API_KEY -> google_api_key
        
        Sensitive fields (API keys, credentials) are loaded from .env files via dotenv.
        """

        model_config = SettingsConfigDict(env_prefix="SEARCH_TOOL_")

        google_api_key: Optional[str] = Field(default=None, description="Google API key for Custom Search")
        google_cse_id: Optional[str] = Field(default=None, description="Custom Search Engine ID")
        google_application_credentials: Optional[str] = Field(default=None, description="Path to service account JSON")
        max_results_per_query: int = Field(default=10, description="Maximum results per single query")
        cache_ttl: int = Field(default=3600, description="Default cache time-to-live in seconds")
        rate_limit_requests: int = Field(default=100, description="Maximum requests per time window")
        rate_limit_window: int = Field(
            default=86400,
            description="Time window for rate limiting in seconds",
        )
        circuit_breaker_threshold: int = Field(default=5, description="Failures before opening circuit")
        circuit_breaker_timeout: int = Field(
            default=60,
            description="Timeout before trying half-open in seconds",
        )
        retry_attempts: int = Field(default=3, description="Number of retry attempts")
        retry_backoff: float = Field(default=2.0, description="Exponential backoff factor")
        timeout: int = Field(default=30, description="API request timeout in seconds")
        user_agent: str = Field(default="AIECS-SearchTool/2.0", description="User agent string")

        # Enhanced features
        enable_quality_analysis: bool = Field(default=True, description="Enable result quality analysis")
        enable_intent_analysis: bool = Field(default=True, description="Enable query intent analysis")
        enable_deduplication: bool = Field(default=True, description="Enable result deduplication")
        enable_context_tracking: bool = Field(default=True, description="Enable search context tracking")
        enable_intelligent_cache: bool = Field(default=True, description="Enable intelligent Redis caching")
        similarity_threshold: float = Field(default=0.85, description="Similarity threshold for deduplication")
        max_search_history: int = Field(default=10, description="Maximum search history to maintain")

    # Operation schemas for input validation and documentation
    SearchWebSchema = SearchWebSchema
    SearchImagesSchema = SearchImagesSchema
    SearchNewsSchema = SearchNewsSchema
    SearchVideosSchema = SearchVideosSchema
    SearchPaginatedSchema = SearchPaginatedSchema
    SearchBatchSchema = SearchBatchSchema
    ValidateCredentialsSchema = ValidateCredentialsSchema
    GetQuotaStatusSchema = GetQuotaStatusSchema
    GetMetricsSchema = GetMetricsSchema
    GetMetricsReportSchema = GetMetricsReportSchema
    GetHealthScoreSchema = GetHealthScoreSchema
    GetSearchContextSchema = GetSearchContextSchema

    # Tool metadata
    description = "Comprehensive web search tool using Google Custom Search API."
    category = "task"

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize SearchTool with enhanced capabilities.

        Args:
            config: Optional configuration overrides
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            AuthenticationError: If Google API libraries not available
            ValidationError: If configuration is invalid

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/search.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Sensitive fields (API keys, credentials) are loaded from .env files.
        """
        super().__init__(config, **kwargs)

        if not GOOGLE_API_AVAILABLE:
            raise AuthenticationError("Google API client libraries not available. " "Install with: pip install google-api-python-client google-auth google-auth-httplib2")

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Initialize logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [SearchTool] %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        # Initialize API client
        self._service = None
        self._credentials = None
        self._init_credentials()

        # Initialize core components
        self.rate_limiter = RateLimiter(self.config.rate_limit_requests, self.config.rate_limit_window)

        self.circuit_breaker = CircuitBreaker(
            self.config.circuit_breaker_threshold,
            self.config.circuit_breaker_timeout,
        )

        # Initialize enhanced components
        self.quality_analyzer = ResultQualityAnalyzer() if self.config.enable_quality_analysis else None
        self.intent_analyzer = QueryIntentAnalyzer() if self.config.enable_intent_analysis else None
        self.deduplicator = ResultDeduplicator() if self.config.enable_deduplication else None
        self.result_summarizer = ResultSummarizer() if self.config.enable_quality_analysis else None
        self.search_context = SearchContext(self.config.max_search_history) if self.config.enable_context_tracking else None
        self.error_handler = AgentFriendlyErrorHandler()

        # Initialize intelligent cache (Redis)
        self.intelligent_cache = None
        if self.config.enable_intelligent_cache:
            try:
                from aiecs.infrastructure.persistence import RedisClient

                redis_client = RedisClient()
                # Note: Redis client needs to be initialized asynchronously
                self.intelligent_cache = IntelligentCache(redis_client, enabled=True)
            except Exception as e:
                self.logger.warning(f"Could not initialize Redis cache: {e}")
                self.intelligent_cache = IntelligentCache(None, enabled=False)

        # Initialize enhanced metrics
        self.metrics = EnhancedMetrics()

        self.logger.info("SearchTool initialized with enhanced capabilities")

    def _create_search_ttl_strategy(self):
        """
        Create intelligent TTL strategy for search results.

        This strategy calculates TTL based on:
        1. Query intent type (from result metadata)
        2. Result freshness score
        3. Result quality score

        Returns:
            Callable: TTL strategy function compatible with cache_result_with_strategy
        """

        def calculate_search_ttl(result: Any, args: tuple, kwargs: dict) -> int:
            """
            Calculate intelligent TTL for search results.

            Args:
                result: Search result (dict with 'results' and '_metadata')
                args: Positional arguments (not used)
                kwargs: Keyword arguments containing 'query', etc.

            Returns:
                int: TTL in seconds
            """
            # Extract metadata from result
            if not isinstance(result, dict):
                return 3600  # Default 1 hour for non-dict results

            metadata = result.get("_metadata", {})
            intent_type = metadata.get("intent_type", "GENERAL")
            results_list = result.get("results", [])
            query = kwargs.get("query", "")

            # Use IntelligentCache logic if available
            if hasattr(self, "intelligent_cache") and self.intelligent_cache:
                try:
                    return self.intelligent_cache.calculate_ttl(query, intent_type, results_list)
                except Exception as e:
                    self.logger.warning(f"Failed to calculate intelligent TTL: {e}")

            # Fallback: Use intent-based TTL
            from .cache import IntelligentCache

            ttl_strategies = IntelligentCache.TTL_STRATEGIES
            base_ttl = ttl_strategies.get(intent_type, ttl_strategies.get("GENERAL", 3600))

            # Adjust based on result count
            if not results_list:
                return base_ttl // 2  # Shorter TTL for empty results

            return base_ttl

        return calculate_search_ttl

    def _init_credentials(self):
        """Initialize Google API credentials"""
        # Method 1: API Key
        if self.config.google_api_key and self.config.google_cse_id:
            try:
                self._service = build(
                    "customsearch",
                    "v1",
                    developerKey=self.config.google_api_key,
                    cache_discovery=False,
                )
                self.logger.info("Initialized with API key")
                return
            except Exception as e:
                self.logger.warning(f"Failed to initialize with API key: {e}")

        # Method 2: Service Account
        if self.config.google_application_credentials:
            creds_path = self.config.google_application_credentials
            if os.path.exists(creds_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=["https://www.googleapis.com/auth/cse"],
                    )
                    self._credentials = credentials
                    self._service = build(
                        "customsearch",
                        "v1",
                        credentials=credentials,
                        cache_discovery=False,
                    )
                    self.logger.info("Initialized with service account")
                    return
                except Exception as e:
                    self.logger.warning(f"Failed to initialize with service account: {e}")

        raise AuthenticationError("No valid Google API credentials found. Set GOOGLE_API_KEY and GOOGLE_CSE_ID")

    def _execute_search(self, query: str, num_results: int = 10, start_index: int = 1, **kwargs) -> Dict[str, Any]:
        """Execute search with rate limiting and circuit breaker"""
        # Check rate limit
        self.rate_limiter.acquire()

        # Prepare parameters
        search_params = {
            "q": query,
            "cx": self.config.google_cse_id,
            "num": min(num_results, 10),
            "start": start_index,
            **kwargs,
        }

        # Execute with circuit breaker
        def _do_search():
            try:
                result = self._service.cse().list(**search_params).execute()
                return result
            except HttpError as e:
                if e.resp.status == 429:
                    raise QuotaExceededError(f"API quota exceeded: {e}")
                elif e.resp.status == 403:
                    raise AuthenticationError(f"Authentication failed: {e}")
                else:
                    raise SearchAPIError(f"Search API error: {e}")
            except Exception as e:
                raise SearchAPIError(f"Unexpected error: {e}")

        return self.circuit_breaker.call(_do_search)

    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """Execute with exponential backoff retry"""
        last_exception = None

        for attempt in range(self.config.retry_attempts):
            try:
                return func(*args, **kwargs)
            except (RateLimitError, CircuitBreakerOpenError) as e:
                # Don't retry these
                raise e
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    wait_time = self.config.retry_backoff**attempt
                    self.logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)

        if last_exception is None:
            raise RuntimeError("Retry logic failed but no exception was captured")
        raise last_exception

    def _parse_search_results(
        self,
        raw_results: Dict[str, Any],
        query: str = "",
        enable_quality_analysis: bool = True,
    ) -> List[Dict[str, Any]]:
        """Parse and enhance search results"""
        items = raw_results.get("items", [])
        results = []

        for position, item in enumerate(items, start=1):
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayLink": item.get("displayLink", ""),
                "formattedUrl": item.get("formattedUrl", ""),
            }

            # Add image metadata
            if "image" in item:
                result["image"] = {
                    "contextLink": item["image"].get("contextLink", ""),
                    "height": item["image"].get("height", 0),
                    "width": item["image"].get("width", 0),
                    "byteSize": item["image"].get("byteSize", 0),
                    "thumbnailLink": item["image"].get("thumbnailLink", ""),
                }

            # Add page metadata
            if "pagemap" in item:
                result["metadata"] = item["pagemap"]

            # Add quality analysis
            if enable_quality_analysis and self.quality_analyzer and query:
                quality_analysis = self.quality_analyzer.analyze_result_quality(result, query, position)
                result["_quality"] = quality_analysis

                # Add agent-friendly quality summary
                result["_quality_summary"] = {
                    "score": quality_analysis["quality_score"],
                    "level": quality_analysis["credibility_level"],
                    "is_authoritative": quality_analysis["authority_score"] > 0.8,
                    "is_relevant": quality_analysis["relevance_score"] > 0.7,
                    "is_fresh": quality_analysis["freshness_score"] > 0.7,
                    "warnings_count": len(quality_analysis["warnings"]),
                }

            results.append(result)

        return results

    # ========================================================================
    # Core Search Methods
    # ========================================================================

    @cache_result_with_strategy(ttl_strategy=lambda self, result, args, kwargs: self._create_search_ttl_strategy()(result, args, kwargs))
    def search_web(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[str] = None,
        auto_enhance: bool = True,
        return_summary: bool = False,
    ) -> Dict[str, Any]:
        """
        Search the web with enhanced intelligence.

        Args:
            query: Search query string
            num_results: Number of results to return
            start_index: Starting index for pagination
            language: Language code
            country: Country code
            safe_search: Safe search level
            date_restrict: Date restriction
            file_type: File type filter
            exclude_terms: Terms to exclude
            auto_enhance: Enable automatic query enhancement
            return_summary: Return summary metadata

        Returns:
            List of search results (or dict with results and summary)
        """
        start_time = time.time()
        intent_analysis = None

        try:
            if not query or not query.strip():
                raise ValidationError("Query cannot be empty")

            if num_results < 1 or num_results > 100:
                raise ValidationError("num_results must be between 1 and 100")

            # Analyze query intent
            enhanced_query = query
            if auto_enhance and self.intent_analyzer:
                intent_analysis = self.intent_analyzer.analyze_query_intent(query)
                enhanced_query = intent_analysis["enhanced_query"]

                # Merge suggested parameters
                for param, value in intent_analysis["suggested_params"].items():
                    if param == "date_restrict" and not date_restrict:
                        date_restrict = value
                    elif param == "file_type" and not file_type:
                        file_type = value
                    elif param == "num_results":
                        num_results = min(num_results, value)

                self.logger.info(f"Intent: {intent_analysis['intent_type']} " f"(confidence: {intent_analysis['confidence']:.2f})")

            # Note: Cache is now handled by @cache_result_with_strategy decorator
            # No need for manual cache check here

            # Prepare search parameters
            search_params = {
                "lr": f"lang_{language}",
                "cr": f"country{country.upper()}",
                "safe": safe_search,
            }

            if date_restrict:
                search_params["dateRestrict"] = date_restrict

            if file_type:
                search_params["fileType"] = file_type

            if exclude_terms:
                enhanced_query = f"{enhanced_query} -{exclude_terms}"

            # Execute search
            raw_results = self._retry_with_backoff(
                self._execute_search,
                enhanced_query,
                num_results,
                start_index,
                **search_params,
            )

            # Parse results
            results = self._parse_search_results(
                raw_results,
                query=query,
                enable_quality_analysis=self.config.enable_quality_analysis,
            )

            # Deduplicate
            if self.deduplicator:
                results = self.deduplicator.deduplicate_results(results, self.config.similarity_threshold)

            # Add search metadata
            if intent_analysis:
                for result in results:
                    result["_search_metadata"] = {
                        "original_query": query,
                        "enhanced_query": enhanced_query,
                        "intent_type": intent_analysis["intent_type"],
                        "intent_confidence": intent_analysis["confidence"],
                        "suggestions": intent_analysis["suggestions"],
                    }

            # Update context
            if self.search_context:
                self.search_context.add_search(query, results)

            # Note: Cache is now handled by @cache_result_with_strategy decorator
            # The decorator will call _create_search_ttl_strategy() to
            # calculate TTL

            # Record metrics
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", results, response_time, cached=False)

            # Prepare result with metadata for TTL calculation
            result_data = {
                "results": results,
                "_metadata": {
                    "intent_type": (intent_analysis["intent_type"] if intent_analysis else "GENERAL"),
                    "query": query,
                    "enhanced_query": enhanced_query,
                    "timestamp": time.time(),
                    "response_time_ms": response_time,
                },
            }

            # Generate summary if requested
            if return_summary and self.result_summarizer:
                summary = self.result_summarizer.generate_summary(results, query)
                result_data["summary"] = summary

            return result_data

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", [], response_time, error=e)

            # Format error for agent
            error_info = self.error_handler.format_error_for_agent(
                e,
                {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
            )

            self.logger.error(f"Search failed: {error_info['user_message']}")
            raise

    def search_images(
        self,
        query: str,
        num_results: int = 10,
        image_size: Optional[str] = None,
        image_type: Optional[str] = None,
        image_color_type: Optional[str] = None,
        safe_search: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Search for images"""
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")

        search_params = {
            "searchType": "image",
            "safe": safe_search,
        }

        if image_size:
            search_params["imgSize"] = image_size
        if image_type:
            search_params["imgType"] = image_type
        if image_color_type:
            search_params["imgColorType"] = image_color_type

        raw_results = self._retry_with_backoff(self._execute_search, query, num_results, 1, **search_params)

        return self._parse_search_results(raw_results, query=query)

    def search_news(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        date_restrict: Optional[str] = None,
        sort_by: str = "date",
    ) -> List[Dict[str, Any]]:
        """Search for news articles"""
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")

        news_query = f"{query} news"

        search_params = {
            "lr": f"lang_{language}",
            "sort": sort_by if sort_by == "date" else "",
        }

        if date_restrict:
            search_params["dateRestrict"] = date_restrict

        raw_results = self._retry_with_backoff(
            self._execute_search,
            news_query,
            num_results,
            start_index,
            **search_params,
        )

        return self._parse_search_results(raw_results, query=query)

    def search_videos(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        safe_search: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Search for videos"""
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")

        video_query = f"{query} filetype:mp4 OR filetype:webm OR filetype:mov"

        search_params = {
            "lr": f"lang_{language}",
            "safe": safe_search,
        }

        raw_results = self._retry_with_backoff(
            self._execute_search,
            video_query,
            num_results,
            start_index,
            **search_params,
        )

        return self._parse_search_results(raw_results, query=query)

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        return self.metrics.get_metrics()

    def get_metrics_report(self) -> str:
        """Get human-readable metrics report"""
        return self.metrics.generate_report()

    def get_health_score(self) -> float:
        """Get system health score (0-1)"""
        return self.metrics.get_health_score()

    def get_quota_status(self) -> Dict[str, Any]:
        """Get quota and rate limit status"""
        return {
            "remaining_quota": self.rate_limiter.get_remaining_quota(),
            "max_requests": self.config.rate_limit_requests,
            "time_window_seconds": self.config.rate_limit_window,
            "circuit_breaker_state": self.circuit_breaker.get_state(),
            "health_score": self.get_health_score(),
        }

    def get_search_context(self) -> Optional[Dict[str, Any]]:
        """Get search context information"""
        if not self.search_context:
            return None

        return {
            "history": self.search_context.get_history(5),
            "preferences": self.search_context.get_preferences(),
        }

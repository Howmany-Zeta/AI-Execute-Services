# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Core SearchTool Implementation

Enhanced Google Custom Search Tool with quality analysis, intent understanding,
intelligent caching, and comprehensive metrics.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Sequence, cast

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from aiecs.tools.base_tool import BaseTool
from aiecs.tools.tool_executor import cache_result_with_strategy

# Import search tool components
from .constants import (
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    CircuitBreakerOpenError,
    SearchAPIError,
    SearchToolError,
    ValidationError,
    QueryIntentType,
)
from .errors import (
    AllBackendsExhaustedError,
    SearchRoutingContext,
    build_search_failure_envelope,
    build_search_failure_envelope_from_exception,
    is_cse_only_deployment,
    should_raise_for_search_error,
    should_return_tier_c_for_router_failure,
)
from .rate_limiter import RateLimiter, CircuitBreaker
from .backends.gemini_grounding import GeminiGroundingBackend
from .backends.grok_grounding import GrokGroundingBackend
from .backends.google_cse import GoogleCseBackend
from .backends.protocol import GroundingSearchBackend, SearchCallParams, BackendRawResult
from .analyzers import (
    ResultQualityAnalyzer,
    QueryIntentAnalyzer,
    ResultSummarizer,
    build_search_next_steps,
    merge_batch_search_results,
    build_batch_intent_analysis,
)
from .partition import partition_search_results, resolve_partition_profile
from .deduplicator import ResultDeduplicator
from .context import SearchContext
from .cache import IntelligentCache
from .metrics import EnhancedMetrics
from .error_handler import AgentFriendlyErrorHandler
from pydantic import BaseModel, field_validator
from .backends.credentials import CredentialResolver
from .backends.registry import GroundingBackendRegistry
from .cache_fingerprint import (
    CACHE_SCHEMA_VERSION,
    build_routing_cache_fingerprint,
    filter_custom_backend_names,
)
from .normalizer import normalize_grounding_result
from .router import BatchRoutingContext, GroundingRouter, RoutingMetadata


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
        # Grounding / custom backend resilience defaults (§3.11) — CSE uses rate_limit_* above.
        grounding_rate_limit_requests: int = Field(
            default=60,
            description="Default max requests per window for gemini/grok/custom backends",
        )
        grounding_rate_limit_window: int = Field(
            default=3600,
            description="Rate-limit window (seconds) for grounding backends",
        )
        grounding_circuit_breaker_threshold: int = Field(
            default=5,
            description="Failures before opening circuit for grounding backends",
        )
        grounding_circuit_breaker_timeout: int = Field(
            default=60,
            description="Seconds before half-open retry for grounding backends",
        )
        # Optional per-backend resilience overrides (§3.11); None → grounding_* defaults.
        gemini_rate_limit_requests: Optional[int] = Field(
            default=None,
            description="Override grounding_rate_limit_requests for Gemini only",
        )
        gemini_rate_limit_window: Optional[int] = Field(
            default=None,
            description="Override grounding_rate_limit_window for Gemini only",
        )
        gemini_circuit_breaker_threshold: Optional[int] = Field(
            default=None,
            description="Override grounding_circuit_breaker_threshold for Gemini only",
        )
        gemini_circuit_breaker_timeout: Optional[int] = Field(
            default=None,
            description="Override grounding_circuit_breaker_timeout for Gemini only",
        )
        grok_rate_limit_requests: Optional[int] = Field(
            default=None,
            description="Override grounding_rate_limit_requests for Grok only",
        )
        grok_rate_limit_window: Optional[int] = Field(
            default=None,
            description="Override grounding_rate_limit_window for Grok only",
        )
        grok_circuit_breaker_threshold: Optional[int] = Field(
            default=None,
            description="Override grounding_circuit_breaker_threshold for Grok only",
        )
        grok_circuit_breaker_timeout: Optional[int] = Field(
            default=None,
            description="Override grounding_circuit_breaker_timeout for Grok only",
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
        max_batch_queries: int = Field(default=3, ge=1, le=10, description="Maximum orthogonal queries per search_batch call")
        allow_llm_credential_fallback: bool = Field(
            default=False,
            description="Opt-in: borrow LLM Settings keys when SEARCH_TOOL_* grounding keys are absent (§3.5)",
        )
        grounding_provider: str = Field(
            default="auto",
            description="Routing mode: auto | gemini | grok | google | google_cse | <custom>",
        )
        grounding_provider_chain: str = Field(
            default="gemini,grok,google_cse",
            description="Comma-separated provider chain for auto routing",
        )
        search_error_mode: str = Field(
            default="auto",
            description="Error policy: auto | return_dict | raise (§3.10)",
        )
        batch_routing_mode: str = Field(
            default="pin_on_first_success",
            description="Batch routing: pin_on_first_success | per_query (§3.7)",
        )
        batch_p95_budget_seconds: float = Field(
            default=15.0,
            description="Total wall-clock budget for search_batch (§3.7)",
        )
        grounding_timeout_seconds: float = Field(
            default=30.0,
            description="Per-backend HTTP timeout cap for grounding search",
        )
        grounding_model_gemini: str = Field(
            default="gemini-2.5-flash",
            description="Model ID for Gemini grounding search",
        )
        gemini_grounding_temperature: float = Field(
            default=1.0,
            description="Temperature for Gemini grounding generate_content",
        )
        gemini_grounding_auth: str = Field(
            default="auto",
            description="Gemini auth: auto | googleai | vertex",
        )
        gemini_include_raw_grounding: bool = Field(
            default=False,
            description=("When true, attach full serialized grounding_metadata and " "generate_content response dump to provider_native / _search_metadata " "(debug / e2e; can be large)"),
        )
        gemini_include_grounding_supports: bool = Field(
            default=True,
            description=("Attach lightweight grounding_supports/chunks to SearchTool envelope " "(SEARCH_TOOL_GEMINI_INCLUDE_GROUNDING_SUPPORTS; independent of raw dump)"),
        )
        gemini_grounding_supports_include_segment_text: bool = Field(
            default=True,
            description=("Include segment.text in grounding_supports " "(SEARCH_TOOL_GEMINI_GROUNDING_SUPPORTS_INCLUDE_SEGMENT_TEXT; False → indices only)"),
        )
        gemini_api_key: Optional[str] = Field(
            default=None,
            description="SEARCH_TOOL_GEMINI_API_KEY — Google GenAI API key path",
        )
        googleai_api_key: Optional[str] = Field(
            default=None,
            description="Alias for gemini_api_key (SEARCH_TOOL_GOOGLEAI_API_KEY)",
        )
        vertex_project_id: Optional[str] = Field(
            default=None,
            description="SEARCH_TOOL_VERTEX_PROJECT_ID — Gemini Vertex grounding",
        )
        vertex_location: str = Field(
            default="global",
            description="SEARCH_TOOL_VERTEX_LOCATION (default global for grounding)",
        )
        google_application_credentials_vertex_gemini: Optional[str] = Field(
            default=None,
            description="Service-account JSON for Gemini Vertex grounding",
        )
        grounding_model_grok: str = Field(
            default="grok-4.5",
            description="Model ID for Grok grounding search (xAI)",
        )
        grok_grounding_auth: str = Field(
            default="auto",
            description="Grok auth: auto | xai | vertex_maas",
        )
        grok_include_raw_grounding: bool = Field(
            default=False,
            description=("When true, attach full xAI/MaaS responses.create dump and web_search " "tool payload to provider_native / _search_metadata (debug / e2e)"),
        )
        grok_api_key: Optional[str] = Field(
            default=None,
            description="SEARCH_TOOL_GROK_API_KEY — xAI direct API key path",
        )
        xai_api_key: Optional[str] = Field(
            default=None,
            description="Alias for grok_api_key (SEARCH_TOOL_XAI_API_KEY)",
        )
        grok_maas_web_search_enabled: bool = Field(
            default=False,
            description=("Opt-in: allow Vertex MaaS Grok in auto routing (§3.12). " "When true, auto MaaS always TTL-probes web_search support."),
        )
        vertex_project_id_maas: Optional[str] = Field(
            default=None,
            description="SEARCH_TOOL_VERTEX_PROJECT_ID_MAAS — Vertex MaaS Grok project",
        )
        vertex_location_maas: str = Field(
            default="global",
            description="SEARCH_TOOL_VERTEX_LOCATION_MAAS (prefer global for xAI Grok)",
        )
        google_application_credentials_vertex_maas: Optional[str] = Field(
            default=None,
            description="Service-account JSON for Vertex MaaS Grok token refresh",
        )
        grok_maas_capability_probe: bool = Field(
            default=False,
            description=("When true, also probe in forced grok_grounding_auth=vertex_maas. " "Auto MaaS (enable=true) always probes regardless of this flag."),
        )
        maas_capability_probe_ttl_seconds: int = Field(
            default=3600,
            description="Re-probe interval for MaaS web_search capability cache",
        )
        grounding_trust_citations: bool = Field(
            default=True,
            description="Enable grounding partition profile (§3.3)",
        )
        grounding_relevance_threshold: float = Field(
            default=0.5,
            description="is_relevant cutoff for grounding partition (CSE stays 0.7)",
        )
        grounding_sparse_snippet_max_len: int = Field(
            default=80,
            description="Below this snippet length, trust floor may keep top citations in primary",
        )
        grounding_citation_trust_top_k: int = Field(
            default=3,
            description="Top-K provider citations eligible for trust floor",
        )
        grounding_min_must_scrape: int = Field(
            default=1,
            description="Min must_scrape_urls for demographic/causal when non-social citations exist",
        )
        rewrite_before_grounding: bool = Field(
            default=True,
            description="Run M-D.1a intent rewrite before grounding provider call",
        )
        cache_schema_version: str = Field(
            default=CACHE_SCHEMA_VERSION,
            description="Routing cache schema bump (M-D.5 §3.2)",
        )

    # Schema definitions
    class Search_webSchema(BaseModel):
        """Schema for search_web operation"""

        query: str = Field(description="Search query string")
        num_results: int = Field(default=10, ge=1, le=100, description="Number of results to return (1-100)")
        start_index: int = Field(default=1, ge=1, le=91, description="Starting index for pagination (1-91)")
        language: str = Field(default="en", description="Language code for results (e.g., 'en', 'zh-CN', 'es')")
        country: str = Field(default="us", description="Country code for geolocation (e.g., 'us', 'cn', 'uk')")
        safe_search: str = Field(default="medium", description="Safe search level: 'off', 'medium', or 'high'")
        date_restrict: Optional[str] = Field(default=None, description="Date restriction (e.g., 'd7' for last 7 days, 'm3' for last 3 months)")
        file_type: Optional[str] = Field(default=None, description="File type filter (e.g., 'pdf', 'doc', 'xls')")
        exclude_terms: Optional[List[str]] = Field(default=None, description="Terms to exclude from search results")
        auto_enhance: bool = Field(default=True, description="Whether to automatically enhance query based on detected intent")
        return_summary: bool = Field(default=False, description="Whether to return a structured summary of results")

        @field_validator("safe_search")
        @classmethod
        def validate_safe_search(cls, v: str) -> str:
            """Validate safe search level"""
            allowed = ["off", "medium", "high"]
            if v not in allowed:
                raise ValueError(f"safe_search must be one of {allowed}")
            return v

    class Search_imagesSchema(BaseModel):
        """Schema for search_images operation"""

        query: str = Field(description="Image search query string")
        num_results: int = Field(default=10, ge=1, le=100, description="Number of image results to return (1-100)")
        image_size: Optional[str] = Field(default=None, description="Image size filter: 'icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge'")
        image_type: Optional[str] = Field(default=None, description="Image type filter: 'clipart', 'face', 'lineart', 'stock', 'photo', 'animated'")
        image_color_type: Optional[str] = Field(default=None, description="Color type filter: 'color', 'gray', 'mono', 'trans'")
        safe_search: str = Field(default="medium", description="Safe search level: 'off', 'medium', or 'high'")

        @field_validator("safe_search")
        @classmethod
        def validate_safe_search(cls, v: str) -> str:
            """Validate safe search level"""
            allowed = ["off", "medium", "high"]
            if v not in allowed:
                raise ValueError(f"safe_search must be one of {allowed}")
            return v

    class Search_newsSchema(BaseModel):
        """Schema for search_news operation"""

        query: str = Field(description="News search query string")
        num_results: int = Field(default=10, ge=1, le=100, description="Number of news results to return (1-100)")
        start_index: int = Field(default=1, ge=1, le=91, description="Starting index for pagination (1-91)")
        language: str = Field(default="en", description="Language code for news articles (e.g., 'en', 'zh-CN', 'es')")
        date_restrict: Optional[str] = Field(default=None, description="Date restriction (e.g., 'd7' for last 7 days, 'm1' for last month)")
        sort_by: str = Field(default="date", description="Sort order: 'date' for newest first, 'relevance' for most relevant")

        @field_validator("sort_by")
        @classmethod
        def validate_sort_by(cls, v: str) -> str:
            """Validate sort order"""
            allowed = ["date", "relevance"]
            if v not in allowed:
                raise ValueError(f"sort_by must be one of {allowed}")
            return v

    class Search_videosSchema(BaseModel):
        """Schema for search_videos operation"""

        query: str = Field(description="Video search query string")
        num_results: int = Field(default=10, ge=1, le=100, description="Number of video results to return (1-100)")
        start_index: int = Field(default=1, ge=1, le=91, description="Starting index for pagination (1-91)")
        language: str = Field(default="en", description="Language code for videos (e.g., 'en', 'zh-CN', 'es')")
        safe_search: str = Field(default="medium", description="Safe search level: 'off', 'medium', or 'high'")

        @field_validator("safe_search")
        @classmethod
        def validate_safe_search(cls, v: str) -> str:
            """Validate safe search level"""
            allowed = ["off", "medium", "high"]
            if v not in allowed:
                raise ValueError(f"safe_search must be one of {allowed}")
            return v

    class Get_metricsSchema(BaseModel):
        """Schema for get_metrics operation (no parameters required)"""

        pass

    class Get_metrics_reportSchema(BaseModel):
        """Schema for get_metrics_report operation (no parameters required)"""

        pass

    class Get_health_scoreSchema(BaseModel):
        """Schema for get_health_score operation (no parameters required)"""

        pass

    class Get_quota_statusSchema(BaseModel):
        """Schema for get_quota_status operation (no parameters required)"""

        pass

    class Get_search_contextSchema(BaseModel):
        """Schema for get_search_context operation (no parameters required)"""

        pass

    class Search_batchSchema(BaseModel):
        """Schema for search_batch operation (2–3 orthogonal queries per call)."""

        queries: List[str] = Field(description="List of orthogonal search queries (1–3 recommended)")
        search_type: str = Field(default="web", description="Batch search type; currently only 'web' is supported")
        num_results: int = Field(default=10, ge=1, le=100, description="Number of results to return per query")
        merged_num_results: Optional[int] = Field(
            default=None,
            ge=1,
            le=100,
            description="Number of merged ranked results across all queries (defaults to num_results)",
        )
        language: str = Field(default="en", description="Language code for results")
        country: str = Field(default="us", description="Country code for geolocation")
        safe_search: str = Field(default="medium", description="Safe search level: 'off', 'medium', or 'high'")
        date_restrict: Optional[str] = Field(default=None, description="Date restriction applied to each query")
        file_type: Optional[str] = Field(default=None, description="File type filter applied to each query")
        exclude_terms: Optional[List[str]] = Field(
            default=None,
            description="Terms to exclude from each query",
        )
        auto_enhance: bool = Field(default=True, description="Apply intent rewrite to each query")

        @field_validator("queries")
        @classmethod
        def validate_queries(cls, values: List[str]) -> List[str]:
            cleaned = [query.strip() for query in values if query and query.strip()]
            if not cleaned:
                raise ValueError("queries list cannot be empty")
            return cleaned

        @field_validator("safe_search")
        @classmethod
        def validate_safe_search(cls, value: str) -> str:
            allowed = ["off", "medium", "high"]
            if value not in allowed:
                raise ValueError(f"safe_search must be one of {allowed}")
            return value

        @field_validator("search_type")
        @classmethod
        def validate_search_type(cls, value: str) -> str:
            allowed = ["web"]
            if value not in allowed:
                raise ValueError(f"search_type must be one of {allowed}")
            return value

    # Tool metadata
    description = "Comprehensive web search tool using Google Custom Search API."
    category = "task"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        custom_grounding_backends: Sequence[GroundingSearchBackend] | None = None,
        **kwargs: Any,
    ):
        """
        Initialize SearchTool with enhanced capabilities.

        Args:
            config: Optional configuration overrides
            custom_grounding_backends: Optional consumer backends (Exa, etc.)
                registered by ``backend.name`` into the grounding registry (§8 / §9.4).
                Include those names in ``grounding_provider_chain`` to route to them.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Raises:
            ValidationError: If configuration is invalid

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/search.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)

        Sensitive fields (API keys, credentials) are loaded from .env files.
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config: SearchTool.Config = self._config_obj if self._config_obj else self.Config()  # type: ignore[assignment]

        # Initialize logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [SearchTool] %(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

        self._google_cse_backend = GoogleCseBackend(self.config, logger=self.logger)
        self._credential_resolver = CredentialResolver(self.config)
        self._registry = GroundingBackendRegistry()
        self._registry.register(GeminiGroundingBackend(self.config, logger=self.logger))
        self._registry.register(GrokGroundingBackend(self.config, logger=self.logger))
        self._registry.register(self._google_cse_backend)
        self._register_custom_grounding_backends(custom_grounding_backends)

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

        if not self._is_cse_configured() and not self._registry.has_configured_backend():
            self.logger.warning("No search backends configured (CSE or grounding). " "Set SEARCH_TOOL_GOOGLE_* or grounding provider credentials.")

        self.logger.info("SearchTool initialized with enhanced capabilities")

    def _register_custom_grounding_backends(
        self,
        custom_grounding_backends: Sequence[GroundingSearchBackend] | None,
    ) -> None:
        """Register consumer backends by ``name`` (after built-ins; may override)."""
        if not custom_grounding_backends:
            return
        for backend in custom_grounding_backends:
            name = getattr(backend, "name", None)
            if not isinstance(name, str) or not name.strip():
                raise ValidationError("custom_grounding_backends entries must define a non-empty string name")
            if not callable(getattr(backend, "is_configured", None)) or not callable(getattr(backend, "search", None)):
                raise ValidationError(f"custom grounding backend '{name}' must implement is_configured() and search()")
            existing = self._registry.get(name.strip())
            if existing is not None and existing is not backend:
                self.logger.warning(
                    "Replacing grounding backend '%s' with custom registration",
                    name.strip(),
                )
            self._registry.register(backend)
            self.logger.info("Registered custom grounding backend '%s'", name.strip())

    def clear_search_cache(self) -> None:
        """
        Clear in-process decorator cache used by ``search_web`` / ``search_batch``.

        Use on staged grounding rollout when ``cache_schema_version`` alone is not
        enough (e.g. mid-process config flip). For Redis dual-layer caches, also
        ``SCAN``/delete ``tool_executor:*`` / ``search_tool:*`` keys.
        """
        utils = getattr(getattr(self, "_executor", None), "execution_utils", None)
        if utils is None:
            return
        lock = getattr(utils, "_cache_lock", None)
        cache = getattr(utils, "_cache", None)
        ttl_dict = getattr(utils, "_cache_ttl_dict", None)
        if lock is None:
            if cache is not None and hasattr(cache, "clear"):
                cache.clear()
            if isinstance(ttl_dict, dict):
                ttl_dict.clear()
        else:
            with lock:
                if cache is not None and hasattr(cache, "clear"):
                    cache.clear()
                if isinstance(ttl_dict, dict):
                    ttl_dict.clear()
        self.logger.info("SearchTool decorator cache cleared (M-D.5 §3.2)")

    @property
    def service(self) -> Any | None:
        """Backward-compatible accessor for the CSE API client (tests)."""
        return self._google_cse_backend.service

    @service.setter
    def service(self, value: Any) -> None:
        self._google_cse_backend.service = value

    @property
    def rate_limiter(self) -> RateLimiter:
        """Backward-compatible accessor for CSE rate limiter (tests)."""
        return self._google_cse_backend.resilience.rate_limiter

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Backward-compatible accessor for CSE circuit breaker (tests)."""
        return self._google_cse_backend.resilience.circuit_breaker

    def _is_cse_configured(self) -> bool:
        """Return True when SEARCH_TOOL CSE credentials are present in config."""
        return self._google_cse_backend.is_configured()

    def _raise_from_cse_backend_result(self, raw: BackendRawResult) -> None:
        """Map backend failure to legacy SearchTool exceptions (CSE-only backward compat)."""
        if raw.error_type == "rate_limit_exceeded":
            raise RateLimitError(raw.error or "Rate limit exceeded")
        if raw.error_type == "circuit_open":
            raise CircuitBreakerOpenError(raw.error or "Circuit breaker is open")
        if raw.error_type == "quota_exceeded":
            raise QuotaExceededError(raw.error or "API quota exceeded")
        if raw.error_type == "auth":
            raise AuthenticationError(raw.error or "Authentication failed")
        raise SearchAPIError(raw.error or "Search API error")

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

    def _execute_search(self, query: str, num_results: int = 10, start_index: int = 1, **kwargs) -> Dict[str, Any]:
        """Execute CSE search via GoogleCseBackend (rate limit + circuit breaker per backend)."""
        params = SearchCallParams(
            query=query,
            original_query=query,
            num_results=num_results,
            start_index=start_index,
        )
        raw = self._google_cse_backend.search(params, extra_api_params=kwargs)
        if not raw.success:
            self._raise_from_cse_backend_result(raw)
        assert raw.provider_native is not None
        return raw.provider_native

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
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        return_summary: bool = False,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search the web with enhanced intelligence (cached; routing fingerprint §3.2)."""
        fingerprint = self._routing_cache_fingerprint(
            overrides={"grounding_provider": grounding_provider},
        )
        return cast(
            Dict[str, Any],
            self._cached_search_web(
                query=query,
                num_results=num_results,
                start_index=start_index,
                language=language,
                country=country,
                safe_search=safe_search,
                date_restrict=date_restrict,
                file_type=file_type,
                exclude_terms=exclude_terms,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                auto_enhance=auto_enhance,
                return_summary=return_summary,
                grounding_provider=grounding_provider,
                _cache_routing_fingerprint=fingerprint,
            ),
        )

    @cache_result_with_strategy(ttl_strategy=lambda self, result, args, kwargs: self._create_search_ttl_strategy()(result, args, kwargs))
    def _cached_search_web(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        return_summary: bool = False,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cached search_web body; `_cache_routing_fingerprint` stripped by decorator."""
        return self._search_web_impl(
            query=query,
            num_results=num_results,
            start_index=start_index,
            language=language,
            country=country,
            safe_search=safe_search,
            date_restrict=date_restrict,
            file_type=file_type,
            exclude_terms=exclude_terms,
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
            auto_enhance=auto_enhance,
            return_summary=return_summary,
            grounding_provider=grounding_provider,
        )

    def _routing_cache_fingerprint(
        self,
        *,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build routing fingerprint for decorator cache keys (§3.2)."""
        return build_routing_cache_fingerprint(
            self.config,
            overrides=overrides,
            custom_backend_names=filter_custom_backend_names(self._registry.list_names()),
        )

    def _search_web_impl(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        return_summary: bool = False,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search the web via GroundingRouter (M-D.5 §10 steps 1–6).

        Returns:
            Dict with results, low_signal, must_scrape_urls, and metadata
        """
        start_time = time.time()
        intent_analysis = None
        enhanced_query = query
        allowed_domains = self._normalize_domain_filter(allowed_domains)
        blocked_domains = self._normalize_domain_filter(blocked_domains)
        exclude_terms = self._normalize_exclude_terms(exclude_terms)

        try:
            if not query or not query.strip():
                raise ValidationError("Query cannot be empty")

            if num_results < 1 or num_results > 100:
                raise ValidationError("num_results must be between 1 and 100")

            enhanced_query = query
            if auto_enhance and self.intent_analyzer and bool(getattr(self.config, "rewrite_before_grounding", True)):
                intent_analysis = self.intent_analyzer.analyze_query_intent(query)
                enhanced_query = intent_analysis["enhanced_query"]

                for param, value in intent_analysis["suggested_params"].items():
                    if param == "date_restrict" and not date_restrict:
                        date_restrict = value
                    elif param == "file_type" and not file_type:
                        file_type = value
                    elif param == "num_results":
                        num_results = min(num_results, value)

                self.logger.info(f"Intent: {intent_analysis['intent_type']} " f"(confidence: {intent_analysis['confidence']:.2f})")

            params = SearchCallParams(
                query=enhanced_query,
                original_query=query,
                num_results=num_results,
                start_index=start_index,
                language=language,
                country=country,
                safe_search=safe_search,
                date_restrict=date_restrict,
                file_type=file_type,
                exclude_terms=exclude_terms,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                timeout_seconds=float(self.config.grounding_timeout_seconds),
            )

            router = GroundingRouter(self._registry, self.config, logger=self.logger)
            raw, routing = router.search_with_chain(params, grounding_provider=grounding_provider)

            if not raw.success:
                return self._finalize_router_failure(
                    raw=raw,
                    routing=routing,
                    query=query,
                    enhanced_query=enhanced_query,
                    start_time=start_time,
                    intent_analysis=intent_analysis,
                )

            backend_used = routing.backend_used or raw.backend or ""
            results, grounding_partial = self._normalize_router_success(
                raw,
                backend_used=backend_used,
                query=query,
                blocked_domains=params.blocked_domains,
                num_results=num_results,
            )

            if self.deduplicator:
                results = self.deduplicator.deduplicate_results(results, self.config.similarity_threshold)

            low_signal_results: List[Dict[str, Any]] = []
            must_scrape_urls: List[Dict[str, Any]] = []
            next_steps: List[str] = []
            partition_profile = resolve_partition_profile(
                backend_used,
                grounding_trust_citations=bool(self.config.grounding_trust_citations),
            )
            if self.config.enable_quality_analysis and self.quality_analyzer:
                intent_type = intent_analysis["intent_type"] if intent_analysis else None
                results, low_signal_results, must_scrape_urls = partition_search_results(
                    self.quality_analyzer,
                    results,
                    num_results=num_results,
                    partition_profile=partition_profile,
                    query=enhanced_query or query,
                    intent_type=intent_type,
                    grounding_citations=(list(grounding_partial.get("grounding_citations") or []) if grounding_partial else None),
                    grounding_trust_citations=bool(self.config.grounding_trust_citations),
                    grounding_relevance_threshold=float(self.config.grounding_relevance_threshold),
                    grounding_sparse_snippet_max_len=int(self.config.grounding_sparse_snippet_max_len),
                    grounding_citation_trust_top_k=int(self.config.grounding_citation_trust_top_k),
                    grounding_min_must_scrape=int(self.config.grounding_min_must_scrape),
                )
                next_steps = build_search_next_steps(must_scrape_urls, intent_analysis)

            search_metadata: Dict[str, Any] = {
                "backend_used": routing.backend_used,
                "provider_chain": list(routing.provider_chain_attempted),
                "provider_chain_attempted": list(routing.provider_chain_attempted),
                "provider_chain_skipped": list(routing.provider_chain_skipped),
                "provider_chain_failed": list(routing.provider_chain_failed),
                "params_applied": list(raw.params_applied),
                "params_ignored": list(raw.params_ignored),
                "partition_profile": partition_profile,
                "original_query": query,
                "enhanced_query": enhanced_query,
            }
            if grounding_partial:
                norm_meta = grounding_partial.get("_search_metadata") or {}
                if "params_applied" in norm_meta:
                    search_metadata["params_applied"] = list(norm_meta["params_applied"])
                if "params_ignored" in norm_meta:
                    search_metadata["params_ignored"] = list(norm_meta["params_ignored"])
            if intent_analysis:
                search_metadata.update(
                    {
                        "intent_type": intent_analysis["intent_type"],
                        "intent_confidence": intent_analysis["confidence"],
                        "rewrite_applied": intent_analysis.get("rewrite_applied", False),
                        "suggestions": intent_analysis["suggestions"],
                    }
                )
            self._merge_grounding_metadata(search_metadata, raw)
            self._apply_credential_source_metadata(search_metadata, backend_used)
            for result in results + low_signal_results:
                result["_search_metadata"] = search_metadata.copy()

            if self.search_context:
                self.search_context.add_search(query, results)

            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", results, response_time, cached=False)

            result_data: Dict[str, Any] = {
                "results": results,
                "low_signal": low_signal_results,
                "must_scrape_urls": must_scrape_urls,
                "next_steps": next_steps,
                "_search_metadata": search_metadata,
                "_metadata": {
                    "intent_type": (intent_analysis["intent_type"] if intent_analysis else QueryIntentType.GENERAL.value),
                    "query": query,
                    "enhanced_query": enhanced_query,
                    "rewrite_applied": (intent_analysis.get("rewrite_applied", False) if intent_analysis else False),
                    "timestamp": time.time(),
                    "response_time_ms": response_time,
                    "backend_used": routing.backend_used,
                    "partition_profile": partition_profile,
                },
            }
            if grounding_partial is not None:
                if grounding_partial.get("grounding_answer"):
                    # Synthesized grounding text — not collected evidence (§3.13 / §10)
                    result_data["grounding_answer"] = grounding_partial["grounding_answer"]
                result_data["grounding_citations"] = list(grounding_partial.get("grounding_citations") or [])
                if grounding_partial.get("grounding_chunks"):
                    result_data["grounding_chunks"] = list(grounding_partial["grounding_chunks"])
                if grounding_partial.get("grounding_supports"):
                    result_data["grounding_supports"] = list(grounding_partial["grounding_supports"])
            elif raw.answer:
                result_data["grounding_answer"] = raw.answer

            if return_summary and self.result_summarizer:
                summary = self.result_summarizer.generate_summary(results, query)
                result_data["summary"] = summary

            return result_data

        except (ValidationError, RateLimitError, CircuitBreakerOpenError) as e:
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", [], response_time, error=e)
            error_info = self.error_handler.format_error_for_agent(
                e,
                {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
            )
            self.logger.error(f"Search failed: {error_info['user_message']}")
            raise

        except SearchToolError as e:
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", [], response_time, error=e)
            if should_raise_for_search_error(
                e,
                self.config,
                cse_only=is_cse_only_deployment(self.config, registry=self._registry),
            ):
                error_info = self.error_handler.format_error_for_agent(
                    e,
                    {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
                )
                self.logger.error(f"Search failed: {error_info['user_message']}")
                raise
            intent_metadata = None
            if intent_analysis:
                intent_metadata = {
                    "original_query": query,
                    "enhanced_query": enhanced_query,
                    "intent_type": intent_analysis["intent_type"],
                    "intent_confidence": intent_analysis["confidence"],
                }
            envelope = build_search_failure_envelope_from_exception(
                e,
                query=query,
                enhanced_query=enhanced_query,
                search_error_mode=self.config.search_error_mode,
                response_time_ms=response_time,
                error_handler=self.error_handler,
                intent_metadata=intent_metadata,
                circuit_breaker_timeout=self.config.circuit_breaker_timeout,
            )
            self.logger.error(f"Search failed: {envelope['_error']['user_message']}")
            return envelope

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_search(query, "web", [], response_time, error=e)
            error_info = self.error_handler.format_error_for_agent(
                e,
                {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
            )
            self.logger.error(f"Search failed: {error_info['user_message']}")
            raise

    def _finalize_router_failure(
        self,
        *,
        raw: BackendRawResult,
        routing: RoutingMetadata,
        query: str,
        enhanced_query: str,
        start_time: float,
        intent_analysis: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Apply Tier A/B raise vs Tier C return-dict for a failed router result."""
        response_time = (time.time() - start_time) * 1000
        mode = getattr(self.config, "search_error_mode", "auto") or "auto"
        # CSE-only raise applies when no non-CSE backend actually failed (skips don't count)
        non_cse_failed = any(entry.get("backend") != "google_cse" for entry in routing.provider_chain_failed)
        cse_only = is_cse_only_deployment(self.config, registry=self._registry) and not non_cse_failed

        # Tier A: rate limit / circuit always raise
        if raw.error_type in ("rate_limit_exceeded", "circuit_open"):
            try:
                self._raise_from_cse_backend_result(raw)
            except (RateLimitError, CircuitBreakerOpenError) as exc:
                self.metrics.record_search(query, "web", [], response_time, error=exc)
                error_info = self.error_handler.format_error_for_agent(
                    exc,
                    {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
                )
                self.logger.error(f"Search failed: {error_info['user_message']}")
                raise

        if mode == "return_dict":
            should_tier_c = True
        elif mode == "raise":
            should_tier_c = False
        elif cse_only:
            # CSE-only (incl. grounding_provider=google_cse): keep raise for API errors
            should_tier_c = False
        elif routing.forced_provider:
            # Forced grounding backend configured but attempt failed → Tier C (§3.10)
            should_tier_c = True
        else:
            should_tier_c = should_return_tier_c_for_router_failure(self.config, routing)

        if not should_tier_c:
            try:
                self._raise_from_cse_backend_result(raw)
            except SearchToolError as exc:
                self.metrics.record_search(query, "web", [], response_time, error=exc)
                if should_raise_for_search_error(exc, self.config, cse_only=cse_only):
                    error_info = self.error_handler.format_error_for_agent(
                        exc,
                        {"circuit_breaker_timeout": self.config.circuit_breaker_timeout},
                    )
                    self.logger.error(f"Search failed: {error_info['user_message']}")
                    raise
                envelope = build_search_failure_envelope_from_exception(
                    exc,
                    query=query,
                    enhanced_query=enhanced_query,
                    search_error_mode=mode,
                    response_time_ms=response_time,
                    error_handler=self.error_handler,
                    circuit_breaker_timeout=self.config.circuit_breaker_timeout,
                )
                self.logger.error(f"Search failed: {envelope['_error']['user_message']}")
                return envelope

        intent_metadata = None
        if intent_analysis:
            intent_metadata = {
                "original_query": query,
                "enhanced_query": enhanced_query,
                "intent_type": intent_analysis["intent_type"],
                "intent_confidence": intent_analysis["confidence"],
            }
        routing_context = SearchRoutingContext(
            routing_metadata=routing,
            last_raw=raw,
            search_error_mode=mode,
            response_time_ms=response_time,
            query=query,
            enhanced_query=enhanced_query,
            intent_metadata=intent_metadata,
        )
        envelope = build_search_failure_envelope(
            routing_context,
            error_handler=self.error_handler,
        )
        synthetic = AllBackendsExhaustedError(envelope["_error"]["technical_details"])
        self.metrics.record_search(query, "web", [], response_time, error=synthetic)
        self.logger.error(f"Search failed: {envelope['_error']['user_message']}")
        return envelope

    def _search_web_via_router(
        self,
        query: str,
        *,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compat helper: routed search through ``_search_web_impl``."""
        return self._search_web_impl(
            query=query,
            num_results=num_results,
            start_index=start_index,
            language=language,
            country=country,
            safe_search=safe_search,
            date_restrict=date_restrict,
            file_type=file_type,
            exclude_terms=exclude_terms,
            auto_enhance=False,
            grounding_provider=grounding_provider,
        )

    def search_batch(
        self,
        queries: List[str],
        search_type: str = "web",
        num_results: int = 10,
        merged_num_results: Optional[int] = None,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        batch_routing_mode: Optional[str] = None,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute 1–3 orthogonal web searches in one call and return per-query buckets
        plus a merged ranked result list (M-D.1 Phase 2 / M-D.5 §3.7).
        """
        fingerprint = self._routing_cache_fingerprint(
            overrides={
                "grounding_provider": grounding_provider,
                "batch_routing_mode": batch_routing_mode,
            },
        )
        # Sorted queries participate in the cache key alongside the fingerprint (§3.2).
        sorted_queries = sorted(q.strip() for q in queries if q and str(q).strip())
        return cast(
            Dict[str, Any],
            self._cached_search_batch(
                queries=list(queries),
                search_type=search_type,
                num_results=num_results,
                merged_num_results=merged_num_results,
                language=language,
                country=country,
                safe_search=safe_search,
                date_restrict=date_restrict,
                file_type=file_type,
                exclude_terms=exclude_terms,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                auto_enhance=auto_enhance,
                batch_routing_mode=batch_routing_mode,
                grounding_provider=grounding_provider,
                _cache_routing_fingerprint=fingerprint,
                _cache_batch_queries="|".join(sorted_queries),
            ),
        )

    @cache_result_with_strategy(ttl_strategy=lambda self, result, args, kwargs: self._create_search_ttl_strategy()(result, args, kwargs))
    def _cached_search_batch(
        self,
        queries: List[str],
        search_type: str = "web",
        num_results: int = 10,
        merged_num_results: Optional[int] = None,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        batch_routing_mode: Optional[str] = None,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cached search_batch body; `_cache_*` kwargs stripped by decorator."""
        return self._search_batch_impl(
            queries=queries,
            search_type=search_type,
            num_results=num_results,
            merged_num_results=merged_num_results,
            language=language,
            country=country,
            safe_search=safe_search,
            date_restrict=date_restrict,
            file_type=file_type,
            exclude_terms=exclude_terms,
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
            auto_enhance=auto_enhance,
            batch_routing_mode=batch_routing_mode,
            grounding_provider=grounding_provider,
        )

    def _search_batch_impl(
        self,
        queries: List[str],
        search_type: str = "web",
        num_results: int = 10,
        merged_num_results: Optional[int] = None,
        language: str = "en",
        country: str = "us",
        safe_search: str = "medium",
        date_restrict: Optional[str] = None,
        file_type: Optional[str] = None,
        exclude_terms: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool = True,
        batch_routing_mode: Optional[str] = None,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        allowed_domains = self._normalize_domain_filter(allowed_domains)
        blocked_domains = self._normalize_domain_filter(blocked_domains)
        exclude_terms = self._normalize_exclude_terms(exclude_terms)

        cleaned_queries = [query.strip() for query in queries if query and query.strip()]
        if not cleaned_queries:
            raise ValidationError("queries list cannot be empty")
        if len(cleaned_queries) > self.config.max_batch_queries:
            raise ValidationError(f"Maximum {self.config.max_batch_queries} queries allowed in batch")
        if search_type != "web":
            raise ValidationError("search_batch currently supports search_type='web' only")
        if num_results < 1 or num_results > 100:
            raise ValidationError("num_results must be between 1 and 100")

        merged_limit = merged_num_results if merged_num_results is not None else num_results
        if merged_limit < 1 or merged_limit > 100:
            raise ValidationError("merged_num_results must be between 1 and 100")

        mode = batch_routing_mode or self.config.batch_routing_mode or "pin_on_first_success"
        ctx = BatchRoutingContext(
            mode=mode,
            budget_seconds=float(self.config.batch_p95_budget_seconds),
        )
        ctx.start_deadline()
        router = GroundingRouter(self._registry, self.config, logger=self.logger)

        per_query_buckets: List[Dict[str, Any]] = []
        failed_query_indices: List[int] = []

        for query_index, query in enumerate(cleaned_queries):
            remaining_queries = len(cleaned_queries) - query_index
            bucket = self._search_batch_one_query(
                router=router,
                ctx=ctx,
                query=query,
                query_index=query_index,
                remaining_queries=remaining_queries,
                num_results=num_results,
                language=language,
                country=country,
                safe_search=safe_search,
                date_restrict=date_restrict,
                file_type=file_type,
                exclude_terms=exclude_terms,
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
                auto_enhance=auto_enhance,
                grounding_provider=grounding_provider,
            )
            if bucket.get("success") is False:
                failed_query_indices.append(query_index)
            per_query_buckets.append(bucket)

        merged_results: List[Dict[str, Any]] = []
        merged_low_signal: List[Dict[str, Any]] = []
        merged_must_scrape: List[Dict[str, Any]] = []
        merged_next_steps: List[str] = []

        successful_buckets = [b for b in per_query_buckets if b.get("success") is not False]
        if self.config.enable_quality_analysis and self.quality_analyzer and successful_buckets:
            merged_results, merged_low_signal, merged_must_scrape = merge_batch_search_results(
                self.quality_analyzer,
                successful_buckets,
                merged_num_results=merged_limit,
                deduplicator=self.deduplicator,
                similarity_threshold=self.config.similarity_threshold,
            )
            merged_next_steps = build_search_next_steps(
                merged_must_scrape,
                build_batch_intent_analysis(successful_buckets),
            )
            if len(cleaned_queries) > 1:
                merged_next_steps.insert(
                    0,
                    f"batch search covered {len(cleaned_queries)} orthogonal queries; prefer merged must_scrape_urls before another search_batch",
                )
            if failed_query_indices:
                merged_next_steps.append(f"partial batch failure on query indices {failed_query_indices}; " "retry those queries or verify SEARCH_TOOL_* credentials")

        response_time = (time.time() - start_time) * 1000
        self.metrics.record_search(
            " | ".join(cleaned_queries),
            "web_batch",
            merged_results,
            response_time,
            cached=False,
        )

        metadata: Dict[str, Any] = {
            "batch_size": len(cleaned_queries),
            "queries": cleaned_queries,
            "search_type": search_type,
            "num_results_per_query": num_results,
            "merged_num_results": merged_limit,
            "timestamp": time.time(),
            "response_time_ms": response_time,
            "batch_routing_mode": ctx.mode,
            "batch_pinned_backend": ctx.pinned_backend,
            "batch_first_query_chain_attempted": list(ctx.first_query_chain_attempted),
            "per_query_backend_used": list(ctx.per_query_backend_used),
            "batch_p95_budget_seconds": ctx.budget_seconds,
            "batch_elapsed_ms": response_time,
        }
        if failed_query_indices:
            metadata["batch_partial_failure"] = True
            metadata["failed_query_indices"] = failed_query_indices

        return {
            "per_query": per_query_buckets,
            "results": merged_results,
            "low_signal": merged_low_signal,
            "must_scrape_urls": merged_must_scrape,
            "next_steps": merged_next_steps,
            "_metadata": metadata,
        }

    def _search_batch_one_query(
        self,
        *,
        router: GroundingRouter,
        ctx: BatchRoutingContext,
        query: str,
        query_index: int,
        remaining_queries: int,
        num_results: int,
        language: str,
        country: str,
        safe_search: str,
        date_restrict: Optional[str],
        file_type: Optional[str],
        exclude_terms: Optional[List[str]],
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        auto_enhance: bool,
        grounding_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run one batch query through router pin/chain rules and partition."""
        query_start = time.time()
        intent_analysis = None
        enhanced_query = query

        if auto_enhance and self.intent_analyzer and bool(getattr(self.config, "rewrite_before_grounding", True)):
            intent_analysis = self.intent_analyzer.analyze_query_intent(query)
            enhanced_query = intent_analysis["enhanced_query"]
            for param, value in intent_analysis["suggested_params"].items():
                if param == "date_restrict" and not date_restrict:
                    date_restrict = value
                elif param == "file_type" and not file_type:
                    file_type = value
                elif param == "num_results":
                    num_results = min(num_results, value)

        params = SearchCallParams(
            query=enhanced_query,
            original_query=query,
            num_results=num_results,
            language=language,
            country=country,
            safe_search=safe_search,
            date_restrict=date_restrict,
            file_type=file_type,
            exclude_terms=exclude_terms,
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
        )

        raw, routing, used_pinned = router.search_for_batch(
            ctx,
            params,
            query_index=query_index,
            grounding_timeout_seconds=float(self.config.grounding_timeout_seconds),
            remaining_queries=remaining_queries,
            grounding_provider=grounding_provider,
        )
        response_time = (time.time() - query_start) * 1000

        search_metadata: Dict[str, Any] = {
            "backend_used": routing.backend_used or (raw.backend if raw.success else None),
            "batch_query_index": query_index,
            "batch_used_pinned_backend": used_pinned,
            "provider_chain": list(routing.provider_chain_attempted),
            "params_applied": list(raw.params_applied),
            "params_ignored": list(raw.params_ignored),
            "original_query": query,
            "enhanced_query": enhanced_query,
        }
        if intent_analysis:
            search_metadata.update(
                {
                    "intent_type": intent_analysis["intent_type"],
                    "intent_confidence": intent_analysis["confidence"],
                    "rewrite_applied": intent_analysis.get("rewrite_applied", False),
                    "suggestions": intent_analysis["suggestions"],
                }
            )
        self._merge_grounding_metadata(search_metadata, raw)
        self._apply_credential_source_metadata(
            search_metadata,
            search_metadata.get("backend_used") or raw.backend,
        )

        if not raw.success:
            # Same Tier A/B/C policy as search_web (§3.10): rate_limit / circuit raise
            # abort the entire batch; Tier C stays a per-query envelope.
            envelope = self._finalize_router_failure(
                raw=raw,
                routing=routing,
                query=query,
                enhanced_query=enhanced_query,
                start_time=query_start,
                intent_analysis=intent_analysis,
            )
            envelope["query"] = query
            envelope["_search_metadata"] = {
                **envelope.get("_search_metadata", {}),
                **search_metadata,
            }
            return envelope

        backend_used = routing.backend_used or raw.backend or ""
        results, grounding_partial = self._normalize_router_success(
            raw,
            backend_used=backend_used,
            query=query,
            blocked_domains=params.blocked_domains,
            num_results=num_results,
        )
        if grounding_partial:
            norm_meta = grounding_partial.get("_search_metadata") or {}
            if "params_applied" in norm_meta:
                search_metadata["params_applied"] = list(norm_meta["params_applied"])
            if "params_ignored" in norm_meta:
                search_metadata["params_ignored"] = list(norm_meta["params_ignored"])

        if self.deduplicator:
            results = self.deduplicator.deduplicate_results(results, self.config.similarity_threshold)

        low_signal_results: List[Dict[str, Any]] = []
        must_scrape_urls: List[Dict[str, Any]] = []
        next_steps: List[str] = []
        partition_profile = resolve_partition_profile(
            backend_used,
            grounding_trust_citations=bool(self.config.grounding_trust_citations),
        )
        search_metadata["partition_profile"] = partition_profile
        if self.config.enable_quality_analysis and self.quality_analyzer:
            intent_type = intent_analysis["intent_type"] if intent_analysis else None
            results, low_signal_results, must_scrape_urls = partition_search_results(
                self.quality_analyzer,
                results,
                num_results=num_results,
                partition_profile=partition_profile,
                query=enhanced_query or query,
                intent_type=intent_type,
                grounding_citations=(list(grounding_partial.get("grounding_citations") or []) if grounding_partial else None),
                grounding_trust_citations=bool(self.config.grounding_trust_citations),
                grounding_relevance_threshold=float(self.config.grounding_relevance_threshold),
                grounding_sparse_snippet_max_len=int(self.config.grounding_sparse_snippet_max_len),
                grounding_citation_trust_top_k=int(self.config.grounding_citation_trust_top_k),
                grounding_min_must_scrape=int(self.config.grounding_min_must_scrape),
            )
            next_steps = build_search_next_steps(must_scrape_urls, intent_analysis)

        for result in results + low_signal_results:
            result["_search_metadata"] = search_metadata.copy()

        if self.search_context:
            self.search_context.add_search(query, results)

        self.metrics.record_search(query, "web", results, response_time, cached=False)

        bucket: Dict[str, Any] = {
            "query": query,
            "results": results,
            "low_signal": low_signal_results,
            "must_scrape_urls": must_scrape_urls,
            "next_steps": next_steps,
            "_search_metadata": search_metadata,
            "_metadata": {
                "intent_type": (intent_analysis["intent_type"] if intent_analysis else QueryIntentType.GENERAL.value),
                "query": query,
                "enhanced_query": enhanced_query,
                "rewrite_applied": (intent_analysis.get("rewrite_applied", False) if intent_analysis else False),
                "timestamp": time.time(),
                "response_time_ms": response_time,
                "partition_profile": partition_profile,
            },
        }
        if grounding_partial is not None:
            if grounding_partial.get("grounding_answer"):
                bucket["grounding_answer"] = grounding_partial["grounding_answer"]
            bucket["grounding_citations"] = list(grounding_partial.get("grounding_citations") or [])
            if grounding_partial.get("grounding_chunks"):
                bucket["grounding_chunks"] = list(grounding_partial["grounding_chunks"])
            if grounding_partial.get("grounding_supports"):
                bucket["grounding_supports"] = list(grounding_partial["grounding_supports"])
        elif raw.answer:
            bucket["grounding_answer"] = raw.answer
        return bucket

    def _normalize_router_success(
        self,
        raw: BackendRawResult,
        *,
        backend_used: str,
        query: str,
        blocked_domains: list[str] | None = None,
        num_results: int | None = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
        """CSE → parse items; grounding → ``normalize_grounding_result`` (§10)."""
        native = raw.provider_native if isinstance(raw.provider_native, dict) else None
        if backend_used == "google_cse" or (native is not None and "items" in native):
            return self._results_from_cse_raw(raw, query=query), None

        partial = normalize_grounding_result(
            raw,
            backend_used,
            blocked_domains=blocked_domains,
            num_results=num_results,
        )
        return list(partial["results"]), partial

    @staticmethod
    def _merge_grounding_metadata(search_metadata: Dict[str, Any], raw: BackendRawResult) -> None:
        """Attach Gemini/Grok passthrough fields from backend ``provider_native``."""
        native = raw.provider_native if isinstance(raw.provider_native, dict) else None
        if not native:
            return
        if native.get("gemini_auth_mode"):
            search_metadata["gemini_auth_mode"] = native["gemini_auth_mode"]
        gemini_grounding = native.get("gemini_grounding")
        if isinstance(gemini_grounding, dict):
            search_metadata["gemini_grounding"] = gemini_grounding
        if "grounding_metadata" in native:
            search_metadata["grounding_metadata"] = native["grounding_metadata"]
        if "generate_content_response" in native:
            search_metadata["generate_content_response"] = native["generate_content_response"]
        if "enterprise_web_search" in native:
            search_metadata["enterprise_web_search"] = native["enterprise_web_search"]
        if "exclude_domains_applied" in native:
            search_metadata["exclude_domains_applied"] = native["exclude_domains_applied"]
        if native.get("grok_auth_mode"):
            search_metadata["grok_auth_mode"] = native["grok_auth_mode"]
        if native.get("grok_client_mode"):
            search_metadata["grok_client_mode"] = native["grok_client_mode"]
        if "grok_maas_web_search_capable" in native:
            search_metadata["grok_maas_web_search_capable"] = native["grok_maas_web_search_capable"]
        if "responses_create_response" in native:
            search_metadata["responses_create_response"] = native["responses_create_response"]
        if "web_search_tool" in native:
            search_metadata["web_search_tool"] = native["web_search_tool"]
        if "allowed_domains_applied" in native:
            search_metadata["allowed_domains_applied"] = native["allowed_domains_applied"]
        if "excluded_domains_applied" in native:
            search_metadata["excluded_domains_applied"] = native["excluded_domains_applied"]

    def _apply_credential_source_metadata(
        self,
        search_metadata: Dict[str, Any],
        backend_used: str | None,
    ) -> None:
        """Set ``credential_source`` for ops billing isolation (§3.5 / §10)."""
        if not backend_used:
            return
        source = self._credential_resolver.resolve_credential_source(str(backend_used))
        if source:
            search_metadata["credential_source"] = source

    @staticmethod
    def _normalize_domain_filter(domains: Optional[List[str]]) -> Optional[List[str]]:
        """Strip empties; return ``None`` when no usable domain entries remain."""
        if not domains:
            return None
        cleaned = [str(d).strip() for d in domains if d is not None and str(d).strip()]
        return cleaned or None

    @staticmethod
    def _normalize_exclude_terms(terms: Optional[List[str]]) -> Optional[List[str]]:
        """Strip empties; return ``None`` when no usable exclude terms remain."""
        if not terms:
            return None
        cleaned = [str(t).strip() for t in terms if t is not None and str(t).strip()]
        return cleaned or None

    def _results_from_cse_raw(self, raw: BackendRawResult, *, query: str) -> List[Dict[str, Any]]:
        """Normalize CSE ``provider_native.items`` into results[] (§10)."""
        native = raw.provider_native if isinstance(raw.provider_native, dict) else {}
        results = self._parse_search_results(
            native,
            query=query,
            enable_quality_analysis=self.config.enable_quality_analysis,
        )
        for item in results:
            link = item.get("link") or item.get("url") or ""
            if link:
                item["link"] = link
                item.setdefault("url", link)
        return results

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
        """
        Get quota and circuit-breaker status.

        Top-level ``remaining_quota`` / ``circuit_breaker_state`` remain CSE-scoped
        for backward compatibility. Per-backend guards are under ``resilience`` (§3.11).
        """
        cse = self._google_cse_backend.resilience
        return {
            "remaining_quota": cse.get_remaining_quota(),
            "max_requests": self.config.rate_limit_requests,
            "time_window_seconds": self.config.rate_limit_window,
            "circuit_breaker_state": cse.get_circuit_state(),
            "health_score": self.get_health_score(),
            "resilience": self._collect_resilience_status(),
        }

    def _collect_resilience_status(self) -> Dict[str, Dict[str, Any]]:
        """Per-backend circuit state + remaining quota from registry guards."""
        status: Dict[str, Dict[str, Any]] = {}
        for name in self._registry.list_names():
            backend = self._registry.get(name)
            if backend is None:
                continue
            guard = getattr(backend, "resilience", None)
            if guard is None:
                continue
            get_remaining = getattr(guard, "get_remaining_quota", None)
            get_state = getattr(guard, "get_circuit_state", None)
            if not callable(get_remaining) or not callable(get_state):
                continue
            status[name] = {
                "circuit_state": get_state(),
                "remaining_quota": get_remaining(),
            }
        return status

    def get_search_context(self) -> Optional[Dict[str, Any]]:
        """Get search context information"""
        if not self.search_context:
            return None

        return {
            "history": self.search_context.get_history(5),
            "preferences": self.search_context.get_preferences(),
        }

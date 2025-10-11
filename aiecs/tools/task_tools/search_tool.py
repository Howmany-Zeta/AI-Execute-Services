"""
Google Custom Search Tool for AI Agents

A comprehensive, production-ready web search tool that integrates Google Custom Search API
with advanced features including multiple search types, pagination, rate limiting, circuit
breaker pattern, caching, and full AIECS architecture compliance.

Features:
- Multiple search types: web, image, news, video
- Dual authentication: API key and service account
- Rate limiting with token bucket algorithm
- Circuit breaker pattern for API resilience
- Intelligent caching with TTL
- Comprehensive error handling and retry logic
- Batch and paginated search support
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationError as PydanticValidationError, ConfigDict

from aiecs.tools import register_tool
from aiecs.tools.base_tool import BaseTool
from aiecs.config.config import get_settings

# Google API imports with graceful fallback
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import GoogleAuthError
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    HttpError = Exception
    GoogleAuthError = Exception


# ============================================================================
# Enums and Constants
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


# ============================================================================
# Exception Hierarchy
# ============================================================================

class SearchToolError(Exception):
    """Base exception for SearchTool errors"""
    pass


class AuthenticationError(SearchToolError):
    """Authentication-related errors"""
    pass


class QuotaExceededError(SearchToolError):
    """API quota exceeded"""
    pass


class RateLimitError(SearchToolError):
    """Rate limit exceeded"""
    pass


class CircuitBreakerOpenError(SearchToolError):
    """Circuit breaker is open"""
    pass


class SearchAPIError(SearchToolError):
    """Search API errors"""
    pass


class ValidationError(SearchToolError):
    """Input validation errors"""
    pass


# ============================================================================
# Configuration
# ============================================================================



# ============================================================================
# Rate Limiter
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for API requests.
    
    Implements a token bucket algorithm to limit the rate of API requests
    and prevent quota exhaustion.
    """

    def __init__(self, max_requests: int, time_window: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.tokens = max_requests
        self.last_update = time.time()
        self.lock = Lock()
        self.request_history: deque = deque()

    def _refill_tokens(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        time_passed = now - self.last_update
        
        # Refill tokens proportionally to time passed
        refill_rate = self.max_requests / self.time_window
        tokens_to_add = time_passed * refill_rate
        
        self.tokens = min(self.max_requests, self.tokens + tokens_to_add)
        self.last_update = now

    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False otherwise

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        with self.lock:
            self._refill_tokens()
            
            # Clean up old request history
            cutoff_time = time.time() - self.time_window
            while self.request_history and self.request_history[0] < cutoff_time:
                self.request_history.popleft()
            
            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.request_history.append(time.time())
                return True
            else:
                # Calculate wait time
                wait_time = (tokens - self.tokens) / (self.max_requests / self.time_window)
                raise RateLimitError(
                    f"Rate limit exceeded. {len(self.request_history)} requests in last "
                    f"{self.time_window}s. Wait {wait_time:.1f}s before retrying."
                )

    def get_remaining_quota(self) -> int:
        """Get remaining quota"""
        with self.lock:
            self._refill_tokens()
            return int(self.tokens)


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for API resilience.
    
    Implements a circuit breaker to prevent cascading failures when
    the API is experiencing issues.
    """

    def __init__(self, failure_threshold: int, timeout: int):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Timeout in seconds before trying half-open state
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.lock = Lock()

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                # Check if timeout has passed
                if time.time() - self.last_failure_time >= self.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.failure_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker is OPEN. Retry after "
                        f"{self.timeout - (time.time() - self.last_failure_time):.1f}s"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call"""
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    def get_state(self) -> str:
        """Get current circuit state"""
        return self.state.value


# ============================================================================
# Search Tool Implementation
# ============================================================================

@register_tool("search")
class SearchTool(BaseTool):
    """
    Comprehensive web search tool using Google Custom Search API.

    Provides multiple search types (web, image, news, video) with advanced features
    including rate limiting, circuit breaker protection, caching, and comprehensive
    error handling.

    Features:
    - Web, image, news, and video search
    - Dual authentication (API key and service account)
    - Rate limiting and circuit breaker
    - Intelligent caching with TTL
    - Batch and paginated search
    - Comprehensive error handling

    Inherits from BaseTool to leverage ToolExecutor for caching, concurrency,
    and error handling.
    """
    
    # Configuration schema
    class Config(BaseModel):
        """Configuration for the search tool"""
        model_config = ConfigDict(env_prefix="SEARCH_TOOL_")
        
        google_api_key: Optional[str] = Field(
            default=None,
            description="Google API key for Custom Search"
        )
        google_cse_id: Optional[str] = Field(
            default=None,
            description="Custom Search Engine ID"
        )
        google_application_credentials: Optional[str] = Field(
            default=None,
            description="Path to service account JSON"
        )
        max_results_per_query: int = Field(
            default=10,
            description="Maximum results per single query"
        )
        cache_ttl: int = Field(
            default=3600,
            description="Cache time-to-live in seconds"
        )
        rate_limit_requests: int = Field(
            default=100,
            description="Maximum requests per time window"
        )
        rate_limit_window: int = Field(
            default=86400,
            description="Time window for rate limiting in seconds"
        )
        circuit_breaker_threshold: int = Field(
            default=5,
            description="Failures before opening circuit"
        )
        circuit_breaker_timeout: int = Field(
            default=60,
            description="Timeout before trying half-open in seconds"
        )
        retry_attempts: int = Field(
            default=3,
            description="Number of retry attempts"
        )
        retry_backoff: float = Field(
            default=2.0,
            description="Exponential backoff factor"
        )
        timeout: int = Field(
            default=30,
            description="API request timeout in seconds"
        )
        user_agent: str = Field(
            default="AIECS-SearchTool/1.0",
            description="User agent string"
        )
        allowed_search_types: List[str] = Field(
            default=["web", "image", "news", "video"],
            description="Allowed search types"
        )

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SearchTool with configuration.

        Args:
            config: Optional configuration overrides

        Raises:
            AuthenticationError: If Google API libraries are not available
            ValidationError: If configuration is invalid
        """
        super().__init__(config)
        
        if not GOOGLE_API_AVAILABLE:
            raise AuthenticationError(
                "Google API client libraries not available. "
                "Install with: pip install google-api-python-client google-auth google-auth-httplib2"
            )
        
        # Load settings from global config
        global_settings = get_settings()
        
        # Merge global settings with config overrides
        merged_config = {
            'google_api_key': global_settings.google_api_key,
            'google_cse_id': global_settings.google_cse_id,
            'google_application_credentials': global_settings.google_application_credentials
        }
        if config:
            merged_config.update(config)
        
        # Parse configuration
        self.config = self.Config(**merged_config)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('%(asctime)s %(levelname)s [SearchTool] %(message)s')
            )
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Initialize API client
        self._service = None
        self._credentials = None
        self._init_credentials()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            self.config.rate_limit_requests,
            self.config.rate_limit_window
        )
        
        # Initialize circuit breaker
        self.circuit_breaker = CircuitBreaker(
            self.config.circuit_breaker_threshold,
            self.config.circuit_breaker_timeout
        )
        
        # Metrics tracking
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'rate_limit_errors': 0,
            'circuit_breaker_trips': 0
        }

    def _init_credentials(self):
        """
        Initialize Google API credentials.

        Supports both API key and service account authentication with auto-detection.

        Raises:
            AuthenticationError: If credentials are not properly configured
        """
        # Method 1: API Key (simpler, recommended for Custom Search)
        if self.config.google_api_key and self.config.google_cse_id:
            try:
                self._service = build(
                    'customsearch',
                    'v1',
                    developerKey=self.config.google_api_key,
                    cache_discovery=False
                )
                self.logger.info("Initialized Google Custom Search with API key")
                return
            except Exception as e:
                self.logger.warning(f"Failed to initialize with API key: {e}")
        
        # Method 2: Service Account (more complex, supports additional features)
        if self.config.google_application_credentials:
            creds_path = self.config.google_application_credentials
            if os.path.exists(creds_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/cse']
                    )
                    self._credentials = credentials
                    self._service = build(
                        'customsearch',
                        'v1',
                        credentials=credentials,
                        cache_discovery=False
                    )
                    self.logger.info("Initialized Google Custom Search with service account")
                    return
                except Exception as e:
                    self.logger.warning(f"Failed to initialize with service account: {e}")
        
        raise AuthenticationError(
            "No valid Google API credentials found. Please set either:\n"
            "1. GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables, or\n"
            "2. GOOGLE_APPLICATION_CREDENTIALS pointing to service account JSON file"
        )

    def _execute_search(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a search request with retry logic.

        Args:
            query: Search query
            num_results: Number of results to return
            start_index: Starting index for pagination
            **kwargs: Additional search parameters

        Returns:
            Search results dictionary

        Raises:
            SearchAPIError: If search fails
            RateLimitError: If rate limit is exceeded
            CircuitBreakerOpenError: If circuit breaker is open
        """
        # Check rate limit
        self.rate_limiter.acquire()
        
        # Prepare search parameters
        search_params = {
            'q': query,
            'cx': self.config.google_cse_id,
            'num': min(num_results, 10),  # Google limits to 10 per request
            'start': start_index,
            **kwargs
        }
        
        # Execute with circuit breaker protection
        def _do_search():
            try:
                self.metrics['total_requests'] += 1
                result = self._service.cse().list(**search_params).execute()
                self.metrics['successful_requests'] += 1
                return result
            except HttpError as e:
                self.metrics['failed_requests'] += 1
                if e.resp.status == 429:
                    raise QuotaExceededError(f"API quota exceeded: {e}")
                elif e.resp.status == 403:
                    raise AuthenticationError(f"Authentication failed: {e}")
                else:
                    raise SearchAPIError(f"Search API error: {e}")
            except Exception as e:
                self.metrics['failed_requests'] += 1
                raise SearchAPIError(f"Unexpected error: {e}")
        
        try:
            return self.circuit_breaker.call(_do_search)
        except CircuitBreakerOpenError as e:
            self.metrics['circuit_breaker_trips'] += 1
            raise e

    def _retry_with_backoff(self, func, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.config.retry_attempts):
            try:
                return func(*args, **kwargs)
            except (RateLimitError, CircuitBreakerOpenError) as e:
                # Don't retry rate limit or circuit breaker errors
                raise e
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    wait_time = self.config.retry_backoff ** attempt
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"All {self.config.retry_attempts} attempts failed")
        
        raise last_exception

    def _parse_search_results(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse and normalize search results.

        Args:
            raw_results: Raw API response

        Returns:
            List of normalized result dictionaries
        """
        items = raw_results.get('items', [])
        results = []
        
        for item in items:
            result = {
                'title': item.get('title', ''),
                'link': item.get('link', ''),
                'snippet': item.get('snippet', ''),
                'displayLink': item.get('displayLink', ''),
                'formattedUrl': item.get('formattedUrl', ''),
            }
            
            # Add image-specific metadata if present
            if 'image' in item:
                result['image'] = {
                    'contextLink': item['image'].get('contextLink', ''),
                    'height': item['image'].get('height', 0),
                    'width': item['image'].get('width', 0),
                    'byteSize': item['image'].get('byteSize', 0),
                    'thumbnailLink': item['image'].get('thumbnailLink', '')
                }
            
            # Add page metadata if present
            if 'pagemap' in item:
                result['metadata'] = item['pagemap']
            
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
        exclude_terms: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the web using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10 per request)
            start_index: Starting index for pagination (1-based)
            language: Language code for results (e.g., 'en', 'zh-CN')
            country: Country code for results (e.g., 'us', 'cn')
            safe_search: Safe search level ('off', 'medium', 'high')
            date_restrict: Restrict results by date (e.g., 'd5' for last 5 days)
            file_type: Filter by file type (e.g., 'pdf', 'doc')
            exclude_terms: Terms to exclude from results

        Returns:
            List of search result dictionaries with title, link, snippet, etc.

        Raises:
            ValidationError: If query is invalid
            SearchAPIError: If search fails
            RateLimitError: If rate limit is exceeded

        Examples:
            >>> tool = SearchTool()
            >>> results = tool.search_web("artificial intelligence", num_results=5)
            >>> print(results[0]['title'])
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        if num_results < 1 or num_results > 100:
            raise ValidationError("num_results must be between 1 and 100")
        
        search_params = {
            'lr': f'lang_{language}',
            'cr': f'country{country.upper()}',
            'safe': safe_search,
        }
        
        if date_restrict:
            search_params['dateRestrict'] = date_restrict
        
        if file_type:
            search_params['fileType'] = file_type
        
        if exclude_terms:
            query = f"{query} -{exclude_terms}"
        
        raw_results = self._retry_with_backoff(
            self._execute_search,
            query,
            num_results,
            start_index,
            **search_params
        )
        
        return self._parse_search_results(raw_results)

    def search_images(
        self,
        query: str,
        num_results: int = 10,
        image_size: Optional[str] = None,
        image_type: Optional[str] = None,
        image_color_type: Optional[str] = None,
        safe_search: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Search for images using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10 per request)
            image_size: Image size filter ('icon', 'small', 'medium', 'large', 'xlarge', 'xxlarge', 'huge')
            image_type: Image type filter ('clipart', 'face', 'lineart', 'stock', 'photo', 'animated')
            image_color_type: Color type filter ('color', 'gray', 'mono', 'trans')
            safe_search: Safe search level ('off', 'medium', 'high')

        Returns:
            List of image result dictionaries with URL, thumbnail, dimensions, etc.

        Raises:
            ValidationError: If query is invalid
            SearchAPIError: If search fails

        Examples:
            >>> tool = SearchTool()
            >>> results = tool.search_images("sunset beach", num_results=5, image_size="large")
            >>> print(results[0]['link'])
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        search_params = {
            'searchType': 'image',
            'safe': safe_search,
        }
        
        if image_size:
            search_params['imgSize'] = image_size
        
        if image_type:
            search_params['imgType'] = image_type
        
        if image_color_type:
            search_params['imgColorType'] = image_color_type
        
        raw_results = self._retry_with_backoff(
            self._execute_search,
            query,
            num_results,
            1,
            **search_params
        )
        
        return self._parse_search_results(raw_results)

    def search_news(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        date_restrict: Optional[str] = None,
        sort_by: str = "date"
    ) -> List[Dict[str, Any]]:
        """
        Search for news articles using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10 per request)
            start_index: Starting index for pagination (1-based)
            language: Language code for results (e.g., 'en', 'zh-CN')
            date_restrict: Restrict results by date (e.g., 'd5' for last 5 days, 'w2' for last 2 weeks)
            sort_by: Sort order ('date' or 'relevance')

        Returns:
            List of news article dictionaries with title, link, snippet, date, etc.

        Raises:
            ValidationError: If query is invalid
            SearchAPIError: If search fails

        Examples:
            >>> tool = SearchTool()
            >>> results = tool.search_news("climate change", date_restrict="w1")
            >>> print(results[0]['title'])
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        # Add "news" to the query to prioritize news sources
        news_query = f"{query} news"
        
        search_params = {
            'lr': f'lang_{language}',
            'sort': sort_by if sort_by == 'date' else '',
        }
        
        if date_restrict:
            search_params['dateRestrict'] = date_restrict
        
        raw_results = self._retry_with_backoff(
            self._execute_search,
            news_query,
            num_results,
            start_index,
            **search_params
        )
        
        return self._parse_search_results(raw_results)

    def search_videos(
        self,
        query: str,
        num_results: int = 10,
        start_index: int = 1,
        language: str = "en",
        safe_search: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Search for videos using Google Custom Search API.

        Args:
            query: Search query string
            num_results: Number of results to return (max 10 per request)
            start_index: Starting index for pagination (1-based)
            language: Language code for results (e.g., 'en', 'zh-CN')
            safe_search: Safe search level ('off', 'medium', 'high')

        Returns:
            List of video result dictionaries with title, link, snippet, etc.

        Raises:
            ValidationError: If query is invalid
            SearchAPIError: If search fails

        Examples:
            >>> tool = SearchTool()
            >>> results = tool.search_videos("python tutorial", num_results=5)
            >>> print(results[0]['title'])
        """
        if not query or not query.strip():
            raise ValidationError("Query cannot be empty")
        
        # Add file type filter for video content
        video_query = f"{query} filetype:mp4 OR filetype:webm OR filetype:mov"
        
        search_params = {
            'lr': f'lang_{language}',
            'safe': safe_search,
        }
        
        raw_results = self._retry_with_backoff(
            self._execute_search,
            video_query,
            num_results,
            start_index,
            **search_params
        )
        
        return self._parse_search_results(raw_results)

    # ========================================================================
    # Advanced Features
    # ========================================================================

    def search_paginated(
        self,
        query: str,
        total_results: int,
        search_type: str = "web",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Perform paginated search to retrieve more than 10 results.

        Google Custom Search API limits each request to 10 results. This method
        automatically handles pagination to retrieve larger result sets.

        Args:
            query: Search query string
            total_results: Total number of results to retrieve
            search_type: Type of search ('web', 'image', 'news', 'video')
            **kwargs: Additional search parameters for the specific search type

        Returns:
            List of all search results combined from multiple pages

        Raises:
            ValidationError: If parameters are invalid
            SearchAPIError: If search fails

        Examples:
            >>> tool = SearchTool()
            >>> results = tool.search_paginated("machine learning", total_results=25)
            >>> len(results)
            25
        """
        if total_results < 1 or total_results > 100:
            raise ValidationError("total_results must be between 1 and 100")
        
        # Select search method based on type
        search_methods = {
            'web': self.search_web,
            'image': self.search_images,
            'news': self.search_news,
            'video': self.search_videos,
        }
        
        if search_type not in search_methods:
            raise ValidationError(f"Invalid search_type: {search_type}")
        
        search_method = search_methods[search_type]
        all_results = []
        
        # Calculate number of pages needed
        results_per_page = 10
        num_pages = (total_results + results_per_page - 1) // results_per_page
        
        for page in range(num_pages):
            start_index = page * results_per_page + 1
            page_size = min(results_per_page, total_results - len(all_results))
            
            try:
                page_results = search_method(
                    query=query,
                    num_results=page_size,
                    start_index=start_index,
                    **kwargs
                )
                all_results.extend(page_results)
                
                if len(all_results) >= total_results:
                    break
                    
            except QuotaExceededError:
                self.logger.warning(
                    f"Quota exceeded after {len(all_results)} results"
                )
                break
        
        return all_results[:total_results]

    async def search_batch(
        self,
        queries: List[str],
        search_type: str = "web",
        num_results: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Execute multiple search queries in batch with async execution.

        Args:
            queries: List of search query strings
            search_type: Type of search ('web', 'image', 'news', 'video')
            num_results: Number of results per query

        Returns:
            Dictionary mapping queries to their search results

        Raises:
            ValidationError: If parameters are invalid

        Examples:
            >>> tool = SearchTool()
            >>> queries = ["AI", "machine learning", "deep learning"]
            >>> results = await tool.search_batch(queries, num_results=5)
            >>> print(results["AI"][0]['title'])
        """
        if not queries:
            raise ValidationError("queries list cannot be empty")
        
        # Select search method
        search_methods = {
            'web': self.search_web,
            'image': self.search_images,
            'news': self.search_news,
            'video': self.search_videos,
        }
        
        if search_type not in search_methods:
            raise ValidationError(f"Invalid search_type: {search_type}")
        
        search_method = search_methods[search_type]
        
        # Execute searches in parallel using asyncio
        async def _search_async(query: str):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                search_method,
                query,
                num_results
            )
        
        tasks = [_search_async(query) for query in queries]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build results dictionary
        results_dict = {}
        for query, result in zip(queries, results_list):
            if isinstance(result, Exception):
                self.logger.error(f"Search failed for query '{query}': {result}")
                results_dict[query] = []
            else:
                results_dict[query] = result
        
        return results_dict

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def validate_credentials(self) -> Dict[str, Any]:
        """
        Validate API credentials by performing a test search.

        Returns:
            Dictionary with validation status and details

        Examples:
            >>> tool = SearchTool()
            >>> status = tool.validate_credentials()
            >>> print(status['valid'])
            True
        """
        try:
            # Perform a minimal test search
            result = self._execute_search("test", num_results=1)
            
            return {
                'valid': True,
                'method': 'api_key' if self.config.google_api_key else 'service_account',
                'cse_id': self.config.google_cse_id,
                'message': 'Credentials are valid and working'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'message': 'Credentials validation failed'
            }

    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get current quota and rate limit status.

        Returns:
            Dictionary with quota information including remaining requests,
            circuit breaker state, and usage metrics

        Examples:
            >>> tool = SearchTool()
            >>> status = tool.get_quota_status()
            >>> print(f"Remaining quota: {status['remaining_quota']}")
        """
        return {
            'remaining_quota': self.rate_limiter.get_remaining_quota(),
            'max_requests': self.config.rate_limit_requests,
            'time_window_seconds': self.config.rate_limit_window,
            'circuit_breaker_state': self.circuit_breaker.get_state(),
            'metrics': self.metrics.copy()
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get detailed metrics about tool usage.

        Returns:
            Dictionary with usage metrics

        Examples:
            >>> tool = SearchTool()
            >>> metrics = tool.get_metrics()
            >>> print(f"Success rate: {metrics['success_rate']:.2%}")
        """
        total = self.metrics['total_requests']
        success_rate = (
            self.metrics['successful_requests'] / total if total > 0 else 0
        )
        
        return {
            **self.metrics,
            'success_rate': success_rate,
            'circuit_breaker_state': self.circuit_breaker.get_state(),
            'remaining_quota': self.rate_limiter.get_remaining_quota()
        }

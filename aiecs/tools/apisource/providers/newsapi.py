"""
News API Provider

Provides access to news articles from various sources worldwide.
Supports headline retrieval, article search, and source listing.

API Documentation: https://newsapi.org/docs
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.providers.base import (
    BaseAPIProvider,
    expose_operation,
)

logger = logging.getLogger(__name__)

# Optional HTTP client
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NewsAPIProvider(BaseAPIProvider):
    """
    News API provider for accessing news articles and headlines.

    Provides access to:
    - Top headlines from various sources
    - Article search by keywords
    - News sources listing
    - Filtering by country, language, category
    """

    BASE_URL = "https://newsapi.org/v2"

    @property
    def name(self) -> str:
        return "newsapi"

    @property
    def description(self) -> str:
        return "News API for accessing news articles, headlines, and sources worldwide"

    @property
    def supported_operations(self) -> List[str]:
        return ["get_top_headlines", "search_everything", "get_sources"]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for News API operations"""

        if operation == "get_top_headlines":
            # At least one of these is required
            if not any(k in params for k in ["q", "country", "category", "sources"]):
                return (
                    False,
                    "At least one of q, country, category, or sources is required",
                )

        elif operation == "search_everything":
            if "q" not in params:
                return False, "Missing required parameter: q (search query)"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_top_headlines",
        description="Get top news headlines from various sources with optional filtering",
    )
    def get_top_headlines(
        self,
        q: Optional[str] = None,
        country: Optional[str] = None,
        category: Optional[str] = None,
        sources: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get top headlines.

        Args:
            q: Keywords or phrases to search for in article title and body
            country: 2-letter ISO country code (e.g., 'us', 'gb', 'cn')
            category: Category (business, entertainment, general, health, science, sports, technology)
            sources: Comma-separated news source IDs
            page_size: Number of results to return (max 100)

        Returns:
            Dictionary containing news articles and metadata
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if country:
            params["country"] = country
        if category:
            params["category"] = category
        if sources:
            params["sources"] = sources
        if page_size:
            params["page_size"] = page_size

        return self.execute("get_top_headlines", params)

    @expose_operation(
        operation_name="search_everything",
        description="Search through millions of articles from news sources and blogs",
    )
    def search_everything(
        self,
        q: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: Optional[str] = None,
        sort_by: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search all articles.

        Args:
            q: Keywords or phrases to search for
            from_date: Start date (YYYY-MM-DD or ISO 8601)
            to_date: End date (YYYY-MM-DD or ISO 8601)
            language: 2-letter ISO language code (e.g., 'en', 'es', 'fr')
            sort_by: Sort order (relevancy, popularity, publishedAt)
            page_size: Number of results to return (max 100)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"q": q}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        if language:
            params["language"] = language
        if sort_by:
            params["sortBy"] = sort_by
        if page_size:
            params["pageSize"] = page_size

        return self.execute("search_everything", params)

    @expose_operation(
        operation_name="get_sources",
        description="Get the list of available news sources",
    )
    def get_sources(
        self,
        category: Optional[str] = None,
        language: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get available news sources.

        Args:
            category: Filter by category
            language: Filter by language (2-letter ISO code)
            country: Filter by country (2-letter ISO code)

        Returns:
            Dictionary containing list of news sources
        """
        params = {}
        if category:
            params["category"] = category
        if language:
            params["language"] = language
        if country:
            params["country"] = country

        return self.execute("get_sources", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from News API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for News API provider")

        # Get API key
        api_key = self._get_api_key("NEWSAPI_API_KEY")
        if not api_key:
            raise ValueError("News API key not found. Set NEWSAPI_API_KEY environment variable or " "provide 'api_key' in config. Get your key at https://newsapi.org")

        headers = {"X-Api-Key": api_key}
        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "get_top_headlines":
            endpoint = f"{self.BASE_URL}/top-headlines"
            query_params = {}

            # Optional parameters
            if "q" in params:
                query_params["q"] = params["q"]
            if "country" in params:
                query_params["country"] = params["country"]
            if "category" in params:
                query_params["category"] = params["category"]
            if "sources" in params:
                query_params["sources"] = params["sources"]
            if "page_size" in params:
                query_params["pageSize"] = params["page_size"]
            if "page" in params:
                query_params["page"] = params["page"]

        elif operation == "search_everything":
            endpoint = f"{self.BASE_URL}/everything"
            query_params = {"q": params["q"]}

            # Optional parameters
            if "from_date" in params:
                query_params["from"] = params["from_date"]
            elif "days_back" in params:
                # Convenience parameter: go back N days
                from_date = datetime.now() - timedelta(days=params["days_back"])
                query_params["from"] = from_date.strftime("%Y-%m-%d")

            if "to_date" in params:
                query_params["to"] = params["to_date"]
            if "language" in params:
                query_params["language"] = params["language"]
            if "sort_by" in params:
                query_params["sortBy"] = params["sort_by"]
            if "page_size" in params:
                query_params["pageSize"] = params["page_size"]
            if "page" in params:
                query_params["page"] = params["page"]

        elif operation == "get_sources":
            endpoint = f"{self.BASE_URL}/top-headlines/sources"
            query_params = {}

            # Optional parameters
            if "country" in params:
                query_params["country"] = params["country"]
            if "language" in params:
                query_params["language"] = params["language"]
            if "category" in params:
                query_params["category"] = params["category"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, headers=headers, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Check API response status
            if data.get("status") != "ok":
                raise Exception(f"News API error: {data.get('message', 'Unknown error')}")

            # Extract relevant data
            if operation == "get_sources":
                result_data = data.get("sources", [])
            else:
                result_data = {
                    "articles": data.get("articles", []),
                    "total_results": data.get("totalResults", 0),
                }

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"News API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"News API request failed: {e}")
            raise Exception(f"News API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for News API operations"""

        schemas = {
            "get_top_headlines": {
                "description": "Get top news headlines",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Keywords or phrases to search for",
                        "examples": [
                            "bitcoin",
                            "climate change",
                            "technology",
                        ],
                    },
                    "country": {
                        "type": "string",
                        "required": False,
                        "description": "2-letter ISO country code",
                        "examples": ["us", "gb", "cn", "jp"],
                    },
                    "category": {
                        "type": "string",
                        "required": False,
                        "description": "News category",
                        "examples": [
                            "business",
                            "entertainment",
                            "health",
                            "science",
                            "sports",
                            "technology",
                        ],
                    },
                    "sources": {
                        "type": "string",
                        "required": False,
                        "description": "Comma-separated news source IDs",
                        "examples": ["bbc-news", "cnn", "the-verge"],
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results (max 100)",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "search_everything": {
                "description": "Search all news articles",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Keywords or phrases to search for",
                        "examples": [
                            "artificial intelligence",
                            "climate summit",
                            "stock market",
                        ],
                    },
                    "from_date": {
                        "type": "string",
                        "required": False,
                        "description": "Start date (YYYY-MM-DD)",
                        "examples": ["2024-01-01", "2024-10-01"],
                    },
                    "to_date": {
                        "type": "string",
                        "required": False,
                        "description": "End date (YYYY-MM-DD)",
                        "examples": ["2024-12-31", "2024-10-17"],
                    },
                    "language": {
                        "type": "string",
                        "required": False,
                        "description": "2-letter ISO language code",
                        "examples": ["en", "es", "fr", "de"],
                    },
                    "sort_by": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["relevancy", "popularity", "publishedAt"],
                        "default": "publishedAt",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results (max 100)",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "get_sources": {
                "description": "Get available news sources",
                "parameters": {
                    "category": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by category",
                        "examples": ["business", "technology", "sports"],
                    },
                    "language": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by language (2-letter ISO code)",
                        "examples": ["en", "es", "fr"],
                    },
                    "country": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by country (2-letter ISO code)",
                        "examples": ["us", "gb", "cn"],
                    },
                },
            },
        }

        return schemas.get(operation)

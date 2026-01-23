"""
Wikipedia API Provider

Provides access to Wikipedia's extensive encyclopedia content via the MediaWiki API.
Supports article search, page content retrieval, page summaries, and random articles.

API Documentation: https://www.mediawiki.org/wiki/API:Main_page
REST API: https://en.wikipedia.org/api/rest_v1/
API Etiquette: https://www.mediawiki.org/wiki/API:Etiquette

No API key required - completely free and open

IMPORTANT - Wikipedia API Rules:
1. User-Agent Header: REQUIRED - Must set unique User-Agent with contact info
   Format: "AppName/Version (URL; contact@email.com)"
2. Rate Limiting: Maximum 200 requests/second (we default to 10 req/s)
3. Caching: Cache responses when possible to reduce server load
"""

import logging
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


class WikipediaProvider(BaseAPIProvider):
    """
    Wikipedia API provider for encyclopedia content.

    Provides access to:
    - Article search by title or content
    - Page summaries and extracts
    - Full page content
    - Random articles
    - Page metadata and information
    """

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    REST_BASE_URL = "https://en.wikipedia.org/api/rest_v1"

    @property
    def name(self) -> str:
        return "wikipedia"

    @property
    def description(self) -> str:
        return "Wikipedia API for encyclopedia articles, summaries, and content"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_pages",
            "get_page_summary",
            "get_page_content",
            "get_random_page",
            "get_page_info",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Wikipedia operations"""

        if operation == "search_pages":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_page_summary":
            if "title" not in params:
                return False, "Missing required parameter: title"

        elif operation == "get_page_content":
            if "title" not in params:
                return False, "Missing required parameter: title"

        elif operation == "get_page_info":
            if "title" not in params:
                return False, "Missing required parameter: title"

        elif operation == "get_random_page":
            # No required parameters
            pass

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_pages",
        description="Search Wikipedia articles by title or content",
    )
    def search_pages(
        self,
        query: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for Wikipedia articles.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if limit:
            params["limit"] = limit

        return self.execute("search_pages", params)

    @expose_operation(
        operation_name="get_page_summary",
        description="Get a summary/extract of a Wikipedia page",
    )
    def get_page_summary(self, title: str) -> Dict[str, Any]:
        """
        Get page summary using REST API.

        Args:
            title: Wikipedia page title

        Returns:
            Dictionary containing page summary
        """
        return self.execute("get_page_summary", {"title": title})

    @expose_operation(
        operation_name="get_page_content",
        description="Get full content of a Wikipedia page",
    )
    def get_page_content(self, title: str) -> Dict[str, Any]:
        """
        Get full page content.

        Args:
            title: Wikipedia page title

        Returns:
            Dictionary containing full page content
        """
        return self.execute("get_page_content", {"title": title})

    @expose_operation(
        operation_name="get_random_page",
        description="Get a random Wikipedia article",
    )
    def get_random_page(self) -> Dict[str, Any]:
        """
        Get a random Wikipedia page.

        Returns:
            Dictionary containing random page information
        """
        return self.execute("get_random_page", {})

    @expose_operation(
        operation_name="get_page_info",
        description="Get metadata and information about a Wikipedia page",
    )
    def get_page_info(self, title: str) -> Dict[str, Any]:
        """
        Get page metadata and information.

        Args:
            title: Wikipedia page title

        Returns:
            Dictionary containing page information
        """
        return self.execute("get_page_info", {"title": title})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Wikipedia API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Wikipedia provider")

        # Wikipedia doesn't require API key
        timeout = self.config.get("timeout", 30)

        # Set User-Agent header as required by Wikipedia API rules
        # See: https://www.mediawiki.org/wiki/API:Etiquette
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
            "Api-User-Agent": user_agent,
        }

        # Build endpoint based on operation
        if operation == "search_pages":
            endpoint = self.BASE_URL
            query_params = {
                "action": "query",
                "list": "search",
                "srsearch": params["query"],
                "srlimit": params.get("limit", 10),
                "format": "json",
            }

        elif operation == "get_page_summary":
            # Use REST API for summaries
            title = params["title"].replace(" ", "_")
            endpoint = f"{self.REST_BASE_URL}/page/summary/{title}"
            query_params = {}

        elif operation == "get_page_content":
            endpoint = self.BASE_URL
            query_params = {
                "action": "query",
                "titles": params["title"],
                "prop": "extracts|revisions",
                "rvprop": "content",
                "format": "json",
            }

        elif operation == "get_random_page":
            endpoint = self.BASE_URL
            query_params = {
                "action": "query",
                "list": "random",
                "rnnamespace": "0",  # Main namespace only
                "rnlimit": "1",
                "format": "json",
            }

        elif operation == "get_page_info":
            endpoint = self.BASE_URL
            query_params = {
                "action": "query",
                "titles": params["title"],
                "prop": "info|pageprops|categories",
                "inprop": "url|displaytitle",
                "format": "json",
            }

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request with proper headers
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract relevant data based on operation
            if operation == "search_pages":
                result_data = data.get("query", {}).get("search", [])
            elif operation == "get_page_summary":
                # REST API returns the summary directly
                result_data = data
            elif operation == "get_page_content":
                pages = data.get("query", {}).get("pages", {})
                # Get first (and only) page
                result_data = next(iter(pages.values())) if pages else {}
            elif operation == "get_random_page":
                result_data = data.get("query", {}).get("random", [])
            elif operation == "get_page_info":
                pages = data.get("query", {}).get("pages", {})
                result_data = next(iter(pages.values())) if pages else {}
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Wikipedia API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wikipedia API request failed: {e}")
            raise Exception(f"Wikipedia API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Wikipedia operations"""

        schemas = {
            "search_pages": {
                "description": "Search Wikipedia articles by title or content",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": ["Python programming", "Albert Einstein", "Machine learning"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                },
            },
            "get_page_summary": {
                "description": "Get a summary/extract of a Wikipedia page",
                "parameters": {
                    "title": {
                        "type": "string",
                        "required": True,
                        "description": "Wikipedia page title",
                        "examples": ["Python (programming language)", "Albert Einstein", "Machine learning"],
                    }
                },
            },
            "get_page_content": {
                "description": "Get full content of a Wikipedia page",
                "parameters": {
                    "title": {
                        "type": "string",
                        "required": True,
                        "description": "Wikipedia page title",
                        "examples": ["Python (programming language)", "Albert Einstein", "Machine learning"],
                    }
                },
            },
            "get_random_page": {
                "description": "Get a random Wikipedia article",
                "parameters": {},
            },
            "get_page_info": {
                "description": "Get metadata and information about a Wikipedia page",
                "parameters": {
                    "title": {
                        "type": "string",
                        "required": True,
                        "description": "Wikipedia page title",
                        "examples": ["Python (programming language)", "Albert Einstein", "Machine learning"],
                    }
                },
            },
        }

        return schemas.get(operation)


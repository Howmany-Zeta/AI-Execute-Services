"""
Hacker News (Algolia Search API) Provider

Provides access to Hacker News stories, comments, and user data via Algolia's search API.
Supports searching stories, comments, and retrieving item details.

API Documentation: https://hn.algolia.com/api
No API key required - completely free and open

IMPORTANT - Hacker News API Rules:
1. Rate Limiting: Be respectful - implement reasonable delays between requests
2. Caching: Cache responses when possible to reduce server load
3. User-Agent: Set a descriptive User-Agent header
4. Max Results: Limited to 1000 results per query (pagination available)
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


class HackerNewsProvider(BaseAPIProvider):
    """
    Hacker News (Algolia Search API) provider for stories, comments, and user data.

    Provides access to:
    - Search stories by keywords
    - Search comments by keywords
    - Get item details by ID (story, comment, poll, etc.)
    - Get user information
    - Search by date or relevance
    """

    BASE_URL = "http://hn.algolia.com/api/v1"

    @property
    def name(self) -> str:
        return "hackernews"

    @property
    def description(self) -> str:
        return "Hacker News (Algolia Search API) for stories, comments, and discussions"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_stories",
            "search_comments",
            "search_by_date",
            "get_item",
            "get_user",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Hacker News operations"""

        if operation in ["search_stories", "search_comments", "search_by_date"]:
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_item":
            if "item_id" not in params:
                return False, "Missing required parameter: item_id"

        elif operation == "get_user":
            if "username" not in params:
                return False, "Missing required parameter: username"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_stories",
        description="Search Hacker News stories by keywords (sorted by relevance)",
    )
    def search_stories(
        self,
        query: str,
        tags: Optional[str] = None,
        num_comments: Optional[int] = None,
        page: Optional[int] = None,
        hits_per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for stories on Hacker News.

        Args:
            query: Search query string
            tags: Filter by tags (e.g., 'story', 'author_pg', 'story,author_pg')
            num_comments: Filter by minimum number of comments
            page: Page number for pagination (default: 0)
            hits_per_page: Number of results per page (default: 20, max: 1000)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if tags:
            params["tags"] = tags
        if num_comments is not None:
            params["num_comments"] = num_comments
        if page is not None:
            params["page"] = page
        if hits_per_page is not None:
            params["hits_per_page"] = hits_per_page

        return self.execute("search_stories", params)

    @expose_operation(
        operation_name="search_comments",
        description="Search Hacker News comments by keywords",
    )
    def search_comments(
        self,
        query: str,
        page: Optional[int] = None,
        hits_per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for comments on Hacker News.

        Args:
            query: Search query string
            page: Page number for pagination (default: 0)
            hits_per_page: Number of results per page (default: 20, max: 1000)

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"query": query}
        if page is not None:
            params["page"] = page
        if hits_per_page is not None:
            params["hits_per_page"] = hits_per_page

        return self.execute("search_comments", params)

    @expose_operation(
        operation_name="search_by_date",
        description="Search Hacker News items sorted by date (most recent first)",
    )
    def search_by_date(
        self,
        query: str,
        tags: Optional[str] = None,
        page: Optional[int] = None,
        hits_per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for items sorted by date.

        Args:
            query: Search query string
            tags: Filter by tags (e.g., 'story', 'comment', 'poll')
            page: Page number for pagination (default: 0)
            hits_per_page: Number of results per page (default: 20, max: 1000)

        Returns:
            Dictionary containing search results sorted by date
        """
        params: Dict[str, Any] = {"query": query}
        if tags:
            params["tags"] = tags
        if page is not None:
            params["page"] = page
        if hits_per_page is not None:
            params["hits_per_page"] = hits_per_page

        return self.execute("search_by_date", params)

    @expose_operation(
        operation_name="get_item",
        description="Get Hacker News item details by ID (story, comment, poll, etc.)",
    )
    def get_item(self, item_id: int) -> Dict[str, Any]:
        """
        Get item details by ID.

        Args:
            item_id: Hacker News item ID

        Returns:
            Dictionary containing item information
        """
        return self.execute("get_item", {"item_id": item_id})

    @expose_operation(
        operation_name="get_user",
        description="Get Hacker News user information by username",
    )
    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Get user information.

        Args:
            username: Hacker News username

        Returns:
            Dictionary containing user information
        """
        return self.execute("get_user", {"username": username})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Hacker News Algolia API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Hacker News provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header for API etiquette
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build endpoint and query parameters based on operation
        if operation == "search_stories":
            endpoint = f"{self.BASE_URL}/search"
            query_params = {
                "query": params["query"],
                "tags": params.get("tags", "story"),
            }
            if "num_comments" in params:
                query_params["numericFilters"] = f"num_comments>={params['num_comments']}"
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "search_comments":
            endpoint = f"{self.BASE_URL}/search"
            query_params = {
                "query": params["query"],
                "tags": "comment",
            }
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "search_by_date":
            endpoint = f"{self.BASE_URL}/search_by_date"
            query_params = {
                "query": params["query"],
            }
            if "tags" in params:
                query_params["tags"] = params["tags"]
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "get_item":
            endpoint = f"{self.BASE_URL}/items/{params['item_id']}"
            query_params = {}

        elif operation == "get_user":
            endpoint = f"{self.BASE_URL}/users/{params['username']}"
            query_params = {}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
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
            if operation in ["search_stories", "search_comments", "search_by_date"]:
                result_data = {
                    "hits": data.get("hits", []),
                    "nb_hits": data.get("nbHits", 0),
                    "page": data.get("page", 0),
                    "nb_pages": data.get("nbPages", 0),
                    "hits_per_page": data.get("hitsPerPage", 20),
                }
            else:
                # get_item or get_user
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Hacker News Algolia API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Hacker News API request failed: {e}")
            raise Exception(f"Hacker News API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Hacker News operations"""

        schemas = {
            "search_stories": {
                "description": "Search Hacker News stories by keywords",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": [
                            "python",
                            "artificial intelligence",
                            "startup",
                        ],
                    },
                    "tags": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by tags (e.g., 'story', 'author_pg')",
                        "examples": ["story", "author_pg", "story,author_pg"],
                    },
                    "num_comments": {
                        "type": "integer",
                        "required": False,
                        "description": "Minimum number of comments",
                        "examples": [10, 50, 100],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination (default: 0)",
                        "examples": [0, 1, 2],
                        "default": 0,
                    },
                    "hits_per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max: 1000)",
                        "examples": [20, 50, 100],
                        "default": 20,
                    },
                },
            },
            "search_comments": {
                "description": "Search Hacker News comments by keywords",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": [
                            "machine learning",
                            "react",
                            "database",
                        ],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination (default: 0)",
                        "examples": [0, 1, 2],
                        "default": 0,
                    },
                    "hits_per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max: 1000)",
                        "examples": [20, 50, 100],
                        "default": 20,
                    },
                },
            },
            "search_by_date": {
                "description": "Search Hacker News items sorted by date",
                "parameters": {
                    "query": {
                        "type": "string",
                        "required": True,
                        "description": "Search query string",
                        "examples": [
                            "AI",
                            "cryptocurrency",
                            "web development",
                        ],
                    },
                    "tags": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by tags (e.g., 'story', 'comment', 'poll')",
                        "examples": ["story", "comment", "poll"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination (default: 0)",
                        "examples": [0, 1, 2],
                        "default": 0,
                    },
                    "hits_per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max: 1000)",
                        "examples": [20, 50, 100],
                        "default": 20,
                    },
                },
            },
            "get_item": {
                "description": "Get Hacker News item details by ID",
                "parameters": {
                    "item_id": {
                        "type": "integer",
                        "required": True,
                        "description": "Hacker News item ID",
                        "examples": [1, 8863, 121003],
                    },
                },
            },
            "get_user": {
                "description": "Get Hacker News user information",
                "parameters": {
                    "username": {
                        "type": "string",
                        "required": True,
                        "description": "Hacker News username",
                        "examples": ["pg", "dang", "tptacek"],
                    },
                },
            },
        }

        return schemas.get(operation)

    @expose_operation(
        operation_name="search_by_date",
        description="Search Hacker News items sorted by date (most recent first)",
    )
    def search_by_date(
        self,
        query: str,
        tags: Optional[str] = None,
        page: Optional[int] = None,
        hits_per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for items sorted by date.

        Args:
            query: Search query string
            tags: Filter by tags (e.g., 'story', 'comment', 'poll')
            page: Page number for pagination (default: 0)
            hits_per_page: Number of results per page (default: 20, max: 1000)

        Returns:
            Dictionary containing search results sorted by date
        """
        params: Dict[str, Any] = {"query": query}
        if tags:
            params["tags"] = tags
        if page is not None:
            params["page"] = page
        if hits_per_page is not None:
            params["hits_per_page"] = hits_per_page

        return self.execute("search_by_date", params)

    @expose_operation(
        operation_name="get_item",
        description="Get Hacker News item details by ID (story, comment, poll, etc.)",
    )
    def get_item(self, item_id: int) -> Dict[str, Any]:
        """
        Get item details by ID.

        Args:
            item_id: Hacker News item ID

        Returns:
            Dictionary containing item information
        """
        return self.execute("get_item", {"item_id": item_id})

    @expose_operation(
        operation_name="get_user",
        description="Get Hacker News user information by username",
    )
    def get_user(self, username: str) -> Dict[str, Any]:
        """
        Get user information.

        Args:
            username: Hacker News username

        Returns:
            Dictionary containing user information
        """
        return self.execute("get_user", {"username": username})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Hacker News Algolia API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Hacker News provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header for API etiquette
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build endpoint and query parameters based on operation
        if operation == "search_stories":
            endpoint = f"{self.BASE_URL}/search"
            query_params = {
                "query": params["query"],
                "tags": params.get("tags", "story"),
            }
            if "num_comments" in params:
                query_params["numericFilters"] = f"num_comments>={params['num_comments']}"
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "search_comments":
            endpoint = f"{self.BASE_URL}/search"
            query_params = {
                "query": params["query"],
                "tags": "comment",
            }
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "search_by_date":
            endpoint = f"{self.BASE_URL}/search_by_date"
            query_params = {
                "query": params["query"],
            }
            if "tags" in params:
                query_params["tags"] = params["tags"]
            if "page" in params:
                query_params["page"] = params["page"]
            if "hits_per_page" in params:
                query_params["hitsPerPage"] = min(params["hits_per_page"], 1000)

        elif operation == "get_item":
            endpoint = f"{self.BASE_URL}/items/{params['item_id']}"
            query_params = {}

        elif operation == "get_user":
            endpoint = f"{self.BASE_URL}/users/{params['username']}"
            query_params = {}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
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
            if operation in ["search_stories", "search_comments", "search_by_date"]:
                result_data = {
                    "hits": data.get("hits", []),
                    "nb_hits": data.get("nbHits", 0),
                    "page": data.get("page", 0),
                    "nb_pages": data.get("nbPages", 0),
                    "hits_per_page": data.get("hitsPerPage", 20),
                }
            else:
                # get_item or get_user
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Hacker News Algolia API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Hacker News API request failed: {e}")
            raise Exception(f"Hacker News API request failed: {str(e)}")


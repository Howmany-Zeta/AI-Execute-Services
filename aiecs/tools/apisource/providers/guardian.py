"""
The Guardian API Provider

Provides access to The Guardian's news content, including articles, tags, and sections.
Supports comprehensive content search, filtering, and metadata retrieval.

API Documentation: https://open-platform.theguardian.com/documentation/
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


class GuardianProvider(BaseAPIProvider):
    """
    The Guardian API provider for accessing news content and metadata.

    Provides access to:
    - Content search across all Guardian articles
    - Tags (keywords, contributors, series, etc.)
    - Sections (news categories)
    - Single item retrieval
    - Advanced filtering and field selection
    """

    BASE_URL = "https://content.guardianapis.com"

    @property
    def name(self) -> str:
        return "guardian"

    @property
    def description(self) -> str:
        return "The Guardian API for accessing news articles, tags, sections, and comprehensive content search"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_content",
            "get_item",
            "get_tags",
            "get_sections",
            "search_tags",
            "get_edition",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Guardian API operations"""

        if operation == "get_item":
            if "item_id" not in params:
                return False, "Missing required parameter: item_id"

        elif operation == "search_tags":
            if "q" not in params:
                return False, "Missing required parameter: q (search query)"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_content",
        description="Search all Guardian content with advanced filtering options",
    )
    def search_content(
        self,
        q: Optional[str] = None,
        section: Optional[str] = None,
        tag: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        order_by: Optional[str] = None,
        page_size: Optional[int] = None,
        page: Optional[int] = None,
        show_fields: Optional[str] = None,
        show_tags: Optional[str] = None,
        show_references: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search Guardian content.

        Args:
            q: Search query text
            section: Filter by section (e.g., 'politics', 'technology', 'business')
            tag: Filter by tag (e.g., 'technology/artificial-intelligence')
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            order_by: Sort order (newest, oldest, relevance)
            page_size: Number of results per page (max 200)
            page: Page number (1-indexed)
            show_fields: Comma-separated fields to include (e.g., 'headline,body,thumbnail')
            show_tags: Comma-separated tag types (e.g., 'keyword,contributor')
            show_references: Comma-separated reference types

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {}
        if q:
            params["q"] = q
        if section:
            params["section"] = section
        if tag:
            params["tag"] = tag
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if order_by:
            params["order_by"] = order_by
        if page_size:
            params["page_size"] = page_size
        if page:
            params["page"] = page
        if show_fields:
            params["show_fields"] = show_fields
        if show_tags:
            params["show_tags"] = show_tags
        if show_references:
            params["show_references"] = show_references

        return self.execute("search_content", params)

    @expose_operation(
        operation_name="get_item",
        description="Get a specific Guardian content item by ID",
    )
    def get_item(
        self,
        item_id: str,
        show_fields: Optional[str] = None,
        show_tags: Optional[str] = None,
        show_references: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific content item.

        Args:
            item_id: The Guardian content ID (e.g., 'technology/2024/jan/01/article-slug')
            show_fields: Comma-separated fields to include
            show_tags: Comma-separated tag types
            show_references: Comma-separated reference types

        Returns:
            Dictionary containing the content item
        """
        params: Dict[str, Any] = {"item_id": item_id}
        if show_fields:
            params["show_fields"] = show_fields
        if show_tags:
            params["show_tags"] = show_tags
        if show_references:
            params["show_references"] = show_references

        return self.execute("get_item", params)

    @expose_operation(
        operation_name="get_tags",
        description="Get all tags or filter tags by type",
    )
    def get_tags(
        self,
        tag_type: Optional[str] = None,
        section: Optional[str] = None,
        page_size: Optional[int] = None,
        page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get tags from The Guardian.

        Args:
            tag_type: Filter by tag type (keyword, contributor, series, blog, etc.)
            section: Filter by section
            page_size: Number of results per page
            page: Page number

        Returns:
            Dictionary containing tags
        """
        params: Dict[str, Any] = {}
        if tag_type:
            params["type"] = tag_type
        if section:
            params["section"] = section
        if page_size:
            params["page_size"] = page_size
        if page:
            params["page"] = page

        return self.execute("get_tags", params)

    @expose_operation(
        operation_name="get_sections",
        description="Get all sections from The Guardian",
    )
    def get_sections(self) -> Dict[str, Any]:
        """
        Get all sections.

        Returns:
            Dictionary containing all Guardian sections
        """
        return self.execute("get_sections", {})

    @expose_operation(
        operation_name="search_tags",
        description="Search for tags by query",
    )
    def search_tags(
        self,
        q: str,
        tag_type: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for tags.

        Args:
            q: Search query
            tag_type: Filter by tag type
            page_size: Number of results

        Returns:
            Dictionary containing matching tags
        """
        params: Dict[str, Any] = {"q": q}
        if tag_type:
            params["type"] = tag_type
        if page_size:
            params["page_size"] = page_size

        return self.execute("search_tags", params)

    @expose_operation(
        operation_name="get_edition",
        description="Get content for a specific Guardian edition",
    )
    def get_edition(
        self,
        edition: str = "uk",
        page_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get content for a specific edition.

        Args:
            edition: Edition code (uk, us, au, international)
            page_size: Number of results

        Returns:
            Dictionary containing edition content
        """
        params: Dict[str, Any] = {"edition": edition}
        if page_size:
            params["page_size"] = page_size

        return self.execute("get_edition", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from The Guardian API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Guardian API provider")

        # Get API key
        api_key = self._get_api_key("GUARDIAN_API_KEY")
        if not api_key:
            raise ValueError(
                "Guardian API key not found. Set GUARDIAN_API_KEY environment variable or "
                "provide 'api_key' in config. Get your key at https://open-platform.theguardian.com/access/"
            )

        timeout = self.config.get("timeout", 30)

        # Build endpoint and query parameters based on operation
        if operation == "search_content":
            endpoint = f"{self.BASE_URL}/search"
            query_params = {"api-key": api_key}

            # Add search parameters
            if "q" in params:
                query_params["q"] = params["q"]
            if "section" in params:
                query_params["section"] = params["section"]
            if "tag" in params:
                query_params["tag"] = params["tag"]
            if "from_date" in params:
                query_params["from-date"] = params["from_date"]
            elif "days_back" in params:
                # Convenience parameter
                from_date = datetime.now() - timedelta(days=params["days_back"])
                query_params["from-date"] = from_date.strftime("%Y-%m-%d")
            if "to_date" in params:
                query_params["to-date"] = params["to_date"]
            if "order_by" in params:
                query_params["order-by"] = params["order_by"]
            if "page_size" in params:
                query_params["page-size"] = min(params["page_size"], 200)
            if "page" in params:
                query_params["page"] = params["page"]
            if "show_fields" in params:
                query_params["show-fields"] = params["show_fields"]
            if "show_tags" in params:
                query_params["show-tags"] = params["show_tags"]
            if "show_references" in params:
                query_params["show-references"] = params["show_references"]

        elif operation == "get_item":
            item_id = params["item_id"]
            endpoint = f"{self.BASE_URL}/{item_id}"
            query_params = {"api-key": api_key}

            if "show_fields" in params:
                query_params["show-fields"] = params["show_fields"]
            if "show_tags" in params:
                query_params["show-tags"] = params["show_tags"]
            if "show_references" in params:
                query_params["show-references"] = params["show_references"]

        elif operation == "get_tags" or operation == "search_tags":
            endpoint = f"{self.BASE_URL}/tags"
            query_params = {"api-key": api_key}

            if "q" in params:
                query_params["q"] = params["q"]
            if "type" in params:
                query_params["type"] = params["type"]
            if "section" in params:
                query_params["section"] = params["section"]
            if "page_size" in params:
                query_params["page-size"] = params["page_size"]
            if "page" in params:
                query_params["page"] = params["page"]

        elif operation == "get_sections":
            endpoint = f"{self.BASE_URL}/sections"
            query_params = {"api-key": api_key}

        elif operation == "get_edition":
            edition = params.get("edition", "uk")
            endpoint = f"{self.BASE_URL}/{edition}"
            query_params = {"api-key": api_key}

            if "page_size" in params:
                query_params["page-size"] = params["page_size"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Check API response status
            if data.get("response", {}).get("status") != "ok":
                error_msg = data.get("response", {}).get("message", "Unknown error")
                raise Exception(f"Guardian API error: {error_msg}")

            # Extract relevant data
            response_data = data.get("response", {})

            if operation == "get_item":
                result_data = response_data.get("content", {})
            elif operation == "get_sections":
                result_data = response_data.get("results", [])
            elif operation == "get_tags" or operation == "search_tags":
                result_data = response_data.get("results", [])
            else:  # search_content, get_edition
                result_data = {
                    "results": response_data.get("results", []),
                    "total": response_data.get("total", 0),
                    "pages": response_data.get("pages", 1),
                    "currentPage": response_data.get("currentPage", 1),
                    "pageSize": response_data.get("pageSize", 10),
                }

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"The Guardian API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Guardian API request failed: {e}")
            raise Exception(f"Guardian API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Guardian API operations"""

        schemas = {
            "search_content": {
                "description": "Search all Guardian content with advanced filtering",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Search query text",
                        "examples": [
                            "climate change",
                            "artificial intelligence",
                            "brexit",
                        ],
                    },
                    "section": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by section",
                        "examples": [
                            "politics",
                            "technology",
                            "business",
                            "world",
                            "sport",
                        ],
                    },
                    "tag": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by tag",
                        "examples": [
                            "technology/artificial-intelligence",
                            "world/climate-change",
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
                    "order_by": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order",
                        "examples": ["newest", "oldest", "relevance"],
                        "default": "newest",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max 200)",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                    "show_fields": {
                        "type": "string",
                        "required": False,
                        "description": "Comma-separated fields to include",
                        "examples": [
                            "headline,body,thumbnail",
                            "all",
                            "trailText,byline",
                        ],
                    },
                    "show_tags": {
                        "type": "string",
                        "required": False,
                        "description": "Comma-separated tag types",
                        "examples": ["keyword,contributor", "all"],
                    },
                },
            },
            "get_item": {
                "description": "Get a specific Guardian content item by ID",
                "parameters": {
                    "item_id": {
                        "type": "string",
                        "required": True,
                        "description": "The Guardian content ID",
                        "examples": [
                            "technology/2024/jan/01/article-slug",
                            "politics/2024/dec/15/news-story",
                        ],
                    },
                    "show_fields": {
                        "type": "string",
                        "required": False,
                        "description": "Comma-separated fields to include",
                        "examples": ["headline,body,thumbnail", "all"],
                    },
                },
            },
            "get_tags": {
                "description": "Get all tags or filter by type",
                "parameters": {
                    "tag_type": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by tag type",
                        "examples": [
                            "keyword",
                            "contributor",
                            "series",
                            "blog",
                            "tone",
                        ],
                    },
                    "section": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by section",
                        "examples": ["politics", "technology"],
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page",
                        "examples": [10, 50, 100],
                        "default": 10,
                    },
                },
            },
            "get_sections": {
                "description": "Get all Guardian sections",
                "parameters": {},
            },
            "search_tags": {
                "description": "Search for tags by query",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Search query",
                        "examples": ["climate", "technology", "politics"],
                    },
                    "tag_type": {
                        "type": "string",
                        "required": False,
                        "description": "Filter by tag type",
                        "examples": ["keyword", "contributor"],
                    },
                },
            },
            "get_edition": {
                "description": "Get content for a specific Guardian edition",
                "parameters": {
                    "edition": {
                        "type": "string",
                        "required": False,
                        "description": "Edition code",
                        "examples": ["uk", "us", "au", "international"],
                        "default": "uk",
                    },
                    "page_size": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results",
                        "examples": [10, 20, 50],
                        "default": 10,
                    },
                },
            },
        }

        return schemas.get(operation)


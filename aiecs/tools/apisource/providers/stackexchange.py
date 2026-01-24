"""
Stack Exchange API Provider

Provides access to Stack Exchange network of Q&A sites including Stack Overflow,
Server Fault, Super User, and many other community sites.

API Documentation: https://api.stackexchange.com/docs
No API key required for basic usage - API key increases rate limits
Rate Limit: 300 requests/day without key, 10,000 requests/day with key

IMPORTANT - Stack Exchange API Rules:
1. Rate Limiting: Respect the backoff field in responses
2. Compression: All responses are gzip compressed
3. Site Parameter: Required for most endpoints (e.g., 'stackoverflow', 'serverfault')
4. Throttling: Max 30 requests per second per IP
5. Attribution: Must provide attribution when displaying content
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

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


class StackExchangeProvider(BaseAPIProvider):
    """
    Stack Exchange API provider for Q&A content across the Stack Exchange network.

    Provides access to:
    - Question search and retrieval
    - Answer retrieval
    - User information
    - Tag information
    - Site information
    """

    BASE_URL = "https://api.stackexchange.com/2.3"

    @property
    def name(self) -> str:
        return "stackexchange"

    @property
    def description(self) -> str:
        return "Stack Exchange API for Q&A content from Stack Overflow and other Stack Exchange sites"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_questions",
            "get_question",
            "get_answers",
            "search_users",
            "get_tags",
            "get_sites",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Stack Exchange operations"""

        if operation == "search_questions":
            if "site" not in params:
                return False, "Missing required parameter: site"

        elif operation == "get_question":
            if "question_id" not in params:
                return False, "Missing required parameter: question_id"
            if "site" not in params:
                return False, "Missing required parameter: site"

        elif operation == "get_answers":
            if "question_id" not in params:
                return False, "Missing required parameter: question_id"
            if "site" not in params:
                return False, "Missing required parameter: site"

        elif operation == "search_users":
            if "site" not in params:
                return False, "Missing required parameter: site"

        elif operation == "get_tags":
            if "site" not in params:
                return False, "Missing required parameter: site"

        elif operation == "get_sites":
            # No required parameters for get_sites
            pass

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_questions",
        description="Search for questions on a Stack Exchange site",
    )
    def search_questions(
        self,
        site: str,
        q: Optional[str] = None,
        tagged: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        pagesize: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for questions on a Stack Exchange site.

        Args:
            site: Site parameter (e.g., 'stackoverflow', 'serverfault', 'superuser')
            q: Search query string
            tagged: Semicolon-delimited list of tags (e.g., 'python;django')
            sort: Sort by 'activity', 'votes', 'creation', or 'relevance'
            order: Sort order 'desc' or 'asc'
            page: Page number for pagination (default: 1)
            pagesize: Number of results per page (default: 30, max: 100)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"site": site}
        if q:
            params["q"] = q
        if tagged:
            params["tagged"] = tagged
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if page:
            params["page"] = page
        if pagesize:
            params["pagesize"] = pagesize

        return self.execute("search_questions", params)

    @expose_operation(
        operation_name="get_question",
        description="Get a specific question by ID",
    )
    def get_question(
        self,
        question_id: int,
        site: str,
        filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific question by its ID.

        Args:
            question_id: Question ID
            site: Site parameter (e.g., 'stackoverflow')
            filter: Custom filter to control response fields

        Returns:
            Dictionary containing question information
        """
        params: Dict[str, Any] = {"question_id": question_id, "site": site}
        if filter:
            params["filter"] = filter

        return self.execute("get_question", params)

    @expose_operation(
        operation_name="get_answers",
        description="Get answers for a specific question",
    )
    def get_answers(
        self,
        question_id: int,
        site: str,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        pagesize: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get answers for a specific question.

        Args:
            question_id: Question ID
            site: Site parameter (e.g., 'stackoverflow')
            sort: Sort by 'activity', 'votes', or 'creation'
            order: Sort order 'desc' or 'asc'
            page: Page number for pagination
            pagesize: Number of results per page (max: 100)

        Returns:
            Dictionary containing answers
        """
        params: Dict[str, Any] = {"question_id": question_id, "site": site}
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if page:
            params["page"] = page
        if pagesize:
            params["pagesize"] = pagesize

        return self.execute("get_answers", params)

    @expose_operation(
        operation_name="search_users",
        description="Search for users on a Stack Exchange site",
    )
    def search_users(
        self,
        site: str,
        inname: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        pagesize: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for users on a Stack Exchange site.

        Args:
            site: Site parameter (e.g., 'stackoverflow')
            inname: Search string for user name
            sort: Sort by 'reputation', 'creation', 'name', or 'modified'
            order: Sort order 'desc' or 'asc'
            page: Page number for pagination
            pagesize: Number of results per page (max: 100)

        Returns:
            Dictionary containing user search results
        """
        params: Dict[str, Any] = {"site": site}
        if inname:
            params["inname"] = inname
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if page:
            params["page"] = page
        if pagesize:
            params["pagesize"] = pagesize

        return self.execute("search_users", params)

    @expose_operation(
        operation_name="get_tags",
        description="Get tags on a Stack Exchange site",
    )
    def get_tags(
        self,
        site: str,
        inname: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        page: Optional[int] = None,
        pagesize: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get tags on a Stack Exchange site.

        Args:
            site: Site parameter (e.g., 'stackoverflow')
            inname: Filter tags by name substring
            sort: Sort by 'popular', 'activity', or 'name'
            order: Sort order 'desc' or 'asc'
            page: Page number for pagination
            pagesize: Number of results per page (max: 100)

        Returns:
            Dictionary containing tags
        """
        params: Dict[str, Any] = {"site": site}
        if inname:
            params["inname"] = inname
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order
        if page:
            params["page"] = page
        if pagesize:
            params["pagesize"] = pagesize

        return self.execute("get_tags", params)

    @expose_operation(
        operation_name="get_sites",
        description="Get all sites in the Stack Exchange network",
    )
    def get_sites(
        self,
        page: Optional[int] = None,
        pagesize: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get all sites in the Stack Exchange network.

        Args:
            page: Page number for pagination
            pagesize: Number of results per page (max: 100)

        Returns:
            Dictionary containing site information
        """
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if pagesize:
            params["pagesize"] = pagesize

        return self.execute("get_sites", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Stack Exchange API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Stack Exchange provider")

        timeout = self.config.get("timeout", 30)
        api_key = self.config.get("api_key")

        # Build URL and query parameters based on operation
        query_params: Dict[str, Any] = {}

        # Add API key if available (increases rate limits)
        if api_key:
            query_params["key"] = api_key

        if operation == "search_questions":
            endpoint = f"{self.BASE_URL}/search"
            # Copy all params to query_params
            for key in ["site", "q", "tagged", "sort", "order", "page", "pagesize"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_question":
            question_id = params["question_id"]
            endpoint = f"{self.BASE_URL}/questions/{question_id}"
            query_params["site"] = params["site"]
            if "filter" in params:
                query_params["filter"] = params["filter"]

        elif operation == "get_answers":
            question_id = params["question_id"]
            endpoint = f"{self.BASE_URL}/questions/{question_id}/answers"
            query_params["site"] = params["site"]
            for key in ["sort", "order", "page", "pagesize"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "search_users":
            endpoint = f"{self.BASE_URL}/users"
            for key in ["site", "inname", "sort", "order", "page", "pagesize"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_tags":
            endpoint = f"{self.BASE_URL}/tags"
            for key in ["site", "inname", "sort", "order", "page", "pagesize"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_sites":
            endpoint = f"{self.BASE_URL}/sites"
            for key in ["page", "pagesize"]:
                if key in params:
                    query_params[key] = params[key]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(
                endpoint,
                params=query_params,
                timeout=timeout,
                # Stack Exchange API returns gzip compressed responses
                headers={"Accept-Encoding": "gzip"}
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Check for API errors
            if "error_id" in data:
                error_msg = data.get("error_message", "Unknown error")
                raise Exception(f"Stack Exchange API error: {error_msg}")

            # Extract items from response wrapper
            items = data.get("items", [])

            # For single item operations, return just the item
            if operation == "get_question":
                result_data = items[0] if items else {}
            else:
                result_data = items

            # Format response with metadata
            response_dict = self._format_response(
                operation=operation,
                data=result_data,
                source=f"Stack Exchange API - {endpoint}",
            )

            # Add pagination metadata if available
            if "metadata" not in response_dict:
                response_dict["metadata"] = {}

            if "has_more" in data:
                response_dict["metadata"]["has_more"] = data["has_more"]
            if "quota_remaining" in data:
                response_dict["metadata"]["quota_remaining"] = data["quota_remaining"]
            if "quota_max" in data:
                response_dict["metadata"]["quota_max"] = data["quota_max"]

            return response_dict

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Stack Exchange API request failed: {e}")
            raise Exception(f"Stack Exchange API request failed: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Failed to parse Stack Exchange API response: {e}")
            raise Exception(f"Failed to parse Stack Exchange API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_questions": {
                "type": "object",
                "properties": {
                    "site": {
                        "type": "string",
                        "description": "Site parameter (e.g., 'stackoverflow', 'serverfault', 'superuser')",
                    },
                    "q": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "tagged": {
                        "type": "string",
                        "description": "Semicolon-delimited list of tags (e.g., 'python;django')",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by field",
                        "enum": ["activity", "votes", "creation", "relevance"],
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["desc", "asc"],
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "minimum": 1,
                    },
                    "pagesize": {
                        "type": "integer",
                        "description": "Number of results per page (default: 30, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["site"],
            },
            "get_question": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "integer",
                        "description": "Question ID",
                    },
                    "site": {
                        "type": "string",
                        "description": "Site parameter (e.g., 'stackoverflow')",
                    },
                    "filter": {
                        "type": "string",
                        "description": "Custom filter to control response fields",
                    },
                },
                "required": ["question_id", "site"],
            },
            "get_answers": {
                "type": "object",
                "properties": {
                    "question_id": {
                        "type": "integer",
                        "description": "Question ID",
                    },
                    "site": {
                        "type": "string",
                        "description": "Site parameter (e.g., 'stackoverflow')",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by field",
                        "enum": ["activity", "votes", "creation"],
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["desc", "asc"],
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "minimum": 1,
                    },
                    "pagesize": {
                        "type": "integer",
                        "description": "Number of results per page (max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["question_id", "site"],
            },
            "search_users": {
                "type": "object",
                "properties": {
                    "site": {
                        "type": "string",
                        "description": "Site parameter (e.g., 'stackoverflow')",
                    },
                    "inname": {
                        "type": "string",
                        "description": "Search string for user name",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by field",
                        "enum": ["reputation", "creation", "name", "modified"],
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["desc", "asc"],
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "minimum": 1,
                    },
                    "pagesize": {
                        "type": "integer",
                        "description": "Number of results per page (max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["site"],
            },
            "get_tags": {
                "type": "object",
                "properties": {
                    "site": {
                        "type": "string",
                        "description": "Site parameter (e.g., 'stackoverflow')",
                    },
                    "inname": {
                        "type": "string",
                        "description": "Filter tags by name substring",
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by field",
                        "enum": ["popular", "activity", "name"],
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["desc", "asc"],
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "minimum": 1,
                    },
                    "pagesize": {
                        "type": "integer",
                        "description": "Number of results per page (max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["site"],
            },
            "get_sites": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination",
                        "minimum": 1,
                    },
                    "pagesize": {
                        "type": "integer",
                        "description": "Number of results per page (max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": [],
            },
        }

        return schemas.get(operation)


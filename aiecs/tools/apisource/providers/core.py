"""
CORE API Provider

Provides access to CORE's extensive repository of open access research papers.
Supports paper search, metadata retrieval, and full-text access.

API Documentation: https://api.core.ac.uk/docs/v3
API Key: Required - Get from https://core.ac.uk/services/api
Rate Limit: Varies by plan (free tier: 10 requests per minute)

IMPORTANT - CORE API Rules:
1. Rate Limiting: Respect rate limits based on your API plan
2. API Key: Required in request headers as 'Authorization: Bearer YOUR_API_KEY'
3. Max Results: Limited to 100 results per request, use pagination for more
4. Endpoints: Use v3 API endpoints for best performance and features
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


class COREProvider(BaseAPIProvider):
    """
    CORE API provider for open access research papers.

    Provides access to:
    - Paper search by query, title, author, DOI
    - Paper metadata retrieval by CORE ID
    - Full-text access to open access papers
    - Journal and repository information
    - Citation data and recommendations
    """

    BASE_URL = "https://api.core.ac.uk/v3"

    @property
    def name(self) -> str:
        return "core"

    @property
    def description(self) -> str:
        return "CORE API for open access research papers, metadata, and full-text content"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_works",
            "get_work",
            "search_by_doi",
            "search_by_title",
            "get_work_fulltext",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for CORE operations"""

        if operation == "search_works":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_work":
            if "work_id" not in params:
                return False, "Missing required parameter: work_id"

        elif operation == "search_by_doi":
            if "doi" not in params:
                return False, "Missing required parameter: doi"

        elif operation == "search_by_title":
            if "title" not in params:
                return False, "Missing required parameter: title"

        elif operation == "get_work_fulltext":
            if "work_id" not in params:
                return False, "Missing required parameter: work_id"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_works",
        description="Search for research papers by query string",
    )
    def search_works(
        self,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers on CORE.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default: 10, max: 100)
            offset: Starting offset for pagination (default: 0)

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if limit:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        return self.execute("search_works", params)

    @expose_operation(
        operation_name="get_work",
        description="Get paper details by CORE work ID",
    )
    def get_work(self, work_id: str) -> Dict[str, Any]:
        """
        Get paper details by CORE work ID.

        Args:
            work_id: CORE work identifier

        Returns:
            Dictionary containing paper information
        """
        return self.execute("get_work", {"work_id": work_id})

    @expose_operation(
        operation_name="search_by_doi",
        description="Search for papers by DOI",
    )
    def search_by_doi(self, doi: str) -> Dict[str, Any]:
        """
        Search for papers by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Dictionary containing paper information
        """
        return self.execute("search_by_doi", {"doi": doi})

    @expose_operation(
        operation_name="search_by_title",
        description="Search for papers by title",
    )
    def search_by_title(
        self,
        title: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for papers by title.

        Args:
            title: Paper title to search for
            limit: Maximum number of results to return (default: 10)

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"title": title}
        if limit:
            params["limit"] = limit

        return self.execute("search_by_title", params)

    @expose_operation(
        operation_name="get_work_fulltext",
        description="Get full-text content of a paper",
    )
    def get_work_fulltext(self, work_id: str) -> Dict[str, Any]:
        """
        Get full-text content of a paper.

        Args:
            work_id: CORE work identifier

        Returns:
            Dictionary containing full-text content
        """
        return self.execute("get_work_fulltext", {"work_id": work_id})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from CORE API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for CORE provider")

        # Get API key from config
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "CORE API key is required. Set it in config or CORE_API_KEY environment variable. "
                "Get your API key from https://core.ac.uk/services/api"
            )

        timeout = self.config.get("timeout", 30)

        # Set headers with API key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        # Build URL and query parameters based on operation
        url = ""
        query_params: Dict[str, Any] = {}
        method = "GET"

        if operation == "search_works":
            # Search endpoint
            url = f"{self.BASE_URL}/search/works"
            query_params["q"] = params["query"]
            query_params["limit"] = params.get("limit", 10)
            if query_params["limit"] > 100:
                self.logger.warning(f"limit {query_params['limit']} exceeds CORE max of 100, capping at 100")
                query_params["limit"] = 100
            query_params["offset"] = params.get("offset", 0)

        elif operation == "get_work":
            # Get specific work by ID
            work_id = params["work_id"]
            url = f"{self.BASE_URL}/works/{work_id}"

        elif operation == "search_by_doi":
            # Search by DOI
            doi = params["doi"]
            url = f"{self.BASE_URL}/search/works"
            query_params["q"] = f'doi:"{doi}"'
            query_params["limit"] = 10

        elif operation == "search_by_title":
            # Search by title
            title = params["title"]
            url = f"{self.BASE_URL}/search/works"
            query_params["q"] = f'title:"{title}"'
            query_params["limit"] = params.get("limit", 10)
            if query_params["limit"] > 100:
                self.logger.warning(f"limit {query_params['limit']} exceeds CORE max of 100, capping at 100")
                query_params["limit"] = 100

        elif operation == "get_work_fulltext":
            # Get full-text content
            work_id = params["work_id"]
            url = f"{self.BASE_URL}/works/{work_id}/fulltext"

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.request(
                method,
                url,
                params=query_params if method == "GET" else None,
                json=query_params if method == "POST" else None,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract data based on operation
            if operation == "search_works" or operation == "search_by_doi" or operation == "search_by_title":
                # Search returns {'totalHits': N, 'results': [...]}
                result_data = data.get("results", [])
                total = data.get("totalHits", len(result_data))
            elif operation == "get_work_fulltext":
                # Full-text returns text content
                result_data = data
                total = None
            else:
                # Single item endpoints return the object directly
                result_data = data
                total = None

            # Format response
            response_dict = self._format_response(
                operation=operation,
                data=result_data,
                source=f"CORE API - {url}",
            )

            # Add total to metadata if available
            if total is not None:
                if "metadata" not in response_dict:
                    response_dict["metadata"] = {}
                response_dict["metadata"]["total_results"] = total

            return response_dict

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.logger.error("CORE API authentication failed - invalid API key")
                raise Exception("Authentication failed. Please check your CORE API key.")
            elif e.response.status_code == 404:
                self.logger.error(f"CORE resource not found: {url}")
                raise Exception(f"Resource not found: {str(e)}")
            elif e.response.status_code == 429:
                self.logger.error("CORE rate limit exceeded")
                raise Exception("Rate limit exceeded. Please wait before making more requests.")
            else:
                self.logger.error(f"CORE API HTTP error: {e}")
                raise Exception(f"API HTTP error: {str(e)}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"CORE API request failed: {e}")
            raise Exception(f"API request failed: {str(e)}")
        except ValueError as e:
            self.logger.error(f"Failed to parse CORE API response: {e}")
            raise Exception(f"Failed to parse API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_works": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (supports field-specific queries like 'title:machine learning')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting offset for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["query"],
            },
            "get_work": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "string",
                        "description": "CORE work identifier",
                    },
                },
                "required": ["work_id"],
            },
            "search_by_doi": {
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "Digital Object Identifier (e.g., '10.1000/xyz123')",
                    },
                },
                "required": ["doi"],
            },
            "search_by_title": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Paper title to search for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["title"],
            },
            "get_work_fulltext": {
                "type": "object",
                "properties": {
                    "work_id": {
                        "type": "string",
                        "description": "CORE work identifier",
                    },
                },
                "required": ["work_id"],
            },
        }

        return schemas.get(operation)


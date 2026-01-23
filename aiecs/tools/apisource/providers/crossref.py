"""
CrossRef API Provider

Provides access to CrossRef's extensive database of scholarly metadata.
Supports DOI lookup, work search, journal queries, and funder information.

API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
No API key required - completely free and open
Polite pool available with email registration for better rate limits

IMPORTANT - CrossRef API Rules:
1. Rate Limiting: Use polite pool (include mailto parameter) for better rate limits
2. User-Agent: Set a descriptive User-Agent header
3. Caching: Cache responses when possible to reduce server load
4. Attribution: Acknowledge CrossRef when using the data
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


class CrossRefProvider(BaseAPIProvider):
    """
    CrossRef API provider for scholarly metadata and DOI resolution.

    Provides access to:
    - DOI metadata lookup
    - Work search by title, author, subject
    - Journal information and works
    - Funder information
    - Member organization data
    """

    BASE_URL = "https://api.crossref.org"

    @property
    def name(self) -> str:
        return "crossref"

    @property
    def description(self) -> str:
        return "CrossRef API for scholarly metadata, DOI resolution, and citation data"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_work_by_doi",
            "search_works",
            "get_journal_works",
            "search_funders",
            "get_funder_works",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for CrossRef operations"""

        if operation == "get_work_by_doi":
            if "doi" not in params:
                return False, "Missing required parameter: doi"

        elif operation == "search_works":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_journal_works":
            if "issn" not in params:
                return False, "Missing required parameter: issn"

        elif operation == "search_funders":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_funder_works":
            if "funder_id" not in params:
                return False, "Missing required parameter: funder_id"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_work_by_doi",
        description="Get metadata for a work by its DOI",
    )
    def get_work_by_doi(self, doi: str) -> Dict[str, Any]:
        """
        Get work metadata by DOI.

        Args:
            doi: Digital Object Identifier (e.g., '10.1128/mbio.01735-25')

        Returns:
            Dictionary containing work metadata
        """
        return self.execute("get_work_by_doi", {"doi": doi})

    @expose_operation(
        operation_name="search_works",
        description="Search for works by query string",
    )
    def search_works(
        self,
        query: str,
        rows: Optional[int] = None,
        offset: Optional[int] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for works in CrossRef.

        Args:
            query: Search query string
            rows: Number of results to return (default: 20, max: 1000)
            offset: Starting index for pagination (default: 0)
            sort: Sort field - 'relevance', 'score', 'updated', 'deposited', 'indexed', 'published'
            order: Sort order - 'asc' or 'desc'

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if rows:
            params["rows"] = rows
        if offset is not None:
            params["offset"] = offset
        if sort:
            params["sort"] = sort
        if order:
            params["order"] = order

        return self.execute("search_works", params)

    @expose_operation(
        operation_name="get_journal_works",
        description="Get works published in a specific journal by ISSN",
    )
    def get_journal_works(
        self,
        issn: str,
        rows: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get works from a specific journal.

        Args:
            issn: Journal ISSN (e.g., '0028-0836' for Nature)
            rows: Number of results to return (default: 20)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing journal works
        """
        params: Dict[str, Any] = {"issn": issn}
        if rows:
            params["rows"] = rows
        if offset is not None:
            params["offset"] = offset

        return self.execute("get_journal_works", params)

    @expose_operation(
        operation_name="search_funders",
        description="Search for funders in the Open Funder Registry",
    )
    def search_funders(
        self,
        query: str,
        rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for funders.

        Args:
            query: Search query string
            rows: Number of results to return (default: 20)

        Returns:
            Dictionary containing funder search results
        """
        params: Dict[str, Any] = {"query": query}
        if rows:
            params["rows"] = rows

        return self.execute("search_funders", params)

    @expose_operation(
        operation_name="get_funder_works",
        description="Get works associated with a specific funder",
    )
    def get_funder_works(
        self,
        funder_id: str,
        rows: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get works funded by a specific funder.

        Args:
            funder_id: Funder ID from Open Funder Registry (e.g., '100000001' for NSF)
            rows: Number of results to return (default: 20)
            offset: Starting index for pagination (default: 0)

        Returns:
            Dictionary containing works funded by the funder
        """
        params: Dict[str, Any] = {"funder_id": funder_id}
        if rows:
            params["rows"] = rows
        if offset is not None:
            params["offset"] = offset

        return self.execute("get_funder_works", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from CrossRef API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for CrossRef provider")

        timeout = self.config.get("timeout", 30)

        # Set User-Agent header as required by CrossRef API etiquette
        # Include mailto for polite pool access (better rate limits)
        user_agent = self.config.get(
            "user_agent",
            "AIECS-APISource/2.0 (https://github.com/your-org/aiecs; mailto:iretbl@gmail.com)"
        )
        headers = {
            "User-Agent": user_agent,
        }

        # Build request URL and parameters based on operation
        try:
            if operation == "get_work_by_doi":
                # Get specific work by DOI
                doi = params["doi"]
                url = f"{self.BASE_URL}/works/{doi}"
                query_params: Dict[str, Any] = {}

                # Add mailto for polite pool
                mailto = self.config.get("mailto", "iretbl@gmail.com")
                if mailto:
                    query_params["mailto"] = mailto

                response = requests.get(
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Extract work from response
                data = response.json()
                work = data.get("message", {})

                return self._format_response(
                    operation=operation,
                    data=work,
                    source=f"CrossRef API - {self.BASE_URL}",
                )

            elif operation == "search_works":
                # Search for works
                url = f"{self.BASE_URL}/works"
                query_params = {
                    "query": params["query"],
                    "rows": params.get("rows", 20),
                    "offset": params.get("offset", 0),
                }

                # Add optional parameters
                if "sort" in params:
                    query_params["sort"] = params["sort"]
                if "order" in params:
                    query_params["order"] = params["order"]

                # Add mailto for polite pool
                mailto = self.config.get("mailto", "iretbl@gmail.com")
                if mailto:
                    query_params["mailto"] = mailto

                response = requests.get(
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Extract works from response
                data = response.json()
                message = data.get("message", {})
                works = message.get("items", [])
                total_results = message.get("total-results", 0)

                # Format response with search metadata
                response_dict = self._format_response(
                    operation=operation,
                    data=works,
                    source=f"CrossRef API - {self.BASE_URL}",
                )

                # Add search-specific metadata
                response_dict["metadata"]["search_info"] = {
                    "total_results": total_results,
                    "returned_results": len(works),
                    "offset": query_params["offset"],
                }

                return response_dict

            elif operation == "get_journal_works":
                # Get works from a specific journal
                issn = params["issn"]
                url = f"{self.BASE_URL}/journals/{issn}/works"
                query_params = {
                    "rows": params.get("rows", 20),
                    "offset": params.get("offset", 0),
                }

                # Add mailto for polite pool
                mailto = self.config.get("mailto", "iretbl@gmail.com")
                if mailto:
                    query_params["mailto"] = mailto

                response = requests.get(
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Extract works from response
                data = response.json()
                message = data.get("message", {})
                works = message.get("items", [])
                total_results = message.get("total-results", 0)

                # Format response
                response_dict = self._format_response(
                    operation=operation,
                    data=works,
                    source=f"CrossRef API - {self.BASE_URL}",
                )

                # Add metadata
                response_dict["metadata"]["journal_info"] = {
                    "issn": issn,
                    "total_results": total_results,
                    "returned_results": len(works),
                }

                return response_dict

            elif operation == "search_funders":
                # Search for funders
                url = f"{self.BASE_URL}/funders"
                query_params = {
                    "query": params["query"],
                    "rows": params.get("rows", 20),
                }

                # Add mailto for polite pool
                mailto = self.config.get("mailto", "iretbl@gmail.com")
                if mailto:
                    query_params["mailto"] = mailto

                response = requests.get(
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Extract funders from response
                data = response.json()
                message = data.get("message", {})
                funders = message.get("items", [])
                total_results = message.get("total-results", 0)

                # Format response
                response_dict = self._format_response(
                    operation=operation,
                    data=funders,
                    source=f"CrossRef API - {self.BASE_URL}",
                )

                # Add search metadata
                response_dict["metadata"]["search_info"] = {
                    "total_results": total_results,
                    "returned_results": len(funders),
                }

                return response_dict

            elif operation == "get_funder_works":
                # Get works funded by a specific funder
                funder_id = params["funder_id"]
                url = f"{self.BASE_URL}/funders/{funder_id}/works"
                query_params = {
                    "rows": params.get("rows", 20),
                    "offset": params.get("offset", 0),
                }

                # Add mailto for polite pool
                mailto = self.config.get("mailto", "iretbl@gmail.com")
                if mailto:
                    query_params["mailto"] = mailto

                response = requests.get(
                    url,
                    params=query_params,
                    headers=headers,
                    timeout=timeout
                )
                response.raise_for_status()

                # Extract works from response
                data = response.json()
                message = data.get("message", {})
                works = message.get("items", [])
                total_results = message.get("total-results", 0)

                # Format response
                response_dict = self._format_response(
                    operation=operation,
                    data=works,
                    source=f"CrossRef API - {self.BASE_URL}",
                )

                # Add metadata
                response_dict["metadata"]["funder_info"] = {
                    "funder_id": funder_id,
                    "total_results": total_results,
                    "returned_results": len(works),
                }

                return response_dict

            else:
                raise ValueError(f"Unknown operation: {operation}")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"CrossRef API request failed: {e}")
            raise Exception(f"CrossRef API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "get_work_by_doi": {
                "type": "object",
                "properties": {
                    "doi": {
                        "type": "string",
                        "description": "Digital Object Identifier (e.g., '10.1128/mbio.01735-25')",
                    },
                },
                "required": ["doi"],
            },
            "search_works": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results to return (default: 20, max: 1000)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort field",
                        "enum": ["relevance", "score", "updated", "deposited", "indexed", "published"],
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order",
                        "enum": ["asc", "desc"],
                    },
                },
                "required": ["query"],
            },
            "get_journal_works": {
                "type": "object",
                "properties": {
                    "issn": {
                        "type": "string",
                        "description": "Journal ISSN (e.g., '0028-0836' for Nature)",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results to return (default: 20)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["issn"],
            },
            "search_funders": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results to return (default: 20)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                },
                "required": ["query"],
            },
            "get_funder_works": {
                "type": "object",
                "properties": {
                    "funder_id": {
                        "type": "string",
                        "description": "Funder ID from Open Funder Registry (e.g., '100000001' for NSF)",
                    },
                    "rows": {
                        "type": "integer",
                        "description": "Number of results to return (default: 20)",
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Starting index for pagination (default: 0)",
                        "minimum": 0,
                    },
                },
                "required": ["funder_id"],
            },
        }

        return schemas.get(operation)


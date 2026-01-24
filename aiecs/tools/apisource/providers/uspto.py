"""
USPTO Patent API Provider

Provides access to the USPTO PatentsView API for patent search and retrieval.
Supports patent search, inventor lookup, assignee information, and detailed patent data.

API Documentation: https://search.patentsview.org/docs/
API Key: Required - Request at https://search.patentsview.org/

IMPORTANT - USPTO API Rules:
1. Rate Limiting: Respect API rate limits
2. API Key: Required for all requests
3. Query Format: Uses JSON query syntax with field-based filtering
4. Max Results: Limited to 10,000 results per query
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


class USPTOProvider(BaseAPIProvider):
    """
    USPTO PatentsView API provider for patent search and data retrieval.

    Provides access to:
    - Patent search by keyword, title, abstract, inventor, assignee
    - Patent metadata retrieval by patent ID
    - Inventor information and search
    - Assignee/organization information
    - Patent classification data (CPC, IPC, USPC)
    """

    BASE_URL = "https://search.patentsview.org/api/v1"

    @property
    def name(self) -> str:
        return "uspto"

    @property
    def description(self) -> str:
        return "USPTO PatentsView API for patent search, inventor lookup, and patent metadata"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_patents",
            "get_patent",
            "search_by_inventor",
            "search_by_assignee",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for USPTO operations"""

        if operation == "search_patents":
            if "query" not in params:
                return False, "Missing required parameter: query"

        elif operation == "get_patent":
            if "patent_id" not in params:
                return False, "Missing required parameter: patent_id"

        elif operation == "search_by_inventor":
            if "inventor_name" not in params:
                return False, "Missing required parameter: inventor_name"

        elif operation == "search_by_assignee":
            if "assignee_name" not in params:
                return False, "Missing required parameter: assignee_name"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_patents",
        description="Search for patents by keyword query (searches title, abstract, claims)",
    )
    def search_patents(
        self,
        query: str,
        max_results: Optional[int] = None,
        sort_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search for patents on USPTO PatentsView.

        Args:
            query: Search query string (searches title, abstract, claims)
            max_results: Maximum number of results to return (default: 25, max: 10000)
            sort_by: Sort by field (e.g., 'patent_date', 'patent_id')

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"query": query}
        if max_results:
            params["max_results"] = max_results
        if sort_by:
            params["sort_by"] = sort_by

        return self.execute("search_patents", params)

    @expose_operation(
        operation_name="get_patent",
        description="Get detailed patent information by patent ID",
    )
    def get_patent(self, patent_id: str) -> Dict[str, Any]:
        """
        Get patent details by patent ID.

        Args:
            patent_id: USPTO patent number (e.g., '10881042')

        Returns:
            Dictionary containing patent information
        """
        return self.execute("get_patent", {"patent_id": patent_id})

    @expose_operation(
        operation_name="search_by_inventor",
        description="Search for patents by inventor name",
    )
    def search_by_inventor(
        self,
        inventor_name: str,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for patents by inventor name.

        Args:
            inventor_name: Inventor name to search for
            max_results: Maximum number of results to return (default: 25)

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"inventor_name": inventor_name}
        if max_results:
            params["max_results"] = max_results

        return self.execute("search_by_inventor", params)

    @expose_operation(
        operation_name="search_by_assignee",
        description="Search for patents by assignee/organization name",
    )
    def search_by_assignee(
        self,
        assignee_name: str,
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for patents by assignee/organization.

        Args:
            assignee_name: Assignee/organization name to search for
            max_results: Maximum number of results to return (default: 25)

        Returns:
            Dictionary containing search results
        """
        params: Dict[str, Any] = {"assignee_name": assignee_name}
        if max_results:
            params["max_results"] = max_results

        return self.execute("search_by_assignee", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from USPTO PatentsView API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for USPTO provider")

        # Get API key
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "USPTO API key is required. Set USPTO_API_KEY environment variable "
                "or provide 'api_key' in config. Request a key at: "
                "https://search.patentsview.org/"
            )

        timeout = self.config.get("timeout", 30)
        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }

        # Build query based on operation
        endpoint = f"{self.BASE_URL}/patent"
        query_body: Dict[str, Any] = {}

        if operation == "search_patents":
            # General keyword search across title, abstract, claims
            query_text = params["query"]
            query_body["q"] = {
                "_or": [
                    {"_text_any": {"patent_title": query_text}},
                    {"_text_any": {"patent_abstract": query_text}},
                ]
            }

            # Fields to return
            query_body["f"] = [
                "patent_id",
                "patent_title",
                "patent_date",
                "patent_abstract",
                "inventors.inventor_name_first",
                "inventors.inventor_name_last",
                "assignees.assignee_organization",
            ]

            # Pagination
            max_results = params.get("max_results", 25)
            if max_results > 10000:
                self.logger.warning(f"max_results {max_results} exceeds USPTO limit of 10000, capping at 10000")
                max_results = 10000
            query_body["o"] = {"per_page": max_results}

            # Sorting
            if "sort_by" in params:
                query_body["s"] = [{params["sort_by"]: "desc"}]

        elif operation == "get_patent":
            # Get specific patent by ID
            patent_id = params["patent_id"]
            query_body["q"] = {"patent_id": patent_id}
            query_body["f"] = [
                "patent_id",
                "patent_title",
                "patent_date",
                "patent_abstract",
                "patent_num_claims",
                "inventors.inventor_name_first",
                "inventors.inventor_name_last",
                "inventors.inventor_city",
                "inventors.inventor_state",
                "inventors.inventor_country",
                "assignees.assignee_organization",
                "assignees.assignee_city",
                "assignees.assignee_state",
                "assignees.assignee_country",
                "cpcs.cpc_section_id",
                "cpcs.cpc_subsection_id",
            ]
            query_body["o"] = {"per_page": 1}

        elif operation == "search_by_inventor":
            # Search by inventor name
            inventor_name = params["inventor_name"]
            # Split name into parts for better matching
            name_parts = inventor_name.split()

            if len(name_parts) >= 2:
                # Assume first part is first name, last part is last name
                query_body["q"] = {
                    "_and": [
                        {"_text_any": {"inventors.inventor_name_first": name_parts[0]}},
                        {"_text_any": {"inventors.inventor_name_last": name_parts[-1]}},
                    ]
                }
            else:
                # Search in both first and last name
                query_body["q"] = {
                    "_or": [
                        {"_text_any": {"inventors.inventor_name_first": inventor_name}},
                        {"_text_any": {"inventors.inventor_name_last": inventor_name}},
                    ]
                }

            query_body["f"] = [
                "patent_id",
                "patent_title",
                "patent_date",
                "inventors.inventor_name_first",
                "inventors.inventor_name_last",
            ]

            max_results = params.get("max_results", 25)
            if max_results > 10000:
                self.logger.warning(f"max_results {max_results} exceeds USPTO limit of 10000, capping at 10000")
                max_results = 10000
            query_body["o"] = {"per_page": max_results}

        elif operation == "search_by_assignee":
            # Search by assignee/organization
            assignee_name = params["assignee_name"]
            query_body["q"] = {
                "_text_any": {"assignees.assignee_organization": assignee_name}
            }

            query_body["f"] = [
                "patent_id",
                "patent_title",
                "patent_date",
                "assignees.assignee_organization",
                "inventors.inventor_name_first",
                "inventors.inventor_name_last",
            ]

            max_results = params.get("max_results", 25)
            if max_results > 10000:
                self.logger.warning(f"max_results {max_results} exceeds USPTO limit of 10000, capping at 10000")
                max_results = 10000
            query_body["o"] = {"per_page": max_results}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.post(
                endpoint,
                json=query_body,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract patents from response
            patents = data.get("patents", [])

            # For single patent lookup, return just the patent
            if operation == "get_patent":
                result_data = patents[0] if patents else {}
            else:
                result_data = patents

            # Format response
            response_dict = self._format_response(
                operation=operation,
                data=result_data,
                source=f"USPTO PatentsView API - {endpoint}",
            )

            # Add total count to metadata if available
            total_count = data.get("total_patent_count")
            if total_count is not None:
                if "metadata" not in response_dict:
                    response_dict["metadata"] = {}
                response_dict["metadata"]["total_results"] = total_count

            return response_dict

        except requests.exceptions.RequestException as e:
            self.logger.error(f"USPTO API request failed: {e}")
            raise Exception(f"USPTO API request failed: {str(e)}")
        except (KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse USPTO API response: {e}")
            raise Exception(f"Failed to parse USPTO API response: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get JSON schema for operation parameters"""

        schemas = {
            "search_patents": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string (searches title, abstract, claims)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 25, max: 10000)",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort by field (e.g., 'patent_date', 'patent_id')",
                    },
                },
                "required": ["query"],
            },
            "get_patent": {
                "type": "object",
                "properties": {
                    "patent_id": {
                        "type": "string",
                        "description": "USPTO patent number (e.g., '10881042')",
                    },
                },
                "required": ["patent_id"],
            },
            "search_by_inventor": {
                "type": "object",
                "properties": {
                    "inventor_name": {
                        "type": "string",
                        "description": "Inventor name to search for (first and/or last name)",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 25, max: 10000)",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                },
                "required": ["inventor_name"],
            },
            "search_by_assignee": {
                "type": "object",
                "properties": {
                    "assignee_name": {
                        "type": "string",
                        "description": "Assignee/organization name to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 25, max: 10000)",
                        "minimum": 1,
                        "maximum": 10000,
                    },
                },
                "required": ["assignee_name"],
            },
        }

        return schemas.get(operation)


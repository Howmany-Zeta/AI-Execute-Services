"""
OpenStates API Provider

Provides access to U.S. state legislative data from OpenStates.org including bills,
legislators, votes, committees, and legislative analysis.

OpenStates provides comprehensive state legislative data through various endpoints
for tracking legislation, state legislators, voting records, and more.

API Documentation: https://docs.openstates.org/api-v3/
Interactive API Docs: https://v3.openstates.org/docs/

API Key Required - Register at: https://openstates.org/accounts/profile/

IMPORTANT - OpenStates API Rules:
1. API Key Required: Must register for a free API key
2. Rate Limiting: Be respectful - implement reasonable delays between requests
3. Attribution: Acknowledge OpenStates.org when using the data
4. Data Freshness: Data is updated regularly from official state sources
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


class OpenStatesProvider(BaseAPIProvider):
    """
    OpenStates API provider for U.S. state legislative data.

    Provides access to:
    - State bills and resolutions
    - State legislators and their information
    - Legislative votes and voting records
    - Committees and committee assignments
    - Legislative sessions and events
    """

    BASE_URL = "https://v3.openstates.org"

    @property
    def name(self) -> str:
        return "openstates"

    @property
    def description(self) -> str:
        return "OpenStates API for comprehensive U.S. state legislative data, bills, legislators, votes, and analysis"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_bills",
            "get_bill",
            "search_people",
            "get_person",
            "list_jurisdictions",
            "get_jurisdiction",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for OpenStates operations"""

        if operation == "search_bills":
            # At least one search parameter is recommended
            if not any(key in params for key in ["jurisdiction", "session", "q", "subject"]):
                return False, "At least one search parameter is recommended (jurisdiction, session, q, or subject)"

        elif operation == "get_bill":
            if "bill_id" not in params:
                return False, "Missing required parameter: bill_id"

        elif operation == "search_people":
            # No required parameters, but at least one filter is recommended
            pass

        elif operation == "get_person":
            if "person_id" not in params:
                return False, "Missing required parameter: person_id"

        elif operation == "list_jurisdictions":
            # No required parameters
            pass

        elif operation == "get_jurisdiction":
            if "jurisdiction_id" not in params:
                return False, "Missing required parameter: jurisdiction_id"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_bills",
        description="Search for state bills and resolutions with advanced filtering",
    )
    def search_bills(
        self,
        jurisdiction: Optional[str] = None,
        session: Optional[str] = None,
        q: Optional[str] = None,
        subject: Optional[str] = None,
        classification: Optional[str] = None,
        updated_since: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for state bills and resolutions.

        Args:
            jurisdiction: State abbreviation (e.g., 'CA', 'NY', 'TX')
            session: Legislative session identifier
            q: Full-text search query
            subject: Subject area filter
            classification: Bill classification (e.g., 'bill', 'resolution')
            updated_since: ISO 8601 datetime to filter by update time
            page: Page number for pagination
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing bill search results
        """
        params: Dict[str, Any] = {}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if session:
            params["session"] = session
        if q:
            params["q"] = q
        if subject:
            params["subject"] = subject
        if classification:
            params["classification"] = classification
        if updated_since:
            params["updated_since"] = updated_since
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        return self.execute("search_bills", params)

    @expose_operation(
        operation_name="get_bill",
        description="Get detailed information about a specific bill by ID",
    )
    def get_bill(self, bill_id: str) -> Dict[str, Any]:
        """
        Get detailed bill information.

        Args:
            bill_id: OpenStates bill ID (e.g., 'ocd-bill/...')

        Returns:
            Dictionary containing detailed bill information
        """
        return self.execute("get_bill", {"bill_id": bill_id})

    @expose_operation(
        operation_name="search_people",
        description="Search for state legislators with filtering options",
    )
    def search_people(
        self,
        jurisdiction: Optional[str] = None,
        name: Optional[str] = None,
        district: Optional[str] = None,
        party: Optional[str] = None,
        current: Optional[bool] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for state legislators.

        Args:
            jurisdiction: State abbreviation (e.g., 'CA', 'NY', 'TX')
            name: Legislator name (partial match)
            district: Legislative district
            party: Political party
            current: Filter to current legislators only
            page: Page number for pagination
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing legislator search results
        """
        params: Dict[str, Any] = {}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction
        if name:
            params["name"] = name
        if district:
            params["district"] = district
        if party:
            params["party"] = party
        if current is not None:
            params["current"] = current
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        return self.execute("search_people", params)

    @expose_operation(
        operation_name="get_person",
        description="Get detailed information about a specific legislator",
    )
    def get_person(self, person_id: str) -> Dict[str, Any]:
        """
        Get detailed legislator information.

        Args:
            person_id: OpenStates person ID (e.g., 'ocd-person/...')

        Returns:
            Dictionary containing detailed legislator information
        """
        return self.execute("get_person", {"person_id": person_id})

    @expose_operation(
        operation_name="list_jurisdictions",
        description="List all available state jurisdictions",
    )
    def list_jurisdictions(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List all available jurisdictions (states).

        Args:
            page: Page number for pagination
            per_page: Results per page (max 100)

        Returns:
            Dictionary containing jurisdiction list
        """
        params: Dict[str, Any] = {}
        if page:
            params["page"] = page
        if per_page:
            params["per_page"] = per_page

        return self.execute("list_jurisdictions", params)

    @expose_operation(
        operation_name="get_jurisdiction",
        description="Get detailed information about a specific jurisdiction",
    )
    def get_jurisdiction(self, jurisdiction_id: str) -> Dict[str, Any]:
        """
        Get detailed jurisdiction information.

        Args:
            jurisdiction_id: Jurisdiction ID (state abbreviation or OCD ID)

        Returns:
            Dictionary containing detailed jurisdiction information
        """
        return self.execute("get_jurisdiction", {"jurisdiction_id": jurisdiction_id})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from OpenStates API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for OpenStates provider")

        # Get API key from config
        api_key = self.config.get("api_key")
        if not api_key:
            raise ValueError("OpenStates API key is required. Register at https://openstates.org/accounts/profile/")

        timeout = self.config.get("timeout", 30)

        # Build headers
        headers = {
            "X-API-Key": api_key,
        }

        # Build endpoint based on operation
        if operation == "search_bills":
            endpoint = f"{self.BASE_URL}/bills"
            query_params = {}

            # Add all search parameters
            for key in ["jurisdiction", "session", "q", "subject", "classification", "updated_since", "page", "per_page"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_bill":
            bill_id = params["bill_id"]
            endpoint = f"{self.BASE_URL}/bills/{bill_id}"
            query_params = {}

        elif operation == "search_people":
            endpoint = f"{self.BASE_URL}/people"
            query_params = {}

            # Add all search parameters
            for key in ["jurisdiction", "name", "district", "party", "current", "page", "per_page"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_person":
            person_id = params["person_id"]
            endpoint = f"{self.BASE_URL}/people/{person_id}"
            query_params = {}

        elif operation == "list_jurisdictions":
            endpoint = f"{self.BASE_URL}/jurisdictions"
            query_params = {}

            # Add pagination parameters
            for key in ["page", "per_page"]:
                if key in params:
                    query_params[key] = params[key]

        elif operation == "get_jurisdiction":
            jurisdiction_id = params["jurisdiction_id"]
            endpoint = f"{self.BASE_URL}/jurisdictions/{jurisdiction_id}"
            query_params = {}

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

            # OpenStates API returns data in 'results' key for list endpoints
            # and direct object for detail endpoints
            if operation in ["search_bills", "search_people", "list_jurisdictions"]:
                # List endpoints return data in 'results' key
                result_data = data.get("results", [])
            else:
                # Detail endpoints return data directly
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"OpenStates API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenStates API request failed: {e}")
            raise Exception(f"OpenStates API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for OpenStates API operations"""

        schemas = {
            "search_bills": {
                "description": "Search for state bills and resolutions with advanced filtering",
                "parameters": {
                    "jurisdiction": {
                        "type": "string",
                        "required": False,
                        "description": "State abbreviation (e.g., 'CA', 'NY', 'TX')",
                        "examples": ["CA", "NY", "TX", "FL"],
                    },
                    "session": {
                        "type": "string",
                        "required": False,
                        "description": "Legislative session identifier",
                        "examples": ["2023", "2024"],
                    },
                    "q": {
                        "type": "string",
                        "required": False,
                        "description": "Full-text search query",
                        "examples": ["education", "healthcare", "budget"],
                    },
                    "subject": {
                        "type": "string",
                        "required": False,
                        "description": "Subject area filter",
                        "examples": ["Education", "Health", "Transportation"],
                    },
                    "classification": {
                        "type": "string",
                        "required": False,
                        "description": "Bill classification",
                        "examples": ["bill", "resolution", "concurrent resolution"],
                    },
                    "updated_since": {
                        "type": "string",
                        "required": False,
                        "description": "ISO 8601 datetime to filter by update time",
                        "examples": ["2024-01-01T00:00:00"],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                        "examples": [1, 2, 3],
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                        "examples": [10, 25, 50, 100],
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Bill search results with pagination info",
                },
            },
            "get_bill": {
                "description": "Get detailed information about a specific bill",
                "parameters": {
                    "bill_id": {
                        "type": "string",
                        "required": True,
                        "description": "OpenStates bill ID",
                        "examples": ["ocd-bill/..."],
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Detailed bill information",
                },
            },
            "search_people": {
                "description": "Search for state legislators with filtering options",
                "parameters": {
                    "jurisdiction": {
                        "type": "string",
                        "required": False,
                        "description": "State abbreviation",
                        "examples": ["CA", "NY", "TX"],
                    },
                    "name": {
                        "type": "string",
                        "required": False,
                        "description": "Legislator name (partial match)",
                        "examples": ["Smith", "Johnson"],
                    },
                    "district": {
                        "type": "string",
                        "required": False,
                        "description": "Legislative district",
                        "examples": ["1", "10", "SD-5"],
                    },
                    "party": {
                        "type": "string",
                        "required": False,
                        "description": "Political party",
                        "examples": ["Democratic", "Republican", "Independent"],
                    },
                    "current": {
                        "type": "boolean",
                        "required": False,
                        "description": "Filter to current legislators only",
                        "examples": [True, False],
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Legislator search results",
                },
            },
            "get_person": {
                "description": "Get detailed information about a specific legislator",
                "parameters": {
                    "person_id": {
                        "type": "string",
                        "required": True,
                        "description": "OpenStates person ID",
                        "examples": ["ocd-person/..."],
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Detailed legislator information",
                },
            },
            "list_jurisdictions": {
                "description": "List all available state jurisdictions",
                "parameters": {
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number for pagination",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Results per page (max 100)",
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "List of jurisdictions",
                },
            },
            "get_jurisdiction": {
                "description": "Get detailed information about a specific jurisdiction",
                "parameters": {
                    "jurisdiction_id": {
                        "type": "string",
                        "required": True,
                        "description": "Jurisdiction ID (state abbreviation or OCD ID)",
                        "examples": ["CA", "NY", "ocd-jurisdiction/..."],
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Detailed jurisdiction information",
                },
            },
        }

        return schemas.get(operation)


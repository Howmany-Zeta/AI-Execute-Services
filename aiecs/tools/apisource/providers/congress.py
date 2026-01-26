"""
Congress.gov API Provider

Provides access to legislative data from the U.S. Congress including bills,
amendments, members, committees, and more.

API Documentation: https://github.com/LibraryOfCongress/api.congress.gov
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


class CongressProvider(BaseAPIProvider):
    """
    Congress.gov API provider for U.S. legislative data.

    Provides access to:
    - Bills and resolutions
    - Amendments
    - Members of Congress
    - Committees
    - Congressional records
    - Nominations
    - Treaties
    """

    BASE_URL = "https://api.congress.gov/v3"

    @property
    def name(self) -> str:
        return "congress"

    @property
    def description(self) -> str:
        return "Congress.gov API for U.S. legislative data including bills, members, and committees"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_bills",
            "get_bill",
            "list_members",
            "get_member",
            "list_committees",
            "get_committee",
            "search_amendments",
            "get_amendment",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Congress API operations"""

        if operation == "search_bills":
            # No required params - can search all bills
            pass

        elif operation == "get_bill":
            if "congress" not in params:
                return False, "Missing required parameter: congress"
            if "bill_type" not in params:
                return False, "Missing required parameter: bill_type"
            if "bill_number" not in params:
                return False, "Missing required parameter: bill_number"

        elif operation == "get_member":
            if "bioguide_id" not in params:
                return False, "Missing required parameter: bioguide_id"

        elif operation == "get_committee":
            if "chamber" not in params:
                return False, "Missing required parameter: chamber"
            if "committee_code" not in params:
                return False, "Missing required parameter: committee_code"

        elif operation == "get_amendment":
            if "congress" not in params:
                return False, "Missing required parameter: congress"
            if "amendment_type" not in params:
                return False, "Missing required parameter: amendment_type"
            if "amendment_number" not in params:
                return False, "Missing required parameter: amendment_number"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_bills",
        description="Search for bills and resolutions in Congress",
    )
    def search_bills(
        self,
        congress: Optional[int] = None,
        bill_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for bills.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress)
            bill_type: Type of bill (hr, s, hjres, sjres, hconres, sconres, hres, sres)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing bill data and metadata
        """
        params: Dict[str, Any] = {}
        if congress:
            params["congress"] = congress
        if bill_type:
            params["bill_type"] = bill_type
        if limit:
            params["limit"] = limit

        return self.execute("search_bills", params)

    @expose_operation(
        operation_name="get_bill",
        description="Get detailed information about a specific bill",
    )
    def get_bill(self, congress: int, bill_type: str, bill_number: int) -> Dict[str, Any]:
        """
        Get bill details.

        Args:
            congress: Congress number (e.g., 118)
            bill_type: Type of bill (hr, s, hjres, sjres, etc.)
            bill_number: Bill number

        Returns:
            Dictionary containing bill details
        """
        params: Dict[str, Any] = {
            "congress": congress,
            "bill_type": bill_type,
            "bill_number": bill_number,
        }

        return self.execute("get_bill", params)

    @expose_operation(
        operation_name="list_members",
        description="List members of Congress",
    )
    def list_members(
        self,
        congress: Optional[int] = None,
        chamber: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List members of Congress.

        Args:
            congress: Congress number (e.g., 118)
            chamber: Chamber (house or senate)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing member data
        """
        params: Dict[str, Any] = {}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        if limit:
            params["limit"] = limit

        return self.execute("list_members", params)

    @expose_operation(
        operation_name="get_member",
        description="Get detailed information about a specific member of Congress",
    )
    def get_member(self, bioguide_id: str) -> Dict[str, Any]:
        """
        Get member details.

        Args:
            bioguide_id: Bioguide ID of the member

        Returns:
            Dictionary containing member details
        """
        params: Dict[str, Any] = {"bioguide_id": bioguide_id}

        return self.execute("get_member", params)

    @expose_operation(
        operation_name="list_committees",
        description="List congressional committees",
    )
    def list_committees(
        self,
        congress: Optional[int] = None,
        chamber: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List committees.

        Args:
            congress: Congress number (e.g., 118)
            chamber: Chamber (house, senate, or joint)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing committee data
        """
        params: Dict[str, Any] = {}
        if congress:
            params["congress"] = congress
        if chamber:
            params["chamber"] = chamber
        if limit:
            params["limit"] = limit

        return self.execute("list_committees", params)

    @expose_operation(
        operation_name="get_committee",
        description="Get detailed information about a specific committee",
    )
    def get_committee(self, chamber: str, committee_code: str) -> Dict[str, Any]:
        """
        Get committee details.

        Args:
            chamber: Chamber (house, senate, or joint)
            committee_code: Committee code

        Returns:
            Dictionary containing committee details
        """
        params: Dict[str, Any] = {
            "chamber": chamber,
            "committee_code": committee_code,
        }

        return self.execute("get_committee", params)

    @expose_operation(
        operation_name="search_amendments",
        description="Search for amendments to bills",
    )
    def search_amendments(
        self,
        congress: Optional[int] = None,
        amendment_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for amendments.

        Args:
            congress: Congress number (e.g., 118)
            amendment_type: Type of amendment (hamdt, samdt)
            limit: Maximum number of results to return

        Returns:
            Dictionary containing amendment data
        """
        params: Dict[str, Any] = {}
        if congress:
            params["congress"] = congress
        if amendment_type:
            params["amendment_type"] = amendment_type
        if limit:
            params["limit"] = limit

        return self.execute("search_amendments", params)

    @expose_operation(
        operation_name="get_amendment",
        description="Get detailed information about a specific amendment",
    )
    def get_amendment(
        self, congress: int, amendment_type: str, amendment_number: int
    ) -> Dict[str, Any]:
        """
        Get amendment details.

        Args:
            congress: Congress number (e.g., 118)
            amendment_type: Type of amendment (hamdt, samdt)
            amendment_number: Amendment number

        Returns:
            Dictionary containing amendment details
        """
        params: Dict[str, Any] = {
            "congress": congress,
            "amendment_type": amendment_type,
            "amendment_number": amendment_number,
        }

        return self.execute("get_amendment", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Congress.gov API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Congress provider")

        # Congress API requires an API key
        api_key = self._get_api_key("CONGRESS_API_KEY")
        if not api_key:
            raise ValueError("CONGRESS_API_KEY is required for Congress.gov API")

        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "search_bills":
            # List bills
            congress = params.get("congress")
            bill_type = params.get("bill_type")

            if congress and bill_type:
                endpoint = f"{self.BASE_URL}/bill/{congress}/{bill_type}"
            elif congress:
                endpoint = f"{self.BASE_URL}/bill/{congress}"
            else:
                endpoint = f"{self.BASE_URL}/bill"

            query_params = {"api_key": api_key, "format": "json"}
            if params.get("limit"):
                query_params["limit"] = params["limit"]

        elif operation == "get_bill":
            # Get specific bill
            congress = params["congress"]
            bill_type = params["bill_type"]
            bill_number = params["bill_number"]
            endpoint = f"{self.BASE_URL}/bill/{congress}/{bill_type}/{bill_number}"

            query_params = {"api_key": api_key, "format": "json"}

        elif operation == "list_members":
            # List members - note: filtering by congress/chamber not supported in list endpoint
            # Use /member endpoint and filter results client-side if needed
            endpoint = f"{self.BASE_URL}/member"

            query_params = {"api_key": api_key, "format": "json"}
            if params.get("limit"):
                query_params["limit"] = params["limit"]
            # Note: congress and chamber parameters are not supported by the API
            # but we keep them in params for potential client-side filtering

        elif operation == "get_member":
            # Get specific member
            bioguide_id = params["bioguide_id"]
            endpoint = f"{self.BASE_URL}/member/{bioguide_id}"

            query_params = {"api_key": api_key, "format": "json"}

        elif operation == "list_committees":
            # List committees
            congress = params.get("congress")
            chamber = params.get("chamber")

            if congress and chamber:
                endpoint = f"{self.BASE_URL}/committee/{congress}/{chamber}"
            elif congress:
                endpoint = f"{self.BASE_URL}/committee/{congress}"
            else:
                endpoint = f"{self.BASE_URL}/committee"

            query_params = {"api_key": api_key, "format": "json"}
            if params.get("limit"):
                query_params["limit"] = params["limit"]

        elif operation == "get_committee":
            # Get specific committee
            chamber = params["chamber"]
            committee_code = params["committee_code"]
            endpoint = f"{self.BASE_URL}/committee/{chamber}/{committee_code}"

            query_params = {"api_key": api_key, "format": "json"}

        elif operation == "search_amendments":
            # List amendments
            congress = params.get("congress")
            amendment_type = params.get("amendment_type")

            if congress and amendment_type:
                endpoint = f"{self.BASE_URL}/amendment/{congress}/{amendment_type}"
            elif congress:
                endpoint = f"{self.BASE_URL}/amendment/{congress}"
            else:
                endpoint = f"{self.BASE_URL}/amendment"

            query_params = {"api_key": api_key, "format": "json"}
            if params.get("limit"):
                query_params["limit"] = params["limit"]

        elif operation == "get_amendment":
            # Get specific amendment
            congress = params["congress"]
            amendment_type = params["amendment_type"]
            amendment_number = params["amendment_number"]
            endpoint = f"{self.BASE_URL}/amendment/{congress}/{amendment_type}/{amendment_number}"

            query_params = {"api_key": api_key, "format": "json"}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Extract the actual data from the response
            # Congress.gov API returns data in different keys depending on endpoint
            if operation in ["search_bills", "list_members", "list_committees", "search_amendments"]:
                # List endpoints return data in a collection
                result_data = data
            else:
                # Detail endpoints return data in a specific key
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Congress.gov API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Congress.gov API request failed: {e}")
            raise Exception(f"Congress.gov API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Congress API operations"""

        schemas = {
            "search_bills": {
                "description": "Search for bills and resolutions in Congress",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": False,
                        "description": "Congress number",
                        "examples": [118, 117, 116],
                    },
                    "bill_type": {
                        "type": "string",
                        "required": False,
                        "description": "Type of bill",
                        "examples": ["hr", "s", "hjres", "sjres", "hconres", "sconres"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [20, 50, 100],
                    },
                },
            },
            "get_bill": {
                "description": "Get detailed information about a specific bill",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": True,
                        "description": "Congress number",
                        "examples": [118, 117],
                    },
                    "bill_type": {
                        "type": "string",
                        "required": True,
                        "description": "Type of bill",
                        "examples": ["hr", "s", "hjres", "sjres"],
                    },
                    "bill_number": {
                        "type": "integer",
                        "required": True,
                        "description": "Bill number",
                        "examples": [1, 100, 1234],
                    },
                },
            },
            "list_members": {
                "description": "List members of Congress",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": False,
                        "description": "Congress number",
                        "examples": [118, 117],
                    },
                    "chamber": {
                        "type": "string",
                        "required": False,
                        "description": "Chamber of Congress",
                        "examples": ["house", "senate"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [20, 50, 100],
                    },
                },
            },
            "get_member": {
                "description": "Get detailed information about a specific member",
                "parameters": {
                    "bioguide_id": {
                        "type": "string",
                        "required": True,
                        "description": "Bioguide ID of the member",
                        "examples": ["B000944", "S000148", "P000197"],
                    },
                },
            },
            "list_committees": {
                "description": "List congressional committees",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": False,
                        "description": "Congress number",
                        "examples": [118, 117],
                    },
                    "chamber": {
                        "type": "string",
                        "required": False,
                        "description": "Chamber of Congress",
                        "examples": ["house", "senate", "joint"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [20, 50, 100],
                    },
                },
            },
            "get_committee": {
                "description": "Get detailed information about a specific committee",
                "parameters": {
                    "chamber": {
                        "type": "string",
                        "required": True,
                        "description": "Chamber of Congress",
                        "examples": ["house", "senate", "joint"],
                    },
                    "committee_code": {
                        "type": "string",
                        "required": True,
                        "description": "Committee code",
                        "examples": ["hsag", "ssaf", "jec"],
                    },
                },
            },
            "search_amendments": {
                "description": "Search for amendments to bills",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": False,
                        "description": "Congress number",
                        "examples": [118, 117],
                    },
                    "amendment_type": {
                        "type": "string",
                        "required": False,
                        "description": "Type of amendment",
                        "examples": ["hamdt", "samdt"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [20, 50, 100],
                    },
                },
            },
            "get_amendment": {
                "description": "Get detailed information about a specific amendment",
                "parameters": {
                    "congress": {
                        "type": "integer",
                        "required": True,
                        "description": "Congress number",
                        "examples": [118, 117],
                    },
                    "amendment_type": {
                        "type": "string",
                        "required": True,
                        "description": "Type of amendment",
                        "examples": ["hamdt", "samdt"],
                    },
                    "amendment_number": {
                        "type": "integer",
                        "required": True,
                        "description": "Amendment number",
                        "examples": [1, 100, 500],
                    },
                },
            },
        }

        return schemas.get(operation)


"""
OpenCorporates API Provider

Provides access to OpenCorporates API for company information.
Supports company search, company details, officer search, and more.

API Documentation: https://api.opencorporates.com/documentation/API-Reference
Note: This API requires an API key
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.providers.base import (
    BaseAPIProvider,
    expose_operation,
)

logger = logging.getLogger(__name__)

# Optional HTTP client - graceful degradation
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OpenCorporatesProvider(BaseAPIProvider):
    """
    OpenCorporates API provider.

    Provides access to company information including:
    - Company search by name
    - Company details by jurisdiction and number
    - Officer search
    - Corporate filings
    - Jurisdiction information
    """

    BASE_URL = "https://api.opencorporates.com/v0.4"

    @property
    def name(self) -> str:
        return "opencorporates"

    @property
    def description(self) -> str:
        return "OpenCorporates API for comprehensive company information including corporate structure, officers, and filings"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "search_companies",
            "get_company",
            "search_officers",
            "get_officer",
            "get_company_filings",
            "list_jurisdictions",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for OpenCorporates operations with detailed guidance"""

        if operation == "search_companies":
            if "q" not in params:
                return False, (
                    "Missing required parameter: q\n"
                    "Example: {'q': 'Apple Inc'}"
                )

        elif operation == "get_company":
            if "jurisdiction_code" not in params:
                return False, (
                    "Missing required parameter: jurisdiction_code\n"
                    "Example: {'jurisdiction_code': 'us_ca', 'company_number': 'C0806592'}"
                )
            if "company_number" not in params:
                return False, (
                    "Missing required parameter: company_number\n"
                    "Example: {'jurisdiction_code': 'us_ca', 'company_number': 'C0806592'}"
                )

        elif operation == "search_officers":
            if "q" not in params:
                return False, (
                    "Missing required parameter: q\n"
                    "Example: {'q': 'John Smith'}"
                )

        elif operation == "get_officer":
            if "officer_id" not in params:
                return False, (
                    "Missing required parameter: officer_id\n"
                    "Example: {'officer_id': '123456'}"
                )

        elif operation == "get_company_filings":
            if "jurisdiction_code" not in params:
                return False, (
                    "Missing required parameter: jurisdiction_code\n"
                    "Example: {'jurisdiction_code': 'us_ca', 'company_number': 'C0806592'}"
                )
            if "company_number" not in params:
                return False, (
                    "Missing required parameter: company_number\n"
                    "Example: {'jurisdiction_code': 'us_ca', 'company_number': 'C0806592'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="search_companies",
        description="Search for companies by name or other criteria",
    )
    def search_companies(
        self,
        q: str,
        jurisdiction_code: Optional[str] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for companies.

        Args:
            q: Search query (company name or other criteria)
            jurisdiction_code: Optional jurisdiction code to filter results
            per_page: Number of results per page (max 100)
            page: Page number

        Returns:
            Dictionary containing matching company data
        """
        params: Dict[str, Any] = {"q": q, "per_page": per_page, "page": page}
        if jurisdiction_code:
            params["jurisdiction_code"] = jurisdiction_code

        return self.execute("search_companies", params)

    @expose_operation(
        operation_name="get_company",
        description="Get detailed information about a specific company by jurisdiction and company number",
    )
    def get_company(
        self, jurisdiction_code: str, company_number: str, sparse: bool = False
    ) -> Dict[str, Any]:
        """
        Get company details by jurisdiction code and company number.

        Args:
            jurisdiction_code: Jurisdiction code (e.g., 'us_ca', 'gb')
            company_number: Company registration number
            sparse: If True, returns minimal data (faster response)

        Returns:
            Dictionary containing company data
        """
        params: Dict[str, Any] = {
            "jurisdiction_code": jurisdiction_code,
            "company_number": company_number,
        }
        if sparse:
            params["sparse"] = sparse

        return self.execute("get_company", params)

    @expose_operation(
        operation_name="search_officers",
        description="Search for company officers (directors, agents) by name",
    )
    def search_officers(
        self,
        q: str,
        jurisdiction_code: Optional[str] = None,
        per_page: int = 30,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for officers.

        Args:
            q: Search query (officer name)
            jurisdiction_code: Optional jurisdiction code to filter results
            per_page: Number of results per page (max 100)
            page: Page number

        Returns:
            Dictionary containing matching officer data
        """
        params: Dict[str, Any] = {"q": q, "per_page": per_page, "page": page}
        if jurisdiction_code:
            params["jurisdiction_code"] = jurisdiction_code

        return self.execute("search_officers", params)

    @expose_operation(
        operation_name="get_officer",
        description="Get detailed information about a specific officer by ID",
    )
    def get_officer(self, officer_id: str) -> Dict[str, Any]:
        """
        Get officer details by ID.

        Args:
            officer_id: Officer ID

        Returns:
            Dictionary containing officer data
        """
        return self.execute("get_officer", {"officer_id": officer_id})

    @expose_operation(
        operation_name="get_company_filings",
        description="Get statutory filings for a specific company",
    )
    def get_company_filings(
        self, jurisdiction_code: str, company_number: str, per_page: int = 30, page: int = 1
    ) -> Dict[str, Any]:
        """
        Get company filings.

        Args:
            jurisdiction_code: Jurisdiction code (e.g., 'us_ca', 'gb')
            company_number: Company registration number
            per_page: Number of results per page (max 100)
            page: Page number

        Returns:
            Dictionary containing filing data
        """
        params: Dict[str, Any] = {
            "jurisdiction_code": jurisdiction_code,
            "company_number": company_number,
            "per_page": per_page,
            "page": page,
        }

        return self.execute("get_company_filings", params)

    @expose_operation(
        operation_name="list_jurisdictions",
        description="Get list of all available jurisdictions",
    )
    def list_jurisdictions(self) -> Dict[str, Any]:
        """
        Get list of jurisdictions.

        Returns:
            Dictionary containing jurisdiction data
        """
        return self.execute("list_jurisdictions", {})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from OpenCorporates API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required for OpenCorporates provider. "
                "Install with: pip install requests"
            )

        # Get API key
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(
                "OpenCorporates API key is required. "
                "Set OPENCORPORATES_API_KEY environment variable or pass api_key in config."
            )

        # Build endpoint based on operation
        if operation == "search_companies":
            endpoint = f"{self.BASE_URL}/companies/search"
            query_params = {
                "q": params["q"],
                "per_page": params.get("per_page", 30),
                "page": params.get("page", 1),
                "api_token": api_key,
            }
            if params.get("jurisdiction_code"):
                query_params["jurisdiction_code"] = params["jurisdiction_code"]

        elif operation == "get_company":
            jurisdiction_code = params["jurisdiction_code"]
            company_number = params["company_number"]
            endpoint = f"{self.BASE_URL}/companies/{jurisdiction_code}/{company_number}"
            query_params = {"api_token": api_key}
            if params.get("sparse"):
                query_params["sparse"] = "true"

        elif operation == "search_officers":
            endpoint = f"{self.BASE_URL}/officers/search"
            query_params = {
                "q": params["q"],
                "per_page": params.get("per_page", 30),
                "page": params.get("page", 1),
                "api_token": api_key,
            }
            if params.get("jurisdiction_code"):
                query_params["jurisdiction_code"] = params["jurisdiction_code"]

        elif operation == "get_officer":
            officer_id = params["officer_id"]
            endpoint = f"{self.BASE_URL}/officers/{officer_id}"
            query_params = {"api_token": api_key}

        elif operation == "get_company_filings":
            jurisdiction_code = params["jurisdiction_code"]
            company_number = params["company_number"]
            endpoint = f"{self.BASE_URL}/companies/{jurisdiction_code}/{company_number}/filings"
            query_params = {
                "per_page": params.get("per_page", 30),
                "page": params.get("page", 1),
                "api_token": api_key,
            }

        elif operation == "list_jurisdictions":
            endpoint = f"{self.BASE_URL}/jurisdictions"
            query_params = {"api_token": api_key}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Extract results from OpenCorporates response format
            result_data = data.get("results", data)

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"OpenCorporates API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenCorporates API request failed: {e}")
            raise Exception(f"OpenCorporates API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Dict[str, Any]:
        """Get schema for a specific operation"""

        schemas = {
            "search_companies": {
                "description": "Search for companies by name or other criteria",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Search query (company name or other criteria)",
                    },
                    "jurisdiction_code": {
                        "type": "string",
                        "required": False,
                        "description": "Jurisdiction code to filter results (e.g., 'us_ca', 'gb')",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max 100, default 30)",
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number (default 1)",
                    },
                },
                "examples": [
                    {
                        "description": "Search for Apple Inc",
                        "params": {"q": "Apple Inc"},
                    },
                    {
                        "description": "Search for companies in California",
                        "params": {"q": "Apple", "jurisdiction_code": "us_ca"},
                    },
                ],
            },
            "get_company": {
                "description": "Get detailed information about a specific company",
                "parameters": {
                    "jurisdiction_code": {
                        "type": "string",
                        "required": True,
                        "description": "Jurisdiction code (e.g., 'us_ca', 'gb')",
                    },
                    "company_number": {
                        "type": "string",
                        "required": True,
                        "description": "Company registration number",
                    },
                    "sparse": {
                        "type": "boolean",
                        "required": False,
                        "description": "If True, returns minimal data (faster response)",
                    },
                },
                "examples": [
                    {
                        "description": "Get Apple Inc details",
                        "params": {"jurisdiction_code": "us_ca", "company_number": "C0806592"},
                    },
                ],
            },
            "search_officers": {
                "description": "Search for company officers (directors, agents) by name",
                "parameters": {
                    "q": {
                        "type": "string",
                        "required": True,
                        "description": "Search query (officer name)",
                    },
                    "jurisdiction_code": {
                        "type": "string",
                        "required": False,
                        "description": "Jurisdiction code to filter results",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max 100, default 30)",
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number (default 1)",
                    },
                },
                "examples": [
                    {
                        "description": "Search for officers named John Smith",
                        "params": {"q": "John Smith"},
                    },
                ],
            },
            "get_officer": {
                "description": "Get detailed information about a specific officer",
                "parameters": {
                    "officer_id": {
                        "type": "string",
                        "required": True,
                        "description": "Officer ID",
                    }
                },
                "examples": [
                    {
                        "description": "Get officer details",
                        "params": {"officer_id": "123456"},
                    },
                ],
            },
            "get_company_filings": {
                "description": "Get statutory filings for a specific company",
                "parameters": {
                    "jurisdiction_code": {
                        "type": "string",
                        "required": True,
                        "description": "Jurisdiction code (e.g., 'us_ca', 'gb')",
                    },
                    "company_number": {
                        "type": "string",
                        "required": True,
                        "description": "Company registration number",
                    },
                    "per_page": {
                        "type": "integer",
                        "required": False,
                        "description": "Number of results per page (max 100, default 30)",
                    },
                    "page": {
                        "type": "integer",
                        "required": False,
                        "description": "Page number (default 1)",
                    },
                },
                "examples": [
                    {
                        "description": "Get filings for Apple Inc",
                        "params": {"jurisdiction_code": "us_ca", "company_number": "C0806592"},
                    },
                ],
            },
            "list_jurisdictions": {
                "description": "Get list of all available jurisdictions",
                "parameters": {},
                "examples": [
                    {
                        "description": "Get all jurisdictions",
                        "params": {},
                    }
                ],
            },
        }

        return schemas.get(operation, {})


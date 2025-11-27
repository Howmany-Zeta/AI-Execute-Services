"""
US Census Bureau API Provider

Provides access to US Census Bureau data including demographic,
economic, and geographic information.

API Documentation: https://www.census.gov/data/developers/guidance/api-user-guide.html
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


class CensusProvider(BaseAPIProvider):
    """
    US Census Bureau API provider for demographic and economic data.

    Provides access to:
    - American Community Survey (ACS) data
    - Decennial Census
    - Economic indicators
    - Population estimates
    - Geographic data
    """

    BASE_URL = "https://api.census.gov/data"

    @property
    def name(self) -> str:
        return "census"

    @property
    def description(self) -> str:
        return "US Census Bureau API for demographic, economic, and geographic data"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_acs_data",
            "get_population",
            "get_economic_data",
            "list_datasets",
            "list_variables",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Census API operations"""

        if operation == "get_acs_data":
            if "variables" not in params:
                return False, "Missing required parameter: variables"
            if "geography" not in params:
                return False, "Missing required parameter: geography"

        elif operation == "get_population":
            if "geography" not in params:
                return False, "Missing required parameter: geography"

        elif operation == "get_economic_data":
            if "variables" not in params:
                return False, "Missing required parameter: variables"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_acs_data",
        description="Get American Community Survey (ACS) demographic and economic data",
    )
    def get_acs_data(self, variables: str, geography: str, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Get ACS data.

        Args:
            variables: Comma-separated variable codes (e.g., 'B01001_001E,B19013_001E')
            geography: Geographic level (e.g., 'state:*', 'county:*', 'tract:*')
            year: Year for data (default: latest available)

        Returns:
            Dictionary containing ACS data and metadata
        """
        params: Dict[str, Any] = {"variables": variables, "geography": geography}
        if year:
            params["year"] = year

        return self.execute("get_acs_data", params)

    @expose_operation(
        operation_name="get_population",
        description="Get population estimates and demographic data",
    )
    def get_population(self, geography: str, year: Optional[int] = None) -> Dict[str, Any]:
        """
        Get population data.

        Args:
            geography: Geographic level (e.g., 'state:06', 'county:*')
            year: Year for data (default: latest available)

        Returns:
            Dictionary containing population data
        """
        params: Dict[str, Any] = {"geography": geography}
        if year:
            params["year"] = year

        return self.execute("get_population", params)

    @expose_operation(
        operation_name="get_economic_data",
        description="Get economic indicators and business statistics",
    )
    def get_economic_data(
        self,
        variables: str,
        geography: Optional[str] = None,
        year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get economic data.

        Args:
            variables: Comma-separated variable codes
            geography: Geographic level (optional)
            year: Year for data (default: latest available)

        Returns:
            Dictionary containing economic data
        """
        params: Dict[str, Any] = {"variables": variables}
        if geography:
            params["geography"] = geography
        if year:
            params["year"] = year

        return self.execute("get_economic_data", params)

    @expose_operation(
        operation_name="list_datasets",
        description="List all available Census datasets",
    )
    def list_datasets(self) -> Dict[str, Any]:
        """
        List available datasets.

        Returns:
            Dictionary containing list of datasets
        """
        return self.execute("list_datasets", {})

    @expose_operation(
        operation_name="list_variables",
        description="List available variables for a specific dataset",
    )
    def list_variables(self, dataset: Optional[str] = None, year: Optional[int] = None) -> Dict[str, Any]:
        """
        List available variables.

        Args:
            dataset: Dataset name (e.g., 'acs/acs5')
            year: Year for dataset

        Returns:
            Dictionary containing list of variables
        """
        params: Dict[str, Any] = {}
        if dataset:
            params["dataset"] = dataset
        if year:
            params["year"] = year

        return self.execute("list_variables", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Census API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for Census provider")

        # Census API may require a key for some datasets
        api_key = self._get_api_key("CENSUS_API_KEY")
        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "get_acs_data":
            # American Community Survey 5-Year Data
            year = params.get("year", "2021")
            endpoint = f"{self.BASE_URL}/{year}/acs/acs5"

            # Build query parameters
            variables = params["variables"]
            if isinstance(variables, list):
                variables = ",".join(variables)

            geography = params["geography"]

            query_params = {"get": variables, "for": geography}

            if api_key:
                query_params["key"] = api_key

        elif operation == "get_population":
            # Population Estimates
            year = params.get("year", "2021")
            endpoint = f"{self.BASE_URL}/{year}/pep/population"

            geography = params["geography"]
            variables = params.get("variables", "POP")

            query_params = {"get": variables, "for": geography}

            if api_key:
                query_params["key"] = api_key

        elif operation == "get_economic_data":
            # Economic Census or other economic data
            year = params.get("year", "2017")
            dataset = params.get("dataset", "ecnbasic")
            endpoint = f"{self.BASE_URL}/{year}/ecnbasic"

            variables = params["variables"]
            if isinstance(variables, list):
                variables = ",".join(variables)

            geography = params.get("geography", "state:*")

            query_params = {"get": variables, "for": geography}

            if api_key:
                query_params["key"] = api_key

        elif operation == "list_datasets":
            # List available datasets
            endpoint = f"{self.BASE_URL}.json"
            query_params = {}

        elif operation == "list_variables":
            # List variables for a dataset
            year = params.get("year", "2021")
            dataset = params.get("dataset", "acs/acs5")
            endpoint = f"{self.BASE_URL}/{year}/{dataset}/variables.json"
            query_params = {}

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Census API typically returns array of arrays
            # First row is headers, subsequent rows are data
            if operation in [
                "get_acs_data",
                "get_population",
                "get_economic_data",
            ]:
                if isinstance(data, list) and len(data) > 1:
                    headers = data[0]
                    rows = data[1:]

                    # Convert to list of dictionaries
                    result_data = [dict(zip(headers, row)) for row in rows]
                else:
                    result_data = data
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"US Census Bureau - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Census API request failed: {e}")
            raise Exception(f"Census API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Census API operations"""

        schemas = {
            "get_acs_data": {
                "description": "Get American Community Survey data",
                "parameters": {
                    "variables": {
                        "type": "string",
                        "required": True,
                        "description": "Comma-separated variable codes",
                        "examples": [
                            "B01001_001E",
                            "B19013_001E",
                            "B25077_001E",
                        ],
                    },
                    "geography": {
                        "type": "string",
                        "required": True,
                        "description": "Geographic level specification",
                        "examples": [
                            "state:*",
                            "county:*",
                            "state:06",
                            "county:037",
                        ],
                    },
                    "year": {
                        "type": "integer",
                        "required": False,
                        "description": "Year for data",
                        "examples": [2020, 2021, 2022],
                    },
                },
            },
            "get_population": {
                "description": "Get population estimates",
                "parameters": {
                    "geography": {
                        "type": "string",
                        "required": True,
                        "description": "Geographic level specification",
                        "examples": ["state:*", "state:06", "county:*"],
                    },
                    "year": {
                        "type": "integer",
                        "required": False,
                        "description": "Year for data",
                        "examples": [2020, 2021, 2022],
                    },
                },
            },
            "get_economic_data": {
                "description": "Get economic indicators",
                "parameters": {
                    "variables": {
                        "type": "string",
                        "required": True,
                        "description": "Comma-separated variable codes",
                        "examples": ["EMP", "PAYANN", "ESTAB"],
                    },
                    "geography": {
                        "type": "string",
                        "required": False,
                        "description": "Geographic level specification",
                        "examples": ["state:*", "county:*"],
                    },
                    "year": {
                        "type": "integer",
                        "required": False,
                        "description": "Year for data",
                        "examples": [2020, 2021, 2022],
                    },
                },
            },
            "list_datasets": {
                "description": "List all available datasets",
                "parameters": {},
            },
            "list_variables": {
                "description": "List available variables",
                "parameters": {
                    "dataset": {
                        "type": "string",
                        "required": False,
                        "description": "Dataset name",
                        "examples": ["acs/acs5", "acs/acs1", "pep/population"],
                    },
                    "year": {
                        "type": "integer",
                        "required": False,
                        "description": "Year for dataset",
                        "examples": [2020, 2021, 2022],
                    },
                },
            },
        }

        return schemas.get(operation)

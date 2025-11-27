"""
World Bank API Provider

Provides access to World Bank development indicators and data.
Supports country data, indicators, and time series queries.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
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


class WorldBankProvider(BaseAPIProvider):
    """
    World Bank API provider for development indicators and country data.

    Provides access to:
    - Economic indicators (GDP, inflation, trade, etc.)
    - Social indicators (education, health, population)
    - Environmental data
    - Country-specific statistics
    """

    BASE_URL = "https://api.worldbank.org/v2"

    @property
    def name(self) -> str:
        return "worldbank"

    @property
    def description(self) -> str:
        return "World Bank API for global development indicators and country statistics"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_indicator",
            "search_indicators",
            "get_country_data",
            "list_countries",
            "list_indicators",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for World Bank operations"""

        if operation == "get_indicator":
            if "indicator_code" not in params:
                return False, "Missing required parameter: indicator_code"
            if "country_code" not in params:
                return False, "Missing required parameter: country_code"

        elif operation == "get_country_data":
            if "country_code" not in params:
                return False, "Missing required parameter: country_code"

        elif operation == "search_indicators":
            if "search_text" not in params:
                return False, "Missing required parameter: search_text"

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_indicator",
        description="Get World Bank development indicator data for a specific country and indicator",
    )
    def get_indicator(
        self,
        indicator_code: str,
        country_code: str,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get World Bank indicator data.

        Args:
            indicator_code: World Bank indicator code (e.g., 'NY.GDP.MKTP.CD', 'SP.POP.TOTL')
            country_code: ISO 3-letter country code (e.g., 'USA', 'CHN', 'GBR')
            start_year: Start year for data range
            end_year: End year for data range

        Returns:
            Dictionary containing indicator data and metadata
        """
        params: Dict[str, Any] = {
            "indicator_code": indicator_code,
            "country_code": country_code,
        }
        if start_year:
            params["start_year"] = start_year
        if end_year:
            params["end_year"] = end_year

        return self.execute("get_indicator", params)

    @expose_operation(
        operation_name="search_indicators",
        description="Search for World Bank indicators by keywords",
    )
    def search_indicators(self, search_text: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Search for World Bank indicators.

        Args:
            search_text: Search keywords (e.g., 'GDP', 'population', 'education')
            limit: Maximum number of results to return

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"search_text": search_text}
        if limit:
            params["limit"] = limit

        return self.execute("search_indicators", params)

    @expose_operation(
        operation_name="get_country_data",
        description="Get general information and statistics about a specific country",
    )
    def get_country_data(self, country_code: str) -> Dict[str, Any]:
        """
        Get country data and metadata.

        Args:
            country_code: ISO 3-letter country code (e.g., 'USA', 'CHN')

        Returns:
            Dictionary containing country information
        """
        return self.execute("get_country_data", {"country_code": country_code})

    @expose_operation(
        operation_name="list_countries",
        description="List all available countries in the World Bank database",
    )
    def list_countries(self) -> Dict[str, Any]:
        """
        List all available countries.

        Returns:
            Dictionary containing list of countries
        """
        return self.execute("list_countries", {})

    @expose_operation(
        operation_name="list_indicators",
        description="List all available World Bank indicators",
    )
    def list_indicators(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all available indicators.

        Args:
            limit: Maximum number of indicators to return

        Returns:
            Dictionary containing list of indicators
        """
        params = {}
        if limit:
            params["limit"] = limit

        return self.execute("list_indicators", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from World Bank API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for World Bank provider")

        # World Bank API doesn't require API key for most operations
        timeout = self.config.get("timeout", 30)

        # Build endpoint based on operation
        if operation == "get_indicator":
            country = params["country_code"]
            indicator = params["indicator_code"]
            endpoint = f"{self.BASE_URL}/country/{country}/indicator/{indicator}"
            query_params = {"format": "json"}

            # Optional parameters
            if "date" in params:
                query_params["date"] = params["date"]
            if "per_page" in params:
                query_params["per_page"] = params["per_page"]

        elif operation == "get_country_data":
            country = params["country_code"]
            endpoint = f"{self.BASE_URL}/country/{country}"
            query_params = {"format": "json"}

        elif operation == "list_countries":
            endpoint = f"{self.BASE_URL}/country"
            query_params = {
                "format": "json",
                "per_page": params.get("per_page", 100),
            }

        elif operation == "list_indicators":
            endpoint = f"{self.BASE_URL}/indicator"
            query_params = {
                "format": "json",
                "per_page": params.get("per_page", 100),
            }

        elif operation == "search_indicators":
            # World Bank doesn't have direct search, so we list and filter
            endpoint = f"{self.BASE_URL}/indicator"
            query_params = {"format": "json", "per_page": "1000"}  # type: ignore[no-redef]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # World Bank API returns [metadata, data]
            if isinstance(data, list) and len(data) > 1:
                result_data = data[1]
            else:
                result_data = data

            # Filter for search operation
            if operation == "search_indicators" and result_data:
                search_text = params["search_text"].lower()
                filtered = [item for item in result_data if search_text in str(item.get("name", "")).lower() or search_text in str(item.get("sourceNote", "")).lower()]
                result_data = filtered[: params.get("limit", 20)]

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"World Bank API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"World Bank API request failed: {e}")
            raise Exception(f"World Bank API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for World Bank operations"""

        schemas = {
            "get_indicator": {
                "description": "Get World Bank development indicator data",
                "parameters": {
                    "indicator_code": {
                        "type": "string",
                        "required": True,
                        "description": "World Bank indicator code",
                        "examples": [
                            "NY.GDP.MKTP.CD",
                            "SP.POP.TOTL",
                            "SE.PRM.ENRR",
                        ],
                    },
                    "country_code": {
                        "type": "string",
                        "required": True,
                        "description": "ISO 3-letter country code",
                        "examples": ["USA", "CHN", "GBR", "IND"],
                    },
                    "start_year": {
                        "type": "integer",
                        "required": False,
                        "description": "Start year for data range",
                        "examples": [2010, 2015, 2020],
                    },
                    "end_year": {
                        "type": "integer",
                        "required": False,
                        "description": "End year for data range",
                        "examples": [2020, 2023, 2025],
                    },
                },
            },
            "search_indicators": {
                "description": "Search for World Bank indicators by keywords",
                "parameters": {
                    "search_text": {
                        "type": "string",
                        "required": True,
                        "description": "Search keywords",
                        "examples": [
                            "GDP",
                            "population",
                            "education",
                            "health",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of results",
                        "examples": [10, 20, 50],
                        "default": 20,
                    },
                },
            },
            "get_country_data": {
                "description": "Get country information and metadata",
                "parameters": {
                    "country_code": {
                        "type": "string",
                        "required": True,
                        "description": "ISO 3-letter country code",
                        "examples": ["USA", "CHN", "GBR"],
                    }
                },
            },
            "list_countries": {
                "description": "List all available countries",
                "parameters": {},
            },
            "list_indicators": {
                "description": "List all available indicators",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of indicators",
                        "examples": [50, 100, 200],
                        "default": 100,
                    }
                },
            },
        }

        return schemas.get(operation)

"""
Federal Reserve Economic Data (FRED) API Provider

Provides access to Federal Reserve Economic Data through the FRED API.
Supports time series data retrieval, search, and metadata operations.

API Documentation: https://fred.stlouisfed.org/docs/api/fred/
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


class FREDProvider(BaseAPIProvider):
    """
    Federal Reserve Economic Data (FRED) API provider.

    Provides access to economic indicators including:
    - GDP, unemployment, inflation data
    - Interest rates and monetary indicators
    - Regional economic data
    - International statistics
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    @property
    def name(self) -> str:
        return "fred"

    @property
    def description(self) -> str:
        return "Federal Reserve Economic Data API for US economic indicators and time series"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_series",
            "search_series",
            "get_series_observations",
            "get_series_info",
            "get_categories",
            "get_releases",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for FRED operations with detailed guidance"""

        if operation == "get_series" or operation == "get_series_info":
            if "series_id" not in params:
                return False, ("Missing required parameter: series_id\n" "Example: {'series_id': 'GDP'}\n" "Use search_series operation to find valid series IDs")

        elif operation == "get_series_observations":
            if "series_id" not in params:
                return False, ("Missing required parameter: series_id\n" "Example: {'series_id': 'GDP', 'observation_start': '2020-01-01'}\n" "Use search_series to find valid series IDs")

        elif operation == "search_series":
            if "search_text" not in params:
                return False, ("Missing required parameter: search_text\n" "Example: {'search_text': 'gdp', 'limit': 10}")

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_series_observations",
        description="Get FRED economic time series observation data with optional date range filtering",
    )
    def get_series_observations(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_order: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get time series observation data from FRED.

        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE', 'CPIAUCSL')
            observation_start: Start date in YYYY-MM-DD format
            observation_end: End date in YYYY-MM-DD format
            limit: Maximum number of observations to return
            offset: Offset for pagination
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Dictionary containing observations and metadata
        """
        params: Dict[str, Any] = {"series_id": series_id}
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset
        if sort_order:
            params["sort_order"] = sort_order

        return self.execute("get_series_observations", params)

    @expose_operation(
        operation_name="search_series",
        description="Search for FRED economic data series by keywords",
    )
    def search_series(
        self,
        search_text: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Search for FRED series by keywords.

        Args:
            search_text: Search keywords (e.g., 'unemployment', 'GDP growth')
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Dictionary containing search results and metadata
        """
        params: Dict[str, Any] = {"search_text": search_text}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        return self.execute("search_series", params)

    @expose_operation(
        operation_name="get_series_info",
        description="Get detailed metadata and information about a specific FRED series",
    )
    def get_series_info(self, series_id: str) -> Dict[str, Any]:
        """
        Get metadata about a FRED series.

        Args:
            series_id: FRED series ID (e.g., 'GDP', 'UNRATE')

        Returns:
            Dictionary containing series metadata
        """
        return self.execute("get_series_info", {"series_id": series_id})

    @expose_operation(
        operation_name="get_categories",
        description="Get FRED data categories for browsing available datasets",
    )
    def get_categories(self, category_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get FRED categories.

        Args:
            category_id: Optional category ID to get subcategories

        Returns:
            Dictionary containing category information
        """
        params = {}
        if category_id:
            params["category_id"] = category_id

        return self.execute("get_categories", params)

    @expose_operation(
        operation_name="get_releases",
        description="Get FRED data release information and schedules",
    )
    def get_releases(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Get FRED releases.

        Args:
            limit: Maximum number of releases to return

        Returns:
            Dictionary containing release information
        """
        params = {}
        if limit:
            params["limit"] = limit

        return self.execute("get_releases", params)

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from FRED API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for FRED provider. Install with: pip install requests")

        # Get API key
        api_key = self._get_api_key("FRED_API_KEY")
        if not api_key:
            raise ValueError("FRED API key not found. Set FRED_API_KEY environment variable or " "provide 'api_key' in config")

        # Build endpoint based on operation
        if operation == "get_series" or operation == "get_series_observations":
            endpoint = f"{self.BASE_URL}/series/observations"
            query_params = {
                "series_id": params["series_id"],
                "api_key": api_key,
                "file_type": "json",
            }

            # Optional parameters
            if "limit" in params:
                query_params["limit"] = params["limit"]
            if "offset" in params:
                query_params["offset"] = params["offset"]
            if "sort_order" in params:
                query_params["sort_order"] = params["sort_order"]
            if "observation_start" in params:
                query_params["observation_start"] = params["observation_start"]
            if "observation_end" in params:
                query_params["observation_end"] = params["observation_end"]

        elif operation == "get_series_info":
            endpoint = f"{self.BASE_URL}/series"
            query_params = {
                "series_id": params["series_id"],
                "api_key": api_key,
                "file_type": "json",
            }

        elif operation == "search_series":
            endpoint = f"{self.BASE_URL}/series/search"
            query_params = {
                "search_text": params["search_text"],
                "api_key": api_key,
                "file_type": "json",
            }

            if "limit" in params:
                query_params["limit"] = params["limit"]
            if "offset" in params:
                query_params["offset"] = params["offset"]

        elif operation == "get_categories":
            endpoint = f"{self.BASE_URL}/category"
            query_params = {"api_key": api_key, "file_type": "json"}

            if "category_id" in params:
                query_params["category_id"] = params["category_id"]

        elif operation == "get_releases":
            endpoint = f"{self.BASE_URL}/releases"
            query_params = {"api_key": api_key, "file_type": "json"}

            if "limit" in params:
                query_params["limit"] = params["limit"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(endpoint, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Extract relevant data based on operation
            if operation in ["get_series", "get_series_observations"]:
                result_data = data.get("observations", [])
            elif operation == "search_series":
                result_data = data.get("seriess", [])
            elif operation == "get_series_info":
                result_data = data.get("seriess", [])
            elif operation == "get_categories":
                result_data = data.get("categories", [])
            elif operation == "get_releases":
                result_data = data.get("releases", [])
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"FRED API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"FRED API request failed: {e}")
            raise Exception(f"FRED API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for FRED operations"""

        schemas = {
            "get_series_observations": {
                "description": "Get time series observation data from FRED",
                "parameters": {
                    "series_id": {
                        "type": "string",
                        "required": True,
                        "description": "FRED series ID (e.g., GDP, UNRATE, CPIAUCSL)",
                        "examples": ["GDP", "UNRATE", "CPIAUCSL", "DGS10"],
                        "validation": {
                            "pattern": r"^[A-Z0-9]+$",
                            "max_length": 50,
                        },
                    },
                    "observation_start": {
                        "type": "string",
                        "required": False,
                        "description": "Start date for observations (YYYY-MM-DD)",
                        "examples": ["2020-01-01", "2015-06-15"],
                        "default": "earliest available",
                    },
                    "observation_end": {
                        "type": "string",
                        "required": False,
                        "description": "End date for observations (YYYY-MM-DD)",
                        "examples": ["2025-10-15", "2023-12-31"],
                        "default": "latest available",
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of observations",
                        "examples": [100, 1000],
                        "default": 100000,
                    },
                    "sort_order": {
                        "type": "string",
                        "required": False,
                        "description": "Sort order (asc/desc)",
                        "examples": ["desc", "asc"],
                        "default": "asc",
                    },
                },
                "examples": [
                    {
                        "description": "Get GDP data for last 5 years",
                        "params": {
                            "series_id": "GDP",
                            "observation_start": "2020-01-01",
                            "limit": 100,
                        },
                    }
                ],
            },
            "search_series": {
                "description": "Search for FRED series by text query",
                "parameters": {
                    "search_text": {
                        "type": "string",
                        "required": True,
                        "description": "Text to search for in series",
                        "examples": ["gdp", "unemployment", "inflation"],
                    },
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum results to return",
                        "examples": [10, 50],
                        "default": 1000,
                    },
                },
                "examples": [
                    {
                        "description": "Search for GDP series",
                        "params": {"search_text": "gdp", "limit": 10},
                    }
                ],
            },
            "get_series_info": {
                "description": "Get metadata about a FRED series",
                "parameters": {
                    "series_id": {
                        "type": "string",
                        "required": True,
                        "description": "FRED series ID to get information about",
                        "examples": ["GDP", "UNRATE", "CPIAUCSL"],
                    }
                },
                "examples": [
                    {
                        "description": "Get info about GDP series",
                        "params": {"series_id": "GDP"},
                    }
                ],
            },
            "get_categories": {
                "description": "Get FRED data categories",
                "parameters": {
                    "category_id": {
                        "type": "integer",
                        "required": False,
                        "description": "Category ID to get subcategories (omit for root categories)",
                        "examples": [125, 32991],
                    }
                },
                "examples": [
                    {"description": "Get root categories", "params": {}},
                    {
                        "description": "Get subcategories of category 125",
                        "params": {"category_id": 125},
                    },
                ],
            },
            "get_releases": {
                "description": "Get FRED data releases",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "required": False,
                        "description": "Maximum number of releases to return",
                        "examples": [10, 50],
                        "default": 1000,
                    }
                },
                "examples": [
                    {
                        "description": "Get recent releases",
                        "params": {"limit": 20},
                    }
                ],
            },
        }

        return schemas.get(operation)

    def validate_and_clean_data(self, operation: str, raw_data: Any) -> Dict[str, Any]:
        """Validate and clean FRED data"""

        result = {
            "data": raw_data,
            "validation_warnings": [],
            "statistics": {},
        }

        if operation in ["get_series", "get_series_observations"]:
            if isinstance(raw_data, list) and len(raw_data) > 0:
                # Check for missing values (FRED uses '.')
                completeness_info = self.validator.check_data_completeness(raw_data, "value", [".", "NA"])

                result["statistics"]["completeness"] = completeness_info

                if completeness_info["missing_count"] > 0:
                    result["validation_warnings"].append(f"{completeness_info['missing_count']} missing values detected " f"({completeness_info['completeness']:.1%} complete)")

                # Extract numeric values for outlier detection
                numeric_values = []
                for item in raw_data:
                    value = item.get("value")
                    if value not in [".", "NA", None]:
                        try:
                            numeric_values.append(float(value))
                        except (ValueError, TypeError):
                            pass

                if len(numeric_values) >= 4:
                    # Detect outliers
                    outlier_indices = self.validator.detect_outliers(numeric_values, method="iqr", threshold=3.0)

                    if outlier_indices:
                        result["validation_warnings"].append(f"{len(outlier_indices)} potential outliers detected")
                        result["statistics"]["outliers_count"] = len(outlier_indices)

                    # Calculate value range
                    value_range = self.validator.calculate_value_range(raw_data, "value")
                    if value_range:
                        result["statistics"]["value_range"] = value_range

                # Detect time gaps
                time_gaps = self.validator.detect_time_gaps(raw_data, "date")
                if time_gaps:
                    result["validation_warnings"].append(f"{len(time_gaps)} time gaps detected in series")
                    result["statistics"]["time_gaps"] = len(time_gaps)

        return result

    def calculate_data_quality(self, operation: str, data: Any, response_time_ms: float) -> Dict[str, Any]:
        """Calculate quality metadata specific to FRED data"""

        # Get base quality from parent
        quality = super().calculate_data_quality(operation, data, response_time_ms)

        # FRED-specific quality enhancements
        # FRED is official government data
        quality["authority_level"] = "official"
        quality["confidence"] = 0.95  # High confidence in FRED data

        # For time series, assess freshness
        if operation in ["get_series", "get_series_observations"]:
            if isinstance(data, list) and len(data) > 0:
                # Check the date of most recent observation
                latest_date = None
                for item in data:
                    if "date" in item:
                        try:
                            from datetime import datetime

                            date_obj = datetime.strptime(item["date"], "%Y-%m-%d")
                            if latest_date is None or date_obj > latest_date:
                                latest_date = date_obj
                        except Exception:
                            pass

                if latest_date:
                    from datetime import datetime

                    age_days = (datetime.now() - latest_date).days
                    quality["freshness_hours"] = age_days * 24

                    # Adjust quality score based on data freshness
                    if age_days < 30:
                        quality["score"] = min(quality["score"] + 0.1, 1.0)
                    elif age_days > 365:
                        quality["score"] = max(quality["score"] - 0.1, 0.0)

        return quality

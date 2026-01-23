"""
OpenWeatherMap API Provider

Provides access to OpenWeatherMap weather data API.
Supports current weather, forecasts, and historical weather data.

API Documentation: https://openweathermap.org/api
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


class OpenWeatherMapProvider(BaseAPIProvider):
    """
    OpenWeatherMap API provider.

    Provides access to weather data including:
    - Current weather conditions
    - 5-day / 3-hour forecast
    - Air pollution data
    - Geocoding for location lookup
    
    Note: Requires an API key from https://openweathermap.org/api
    """

    BASE_URL = "https://api.openweathermap.org/data/2.5"
    GEO_URL = "https://api.openweathermap.org/geo/1.0"

    @property
    def name(self) -> str:
        return "openweathermap"

    @property
    def description(self) -> str:
        return "OpenWeatherMap API for current weather, forecasts, and air quality data"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_current_weather",
            "get_forecast",
            "get_air_pollution",
            "geocode_location",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for OpenWeatherMap operations with detailed guidance"""

        # API key is required for all operations
        if "appid" not in params:
            return False, (
                "Missing required parameter: appid (API key)\n"
                "Get your API key from: https://openweathermap.org/api\n"
                "Example: {'appid': 'your_api_key_here', ...}"
            )

        if operation in ["get_current_weather", "get_forecast", "get_air_pollution"]:
            # Need either city name or coordinates
            has_city = "q" in params
            has_coords = "lat" in params and "lon" in params

            if not has_city and not has_coords:
                return False, (
                    "Missing location parameters. Provide either:\n"
                    "  - City name: {'q': 'London,UK', 'appid': '...'}\n"
                    "  - Coordinates: {'lat': 51.5074, 'lon': -0.1278, 'appid': '...'}\n"
                    "Use geocode_location operation to find coordinates for a city"
                )

        elif operation == "geocode_location":
            if "q" not in params:
                return False, (
                    "Missing required parameter: q (location query)\n"
                    "Example: {'q': 'London,UK', 'appid': '...'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_current_weather",
        description="Get current weather conditions for a location",
    )
    def get_current_weather(
        self,
        appid: str,
        q: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        units: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get current weather data for a location.

        Args:
            appid: OpenWeatherMap API key (required)
            q: City name (e.g., 'London,UK') - use this OR lat/lon
            lat: Latitude (use with lon instead of q)
            lon: Longitude (use with lat instead of q)
            units: Units of measurement ('standard', 'metric', 'imperial', optional)
            lang: Language code for output (optional)

        Returns:
            Dictionary containing current weather data
        """
        params: Dict[str, Any] = {"appid": appid}
        if q:
            params["q"] = q
        if lat is not None:
            params["lat"] = lat
        if lon is not None:
            params["lon"] = lon
        if units:
            params["units"] = units
        if lang:
            params["lang"] = lang

        return self.execute("get_current_weather", params)

    @expose_operation(
        operation_name="get_forecast",
        description="Get 5-day weather forecast with 3-hour intervals for a location",
    )
    def get_forecast(
        self,
        appid: str,
        q: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        units: Optional[str] = None,
        lang: Optional[str] = None,
        cnt: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get 5-day / 3-hour forecast data for a location.

        Args:
            appid: OpenWeatherMap API key (required)
            q: City name (e.g., 'London,UK') - use this OR lat/lon
            lat: Latitude (use with lon instead of q)
            lon: Longitude (use with lat instead of q)
            units: Units of measurement ('standard', 'metric', 'imperial', optional)
            lang: Language code for output (optional)
            cnt: Number of timestamps to return (optional, max 40)

        Returns:
            Dictionary containing forecast data
        """
        params: Dict[str, Any] = {"appid": appid}
        if q:
            params["q"] = q
        if lat is not None:
            params["lat"] = lat
        if lon is not None:
            params["lon"] = lon
        if units:
            params["units"] = units
        if lang:
            params["lang"] = lang
        if cnt is not None:
            params["cnt"] = cnt

        return self.execute("get_forecast", params)

    @expose_operation(
        operation_name="get_air_pollution",
        description="Get current air pollution data for a location",
    )
    def get_air_pollution(
        self,
        appid: str,
        lat: float,
        lon: float,
    ) -> Dict[str, Any]:
        """
        Get current air pollution data for coordinates.

        Args:
            appid: OpenWeatherMap API key (required)
            lat: Latitude (required)
            lon: Longitude (required)

        Returns:
            Dictionary containing air pollution data including AQI and pollutant concentrations
        """
        params: Dict[str, Any] = {
            "appid": appid,
            "lat": lat,
            "lon": lon,
        }
        return self.execute("get_air_pollution", params)

    @expose_operation(
        operation_name="geocode_location",
        description="Convert city name to geographic coordinates (latitude/longitude)",
    )
    def geocode_location(
        self,
        appid: str,
        q: str,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Geocode a location name to coordinates.

        Args:
            appid: OpenWeatherMap API key (required)
            q: Location query (e.g., 'London,UK', 'New York,US')
            limit: Number of results to return (optional, default 5)

        Returns:
            List of locations with coordinates and metadata
        """
        params: Dict[str, Any] = {
            "appid": appid,
            "q": q,
        }
        if limit is not None:
            params["limit"] = limit

        return self.execute("geocode_location", params)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an OpenWeatherMap API operation"""

        if not REQUESTS_AVAILABLE:
            return {
                "error": "requests library not available",
                "message": "Install requests library to use OpenWeatherMap provider: pip install requests",
            }

        # Validate parameters
        is_valid, error_msg = self.validate_params(operation, params)
        if not is_valid:
            return {"error": "Invalid parameters", "message": error_msg}

        # Map operations to endpoints
        if operation == "get_current_weather":
            url = f"{self.BASE_URL}/weather"
        elif operation == "get_forecast":
            url = f"{self.BASE_URL}/forecast"
        elif operation == "get_air_pollution":
            url = f"{self.BASE_URL}/air_pollution"
        elif operation == "geocode_location":
            url = f"{self.GEO_URL}/direct"
        else:
            return {"error": f"Unknown operation: {operation}"}

        try:
            logger.info(f"OpenWeatherMap API request: {operation} -> {url}")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"OpenWeatherMap API response: {operation} successful")
            return data

        except requests.exceptions.RequestException as e:
            error_msg = f"OpenWeatherMap API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from OpenWeatherMap API.

        This method is required by the BaseProvider abstract class.
        It delegates to the execute method which handles the actual API calls.

        Args:
            operation: Operation to perform
            params: Operation parameters

        Returns:
            API response data
        """
        return self.execute(operation, params)


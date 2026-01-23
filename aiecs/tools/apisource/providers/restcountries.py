"""
REST Countries API Provider

Provides access to REST Countries API for country information.
Supports country search, filtering by region, language, currency, and more.

API Documentation: https://restcountries.com/
Note: This API does not require an API key
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


class RESTCountriesProvider(BaseAPIProvider):
    """
    REST Countries API provider.

    Provides access to country information including:
    - Country details (name, capital, population, area, etc.)
    - Search by name, code, capital, region
    - Filter by language, currency, region
    - All countries listing
    """

    BASE_URL = "https://restcountries.com/v3.1"

    @property
    def name(self) -> str:
        return "restcountries"

    @property
    def description(self) -> str:
        return "REST Countries API for comprehensive country information including geography, demographics, and more"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_all_countries",
            "get_country_by_name",
            "get_country_by_code",
            "get_countries_by_region",
            "get_countries_by_subregion",
            "get_countries_by_language",
            "get_countries_by_currency",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for REST Countries operations with detailed guidance"""

        if operation == "get_country_by_name":
            if "name" not in params:
                return False, (
                    "Missing required parameter: name\n"
                    "Example: {'name': 'United States'}"
                )

        elif operation == "get_country_by_code":
            if "code" not in params:
                return False, (
                    "Missing required parameter: code\n"
                    "Example: {'code': 'USA'} or {'code': 'US'}"
                )

        elif operation == "get_countries_by_region":
            if "region" not in params:
                return False, (
                    "Missing required parameter: region\n"
                    "Example: {'region': 'Europe'}\n"
                    "Valid regions: Africa, Americas, Asia, Europe, Oceania"
                )

        elif operation == "get_countries_by_subregion":
            if "subregion" not in params:
                return False, (
                    "Missing required parameter: subregion\n"
                    "Example: {'subregion': 'Western Europe'}"
                )

        elif operation == "get_countries_by_language":
            if "language" not in params:
                return False, (
                    "Missing required parameter: language\n"
                    "Example: {'language': 'spanish'}"
                )

        elif operation == "get_countries_by_currency":
            if "currency" not in params:
                return False, (
                    "Missing required parameter: currency\n"
                    "Example: {'currency': 'USD'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_all_countries",
        description="Get information about all countries",
    )
    def get_all_countries(self) -> Dict[str, Any]:
        """
        Get information about all countries.

        Returns:
            Dictionary containing data for all countries
        """
        return self.execute("get_all_countries", {})

    @expose_operation(
        operation_name="get_country_by_name",
        description="Search for countries by name (supports partial matching)",
    )
    def get_country_by_name(self, name: str, full_text: bool = False) -> Dict[str, Any]:
        """
        Search for countries by name.

        Args:
            name: Country name to search for
            full_text: If True, only exact matches are returned

        Returns:
            Dictionary containing matching country data
        """
        params: Dict[str, Any] = {"name": name}
        if full_text:
            params["full_text"] = full_text

        return self.execute("get_country_by_name", params)

    @expose_operation(
        operation_name="get_country_by_code",
        description="Get country information by ISO country code (alpha-2, alpha-3, or numeric)",
    )
    def get_country_by_code(self, code: str) -> Dict[str, Any]:
        """
        Get country by ISO code.

        Args:
            code: ISO country code (e.g., 'US', 'USA', or '840')

        Returns:
            Dictionary containing country data
        """
        return self.execute("get_country_by_code", {"code": code})

    @expose_operation(
        operation_name="get_countries_by_region",
        description="Get all countries in a specific region",
    )
    def get_countries_by_region(self, region: str) -> Dict[str, Any]:
        """
        Get countries by region.

        Args:
            region: Region name (Africa, Americas, Asia, Europe, Oceania)

        Returns:
            Dictionary containing countries in the region
        """
        return self.execute("get_countries_by_region", {"region": region})

    @expose_operation(
        operation_name="get_countries_by_subregion",
        description="Get all countries in a specific subregion",
    )
    def get_countries_by_subregion(self, subregion: str) -> Dict[str, Any]:
        """
        Get countries by subregion.

        Args:
            subregion: Subregion name (e.g., 'Western Europe', 'South America')

        Returns:
            Dictionary containing countries in the subregion
        """
        return self.execute("get_countries_by_subregion", {"subregion": subregion})

    @expose_operation(
        operation_name="get_countries_by_language",
        description="Get all countries that speak a specific language",
    )
    def get_countries_by_language(self, language: str) -> Dict[str, Any]:
        """
        Get countries by language.

        Args:
            language: Language name (e.g., 'spanish', 'english')

        Returns:
            Dictionary containing countries that speak the language
        """
        return self.execute("get_countries_by_language", {"language": language})

    @expose_operation(
        operation_name="get_countries_by_currency",
        description="Get all countries that use a specific currency",
    )
    def get_countries_by_currency(self, currency: str) -> Dict[str, Any]:
        """
        Get countries by currency.

        Args:
            currency: Currency code (e.g., 'USD', 'EUR')

        Returns:
            Dictionary containing countries that use the currency
        """
        return self.execute("get_countries_by_currency", {"currency": currency})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from REST Countries API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required for REST Countries provider. "
                "Install with: pip install requests"
            )

        # Build endpoint based on operation
        if operation == "get_all_countries":
            endpoint = f"{self.BASE_URL}/all"

        elif operation == "get_country_by_name":
            name = params["name"]
            endpoint = f"{self.BASE_URL}/name/{name}"
            if params.get("full_text"):
                endpoint += "?fullText=true"

        elif operation == "get_country_by_code":
            code = params["code"]
            endpoint = f"{self.BASE_URL}/alpha/{code}"

        elif operation == "get_countries_by_region":
            region = params["region"]
            endpoint = f"{self.BASE_URL}/region/{region}"

        elif operation == "get_countries_by_subregion":
            subregion = params["subregion"]
            endpoint = f"{self.BASE_URL}/subregion/{subregion}"

        elif operation == "get_countries_by_language":
            language = params["language"]
            endpoint = f"{self.BASE_URL}/lang/{language}"

        elif operation == "get_countries_by_currency":
            currency = params["currency"]
            endpoint = f"{self.BASE_URL}/currency/{currency}"

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # REST Countries API returns a list of countries for most operations
            result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"REST Countries API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"REST Countries API request failed: {e}")
            raise Exception(f"REST Countries API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Dict[str, Any]:
        """Get schema for a specific operation"""

        schemas = {
            "get_all_countries": {
                "description": "Get information about all countries",
                "parameters": {},
                "examples": [
                    {
                        "description": "Get all countries",
                        "params": {},
                    }
                ],
            },
            "get_country_by_name": {
                "description": "Search for countries by name (supports partial matching)",
                "parameters": {
                    "name": {
                        "type": "string",
                        "required": True,
                        "description": "Country name to search for",
                    },
                    "full_text": {
                        "type": "boolean",
                        "required": False,
                        "description": "If True, only exact matches are returned",
                    },
                },
                "examples": [
                    {
                        "description": "Search for United States",
                        "params": {"name": "United States"},
                    },
                    {
                        "description": "Exact match for Germany",
                        "params": {"name": "Germany", "full_text": True},
                    },
                ],
            },
            "get_country_by_code": {
                "description": "Get country information by ISO country code",
                "parameters": {
                    "code": {
                        "type": "string",
                        "required": True,
                        "description": "ISO country code (alpha-2, alpha-3, or numeric)",
                    }
                },
                "examples": [
                    {
                        "description": "Get USA by alpha-2 code",
                        "params": {"code": "US"},
                    },
                    {
                        "description": "Get USA by alpha-3 code",
                        "params": {"code": "USA"},
                    },
                ],
            },
            "get_countries_by_region": {
                "description": "Get all countries in a specific region",
                "parameters": {
                    "region": {
                        "type": "string",
                        "required": True,
                        "description": "Region name (Africa, Americas, Asia, Europe, Oceania)",
                    }
                },
                "examples": [
                    {
                        "description": "Get all European countries",
                        "params": {"region": "Europe"},
                    },
                    {
                        "description": "Get all Asian countries",
                        "params": {"region": "Asia"},
                    },
                ],
            },
            "get_countries_by_subregion": {
                "description": "Get all countries in a specific subregion",
                "parameters": {
                    "subregion": {
                        "type": "string",
                        "required": True,
                        "description": "Subregion name (e.g., 'Western Europe', 'South America')",
                    }
                },
                "examples": [
                    {
                        "description": "Get Western European countries",
                        "params": {"subregion": "Western Europe"},
                    },
                ],
            },
            "get_countries_by_language": {
                "description": "Get all countries that speak a specific language",
                "parameters": {
                    "language": {
                        "type": "string",
                        "required": True,
                        "description": "Language name (e.g., 'spanish', 'english')",
                    }
                },
                "examples": [
                    {
                        "description": "Get Spanish-speaking countries",
                        "params": {"language": "spanish"},
                    },
                ],
            },
            "get_countries_by_currency": {
                "description": "Get all countries that use a specific currency",
                "parameters": {
                    "currency": {
                        "type": "string",
                        "required": True,
                        "description": "Currency code (e.g., 'USD', 'EUR')",
                    }
                },
                "examples": [
                    {
                        "description": "Get countries using USD",
                        "params": {"currency": "USD"},
                    },
                ],
            },
        }

        return schemas.get(operation, {})

    def validate_response(self, operation: str, data: Any) -> Tuple[bool, Optional[str]]:
        """Validate API response data"""

        # REST Countries API returns a list for most operations
        if operation == "get_all_countries":
            if not isinstance(data, list):
                return False, "Expected list of countries"
            if len(data) == 0:
                return False, "No countries returned"

        elif operation in [
            "get_country_by_name",
            "get_country_by_code",
            "get_countries_by_region",
            "get_countries_by_subregion",
            "get_countries_by_language",
            "get_countries_by_currency",
        ]:
            if not isinstance(data, list):
                return False, "Expected list of countries"
            if len(data) == 0:
                return False, "No countries found matching criteria"

            # Validate country structure
            for country in data:
                if not isinstance(country, dict):
                    return False, "Invalid country data structure"
                # Check for essential fields
                if "name" not in country:
                    return False, "Country missing 'name' field"

        return True, None

    def assess_data_quality(self, operation: str, data: Any) -> Dict[str, Any]:
        """Assess quality of returned data"""

        quality = {
            "completeness": 0.0,
            "freshness": 1.0,  # REST Countries data is relatively static
            "accuracy": 1.0,  # Assumed high accuracy from official source
            "issues": [],
        }

        if isinstance(data, list):
            total_countries = len(data)
            complete_countries = 0

            for country in data:
                if not isinstance(country, dict):
                    continue

                # Check for key fields
                required_fields = ["name", "cca2", "cca3"]
                optional_fields = ["capital", "population", "area", "region", "languages"]

                has_required = all(field in country for field in required_fields)
                has_optional = sum(1 for field in optional_fields if field in country)

                if has_required and has_optional >= 3:
                    complete_countries += 1

            if total_countries > 0:
                quality["completeness"] = complete_countries / total_countries

            if quality["completeness"] < 0.5:
                quality["issues"].append("Many countries missing key information")

        elif isinstance(data, dict):
            # Single country response
            required_fields = ["name", "cca2", "cca3"]
            optional_fields = ["capital", "population", "area", "region", "languages"]

            has_required = all(field in data for field in required_fields)
            has_optional = sum(1 for field in optional_fields if field in data)

            quality["completeness"] = (
                1.0 if has_required and has_optional >= 3 else 0.5
            )

        return quality

    def clean_response_data(self, operation: str, data: Any) -> Any:
        """Clean and normalize response data"""

        if not isinstance(data, list):
            return data

        # For list responses, ensure consistent structure
        cleaned_data = []
        for country in data:
            if not isinstance(country, dict):
                continue

            # Extract key information in a consistent format
            cleaned_country = {
                "name": country.get("name", {}),
                "codes": {
                    "cca2": country.get("cca2"),
                    "cca3": country.get("cca3"),
                    "ccn3": country.get("ccn3"),
                },
                "capital": country.get("capital", []),
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "languages": country.get("languages", {}),
                "currencies": country.get("currencies", {}),
                "population": country.get("population"),
                "area": country.get("area"),
                "flags": country.get("flags", {}),
                "maps": country.get("maps", {}),
            }

            # Include all original data as well
            cleaned_country["_raw"] = country

            cleaned_data.append(cleaned_country)

        return cleaned_data


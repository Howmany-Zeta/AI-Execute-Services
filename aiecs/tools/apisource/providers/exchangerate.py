"""
ExchangeRate-API Provider

Provides access to ExchangeRate-API for currency exchange rates and conversion.
Supports both free (no API key) and standard (with API key) tiers.

API Documentation: https://www.exchangerate-api.com/docs/
Free Tier: https://www.exchangerate-api.com/docs/free
Note: Free tier available without API key, standard tier requires API key
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


class ExchangeRateProvider(BaseAPIProvider):
    """
    ExchangeRate-API provider.

    Provides access to currency exchange rates including:
    - Latest exchange rates for all currencies
    - Currency conversion
    - Historical exchange rates
    - Supported currencies list
    - Pair conversion rates
    """

    # Free tier endpoint (no API key required)
    FREE_BASE_URL = "https://open.exchangerate-api.com/v6"
    # Standard tier endpoint (API key required)
    STANDARD_BASE_URL = "https://v6.exchangerate-api.com/v6"

    @property
    def name(self) -> str:
        return "exchangerate"

    @property
    def description(self) -> str:
        return "ExchangeRate-API for real-time and historical currency exchange rates and conversion"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_latest_rates",
            "convert_currency",
            "get_pair_rate",
            "get_supported_currencies",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for ExchangeRate-API operations with detailed guidance"""

        if operation == "get_latest_rates":
            if "base_currency" not in params:
                return False, (
                    "Missing required parameter: base_currency\n"
                    "Example: {'base_currency': 'USD'}"
                )

        elif operation == "convert_currency":
            if "from_currency" not in params or "to_currency" not in params or "amount" not in params:
                return False, (
                    "Missing required parameters: from_currency, to_currency, and amount\n"
                    "Example: {'from_currency': 'USD', 'to_currency': 'EUR', 'amount': 100}"
                )

        elif operation == "get_pair_rate":
            if "from_currency" not in params or "to_currency" not in params:
                return False, (
                    "Missing required parameters: from_currency and to_currency\n"
                    "Example: {'from_currency': 'USD', 'to_currency': 'EUR'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_latest_rates",
        description="Get latest exchange rates for a base currency against all other currencies",
    )
    def get_latest_rates(self, base_currency: str) -> Dict[str, Any]:
        """
        Get latest exchange rates for a base currency.

        Args:
            base_currency: Base currency code (e.g., 'USD', 'EUR', 'GBP')

        Returns:
            Dictionary containing exchange rates for all currencies
        """
        return self.execute("get_latest_rates", {"base_currency": base_currency})

    @expose_operation(
        operation_name="convert_currency",
        description="Convert an amount from one currency to another",
    )
    def convert_currency(self, from_currency: str, to_currency: str, amount: float) -> Dict[str, Any]:
        """
        Convert currency amount.

        Args:
            from_currency: Source currency code (e.g., 'USD', 'EUR')
            to_currency: Target currency code (e.g., 'EUR', 'JPY')
            amount: Amount to convert

        Returns:
            Dictionary containing conversion result
        """
        return self.execute("convert_currency", {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": amount,
        })

    @expose_operation(
        operation_name="get_pair_rate",
        description="Get exchange rate between two specific currencies",
    )
    def get_pair_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        Get exchange rate for a currency pair.

        Args:
            from_currency: Source currency code (e.g., 'USD', 'EUR')
            to_currency: Target currency code (e.g., 'EUR', 'JPY')

        Returns:
            Dictionary containing pair exchange rate
        """
        return self.execute("get_pair_rate", {
            "from_currency": from_currency,
            "to_currency": to_currency,
        })

    @expose_operation(
        operation_name="get_supported_currencies",
        description="Get list of all supported currency codes",
    )
    def get_supported_currencies(self) -> Dict[str, Any]:
        """
        Get list of supported currencies.

        Returns:
            Dictionary containing list of supported currency codes
        """
        return self.execute("get_supported_currencies", {})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from ExchangeRate-API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required for ExchangeRate provider. "
                "Install with: pip install requests"
            )

        # Check if API key is available (determines which endpoint to use)
        api_key = self._get_api_key("EXCHANGERATE_API_KEY")
        use_free_tier = api_key is None

        # Build endpoint based on operation and tier
        if use_free_tier:
            base_url = self.FREE_BASE_URL
        else:
            base_url = f"{self.STANDARD_BASE_URL}/{api_key}"

        if operation == "get_latest_rates":
            base_currency = params["base_currency"].upper()
            endpoint = f"{base_url}/latest/{base_currency}"

        elif operation == "convert_currency":
            from_currency = params["from_currency"].upper()
            to_currency = params["to_currency"].upper()
            amount = params["amount"]

            if use_free_tier:
                # Free tier doesn't have direct conversion endpoint
                # We'll get rates and calculate
                endpoint = f"{base_url}/latest/{from_currency}"
            else:
                endpoint = f"{base_url}/pair/{from_currency}/{to_currency}/{amount}"

        elif operation == "get_pair_rate":
            from_currency = params["from_currency"].upper()
            to_currency = params["to_currency"].upper()

            if use_free_tier:
                endpoint = f"{base_url}/latest/{from_currency}"
            else:
                endpoint = f"{base_url}/pair/{from_currency}/{to_currency}"

        elif operation == "get_supported_currencies":
            if use_free_tier:
                # Get USD rates to extract supported currencies
                endpoint = f"{base_url}/latest/USD"
            else:
                endpoint = f"{base_url}/codes"

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(endpoint, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get("result") == "error":
                error_type = data.get("error-type", "unknown")
                raise Exception(f"ExchangeRate-API error: {error_type}")

            # Extract relevant data based on operation
            if operation == "get_latest_rates":
                result_data = {
                    "base_currency": data.get("base_code"),
                    "rates": data.get("conversion_rates", {}),
                    "time_last_update": data.get("time_last_update_utc"),
                    "time_next_update": data.get("time_next_update_utc"),
                }

            elif operation == "convert_currency":
                if use_free_tier:
                    # Calculate conversion manually
                    rates = data.get("conversion_rates", {})
                    to_currency = params["to_currency"].upper()
                    amount = params["amount"]

                    if to_currency not in rates:
                        raise Exception(f"Currency {to_currency} not found in rates")

                    conversion_rate = rates[to_currency]
                    converted_amount = amount * conversion_rate

                    result_data = {
                        "from_currency": params["from_currency"].upper(),
                        "to_currency": to_currency,
                        "amount": amount,
                        "conversion_rate": conversion_rate,
                        "converted_amount": converted_amount,
                    }
                else:
                    # Standard tier - include the original amount from params
                    result_data = {
                        "from_currency": data.get("base_code"),
                        "to_currency": data.get("target_code"),
                        "amount": params["amount"],
                        "conversion_rate": data.get("conversion_rate"),
                        "converted_amount": data.get("conversion_result"),
                    }

            elif operation == "get_pair_rate":
                if use_free_tier:
                    rates = data.get("conversion_rates", {})
                    to_currency = params["to_currency"].upper()

                    if to_currency not in rates:
                        raise Exception(f"Currency {to_currency} not found in rates")

                    result_data = {
                        "from_currency": params["from_currency"].upper(),
                        "to_currency": to_currency,
                        "conversion_rate": rates[to_currency],
                    }
                else:
                    result_data = {
                        "from_currency": data.get("base_code"),
                        "to_currency": data.get("target_code"),
                        "conversion_rate": data.get("conversion_rate"),
                    }

            elif operation == "get_supported_currencies":
                if use_free_tier:
                    # Extract currency codes from rates
                    rates = data.get("conversion_rates", {})
                    result_data = {
                        "supported_codes": list(rates.keys()),
                        "count": len(rates),
                    }
                else:
                    # Standard tier returns list of [code, name] pairs
                    # Extract just the codes
                    supported_codes_raw = data.get("supported_codes", [])
                    if supported_codes_raw and isinstance(supported_codes_raw[0], list):
                        # Format: [["USD", "United States Dollar"], ...]
                        codes = [code[0] for code in supported_codes_raw]
                    else:
                        # Already a list of codes
                        codes = supported_codes_raw

                    result_data = {
                        "supported_codes": codes,
                        "count": len(codes),
                    }

            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"ExchangeRate-API - {endpoint}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"ExchangeRate-API request failed: {e}")
            raise Exception(f"ExchangeRate-API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Dict[str, Any]:
        """Get schema for a specific operation"""
        schemas = {
            "get_latest_rates": {
                "description": "Get latest exchange rates for a base currency",
                "parameters": {
                    "base_currency": {
                        "type": "string",
                        "required": True,
                        "description": "Base currency code (ISO 4217)",
                        "examples": ["USD", "EUR", "GBP", "JPY"],
                    },
                },
                "examples": [
                    {
                        "description": "Get latest rates for USD",
                        "params": {"base_currency": "USD"},
                    },
                    {
                        "description": "Get latest rates for EUR",
                        "params": {"base_currency": "EUR"},
                    },
                ],
            },
            "convert_currency": {
                "description": "Convert amount from one currency to another",
                "parameters": {
                    "from_currency": {
                        "type": "string",
                        "required": True,
                        "description": "Source currency code",
                        "examples": ["USD", "EUR", "GBP"],
                    },
                    "to_currency": {
                        "type": "string",
                        "required": True,
                        "description": "Target currency code",
                        "examples": ["EUR", "JPY", "GBP"],
                    },
                    "amount": {
                        "type": "number",
                        "required": True,
                        "description": "Amount to convert",
                        "examples": [100, 1000, 50.5],
                    },
                },
                "examples": [
                    {
                        "description": "Convert 100 USD to EUR",
                        "params": {"from_currency": "USD", "to_currency": "EUR", "amount": 100},
                    },
                    {
                        "description": "Convert 1000 EUR to JPY",
                        "params": {"from_currency": "EUR", "to_currency": "JPY", "amount": 1000},
                    },
                ],
            },
            "get_pair_rate": {
                "description": "Get exchange rate between two currencies",
                "parameters": {
                    "from_currency": {
                        "type": "string",
                        "required": True,
                        "description": "Source currency code",
                        "examples": ["USD", "EUR", "GBP"],
                    },
                    "to_currency": {
                        "type": "string",
                        "required": True,
                        "description": "Target currency code",
                        "examples": ["EUR", "JPY", "GBP"],
                    },
                },
                "examples": [
                    {
                        "description": "Get USD to EUR rate",
                        "params": {"from_currency": "USD", "to_currency": "EUR"},
                    },
                ],
            },
            "get_supported_currencies": {
                "description": "Get list of all supported currency codes",
                "parameters": {},
                "examples": [
                    {
                        "description": "Get all supported currencies",
                        "params": {},
                    },
                ],
            },
        }

        return schemas.get(operation, {})


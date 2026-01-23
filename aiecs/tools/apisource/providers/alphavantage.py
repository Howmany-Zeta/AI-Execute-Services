"""
Alpha Vantage API Provider

Provides access to Alpha Vantage financial market data API.
Supports stock quotes, time series data, forex, cryptocurrency, and technical indicators.

API Documentation: https://www.alphavantage.co/documentation/
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


class AlphaVantageProvider(BaseAPIProvider):
    """
    Alpha Vantage API provider.

    Provides access to financial market data including:
    - Real-time and historical stock quotes
    - Time series data (daily, weekly, monthly, intraday)
    - Global market quotes
    - Symbol search
    - Forex and cryptocurrency data
    - Technical indicators
    """

    BASE_URL = "https://www.alphavantage.co/query"

    @property
    def name(self) -> str:
        return "alphavantage"

    @property
    def description(self) -> str:
        return "Alpha Vantage API for real-time and historical stock market data, forex, and cryptocurrency"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_quote",
            "get_time_series_daily",
            "get_time_series_intraday",
            "search_symbol",
            "get_global_quote",
            "get_forex_rate",
            "get_crypto_rating",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for Alpha Vantage operations with detailed guidance"""

        if operation in ["get_quote", "get_time_series_daily", "get_time_series_intraday", "get_global_quote"]:
            if "symbol" not in params:
                return False, (
                    "Missing required parameter: symbol\n"
                    "Example: {'symbol': 'AAPL'}\n"
                    "Use search_symbol operation to find valid symbols"
                )

        elif operation == "search_symbol":
            if "keywords" not in params:
                return False, (
                    "Missing required parameter: keywords\n"
                    "Example: {'keywords': 'Apple'}"
                )

        elif operation == "get_forex_rate":
            if "from_currency" not in params or "to_currency" not in params:
                return False, (
                    "Missing required parameters: from_currency and to_currency\n"
                    "Example: {'from_currency': 'USD', 'to_currency': 'EUR'}"
                )

        elif operation == "get_crypto_rating":
            if "symbol" not in params:
                return False, (
                    "Missing required parameter: symbol\n"
                    "Example: {'symbol': 'BTC'}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_global_quote",
        description="Get real-time global quote for a stock symbol including price, volume, and change",
    )
    def get_global_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time global quote for a stock.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')

        Returns:
            Dictionary containing real-time quote data
        """
        return self.execute("get_global_quote", {"symbol": symbol})

    @expose_operation(
        operation_name="get_time_series_daily",
        description="Get daily time series stock data with open, high, low, close, and volume",
    )
    def get_time_series_daily(
        self,
        symbol: str,
        outputsize: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get daily time series data for a stock.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            outputsize: 'compact' (100 data points) or 'full' (20+ years). Default: 'compact'

        Returns:
            Dictionary containing daily time series data
        """
        params: Dict[str, Any] = {"symbol": symbol}
        if outputsize:
            params["outputsize"] = outputsize

        return self.execute("get_time_series_daily", params)

    @expose_operation(
        operation_name="search_symbol",
        description="Search for stock symbols by company name or keywords",
    )
    def search_symbol(self, keywords: str) -> Dict[str, Any]:
        """
        Search for stock symbols by keywords.

        Args:
            keywords: Search keywords (e.g., 'Apple', 'Microsoft')

        Returns:
            Dictionary containing search results with symbols and company names
        """
        return self.execute("search_symbol", {"keywords": keywords})

    @expose_operation(
        operation_name="get_time_series_intraday",
        description="Get intraday time series stock data at specified intervals",
    )
    def get_time_series_intraday(
        self,
        symbol: str,
        interval: str = "5min",
        outputsize: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get intraday time series data for a stock.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            interval: Time interval ('1min', '5min', '15min', '30min', '60min'). Default: '5min'
            outputsize: 'compact' (100 data points) or 'full' (full history). Default: 'compact'

        Returns:
            Dictionary containing intraday time series data
        """
        params: Dict[str, Any] = {"symbol": symbol, "interval": interval}
        if outputsize:
            params["outputsize"] = outputsize

        return self.execute("get_time_series_intraday", params)

    @expose_operation(
        operation_name="get_forex_rate",
        description="Get real-time foreign exchange rate between two currencies",
    )
    def get_forex_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """
        Get forex exchange rate.

        Args:
            from_currency: Source currency code (e.g., 'USD', 'EUR')
            to_currency: Target currency code (e.g., 'EUR', 'JPY')

        Returns:
            Dictionary containing exchange rate data
        """
        return self.execute("get_forex_rate", {
            "from_currency": from_currency,
            "to_currency": to_currency,
        })

    @expose_operation(
        operation_name="get_crypto_rating",
        description="Get cryptocurrency rating and fundamental data",
    )
    def get_crypto_rating(self, symbol: str) -> Dict[str, Any]:
        """
        Get cryptocurrency rating.

        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')

        Returns:
            Dictionary containing crypto rating data
        """
        return self.execute("get_crypto_rating", {"symbol": symbol})

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from Alpha Vantage API"""

        if not REQUESTS_AVAILABLE:
            raise ImportError(
                "requests library is required for Alpha Vantage provider. "
                "Install with: pip install requests"
            )

        # Get API key
        api_key = self._get_api_key("ALPHAVANTAGE_API_KEY")
        if not api_key:
            raise ValueError(
                "Alpha Vantage API key not found. Set ALPHAVANTAGE_API_KEY environment variable or "
                "provide 'api_key' in config. Get your free key at https://www.alphavantage.co/support/#api-key"
            )

        # Build query parameters based on operation
        query_params = {"apikey": api_key}

        if operation == "get_global_quote":
            query_params["function"] = "GLOBAL_QUOTE"
            query_params["symbol"] = params["symbol"]

        elif operation == "get_time_series_daily":
            query_params["function"] = "TIME_SERIES_DAILY"
            query_params["symbol"] = params["symbol"]
            if "outputsize" in params:
                query_params["outputsize"] = params["outputsize"]

        elif operation == "get_time_series_intraday":
            query_params["function"] = "TIME_SERIES_INTRADAY"
            query_params["symbol"] = params["symbol"]
            query_params["interval"] = params.get("interval", "5min")
            if "outputsize" in params:
                query_params["outputsize"] = params["outputsize"]

        elif operation == "search_symbol":
            query_params["function"] = "SYMBOL_SEARCH"
            query_params["keywords"] = params["keywords"]

        elif operation == "get_forex_rate":
            query_params["function"] = "CURRENCY_EXCHANGE_RATE"
            query_params["from_currency"] = params["from_currency"]
            query_params["to_currency"] = params["to_currency"]

        elif operation == "get_crypto_rating":
            query_params["function"] = "CRYPTO_RATING"
            query_params["symbol"] = params["symbol"]

        elif operation == "get_quote":
            # Alias for get_global_quote
            query_params["function"] = "GLOBAL_QUOTE"
            query_params["symbol"] = params["symbol"]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Make API request
        timeout = self.config.get("timeout", 30)
        try:
            response = requests.get(self.BASE_URL, params=query_params, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Check for API error messages
            if "Error Message" in data:
                raise Exception(f"Alpha Vantage API error: {data['Error Message']}")
            if "Note" in data:
                # Rate limit message
                self.logger.warning(f"Alpha Vantage API note: {data['Note']}")

            # Extract relevant data based on operation
            if operation in ["get_global_quote", "get_quote"]:
                result_data = data.get("Global Quote", {})
            elif operation == "get_time_series_daily":
                result_data = data.get("Time Series (Daily)", {})
            elif operation == "get_time_series_intraday":
                # Key varies by interval
                interval = params.get("interval", "5min")
                result_data = data.get(f"Time Series ({interval})", {})
            elif operation == "search_symbol":
                result_data = data.get("bestMatches", [])
            elif operation == "get_forex_rate":
                result_data = data.get("Realtime Currency Exchange Rate", {})
            elif operation == "get_crypto_rating":
                result_data = data.get("Crypto Rating (FCAS)", {})
            else:
                result_data = data

            return self._format_response(
                operation=operation,
                data=result_data,
                source=f"Alpha Vantage API - {query_params.get('function')}",
            )

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Alpha Vantage API request failed: {e}")
            raise Exception(f"Alpha Vantage API request failed: {str(e)}")

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """Get detailed schema for Alpha Vantage operations"""

        schemas = {
            "get_global_quote": {
                "description": "Get real-time global quote for a stock symbol",
                "parameters": {
                    "symbol": {
                        "type": "string",
                        "required": True,
                        "description": "Stock symbol (e.g., AAPL, MSFT, GOOGL)",
                        "examples": ["AAPL", "MSFT", "GOOGL", "TSLA"],
                    }
                },
                "examples": [
                    {
                        "description": "Get Apple stock quote",
                        "params": {"symbol": "AAPL"},
                    }
                ],
            },
            "get_time_series_daily": {
                "description": "Get daily time series stock data",
                "parameters": {
                    "symbol": {
                        "type": "string",
                        "required": True,
                        "description": "Stock symbol",
                        "examples": ["AAPL", "MSFT"],
                    },
                    "outputsize": {
                        "type": "string",
                        "required": False,
                        "description": "Output size: 'compact' (100 points) or 'full' (20+ years)",
                        "examples": ["compact", "full"],
                        "default": "compact",
                    },
                },
                "examples": [
                    {
                        "description": "Get Apple daily data",
                        "params": {"symbol": "AAPL", "outputsize": "compact"},
                    }
                ],
            },
            "get_time_series_intraday": {
                "description": "Get intraday time series stock data",
                "parameters": {
                    "symbol": {
                        "type": "string",
                        "required": True,
                        "description": "Stock symbol",
                        "examples": ["AAPL", "MSFT"],
                    },
                    "interval": {
                        "type": "string",
                        "required": False,
                        "description": "Time interval",
                        "examples": ["1min", "5min", "15min", "30min", "60min"],
                        "default": "5min",
                    },
                    "outputsize": {
                        "type": "string",
                        "required": False,
                        "description": "Output size: 'compact' or 'full'",
                        "examples": ["compact", "full"],
                        "default": "compact",
                    },
                },
                "examples": [
                    {
                        "description": "Get Apple 5-minute intraday data",
                        "params": {"symbol": "AAPL", "interval": "5min"},
                    }
                ],
            },
            "search_symbol": {
                "description": "Search for stock symbols by keywords",
                "parameters": {
                    "keywords": {
                        "type": "string",
                        "required": True,
                        "description": "Search keywords (company name or symbol)",
                        "examples": ["Apple", "Microsoft", "Tesla"],
                    }
                },
                "examples": [
                    {
                        "description": "Search for Apple stock",
                        "params": {"keywords": "Apple"},
                    }
                ],
            },
            "get_forex_rate": {
                "description": "Get foreign exchange rate between two currencies",
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
                        "description": "Get USD to EUR exchange rate",
                        "params": {"from_currency": "USD", "to_currency": "EUR"},
                    }
                ],
            },
            "get_crypto_rating": {
                "description": "Get cryptocurrency rating and fundamental data",
                "parameters": {
                    "symbol": {
                        "type": "string",
                        "required": True,
                        "description": "Cryptocurrency symbol",
                        "examples": ["BTC", "ETH", "LTC"],
                    }
                },
                "examples": [
                    {
                        "description": "Get Bitcoin rating",
                        "params": {"symbol": "BTC"},
                    }
                ],
            },
        }

        return schemas.get(operation)

    def validate_and_clean_data(self, operation: str, raw_data: Any) -> Dict[str, Any]:
        """Validate and clean Alpha Vantage data"""

        result = {
            "data": raw_data,
            "validation_warnings": [],
            "statistics": {},
        }

        if operation in ["get_time_series_daily", "get_time_series_intraday"]:
            if isinstance(raw_data, dict) and len(raw_data) > 0:
                # Time series data is a dict with dates as keys
                data_points = list(raw_data.values())

                if len(data_points) > 0:
                    # Check for completeness
                    result["statistics"]["data_points"] = len(data_points)

                    # Extract numeric values for validation
                    close_values = []
                    for point in data_points:
                        if isinstance(point, dict):
                            close_val = point.get("4. close") or point.get("close")
                            if close_val:
                                try:
                                    close_values.append(float(close_val))
                                except (ValueError, TypeError):
                                    pass

                    if len(close_values) >= 4:
                        # Detect outliers
                        outlier_indices = self.validator.detect_outliers(
                            close_values, method="iqr", threshold=3.0
                        )

                        if outlier_indices:
                            result["validation_warnings"].append(
                                f"{len(outlier_indices)} potential outliers detected"
                            )
                            result["statistics"]["outliers_count"] = len(outlier_indices)

        elif operation == "search_symbol":
            if isinstance(raw_data, list):
                result["statistics"]["results_count"] = len(raw_data)
                if len(raw_data) == 0:
                    result["validation_warnings"].append("No symbols found matching search criteria")

        return result

    def calculate_data_quality(self, operation: str, data: Any, response_time_ms: float) -> Dict[str, Any]:
        """Calculate quality metadata specific to Alpha Vantage data"""

        # Get base quality from parent
        quality = super().calculate_data_quality(operation, data, response_time_ms)

        # Alpha Vantage is a reputable financial data provider
        quality["authority_level"] = "commercial"
        quality["confidence"] = 0.90  # High confidence in Alpha Vantage data

        # For real-time quotes, data is very fresh
        if operation in ["get_global_quote", "get_quote"]:
            quality["freshness_hours"] = 0  # Real-time data
            quality["score"] = min(quality["score"] + 0.1, 1.0)

        # For time series, assess data completeness
        if operation in ["get_time_series_daily", "get_time_series_intraday"]:
            if isinstance(data, dict) and len(data) > 0:
                # More data points = higher quality
                data_point_count = len(data)
                if data_point_count >= 100:
                    quality["score"] = min(quality["score"] + 0.05, 1.0)

        return quality


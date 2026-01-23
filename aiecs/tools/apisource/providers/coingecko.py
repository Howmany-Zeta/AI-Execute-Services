"""
CoinGecko API Provider

Provides access to CoinGecko cryptocurrency data API.
Supports coin prices, market data, historical data, and trending coins.

API Documentation: https://docs.coingecko.com/
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


class CoinGeckoProvider(BaseAPIProvider):
    """
    CoinGecko API provider.

    Provides access to cryptocurrency data including:
    - Real-time and historical coin prices
    - Market data (market cap, volume, price changes)
    - Coin metadata and information
    - Trending coins
    - Global cryptocurrency market data
    - Exchange data
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    @property
    def name(self) -> str:
        return "coingecko"

    @property
    def description(self) -> str:
        return "CoinGecko API for cryptocurrency prices, market data, and trending coins"

    @property
    def supported_operations(self) -> List[str]:
        return [
            "get_coin_price",
            "get_coin_data",
            "get_coin_market_chart",
            "get_trending_coins",
            "get_global_data",
            "search_coins",
            "get_coins_markets",
        ]

    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate parameters for CoinGecko operations with detailed guidance"""

        if operation == "get_coin_price":
            if "ids" not in params:
                return False, (
                    "Missing required parameter: ids\n"
                    "Example: {'ids': 'bitcoin,ethereum', 'vs_currencies': 'usd'}\n"
                    "Use search_coins operation to find valid coin IDs"
                )
            if "vs_currencies" not in params:
                return False, (
                    "Missing required parameter: vs_currencies\n"
                    "Example: {'ids': 'bitcoin', 'vs_currencies': 'usd,eur'}"
                )

        elif operation == "get_coin_data":
            if "id" not in params:
                return False, (
                    "Missing required parameter: id\n"
                    "Example: {'id': 'bitcoin'}"
                )

        elif operation == "get_coin_market_chart":
            if "id" not in params or "vs_currency" not in params or "days" not in params:
                return False, (
                    "Missing required parameters: id, vs_currency, and days\n"
                    "Example: {'id': 'bitcoin', 'vs_currency': 'usd', 'days': '7'}"
                )

        elif operation == "search_coins":
            if "query" not in params:
                return False, (
                    "Missing required parameter: query\n"
                    "Example: {'query': 'bitcoin'}"
                )

        elif operation == "get_coins_markets":
            if "vs_currency" not in params:
                return False, (
                    "Missing required parameter: vs_currency\n"
                    "Example: {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 100}"
                )

        return True, None

    # Exposed operations for AI agent visibility

    @expose_operation(
        operation_name="get_coin_price",
        description="Get current price of cryptocurrencies in multiple currencies",
    )
    def get_coin_price(
        self,
        ids: str,
        vs_currencies: str,
        include_market_cap: Optional[bool] = None,
        include_24hr_vol: Optional[bool] = None,
        include_24hr_change: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get current price of one or more cryptocurrencies.

        Args:
            ids: Comma-separated coin IDs (e.g., 'bitcoin,ethereum,cardano')
            vs_currencies: Comma-separated currency codes (e.g., 'usd,eur,jpy')
            include_market_cap: Include market cap data (optional)
            include_24hr_vol: Include 24hr volume data (optional)
            include_24hr_change: Include 24hr price change data (optional)

        Returns:
            Dictionary containing price data for requested coins
        """
        params: Dict[str, Any] = {
            "ids": ids,
            "vs_currencies": vs_currencies,
        }
        if include_market_cap is not None:
            params["include_market_cap"] = str(include_market_cap).lower()
        if include_24hr_vol is not None:
            params["include_24hr_vol"] = str(include_24hr_vol).lower()
        if include_24hr_change is not None:
            params["include_24hr_change"] = str(include_24hr_change).lower()

        return self.execute("get_coin_price", params)

    @expose_operation(
        operation_name="get_coin_data",
        description="Get comprehensive data for a cryptocurrency including market data, metadata, and links",
    )
    def get_coin_data(
        self,
        id: str,
        localization: Optional[bool] = None,
        tickers: Optional[bool] = None,
        market_data: Optional[bool] = None,
        community_data: Optional[bool] = None,
        developer_data: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive data for a specific cryptocurrency.

        Args:
            id: Coin ID (e.g., 'bitcoin', 'ethereum')
            localization: Include localized language fields (optional)
            tickers: Include ticker data (optional)
            market_data: Include market data (optional)
            community_data: Include community data (optional)
            developer_data: Include developer data (optional)

        Returns:
            Dictionary containing comprehensive coin data
        """
        params: Dict[str, Any] = {"id": id}
        if localization is not None:
            params["localization"] = str(localization).lower()
        if tickers is not None:
            params["tickers"] = str(tickers).lower()
        if market_data is not None:
            params["market_data"] = str(market_data).lower()
        if community_data is not None:
            params["community_data"] = str(community_data).lower()
        if developer_data is not None:
            params["developer_data"] = str(developer_data).lower()

        return self.execute("get_coin_data", params)

    @expose_operation(
        operation_name="get_coin_market_chart",
        description="Get historical market data for a cryptocurrency including price, market cap, and volume",
    )
    def get_coin_market_chart(
        self,
        id: str,
        vs_currency: str,
        days: str,
        interval: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get historical market chart data for a cryptocurrency.

        Args:
            id: Coin ID (e.g., 'bitcoin', 'ethereum')
            vs_currency: Target currency (e.g., 'usd', 'eur')
            days: Number of days ('1', '7', '14', '30', '90', '180', '365', 'max')
            interval: Data interval ('daily' for 90+ days, optional)

        Returns:
            Dictionary containing historical price, market cap, and volume data
        """
        params: Dict[str, Any] = {
            "id": id,
            "vs_currency": vs_currency,
            "days": days,
        }
        if interval:
            params["interval"] = interval

        return self.execute("get_coin_market_chart", params)

    @expose_operation(
        operation_name="get_trending_coins",
        description="Get trending cryptocurrencies in the last 24 hours",
    )
    def get_trending_coins(self) -> Dict[str, Any]:
        """
        Get trending cryptocurrencies.

        Returns:
            Dictionary containing trending coins data
        """
        return self.execute("get_trending_coins", {})

    @expose_operation(
        operation_name="get_global_data",
        description="Get global cryptocurrency market data including total market cap and volume",
    )
    def get_global_data(self) -> Dict[str, Any]:
        """
        Get global cryptocurrency market data.

        Returns:
            Dictionary containing global market statistics
        """
        return self.execute("get_global_data", {})

    @expose_operation(
        operation_name="search_coins",
        description="Search for cryptocurrencies by name or symbol",
    )
    def search_coins(self, query: str) -> Dict[str, Any]:
        """
        Search for cryptocurrencies.

        Args:
            query: Search query (coin name or symbol)

        Returns:
            Dictionary containing search results
        """
        return self.execute("search_coins", {"query": query})

    @expose_operation(
        operation_name="get_coins_markets",
        description="Get list of cryptocurrencies with market data sorted by market cap or volume",
    )
    def get_coins_markets(
        self,
        vs_currency: str,
        ids: Optional[str] = None,
        order: Optional[str] = None,
        per_page: Optional[int] = None,
        page: Optional[int] = None,
        sparkline: Optional[bool] = None,
        price_change_percentage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get list of cryptocurrencies with market data.

        Args:
            vs_currency: Target currency (e.g., 'usd', 'eur')
            ids: Comma-separated coin IDs to filter (optional)
            order: Sort order ('market_cap_desc', 'volume_desc', etc., optional)
            per_page: Results per page (1-250, default 100, optional)
            page: Page number (optional)
            sparkline: Include sparkline 7d data (optional)
            price_change_percentage: Comma-separated time periods ('1h', '24h', '7d', etc., optional)

        Returns:
            Dictionary containing list of coins with market data
        """
        params: Dict[str, Any] = {"vs_currency": vs_currency}
        if ids:
            params["ids"] = ids
        if order:
            params["order"] = order
        if per_page is not None:
            params["per_page"] = per_page
        if page is not None:
            params["page"] = page
        if sparkline is not None:
            params["sparkline"] = str(sparkline).lower()
        if price_change_percentage:
            params["price_change_percentage"] = price_change_percentage

        return self.execute("get_coins_markets", params)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a CoinGecko API operation"""

        if not REQUESTS_AVAILABLE:
            return {
                "error": "requests library not available",
                "message": "Install requests library to use CoinGecko provider: pip install requests",
            }

        # Validate parameters
        is_valid, error_msg = self.validate_params(operation, params)
        if not is_valid:
            return {"error": "Invalid parameters", "message": error_msg}

        # Map operations to endpoints
        endpoint_map = {
            "get_coin_price": "/simple/price",
            "get_coin_data": f"/coins/{params.get('id')}",
            "get_coin_market_chart": f"/coins/{params.get('id')}/market_chart",
            "get_trending_coins": "/search/trending",
            "get_global_data": "/global",
            "search_coins": "/search",
            "get_coins_markets": "/coins/markets",
        }

        endpoint = endpoint_map.get(operation)
        if not endpoint:
            return {"error": f"Unknown operation: {operation}"}

        # Build URL
        url = f"{self.BASE_URL}{endpoint}"

        # Prepare query parameters (remove 'id' from params as it's in the URL)
        query_params = {k: v for k, v in params.items() if k != "id"}

        try:
            logger.info(f"CoinGecko API request: {operation} -> {url}")
            response = requests.get(url, params=query_params, timeout=30)
            response.raise_for_status()

            data = response.json()
            logger.info(f"CoinGecko API response: {operation} successful")
            return data

        except requests.exceptions.RequestException as e:
            error_msg = f"CoinGecko API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}

    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from CoinGecko API.

        This method is required by the BaseProvider abstract class.
        It delegates to the execute method which handles the actual API calls.

        Args:
            operation: Operation to perform
            params: Operation parameters

        Returns:
            API response data
        """
        return self.execute(operation, params)


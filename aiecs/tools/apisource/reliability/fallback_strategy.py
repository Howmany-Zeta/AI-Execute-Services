"""
Intelligent Fallback Strategy for API Providers

Provides automatic provider failover:
- Define fallback chains between providers
- Map equivalent operations across providers
- Convert parameters between provider formats
- Track fallback attempts and success rates
"""

import logging
from typing import Any, Callable, Dict, List, cast

logger = logging.getLogger(__name__)


class FallbackStrategy:
    """
    Manages fallback logic when primary providers fail.

    Automatically retries with alternative providers when a request fails,
    handling operation mapping and parameter conversion.
    """

    # Provider fallback chains: primary -> [fallbacks]
    FALLBACK_MAP = {
        "fred": ["worldbank"],  # FRED -> World Bank for economic data
        "worldbank": [],  # World Bank has no fallback
        "newsapi": [],  # News API has no fallback
        "census": ["worldbank"],  # Census -> World Bank for demographic data
    }

    # Operation mappings: (provider, operation) -> [(fallback_provider,
    # fallback_operation)]
    OPERATION_MAP = {
        ("fred", "get_series"): [("worldbank", "get_indicator")],
        ("fred", "get_series_observations"): [("worldbank", "get_indicator")],
        ("fred", "search_series"): [("worldbank", "search_indicators")],
        ("census", "get_population"): [("worldbank", "get_indicator")],
        ("census", "get_acs_data"): [("worldbank", "get_indicator")],
    }

    # Parameter conversion rules
    PARAMETER_CONVERSIONS = {
        ("fred", "worldbank"): {
            "series_id": "indicator_code",
            "observation_start": "date",  # Note: will need special handling
            "observation_end": "date",
            "limit": "per_page",
        },
        ("census", "worldbank"): {
            "variables": "indicator_code",
            # Note: needs conversion (e.g., 'state:*' -> 'US')
            "geography": "country_code",
        },
    }

    def __init__(self):
        """Initialize fallback strategy"""
        self.fallback_stats = {}  # Track fallback success rates

    def execute_with_fallback(
        self,
        primary_provider: str,
        operation: str,
        params: Dict[str, Any],
        provider_executor: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
        providers_available: List[str],
    ) -> Dict[str, Any]:
        """
        Execute operation with automatic fallback to alternative providers.

        Args:
            primary_provider: Primary provider name
            operation: Operation name
            params: Operation parameters
            provider_executor: Function to execute provider operation:
                               (provider, operation, params) -> result
            providers_available: List of available provider names

        Returns:
            Result dictionary with:
                - success: bool
                - data: result data if successful
                - attempts: list of attempt information
                - fallback_used: bool
        """
        result: Dict[str, Any] = {
            "success": False,
            "data": None,
            "attempts": [],
            "fallback_used": False,
        }

        # Try primary provider
        try:
            logger.info(f"Attempting primary provider: {primary_provider}.{operation}")
            data = provider_executor(primary_provider, operation, params)

            result["success"] = True
            result["data"] = data
            attempts = cast(List[Dict[str, Any]], result["attempts"])
            attempts.append(
                {
                    "provider": primary_provider,
                    "operation": operation,
                    "status": "success",
                }
            )

            return result

        except Exception as primary_error:
            logger.warning(f"Primary provider {primary_provider}.{operation} failed: {primary_error}")
            attempts = cast(List[Dict[str, Any]], result["attempts"])
            attempts.append(
                {
                    "provider": primary_provider,
                    "operation": operation,
                    "status": "failed",
                    "error": str(primary_error),
                }
            )

        # Get fallback providers
        fallback_providers = self.FALLBACK_MAP.get(primary_provider, [])

        if not fallback_providers:
            logger.info(f"No fallback providers configured for {primary_provider}")
            return result

        # Try each fallback provider
        for fallback_provider in fallback_providers:
            if fallback_provider not in providers_available:
                logger.debug(f"Fallback provider {fallback_provider} not available")
                continue

            # Find equivalent operation
            fallback_operations = self._get_fallback_operations(primary_provider, operation, fallback_provider)

            if not fallback_operations:
                logger.debug(f"No operation mapping from {primary_provider}.{operation} " f"to {fallback_provider}")
                continue

            # Try each mapped operation
            for fallback_op in fallback_operations:
                try:
                    logger.info(f"Attempting fallback: {fallback_provider}.{fallback_op}")

                    # Convert parameters
                    converted_params = self._convert_parameters(primary_provider, fallback_provider, params)

                    # Execute fallback
                    data = provider_executor(fallback_provider, fallback_op, converted_params)

                    # Success!
                    result["success"] = True
                    result["data"] = data
                    result["fallback_used"] = True
                    attempts = cast(List[Dict[str, Any]], result["attempts"])
                    attempts.append(
                        {
                            "provider": fallback_provider,
                            "operation": fallback_op,
                            "status": "success",
                        }
                    )

                    # Add fallback warning to metadata
                    if isinstance(data, dict) and "metadata" in data:
                        data["metadata"]["fallback_warning"] = f"Primary provider {primary_provider} failed, " f"using fallback {fallback_provider}"
                        data["metadata"]["original_provider"] = primary_provider
                        data["metadata"]["original_operation"] = operation

                    # Update success stats
                    self._update_stats(fallback_provider, fallback_op, success=True)

                    logger.info(f"Fallback successful: {fallback_provider}.{fallback_op}")

                    return result

                except Exception as fallback_error:
                    logger.warning(f"Fallback {fallback_provider}.{fallback_op} failed: " f"{fallback_error}")
                    attempts = cast(List[Dict[str, Any]], result["attempts"])
                    attempts.append(
                        {
                            "provider": fallback_provider,
                            "operation": fallback_op,
                            "status": "failed",
                            "error": str(fallback_error),
                        }
                    )

                    # Update failure stats
                    self._update_stats(fallback_provider, fallback_op, success=False)

        # All attempts failed
        logger.error(f"All providers failed for operation {operation}. " f"Attempts: {len(result['attempts'])}")

        return result

    def _get_fallback_operations(self, primary_provider: str, operation: str, fallback_provider: str) -> List[str]:
        """
        Get equivalent operations in fallback provider.

        Args:
            primary_provider: Primary provider name
            operation: Operation name
            fallback_provider: Fallback provider name

        Returns:
            List of equivalent operation names
        """
        key = (primary_provider, operation)
        mappings = self.OPERATION_MAP.get(key, [])

        # Filter for specific fallback provider
        fallback_ops = [op for provider, op in mappings if provider == fallback_provider]

        return fallback_ops

    def _convert_parameters(
        self,
        source_provider: str,
        target_provider: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Convert parameters from source to target provider format.

        Args:
            source_provider: Source provider name
            target_provider: Target provider name
            params: Original parameters

        Returns:
            Converted parameters
        """
        conversion_key = (source_provider, target_provider)
        conversion_rules = self.PARAMETER_CONVERSIONS.get(conversion_key, {})

        converted = {}

        for source_param, value in params.items():
            # Check if there's a conversion rule
            if source_param in conversion_rules:
                target_param = conversion_rules[source_param]

                # Apply special conversions
                converted_value = self._convert_parameter_value(
                    source_provider,
                    target_provider,
                    source_param,
                    target_param,
                    value,
                )

                converted[target_param] = converted_value
            else:
                # Keep parameter as-is
                converted[source_param] = value

        # Add default parameters for target provider
        converted = self._add_default_parameters(target_provider, converted)

        return converted

    def _convert_parameter_value(
        self,
        source_provider: str,
        target_provider: str,
        source_param: str,
        target_param: str,
        value: Any,
    ) -> Any:
        """
        Convert parameter value between provider formats.

        Args:
            source_provider: Source provider
            target_provider: Target provider
            source_param: Source parameter name
            target_param: Target parameter name
            value: Original value

        Returns:
            Converted value
        """
        # FRED -> World Bank conversions
        if source_provider == "fred" and target_provider == "worldbank":
            if source_param == "series_id":
                # Try to map common FRED series to World Bank indicators
                series_map = {
                    "GDP": "NY.GDP.MKTP.CD",
                    "GDPC1": "NY.GDP.MKTP.KD",
                    "UNRATE": "SL.UEM.TOTL.NE.ZS",
                    "CPIAUCSL": "FP.CPI.TOTL",
                    "CPILFESL": "FP.CPI.TOTL",
                }
                return series_map.get(value, value)

            elif source_param in ["observation_start", "observation_end"]:
                # Convert to World Bank date format (year or year:year)
                # Extract year from date string
                if isinstance(value, str) and len(value) >= 4:
                    return value[:4]

        # Census -> World Bank conversions
        elif source_provider == "census" and target_provider == "worldbank":
            if source_param == "geography":
                # Convert census geography to country code
                if "state" in str(value).lower():
                    return "US"  # US country code

        return value

    def _add_default_parameters(self, provider: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add default parameters required by provider.

        Args:
            provider: Provider name
            params: Current parameters

        Returns:
            Parameters with defaults added
        """
        if provider == "worldbank":
            # World Bank needs country code
            if "country_code" not in params:
                params["country_code"] = "US"  # Default to US

        return params

    def _update_stats(self, provider: str, operation: str, success: bool):
        """
        Update fallback success statistics.

        Args:
            provider: Provider name
            operation: Operation name
            success: Whether attempt was successful
        """
        key = f"{provider}.{operation}"

        if key not in self.fallback_stats:
            self.fallback_stats[key] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
            }

        self.fallback_stats[key]["attempts"] += 1
        if success:
            self.fallback_stats[key]["successes"] += 1
        else:
            self.fallback_stats[key]["failures"] += 1

    def get_fallback_stats(self) -> Dict[str, Any]:
        """
        Get fallback statistics.

        Returns:
            Dictionary with fallback statistics
        """
        stats = {}
        for key, data in self.fallback_stats.items():
            success_rate = data["successes"] / data["attempts"] if data["attempts"] > 0 else 0.0
            stats[key] = {
                "attempts": data["attempts"],
                "successes": data["successes"],
                "failures": data["failures"],
                "success_rate": round(success_rate, 3),
            }

        return stats

"""
Base API Provider Interface

Abstract base class for all API data source providers in the API Source Tool.
Provides common functionality for rate limiting, caching, error handling, and metadata.

Enhanced with:
- Detailed metrics and health monitoring
- Smart error handling with retries
- Data quality assessment
- Comprehensive metadata with quality scores
- Operation exposure for AI agent visibility
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from aiecs.tools.apisource.monitoring.metrics import DetailedMetrics
from aiecs.tools.apisource.reliability.error_handler import SmartErrorHandler
from aiecs.tools.apisource.utils.validators import DataValidator

logger = logging.getLogger(__name__)


def expose_operation(operation_name: str, description: str):
    """
    Decorator: Mark provider operations that should be exposed to AI agents.

    This decorator allows provider operations to be automatically discovered by the
    LangChain adapter and exposed as individual tools to AI agents, providing
    fine-grained visibility into provider capabilities.

    Args:
        operation_name: The name of the operation (e.g., 'get_series_observations')
        description: Human-readable description of what the operation does

    Returns:
        Decorated function with metadata for operation discovery

    Example:
        @expose_operation(
            operation_name='get_series_observations',
            description='Get FRED economic time series data'
        )
        def get_series_observations(self, series_id: str, ...):
            pass
    """

    def decorator(func):
        func._exposed_operation = True
        func._operation_name = operation_name
        func._operation_description = description
        return func

    return decorator


class RateLimiter:
    """Token bucket rate limiter for API requests"""

    def __init__(self, tokens_per_second: float = 1.0, max_tokens: int = 10):
        """
        Initialize rate limiter with token bucket algorithm.

        Args:
            tokens_per_second: Rate at which tokens are added to the bucket
            max_tokens: Maximum number of tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_update = time.time()
        self.lock = Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Add new tokens based on elapsed time
            self.tokens = int(min(self.max_tokens, self.tokens + elapsed * self.tokens_per_second))
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def wait(self, tokens: int = 1, timeout: float = 30.0) -> bool:
        """
        Wait until tokens are available.

        Args:
            tokens: Number of tokens to acquire
            timeout: Maximum time to wait in seconds

        Returns:
            True if tokens were acquired, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.acquire(tokens):
                return True
            time.sleep(0.1)
        return False


class BaseAPIProvider(ABC):
    """
    Abstract base class for all API data source providers.

    Provides:
    - Rate limiting with token bucket algorithm
    - Standardized error handling
    - Metadata about provider capabilities
    - Parameter validation
    - Response formatting
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the API provider.

        Args:
            config: Configuration dictionary with API keys, rate limits, etc.
        """
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Initialize rate limiter
        rate_limit = self.config.get("rate_limit", 10)  # requests per second
        max_burst = self.config.get("max_burst", 20)
        self.rate_limiter = RateLimiter(tokens_per_second=rate_limit, max_tokens=max_burst)

        # Initialize detailed metrics
        self.metrics = DetailedMetrics(max_response_times=100)

        # Initialize smart error handler
        self.error_handler = SmartErrorHandler(
            max_retries=self.config.get("max_retries", 3),
            backoff_factor=self.config.get("backoff_factor", 2.0),
            initial_delay=self.config.get("initial_delay", 1.0),
            max_delay=self.config.get("max_delay", 30.0),
        )

        # Initialize data validator
        self.validator = DataValidator()

        # Legacy stats for backwards compatibility
        self.stats: Dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
        }
        self.stats_lock = Lock()

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'fred', 'worldbank')"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the provider"""

    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        """List of supported operation names"""

    @abstractmethod
    def validate_params(self, operation: str, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate parameters for a specific operation.

        Args:
            operation: Operation name
            params: Parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """

    @abstractmethod
    def fetch(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from the API.

        Args:
            operation: Operation to perform
            params: Operation parameters

        Returns:
            Response data in standardized format

        Raises:
            ValueError: If operation is not supported
            Exception: If API request fails
        """

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get provider metadata including health status and detailed metrics.

        Returns:
            Dictionary with comprehensive provider information
        """
        return {
            "name": self.name,
            "description": self.description,
            "operations": self.supported_operations,
            "stats": self.metrics.get_summary(),  # Use detailed metrics
            "health": {
                "score": self.metrics.get_health_score(),
                "status": ("healthy" if self.metrics.get_health_score() > 0.7 else "degraded"),
            },
            "config": {
                "rate_limit": self.config.get("rate_limit", 10),
                "timeout": self.config.get("timeout", 30),
                "max_retries": self.config.get("max_retries", 3),
            },
        }

    def get_operation_schema(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get schema for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Schema dictionary or None if not available
        """
        # Override in subclass to provide operation-specific schemas
        return None

    @classmethod
    def get_exposed_operations(cls) -> List[Dict[str, Any]]:
        """
        Get all operations that are exposed to AI agents via the @expose_operation decorator.

        This method discovers all methods decorated with @expose_operation and returns
        their metadata along with their schemas. This enables the LangChain adapter to
        automatically create individual tools for each provider operation.

        Returns:
            List of operation dictionaries, each containing:
                - name: Operation name
                - description: Operation description
                - schema: Operation schema (parameters, types, descriptions)
                - method_name: The actual method name on the class

        Example:
            >>> FREDProvider.get_exposed_operations()
            [
                {
                    'name': 'get_series_observations',
                    'description': 'Get FRED economic time series data',
                    'schema': {...},
                    'method_name': 'get_series_observations'
                },
                ...
            ]
        """
        operations = []

        # Create a temporary instance to access get_operation_schema
        # We need this because get_operation_schema might be an instance method
        try:
            # Try to get schema without instantiation first
            for attr_name in dir(cls):
                # Skip private and special methods
                if attr_name.startswith("_"):
                    continue

                try:
                    attr = getattr(cls, attr_name)
                except AttributeError:
                    continue

                # Check if this is an exposed operation
                if callable(attr) and hasattr(attr, "_exposed_operation"):
                    operation_name = attr._operation_name
                    operation_description = attr._operation_description

                    # Schema retrieval requires an instance, so skip at class level
                    # Schema will be available at runtime when provider instances are created
                    schema = None

                    operations.append(
                        {
                            "name": operation_name,
                            "description": operation_description,
                            "schema": schema,
                            "method_name": attr_name,
                        }
                    )

                    logger.debug(f"Discovered exposed operation: {operation_name} from {cls.__name__}")

        except Exception as e:
            logger.warning(f"Error discovering exposed operations for {cls.__name__}: {e}")

        return operations

    def validate_and_clean_data(self, operation: str, raw_data: Any) -> Dict[str, Any]:
        """
        Validate and clean data (optional, override in subclass).

        Providers can implement custom validation logic for their specific data formats.

        Args:
            operation: Operation that produced the data
            raw_data: Raw data from API

        Returns:
            Dictionary with:
                - data: Cleaned data
                - validation_warnings: List of warnings
                - statistics: Data quality statistics
        """
        # Default implementation: no validation
        return {"data": raw_data, "validation_warnings": [], "statistics": {}}

    def calculate_data_quality(self, operation: str, data: Any, response_time_ms: float) -> Dict[str, Any]:
        """
        Calculate quality metadata for the response.

        Can be overridden by providers for custom quality assessment.

        Args:
            operation: Operation performed
            data: Response data
            response_time_ms: Response time in milliseconds

        Returns:
            Quality metadata dictionary
        """
        quality: Dict[str, Any] = {
            "score": 0.7,  # Default quality score
            "completeness": 1.0,  # Assume complete unless validated otherwise
            "freshness_hours": None,  # Unknown freshness
            "confidence": 0.8,  # Default confidence
            "authority_level": "verified",  # Provider is verified
        }

        # Adjust score based on response time
        if response_time_ms < 500:
            score = quality.get("score", 0.7)
            if isinstance(score, (int, float)):
                quality["score"] = min(score + 0.1, 1.0)
        elif response_time_ms > 5000:
            score = quality.get("score", 0.7)
            if isinstance(score, (int, float)):
                quality["score"] = max(score - 0.1, 0.0)

        # Check if data is empty
        if data is None:
            quality["completeness"] = 0.0
            quality["score"] = 0.0
        elif isinstance(data, list) and len(data) == 0:
            quality["completeness"] = 0.0
            score = quality.get("score", 0.7)
            if isinstance(score, (int, float)):
                quality["score"] = max(score - 0.3, 0.0)

        return quality

    def _update_stats(self, success: bool):
        """Update request statistics"""
        with self.stats_lock:
            total = self.stats.get("total_requests", 0)
            if isinstance(total, (int, float)):
                self.stats["total_requests"] = total + 1
            if success:
                successful = self.stats.get("successful_requests", 0)
                if isinstance(successful, (int, float)):
                    self.stats["successful_requests"] = successful + 1
            else:
                failed = self.stats.get("failed_requests", 0)
                if isinstance(failed, (int, float)):
                    self.stats["failed_requests"] = failed + 1
            self.stats["last_request_time"] = datetime.utcnow().isoformat()

    def _format_response(
        self,
        operation: str,
        data: Any,
        source: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        validation_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format response in standardized format with enhanced metadata.

        Args:
            operation: Operation that was performed
            data: Response data
            source: Data source URL or identifier
            response_time_ms: Response time in milliseconds
            validation_result: Optional validation result from validate_and_clean_data

        Returns:
            Standardized response dictionary with comprehensive metadata
        """
        # Calculate quality metadata
        quality = self.calculate_data_quality(operation, data, response_time_ms or 0)

        # Calculate coverage information
        coverage = self._calculate_coverage(data)

        # Build metadata
        metadata = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source or f"{self.name} API",
            "quality": quality,
            "coverage": coverage,
        }

        # Add API info if response time provided
        if response_time_ms is not None:
            metadata["api_info"] = {
                "response_time_ms": round(response_time_ms, 2),
                "provider": self.name,
            }

        # Add validation warnings if present
        if validation_result and validation_result.get("validation_warnings"):
            metadata["validation_warnings"] = validation_result["validation_warnings"]

        # Add statistics if present
        if validation_result and validation_result.get("statistics"):
            metadata["statistics"] = validation_result["statistics"]

        return {
            "provider": self.name,
            "operation": operation,
            "data": data,
            "metadata": metadata,
        }

    def _calculate_coverage(self, data: Any) -> Dict[str, Any]:
        """
        Calculate data coverage information.

        Args:
            data: Response data

        Returns:
            Coverage information dictionary
        """
        coverage: Dict[str, Any] = {}

        # Calculate record count
        if isinstance(data, list):
            coverage["total_records"] = len(data)

            # Try to extract date range from time series data
            if len(data) > 0 and isinstance(data[0], dict):
                date_fields = ["date", "observation_date", "timestamp"]
                for date_field in date_fields:
                    if date_field in data[0]:
                        dates = [item.get(date_field) for item in data if date_field in item and item.get(date_field)]
                        if dates:
                            try:
                                # Sort to get earliest and latest
                                dates_sorted = sorted(dates)
                                coverage["start_date"] = dates_sorted[0]
                                coverage["end_date"] = dates_sorted[-1]

                                # Try to infer frequency
                                frequency = self.validator.infer_data_frequency(data, date_field)
                                if frequency:
                                    coverage["frequency"] = frequency
                            except Exception:
                                pass
                        break
        elif isinstance(data, dict):
            # For dict responses
            if "articles" in data:
                coverage["total_records"] = len(data["articles"])
            elif "total_results" in data:
                coverage["total_results"] = data["total_results"]
            else:
                coverage["total_records"] = 1
        else:
            coverage["total_records"] = 1 if data is not None else 0

        return coverage

    def _get_api_key(self, key_name: Optional[str] = None) -> Optional[str]:
        """
        Get API key from config or environment.

        Args:
            key_name: Specific key name to retrieve

        Returns:
            API key or None if not found
        
        Note: When used through APISourceTool, API keys are loaded from .env files
        via BaseSettings and passed via config dict. This fallback is for backward
        compatibility and independent provider usage.
        """
        import os

        # Try config first (primary path - API keys come from APISourceTool's BaseSettings)
        if "api_key" in self.config:
            return self.config["api_key"]

        # Fallback: Try environment variable (ensures .env files are loaded)
        # Use ToolConfigLoader to ensure .env files are loaded if not already
        try:
            from aiecs.config.tool_config import get_tool_config_loader
            
            loader = get_tool_config_loader()
            loader.load_env_config()  # Ensures .env files are loaded
        except Exception:
            # If loader is unavailable, try direct dotenv load as fallback
            try:
                from dotenv import load_dotenv
                from pathlib import Path
                
                # Try to load .env files from common locations
                for env_file in [".env", ".env.local"]:
                    env_path = Path(env_file)
                    if env_path.exists():
                        load_dotenv(env_path, override=False)
                        break
            except Exception:
                pass  # If dotenv is unavailable, continue with os.environ

        # Try environment variable (now includes values from .env files)
        env_var = key_name or f"{self.name.upper()}_API_KEY"
        return os.environ.get(env_var)

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an operation with rate limiting, error handling, and metrics tracking.

        Args:
            operation: Operation to perform
            params: Operation parameters

        Returns:
            Response data with enhanced metadata

        Raises:
            ValueError: If operation is invalid or parameters are invalid
            Exception: If API request fails after all retries
        """
        # Validate operation
        if operation not in self.supported_operations:
            available_ops = ", ".join(self.supported_operations)
            schema = self.get_operation_schema(operation)
            operation_error_msg = f"Operation '{operation}' not supported by {self.name}.\n" f"Supported operations: {available_ops}"
            if schema:
                operation_error_msg += f"\nSee get_operation_schema('{operation}') for details"
            raise ValueError(operation_error_msg)

        # Validate parameters with enhanced error messages
        validation_result = self.validate_params(operation, params)
        is_valid: bool = validation_result[0]
        error_msg: Optional[str] = validation_result[1]
        if not is_valid:
            schema = self.get_operation_schema(operation)
            enhanced_error = f"Invalid parameters for {self.name}.{operation}: {error_msg or 'Unknown error'}"

            if schema and "parameters" in schema:
                # Add helpful parameter information
                required_params = [name for name, info in schema["parameters"].items() if info.get("required", False)]
                if required_params:
                    enhanced_error += f"\nRequired parameters: {', '.join(required_params)}"

                # Add examples if available
                if "examples" in schema and schema["examples"]:
                    example = schema["examples"][0]
                    enhanced_error += f"\nExample: {example.get('params', {})}"

            raise ValueError(enhanced_error)

        # Apply rate limiting
        wait_start = time.time()
        if not self.rate_limiter.wait(tokens=1, timeout=30):
            self.metrics.record_request(success=False, response_time_ms=0, error_type="rate_limit")
            raise Exception(f"Rate limit exceeded for {self.name}. " "Please try again later or increase rate limits in config.")

        # Track rate limit wait time
        wait_time_ms = (time.time() - wait_start) * 1000
        if wait_time_ms > 100:  # Only record significant waits
            self.metrics.record_rate_limit_wait(wait_time_ms)

        # Execute with smart retry logic
        def fetch_operation():
            """Wrapper for fetch with timing"""
            start_time = time.time()
            result = self.fetch(operation, params)
            response_time_ms = (time.time() - start_time) * 1000
            return result, response_time_ms

        # Use error handler for retries
        execution_result = self.error_handler.execute_with_retry(
            operation_func=fetch_operation,
            operation_name=operation,
            provider_name=self.name,
        )

        if execution_result["success"]:
            result, response_time_ms = execution_result["data"]

            # Calculate data size for metrics
            data = result.get("data") if isinstance(result, dict) else result
            record_count = len(data) if isinstance(data, list) else (1 if data else 0)

            # Record success metrics
            self.metrics.record_request(
                success=True,
                response_time_ms=response_time_ms,
                record_count=record_count,
                cached=False,
            )

            # Update legacy stats
            self._update_stats(success=True)

            self.logger.info(f"Successfully executed {self.name}.{operation} " f"in {response_time_ms:.0f}ms ({record_count} records)")

            return result
        else:
            # All retries failed
            error_info = execution_result["error"]
            retry_info = execution_result["retry_info"]

            # Record failure metrics
            self.metrics.record_request(
                success=False,
                response_time_ms=0,
                error_type=error_info.get("type", "unknown"),
                error_message=error_info.get("message"),
            )

            # Update legacy stats
            self._update_stats(success=False)

            # Build comprehensive error message
            error_msg = f"Failed to execute {self.name}.{operation} after " f"{retry_info['attempts']} attempts.\n" f"Error: {error_info['message']}"

            # Add recovery suggestions
            if retry_info.get("recovery_suggestions"):
                error_msg += "\n\nSuggestions:"
                for suggestion in retry_info["recovery_suggestions"][:3]:
                    error_msg += f"\n  - {suggestion}"

            self.logger.error(error_msg)

            raise Exception(error_msg)

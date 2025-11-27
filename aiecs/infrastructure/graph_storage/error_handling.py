"""
Comprehensive Error Handling and Logging for Graph Storage

Provides structured error handling, logging, and exception types
for production-ready graph storage operations.
"""

import asyncio
import logging
import traceback
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import functools

logger = logging.getLogger(__name__)


class GraphStoreError(Exception):
    """Base exception for graph store errors"""


class GraphStoreConnectionError(GraphStoreError):
    """Connection-related errors"""


class GraphStoreQueryError(GraphStoreError):
    """Query execution errors"""


class GraphStoreValidationError(GraphStoreError):
    """Data validation errors"""


class GraphStoreNotFoundError(GraphStoreError):
    """Entity/relation not found errors"""


class GraphStoreConflictError(GraphStoreError):
    """Conflict errors (duplicate IDs, etc.)"""


class GraphStoreTimeoutError(GraphStoreError):
    """Operation timeout errors"""


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for error reporting"""

    operation: str
    entity_id: Optional[str] = None
    relation_id: Optional[str] = None
    query: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "operation": self.operation,
            "entity_id": self.entity_id,
            "relation_id": self.relation_id,
            "query": (self.query[:100] + "..." if self.query and len(self.query) > 100 else self.query),
            "parameters": self.parameters,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "severity": self.severity.value,
        }


class ErrorHandler:
    """
    Centralized error handling and logging

    Provides structured error handling with context and logging.

    Example:
        ```python
        handler = ErrorHandler()

        try:
            await store.add_entity(entity)
        except Exception as e:
            handler.handle_error(
                e,
                ErrorContext(
                    operation="add_entity",
                    entity_id=entity.id,
                    severity=ErrorSeverity.HIGH
                )
            )
        ```
    """

    def __init__(self, log_level: int = logging.ERROR):
        """
        Initialize error handler

        Args:
            log_level: Logging level for errors
        """
        self.log_level = log_level

    def handle_error(self, error: Exception, context: ErrorContext, reraise: bool = True) -> None:
        """
        Handle and log an error with context

        Args:
            error: Exception that occurred
            context: Error context information
            reraise: Whether to re-raise the exception
        """
        # Map exception types
        mapped_error = self._map_exception(error)

        # Log error with context
        self._log_error(mapped_error, context)

        # Re-raise if requested
        if reraise:
            raise mapped_error from error

    def _map_exception(self, error: Exception) -> Exception:
        """
        Map generic exceptions to specific graph store exceptions

        Args:
            error: Original exception

        Returns:
            Mapped exception
        """
        error_str = str(error).lower()
        error_type = type(error).__name__

        # Connection errors
        if any(keyword in error_str for keyword in ["connection", "connect", "timeout", "network"]):
            return GraphStoreConnectionError(str(error))

        # Not found errors
        if any(keyword in error_str for keyword in ["not found", "does not exist", "missing"]):
            return GraphStoreNotFoundError(str(error))

        # Conflict errors
        if any(
            keyword in error_str
            for keyword in [
                "duplicate",
                "already exists",
                "conflict",
                "unique",
            ]
        ):
            return GraphStoreConflictError(str(error))

        # Validation errors
        if any(keyword in error_str for keyword in ["invalid", "validation", "required", "missing"]):
            return GraphStoreValidationError(str(error))

        # Timeout errors
        if "timeout" in error_str or "TimeoutError" in error_type:
            return GraphStoreTimeoutError(str(error))

        # Query errors
        if any(keyword in error_str for keyword in ["syntax", "query", "sql", "execute"]):
            return GraphStoreQueryError(str(error))

        # Return original if no mapping
        return error

    def _log_error(self, error: Exception, context: ErrorContext) -> None:
        """
        Log error with structured context

        Args:
            error: Exception to log
            context: Error context
        """
        error_dict = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context.to_dict(),
            "traceback": traceback.format_exc(),
        }

        # Log based on severity
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL: {error_dict}")
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH: {error_dict}")
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM: {error_dict}")
        else:
            logger.info(f"LOW: {error_dict}")


def error_handler(
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = True,
):
    """
    Decorator for automatic error handling

    Args:
        operation: Operation name for context
        severity: Error severity level
        reraise: Whether to re-raise exceptions

    Example:
        ```python
        @error_handler("add_entity", severity=ErrorSeverity.HIGH)
        async def add_entity(self, entity: Entity):
            # Implementation
            pass
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            handler = ErrorHandler()

            # Extract context from arguments
            entity_id = None
            relation_id = None

            if args and hasattr(args[0], "id"):
                entity_id = args[0].id
            elif "entity_id" in kwargs:
                entity_id = kwargs["entity_id"]
            elif "relation_id" in kwargs:
                relation_id = kwargs["relation_id"]

            context = ErrorContext(
                operation=operation,
                entity_id=entity_id,
                relation_id=relation_id,
                severity=severity,
            )

            try:
                return await func(self, *args, **kwargs)
            except Exception as e:
                handler.handle_error(e, context, reraise=reraise)

        return wrapper

    return decorator


class RetryHandler:
    """
    Retry handler for transient errors

    Implements exponential backoff retry logic for operations
    that may fail due to transient issues.

    Example:
        ```python
        retry = RetryHandler(max_retries=3, base_delay=1.0)

        result = await retry.execute(
            lambda: store.get_entity("entity_1"),
            retry_on=[GraphStoreConnectionError]
        )
        ```
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry handler

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    async def execute(self, func: Callable, retry_on: Optional[list] = None, *args, **kwargs) -> Any:
        """
        Execute function with retry logic

        Args:
            func: Async function to execute
            retry_on: List of exception types to retry on (None = all)
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        if retry_on is None:
            retry_on = [Exception]

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry
                if not any(isinstance(e, exc_type) for exc_type in retry_on):
                    raise

                # Don't retry on last attempt
                if attempt >= self.max_retries:
                    break

                # Calculate delay with exponential backoff
                delay = min(
                    self.base_delay * (self.exponential_base**attempt),
                    self.max_delay,
                )

                logger.warning(f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.1f}s: {e}")

                await asyncio.sleep(delay)

        # All retries exhausted
        if last_exception is None:
            raise RuntimeError("Retry logic failed but no exception was captured")
        raise last_exception


# Configure logging for graph storage
def configure_graph_storage_logging(level: int = logging.INFO, format_string: Optional[str] = None) -> None:
    """
    Configure logging for graph storage modules

    Args:
        level: Logging level
        format_string: Custom format string
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - " "%(message)s - [%(filename)s:%(lineno)d]"

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))

    # Configure graph storage logger
    graph_logger = logging.getLogger("aiecs.infrastructure.graph_storage")
    graph_logger.setLevel(level)
    graph_logger.addHandler(handler)

    logger.info(f"Graph storage logging configured at level {logging.getLevelName(level)}")


# Import asyncio for retry handler

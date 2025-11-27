"""
Runnable Pattern for Async Components

Provides a formal base class for async task components with standardized
lifecycle management, configuration, error handling, and retry logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Type variable for configuration - must be a subclass of RunnableConfig
ConfigT = TypeVar("ConfigT", bound="RunnableConfig")
# Type variable for result
ResultT = TypeVar("ResultT")


class RunnableState(Enum):
    """Runnable component lifecycle states"""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class RunnableConfig:
    """
    Base configuration for Runnable components

    Attributes:
        max_retries: Maximum number of retry attempts on failure
        retry_delay: Initial delay between retries in seconds
        retry_backoff: Exponential backoff multiplier for retries
        max_retry_delay: Maximum delay between retries in seconds
        timeout: Execution timeout in seconds (None = no timeout)
        enable_circuit_breaker: Enable circuit breaker pattern
        circuit_breaker_threshold: Number of failures before opening circuit
        circuit_breaker_timeout: Time to wait before attempting reset (seconds)
    """

    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    max_retry_delay: float = 30.0
    timeout: Optional[float] = None
    enable_circuit_breaker: bool = False
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0

    # Additional custom configuration
    custom_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Metrics collected during execution"""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    retry_count: int = 0
    success: bool = False
    error: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker pattern implementation

    Prevents cascading failures by stopping execution after threshold failures.
    """

    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        """
        Initialize circuit breaker

        Args:
            threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting reset (seconds)
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.is_open = False

    def record_success(self) -> None:
        """Record successful execution"""
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if not self.is_open:
            return True

        # Check if timeout has passed (half-open state)
        if self.last_failure_time and (time.time() - self.last_failure_time) >= self.timeout:
            logger.info("Circuit breaker attempting reset (half-open)")
            self.is_open = False
            self.failure_count = 0
            return True

        return False


class Runnable(ABC, Generic[ConfigT, ResultT]):
    """
    Abstract base class for async runnable components

    Provides standardized lifecycle management with:
    - Setup/Execute/Teardown pattern
    - Configuration management with validation
    - Error handling and retry logic with exponential backoff
    - Circuit breaker pattern for fault tolerance
    - Execution metrics and monitoring
    - Timeout support

    Type Parameters:
        ConfigT: Configuration type (subclass of RunnableConfig)
        ResultT: Result type returned by execute()

    Example:
        ```python
        @dataclass
        class MyConfig(RunnableConfig):
            api_key: str = ""
            max_items: int = 100

        class MyComponent(Runnable[MyConfig, Dict[str, Any]]):
            async def _setup(self) -> None:
                # Initialize resources
                self.client = APIClient(self.config.api_key)

            async def _execute(self, **kwargs) -> Dict[str, Any]:
                # Main execution logic
                return await self.client.fetch_data()

            async def _teardown(self) -> None:
                # Cleanup resources
                await self.client.close()
        ```
    """

    def __init__(self, config: Optional[ConfigT] = None):
        """
        Initialize runnable component

        Args:
            config: Component configuration (uses default if None)
        """
        self._config = config or self._get_default_config()
        self._state = RunnableState.CREATED
        self._metrics = ExecutionMetrics()
        self._circuit_breaker: Optional[CircuitBreaker] = None

        # Initialize circuit breaker if enabled
        if self._config.enable_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                threshold=self._config.circuit_breaker_threshold,
                timeout=self._config.circuit_breaker_timeout,
            )

        # Validate configuration
        self._validate_config()

    @property
    def config(self) -> ConfigT:
        """Get component configuration"""
        return self._config

    @property
    def state(self) -> RunnableState:
        """Get current component state"""
        return self._state

    @property
    def metrics(self) -> ExecutionMetrics:
        """Get execution metrics"""
        return self._metrics

    def _get_default_config(self) -> ConfigT:
        """
        Get default configuration

        Override in subclasses to provide custom default configuration.

        Returns:
            Default configuration instance
        """
        return RunnableConfig()  # type: ignore

    def _validate_config(self) -> None:
        """
        Validate configuration

        Override in subclasses to add custom validation logic.
        Raise ValueError if configuration is invalid.
        """
        if self._config.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self._config.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self._config.retry_backoff < 1.0:
            raise ValueError("retry_backoff must be >= 1.0")

    async def setup(self) -> None:
        """
        Setup component (initialize resources)

        This method should be called before run() or execute().
        Transitions state from CREATED to READY.

        Raises:
            RuntimeError: If component is not in CREATED state
            Exception: If setup fails
        """
        if self._state != RunnableState.CREATED:
            raise RuntimeError(f"Cannot setup component in state {self._state.value}")

        try:
            self._state = RunnableState.INITIALIZING
            logger.info(f"Setting up {self.__class__.__name__}...")

            await self._setup()

            self._state = RunnableState.READY
            logger.info(f"{self.__class__.__name__} setup complete")

        except Exception as e:
            self._state = RunnableState.FAILED
            logger.error(f"{self.__class__.__name__} setup failed: {e}")
            raise

    @abstractmethod
    async def _setup(self) -> None:
        """
        Subclass-specific setup logic

        Override this method to implement custom initialization.
        Called by setup() method.
        """

    async def execute(self, **kwargs) -> ResultT:
        """
        Execute component logic (without retry/circuit breaker)

        This is a low-level execution method. Use run() for production
        code to get retry and circuit breaker support.

        Args:
            **kwargs: Execution parameters

        Returns:
            Execution result

        Raises:
            RuntimeError: If component is not in READY state
            Exception: If execution fails
        """
        if self._state != RunnableState.READY:
            raise RuntimeError(f"Cannot execute component in state {self._state.value}. " f"Call setup() first.")

        try:
            self._state = RunnableState.RUNNING
            self._metrics.start_time = datetime.utcnow()

            logger.debug(f"Executing {self.__class__.__name__}...")
            result = await self._execute(**kwargs)

            self._metrics.end_time = datetime.utcnow()
            self._metrics.duration_seconds = (self._metrics.end_time - self._metrics.start_time).total_seconds()
            self._metrics.success = True

            # Reset to READY for potential re-execution
            self._state = RunnableState.READY
            logger.debug(f"{self.__class__.__name__} execution completed in " f"{self._metrics.duration_seconds:.2f}s")

            return result

        except Exception as e:
            self._metrics.end_time = datetime.utcnow()
            if self._metrics.start_time is not None:
                self._metrics.duration_seconds = (self._metrics.end_time - self._metrics.start_time).total_seconds()
            else:
                self._metrics.duration_seconds = 0.0
            self._metrics.error = str(e)
            self._state = RunnableState.FAILED
            logger.error(f"{self.__class__.__name__} execution failed: {e}")
            raise

    @abstractmethod
    async def _execute(self, **kwargs) -> ResultT:
        """
        Subclass-specific execution logic

        Override this method to implement the main component logic.
        Called by execute() and run() methods.

        Args:
            **kwargs: Execution parameters

        Returns:
            Execution result
        """

    async def run(self, **kwargs) -> ResultT:
        """
        Run component with retry logic and circuit breaker

        This is the recommended method for production use.
        Includes:
        - Circuit breaker check
        - Retry logic with exponential backoff
        - Timeout support
        - Automatic state management

        Args:
            **kwargs: Execution parameters

        Returns:
            Execution result

        Raises:
            RuntimeError: If circuit breaker is open
            asyncio.TimeoutError: If execution times out
            Exception: If all retries fail
        """
        # Check circuit breaker
        if self._circuit_breaker and not self._circuit_breaker.can_execute():
            raise RuntimeError(f"Circuit breaker is open for {self.__class__.__name__}")

        last_exception: Optional[Exception] = None
        retry_delay = self._config.retry_delay

        for attempt in range(self._config.max_retries + 1):
            try:
                # Execute with timeout if configured
                if self._config.timeout:
                    result = await asyncio.wait_for(self.execute(**kwargs), timeout=self._config.timeout)
                else:
                    result = await self.execute(**kwargs)

                # Record success in circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()

                # Update retry count on success (number of retries that
                # occurred)
                if attempt > 0:
                    self._metrics.retry_count = attempt

                return result

            except Exception as e:
                last_exception = e
                # Track number of retries (not including initial attempt)
                if attempt > 0:
                    self._metrics.retry_count = attempt

                # Record failure in circuit breaker
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure()

                # Don't retry if this was the last attempt
                if attempt >= self._config.max_retries:
                    logger.error(f"{self.__class__.__name__} failed after " f"{attempt + 1} attempts: {e}")
                    break

                # Log retry attempt
                logger.warning(f"{self.__class__.__name__} attempt {attempt + 1} failed: {e}. " f"Retrying in {retry_delay:.1f}s...")

                # Wait before retry
                await asyncio.sleep(retry_delay)

                # Increase delay with exponential backoff
                retry_delay = min(
                    retry_delay * self._config.retry_backoff,
                    self._config.max_retry_delay,
                )

                # Reset state to READY for next attempt
                self._state = RunnableState.READY

        # All retries failed
        raise last_exception or RuntimeError("Execution failed")

    async def teardown(self) -> None:
        """
        Teardown component (cleanup resources)

        This method should be called after execution is complete.
        Can be called from any state.

        Raises:
            Exception: If teardown fails
        """
        try:
            logger.info(f"Tearing down {self.__class__.__name__}...")

            await self._teardown()

            self._state = RunnableState.STOPPED
            logger.info(f"{self.__class__.__name__} teardown complete")

        except Exception as e:
            logger.error(f"{self.__class__.__name__} teardown failed: {e}")
            raise

    @abstractmethod
    async def _teardown(self) -> None:
        """
        Subclass-specific teardown logic

        Override this method to implement custom cleanup.
        Called by teardown() method.
        """

    async def __aenter__(self):
        """Async context manager entry"""
        await self.setup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.teardown()
        return False

    def reset_metrics(self) -> None:
        """Reset execution metrics"""
        self._metrics = ExecutionMetrics()

    def get_metrics_dict(self) -> Dict[str, Any]:
        """
        Get metrics as dictionary

        Returns:
            Dictionary with execution metrics
        """
        return {
            "start_time": (self._metrics.start_time.isoformat() if self._metrics.start_time else None),
            "end_time": (self._metrics.end_time.isoformat() if self._metrics.end_time else None),
            "duration_seconds": self._metrics.duration_seconds,
            "retry_count": self._metrics.retry_count,
            "success": self._metrics.success,
            "error": self._metrics.error,
            "state": self._state.value,
        }

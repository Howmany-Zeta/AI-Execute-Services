"""
Health Checks for Graph Storage Backends

Provides health check endpoints and monitoring for graph storage backends,
enabling production-ready health monitoring and alerting.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health check status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """
    Result of a health check

    Example:
        ```python
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All checks passed",
            response_time_ms=12.5,
            details={"connection_pool": "ok", "query_test": "ok"}
        )
        ```
    """

    status: HealthStatus
    message: str
    response_time_ms: float = 0.0
    timestamp: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.details is None:
            self.details = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": round(self.response_time_ms, 2),
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "details": self.details,
            "error": self.error,
        }

    def is_healthy(self) -> bool:
        """Check if status is healthy"""
        return self.status == HealthStatus.HEALTHY


class HealthChecker:
    """
    Health checker for graph storage backends

    Performs comprehensive health checks including:
    - Connection availability
    - Query execution
    - Response time
    - Resource availability

    Example:
        ```python
        checker = HealthChecker(store)
        result = await checker.check_health()

        if result.is_healthy():
            print("Store is healthy")
        else:
            print(f"Store is {result.status}: {result.message}")
        ```
    """

    def __init__(
        self,
        store: Any,
        timeout_seconds: float = 5.0,
        query_timeout_ms: float = 1000.0,
    ):
        """
        Initialize health checker

        Args:
            store: Graph store instance
            timeout_seconds: Overall health check timeout
            query_timeout_ms: Query execution timeout
        """
        self.store = store
        self.timeout_seconds = timeout_seconds
        self.query_timeout_ms = query_timeout_ms

    async def check_health(self) -> HealthCheckResult:
        """
        Perform comprehensive health check

        Returns:
            HealthCheckResult with status and details
        """
        start_time = asyncio.get_event_loop().time()
        details: Dict[str, Any] = {}
        errors: List[str] = []

        try:
            # Check 1: Store initialization
            if not hasattr(self.store, "_is_initialized") or not self.store._is_initialized:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Store not initialized",
                    response_time_ms=0.0,
                    error="Store not initialized",
                )
            details["initialized"] = True

            # Check 2: Connection availability
            connection_ok = await self._check_connection()
            details["connection"] = "ok" if connection_ok else "failed"
            if not connection_ok:
                errors.append("Connection check failed")

            # Check 3: Query execution
            query_ok = await self._check_query_execution()
            details["query_execution"] = "ok" if query_ok else "failed"
            if not query_ok:
                errors.append("Query execution failed")

            # Check 4: Response time
            response_time = await self._check_response_time()
            details["response_time_ms"] = response_time
            if response_time > self.query_timeout_ms:
                errors.append(f"Response time too high: {response_time}ms")

            # Check 5: Resource availability (if applicable)
            if hasattr(self.store, "pool"):
                pool_ok = await self._check_connection_pool()
                details["connection_pool"] = "ok" if pool_ok else "degraded"
                if not pool_ok:
                    errors.append("Connection pool issues")

            # Determine status
            if errors:
                if len(errors) >= 2:
                    status = HealthStatus.UNHEALTHY
                else:
                    status = HealthStatus.DEGRADED
                message = "; ".join(errors)
            else:
                status = HealthStatus.HEALTHY
                message = "All health checks passed"

            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            return HealthCheckResult(
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                details=details,
            )

        except Exception as e:
            response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            logger.error(f"Health check failed: {e}", exc_info=True)

            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check exception: {str(e)}",
                response_time_ms=response_time_ms,
                error=str(e),
                details=details,
            )

    async def _check_connection(self) -> bool:
        """Check if connection is available"""
        try:
            # Try a simple operation
            if hasattr(self.store, "get_stats"):
                await asyncio.wait_for(self.store.get_stats(), timeout=self.timeout_seconds)
                return True
            return False
        except Exception as e:
            logger.debug(f"Connection check failed: {e}")
            return False

    async def _check_query_execution(self) -> bool:
        """Check if queries can be executed"""
        try:
            # Try a simple query (get_stats or similar)
            if hasattr(self.store, "get_stats"):
                await asyncio.wait_for(self.store.get_stats(), timeout=self.timeout_seconds)
                return True
            return False
        except Exception as e:
            logger.debug(f"Query execution check failed: {e}")
            return False

    async def _check_response_time(self) -> float:
        """Check average response time"""
        try:
            times = []
            for _ in range(3):
                start = asyncio.get_event_loop().time()
                if hasattr(self.store, "get_stats"):
                    await self.store.get_stats()
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                times.append(elapsed)

            return sum(times) / len(times) if times else 0.0
        except Exception:
            return float("inf")

    async def _check_connection_pool(self) -> bool:
        """Check connection pool health"""
        try:
            if hasattr(self.store, "pool"):
                pool = self.store.pool

                # Check pool size
                if hasattr(pool, "get_size"):
                    size = pool.get_size()
                    free = pool.get_idle_size()

                    # Pool is healthy if not completely exhausted
                    return free > 0 or size < pool.get_max_size()

                # If we can't check, assume OK
                return True
            return True
        except Exception:
            return False

    async def check_liveness(self) -> bool:
        """
        Quick liveness check (faster than full health check)

        Returns:
            True if store is alive, False otherwise
        """
        try:
            if hasattr(self.store, "get_stats"):
                await asyncio.wait_for(self.store.get_stats(), timeout=1.0)
                return True
            return False
        except Exception:
            return False

    async def check_readiness(self) -> bool:
        """
        Readiness check (can handle requests)

        Returns:
            True if store is ready, False otherwise
        """
        result = await self.check_health()
        return result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


class HealthMonitor:
    """
    Continuous health monitoring

    Monitors health status over time and tracks metrics.

    Example:
        ```python
        monitor = HealthMonitor(checker, interval_seconds=30)
        await monitor.start()

        # Get current status
        status = monitor.get_current_status()

        # Get health history
        history = monitor.get_health_history()
        ```
    """

    def __init__(self, checker: HealthChecker, interval_seconds: float = 30.0):
        """
        Initialize health monitor

        Args:
            checker: Health checker instance
            interval_seconds: Check interval in seconds
        """
        self.checker = checker
        self.interval_seconds = interval_seconds
        self.health_history: List[HealthCheckResult] = []
        self.max_history = 100
        self._monitoring = False
        self._task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start continuous monitoring"""
        if self._monitoring:
            return

        self._monitoring = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Health monitoring started")

    async def stop(self) -> None:
        """Stop continuous monitoring"""
        self._monitoring = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")

    async def _monitor_loop(self) -> None:
        """Monitoring loop"""
        while self._monitoring:
            try:
                result = await self.checker.check_health()
                self.health_history.append(result)

                # Keep only recent history
                if len(self.health_history) > self.max_history:
                    self.health_history.pop(0)

                # Log unhealthy status
                if not result.is_healthy():
                    logger.warning(f"Health check failed: {result.status} - {result.message}")

                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}", exc_info=True)
                await asyncio.sleep(self.interval_seconds)

    def get_current_status(self) -> Optional[HealthCheckResult]:
        """Get most recent health check result"""
        return self.health_history[-1] if self.health_history else None

    def get_health_history(self, limit: int = 10) -> List[HealthCheckResult]:
        """Get recent health check history"""
        return self.health_history[-limit:]

    def get_uptime_percentage(self, window_minutes: int = 60) -> float:
        """
        Calculate uptime percentage over time window

        Args:
            window_minutes: Time window in minutes

        Returns:
            Uptime percentage (0-100)
        """
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)

        recent = [r for r in self.health_history if r.timestamp is not None and r.timestamp >= cutoff]

        if not recent:
            return 0.0

        healthy_count = sum(1 for r in recent if r.is_healthy())
        return (healthy_count / len(recent)) * 100.0

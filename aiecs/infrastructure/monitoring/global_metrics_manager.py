"""
Global Metrics Manager

This module provides a singleton ExecutorMetrics instance that can be shared
across all components in the application. It follows the same pattern as
other global managers in the infrastructure layer.

Usage:
    # In main.py startup:
    await initialize_global_metrics()

    # In any component:
    from aiecs.infrastructure.monitoring.global_metrics_manager import get_global_metrics
    metrics = get_global_metrics()
"""

import logging
import asyncio
import os
from typing import Optional, Dict, Any
from .executor_metrics import ExecutorMetrics

logger = logging.getLogger(__name__)

# Global singleton instance
_global_metrics: Optional[ExecutorMetrics] = None
_initialization_lock = asyncio.Lock()
_initialized = False


async def initialize_global_metrics(
    enable_metrics: bool = True,
    metrics_port: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Optional[ExecutorMetrics]:
    """
    Initialize the global ExecutorMetrics instance.

    This should be called once during application startup (in main.py lifespan).

    Args:
        enable_metrics: Whether to enable metrics collection (default: True)
        metrics_port: Port for metrics server (default: from env or 8001)
        config: Additional configuration options

    Returns:
        The initialized ExecutorMetrics instance or None if initialization fails

    Example:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_global_metrics()
            yield
            # Shutdown
            await close_global_metrics()
    """
    global _global_metrics, _initialized

    if _initialized and _global_metrics:
        logger.info("Global metrics already initialized")
        return _global_metrics

    async with _initialization_lock:
        # Double-check after acquiring lock
        if _initialized and _global_metrics:
            return _global_metrics

        try:
            # Determine metrics port
            if metrics_port is None:
                metrics_port = int(os.environ.get("METRICS_PORT", "8001"))

            # Check if metrics should be enabled
            if not enable_metrics:
                enable_metrics = os.environ.get("ENABLE_METRICS", "true").lower() == "true"

            logger.info(f"Initializing global metrics (port: {metrics_port}, enabled: {enable_metrics})...")

            # Create metrics instance
            _global_metrics = ExecutorMetrics(enable_metrics=enable_metrics, metrics_port=metrics_port)

            _initialized = True
            logger.info("✅ Global metrics initialized successfully")
            return _global_metrics

        except Exception as e:
            logger.error(f"❌ Failed to initialize global metrics: {e}")
            logger.warning("Application will continue without metrics (degraded mode)")
            _global_metrics = None
            _initialized = False
            return None


def get_global_metrics() -> Optional[ExecutorMetrics]:
    """
    Get the global ExecutorMetrics instance.

    Returns:
        The global ExecutorMetrics instance or None if not initialized

    Raises:
        RuntimeError: If metrics are requested but not initialized

    Example:
        metrics = get_global_metrics()
        if metrics:
            metrics.record_operation('my_operation', 1)
    """
    if _global_metrics is None:
        logger.warning("Global metrics not initialized - call initialize_global_metrics() first")
        return None

    return _global_metrics


async def close_global_metrics():
    """
    Close the global metrics instance.

    This should be called during application shutdown.
    """
    global _global_metrics, _initialized

    if _global_metrics:
        try:
            # ExecutorMetrics doesn't have a close method, but we can clean up
            logger.info("Closing global metrics...")
            _global_metrics = None
            _initialized = False
            logger.info("✅ Global metrics closed successfully")
        except Exception as e:
            logger.error(f"❌ Error closing global metrics: {e}")


def is_metrics_initialized() -> bool:
    """
    Check if global metrics are initialized.

    Returns:
        True if metrics are initialized, False otherwise
    """
    return _initialized and _global_metrics is not None


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get a summary of the global metrics status.

    Returns:
        Dictionary containing metrics status information
    """
    if not is_metrics_initialized():
        return {
            "initialized": False,
            "message": "Global metrics not initialized",
        }

    if _global_metrics is None:
        return {
            "initialized": False,
            "message": "Global metrics not initialized",
        }
    try:
        return _global_metrics.get_metrics_summary()
    except Exception as e:
        return {
            "initialized": True,
            "error": str(e),
            "message": "Failed to get metrics summary",
        }


# Convenience functions for common operations
def record_operation(
    operation_type: str,
    success: bool = True,
    duration: Optional[float] = None,
    **kwargs,
):
    """Record an operation using global metrics."""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_operation(operation_type, success, duration, **kwargs)


def record_duration(operation: str, duration: float, labels: Optional[Dict[str, str]] = None):
    """Record operation duration using global metrics."""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_duration(operation, duration, labels)


def record_operation_success(operation: str, labels: Optional[Dict[str, str]] = None):
    """Record operation success using global metrics."""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_operation_success(operation, labels)


def record_operation_failure(operation: str, error_type: str, labels: Optional[Dict[str, str]] = None):
    """Record operation failure using global metrics."""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_operation_failure(operation, error_type, labels)


def record_retry(operation: str, attempt_number: int):
    """Record retry using global metrics."""
    metrics = get_global_metrics()
    if metrics:
        metrics.record_retry(operation, attempt_number)

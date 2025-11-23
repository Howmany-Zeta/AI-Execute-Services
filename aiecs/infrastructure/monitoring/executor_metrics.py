import logging
import functools
from typing import Dict, Optional, Any
from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)


class ExecutorMetrics:
    """
    Specialized handler for executor performance monitoring and metrics collection
    """

    def __init__(self, enable_metrics: bool = True, metrics_port: int = 8001):
        self.enable_metrics = enable_metrics
        self.metrics_port = metrics_port
        self.metrics: Dict[str, Any] = {}

        if self.enable_metrics:
            self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        try:
            start_http_server(self.metrics_port)
            self.metrics = {
                "intent_latency": Histogram("intent_latency_seconds", "Latency of intent parsing"),
                "intent_success": Counter(
                    "intent_success_total",
                    "Number of successful intent parsings",
                ),
                "intent_retries": Counter("intent_retries_total", "Number of intent parsing retries"),
                "plan_latency": Histogram("plan_latency_seconds", "Latency of task planning"),
                "plan_success": Counter("plan_success_total", "Number of successful plans"),
                "plan_retries": Counter("plan_retries_total", "Number of plan retries"),
                "execute_latency": Histogram(
                    "execute_latency_seconds",
                    "Latency of task execution",
                    ["task_type"],
                ),
                "execute_success": Counter(
                    "execute_success_total",
                    "Number of successful executions",
                    ["task_type"],
                ),
                "execute_retries": Counter(
                    "execute_retries_total",
                    "Number of execution retries",
                    ["task_type"],
                ),
            }
            logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")
            self.metrics = {}

    def record_operation_latency(self, operation: str, duration: float):
        """Record operation latency"""
        if not self.enable_metrics or f"{operation}_latency" not in self.metrics:
            return
        self.metrics[f"{operation}_latency"].observe(duration)

    def record_operation_success(self, operation: str, labels: Optional[Dict[str, str]] = None):
        """Record operation success"""
        if not self.enable_metrics or f"{operation}_success" not in self.metrics:
            return
        metric = self.metrics[f"{operation}_success"]
        if labels:
            metric = metric.labels(**labels)
        metric.inc()

    def record_operation_failure(
        self,
        operation: str,
        error_type: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Record operation failure"""
        if not self.enable_metrics:
            return
        # Failure metrics can be added
        logger.error(f"Operation {operation} failed with error type: {error_type}")

    def record_retry(self, operation: str, attempt_number: int):
        """Record retry"""
        if not self.enable_metrics or f"{operation}_retries" not in self.metrics:
            return
        if attempt_number > 1:
            self.metrics[f"{operation}_retries"].inc()

    def with_metrics(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """Monitoring decorator"""

        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.metrics or f"{metric_name}_latency" not in self.metrics:
                    return await func(*args, **kwargs)

                labels_dict = labels or {}
                metric = self.metrics[f"{metric_name}_latency"]
                if labels:
                    metric = metric.labels(**labels_dict)

                with metric.time():
                    try:
                        result = await func(*args, **kwargs)
                        if f"{metric_name}_success" in self.metrics:
                            success_metric = self.metrics[f"{metric_name}_success"]
                            if labels:
                                success_metric = success_metric.labels(**labels_dict)
                            success_metric.inc()
                        return result
                    except Exception as e:
                        logger.error(f"Error in {func.__name__}: {e}")
                        raise

            return wrapper

        return decorator

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        if not self.enable_metrics:
            return {"metrics_enabled": False}

        return {
            "metrics_enabled": True,
            "metrics_port": self.metrics_port,
            "available_metrics": list(self.metrics.keys()),
        }

    def record_operation(
        self,
        operation_type: str,
        success: bool = True,
        duration: Optional[float] = None,
        **kwargs,
    ):
        """Record a general operation for metrics tracking"""
        if not self.enable_metrics:
            return

        try:
            # Record operation success/failure
            if success:
                self.record_operation_success(operation_type, kwargs.get("labels"))
            else:
                error_type = kwargs.get("error_type", "unknown")
                self.record_operation_failure(operation_type, error_type, kwargs.get("labels"))

            # Record operation latency if provided
            if duration is not None:
                self.record_operation_latency(operation_type, duration)

        except Exception as e:
            logger.warning(f"Failed to record operation metrics: {e}")

    def record_duration(
        self,
        operation: str,
        duration: float,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Record operation duration for metrics tracking"""
        if not self.enable_metrics:
            return

        try:
            self.record_operation_latency(operation, duration)
        except Exception as e:
            logger.warning(f"Failed to record duration metrics: {e}")

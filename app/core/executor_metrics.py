import logging
import functools
from typing import Dict, Optional, Any
from prometheus_client import Counter, Histogram, start_http_server

logger = logging.getLogger(__name__)


class ExecutorMetrics:
    """
    专门处理执行器的性能监控和指标收集
    """

    def __init__(self, enable_metrics: bool = True, metrics_port: int = 8001):
        self.enable_metrics = enable_metrics
        self.metrics_port = metrics_port
        self.metrics: Dict[str, Any] = {}

        if self.enable_metrics:
            self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """初始化 Prometheus 指标"""
        try:
            start_http_server(self.metrics_port)
            self.metrics = {
                "intent_latency": Histogram("intent_latency_seconds", "Latency of intent parsing"),
                "intent_success": Counter("intent_success_total", "Number of successful intent parsings"),
                "intent_retries": Counter("intent_retries_total", "Number of intent parsing retries"),
                "plan_latency": Histogram("plan_latency_seconds", "Latency of task planning"),
                "plan_success": Counter("plan_success_total", "Number of successful plans"),
                "plan_retries": Counter("plan_retries_total", "Number of plan retries"),
                "execute_latency": Histogram("execute_latency_seconds", "Latency of task execution", ["task_type"]),
                "execute_success": Counter("execute_success_total", "Number of successful executions", ["task_type"]),
                "execute_retries": Counter("execute_retries_total", "Number of execution retries", ["task_type"]),
            }
            logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")
            self.metrics = {}

    def record_operation_latency(self, operation: str, duration: float):
        """记录操作延迟"""
        if not self.enable_metrics or f"{operation}_latency" not in self.metrics:
            return
        self.metrics[f"{operation}_latency"].observe(duration)

    def record_operation_success(self, operation: str, labels: Optional[Dict[str, str]] = None):
        """记录操作成功"""
        if not self.enable_metrics or f"{operation}_success" not in self.metrics:
            return
        metric = self.metrics[f"{operation}_success"]
        if labels:
            metric = metric.labels(**labels)
        metric.inc()

    def record_operation_failure(self, operation: str, error_type: str, labels: Optional[Dict[str, str]] = None):
        """记录操作失败"""
        if not self.enable_metrics:
            return
        # 可以添加失败指标
        logger.error(f"Operation {operation} failed with error type: {error_type}")

    def record_retry(self, operation: str, attempt_number: int):
        """记录重试"""
        if not self.enable_metrics or f"{operation}_retries" not in self.metrics:
            return
        if attempt_number > 1:
            self.metrics[f"{operation}_retries"].inc()

    def with_metrics(self, metric_name: str, labels: Optional[Dict[str, str]] = None):
        """监控装饰器"""
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
        """获取指标摘要"""
        if not self.enable_metrics:
            return {"metrics_enabled": False}

        return {
            "metrics_enabled": True,
            "metrics_port": self.metrics_port,
            "available_metrics": list(self.metrics.keys())
        }

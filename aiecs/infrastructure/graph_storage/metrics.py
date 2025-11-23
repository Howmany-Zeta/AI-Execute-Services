"""
Monitoring Metrics for Graph Storage

Provides metrics collection and export for production monitoring,
including query latency, cache hit rates, and resource usage.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Single metric value"""

    name: str
    value: float
    timestamp: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        timestamp_str = self.timestamp.isoformat() if self.timestamp else None
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": timestamp_str,
            "tags": self.tags,
        }


class MetricsCollector:
    """
    Metrics collector for graph storage operations

    Collects and aggregates metrics for monitoring systems.

    Example:
        ```python
        collector = MetricsCollector()

        # Record metrics
        collector.record_latency("get_entity", 12.5)
        collector.record_cache_hit()
        collector.record_error("connection_error")

        # Export metrics
        metrics = collector.get_metrics()
        ```
    """

    def __init__(self, window_seconds: int = 300):
        """
        Initialize metrics collector

        Args:
            window_seconds: Time window for metric aggregation
        """
        self.window_seconds = window_seconds

        # Latency metrics
        self.latency_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Counter metrics
        self.counters: Dict[str, int] = defaultdict(int)

        # Cache metrics
        self.cache_hits = 0
        self.cache_misses = 0

        # Error metrics
        self.error_counts: Dict[str, int] = defaultdict(int)

        # Resource metrics
        self.resource_metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def record_latency(
        self,
        operation: str,
        latency_ms: float,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record operation latency

        Args:
            operation: Operation name
            latency_ms: Latency in milliseconds
            tags: Optional tags for the metric
        """
        self.latency_metrics[operation].append(
            {
                "value": latency_ms,
                "timestamp": datetime.utcnow(),
                "tags": tags or {},
            }
        )

    def record_cache_hit(self) -> None:
        """Record a cache hit"""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record a cache miss"""
        self.cache_misses += 1

    def record_error(self, error_type: str) -> None:
        """
        Record an error

        Args:
            error_type: Type of error
        """
        self.error_counts[error_type] += 1

    def record_counter(self, name: str, value: int = 1) -> None:
        """
        Record a counter metric

        Args:
            name: Counter name
            value: Counter increment
        """
        self.counters[name] += value

    def record_resource_metric(self, name: str, value: float) -> None:
        """
        Record a resource metric (e.g., memory, connections)

        Args:
            name: Metric name
            value: Metric value
        """
        self.resource_metrics[name].append({"value": value, "timestamp": datetime.utcnow()})

    def get_cache_hit_rate(self) -> float:
        """
        Get cache hit rate

        Returns:
            Cache hit rate (0.0 to 1.0)
        """
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def get_latency_stats(self, operation: str) -> Dict[str, float]:
        """
        Get latency statistics for an operation

        Args:
            operation: Operation name

        Returns:
            Dictionary with min, max, avg, p50, p95, p99
        """
        latencies = self.latency_metrics.get(operation, deque())
        if not latencies:
            return {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "count": 0,
            }

        values = [m["value"] for m in latencies]
        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / count,
            "p50": sorted_values[int(count * 0.50)] if count > 0 else 0.0,
            "p95": sorted_values[int(count * 0.95)] if count > 0 else 0.0,
            "p99": sorted_values[int(count * 0.99)] if count > 0 else 0.0,
            "count": count,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics in a format suitable for monitoring systems

        Returns:
            Dictionary with all metrics
        """
        # Aggregate latency metrics
        latency_stats = {}
        for operation in self.latency_metrics:
            latency_stats[operation] = self.get_latency_stats(operation)

        # Calculate cache metrics
        cache_total = self.cache_hits + self.cache_misses
        cache_metrics = {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "total": cache_total,
            "hit_rate": self.get_cache_hit_rate(),
        }

        # Resource metrics (average over window)
        resource_avgs = {}
        for name, values in self.resource_metrics.items():
            if values:
                recent = [v["value"] for v in values if (datetime.utcnow() - v["timestamp"]).total_seconds() <= self.window_seconds]
                if recent:
                    resource_avgs[name] = sum(recent) / len(recent)

        return {
            "latency": latency_stats,
            "cache": cache_metrics,
            "counters": dict(self.counters),
            "errors": dict(self.error_counts),
            "resources": resource_avgs,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def reset(self) -> None:
        """Reset all metrics"""
        self.latency_metrics.clear()
        self.counters.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.error_counts.clear()
        self.resource_metrics.clear()
        logger.info("Metrics reset")


class MetricsExporter:
    """
    Export metrics to monitoring systems

    Supports Prometheus, StatsD, and custom formats.

    Example:
        ```python
        exporter = MetricsExporter(collector)

        # Export to Prometheus format
        prometheus_metrics = exporter.to_prometheus()

        # Export to StatsD format
        statsd_metrics = exporter.to_statsd()
        ```
    """

    def __init__(self, collector: MetricsCollector):
        """
        Initialize metrics exporter

        Args:
            collector: Metrics collector instance
        """
        self.collector = collector

    def to_prometheus(self) -> str:
        """
        Export metrics in Prometheus format

        Returns:
            Prometheus metrics text format
        """
        metrics = self.collector.get_metrics()
        lines = []

        # Latency metrics
        for operation, stats in metrics["latency"].items():
            lines.append("# TYPE graph_store_latency_seconds histogram")
            lines.append(f'graph_store_latency_seconds{{operation="{operation}",quantile="0.5"}} {stats["p50"]/1000}')
            lines.append(f'graph_store_latency_seconds{{operation="{operation}",quantile="0.95"}} {stats["p95"]/1000}')
            lines.append(f'graph_store_latency_seconds{{operation="{operation}",quantile="0.99"}} {stats["p99"]/1000}')
            lines.append(f'graph_store_latency_seconds_count{{operation="{operation}"}} {stats["count"]}')
            lines.append(f'graph_store_latency_seconds_sum{{operation="{operation}"}} {stats["avg"] * stats["count"] / 1000}')

        # Cache metrics
        cache = metrics["cache"]
        lines.append("# TYPE graph_store_cache_hits counter")
        lines.append(f'graph_store_cache_hits {cache["hits"]}')
        lines.append("# TYPE graph_store_cache_misses counter")
        lines.append(f'graph_store_cache_misses {cache["misses"]}')
        lines.append("# TYPE graph_store_cache_hit_rate gauge")
        lines.append(f'graph_store_cache_hit_rate {cache["hit_rate"]}')

        # Error metrics
        for error_type, count in metrics["errors"].items():
            lines.append("# TYPE graph_store_errors counter")
            lines.append(f'graph_store_errors{{type="{error_type}"}} {count}')

        # Counter metrics
        for name, value in metrics["counters"].items():
            lines.append("# TYPE graph_store_counter counter")
            lines.append(f'graph_store_counter{{name="{name}"}} {value}')

        return "\n".join(lines)

    def to_statsd(self) -> List[str]:
        """
        Export metrics in StatsD format

        Returns:
            List of StatsD metric strings
        """
        metrics = self.collector.get_metrics()
        lines = []

        # Latency metrics
        for operation, stats in metrics["latency"].items():
            lines.append(f'graph_store.latency.{operation}:{stats["avg"]}|ms')
            lines.append(f'graph_store.latency.{operation}.p95:{stats["p95"]}|ms')
            lines.append(f'graph_store.latency.{operation}.p99:{stats["p99"]}|ms')

        # Cache metrics
        cache = metrics["cache"]
        lines.append(f'graph_store.cache.hits:{cache["hits"]}|c')
        lines.append(f'graph_store.cache.misses:{cache["misses"]}|c')
        lines.append(f'graph_store.cache.hit_rate:{cache["hit_rate"]}|g')

        # Error metrics
        for error_type, count in metrics["errors"].items():
            lines.append(f"graph_store.errors.{error_type}:{count}|c")

        return lines

    def to_dict(self) -> Dict[str, Any]:
        """
        Export metrics as dictionary (for JSON APIs)

        Returns:
            Dictionary with all metrics
        """
        return self.collector.get_metrics()

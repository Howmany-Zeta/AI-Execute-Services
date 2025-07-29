"""
Performance Monitor

Monitors performance metrics and resource usage for execution optimization.
Provides performance analysis and optimization recommendations.
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import uuid
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from ...core.models.execution_models import ExecutionResult, ExecutionStatus
from ...core.models.monitoring_models import (
    MetricType, AlertLevel, PerformanceMetric, PerformanceAlert,
    PerformanceThreshold, ResourceUsage
)

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Performance monitor for tracking execution performance and resource usage.

    This monitor provides:
    - Real-time performance metrics collection
    - Resource usage monitoring
    - Performance threshold alerting
    - Trend analysis and reporting
    - Optimization recommendations
    - Performance bottleneck detection
    """

    def __init__(
        self,
        collection_interval: int = 5,
        max_metrics: int = 10000,
        max_alerts: int = 1000
    ):
        """
        Initialize the performance monitor.

        Args:
            collection_interval: Metrics collection interval in seconds
            max_metrics: Maximum number of metrics to keep in memory
            max_alerts: Maximum number of alerts to keep in memory
        """
        self.collection_interval = collection_interval
        self.max_metrics = max_metrics
        self.max_alerts = max_alerts
        self.logger = logging.getLogger(__name__)

        # Metrics storage
        self._metrics = deque(maxlen=max_metrics)
        self._metrics_by_type = defaultdict(lambda: deque(maxlen=1000))
        self._metrics_by_execution = defaultdict(list)

        # Alerts storage
        self._alerts = deque(maxlen=max_alerts)
        self._active_alerts = {}

        # Thresholds
        self._thresholds = {}
        self._setup_default_thresholds()

        # Resource monitoring
        self._resource_history = deque(maxlen=1000)
        self._baseline_resources = None

        # Performance tracking
        self._execution_stats = defaultdict(list)
        self._component_stats = defaultdict(list)

        # Monitoring state
        self._monitoring_active = False
        self._monitoring_task = None
        self._collection_task = None

        # Alert handlers
        self._alert_handlers = defaultdict(list)

    async def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if self._monitoring_active:
            return

        self._monitoring_active = True

        # Start monitoring tasks
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self._collection_task = asyncio.create_task(self._collection_loop())

        # Collect baseline resource usage
        await self._collect_baseline_resources()

        self.logger.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if not self._monitoring_active:
            return

        self._monitoring_active = False

        # Cancel monitoring tasks
        if self._monitoring_task:
            self._monitoring_task.cancel()
        if self._collection_task:
            self._collection_task.cancel()

        # Wait for tasks to complete
        for task in [self._monitoring_task, self._collection_task]:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.logger.info("Performance monitoring stopped")

    async def record_metric(
        self,
        metric_type: MetricType,
        value: float,
        unit: str,
        execution_id: Optional[str] = None,
        component: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a performance metric.

        Args:
            metric_type: Type of metric
            value: Metric value
            unit: Unit of measurement
            execution_id: Associated execution ID
            component: Component that generated the metric
            tags: Additional metric tags
        """
        metric = PerformanceMetric(
            metric_id=str(uuid.uuid4()),
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            execution_id=execution_id,
            component=component,
            tags=tags or {}
        )

        # Store metric
        self._metrics.append(metric)
        self._metrics_by_type[metric_type].append(metric)

        if execution_id:
            self._metrics_by_execution[execution_id].append(metric)

        # Check thresholds
        await self._check_thresholds(metric)

        # Update statistics
        await self._update_statistics(metric)

    async def record_execution_performance(
        self,
        execution_id: str,
        execution_result: ExecutionResult,
        component: Optional[str] = None
    ) -> None:
        """
        Record execution performance metrics.

        Args:
            execution_id: Execution identifier
            execution_result: Execution result
            component: Component that executed the task
        """
        if not execution_result.started_at or not execution_result.completed_at:
            return

        # Calculate execution time
        execution_time = (execution_result.completed_at - execution_result.started_at).total_seconds()

        await self.record_metric(
            metric_type=MetricType.EXECUTION_TIME,
            value=execution_time,
            unit="seconds",
            execution_id=execution_id,
            component=component,
            tags={
                'success': str(execution_result.success),
                'status': execution_result.status.value if hasattr(execution_result.status, 'value') else execution_result.status
            }
        )

        # Record error rate
        error_rate = 0.0 if execution_result.success else 1.0
        await self.record_metric(
            metric_type=MetricType.ERROR_RATE,
            value=error_rate,
            unit="ratio",
            execution_id=execution_id,
            component=component
        )

    async def get_performance_summary(
        self,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get performance summary.

        Args:
            time_window: Time window for metrics (default: last hour)

        Returns:
            Dict[str, Any]: Performance summary
        """
        if time_window is None:
            time_window = timedelta(hours=1)

        cutoff_time = datetime.utcnow() - time_window

        # Filter metrics by time window
        recent_metrics = [m for m in self._metrics if m.timestamp > cutoff_time]

        if not recent_metrics:
            return {
                'time_window': str(time_window),
                'total_metrics': 0,
                'metrics_by_type': {},
                'resource_usage': {},
                'alerts': {'active': 0, 'total': 0}
            }

        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_type[metric.metric_type].append(metric.value)

        # Calculate statistics for each metric type
        type_stats = {}
        for metric_type, values in metrics_by_type.items():
            if values:
                type_stats[metric_type.value] = {
                    'count': len(values),
                    'min': min(values),
                    'max': max(values),
                    'mean': statistics.mean(values),
                    'median': statistics.median(values),
                    'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0
                }

        # Get current resource usage
        current_resources = await self._get_current_resource_usage()

        # Count alerts
        active_alerts = len([a for a in self._alerts if not a.resolved])
        total_alerts = len(self._alerts)

        return {
            'time_window': str(time_window),
            'total_metrics': len(recent_metrics),
            'metrics_by_type': type_stats,
            'resource_usage': {
                'cpu_percent': current_resources.cpu_percent,
                'memory_percent': current_resources.memory_percent,
                'memory_used_mb': current_resources.memory_used_mb,
                'disk_usage_percent': current_resources.disk_usage_percent
            },
            'alerts': {
                'active': active_alerts,
                'total': total_alerts
            }
        }

    async def get_execution_performance(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a specific execution.

        Args:
            execution_id: Execution identifier

        Returns:
            Dict[str, Any]: Execution performance data
        """
        execution_metrics = self._metrics_by_execution.get(execution_id, [])

        if not execution_metrics:
            return {
                'execution_id': execution_id,
                'metrics_count': 0,
                'performance_data': {}
            }

        # Group metrics by type
        metrics_by_type = defaultdict(list)
        for metric in execution_metrics:
            metrics_by_type[metric.metric_type].append(metric.value)

        # Calculate performance data
        performance_data = {}
        for metric_type, values in metrics_by_type.items():
            if values:
                performance_data[metric_type.value] = {
                    'count': len(values),
                    'total': sum(values),
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }

        return {
            'execution_id': execution_id,
            'metrics_count': len(execution_metrics),
            'performance_data': performance_data
        }

    async def get_performance_trends(
        self,
        metric_type: MetricType,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Get performance trends for a specific metric type.

        Args:
            metric_type: Metric type to analyze
            time_window: Time window for analysis

        Returns:
            Dict[str, Any]: Trend analysis data
        """
        if time_window is None:
            time_window = timedelta(hours=24)

        cutoff_time = datetime.utcnow() - time_window

        # Get metrics for the specified type and time window
        metrics = [
            m for m in self._metrics_by_type[metric_type]
            if m.timestamp > cutoff_time
        ]

        if not metrics:
            return {
                'metric_type': metric_type.value,
                'time_window': str(time_window),
                'data_points': 0,
                'trend': 'no_data'
            }

        # Sort by timestamp
        metrics.sort(key=lambda m: m.timestamp)

        # Calculate trend
        values = [m.value for m in metrics]
        timestamps = [m.timestamp for m in metrics]

        # Simple trend calculation (comparing first and last quartiles)
        if len(values) >= 4:
            q1_size = len(values) // 4
            first_quartile = statistics.mean(values[:q1_size])
            last_quartile = statistics.mean(values[-q1_size:])

            if last_quartile > first_quartile * 1.1:
                trend = 'increasing'
            elif last_quartile < first_quartile * 0.9:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'metric_type': metric_type.value,
            'time_window': str(time_window),
            'data_points': len(metrics),
            'trend': trend,
            'first_value': values[0],
            'last_value': values[-1],
            'min_value': min(values),
            'max_value': max(values),
            'average_value': statistics.mean(values),
            'std_deviation': statistics.stdev(values) if len(values) > 1 else 0.0
        }

    async def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get performance optimization recommendations.

        Returns:
            List[Dict[str, Any]]: List of optimization recommendations
        """
        recommendations = []

        # Analyze execution time trends
        exec_time_trend = await self.get_performance_trends(
            MetricType.EXECUTION_TIME,
            timedelta(hours=6)
        )

        if exec_time_trend['trend'] == 'increasing':
            recommendations.append({
                'type': 'performance_degradation',
                'priority': 'high',
                'message': 'Execution times are increasing over time',
                'suggestion': 'Review recent changes and consider performance optimization',
                'metric': 'execution_time'
            })

        # Analyze error rates
        error_rate_metrics = [
            m for m in self._metrics_by_type[MetricType.ERROR_RATE]
            if m.timestamp > datetime.utcnow() - timedelta(hours=1)
        ]

        if error_rate_metrics:
            recent_error_rate = statistics.mean([m.value for m in error_rate_metrics])
            if recent_error_rate > 0.1:  # 10% error rate
                recommendations.append({
                    'type': 'high_error_rate',
                    'priority': 'critical',
                    'message': f'High error rate detected: {recent_error_rate:.1%}',
                    'suggestion': 'Investigate and fix underlying issues causing failures',
                    'metric': 'error_rate'
                })

        # Analyze resource usage
        if self._resource_history:
            recent_resources = list(self._resource_history)[-10:]  # Last 10 measurements
            avg_cpu = statistics.mean([r.cpu_percent for r in recent_resources])
            avg_memory = statistics.mean([r.memory_percent for r in recent_resources])

            if avg_cpu > 80:
                recommendations.append({
                    'type': 'high_cpu_usage',
                    'priority': 'warning',
                    'message': f'High CPU usage detected: {avg_cpu:.1f}%',
                    'suggestion': 'Consider scaling up or optimizing CPU-intensive operations',
                    'metric': 'cpu_usage'
                })

            if avg_memory > 85:
                recommendations.append({
                    'type': 'high_memory_usage',
                    'priority': 'warning',
                    'message': f'High memory usage detected: {avg_memory:.1f}%',
                    'suggestion': 'Consider scaling up or optimizing memory usage',
                    'metric': 'memory_usage'
                })

        return recommendations

    def set_threshold(
        self,
        metric_type: MetricType,
        warning_threshold: float,
        critical_threshold: float,
        comparison: str = "greater_than"
    ) -> None:
        """
        Set performance threshold for alerting.

        Args:
            metric_type: Metric type to set threshold for
            warning_threshold: Warning threshold value
            critical_threshold: Critical threshold value
            comparison: Comparison operator (greater_than, less_than, equal_to)
        """
        self._thresholds[metric_type] = PerformanceThreshold(
            metric_type=metric_type,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            comparison=comparison
        )

        self.logger.info(f"Set threshold for {metric_type.value}: warning={warning_threshold}, critical={critical_threshold}")

    def register_alert_handler(
        self,
        alert_level: AlertLevel,
        handler: Callable[[PerformanceAlert], None]
    ) -> None:
        """
        Register an alert handler.

        Args:
            alert_level: Alert level to handle
            handler: Handler function
        """
        self._alert_handlers[alert_level].append(handler)
        self.logger.info(f"Registered alert handler for {alert_level.value}")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                # Check for performance issues
                await self._analyze_performance_issues()

                # Clean up old data
                await self._cleanup_old_data()

                # Sleep for monitoring interval
                await asyncio.sleep(30)  # 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)

    async def _collection_loop(self) -> None:
        """Resource collection loop."""
        while self._monitoring_active:
            try:
                # Collect resource usage
                await self._collect_resource_usage()

                # Sleep for collection interval
                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Collection loop error: {e}")
                await asyncio.sleep(5)

    async def _collect_resource_usage(self) -> None:
        """Collect current resource usage."""
        try:
            # Get system resource usage
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Get network I/O (simplified)
            network = psutil.net_io_counters()
            network_io = network.bytes_sent + network.bytes_recv

            # Get process information
            process_count = len(psutil.pids())

            # Get current process thread count
            current_process = psutil.Process()
            thread_count = current_process.num_threads()

            resource_usage = ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_io_bytes=network_io,
                process_count=process_count,
                thread_count=thread_count
            )

            self._resource_history.append(resource_usage)

            # Record as metrics
            await self.record_metric(MetricType.CPU_USAGE, cpu_percent, "percent", component="system")
            await self.record_metric(MetricType.MEMORY_USAGE, memory.percent, "percent", component="system")

        except Exception as e:
            self.logger.error(f"Failed to collect resource usage: {e}")

    async def _collect_baseline_resources(self) -> None:
        """Collect baseline resource usage."""
        try:
            await self._collect_resource_usage()
            if self._resource_history:
                self._baseline_resources = self._resource_history[-1]
                self.logger.info("Baseline resource usage collected")
        except Exception as e:
            self.logger.error(f"Failed to collect baseline resources: {e}")

    async def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check if metric exceeds thresholds."""
        threshold = self._thresholds.get(metric.metric_type)
        if not threshold or not threshold.enabled:
            return

        # Get recent values for window-based comparison
        recent_metrics = [
            m for m in self._metrics_by_type[metric.metric_type]
            if m.timestamp > datetime.utcnow() - timedelta(minutes=5)
        ][-threshold.window_size:]

        if len(recent_metrics) < threshold.window_size:
            return

        # Calculate average value in window
        avg_value = statistics.mean([m.value for m in recent_metrics])

        # Check thresholds
        alert_level = None
        threshold_value = None

        if threshold.comparison == "greater_than":
            if avg_value > threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif avg_value > threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold
        elif threshold.comparison == "less_than":
            if avg_value < threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif avg_value < threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold

        if alert_level:
            await self._create_alert(
                alert_level=alert_level,
                metric_type=metric.metric_type,
                message=f"{metric.metric_type.value} threshold exceeded",
                value=avg_value,
                threshold=threshold_value,
                execution_id=metric.execution_id,
                component=metric.component
            )

    async def _create_alert(
        self,
        alert_level: AlertLevel,
        metric_type: MetricType,
        message: str,
        value: float,
        threshold: float,
        execution_id: Optional[str] = None,
        component: Optional[str] = None
    ) -> None:
        """Create a performance alert."""
        alert = PerformanceAlert(
            alert_id=str(uuid.uuid4()),
            alert_level=alert_level,
            metric_type=metric_type,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=datetime.utcnow(),
            execution_id=execution_id,
            component=component
        )

        # Store alert
        self._alerts.append(alert)
        self._active_alerts[alert.alert_id] = alert

        # Call alert handlers
        for handler in self._alert_handlers[alert_level]:
            try:
                await asyncio.get_event_loop().run_in_executor(None, handler, alert)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {e}")

        self.logger.warning(f"Performance alert: {message} (value={value}, threshold={threshold})")

    async def _update_statistics(self, metric: PerformanceMetric) -> None:
        """Update performance statistics."""
        if metric.execution_id:
            self._execution_stats[metric.execution_id].append(metric.value)

        if metric.component:
            self._component_stats[metric.component].append(metric.value)

    async def _analyze_performance_issues(self) -> None:
        """Analyze for performance issues."""
        # This could include more sophisticated analysis
        # For now, just check for basic patterns
        pass

    async def _cleanup_old_data(self) -> None:
        """Clean up old performance data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Clean up execution-specific metrics
        for execution_id in list(self._metrics_by_execution.keys()):
            metrics = self._metrics_by_execution[execution_id]
            self._metrics_by_execution[execution_id] = [
                m for m in metrics if m.timestamp > cutoff_time
            ]

            if not self._metrics_by_execution[execution_id]:
                del self._metrics_by_execution[execution_id]

    async def _get_current_resource_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        if self._resource_history:
            return self._resource_history[-1]

        # Fallback: collect current usage
        await self._collect_resource_usage()
        return self._resource_history[-1] if self._resource_history else ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_mb=0.0,
            memory_available_mb=0.0,
            disk_usage_percent=0.0,
            network_io_bytes=0,
            process_count=0,
            thread_count=0
        )

    def _setup_default_thresholds(self) -> None:
        """Setup default performance thresholds."""
        # Execution time thresholds
        self.set_threshold(
            MetricType.EXECUTION_TIME,
            warning_threshold=300.0,  # 5 minutes
            critical_threshold=600.0,  # 10 minutes
            comparison="greater_than"
        )

        # Error rate thresholds
        self.set_threshold(
            MetricType.ERROR_RATE,
            warning_threshold=0.05,  # 5%
            critical_threshold=0.10,  # 10%
            comparison="greater_than"
        )

        # CPU usage thresholds
        self.set_threshold(
            MetricType.CPU_USAGE,
            warning_threshold=80.0,  # 80%
            critical_threshold=95.0,  # 95%
            comparison="greater_than"
        )

        # Memory usage thresholds
        self.set_threshold(
            MetricType.MEMORY_USAGE,
            warning_threshold=85.0,  # 85%
            critical_threshold=95.0,  # 95%
            comparison="greater_than"
        )

"""
Detailed Metrics and Health Monitoring for API Providers

This module provides comprehensive performance tracking including:
- Response time percentiles
- Data volume statistics
- Error type distribution
- Rate limiting events
- Cache hit rates
- Overall health scoring
"""

import logging
from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional, cast

logger = logging.getLogger(__name__)

# Type definitions for metrics structure
MetricsDict = Dict[str, Any]
RequestsMetrics = Dict[str, int]
PerformanceMetrics = Dict[str, Any]
DataVolumeMetrics = Dict[str, Any]
ErrorsMetrics = Dict[str, Any]
RateLimitingMetrics = Dict[str, Any]
TimestampsMetrics = Dict[str, Optional[str]]


class DetailedMetrics:
    """
    Tracks detailed performance metrics for API providers.

    Provides comprehensive monitoring including response times, data volumes,
    error patterns, and overall health scoring.
    """

    def __init__(self, max_response_times: int = 100):
        """
        Initialize metrics tracker.

        Args:
            max_response_times: Maximum number of response times to keep in memory
        """
        self.max_response_times = max_response_times
        self.lock = Lock()

        # Request metrics with proper type annotations
        self.metrics: Dict[str, MetricsDict] = {
            "requests": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "cached": 0,
            },
            "performance": {
                "response_times": [],  # Last N response times
                "avg_response_time_ms": 0.0,
                "p50_response_time_ms": 0.0,
                "p95_response_time_ms": 0.0,
                "p99_response_time_ms": 0.0,
                "min_response_time_ms": 0.0,
                "max_response_time_ms": 0.0,
            },
            "data_volume": {
                "total_records_fetched": 0,
                "total_bytes_transferred": 0,
                "avg_records_per_request": 0.0,
                "avg_bytes_per_request": 0.0,
            },
            "errors": {
                "by_type": defaultdict(int),  # {error_type: count}
                "recent_errors": [],  # Last 10 errors with details
            },
            "rate_limiting": {
                "throttled_requests": 0,
                "total_wait_time_ms": 0.0,
                "avg_wait_time_ms": 0.0,
            },
            "timestamps": {
                "first_request": None,
                "last_request": None,
                "last_success": None,
                "last_failure": None,
            },
        }

    def record_request(
        self,
        success: bool,
        response_time_ms: float,
        record_count: int = 0,
        bytes_transferred: int = 0,
        cached: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """
        Record a request with its metrics.

        Args:
            success: Whether the request was successful
            response_time_ms: Response time in milliseconds
            record_count: Number of records returned
            bytes_transferred: Bytes transferred in the response
            cached: Whether the response was cached
            error_type: Type of error if failed (e.g., 'timeout', 'auth', 'rate_limit')
            error_message: Error message if failed
        """
        with self.lock:
            now = datetime.utcnow().isoformat()

            # Get typed references to nested dictionaries
            requests = cast(RequestsMetrics, self.metrics["requests"])
            timestamps = cast(TimestampsMetrics, self.metrics["timestamps"])
            performance = cast(PerformanceMetrics, self.metrics["performance"])
            data_volume = cast(DataVolumeMetrics, self.metrics["data_volume"])
            errors = cast(ErrorsMetrics, self.metrics["errors"])

            # Update request counts
            requests["total"] += 1
            if success:
                requests["successful"] += 1
                timestamps["last_success"] = now
            else:
                requests["failed"] += 1
                timestamps["last_failure"] = now

            if cached:
                requests["cached"] += 1

            # Update timestamps
            if timestamps["first_request"] is None:
                timestamps["first_request"] = now
            timestamps["last_request"] = now

            # Update performance metrics
            response_times = cast(List[float], performance["response_times"])
            response_times.append(response_time_ms)
            if len(response_times) > self.max_response_times:
                response_times.pop(0)

            # Calculate percentiles
            self._calculate_percentiles()

            # Update data volume metrics
            data_volume["total_records_fetched"] += record_count
            data_volume["total_bytes_transferred"] += bytes_transferred

            total_requests = requests["total"]
            if total_requests > 0:
                data_volume["avg_records_per_request"] = data_volume["total_records_fetched"] / total_requests
                data_volume["avg_bytes_per_request"] = data_volume["total_bytes_transferred"] / total_requests

            # Record errors
            if not success and error_type:
                by_type = cast(Dict[str, int], errors["by_type"])
                by_type[error_type] += 1

                error_entry = {
                    "type": error_type,
                    "message": error_message or "Unknown error",
                    "timestamp": now,
                    "response_time_ms": response_time_ms,
                }

                recent_errors = cast(List[Dict[str, Any]], errors["recent_errors"])
                recent_errors.append(error_entry)
                if len(recent_errors) > 10:
                    recent_errors.pop(0)

    def record_rate_limit_wait(self, wait_time_ms: float):
        """
        Record a rate limit wait event.

        Args:
            wait_time_ms: Time waited in milliseconds
        """
        with self.lock:
            rate_limiting = cast(RateLimitingMetrics, self.metrics["rate_limiting"])
            rate_limiting["throttled_requests"] += 1
            rate_limiting["total_wait_time_ms"] += wait_time_ms

            throttled = rate_limiting["throttled_requests"]
            if throttled > 0:
                rate_limiting["avg_wait_time_ms"] = rate_limiting["total_wait_time_ms"] / throttled

    def _calculate_percentiles(self):
        """Calculate response time percentiles"""
        performance = cast(PerformanceMetrics, self.metrics["performance"])
        response_times = cast(List[float], performance["response_times"])
        times = sorted(response_times)
        if not times:
            return

        n = len(times)
        performance["avg_response_time_ms"] = sum(times) / n
        performance["min_response_time_ms"] = times[0]
        performance["max_response_time_ms"] = times[-1]
        performance["p50_response_time_ms"] = times[n // 2]
        performance["p95_response_time_ms"] = times[int(n * 0.95)]
        performance["p99_response_time_ms"] = times[min(int(n * 0.99), n - 1)]

    def _calculate_health_score_unlocked(self) -> float:
        """
        Calculate health score without acquiring lock (internal use only).
        Must be called while holding self.lock.
        """
        requests = cast(RequestsMetrics, self.metrics["requests"])
        performance = cast(PerformanceMetrics, self.metrics["performance"])
        errors = cast(ErrorsMetrics, self.metrics["errors"])

        total = requests["total"]
        if total == 0:
            return 1.0

        # Success rate score (40%)
        success_rate = requests["successful"] / total
        success_score = success_rate * 0.4

        # Performance score (30%)
        avg_time = cast(float, performance["avg_response_time_ms"])
        # Assume < 200ms is excellent, > 2000ms is poor
        if avg_time < 200:
            performance_score = 0.3
        elif avg_time > 2000:
            performance_score = 0.0
        else:
            performance_score = max(0, min(1, (2000 - avg_time) / 1800)) * 0.3

        # Cache hit rate score (20%)
        cache_rate = requests["cached"] / total
        cache_score = cache_rate * 0.2

        # Error diversity score (10%) - fewer error types is better
        by_type = cast(Dict[str, int], errors["by_type"])
        error_types = len(by_type)
        error_score = max(0, (5 - error_types) / 5) * 0.1

        return success_score + performance_score + cache_score + error_score

    def get_health_score(self) -> float:
        """
        Calculate overall health score (0-1).

        The health score considers:
        - Success rate (40%)
        - Performance (30%)
        - Cache hit rate (20%)
        - Error diversity (10%)

        Returns:
            Health score between 0 and 1
        """
        with self.lock:
            return self._calculate_health_score_unlocked()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get all metrics as a dictionary.

        Returns:
            Complete metrics dictionary
        """
        with self.lock:
            # Convert defaultdict to regular dict for JSON serialization
            requests_dict: Dict[str, int] = dict(self.metrics["requests"])  # type: ignore[arg-type]
            performance_dict: Dict[str, Any] = dict(self.metrics["performance"])  # type: ignore[arg-type]
            data_volume_dict: Dict[str, Any] = dict(self.metrics["data_volume"])  # type: ignore[arg-type]
            errors_by_type: Dict[str, int] = dict(self.metrics["errors"]["by_type"])  # type: ignore[arg-type]
            recent_errors_list: List[Dict[str, Any]] = list(self.metrics["errors"]["recent_errors"])  # type: ignore[arg-type]
            rate_limiting_dict: Dict[str, Any] = dict(self.metrics["rate_limiting"])  # type: ignore[arg-type]
            timestamps_dict: Dict[str, Optional[str]] = dict(self.metrics["timestamps"])  # type: ignore[arg-type]

            stats: Dict[str, Any] = {
                "requests": requests_dict,
                "performance": performance_dict,
                "data_volume": data_volume_dict,
                "errors": {
                    "by_type": errors_by_type,
                    "recent_errors": recent_errors_list,
                },
                "rate_limiting": rate_limiting_dict,
                "timestamps": timestamps_dict,
                "health_score": self.get_health_score(),
            }

            # Remove response_times array to keep output clean
            stats["performance"] = {k: v for k, v in stats["performance"].items() if k != "response_times"}

            return stats

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a concise summary of key metrics.

        Returns:
            Summary dictionary with key metrics
        """
        with self.lock:
            requests = cast(RequestsMetrics, self.metrics["requests"])
            performance = cast(PerformanceMetrics, self.metrics["performance"])
            errors = cast(ErrorsMetrics, self.metrics["errors"])

            total = requests["total"]
            if total == 0:
                return {"status": "no_activity", "health_score": 1.0}

            success_rate = requests["successful"] / total
            cache_hit_rate = requests["cached"] / total
            # Use unlocked version to avoid deadlock
            health_score = self._calculate_health_score_unlocked()

            return {
                "status": "healthy" if health_score > 0.7 else "degraded",
                "health_score": round(health_score, 3),
                "total_requests": total,
                "success_rate": round(success_rate, 3),
                "cache_hit_rate": round(cache_hit_rate, 3),
                "avg_response_time_ms": round(cast(float, performance["avg_response_time_ms"]), 2),
                "p95_response_time_ms": round(cast(float, performance["p95_response_time_ms"]), 2),
                "total_errors": requests["failed"],
                "error_types": len(cast(Dict[str, int], errors["by_type"])),
            }

    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.__init__(self.max_response_times)

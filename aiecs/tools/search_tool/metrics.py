"""
Enhanced Metrics Collection

This module provides comprehensive performance and quality metrics tracking
for the search tool.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class EnhancedMetrics:
    """Comprehensive metrics collection for search operations"""

    def __init__(self):
        """Initialize enhanced metrics"""
        self.metrics = {
            # Basic counters
            "requests": {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "cached": 0,
            },
            # Performance metrics
            "performance": {
                "response_times_ms": [],  # Recent 100
                "avg_response_time_ms": 0,
                "p50_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "slowest_query": None,
                "fastest_query": None,
            },
            # Quality metrics
            "quality": {
                "avg_results_per_query": 0,
                "avg_quality_score": 0,
                "high_quality_results_pct": 0,
                "queries_with_no_results": 0,
            },
            # Error analysis
            "errors": {
                "by_type": {},
                "recent_errors": [],  # Recent 10
                "error_rate": 0.0,
            },
            # Cache efficiency
            "cache": {
                "hit_rate": 0.0,
                "total_hits": 0,
                "total_misses": 0,
                "avg_age_seconds": 0,
            },
            # Rate limiting
            "rate_limiting": {
                "throttled_requests": 0,
                "avg_wait_time_ms": 0,
                "quota_utilization_pct": 0,
            },
            # Query patterns
            "patterns": {
                "top_query_types": {},
                "top_domains_returned": {},
                "avg_query_length": 0,
            },
        }

    def record_search(
        self,
        query: str,
        search_type: str,
        results: List[Dict[str, Any]],
        response_time_ms: float,
        cached: bool = False,
        error: Optional[Exception] = None,
    ):
        """
        Record a search operation.

        Args:
            query: Search query
            search_type: Type of search performed
            results: Search results
            response_time_ms: Response time in milliseconds
            cached: Whether result was from cache
            error: Error if search failed
        """
        # Update request counts
        self.metrics["requests"]["total"] += 1

        if error:
            self.metrics["requests"]["failed"] += 1
            self._record_error(error)
        else:
            self.metrics["requests"]["successful"] += 1

        if cached:
            self.metrics["requests"]["cached"] += 1
            self.metrics["cache"]["total_hits"] += 1
        else:
            self.metrics["cache"]["total_misses"] += 1

        # Update performance metrics
        self.metrics["performance"]["response_times_ms"].append(response_time_ms)
        if len(self.metrics["performance"]["response_times_ms"]) > 100:
            self.metrics["performance"]["response_times_ms"].pop(0)

        self._update_percentiles()

        # Track slowest/fastest queries
        if not self.metrics["performance"]["slowest_query"] or response_time_ms > self.metrics["performance"]["slowest_query"]["time"]:
            self.metrics["performance"]["slowest_query"] = {
                "query": query,
                "time": response_time_ms,
                "type": search_type,
            }

        if not self.metrics["performance"]["fastest_query"] or response_time_ms < self.metrics["performance"]["fastest_query"]["time"]:
            self.metrics["performance"]["fastest_query"] = {
                "query": query,
                "time": response_time_ms,
                "type": search_type,
            }

        # Update quality metrics
        if results:
            result_count = len(results)

            # Calculate average quality
            avg_quality = sum(r.get("_quality", {}).get("quality_score", 0.5) for r in results) / result_count

            # Count high quality results
            high_quality_count = sum(1 for r in results if r.get("_quality", {}).get("quality_score", 0) > 0.75)

            # Update running averages
            total = self.metrics["requests"]["successful"]

            current_avg_results = self.metrics["quality"]["avg_results_per_query"]
            self.metrics["quality"]["avg_results_per_query"] = (current_avg_results * (total - 1) + result_count) / total

            current_avg_quality = self.metrics["quality"]["avg_quality_score"]
            self.metrics["quality"]["avg_quality_score"] = (current_avg_quality * (total - 1) + avg_quality) / total

            current_high_pct = self.metrics["quality"]["high_quality_results_pct"]
            high_pct = high_quality_count / result_count
            self.metrics["quality"]["high_quality_results_pct"] = (current_high_pct * (total - 1) + high_pct) / total
        else:
            self.metrics["quality"]["queries_with_no_results"] += 1

        # Update query patterns
        query_type = self._detect_query_type(query)
        self.metrics["patterns"]["top_query_types"][query_type] = self.metrics["patterns"]["top_query_types"].get(query_type, 0) + 1

        # Track returned domains
        for result in results:
            domain = result.get("displayLink", "unknown")
            self.metrics["patterns"]["top_domains_returned"][domain] = self.metrics["patterns"]["top_domains_returned"].get(domain, 0) + 1

        # Update average query length
        total = self.metrics["requests"]["total"]
        current_avg_len = self.metrics["patterns"]["avg_query_length"]
        self.metrics["patterns"]["avg_query_length"] = (current_avg_len * (total - 1) + len(query.split())) / total

        # Update cache hit rate
        total_cache_requests = self.metrics["cache"]["total_hits"] + self.metrics["cache"]["total_misses"]
        if total_cache_requests > 0:
            self.metrics["cache"]["hit_rate"] = self.metrics["cache"]["total_hits"] / total_cache_requests

    def _update_percentiles(self):
        """Update response time percentiles"""
        times = sorted(self.metrics["performance"]["response_times_ms"])
        if not times:
            return

        self.metrics["performance"]["avg_response_time_ms"] = sum(times) / len(times)
        self.metrics["performance"]["p50_response_time_ms"] = times[len(times) // 2]
        self.metrics["performance"]["p95_response_time_ms"] = times[int(len(times) * 0.95)]
        self.metrics["performance"]["p99_response_time_ms"] = times[int(len(times) * 0.99)]

    def _record_error(self, error: Exception):
        """Record an error"""
        error_type = type(error).__name__

        self.metrics["errors"]["by_type"][error_type] = self.metrics["errors"]["by_type"].get(error_type, 0) + 1

        self.metrics["errors"]["recent_errors"].append(
            {
                "type": error_type,
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        if len(self.metrics["errors"]["recent_errors"]) > 10:
            self.metrics["errors"]["recent_errors"].pop(0)

        # Update error rate
        total = self.metrics["requests"]["total"]
        failed = self.metrics["requests"]["failed"]
        self.metrics["errors"]["error_rate"] = failed / total if total > 0 else 0

    def _detect_query_type(self, query: str) -> str:
        """Detect query type from query text"""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["how to", "tutorial", "guide"]):
            return "how_to"
        elif any(kw in query_lower for kw in ["what is", "define", "meaning"]):
            return "definition"
        elif any(kw in query_lower for kw in ["vs", "versus", "compare"]):
            return "comparison"
        elif any(kw in query_lower for kw in ["latest", "news", "recent"]):
            return "news"
        else:
            return "general"

    def get_health_score(self) -> float:
        """
        Calculate system health score (0-1).

        Returns:
            Health score based on success rate, performance, quality, and cache efficiency
        """
        total = self.metrics["requests"]["total"]
        if total == 0:
            return 1.0

        # Success rate score (40%)
        success_rate = self.metrics["requests"]["successful"] / total
        success_score = success_rate * 0.4

        # Performance score (25%)
        avg_time = self.metrics["performance"]["avg_response_time_ms"]
        # < 500ms excellent, > 3000ms poor
        performance_score = max(0, min(1, (3000 - avg_time) / 2500)) * 0.25

        # Quality score (25%)
        quality_score = self.metrics["quality"]["avg_quality_score"] * 0.25

        # Cache efficiency score (10%)
        cache_score = self.metrics["cache"]["hit_rate"] * 0.1

        return success_score + performance_score + quality_score + cache_score

    def generate_report(self) -> str:
        """
        Generate human-readable metrics report.

        Returns:
            Formatted report string
        """
        health = self.get_health_score()
        total = self.metrics["requests"]["total"]

        if total == 0:
            return "No search operations recorded yet."

        health_indicator = "✅" if health > 0.8 else "⚠️" if health > 0.6 else "❌"

        # Format top error types
        top_errors = sorted(
            self.metrics["errors"]["by_type"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        error_str = ", ".join(f"{k}({v})" for k, v in top_errors) if top_errors else "None"

        # Format top query types
        top_types = sorted(
            self.metrics["patterns"]["top_query_types"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]
        types_str = ", ".join(f"{k}({v})" for k, v in top_types)

        # Format top domains
        top_domains = sorted(
            self.metrics["patterns"]["top_domains_returned"].items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        domains_str = ", ".join(f"{k}({v})" for k, v in top_domains)

        # Extract slowest query info
        slowest_query = self.metrics["performance"]["slowest_query"]
        slowest_query_str = "N/A"
        slowest_time_str = "0ms"
        if slowest_query:
            slowest_query_str = slowest_query["query"]
            slowest_time_str = f"{slowest_query['time']:.0f}ms"

        report = f"""
Search Tool Performance Report
{'='*50}

Overall Health Score: {health:.2%} {health_indicator}

Requests:
  Total: {total}
  Successful: {self.metrics['requests']['successful']} ({self.metrics['requests']['successful']/total:.1%})
  Failed: {self.metrics['requests']['failed']}
  Cached: {self.metrics['requests']['cached']}

Performance:
  Avg Response: {self.metrics['performance']['avg_response_time_ms']:.0f}ms
  P95 Response: {self.metrics['performance']['p95_response_time_ms']:.0f}ms
  Slowest: {slowest_query_str} ({slowest_time_str})

Quality:
  Avg Results/Query: {self.metrics['quality']['avg_results_per_query']:.1f}
  Avg Quality Score: {self.metrics['quality']['avg_quality_score']:.2f}
  High Quality %: {self.metrics['quality']['high_quality_results_pct']:.1%}
  No Results: {self.metrics['quality']['queries_with_no_results']}

Cache:
  Hit Rate: {self.metrics['cache']['hit_rate']:.1%}
  Hits: {self.metrics['cache']['total_hits']}
  Misses: {self.metrics['cache']['total_misses']}

Errors:
  Error Rate: {self.metrics['errors']['error_rate']:.1%}
  Top Types: {error_str}

Query Patterns:
  Top Types: {types_str}
  Avg Query Length: {self.metrics['patterns']['avg_query_length']:.1f} words
  Top Domains: {domains_str}
"""
        return report

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all metrics.

        Returns:
            Complete metrics dictionary
        """
        return self.metrics.copy()

    def reset(self):
        """Reset all metrics"""
        self.__init__()

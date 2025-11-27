"""
Performance Monitoring for Graph Storage

Provides query performance monitoring, query plan analysis, and optimization suggestions.
"""

import time
import logging
import asyncio
import asyncpg  # type: ignore[import-untyped]
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for a single query"""

    query_type: str
    query_text: str
    execution_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    execution_times: List[float] = field(default_factory=list)

    def add_execution(self, duration_ms: float) -> None:
        """Add a query execution time"""
        self.execution_count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.execution_times.append(duration_ms)

        # Keep only last 100 executions for percentile calculations
        if len(self.execution_times) > 100:
            self.execution_times.pop(0)

        self.avg_time_ms = self.total_time_ms / self.execution_count

    def get_percentile(self, percentile: float) -> float:
        """Get percentile execution time"""
        if not self.execution_times:
            return 0.0
        sorted_times = sorted(self.execution_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "query_type": self.query_type,
            "query_text": (self.query_text[:100] + "..." if len(self.query_text) > 100 else self.query_text),
            "execution_count": self.execution_count,
            "total_time_ms": round(self.total_time_ms, 2),
            "avg_time_ms": round(self.avg_time_ms, 2),
            "min_time_ms": round(self.min_time_ms, 2),
            "max_time_ms": round(self.max_time_ms, 2),
            "p50_ms": round(self.get_percentile(50), 2),
            "p95_ms": round(self.get_percentile(95), 2),
            "p99_ms": round(self.get_percentile(99), 2),
        }


@dataclass
class QueryPlan:
    """PostgreSQL query execution plan"""

    query: str
    plan: Dict[str, Any]
    total_cost: float
    execution_time_ms: Optional[float] = None

    def get_warnings(self) -> List[str]:
        """Get performance warnings from query plan"""
        warnings = []

        # Check for sequential scans
        if self._has_sequential_scan(self.plan):
            warnings.append("Sequential scan detected - consider adding index")

        # Check for nested loops with large datasets
        if self._has_inefficient_nested_loop(self.plan):
            warnings.append("Inefficient nested loop - consider optimizing join")

        # Check for high cost
        if self.total_cost > 10000:
            warnings.append(f"High query cost ({self.total_cost:.0f}) - consider optimization")

        return warnings

    def _has_sequential_scan(self, node: Dict[str, Any]) -> bool:
        """Check if plan has sequential scan"""
        if node.get("Node Type") == "Seq Scan":
            return True
        for child in node.get("Plans", []):
            if self._has_sequential_scan(child):
                return True
        return False

    def _has_inefficient_nested_loop(self, node: Dict[str, Any]) -> bool:
        """Check if plan has inefficient nested loop"""
        if node.get("Node Type") == "Nested Loop":
            # Check if estimated rows is large
            if node.get("Plan Rows", 0) > 1000:
                return True
        for child in node.get("Plans", []):
            if self._has_inefficient_nested_loop(child):
                return True
        return False


class PerformanceMonitor:
    """
    Monitor query performance and provide optimization suggestions

    Tracks query execution times, analyzes query plans, and provides
    recommendations for improving query performance.

    Example:
        ```python
        monitor = PerformanceMonitor()

        # Track query execution
        async with monitor.track_query("get_entity", "SELECT * FROM entities WHERE id = $1"):
            result = await conn.fetch(query, entity_id)

        # Get performance report
        report = monitor.get_performance_report()
        print(report["slow_queries"])
        ```
    """

    def __init__(
        self,
        enabled: bool = True,
        slow_query_threshold_ms: float = 100.0,
        log_slow_queries: bool = True,
    ):
        """
        Initialize performance monitor

        Args:
            enabled: Enable/disable monitoring
            slow_query_threshold_ms: Threshold for slow query logging (ms)
            log_slow_queries: Log slow queries to logger
        """
        self.enabled = enabled
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self.log_slow_queries = log_slow_queries

        self.query_stats: Dict[str, QueryStats] = {}
        self.slow_queries: List[Dict[str, Any]] = []
        self._lock: Optional[asyncio.Lock] = None

    async def initialize(self) -> None:
        """Initialize monitor (create locks, etc.)"""
        self._lock = asyncio.Lock()

    def track_query(self, query_type: str, query_text: str):
        """
        Context manager for tracking query execution

        Args:
            query_type: Type of query (e.g., "get_entity", "find_paths")
            query_text: SQL query text

        Returns:
            Context manager

        Example:
            ```python
            async with monitor.track_query("get_entity", query):
                result = await conn.fetch(query)
            ```
        """
        return QueryTracker(self, query_type, query_text)

    async def record_query(
        self,
        query_type: str,
        query_text: str,
        duration_ms: float,
        row_count: Optional[int] = None,
    ) -> None:
        """
        Record a query execution

        Args:
            query_type: Type of query
            query_text: SQL query text
            duration_ms: Execution time in milliseconds
            row_count: Number of rows returned/affected
        """
        if not self.enabled:
            return

        # Update stats
        key = f"{query_type}:{query_text[:50]}"
        if key not in self.query_stats:
            self.query_stats[key] = QueryStats(query_type, query_text)

        self.query_stats[key].add_execution(duration_ms)

        # Check if slow query
        if duration_ms >= self.slow_query_threshold_ms:
            slow_query = {
                "query_type": query_type,
                "query_text": query_text[:200],
                "duration_ms": duration_ms,
                "row_count": row_count,
                "timestamp": time.time(),
            }
            self.slow_queries.append(slow_query)

            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)

            if self.log_slow_queries:
                logger.warning(f"Slow query detected: {query_type} took {duration_ms:.2f}ms " f"(rows: {row_count})")

    async def analyze_query_plan(self, conn: asyncpg.Connection, query: str, params: tuple = ()) -> QueryPlan:
        """
        Analyze query execution plan

        Args:
            conn: Database connection
            query: SQL query to analyze
            params: Query parameters

        Returns:
            QueryPlan with analysis results

        Example:
            ```python
            plan = await monitor.analyze_query_plan(
                conn,
                "SELECT * FROM entities WHERE entity_type = $1",
                ("Person",)
            )
            print(plan.get_warnings())
            ```
        """
        if not self.enabled:
            raise RuntimeError("Performance monitoring is disabled")

        # Get query plan with EXPLAIN (ANALYZE, FORMAT JSON)
        explain_query = f"EXPLAIN (ANALYZE, FORMAT JSON) {query}"

        try:
            start = time.time()
            result = await conn.fetch(explain_query, *params)
            duration_ms = (time.time() - start) * 1000

            if not result:
                raise ValueError("No query plan returned")

            # Parse JSON plan
            plan_json = result[0]["QUERY PLAN"]
            if isinstance(plan_json, str):
                import json

                plan_json = json.loads(plan_json)

            # Extract plan details
            plan_data = plan_json[0] if isinstance(plan_json, list) else plan_json
            total_cost = plan_data.get("Plan", {}).get("Total Cost", 0)

            return QueryPlan(
                query=query,
                plan=plan_data,
                total_cost=total_cost,
                execution_time_ms=duration_ms,
            )

        except Exception as e:
            logger.error(f"Failed to analyze query plan: {e}")
            raise

    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report

        Returns:
            Dictionary with performance statistics

        Example:
            ```python
            report = monitor.get_performance_report()
            print(f"Total queries: {report['total_queries']}")
            print(f"Slow queries: {len(report['slow_queries'])}")
            ```
        """
        if not self.enabled:
            return {"enabled": False}

        # Calculate aggregate stats
        total_queries = sum(stats.execution_count for stats in self.query_stats.values())
        total_time_ms = sum(stats.total_time_ms for stats in self.query_stats.values())

        # Get top slow queries
        sorted_stats = sorted(
            self.query_stats.values(),
            key=lambda s: s.avg_time_ms,
            reverse=True,
        )
        top_slow = [stats.to_dict() for stats in sorted_stats[:10]]

        # Get most frequent queries
        sorted_by_count = sorted(
            self.query_stats.values(),
            key=lambda s: s.execution_count,
            reverse=True,
        )
        most_frequent = [stats.to_dict() for stats in sorted_by_count[:10]]

        return {
            "enabled": True,
            "total_queries": total_queries,
            "total_time_ms": round(total_time_ms, 2),
            "avg_query_time_ms": (round(total_time_ms / total_queries, 2) if total_queries > 0 else 0),
            "unique_queries": len(self.query_stats),
            "slow_query_count": len(self.slow_queries),
            "slow_query_threshold_ms": self.slow_query_threshold_ms,
            "top_slow_queries": top_slow,
            "most_frequent_queries": most_frequent,
            "recent_slow_queries": self.slow_queries[-10:],
        }

    def get_query_stats(self, query_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get statistics for specific query type or all queries

        Args:
            query_type: Filter by query type (None for all)

        Returns:
            List of query statistics
        """
        if not self.enabled:
            return []

        stats_list: List[QueryStats] = list(self.query_stats.values())
        if query_type:
            stats_list = [s for s in stats_list if s.query_type == query_type]

        return [s.to_dict() for s in stats_list]

    def reset_stats(self) -> None:
        """Reset all performance statistics"""
        self.query_stats.clear()
        self.slow_queries.clear()
        logger.info("Performance statistics reset")


class QueryTracker:
    """Context manager for tracking query execution time"""

    def __init__(self, monitor: PerformanceMonitor, query_type: str, query_text: str):
        """
        Initialize query tracker

        Args:
            monitor: Performance monitor instance
            query_type: Type of query
            query_text: SQL query text
        """
        self.monitor = monitor
        self.query_type = query_type
        self.query_text = query_text
        self.start_time = 0.0

    async def __aenter__(self):
        """Start timing"""
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End timing and record"""
        if not self.monitor.enabled:
            return

        duration_ms = (time.time() - self.start_time) * 1000
        await self.monitor.record_query(self.query_type, self.query_text, duration_ms)


class PreparedStatementCache:
    """
    Cache for prepared statements

    Provides caching of prepared statements to reduce query planning overhead.

    Example:
        ```python
        cache = PreparedStatementCache(max_size=100)

        # Get or create prepared statement
        stmt = await cache.get_or_prepare(
            conn,
            "get_entity",
            "SELECT * FROM entities WHERE id = $1"
        )
        result = await conn.fetch(stmt, entity_id)
        ```
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize prepared statement cache

        Args:
            max_size: Maximum number of cached statements
        """
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.access_count: Dict[str, int] = defaultdict(int)

    async def get_or_prepare(self, conn: asyncpg.Connection, name: str, query: str) -> Any:
        """
        Get cached prepared statement or create new one

        Args:
            conn: Database connection
            name: Statement name (unique identifier)
            query: SQL query text

        Returns:
            Prepared statement
        """
        # Check cache
        if name in self.cache:
            self.access_count[name] += 1
            return self.cache[name]

        # Evict least used if cache full
        if len(self.cache) >= self.max_size:
            least_used = min(self.access_count.items(), key=lambda x: x[1])[0]
            del self.cache[least_used]
            del self.access_count[least_used]

        # Prepare statement
        stmt = await conn.prepare(query)
        self.cache[name] = stmt
        self.access_count[name] = 1

        return stmt

    def clear(self) -> None:
        """Clear all cached statements"""
        self.cache.clear()
        self.access_count.clear()

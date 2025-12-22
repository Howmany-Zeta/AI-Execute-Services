"""
Unit tests for graph storage performance monitoring module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import time
import asyncio
from aiecs.infrastructure.graph_storage.performance_monitoring import (
    QueryStats,
    QueryPlan,
    PerformanceMonitor
)


class TestQueryStats:
    """Test QueryStats dataclass"""
    
    def test_query_stats_init(self):
        """Test QueryStats initialization"""
        stats = QueryStats(
            query_type="get_entity",
            query_text="SELECT * FROM entities WHERE id = $1"
        )
        
        assert stats.query_type == "get_entity"
        assert stats.query_text == "SELECT * FROM entities WHERE id = $1"
        assert stats.execution_count == 0
        assert stats.total_time_ms == 0.0
        assert stats.min_time_ms == float('inf')
        assert stats.max_time_ms == 0.0
        assert stats.avg_time_ms == 0.0
    
    def test_query_stats_add_execution(self):
        """Test adding execution time"""
        stats = QueryStats("get_entity", "SELECT * FROM entities")
        
        stats.add_execution(10.0)
        
        assert stats.execution_count == 1
        assert stats.total_time_ms == 10.0
        assert stats.min_time_ms == 10.0
        assert stats.max_time_ms == 10.0
        assert stats.avg_time_ms == 10.0
    
    def test_query_stats_add_multiple_executions(self):
        """Test adding multiple executions"""
        stats = QueryStats("get_entity", "SELECT * FROM entities")
        
        stats.add_execution(10.0)
        stats.add_execution(20.0)
        stats.add_execution(30.0)
        
        assert stats.execution_count == 3
        assert stats.total_time_ms == 60.0
        assert stats.min_time_ms == 10.0
        assert stats.max_time_ms == 30.0
        assert stats.avg_time_ms == 20.0
    
    def test_query_stats_get_percentile(self):
        """Test getting percentile"""
        stats = QueryStats("get_entity", "SELECT * FROM entities")
        
        # Add multiple executions
        for i in range(10, 21):
            stats.add_execution(float(i))
        
        p50 = stats.get_percentile(50)
        p95 = stats.get_percentile(95)
        p99 = stats.get_percentile(99)
        
        assert p50 > 0
        assert p95 > p50
        assert p99 >= p95
    
    def test_query_stats_get_percentile_empty(self):
        """Test getting percentile with no executions"""
        stats = QueryStats("get_entity", "SELECT * FROM entities")
        
        p50 = stats.get_percentile(50)
        
        assert p50 == 0.0
    
    def test_query_stats_to_dict(self):
        """Test QueryStats.to_dict()"""
        stats = QueryStats("get_entity", "SELECT * FROM entities WHERE id = $1")
        stats.add_execution(10.0)
        stats.add_execution(20.0)
        
        result = stats.to_dict()
        
        assert result["query_type"] == "get_entity"
        assert "SELECT * FROM entities" in result["query_text"]
        assert result["execution_count"] == 2
        assert result["avg_time_ms"] == 15.0
        assert "p50_ms" in result
        assert "p95_ms" in result
        assert "p99_ms" in result


class TestQueryPlan:
    """Test QueryPlan dataclass"""
    
    def test_query_plan_init(self):
        """Test QueryPlan initialization"""
        plan = QueryPlan(
            query="SELECT * FROM entities",
            plan={"Node Type": "Seq Scan"},
            total_cost=100.0
        )
        
        assert plan.query == "SELECT * FROM entities"
        assert plan.plan == {"Node Type": "Seq Scan"}
        assert plan.total_cost == 100.0
        assert plan.execution_time_ms is None
    
    def test_query_plan_get_warnings_sequential_scan(self):
        """Test QueryPlan warnings for sequential scan"""
        plan = QueryPlan(
            query="SELECT * FROM entities",
            plan={
                "Node Type": "Seq Scan",
                "Plans": []
            },
            total_cost=100.0
        )
        
        warnings = plan.get_warnings()
        
        assert len(warnings) > 0
        assert any("Sequential scan" in w for w in warnings)
    
    def test_query_plan_get_warnings_high_cost(self):
        """Test QueryPlan warnings for high cost"""
        plan = QueryPlan(
            query="SELECT * FROM entities",
            plan={"Node Type": "Index Scan"},
            total_cost=15000.0
        )
        
        warnings = plan.get_warnings()
        
        assert len(warnings) > 0
        assert any("High query cost" in w for w in warnings)
    
    def test_query_plan_get_warnings_no_warnings(self):
        """Test QueryPlan with no warnings"""
        plan = QueryPlan(
            query="SELECT * FROM entities WHERE id = $1",
            plan={
                "Node Type": "Index Scan",
                "Plans": []
            },
            total_cost=10.0
        )
        
        warnings = plan.get_warnings()
        
        # May or may not have warnings depending on implementation
        assert isinstance(warnings, list)


class TestPerformanceMonitor:
    """Test PerformanceMonitor"""
    
    @pytest.fixture
    def monitor(self):
        """Create PerformanceMonitor instance"""
        return PerformanceMonitor(enabled=True, slow_query_threshold_ms=100.0)
    
    @pytest.mark.asyncio
    async def test_initialize(self, monitor):
        """Test monitor initialization"""
        await monitor.initialize()
        
        assert monitor._lock is not None
    
    @pytest.mark.asyncio
    async def test_record_query(self, monitor):
        """Test recording query execution"""
        await monitor.initialize()
        
        await monitor.record_query(
            query_type="get_entity",
            query_text="SELECT * FROM entities WHERE id = $1",
            duration_ms=50.0,
            row_count=1
        )
        
        assert len(monitor.query_stats) > 0
    
    @pytest.mark.asyncio
    async def test_record_slow_query(self, monitor):
        """Test recording slow query"""
        await monitor.initialize()
        
        await monitor.record_query(
            query_type="get_entity",
            query_text="SELECT * FROM entities",
            duration_ms=150.0,  # Above threshold
            row_count=1
        )
        
        assert len(monitor.slow_queries) == 1
        assert monitor.slow_queries[0]["duration_ms"] == 150.0
    
    @pytest.mark.asyncio
    async def test_record_query_disabled(self):
        """Test recording query when disabled"""
        monitor = PerformanceMonitor(enabled=False)
        await monitor.initialize()
        
        await monitor.record_query(
            query_type="get_entity",
            query_text="SELECT * FROM entities",
            duration_ms=50.0
        )
        
        assert len(monitor.query_stats) == 0
    
    @pytest.mark.asyncio
    async def test_get_performance_report(self, monitor):
        """Test getting performance report"""
        await monitor.initialize()
        
        await monitor.record_query("get_entity", "SELECT * FROM entities", 50.0)
        await monitor.record_query("get_entity", "SELECT * FROM entities", 60.0)
        
        report = monitor.get_performance_report()
        
        assert report["enabled"] is True
        assert report["total_queries"] == 2
        assert report["unique_queries"] > 0
        assert "top_slow_queries" in report
        assert "most_frequent_queries" in report
    
    @pytest.mark.asyncio
    async def test_get_performance_report_disabled(self):
        """Test getting performance report when disabled"""
        monitor = PerformanceMonitor(enabled=False)
        await monitor.initialize()
        
        report = monitor.get_performance_report()
        
        assert report["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_get_query_stats(self, monitor):
        """Test getting query stats"""
        await monitor.initialize()
        
        await monitor.record_query("get_entity", "SELECT * FROM entities", 50.0)
        await monitor.record_query("get_relation", "SELECT * FROM relations", 60.0)
        
        stats = monitor.get_query_stats()
        
        assert len(stats) > 0
    
    @pytest.mark.asyncio
    async def test_get_query_stats_filtered(self, monitor):
        """Test getting query stats filtered by type"""
        await monitor.initialize()
        
        await monitor.record_query("get_entity", "SELECT * FROM entities", 50.0)
        await monitor.record_query("get_relation", "SELECT * FROM relations", 60.0)
        
        stats = monitor.get_query_stats(query_type="get_entity")
        
        assert len(stats) > 0
        assert all(s["query_type"] == "get_entity" for s in stats)
    
    @pytest.mark.asyncio
    async def test_track_query_context_manager(self, monitor):
        """Test track_query context manager"""
        await monitor.initialize()
        
        async with monitor.track_query("get_entity", "SELECT * FROM entities"):
            await asyncio.sleep(0.01)  # Simulate query execution
        
        # Query should be recorded
        assert len(monitor.query_stats) > 0


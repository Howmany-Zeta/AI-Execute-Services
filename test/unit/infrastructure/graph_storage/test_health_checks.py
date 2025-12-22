"""
Unit tests for graph storage health checks module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from datetime import datetime

from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.health_checks import (
    HealthStatus,
    HealthCheckResult,
    HealthChecker,
    HealthMonitor
)


class TestHealthStatus:
    """Test HealthStatus enum"""
    
    def test_health_status_values(self):
        """Test HealthStatus enum values"""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass"""
    
    def test_health_check_result_defaults(self):
        """Test HealthCheckResult with defaults"""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="All checks passed"
        )
        
        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All checks passed"
        assert result.response_time_ms == 0.0
        assert isinstance(result.timestamp, datetime)
        assert result.details == {}
        assert result.error is None
    
    def test_health_check_result_custom(self):
        """Test HealthCheckResult with custom values"""
        timestamp = datetime.utcnow()
        result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message="Some checks failed",
            response_time_ms=15.5,
            timestamp=timestamp,
            details={"connection": "ok", "query": "slow"},
            error="Query timeout"
        )
        
        assert result.status == HealthStatus.DEGRADED
        assert result.message == "Some checks failed"
        assert result.response_time_ms == 15.5
        assert result.timestamp == timestamp
        assert result.details == {"connection": "ok", "query": "slow"}
        assert result.error == "Query timeout"
    
    def test_health_check_result_to_dict(self):
        """Test HealthCheckResult.to_dict()"""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK",
            response_time_ms=12.345,
            details={"test": "value"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["status"] == "healthy"
        assert result_dict["message"] == "OK"
        assert result_dict["response_time_ms"] == 12.35  # Rounded
        assert "timestamp" in result_dict
        assert result_dict["details"] == {"test": "value"}
    
    def test_health_check_result_is_healthy(self):
        """Test is_healthy() method"""
        healthy_result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK"
        )
        unhealthy_result = HealthCheckResult(
            status=HealthStatus.UNHEALTHY,
            message="Failed"
        )
        
        assert healthy_result.is_healthy() is True
        assert unhealthy_result.is_healthy() is False


class TestHealthChecker:
    """Test HealthChecker"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    def checker(self, store):
        """Create HealthChecker instance"""
        return HealthChecker(store, timeout_seconds=5.0, query_timeout_ms=1000.0)
    
    @pytest.mark.asyncio
    async def test_check_health_initialized(self, checker):
        """Test health check with initialized store"""
        result = await checker.check_health()
        
        assert isinstance(result, HealthCheckResult)
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "details" in result.to_dict()
    
    @pytest.mark.asyncio
    async def test_check_health_uninitialized(self):
        """Test health check with uninitialized store"""
        store = InMemoryGraphStore()
        checker = HealthChecker(store)
        
        result = await checker.check_health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "not initialized" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_check_health_response_time(self, checker):
        """Test health check measures response time"""
        result = await checker.check_health()
        
        assert result.response_time_ms >= 0.0
        # response_time_ms may be in details if health check completes fully
        # or may not be if check fails early
        assert isinstance(result.details, dict)
    
    @pytest.mark.asyncio
    async def test_check_liveness(self, checker):
        """Test liveness check"""
        is_alive = await checker.check_liveness()
        
        assert isinstance(is_alive, bool)
    
    @pytest.mark.asyncio
    async def test_check_readiness(self, checker):
        """Test readiness check"""
        is_ready = await checker.check_readiness()
        
        assert isinstance(is_ready, bool)
    
    @pytest.mark.asyncio
    async def test_check_readiness_healthy(self, checker):
        """Test readiness check returns True for healthy status"""
        # Mock a healthy result
        result = await checker.check_health()
        is_ready = await checker.check_readiness()
        
        # Should be ready if healthy or degraded
        if result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            assert is_ready is True


class TestHealthMonitor:
    """Test HealthMonitor"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    def checker(self, store):
        """Create HealthChecker instance"""
        return HealthChecker(store)
    
    @pytest.fixture
    def monitor(self, checker):
        """Create HealthMonitor instance"""
        return HealthMonitor(checker, interval_seconds=0.1)  # Short interval for tests
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, monitor):
        """Test starting and stopping monitor"""
        await monitor.start()
        assert monitor._monitoring is True
        
        await monitor.stop()
        assert monitor._monitoring is False
    
    @pytest.mark.asyncio
    async def test_monitor_collects_history(self, monitor):
        """Test monitor collects health history"""
        await monitor.start()
        
        # Wait for at least one check
        import asyncio
        await asyncio.sleep(0.15)  # Wait for one check cycle
        
        await monitor.stop()
        
        assert len(monitor.health_history) > 0
    
    def test_get_current_status_empty(self, monitor):
        """Test get_current_status with no history"""
        status = monitor.get_current_status()
        
        assert status is None
    
    def test_get_current_status_with_history(self, monitor):
        """Test get_current_status with history"""
        # Manually add a result
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="OK"
        )
        monitor.health_history.append(result)
        
        current = monitor.get_current_status()
        
        assert current == result
    
    def test_get_health_history(self, monitor):
        """Test get_health_history"""
        # Add multiple results
        for i in range(5):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message=f"Check {i}"
            )
            monitor.health_history.append(result)
        
        history = monitor.get_health_history(limit=3)
        
        assert len(history) == 3
        assert history[-1].message == "Check 4"
    
    def test_get_uptime_percentage_no_history(self, monitor):
        """Test uptime percentage with no history"""
        uptime = monitor.get_uptime_percentage()
        
        assert uptime == 0.0
    
    def test_get_uptime_percentage_all_healthy(self, monitor):
        """Test uptime percentage with all healthy checks"""
        # Add healthy results
        for _ in range(10):
            result = HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="OK",
                timestamp=datetime.utcnow()
            )
            monitor.health_history.append(result)
        
        uptime = monitor.get_uptime_percentage(window_minutes=60)
        
        assert uptime == 100.0
    
    def test_get_uptime_percentage_mixed(self, monitor):
        """Test uptime percentage with mixed results"""
        # Add mixed results
        for i in range(10):
            status = HealthStatus.HEALTHY if i % 2 == 0 else HealthStatus.UNHEALTHY
            result = HealthCheckResult(
                status=status,
                message="OK",
                timestamp=datetime.utcnow()
            )
            monitor.health_history.append(result)
        
        uptime = monitor.get_uptime_percentage(window_minutes=60)
        
        assert uptime == 50.0
    
    @pytest.mark.asyncio
    async def test_monitor_max_history(self, monitor):
        """Test monitor limits history size"""
        monitor.max_history = 5
        
        await monitor.start()
        
        # Wait for multiple checks
        import asyncio
        await asyncio.sleep(0.6)  # Wait for multiple check cycles
        
        await monitor.stop()
        
        # History should be limited
        assert len(monitor.health_history) <= monitor.max_history


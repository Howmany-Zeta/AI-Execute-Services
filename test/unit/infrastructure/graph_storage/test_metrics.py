"""
Unit tests for graph storage metrics module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from datetime import datetime, timedelta

from aiecs.infrastructure.graph_storage.metrics import (
    Metric,
    MetricsCollector,
    MetricsExporter
)


class TestMetric:
    """Test Metric dataclass"""
    
    def test_metric_defaults(self):
        """Test Metric with defaults"""
        metric = Metric(name="test_metric", value=10.5)
        
        assert metric.name == "test_metric"
        assert metric.value == 10.5
        assert isinstance(metric.timestamp, datetime)
        assert metric.tags == {}
    
    def test_metric_custom(self):
        """Test Metric with custom values"""
        timestamp = datetime.utcnow()
        metric = Metric(
            name="custom_metric",
            value=20.0,
            timestamp=timestamp,
            tags={"env": "test", "service": "graph"}
        )
        
        assert metric.name == "custom_metric"
        assert metric.value == 20.0
        assert metric.timestamp == timestamp
        assert metric.tags == {"env": "test", "service": "graph"}
    
    def test_metric_to_dict(self):
        """Test Metric.to_dict()"""
        metric = Metric(name="test", value=15.5, tags={"key": "value"})
        
        result = metric.to_dict()
        
        assert result["name"] == "test"
        assert result["value"] == 15.5
        assert result["tags"] == {"key": "value"}
        assert "timestamp" in result


class TestMetricsCollector:
    """Test MetricsCollector"""
    
    @pytest.fixture
    def collector(self):
        """Create MetricsCollector instance"""
        return MetricsCollector(window_seconds=300)
    
    def test_init_defaults(self):
        """Test MetricsCollector initialization with defaults"""
        collector = MetricsCollector()
        
        assert collector.window_seconds == 300
        assert collector.cache_hits == 0
        assert collector.cache_misses == 0
    
    def test_init_custom_window(self):
        """Test MetricsCollector initialization with custom window"""
        collector = MetricsCollector(window_seconds=600)
        
        assert collector.window_seconds == 600
    
    def test_record_latency(self, collector):
        """Test recording latency"""
        collector.record_latency("get_entity", 12.5)
        
        assert len(collector.latency_metrics["get_entity"]) == 1
        assert collector.latency_metrics["get_entity"][0]["value"] == 12.5
    
    def test_record_latency_with_tags(self, collector):
        """Test recording latency with tags"""
        collector.record_latency("get_entity", 15.0, tags={"type": "Person"})
        
        metric = collector.latency_metrics["get_entity"][0]
        assert metric["value"] == 15.0
        assert metric["tags"] == {"type": "Person"}
    
    def test_record_latency_multiple(self, collector):
        """Test recording multiple latency measurements"""
        collector.record_latency("get_entity", 10.0)
        collector.record_latency("get_entity", 20.0)
        collector.record_latency("get_entity", 30.0)
        
        assert len(collector.latency_metrics["get_entity"]) == 3
    
    def test_record_cache_hit(self, collector):
        """Test recording cache hit"""
        collector.record_cache_hit()
        
        assert collector.cache_hits == 1
    
    def test_record_cache_miss(self, collector):
        """Test recording cache miss"""
        collector.record_cache_miss()
        
        assert collector.cache_misses == 1
    
    def test_record_cache_multiple(self, collector):
        """Test recording multiple cache events"""
        collector.record_cache_hit()
        collector.record_cache_hit()
        collector.record_cache_miss()
        
        assert collector.cache_hits == 2
        assert collector.cache_misses == 1
    
    def test_record_error(self, collector):
        """Test recording error"""
        collector.record_error("connection_error")
        
        assert collector.error_counts["connection_error"] == 1
    
    def test_record_error_multiple(self, collector):
        """Test recording multiple errors"""
        collector.record_error("connection_error")
        collector.record_error("connection_error")
        collector.record_error("query_error")
        
        assert collector.error_counts["connection_error"] == 2
        assert collector.error_counts["query_error"] == 1
    
    def test_record_counter(self, collector):
        """Test recording counter"""
        collector.record_counter("entities_added", 5)
        
        assert collector.counters["entities_added"] == 5
    
    def test_record_counter_default(self, collector):
        """Test recording counter with default increment"""
        collector.record_counter("entities_added")
        
        assert collector.counters["entities_added"] == 1
    
    def test_record_counter_multiple(self, collector):
        """Test recording counter multiple times"""
        collector.record_counter("entities_added", 3)
        collector.record_counter("entities_added", 2)
        
        assert collector.counters["entities_added"] == 5
    
    def test_record_resource_metric(self, collector):
        """Test recording resource metric"""
        collector.record_resource_metric("memory_mb", 512.0)
        
        assert len(collector.resource_metrics["memory_mb"]) == 1
        assert collector.resource_metrics["memory_mb"][0]["value"] == 512.0
    
    def test_get_cache_hit_rate_no_requests(self, collector):
        """Test cache hit rate with no requests"""
        rate = collector.get_cache_hit_rate()
        
        assert rate == 0.0
    
    def test_get_cache_hit_rate_all_hits(self, collector):
        """Test cache hit rate with all hits"""
        collector.record_cache_hit()
        collector.record_cache_hit()
        
        rate = collector.get_cache_hit_rate()
        
        assert rate == 1.0
    
    def test_get_cache_hit_rate_all_misses(self, collector):
        """Test cache hit rate with all misses"""
        collector.record_cache_miss()
        collector.record_cache_miss()
        
        rate = collector.get_cache_hit_rate()
        
        assert rate == 0.0
    
    def test_get_cache_hit_rate_mixed(self, collector):
        """Test cache hit rate with mixed hits and misses"""
        collector.record_cache_hit()
        collector.record_cache_hit()
        collector.record_cache_miss()
        
        rate = collector.get_cache_hit_rate()
        
        assert rate == pytest.approx(2.0 / 3.0)
    
    def test_get_latency_stats_empty(self, collector):
        """Test latency stats with no data"""
        stats = collector.get_latency_stats("get_entity")
        
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["avg"] == 0.0
        assert stats["count"] == 0
    
    def test_get_latency_stats_single(self, collector):
        """Test latency stats with single measurement"""
        collector.record_latency("get_entity", 10.0)
        
        stats = collector.get_latency_stats("get_entity")
        
        assert stats["min"] == 10.0
        assert stats["max"] == 10.0
        assert stats["avg"] == 10.0
        assert stats["count"] == 1
    
    def test_get_latency_stats_multiple(self, collector):
        """Test latency stats with multiple measurements"""
        collector.record_latency("get_entity", 10.0)
        collector.record_latency("get_entity", 20.0)
        collector.record_latency("get_entity", 30.0)
        
        stats = collector.get_latency_stats("get_entity")
        
        assert stats["min"] == 10.0
        assert stats["max"] == 30.0
        assert stats["avg"] == 20.0
        assert stats["count"] == 3
        assert stats["p50"] > 0
        assert stats["p95"] > 0
        assert stats["p99"] > 0
    
    def test_get_metrics(self, collector):
        """Test getting all metrics"""
        collector.record_latency("get_entity", 10.0)
        collector.record_cache_hit()
        collector.record_error("connection_error")
        collector.record_counter("entities_added", 5)
        collector.record_resource_metric("memory_mb", 512.0)
        
        metrics = collector.get_metrics()
        
        assert "latency" in metrics
        assert "cache" in metrics
        assert "counters" in metrics
        assert "errors" in metrics
        assert "resources" in metrics
        assert "timestamp" in metrics
        assert "get_entity" in metrics["latency"]
        assert metrics["cache"]["hits"] == 1
        assert metrics["counters"]["entities_added"] == 5
        assert metrics["errors"]["connection_error"] == 1
    
    def test_reset(self, collector):
        """Test resetting metrics"""
        collector.record_latency("get_entity", 10.0)
        collector.record_cache_hit()
        collector.record_error("connection_error")
        collector.record_counter("entities_added", 5)
        
        collector.reset()
        
        assert len(collector.latency_metrics) == 0
        assert collector.cache_hits == 0
        assert collector.cache_misses == 0
        assert len(collector.error_counts) == 0
        assert len(collector.counters) == 0


class TestMetricsExporter:
    """Test MetricsExporter"""
    
    @pytest.fixture
    def collector(self):
        """Create MetricsCollector instance"""
        collector = MetricsCollector()
        collector.record_latency("get_entity", 10.0)
        collector.record_latency("get_entity", 20.0)
        collector.record_cache_hit()
        collector.record_cache_miss()
        collector.record_error("connection_error")
        collector.record_counter("entities_added", 5)
        return collector
    
    @pytest.fixture
    def exporter(self, collector):
        """Create MetricsExporter instance"""
        return MetricsExporter(collector)
    
    def test_to_prometheus(self, exporter):
        """Test Prometheus export"""
        prometheus = exporter.to_prometheus()
        
        assert isinstance(prometheus, str)
        assert "graph_store_latency_seconds" in prometheus
        assert "graph_store_cache_hits" in prometheus
        assert "graph_store_cache_misses" in prometheus
        assert "graph_store_errors" in prometheus
    
    def test_to_statsd(self, exporter):
        """Test StatsD export"""
        statsd = exporter.to_statsd()
        
        assert isinstance(statsd, list)
        assert len(statsd) > 0
        assert any("graph_store.latency" in line for line in statsd)
        assert any("graph_store.cache" in line for line in statsd)
    
    def test_to_dict(self, exporter):
        """Test dictionary export"""
        result = exporter.to_dict()
        
        assert isinstance(result, dict)
        assert "latency" in result
        assert "cache" in result
        assert "counters" in result
        assert "errors" in result


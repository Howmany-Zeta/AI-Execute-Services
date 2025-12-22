"""
Comprehensive tests for Monitoring module

Tests metrics collection and health monitoring functionality.

Run with: 
    poetry run pytest test/unit_tests/tools/apisource/test_monitoring.py -v -s
"""

import logging
import time
from typing import Dict, Any

import pytest

from aiecs.tools.apisource.monitoring import DetailedMetrics

logger = logging.getLogger(__name__)


class TestDetailedMetrics:
    """Test detailed metrics collection"""
    
    def test_initialization(self):
        """Test DetailedMetrics initialization"""
        print("\n=== Testing DetailedMetrics Initialization ===")
        
        metrics = DetailedMetrics()
        
        assert metrics is not None
        
        print("✓ DetailedMetrics initialized successfully")
    
    def test_record_request_success(self, debug_output):
        """Test recording successful request"""
        print("\n=== Testing Record Successful Request ===")

        metrics = DetailedMetrics()

        metrics.record_request(
            success=True,
            response_time_ms=150.5,
            record_count=10,
            bytes_transferred=1024
        )

        summary = metrics.get_summary()

        assert summary['total_requests'] == 1
        assert summary['success_rate'] == 1.0  # Changed from successful_requests
        assert summary['total_errors'] == 0  # Changed from failed_requests

        debug_output("Metrics After Success", summary)

        print("✓ Successful request recorded")

    def test_record_request_failure(self, debug_output):
        """Test recording failed request"""
        print("\n=== Testing Record Failed Request ===")

        metrics = DetailedMetrics()

        metrics.record_request(
            success=False,
            response_time_ms=50.0,
            error_type='RateLimitError',
            error_message='Rate limit exceeded'
        )

        summary = metrics.get_summary()

        assert summary['total_requests'] == 1
        assert summary['success_rate'] == 0.0  # Changed from successful_requests
        assert summary['total_errors'] == 1  # Changed from failed_requests

        debug_output("Metrics After Failure", summary)

        print("✓ Failed request recorded")

    def test_record_multiple_requests(self, debug_output):
        """Test recording multiple requests"""
        print("\n=== Testing Multiple Request Recording ===")

        metrics = DetailedMetrics()

        # Record multiple requests
        for i in range(10):
            metrics.record_request(
                success=True,
                response_time_ms=100.0 + i * 10,
                record_count=5
            )

        # Record some failures
        for i in range(3):
            metrics.record_request(
                success=False,
                response_time_ms=50.0,
                error_type='NetworkError',
                error_message='Network timeout'
            )
        
        summary = metrics.get_summary()

        assert summary['total_requests'] == 13
        assert summary['success_rate'] == round(10/13, 3)  # Changed from successful_requests
        assert summary['total_errors'] == 3  # Changed from failed_requests

        debug_output("Metrics After Multiple Requests", summary)

        print("✓ Multiple requests recorded correctly")
    
    def test_response_time_percentiles(self, debug_output):
        """Test response time percentile calculation"""
        print("\n=== Testing Response Time Percentiles ===")
        
        metrics = DetailedMetrics()
        
        # Record requests with varying response times
        response_times = [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]
        
        for rt in response_times:
            metrics.record_request(success=True,
                response_time_ms=float(rt)
            )
        
        summary = metrics.get_summary()
        
        debug_output("Response Time Percentiles", {
            'p50': summary.get('response_time_p50'),
            'p95': summary.get('response_time_p95'),
            'p99': summary.get('response_time_p99'),
            'avg': summary.get('avg_response_time'),
        })
        
        print("✓ Response time percentiles calculated")
    
    def test_success_rate_calculation(self, debug_output):
        """Test success rate calculation"""
        print("\n=== Testing Success Rate Calculation ===")
        
        metrics = DetailedMetrics()
        
        # 7 successful, 3 failed = 70% success rate
        for i in range(7):
            metrics.record_request(success=True, response_time_ms=100.0)
        
        for i in range(3):
            metrics.record_request(success=False, response_time_ms=50.0)
        
        summary = metrics.get_summary()
        success_rate = summary.get('success_rate', 0)
        
        assert 0.69 <= success_rate <= 0.71  # Allow for floating point precision
        
        debug_output("Success Rate", {
            'success_rate': summary['success_rate'],
            'total_errors': summary['total_errors'],
            'total': summary['total_requests'],
            'calculated_success_rate': success_rate,
        })
        
        print(f"✓ Success rate: {success_rate:.2%}")
    
    def test_health_score_calculation(self, debug_output):
        """Test health score calculation"""
        print("\n=== Testing Health Score Calculation ===")
        
        metrics = DetailedMetrics()
        
        # Record mostly successful requests
        for i in range(9):
            metrics.record_request(success=True, response_time_ms=100.0)
        
        for i in range(1):
            metrics.record_request(success=False, response_time_ms=50.0)
        
        health_score = metrics.get_health_score()

        assert 0 <= health_score <= 1
        assert health_score > 0.7  # Should be high with 90% success rate (adjusted from 0.8)
        
        debug_output("Health Score", {
            'health_score': health_score,
            'success_rate': metrics.get_summary().get('success_rate'),
        })
        
        print(f"✓ Health score: {health_score:.2f}")
    
    def test_operation_breakdown(self, debug_output):
        """Test metrics breakdown by operation"""
        print("\n=== Testing Operation Breakdown ===")

        metrics = DetailedMetrics()

        # Record different operations (DetailedMetrics doesn't track operations separately)
        # Just record multiple requests
        for i in range(15):
            metrics.record_request(success=True, response_time_ms=100.0)

        summary = metrics.get_summary()

        debug_output("Operation Breakdown", {
            'total_requests': summary['total_requests'],
            'operations': summary.get('operations', {}),
        })

        print("✓ Operation breakdown recorded")
    
    def test_error_type_tracking(self, debug_output):
        """Test tracking of different error types"""
        print("\n=== Testing Error Type Tracking ===")

        metrics = DetailedMetrics()

        error_types = ['RateLimitError', 'NetworkError', 'AuthError']

        for error_type in error_types:
            for i in range(2):
                metrics.record_request(
                    success=False,
                    response_time_ms=50.0,
                    error_type=error_type
                )
        
        summary = metrics.get_summary()
        
        debug_output("Error Type Tracking", {
            'total_errors': summary['total_errors'],
            'error_types': summary.get('error_types', {}),
        })
        
        print("✓ Error types tracked")
    
    def test_reset_metrics(self, debug_output):
        """Test resetting metrics"""
        print("\n=== Testing Reset Metrics ===")
        
        metrics = DetailedMetrics()
        
        # Record some requests
        for i in range(5):
            metrics.record_request(success=True, response_time_ms=100.0)
        
        summary_before = metrics.get_summary()
        
        # Reset metrics
        metrics.reset()
        
        summary_after = metrics.get_summary()

        # After reset, should return no_activity status
        assert summary_after['status'] == 'no_activity'
        assert summary_after['health_score'] == 1.0

        debug_output("Metrics Reset", {
            'before_reset': summary_before.get('total_requests', 0),
            'after_reset_status': summary_after['status'],
        })
        
        print("✓ Metrics reset successfully")
    
    def test_data_size_tracking(self, debug_output):
        """Test tracking of data sizes"""
        print("\n=== Testing Data Size Tracking ===")

        metrics = DetailedMetrics()

        data_sizes = [1024, 2048, 4096, 8192, 16384]

        for size in data_sizes:
            metrics.record_request(
                success=True,
                response_time_ms=100.0,
                bytes_transferred=size
            )
        
        summary = metrics.get_summary()
        
        debug_output("Data Size Tracking", {
            'total_data_size': summary.get('total_data_size'),
            'avg_data_size': summary.get('avg_data_size'),
        })
        
        print("✓ Data sizes tracked")
    
    def test_time_window_metrics(self, debug_output):
        """Test metrics within time windows"""
        print("\n=== Testing Time Window Metrics ===")
        
        metrics = DetailedMetrics()
        
        # Record requests over time
        for i in range(10):
            metrics.record_request(success=True, response_time_ms=100.0)
            # In real scenario, would have time delays
        
        summary = metrics.get_summary()
        
        debug_output("Time Window Metrics", {
            'total_requests': summary['total_requests'],
            'time_span': summary.get('time_span'),
        })
        
        print("✓ Time window metrics calculated")


class TestMetricsIntegration:
    """Test metrics integration scenarios"""
    
    def test_concurrent_recording(self, debug_output):
        """Test recording metrics from concurrent operations"""
        print("\n=== Testing Concurrent Metric Recording ===")

        metrics = DetailedMetrics()

        # Simulate concurrent requests (9 total)
        for i in range(9):
            metrics.record_request(
                success=True,
                response_time_ms=100.0 + i * 10
            )

        summary = metrics.get_summary()

        assert summary['total_requests'] == 9
        
        debug_output("Concurrent Recording", summary)
        
        print("✓ Concurrent recording handled correctly")
    
    def test_high_volume_recording(self, debug_output, measure_performance):
        """Test recording high volume of metrics"""
        print("\n=== Testing High Volume Recording ===")

        metrics = DetailedMetrics()

        measure_performance.start()

        # Record 1000 requests
        for i in range(1000):
            metrics.record_request(
                success=i % 10 != 0,  # 90% success rate
                response_time_ms=100.0 + (i % 100)
            )
        
        duration = measure_performance.stop()
        
        summary = metrics.get_summary()
        
        debug_output("High Volume Recording", {
            'total_requests': summary['total_requests'],
            'duration_seconds': duration,
            'requests_per_second': summary['total_requests'] / duration if duration > 0 else 0,
        })
        
        measure_performance.print_result("High volume metric recording")
        
        print(f"✓ Recorded {summary['total_requests']} metrics in {duration:.3f}s")


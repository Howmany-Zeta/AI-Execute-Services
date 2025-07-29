"""
Test configuration for integration tests
Provides safe defaults that don't require external services
"""

import os
import tempfile
from typing import Dict, Any

def get_integration_test_config() -> Dict[str, Any]:
    """
    Get configuration for integration tests that minimizes external dependencies
    """
    return {
        # Disable external services that may not be available in test environment
        "enable_metrics": False,
        "enable_tracing": False,
        "enable_cache": True,

        # Use shorter timeouts for faster tests
        "task_timeout_seconds": 10,
        "call_timeout_seconds": 15,
        "rate_limit_requests_per_second": 20,
        "batch_size": 3,

        # Use in-memory brokers for testing
        "broker_url": "memory://",
        "backend_url": "cache+memory://",

        # Use localhost with random port for WebSocket
        "websocket_host": "localhost",
        "websocket_port": 0,  # Let system choose available port

        # Test database configuration (may not connect, but won't crash)
        "db_config": {
            "user": "test_user",
            "password": "test_password",
            "database": "test_database",
            "host": "localhost",
            "port": 5432
        },

        # Retry configuration for faster tests
        "retry_max_attempts": 2,
        "retry_min_wait": 1,
        "retry_max_wait": 5,

        # Cache configuration
        "cache_ttl": 60,

        # Task queue configuration for testing
        "task_queues": {
            'test_tasks': {'exchange': 'test_tasks', 'routing_key': 'test_tasks'}
        },
        "worker_concurrency": {
            'test_worker': 2
        },

        # Tracing configuration (disabled)
        "tracing_service_name": "test_service_executor",
        "tracing_host": "localhost",
        "tracing_port": 6831,

        # Metrics configuration (disabled)
        "metrics_port": 0,  # Let system choose available port
    }

def get_minimal_test_config() -> Dict[str, Any]:
    """
    Get minimal configuration for basic functionality tests
    """
    return {
        "enable_metrics": False,
        "enable_tracing": False,
        "enable_cache": False,
        "task_timeout_seconds": 5,
        "broker_url": "memory://",
        "backend_url": "cache+memory://",
        "websocket_port": 0,
    }

def get_isolated_test_config() -> Dict[str, Any]:
    """
    Get configuration that completely isolates tests from external systems
    """
    temp_dir = tempfile.mkdtemp()

    return {
        "enable_metrics": False,
        "enable_tracing": False,
        "enable_cache": True,
        "task_timeout_seconds": 3,
        "broker_url": "memory://",
        "backend_url": "cache+memory://",
        "websocket_host": "127.0.0.1",
        "websocket_port": 0,
        "db_config": {
            "user": "isolated_test",
            "password": "isolated_test",
            "database": "isolated_test",
            "host": "127.0.0.1",
            "port": 5432
        },
        "retry_max_attempts": 1,
        "retry_min_wait": 1,
        "retry_max_wait": 2,
        "cache_ttl": 30,
        "temp_dir": temp_dir,
    }

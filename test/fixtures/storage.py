"""
Storage and database fixtures for testing.

Provides fixtures for:
- Temporary directories and files
- Mock storage backends
- Database connections (Redis, PostgreSQL)
- Tool executor and execution utilities
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import Dict, Any


# =============================================================================
# Temporary Storage Fixtures
# =============================================================================

@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for testing.
    
    The directory is automatically cleaned up after the test.
    
    Returns:
        Path: Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_file():
    """
    Create a temporary file for testing.
    
    The file is automatically cleaned up after the test.
    
    Returns:
        Path: Path to temporary file
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    
    yield tmp_path
    
    # Cleanup
    if tmp_path.exists():
        tmp_path.unlink()


# =============================================================================
# Tool Executor Fixtures
# =============================================================================

@pytest.fixture
def tool_executor():
    """
    Create a ToolExecutor instance for testing.
    
    Returns:
        ToolExecutor: Configured tool executor
    """
    from aiecs.tools.tool_executor.tool_executor import ToolExecutor
    
    config = {
        'enable_cache': True,
        'cache_size': 50,
        'cache_ttl': 300,
        'max_workers': 2,
        'log_level': 'WARNING',
        'retry_attempts': 2,
        'timeout': 10
    }
    return ToolExecutor(config)


@pytest.fixture
def execution_utils():
    """
    Create an ExecutionUtils instance for testing.
    
    Returns:
        ExecutionUtils: Configured execution utilities
    """
    from aiecs.utils.execution_utils import ExecutionUtils
    
    return ExecutionUtils(
        cache_size=50, 
        cache_ttl=300, 
        retry_attempts=2, 
        retry_backoff=0.5
    )


@pytest.fixture
def operation_executor_config():
    """
    Configuration for OperationExecutor.
    
    Returns:
        dict: Operation executor configuration
    """
    return {
        'rate_limit_requests_per_second': 10,
        'batch_size': 5,
        'enable_cache': True
    }


@pytest.fixture
def operation_executor(tool_executor, execution_utils, operation_executor_config):
    """
    Create an OperationExecutor instance for testing.
    
    Returns:
        OperationExecutor: Configured operation executor
    """
    from aiecs.application.executors.operation_executor import OperationExecutor
    return OperationExecutor(tool_executor, execution_utils, operation_executor_config)


# =============================================================================
# Mock Storage Backends
# =============================================================================

class MockStorageBackend:
    """Mock storage backend for testing."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.call_history = []
    
    def store(self, key: str, value: Any):
        """Store a value."""
        self.data[key] = value
        self.call_history.append(('store', key, value))
    
    def retrieve(self, key: str) -> Any:
        """Retrieve a value."""
        self.call_history.append(('retrieve', key))
        return self.data.get(key)
    
    def delete(self, key: str):
        """Delete a value."""
        self.call_history.append(('delete', key))
        if key in self.data:
            del self.data[key]
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        self.call_history.append(('exists', key))
        return key in self.data
    
    def clear(self):
        """Clear all data."""
        self.data = {}
        self.call_history = []


@pytest.fixture
def mock_storage():
    """
    Create a mock storage backend for testing.
    
    Returns:
        MockStorageBackend: Mock storage backend
    """
    return MockStorageBackend()


# =============================================================================
# Callback Fixtures
# =============================================================================

@pytest.fixture
def mock_save_callback():
    """
    Create a mock save callback for testing.
    
    Returns:
        MockSaveCallback: Mock callback that records calls
    """
    class MockSaveCallback:
        def __init__(self):
            self.calls = []
        
        async def __call__(self, user_id: str, task_id: str, step: int, result):
            self.calls.append((user_id, task_id, step, result))
        
        def reset(self):
            self.calls = []
    
    return MockSaveCallback()


# =============================================================================
# Redis Fixtures (for integration tests)
# =============================================================================

@pytest.fixture
def redis_config():
    """
    Redis configuration for testing.
    
    Returns:
        dict: Redis configuration
    """
    return {
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'db': int(os.getenv('REDIS_DB', 0)),
        'password': os.getenv('REDIS_PASSWORD'),
        'decode_responses': True
    }


@pytest.fixture
def skip_if_no_redis():
    """
    Skip test if Redis is not available.
    
    Usage:
        def test_something(skip_if_no_redis):
            # test code
    """
    import socket
    
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((redis_host, redis_port))
        sock.close()
        
        if result != 0:
            pytest.skip("Redis is not available")
    except Exception:
        pytest.skip("Redis is not available")


# =============================================================================
# PostgreSQL Fixtures (for integration tests)
# =============================================================================

@pytest.fixture
def postgres_config():
    """
    PostgreSQL configuration for testing.
    
    Returns:
        dict: PostgreSQL configuration
    """
    return {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_PORT', 5432)),
        'database': os.getenv('POSTGRES_DB', 'test_db'),
        'user': os.getenv('POSTGRES_USER', 'test_user'),
        'password': os.getenv('POSTGRES_PASSWORD', 'test_password')
    }


@pytest.fixture
def skip_if_no_postgres():
    """
    Skip test if PostgreSQL is not available.
    
    Usage:
        def test_something(skip_if_no_postgres):
            # test code
    """
    import socket
    
    pg_host = os.getenv('POSTGRES_HOST', 'localhost')
    pg_port = int(os.getenv('POSTGRES_PORT', 5432))
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((pg_host, pg_port))
        sock.close()
        
        if result != 0:
            pytest.skip("PostgreSQL is not available")
    except Exception:
        pytest.skip("PostgreSQL is not available")

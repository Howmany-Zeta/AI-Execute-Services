"""
Pytest configuration for comprehensive operation executor tests.
Provides fixtures and setup for testing without mocks.
"""
import pytest
import tempfile
import os
from pathlib import Path
import pandas as pd

from aiecs.tools.tool_executor.tool_executor import ToolExecutor
from aiecs.utils.execution_utils import ExecutionUtils


@pytest.fixture(scope="session")
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent.parent / "data"


@pytest.fixture(scope="session")
def sample_csv_file(test_data_dir):
    """Create a sample CSV file for testing."""
    # Create test data directory if it doesn't exist
    test_data_dir.mkdir(exist_ok=True)
    
    csv_file = test_data_dir / "sample_data.csv"
    if not csv_file.exists():
        data = {
            'name': ['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'],
            'age': [25, 30, 35, 28, 32],
            'salary': [50000, 60000, 70000, 55000, 65000],
            'department': ['IT', 'HR', 'IT', 'Finance', 'IT']
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_file, index=False)
    
    return str(csv_file)


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        data = {
            'x': [1, 2, 3, 4, 5],
            'y': [2, 4, 6, 8, 10],
            'group': ['A', 'A', 'B', 'B', 'C']
        }
        df = pd.DataFrame(data)
        df.to_csv(f.name, index=False)
        yield f.name
    
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


@pytest.fixture
def tool_executor():
    """Create a ToolExecutor instance for testing."""
    config = {
        'enable_cache': True,
        'cache_size': 50,
        'cache_ttl': 300,
        'max_workers': 2,
        'log_level': 'WARNING'
    }
    return ToolExecutor(config)


@pytest.fixture
def execution_utils():
    """Create an ExecutionUtils instance for testing."""
    return ExecutionUtils(cache_size=50, cache_ttl=300, retry_attempts=2, retry_backoff=0.5)


@pytest.fixture
def operation_executor(tool_executor, execution_utils):
    """Create an OperationExecutor instance for testing."""
    config = {
        'rate_limit_requests_per_second': 10,
        'batch_size': 5,
        'enable_cache': True
    }
    from aiecs.application.executors.operation_executor import OperationExecutor
    return OperationExecutor(tool_executor, execution_utils, config)


@pytest.fixture
def mock_save_callback():
    """Create a mock save callback for testing."""
    class MockSaveCallback:
        def __init__(self):
            self.calls = []
        
        async def __call__(self, user_id: str, task_id: str, step: int, result):
            self.calls.append((user_id, task_id, step, result))
    
    return MockSaveCallback()


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables and discover tools."""
    # Set environment variables to avoid issues with heavy dependencies
    os.environ['SKIP_OFFICE_TOOL'] = 'true'
    os.environ['SKIP_IMAGE_TOOL'] = 'true'
    os.environ['SKIP_CHART_TOOL'] = 'true'
    
    # Set environment variables for stats tool to avoid validation issues
    os.environ['STATS_TOOL_MAX_FILE_SIZE_MB'] = '200'
    os.environ['STATS_TOOL_ALLOWED_EXTENSIONS'] = '["csv", "xlsx", "json"]'
    
    # Discover tools to make them available for testing
    from aiecs.tools import discover_tools
    discover_tools()
    
    yield
    # Cleanup if needed
    pass

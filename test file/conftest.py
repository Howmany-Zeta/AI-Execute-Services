import pytest
import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for testing
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment before each test."""
    # Disable metrics for testing to avoid port conflicts
    os.environ["ENABLE_METRICS"] = "false"
    yield
    # Cleanup after test
    if "ENABLE_METRICS" in os.environ:
        del os.environ["ENABLE_METRICS"]

@pytest.fixture
def mock_config():
    """Mock configuration for tests."""
    return {
        "call_timeout_seconds": 600,
        "enable_metrics": False,
        "log_level": "DEBUG"
    }

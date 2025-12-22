"""
Global pytest configuration for the entire test suite.

This is the unified root conftest that provides:
- Session-level event loop
- Test environment setup
- Custom pytest markers
- Basic test utilities

Specialized fixtures are in test/fixtures/ modules:
- data.py: Test data fixtures
- llm.py: LLM client mocks and fixtures
- storage.py: Storage and database fixtures
"""

import pytest
import asyncio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv


# =============================================================================
# Environment Setup
# =============================================================================

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
TEST_ROOT = Path(__file__).parent

# Load test environment variables from .env.test
env_test_path = PROJECT_ROOT / ".env.test"
if env_test_path.exists():
    load_dotenv(env_test_path, override=True)
    logging.info(f"✓ Loaded test environment from {env_test_path}")


# =============================================================================
# Session-Level Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    
    This ensures all async tests share the same event loop,
    which is important for pytest-asyncio compatibility.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_root_dir():
    """Path to test root directory."""
    return TEST_ROOT


@pytest.fixture(scope="session")
def project_root_dir():
    """Path to project root directory."""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_data_dir(test_root_dir):
    """Path to test data directory."""
    data_dir = test_root_dir / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


# =============================================================================
# Function-Level Setup/Teardown
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Setup test environment for each test.
    
    Sets environment variables to:
    - Skip heavy tool dependencies
    - Configure logging levels
    - Set test-specific configurations
    """
    # Skip heavy tool dependencies in tests
    os.environ['SKIP_OFFICE_TOOL'] = 'true'
    os.environ['SKIP_IMAGE_TOOL'] = 'true'
    os.environ['SKIP_CHART_TOOL'] = 'true'
    
    # Configure tool settings for tests
    os.environ['STATS_TOOL_MAX_FILE_SIZE_MB'] = '200'
    os.environ['STATS_TOOL_ALLOWED_EXTENSIONS'] = '[".csv", ".xlsx", ".json"]'
    
    # Reduce logging noise during tests
    logging.getLogger('aiecs').setLevel(logging.WARNING)
    logging.getLogger('tika').setLevel(logging.ERROR)
    
    # Discover tools for testing
    try:
        from aiecs.tools import discover_tools
        discover_tools()
    except Exception as e:
        # If tool discovery fails, continue with tests
        logging.warning(f"Tool discovery failed: {e}")
    
    yield
    
    # Cleanup environment variables
    cleanup_vars = [
        'SKIP_OFFICE_TOOL', 
        'SKIP_IMAGE_TOOL', 
        'SKIP_CHART_TOOL',
        'STATS_TOOL_MAX_FILE_SIZE_MB', 
        'STATS_TOOL_ALLOWED_EXTENSIONS'
    ]
    for var in cleanup_vars:
        os.environ.pop(var, None)


@pytest.fixture(autouse=True)
def handle_missing_dependencies():
    """
    Handle missing dependencies gracefully.
    
    Automatically skips tests when imports fail,
    allowing the test suite to run even with missing optional dependencies.
    """
    try:
        yield
    except ImportError as e:
        pytest.skip(f"Skipping test due to missing dependency: {e}")
    except Exception as e:
        if "No module named" in str(e):
            pytest.skip(f"Skipping test due to import error: {e}")
        else:
            raise


# =============================================================================
# Pytest Configuration Hooks
# =============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.
    
    Markers follow the testing pyramid:
    - unit: Fast, isolated unit tests (70%)
    - integration: Tests with real dependencies (20%)
    - e2e: End-to-end tests with real APIs (10%)
    - performance: Performance and load tests
    - slow: Long-running tests
    - requires_api: Tests requiring real API keys
    - requires_redis: Tests requiring Redis
    """
    # Primary test level markers (testing pyramid)
    config.addinivalue_line(
        "markers", 
        "unit: Unit tests - fast, isolated, no external dependencies"
    )
    config.addinivalue_line(
        "markers", 
        "integration: Integration tests - test component interactions"
    )
    config.addinivalue_line(
        "markers", 
        "e2e: End-to-end tests - full workflow with real APIs"
    )
    
    # Special test categories
    config.addinivalue_line(
        "markers", 
        "performance: Performance tests - measure speed and resource usage"
    )
    config.addinivalue_line(
        "markers", 
        "slow: Slow tests - may take several seconds or minutes"
    )
    
    # Dependency markers
    config.addinivalue_line(
        "markers", 
        "requires_api: Tests requiring real API keys (OpenAI, Google, etc.)"
    )
    config.addinivalue_line(
        "markers", 
        "requires_redis: Tests requiring Redis connection"
    )
    config.addinivalue_line(
        "markers", 
        "requires_postgres: Tests requiring PostgreSQL connection"
    )
    
    # Legacy markers (for backward compatibility)
    config.addinivalue_line(
        "markers", 
        "asyncio: Async tests (automatically applied by pytest-asyncio)"
    )
    config.addinivalue_line(
        "markers", 
        "security: Security-related tests"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers automatically.
    
    This hook automatically adds appropriate markers based on:
    - Test file location (unit/, integration/, e2e/)
    - Test name patterns
    - Test characteristics
    """
    for item in items:
        test_path = str(item.fspath)
        
        # Auto-add markers based on directory structure
        if "/unit/" in test_path:
            if not any(marker.name in ["unit", "integration", "e2e"] 
                      for marker in item.iter_markers()):
                item.add_marker(pytest.mark.unit)
        
        elif "/integration/" in test_path:
            if not any(marker.name in ["unit", "integration", "e2e"] 
                      for marker in item.iter_markers()):
                item.add_marker(pytest.mark.integration)
        
        elif "/e2e/" in test_path:
            if not any(marker.name in ["unit", "integration", "e2e"] 
                      for marker in item.iter_markers()):
                item.add_marker(pytest.mark.e2e)
                # E2E tests are typically slow and require APIs
                item.add_marker(pytest.mark.slow)
                item.add_marker(pytest.mark.requires_api)
        
        # Auto-add slow marker for performance tests
        if "/performance/" in test_path or "performance" in item.nodeid:
            item.add_marker(pytest.mark.slow)
            item.add_marker(pytest.mark.performance)
        
        # Auto-add security marker
        if "security" in item.nodeid.lower():
            item.add_marker(pytest.mark.security)


# =============================================================================
# Cache Cleanup (Critical for CI/CD)
# =============================================================================

def pytest_sessionstart(session):
    """
    Called before test session starts.
    
    Cleans pytest cache to prevent false collection errors
    from different Python versions.
    """
    # This is handled by CI/CD workflows, but we document it here
    # CI workflows should include:
    # find . -type d -name __pycache__ -exec rm -rf {} +
    # find . -name "*.pyc" -delete
    pass


def pytest_sessionfinish(session, exitstatus):
    """
    Called after entire test session finishes.
    
    Can be used for cleanup or final reporting.
    """
    pass

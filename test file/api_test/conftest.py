import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime
from typing import Dict, Any, Optional

# Import the modules we're testing
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.api.user_token import router, TokenUsageResponse, TokenLimitRequest
from app.utils.token_usage_repository import TokenUsageRepository


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()

    # Mock Redis operations
    mock_client.hincrby = AsyncMock(return_value=1)
    mock_client.hget = AsyncMock(return_value=None)
    mock_client.hgetall = AsyncMock(return_value={})
    mock_client.hset = AsyncMock(return_value=1)
    mock_client.get_client = AsyncMock(return_value=mock_client)
    mock_client.ping = AsyncMock(return_value=True)

    # Mock pipeline
    mock_pipeline = AsyncMock()
    mock_pipeline.hincrby = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[1, 1, 1])
    mock_client.pipeline = MagicMock(return_value=mock_pipeline)

    return mock_client


@pytest.fixture
def mock_token_usage_repo(mock_redis_client):
    """Mock token usage repository with predefined behaviors."""
    repo = AsyncMock(spec=TokenUsageRepository)

    # Default return values
    repo.get_usage_stats = AsyncMock(return_value={
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150
    })

    repo.check_usage_limit = AsyncMock(return_value={
        "exceeded": False,
        "current_usage": 150,
        "limit": 1000,
        "remaining": 850
    })

    repo.set_usage_limit = AsyncMock()
    repo.reset_usage = AsyncMock()
    repo.increment_prompt_tokens = AsyncMock()
    repo.increment_completion_tokens = AsyncMock()
    repo.increment_total_usage = AsyncMock()
    repo.increment_detailed_usage = AsyncMock()

    return repo


@pytest.fixture
def app_with_mocked_dependencies(mock_token_usage_repo):
    """Create FastAPI app with mocked dependencies."""
    app = FastAPI()

    # Patch the token_usage_repo import
    with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
        app.include_router(router)
        yield app


@pytest.fixture
def client(app_with_mocked_dependencies):
    """Create test client."""
    return TestClient(app_with_mocked_dependencies)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return "test_user_123"


@pytest.fixture
def sample_cycle_date():
    """Sample cycle start date for testing."""
    return "2025-01-01"


@pytest.fixture
def sample_token_usage_stats():
    """Sample token usage statistics."""
    return {
        "prompt_tokens": 500,
        "completion_tokens": 300,
        "total_tokens": 800
    }


@pytest.fixture
def sample_limit_check_result():
    """Sample limit check result."""
    return {
        "exceeded": False,
        "current_usage": 800,
        "limit": 1000,
        "remaining": 200
    }


@pytest.fixture
def sample_limit_check_exceeded():
    """Sample limit check result when exceeded."""
    return {
        "exceeded": True,
        "current_usage": 1200,
        "limit": 1000,
        "remaining": 0
    }


@pytest.fixture
def sample_token_limit_request():
    """Sample token limit request."""
    return TokenLimitRequest(
        user_id="test_user_123",
        limit=1000,
        cycle_start_date="2025-01-01"
    )


@pytest.fixture
def sample_token_usage_response():
    """Sample token usage response."""
    return TokenUsageResponse(
        user_id="test_user_123",
        cycle_start_date="2025-01-01",
        total_tokens=800,
        prompt_tokens=500,
        completion_tokens=300,
        usage_limit=1000,
        remaining_tokens=200,
        exceeded=False,
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing."""
    with patch('app.api.user_token.datetime') as mock_dt:
        mock_now = Mock()
        mock_now.strftime.return_value = "2025-01-15"
        mock_now.isoformat.return_value = "2025-01-15T12:00:00"
        mock_dt.now.return_value = mock_now
        yield mock_dt


@pytest.fixture
def empty_usage_stats():
    """Empty usage statistics for new users."""
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }


@pytest.fixture
def no_limit_check_result():
    """Limit check result when no limit is set."""
    return {
        "exceeded": False,
        "current_usage": 150,
        "limit": 0,
        "remaining": 0
    }


@pytest.fixture
def redis_error_mock():
    """Mock Redis client that raises errors."""
    mock_client = AsyncMock()
    mock_client.get_client.side_effect = Exception("Redis connection failed")
    return mock_client


@pytest.fixture
def repo_error_mock():
    """Mock repository that raises errors."""
    repo = AsyncMock(spec=TokenUsageRepository)
    repo.get_usage_stats.side_effect = Exception("Database error")
    repo.check_usage_limit.side_effect = Exception("Database error")
    repo.set_usage_limit.side_effect = Exception("Database error")
    repo.reset_usage.side_effect = Exception("Database error")
    return repo


# Utility fixtures for common test scenarios
@pytest.fixture
def high_usage_scenario(mock_token_usage_repo):
    """Configure mock for high usage scenario."""
    mock_token_usage_repo.get_usage_stats.return_value = {
        "prompt_tokens": 8000,
        "completion_tokens": 4000,
        "total_tokens": 12000
    }
    mock_token_usage_repo.check_usage_limit.return_value = {
        "exceeded": True,
        "current_usage": 12000,
        "limit": 10000,
        "remaining": 0
    }
    return mock_token_usage_repo


@pytest.fixture
def no_limit_scenario(mock_token_usage_repo):
    """Configure mock for no limit scenario."""
    mock_token_usage_repo.check_usage_limit.return_value = {
        "exceeded": False,
        "current_usage": 150,
        "limit": 0,
        "remaining": 0
    }
    return mock_token_usage_repo


@pytest.fixture
def new_user_scenario(mock_token_usage_repo):
    """Configure mock for new user scenario."""
    mock_token_usage_repo.get_usage_stats.return_value = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }
    mock_token_usage_repo.check_usage_limit.return_value = {
        "exceeded": False,
        "current_usage": 0,
        "limit": 0,
        "remaining": 0
    }
    return mock_token_usage_repo

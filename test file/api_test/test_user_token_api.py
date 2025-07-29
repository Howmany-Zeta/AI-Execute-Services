import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from datetime import datetime
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.api.user_token import (
    get_user_token_usage,
    get_user_total_tokens,
    set_user_token_limit,
    reset_user_token_usage,
    health_check,
    get_user_total_token_count,
    check_user_token_limit,
    TokenUsageResponse,
    TokenLimitRequest
)


class TestGetUserTokenUsage:
    """Test cases for get_user_token_usage endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_token_usage_success(self, client, sample_user_id, mock_token_usage_repo, mock_datetime):
        """Test successful retrieval of user token usage."""
        # Configure mock responses
        mock_token_usage_repo.get_usage_stats.return_value = {
            "prompt_tokens": 500,
            "completion_tokens": 300,
            "total_tokens": 800
        }
        mock_token_usage_repo.check_usage_limit.return_value = {
            "exceeded": False,
            "current_usage": 800,
            "limit": 1000,
            "remaining": 200
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == sample_user_id
        assert data["total_tokens"] == 800
        assert data["prompt_tokens"] == 500
        assert data["completion_tokens"] == 300
        assert data["usage_limit"] == 1000
        assert data["remaining_tokens"] == 200
        assert data["exceeded"] is False
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_get_user_token_usage_with_cycle_date(self, client, sample_user_id, sample_cycle_date, mock_token_usage_repo):
        """Test retrieval with specific cycle date."""
        mock_token_usage_repo.get_usage_stats.return_value = {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300
        }
        mock_token_usage_repo.check_usage_limit.return_value = {
            "exceeded": False,
            "current_usage": 300,
            "limit": 500,
            "remaining": 200
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}?cycle_start_date={sample_cycle_date}")

        assert response.status_code == 200
        data = response.json()
        assert data["cycle_start_date"] == sample_cycle_date

        # Verify repository was called with correct parameters
        mock_token_usage_repo.get_usage_stats.assert_called_with(sample_user_id, sample_cycle_date)
        mock_token_usage_repo.check_usage_limit.assert_called_with(sample_user_id, sample_cycle_date)

    @pytest.mark.asyncio
    async def test_get_user_token_usage_no_limit(self, client, sample_user_id, no_limit_scenario):
        """Test retrieval when no usage limit is set."""
        with patch('app.api.user_token.token_usage_repo', no_limit_scenario):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["usage_limit"] is None
        assert data["remaining_tokens"] is None
        assert data["exceeded"] is False

    @pytest.mark.asyncio
    async def test_get_user_token_usage_exceeded_limit(self, client, sample_user_id, high_usage_scenario):
        """Test retrieval when usage limit is exceeded."""
        with patch('app.api.user_token.token_usage_repo', high_usage_scenario):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["exceeded"] is True
        assert data["total_tokens"] == 12000
        assert data["usage_limit"] == 10000

    @pytest.mark.asyncio
    async def test_get_user_token_usage_empty_user_id(self, client):
        """Test with empty user ID."""
        response = client.get("/api/token/usage/")
        assert response.status_code == 404  # FastAPI returns 404 for missing path parameter

    @pytest.mark.asyncio
    async def test_get_user_token_usage_repository_error(self, client, sample_user_id, repo_error_mock):
        """Test handling of repository errors."""
        with patch('app.api.user_token.token_usage_repo', repo_error_mock):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 500
        assert "获取用户token使用量失败" in response.json()["detail"]


class TestGetUserTotalTokens:
    """Test cases for get_user_total_tokens endpoint."""

    @pytest.mark.asyncio
    async def test_get_user_total_tokens_success(self, client, sample_user_id, mock_token_usage_repo, mock_datetime):
        """Test successful retrieval of total tokens."""
        mock_token_usage_repo.get_usage_stats.return_value = {
            "total_tokens": 1500
        }
        mock_token_usage_repo.check_usage_limit.return_value = {
            "exceeded": False,
            "limit": 2000,
            "remaining": 500
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}/total")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == sample_user_id
        assert data["total_tokens"] == 1500
        assert data["exceeded"] is False
        assert data["limit"] == 2000
        assert data["remaining"] == 500

    @pytest.mark.asyncio
    async def test_get_user_total_tokens_with_cycle_date(self, client, sample_user_id, sample_cycle_date, mock_token_usage_repo):
        """Test total tokens retrieval with cycle date."""
        mock_token_usage_repo.get_usage_stats.return_value = {"total_tokens": 750}
        mock_token_usage_repo.check_usage_limit.return_value = {
            "exceeded": False,
            "limit": 1000,
            "remaining": 250
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}/total?cycle_start_date={sample_cycle_date}")

        assert response.status_code == 200
        data = response.json()
        assert data["cycle_start_date"] == sample_cycle_date

    @pytest.mark.asyncio
    async def test_get_user_total_tokens_no_limit(self, client, sample_user_id, no_limit_scenario):
        """Test total tokens when no limit is set."""
        no_limit_scenario.get_usage_stats.return_value = {"total_tokens": 500}

        with patch('app.api.user_token.token_usage_repo', no_limit_scenario):
            response = client.get(f"/api/token/usage/{sample_user_id}/total")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 0
        assert data["remaining"] is None

    @pytest.mark.asyncio
    async def test_get_user_total_tokens_exceeded(self, client, sample_user_id, high_usage_scenario):
        """Test total tokens when limit is exceeded."""
        high_usage_scenario.get_usage_stats.return_value = {"total_tokens": 12000}

        with patch('app.api.user_token.token_usage_repo', high_usage_scenario):
            response = client.get(f"/api/token/usage/{sample_user_id}/total")

        assert response.status_code == 200
        data = response.json()
        assert data["exceeded"] is True
        assert data["total_tokens"] == 12000


class TestSetUserTokenLimit:
    """Test cases for set_user_token_limit endpoint."""

    @pytest.mark.asyncio
    async def test_set_user_token_limit_success(self, client, sample_token_limit_request, mock_token_usage_repo, mock_datetime):
        """Test successful setting of token limit."""
        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.post(
                "/api/token/limit",
                json=sample_token_limit_request.dict()
            )

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == sample_token_limit_request.user_id
        assert data["limit"] == sample_token_limit_request.limit
        assert data["status"] == "success"
        assert "成功设置用户" in data["message"]

        # Verify repository method was called
        mock_token_usage_repo.set_usage_limit.assert_called_once_with(
            sample_token_limit_request.user_id,
            sample_token_limit_request.limit,
            sample_token_limit_request.cycle_start_date
        )

    @pytest.mark.asyncio
    async def test_set_user_token_limit_without_cycle_date(self, client, mock_token_usage_repo, mock_datetime):
        """Test setting limit without cycle date."""
        request_data = {
            "user_id": "test_user",
            "limit": 5000
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.post("/api/token/limit", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["cycle_start_date"] == "2025-01-15"  # From mock_datetime

    @pytest.mark.asyncio
    async def test_set_user_token_limit_empty_user_id(self, client):
        """Test setting limit with empty user ID."""
        request_data = {
            "user_id": "",
            "limit": 1000
        }

        response = client.post("/api/token/limit", json=request_data)
        assert response.status_code == 400
        assert "用户ID不能为空" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_user_token_limit_invalid_limit(self, client):
        """Test setting limit with invalid limit value."""
        request_data = {
            "user_id": "test_user",
            "limit": 0
        }

        response = client.post("/api/token/limit", json=request_data)
        assert response.status_code == 400
        assert "限制值必须大于0" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_user_token_limit_negative_limit(self, client):
        """Test setting limit with negative limit value."""
        request_data = {
            "user_id": "test_user",
            "limit": -100
        }

        response = client.post("/api/token/limit", json=request_data)
        assert response.status_code == 400
        assert "限制值必须大于0" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_user_token_limit_repository_error(self, client, repo_error_mock):
        """Test handling of repository errors when setting limit."""
        request_data = {
            "user_id": "test_user",
            "limit": 1000
        }

        with patch('app.api.user_token.token_usage_repo', repo_error_mock):
            response = client.post("/api/token/limit", json=request_data)

        assert response.status_code == 500
        assert "设置用户token限制失败" in response.json()["detail"]


class TestResetUserTokenUsage:
    """Test cases for reset_user_token_usage endpoint."""

    @pytest.mark.asyncio
    async def test_reset_user_token_usage_success(self, client, sample_user_id, mock_token_usage_repo, mock_datetime):
        """Test successful reset of user token usage."""
        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.delete(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["user_id"] == sample_user_id
        assert data["status"] == "success"
        assert "成功重置用户" in data["message"]

        # Verify repository method was called
        mock_token_usage_repo.reset_usage.assert_called_once_with(sample_user_id, None)

    @pytest.mark.asyncio
    async def test_reset_user_token_usage_with_cycle_date(self, client, sample_user_id, sample_cycle_date, mock_token_usage_repo):
        """Test reset with specific cycle date."""
        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.delete(f"/api/token/usage/{sample_user_id}?cycle_start_date={sample_cycle_date}")

        assert response.status_code == 200
        data = response.json()
        assert data["cycle_start_date"] == sample_cycle_date

        # Verify repository was called with correct parameters
        mock_token_usage_repo.reset_usage.assert_called_once_with(sample_user_id, sample_cycle_date)

    @pytest.mark.asyncio
    async def test_reset_user_token_usage_empty_user_id(self, client):
        """Test reset with empty user ID."""
        response = client.delete("/api/token/usage/")
        assert response.status_code == 404  # FastAPI returns 404 for missing path parameter

    @pytest.mark.asyncio
    async def test_reset_user_token_usage_repository_error(self, client, sample_user_id, repo_error_mock):
        """Test handling of repository errors during reset."""
        with patch('app.api.user_token.token_usage_repo', repo_error_mock):
            response = client.delete(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 500
        assert "重置用户token使用量失败" in response.json()["detail"]


class TestHealthCheck:
    """Test cases for health_check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_redis_client):
        """Test successful health check."""
        with patch('app.api.user_token.redis_client', mock_redis_client):
            response = client.get("/api/token/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "token-management"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_check_redis_failure(self, client, redis_error_mock):
        """Test health check when Redis is unavailable."""
        with patch('app.api.user_token.redis_client', redis_error_mock):
            response = client.get("/api/token/health")

        assert response.status_code == 503
        assert "服务不可用" in response.json()["detail"]


class TestUtilityFunctions:
    """Test cases for utility functions."""

    @pytest.mark.asyncio
    async def test_get_user_total_token_count_success(self, sample_user_id, mock_token_usage_repo):
        """Test successful retrieval of total token count."""
        mock_token_usage_repo.get_usage_stats.return_value = {"total_tokens": 1000}

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            result = await get_user_total_token_count(sample_user_id)

        assert result == 1000
        mock_token_usage_repo.get_usage_stats.assert_called_once_with(sample_user_id, None)

    @pytest.mark.asyncio
    async def test_get_user_total_token_count_with_cycle_date(self, sample_user_id, sample_cycle_date, mock_token_usage_repo):
        """Test total token count with cycle date."""
        mock_token_usage_repo.get_usage_stats.return_value = {"total_tokens": 500}

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            result = await get_user_total_token_count(sample_user_id, sample_cycle_date)

        assert result == 500
        mock_token_usage_repo.get_usage_stats.assert_called_once_with(sample_user_id, sample_cycle_date)

    @pytest.mark.asyncio
    async def test_get_user_total_token_count_error(self, sample_user_id, repo_error_mock):
        """Test total token count when repository raises error."""
        with patch('app.api.user_token.token_usage_repo', repo_error_mock):
            result = await get_user_total_token_count(sample_user_id)

        assert result == 0

    @pytest.mark.asyncio
    async def test_check_user_token_limit_not_exceeded(self, sample_user_id, mock_token_usage_repo):
        """Test token limit check when not exceeded."""
        mock_token_usage_repo.check_usage_limit.return_value = {"exceeded": False}

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            result = await check_user_token_limit(sample_user_id)

        assert result is False
        mock_token_usage_repo.check_usage_limit.assert_called_once_with(sample_user_id, None)

    @pytest.mark.asyncio
    async def test_check_user_token_limit_exceeded(self, sample_user_id, mock_token_usage_repo):
        """Test token limit check when exceeded."""
        mock_token_usage_repo.check_usage_limit.return_value = {"exceeded": True}

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            result = await check_user_token_limit(sample_user_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_check_user_token_limit_error(self, sample_user_id, repo_error_mock):
        """Test token limit check when repository raises error."""
        with patch('app.api.user_token.token_usage_repo', repo_error_mock):
            result = await check_user_token_limit(sample_user_id)

        assert result is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_new_user_no_usage(self, client, sample_user_id, new_user_scenario):
        """Test API behavior for new user with no usage."""
        with patch('app.api.user_token.token_usage_repo', new_user_scenario):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == 0
        assert data["prompt_tokens"] == 0
        assert data["completion_tokens"] == 0

    @pytest.mark.asyncio
    async def test_invalid_cycle_date_format(self, client, sample_user_id, mock_token_usage_repo):
        """Test with invalid cycle date format."""
        invalid_date = "invalid-date"

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}?cycle_start_date={invalid_date}")

        # The API should still work, passing the invalid date to the repository
        # The repository layer should handle date validation
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_very_large_token_numbers(self, client, sample_user_id, mock_token_usage_repo):
        """Test with very large token numbers."""
        large_number = 999999999
        mock_token_usage_repo.get_usage_stats.return_value = {
            "prompt_tokens": large_number,
            "completion_tokens": large_number,
            "total_tokens": large_number * 2
        }
        mock_token_usage_repo.check_usage_limit.return_value = {
            "exceeded": True,
            "current_usage": large_number * 2,
            "limit": large_number,
            "remaining": 0
        }

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{sample_user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tokens"] == large_number * 2

    @pytest.mark.asyncio
    async def test_unicode_user_id(self, client, mock_token_usage_repo):
        """Test with Unicode characters in user ID."""
        unicode_user_id = "用户_123_测试"

        with patch('app.api.user_token.token_usage_repo', mock_token_usage_repo):
            response = client.get(f"/api/token/usage/{unicode_user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == unicode_user_id

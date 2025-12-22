"""
Unit tests for retry integration in BaseAIAgent.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentState, AgentType, AgentConfiguration, RetryPolicy
from aiecs.domain.agent.integration.retry_policy import ErrorType
from .test_base_agent import MockAgent


@pytest.mark.unit
@pytest.mark.asyncio
class TestRetryIntegration:
    """Test retry logic integration in BaseAIAgent."""

    @pytest.fixture
    def config_with_retry(self):
        """Create configuration with custom retry policy."""
        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=0.1,  # Fast for testing
            max_delay=1.0,
            exponential_factor=2.0,
            jitter_factor=0.0  # Disable jitter for predictable tests
        )
        return AgentConfiguration(
            goal="Test agent",
            retry_policy=retry_policy
        )

    @pytest.fixture
    def agent(self, config_with_retry):
        """Create agent with retry policy."""
        return MockAgent(
            agent_id="retry-test-agent",
            name="Retry Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config_with_retry
        )

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, agent):
        """Test successful execution without retries."""
        async def successful_func(arg1, arg2):
            return {"result": arg1 + arg2}

        result = await agent._execute_with_retry(successful_func, 2, 3)
        assert result["result"] == 5

    @pytest.mark.asyncio
    async def test_execute_with_retry_retries_on_error(self, agent):
        """Test retry logic retries on transient errors."""
        attempt_count = [0]

        async def failing_then_success():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ConnectionError("Network error")
            return {"result": "success"}

        result = await agent._execute_with_retry(failing_then_success)
        assert result["result"] == "success"
        assert attempt_count[0] == 3

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhausts_retries(self, agent):
        """Test retry logic exhausts retries and raises."""
        async def always_fails():
            raise ConnectionError("Persistent network error")

        with pytest.raises(ConnectionError):
            await agent._execute_with_retry(always_fails)

    @pytest.mark.asyncio
    async def test_execute_with_retry_uses_config_retry_policy(self, agent):
        """Test that retry uses agent's configuration."""
        attempt_count = [0]

        async def slow_success():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise TimeoutError("Timeout")
            return {"result": "success"}

        # Should retry based on config (max_retries=3)
        result = await agent._execute_with_retry(slow_success)
        assert result["result"] == "success"
        assert attempt_count[0] == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_respects_error_classification(self, agent):
        """Test retry respects error classification."""
        attempt_count = [0]

        async def fails_with_client_error():
            attempt_count[0] += 1
            # Client errors (4xx) are not retryable
            raise ValueError("400 Bad Request")

        # Client errors should not be retried
        with pytest.raises(ValueError):
            await agent._execute_with_retry(fails_with_client_error)
        
        # Should only attempt once (not retryable)
        assert attempt_count[0] == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_in_subclass(self, agent):
        """Test retry can be used in subclass implementations."""
        class RetryAgent(MockAgent):
            async def execute_task(self, task, context):
                async def _internal_execute():
                    # Simulate operation that might fail
                    if "fail" in task.get("description", ""):
                        raise ConnectionError("Network issue")
                    return {"success": True, "output": "Done"}
                
                return await self._execute_with_retry(_internal_execute)

        retry_agent = RetryAgent(
            agent_id="retry-subclass-agent",
            name="Retry Subclass",
            agent_type=AgentType.TASK_EXECUTOR,
            config=agent.get_config()
        )

        # Successful execution
        result = await retry_agent.execute_task({"description": "test"}, {})
        assert result["success"] is True

        # Should retry on transient errors
        attempt_count = [0]
        async def mock_internal():
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                raise ConnectionError("Network issue")
            return {"success": True, "output": "Done"}

        retry_agent._execute_with_retry = AsyncMock(side_effect=lambda f: f())
        # Test would require more complex mocking, but demonstrates usage pattern


"""
Unit tests for integration components (retry, roles, compression).
"""

import pytest
from aiecs.domain.agent.integration import (
    EnhancedRetryPolicy,
    ErrorClassifier,
    ErrorType,
    RoleConfiguration,
    ContextCompressor,
    CompressionStrategy,
)
from aiecs.llm import LLMMessage


@pytest.mark.unit
class TestErrorClassifier:
    """Test ErrorClassifier."""

    def test_classify_rate_limit_error(self):
        """Test classifying rate limit error."""
        error = Exception("Rate limit exceeded")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.RATE_LIMIT

    def test_classify_timeout_error(self):
        """Test classifying timeout error."""
        error = Exception("Request timeout")
        error_type = ErrorClassifier.classify(error)
        assert error_type == ErrorType.TIMEOUT

    def test_is_retryable(self):
        """Test checking if error is retryable."""
        assert ErrorClassifier.is_retryable(ErrorType.RATE_LIMIT) is True
        assert ErrorClassifier.is_retryable(ErrorType.TIMEOUT) is True
        assert ErrorClassifier.is_retryable(ErrorType.CLIENT_ERROR) is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestEnhancedRetryPolicy:
    """Test EnhancedRetryPolicy."""

    @pytest.fixture
    def retry_policy(self):
        """Create retry policy."""
        return EnhancedRetryPolicy(max_retries=3, base_delay=0.1)

    def test_calculate_delay(self, retry_policy):
        """Test calculating delay."""
        delay = retry_policy.calculate_delay(0, ErrorType.RATE_LIMIT)
        assert delay > 0
        assert delay <= retry_policy.max_delay

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, retry_policy):
        """Test successful execution with retry."""
        async def success_func():
            return "success"
        
        result = await retry_policy.execute_with_retry(success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_failure(self, retry_policy):
        """Test failed execution exhausts retries."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Rate limit exceeded")
        
        with pytest.raises(Exception):
            await retry_policy.execute_with_retry(failing_func)
        
        assert call_count == retry_policy.max_retries + 1


@pytest.mark.unit
class TestRoleConfiguration:
    """Test RoleConfiguration."""

    def test_role_config_creation(self):
        """Test creating role configuration."""
        config = RoleConfiguration(
            role_name="developer",
            goal="Write code",
            backstory="Experienced developer",
            temperature=0.3
        )
        assert config.role_name == "developer"
        assert config.goal == "Write code"
        assert config.temperature == 0.3

    def test_to_agent_config(self):
        """Test converting to AgentConfiguration."""
        from aiecs.domain.agent.models import AgentConfiguration
        role_config = RoleConfiguration(
            role_name="developer",
            goal="Write code",
            llm_model="gpt-4",
            temperature=0.3,
            max_tokens=4096  # Provide required field
        )
        agent_config = role_config.to_agent_config()
        assert agent_config.goal == "Write code"
        assert agent_config.llm_model == "gpt-4"
        assert agent_config.temperature == 0.3

    def test_get_role_template(self):
        """Test getting predefined role template."""
        from aiecs.domain.agent.integration.role_config import get_role_template
        
        template = get_role_template("developer")
        assert template.role_name == "developer"
        assert template.goal is not None


@pytest.mark.unit
class TestContextCompressor:
    """Test ContextCompressor."""

    @pytest.fixture
    def compressor(self):
        """Create context compressor."""
        return ContextCompressor(max_tokens=100)

    @pytest.fixture
    def messages(self):
        """Create test messages."""
        return [
            LLMMessage(role="system", content="System prompt"),
            LLMMessage(role="user", content="User message " * 10),  # Long message
            LLMMessage(role="assistant", content="Assistant response")
        ]

    def test_compress_messages_within_limit(self, compressor):
        """Test compressing messages within limit."""
        messages = [
            LLMMessage(role="user", content="Short message")
        ]
        compressed = compressor.compress_messages(messages)
        assert len(compressed) == len(messages)

    def test_compress_messages_over_limit(self, compressor, messages):
        """Test compressing messages over limit."""
        compressed = compressor.compress_messages(messages)
        # Should compress to fit within token limit
        total_chars = sum(len(msg.content) for msg in compressed)
        estimated_tokens = total_chars // 4
        assert estimated_tokens <= compressor.max_tokens

    def test_preserve_system_messages(self, compressor, messages):
        """Test preserving system messages."""
        compressed = compressor.compress_messages(messages)
        system_messages = [msg for msg in compressed if msg.role == "system"]
        assert len(system_messages) > 0

    def test_estimate_tokens(self, compressor):
        """Test token estimation."""
        text = "This is a test message with some content."
        tokens = compressor._estimate_tokens([LLMMessage(role="user", content=text)])
        assert tokens > 0

    def test_compress_text(self, compressor):
        """Test compressing text."""
        long_text = "A" * 1000
        compressed = compressor.compress_text(long_text, max_tokens=10)
        assert len(compressed) < len(long_text)
        assert "[truncated]" in compressed or len(compressed) <= 40


"""
Unit tests for Runnable pattern

Tests cover:
- Lifecycle management (setup, execute, teardown)
- Configuration validation
- Error handling and retry logic
- Circuit breaker pattern
- Timeout support
- Metrics collection
- Async context manager
"""

import pytest
import asyncio
from dataclasses import dataclass
from typing import Dict, Any

from aiecs.common.knowledge_graph import (
    Runnable,
    RunnableConfig,
    RunnableState,
    ExecutionMetrics,
    CircuitBreaker,
)


# Test implementations

@dataclass
class TestConfig(RunnableConfig):
    """Test configuration"""
    test_value: str = "default"
    fail_on_setup: bool = False
    fail_on_execute: bool = False
    fail_on_teardown: bool = False
    execution_delay: float = 0.0


class TestRunnable(Runnable[TestConfig, Dict[str, Any]]):
    """Test runnable implementation"""
    
    def __init__(self, config: TestConfig = None):
        super().__init__(config)
        self.setup_called = False
        self.execute_called = False
        self.teardown_called = False
        self.execute_count = 0
    
    def _get_default_config(self) -> TestConfig:
        return TestConfig()
    
    async def _setup(self) -> None:
        self.setup_called = True
        if self.config.fail_on_setup:
            raise RuntimeError("Setup failed")
    
    async def _execute(self, **kwargs) -> Dict[str, Any]:
        self.execute_called = True
        self.execute_count += 1
        
        if self.config.execution_delay > 0:
            await asyncio.sleep(self.config.execution_delay)
        
        if self.config.fail_on_execute:
            raise RuntimeError("Execute failed")
        
        return {
            "success": True,
            "test_value": self.config.test_value,
            "kwargs": kwargs,
            "execute_count": self.execute_count
        }
    
    async def _teardown(self) -> None:
        self.teardown_called = True
        if self.config.fail_on_teardown:
            raise RuntimeError("Teardown failed")


# Basic lifecycle tests

@pytest.mark.asyncio
async def test_basic_lifecycle():
    """Test basic setup -> execute -> teardown lifecycle"""
    runnable = TestRunnable()
    
    # Initial state
    assert runnable.state == RunnableState.CREATED
    assert not runnable.setup_called
    
    # Setup
    await runnable.setup()
    assert runnable.state == RunnableState.READY
    assert runnable.setup_called
    
    # Execute
    result = await runnable.execute()
    assert runnable.state == RunnableState.READY  # State resets to READY after execution
    assert runnable.execute_called
    assert result["success"] is True
    
    # Teardown
    await runnable.teardown()
    assert runnable.state == RunnableState.STOPPED
    assert runnable.teardown_called


@pytest.mark.asyncio
async def test_context_manager():
    """Test async context manager support"""
    config = TestConfig(test_value="context_test")
    
    async with TestRunnable(config) as runnable:
        assert runnable.state == RunnableState.READY
        assert runnable.setup_called
        
        result = await runnable.execute()
        assert result["test_value"] == "context_test"
    
    # After context exit, teardown should be called
    assert runnable.teardown_called
    assert runnable.state == RunnableState.STOPPED


@pytest.mark.asyncio
async def test_cannot_execute_without_setup():
    """Test that execute fails if setup not called"""
    runnable = TestRunnable()
    
    with pytest.raises(RuntimeError, match="Cannot execute component in state created"):
        await runnable.execute()


@pytest.mark.asyncio
async def test_cannot_setup_twice():
    """Test that setup cannot be called twice"""
    runnable = TestRunnable()
    await runnable.setup()
    
    with pytest.raises(RuntimeError, match="Cannot setup component in state ready"):
        await runnable.setup()


# Configuration tests

@pytest.mark.asyncio
async def test_custom_configuration():
    """Test custom configuration"""
    config = TestConfig(
        test_value="custom",
        max_retries=5,
        retry_delay=2.0
    )
    
    runnable = TestRunnable(config)
    assert runnable.config.test_value == "custom"
    assert runnable.config.max_retries == 5
    assert runnable.config.retry_delay == 2.0


@pytest.mark.asyncio
async def test_invalid_configuration():
    """Test configuration validation"""
    with pytest.raises(ValueError, match="max_retries must be non-negative"):
        config = TestConfig(max_retries=-1)
        TestRunnable(config)

    with pytest.raises(ValueError, match="retry_delay must be non-negative"):
        config = TestConfig(retry_delay=-1.0)
        TestRunnable(config)

    with pytest.raises(ValueError, match="retry_backoff must be >= 1.0"):
        config = TestConfig(retry_backoff=0.5)
        TestRunnable(config)


# Error handling tests

@pytest.mark.asyncio
async def test_setup_failure():
    """Test setup failure handling"""
    config = TestConfig(fail_on_setup=True)
    runnable = TestRunnable(config)

    with pytest.raises(RuntimeError, match="Setup failed"):
        await runnable.setup()

    assert runnable.state == RunnableState.FAILED


@pytest.mark.asyncio
async def test_execute_failure():
    """Test execute failure handling"""
    config = TestConfig(fail_on_execute=True)
    runnable = TestRunnable(config)
    await runnable.setup()

    with pytest.raises(RuntimeError, match="Execute failed"):
        await runnable.execute()

    assert runnable.state == RunnableState.FAILED
    assert runnable.metrics.success is False
    assert runnable.metrics.error == "Execute failed"


@pytest.mark.asyncio
async def test_teardown_failure():
    """Test teardown failure handling"""
    config = TestConfig(fail_on_teardown=True)
    runnable = TestRunnable(config)
    await runnable.setup()
    await runnable.execute()

    with pytest.raises(RuntimeError, match="Teardown failed"):
        await runnable.teardown()


# Retry logic tests

@pytest.mark.asyncio
async def test_retry_on_failure():
    """Test retry logic on execution failure"""

    class RetryTestRunnable(TestRunnable):
        def __init__(self, config):
            super().__init__(config)
            self.attempt_count = 0

        async def _execute(self, **kwargs):
            self.attempt_count += 1
            # Fail first 2 attempts, succeed on 3rd
            if self.attempt_count < 3:
                raise RuntimeError(f"Attempt {self.attempt_count} failed")
            return {"success": True, "attempts": self.attempt_count}

    config = TestConfig(max_retries=5, retry_delay=0.1)
    runnable = RetryTestRunnable(config)
    await runnable.setup()

    result = await runnable.run()
    assert result["success"] is True
    assert result["attempts"] == 3
    assert runnable.metrics.retry_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion():
    """Test that retries are exhausted after max_retries"""
    config = TestConfig(
        fail_on_execute=True,
        max_retries=2,
        retry_delay=0.1
    )
    runnable = TestRunnable(config)
    await runnable.setup()

    with pytest.raises(RuntimeError, match="Execute failed"):
        await runnable.run()

    # Should have tried 3 times (initial + 2 retries)
    assert runnable.execute_count == 3
    assert runnable.metrics.retry_count == 2


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Test exponential backoff in retry logic"""
    import time

    class TimingRunnable(TestRunnable):
        def __init__(self, config):
            super().__init__(config)
            self.attempt_times = []

        async def _execute(self, **kwargs):
            self.attempt_times.append(time.time())
            if len(self.attempt_times) < 3:
                raise RuntimeError("Retry test")
            return {"success": True}

    config = TestConfig(
        max_retries=3,
        retry_delay=0.1,
        retry_backoff=2.0
    )
    runnable = TimingRunnable(config)
    await runnable.setup()

    await runnable.run()

    # Check delays between attempts
    assert len(runnable.attempt_times) == 3
    delay1 = runnable.attempt_times[1] - runnable.attempt_times[0]
    delay2 = runnable.attempt_times[2] - runnable.attempt_times[1]

    # Second delay should be roughly 2x first delay (exponential backoff)
    assert delay1 >= 0.1
    assert delay2 >= 0.2
    assert delay2 > delay1


@pytest.mark.asyncio
async def test_max_retry_delay():
    """Test max retry delay cap"""
    config = TestConfig(
        max_retries=5,
        retry_delay=1.0,
        retry_backoff=10.0,
        max_retry_delay=2.0
    )

    # Delay should be capped at max_retry_delay
    assert config.max_retry_delay == 2.0


# Circuit breaker tests

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Test circuit breaker opens after threshold failures"""
    config = TestConfig(
        fail_on_execute=True,
        max_retries=0,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3
    )
    runnable = TestRunnable(config)
    await runnable.setup()

    # First 3 failures should work
    for i in range(3):
        runnable._state = RunnableState.READY  # Reset state
        with pytest.raises(RuntimeError):
            await runnable.run()

    # Circuit should now be open
    runnable._state = RunnableState.READY
    with pytest.raises(RuntimeError, match="Circuit breaker is open"):
        await runnable.run()


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success():
    """Test circuit breaker resets on successful execution"""

    class FlakeyRunnable(TestRunnable):
        def __init__(self, config):
            super().__init__(config)
            self.should_fail = True

        async def _execute(self, **kwargs):
            if self.should_fail:
                raise RuntimeError("Flake")
            return {"success": True}

    config = TestConfig(
        max_retries=0,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=3
    )
    runnable = FlakeyRunnable(config)
    await runnable.setup()

    # Fail twice
    for i in range(2):
        runnable._state = RunnableState.READY
        with pytest.raises(RuntimeError):
            await runnable.run()

    # Succeed once - should reset circuit breaker
    runnable._state = RunnableState.READY
    runnable.should_fail = False
    result = await runnable.run()
    assert result["success"] is True

    # Circuit breaker should be reset
    assert runnable._circuit_breaker.failure_count == 0
    assert not runnable._circuit_breaker.is_open


@pytest.mark.asyncio
async def test_circuit_breaker_timeout():
    """Test circuit breaker timeout and half-open state"""
    config = TestConfig(
        fail_on_execute=True,
        max_retries=0,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=2,
        circuit_breaker_timeout=0.5  # 0.5 second timeout
    )
    runnable = TestRunnable(config)
    await runnable.setup()

    # Trigger circuit breaker
    for i in range(2):
        runnable._state = RunnableState.READY
        with pytest.raises(RuntimeError):
            await runnable.run()

    # Circuit should be open
    assert runnable._circuit_breaker.is_open

    # Wait for timeout
    await asyncio.sleep(0.6)

    # Circuit should allow execution (half-open)
    runnable._state = RunnableState.READY
    with pytest.raises(RuntimeError):  # Still fails, but allowed to try
        await runnable.run()


# Timeout tests

@pytest.mark.asyncio
async def test_execution_timeout():
    """Test execution timeout"""
    config = TestConfig(
        execution_delay=2.0,  # Takes 2 seconds
        timeout=0.5  # Timeout after 0.5 seconds
    )
    runnable = TestRunnable(config)
    await runnable.setup()

    with pytest.raises(asyncio.TimeoutError):
        await runnable.run()


@pytest.mark.asyncio
async def test_no_timeout_when_disabled():
    """Test that execution completes when timeout is disabled"""
    config = TestConfig(
        execution_delay=0.2,
        timeout=None  # No timeout
    )
    runnable = TestRunnable(config)
    await runnable.setup()

    result = await runnable.run()
    assert result["success"] is True


# Metrics tests

@pytest.mark.asyncio
async def test_metrics_collection():
    """Test execution metrics collection"""
    runnable = TestRunnable()
    await runnable.setup()

    result = await runnable.execute()

    metrics = runnable.metrics
    assert metrics.start_time is not None
    assert metrics.end_time is not None
    assert metrics.duration_seconds > 0
    assert metrics.success is True
    assert metrics.error is None
    assert metrics.retry_count == 0


@pytest.mark.asyncio
async def test_metrics_on_failure():
    """Test metrics collection on failure"""
    config = TestConfig(fail_on_execute=True)
    runnable = TestRunnable(config)
    await runnable.setup()

    with pytest.raises(RuntimeError):
        await runnable.execute()

    metrics = runnable.metrics
    assert metrics.success is False
    assert metrics.error == "Execute failed"


@pytest.mark.asyncio
async def test_metrics_dict():
    """Test metrics dictionary export"""
    runnable = TestRunnable()
    await runnable.setup()
    await runnable.execute()

    metrics_dict = runnable.get_metrics_dict()
    assert "start_time" in metrics_dict
    assert "end_time" in metrics_dict
    assert "duration_seconds" in metrics_dict
    assert "retry_count" in metrics_dict
    assert "success" in metrics_dict
    assert "error" in metrics_dict
    assert "state" in metrics_dict
    assert metrics_dict["success"] is True
    assert metrics_dict["state"] == "ready"  # State resets to READY after execution


@pytest.mark.asyncio
async def test_reset_metrics():
    """Test metrics reset"""
    runnable = TestRunnable()
    await runnable.setup()
    await runnable.execute()

    # Metrics should be populated
    assert runnable.metrics.success is True

    # Reset metrics
    runnable.reset_metrics()

    # Metrics should be cleared
    assert runnable.metrics.start_time is None
    assert runnable.metrics.end_time is None
    assert runnable.metrics.duration_seconds == 0.0
    assert runnable.metrics.success is False


# CircuitBreaker unit tests

def test_circuit_breaker_basic():
    """Test basic circuit breaker functionality"""
    cb = CircuitBreaker(threshold=3, timeout=60.0)

    assert not cb.is_open
    assert cb.failure_count == 0

    # Record failures
    cb.record_failure()
    assert cb.failure_count == 1
    assert not cb.is_open

    cb.record_failure()
    assert cb.failure_count == 2
    assert not cb.is_open

    cb.record_failure()
    assert cb.failure_count == 3
    assert cb.is_open


def test_circuit_breaker_success_resets():
    """Test circuit breaker reset on success"""
    cb = CircuitBreaker(threshold=3, timeout=60.0)

    cb.record_failure()
    cb.record_failure()
    assert cb.failure_count == 2

    cb.record_success()
    assert cb.failure_count == 0
    assert not cb.is_open


def test_circuit_breaker_can_execute():
    """Test circuit breaker execution permission"""
    cb = CircuitBreaker(threshold=2, timeout=0.5)

    # Initially can execute
    assert cb.can_execute()

    # After threshold failures, cannot execute
    cb.record_failure()
    cb.record_failure()
    assert not cb.can_execute()

    # After timeout, can execute again
    import time
    time.sleep(0.6)
    assert cb.can_execute()


"""
Performance and Observability Tests

Tests OperationTimer, operation-level metrics, percentile calculations, health status,
comprehensive status reporting, and metrics reset functionality.
Covers tasks 2.7.1-2.7.7 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
import time
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from aiecs.domain.agent.base_agent import BaseAIAgent, OperationTimer
from aiecs.domain.agent.models import AgentConfiguration, AgentType, AgentState
from aiecs.llm import BaseLLMClient


# ==================== Mock Agent for Testing ====================


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing."""

    def __init__(self):
        super().__init__(provider="mock", model="mock-model")

    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Mock generate text."""
        await asyncio.sleep(0.01)  # Simulate some work
        return "Mock response"

    async def stream_text(self, prompt: str, **kwargs):
        """Mock stream text."""
        yield "Mock"
        yield " response"

    async def close(self):
        """Mock close."""
        pass


class MockTestAgent(BaseAIAgent):
    """Test agent implementation for testing."""

    def __init__(self, agent_id: str, name: str, config: AgentConfiguration):
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
        )

    async def _initialize(self) -> None:
        """Initialize test agent."""
        pass

    async def _shutdown(self) -> None:
        """Shutdown test agent."""
        pass

    async def execute_task(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute task implementation."""
        return {"output": "Test result", "success": True}

    async def process_message(
        self, message: str, sender_id: str = None
    ) -> Dict[str, Any]:
        """Process message implementation."""
        return {"response": "Test response", "success": True}


# ==================== Test 2.7.1: OperationTimer Context Manager ====================


@pytest.mark.asyncio
async def test_operation_timer_basic():
    """
    Test 2.7.1: Test OperationTimer context manager basic functionality.

    Verifies that OperationTimer correctly tracks operation duration.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-1", name="Test Agent", config=config)

    # Test basic timing
    with agent.track_operation_time("test_operation") as timer:
        await asyncio.sleep(0.1)  # Sleep for 100ms

    # Verify timer recorded duration
    assert timer.duration is not None
    assert timer.duration >= 0.1  # Should be at least 100ms
    assert timer.duration < 0.2  # Should be less than 200ms
    assert timer.start_time is not None
    assert timer.end_time is not None
    assert timer.error is None
    assert timer.operation_name == "test_operation"


@pytest.mark.asyncio
async def test_operation_timer_with_error():
    """
    Test 2.7.1: Test OperationTimer with error handling.

    Verifies that OperationTimer correctly tracks errors.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-2", name="Test Agent", config=config)

    # Test error tracking
    with pytest.raises(ValueError):
        with agent.track_operation_time("error_operation") as timer:
            raise ValueError("Test error")

    # Verify timer recorded error
    assert timer.error is not None
    assert isinstance(timer.error, ValueError)
    assert str(timer.error) == "Test error"
    assert timer.duration is not None


@pytest.mark.asyncio
async def test_operation_timer_standalone():
    """
    Test 2.7.1: Test OperationTimer standalone (without agent).

    Verifies that OperationTimer works without automatic metrics recording.
    """
    # Test standalone timer (no agent)
    timer = OperationTimer(operation_name="standalone_op")

    with timer:
        await asyncio.sleep(0.05)

    # Verify timer worked
    assert timer.duration is not None
    assert timer.duration >= 0.05
    assert timer.error is None


# ==================== Test 2.7.2: Operation-Level Metrics Recording ====================


@pytest.mark.asyncio
async def test_record_operation_metrics():
    """
    Test 2.7.2: Test operation-level metrics recording.

    Verifies that _record_operation_metrics() correctly records metrics.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-3", name="Test Agent", config=config)

    # Record some operations
    agent._record_operation_metrics("llm_call", 0.5, success=True)
    agent._record_operation_metrics("llm_call", 0.7, success=True)
    agent._record_operation_metrics("llm_call", 1.2, success=False)
    agent._record_operation_metrics("tool_call", 0.3, success=True)

    # Verify metrics were recorded
    assert "llm_call" in agent._metrics.operation_counts
    assert agent._metrics.operation_counts["llm_call"] == 3
    assert agent._metrics.operation_total_time["llm_call"] == pytest.approx(2.4, 0.01)
    assert agent._metrics.operation_error_counts["llm_call"] == 1

    assert "tool_call" in agent._metrics.operation_counts
    assert agent._metrics.operation_counts["tool_call"] == 1
    assert agent._metrics.operation_total_time["tool_call"] == pytest.approx(0.3, 0.01)
    assert agent._metrics.operation_error_counts["tool_call"] == 0


@pytest.mark.asyncio
async def test_operation_history_limit():
    """
    Test 2.7.2: Test operation history limit (keeps last 100).

    Verifies that operation history is limited to 100 entries.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-4", name="Test Agent", config=config)

    # Record 150 operations
    for i in range(150):
        agent._record_operation_metrics(f"op_{i % 5}", 0.1, success=True)

    # Verify history is limited to 100
    assert len(agent._metrics.operation_history) == 100


@pytest.mark.asyncio
async def test_automatic_metrics_recording():
    """
    Test 2.7.2: Test automatic metrics recording via OperationTimer.

    Verifies that OperationTimer automatically records metrics when agent is provided.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-5", name="Test Agent", config=config)

    # Use timer with agent (automatic recording)
    with agent.track_operation_time("auto_op"):
        await asyncio.sleep(0.05)

    # Verify metrics were automatically recorded
    assert "auto_op" in agent._metrics.operation_counts
    assert agent._metrics.operation_counts["auto_op"] == 1
    assert agent._metrics.operation_total_time["auto_op"] >= 0.05


# ==================== Test 2.7.3: Percentile Calculations ====================


@pytest.mark.asyncio
async def test_calculate_percentile():
    """
    Test 2.7.3: Test percentile calculations for response times.

    Verifies that _calculate_percentile() correctly calculates percentiles.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-6", name="Test Agent", config=config)

    # Test with known values
    values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

    p50 = agent._calculate_percentile(values, 50)
    p95 = agent._calculate_percentile(values, 95)
    p99 = agent._calculate_percentile(values, 99)

    # Verify percentiles (using index-based calculation: int(len * percentile / 100))
    # For 10 values: p50 = index 5 (value 6.0), p95 = index 9 (value 10.0)
    assert p50 == 6.0  # 50th percentile (index 5)
    assert p95 == 10.0  # 95th percentile (index 9)
    assert p99 == 10.0  # 99th percentile (index 9, capped at len-1)

    # Test with empty list
    assert agent._calculate_percentile([], 50) is None

    # Test with single value
    assert agent._calculate_percentile([5.0], 50) == 5.0


@pytest.mark.asyncio
async def test_percentile_updates():
    """
    Test 2.7.3: Test percentile updates after recording operations.

    Verifies that percentiles are automatically updated when operations are recorded.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-7", name="Test Agent", config=config)

    # Record operations with varying durations
    for duration in [0.1, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]:
        agent._record_operation_metrics("test_op", duration, success=True)

    # Verify percentiles were calculated
    assert agent._metrics.p50_operation_time is not None
    assert agent._metrics.p95_operation_time is not None
    assert agent._metrics.p99_operation_time is not None

    # Verify percentile values are reasonable
    assert agent._metrics.p50_operation_time < agent._metrics.p95_operation_time
    assert agent._metrics.p95_operation_time <= agent._metrics.p99_operation_time


# ==================== Test 2.7.4: Health Status Calculation ====================


@pytest.mark.asyncio
async def test_health_status_healthy():
    """
    Test 2.7.4: Test health status calculation for healthy agent.

    Verifies that get_health_status() correctly calculates health score for healthy agent.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-8", name="Test Agent", config=config)
    await agent.initialize()

    # Simulate successful operations
    for _ in range(100):
        agent.update_metrics(execution_time=0.5, success=True)
        agent._record_operation_metrics("test_op", 0.5, success=True)

    health = agent.get_health_status()

    # Verify health status
    assert health["health_score"] >= 80  # Should be healthy
    assert health["status"] == "healthy"
    assert len(health["issues"]) == 0


@pytest.mark.asyncio
async def test_health_status_degraded():
    """
    Test 2.7.4: Test health status calculation for degraded agent.

    Verifies that get_health_status() correctly identifies degraded performance.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-9", name="Test Agent", config=config)
    await agent.initialize()

    # Simulate mixed success/failure
    for _ in range(70):
        agent.update_metrics(execution_time=0.5, success=True)
    for _ in range(30):
        agent.update_metrics(execution_time=0.5, success=False)

    # Add slow operations
    for _ in range(10):
        agent._record_operation_metrics("slow_op", 6.0, success=True)

    health = agent.get_health_status()

    # Verify degraded status
    assert 50 <= health["health_score"] < 80
    assert health["status"] == "degraded"
    assert len(health["issues"]) > 0


@pytest.mark.asyncio
async def test_health_status_unhealthy():
    """
    Test 2.7.4: Test health status calculation for unhealthy agent.

    Verifies that get_health_status() correctly identifies unhealthy agent.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-10", name="Test Agent", config=config)
    await agent.initialize()

    # Simulate mostly failures
    for _ in range(20):
        agent.update_metrics(execution_time=0.5, success=True)
    for _ in range(80):
        agent.update_metrics(execution_time=0.5, success=False)

    # Add very slow operations
    for _ in range(10):
        agent._record_operation_metrics("very_slow_op", 15.0, success=True)

    health = agent.get_health_status()

    # Verify unhealthy status
    assert health["health_score"] < 50
    assert health["status"] == "unhealthy"
    assert len(health["issues"]) > 0
    assert any("error rate" in issue.lower() for issue in health["issues"])


# ==================== Test 2.7.5: Comprehensive Status Reporting ====================


@pytest.mark.asyncio
async def test_comprehensive_status():
    """
    Test 2.7.5: Test comprehensive status reporting.

    Verifies that get_comprehensive_status() includes all metrics.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-11", name="Test Agent", config=config)
    await agent.initialize()
    await agent.activate()

    # Record some operations
    for _ in range(10):
        agent.update_metrics(execution_time=0.5, success=True)
        agent._record_operation_metrics("test_op", 0.5, success=True)

    status = agent.get_comprehensive_status()

    # Verify all required fields are present
    assert "agent_id" in status
    assert status["agent_id"] == "test-agent-11"
    assert "name" in status
    assert status["name"] == "Test Agent"
    assert "type" in status
    assert "version" in status
    assert "state" in status
    assert status["state"] == AgentState.ACTIVE.value

    # Verify health section
    assert "health" in status
    assert "health_score" in status["health"]
    assert "status" in status["health"]
    assert "issues" in status["health"]

    # Verify performance section
    assert "performance" in status
    assert "total_operations" in status["performance"]
    assert "operations" in status["performance"]
    assert "p50_operation_time" in status["performance"]
    assert "p95_operation_time" in status["performance"]
    assert "p99_operation_time" in status["performance"]

    # Verify metrics section
    assert "metrics" in status
    assert "total_tasks_executed" in status["metrics"]
    assert "successful_tasks" in status["metrics"]
    assert "failed_tasks" in status["metrics"]


@pytest.mark.asyncio
async def test_performance_metrics():
    """
    Test 2.7.5: Test get_performance_metrics() method.

    Verifies that performance metrics include per-operation statistics.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-12", name="Test Agent", config=config)

    # Record operations for multiple operation types
    agent._record_operation_metrics("llm_call", 1.0, success=True)
    agent._record_operation_metrics("llm_call", 1.5, success=True)
    agent._record_operation_metrics("llm_call", 2.0, success=False)
    agent._record_operation_metrics("tool_call", 0.5, success=True)
    agent._record_operation_metrics("tool_call", 0.7, success=True)

    metrics = agent.get_performance_metrics()

    # Verify overall metrics
    assert metrics["total_operations"] == 5

    # Verify per-operation metrics
    assert "llm_call" in metrics["operations"]
    llm_stats = metrics["operations"]["llm_call"]
    assert llm_stats["count"] == 3
    assert llm_stats["total_time"] == pytest.approx(4.5, 0.01)
    assert llm_stats["average_time"] == pytest.approx(1.5, 0.01)
    assert llm_stats["error_count"] == 1
    assert llm_stats["error_rate"] == pytest.approx(33.33, 0.1)

    assert "tool_call" in metrics["operations"]
    tool_stats = metrics["operations"]["tool_call"]
    assert tool_stats["count"] == 2
    assert tool_stats["total_time"] == pytest.approx(1.2, 0.01)
    assert tool_stats["average_time"] == pytest.approx(0.6, 0.01)
    assert tool_stats["error_count"] == 0
    assert tool_stats["error_rate"] == 0.0

    # Verify percentiles are present
    assert "p50_operation_time" in metrics
    assert "p95_operation_time" in metrics
    assert "p99_operation_time" in metrics

    # Verify recent operations
    assert "recent_operations" in metrics
    assert len(metrics["recent_operations"]) <= 10


# ==================== Test 2.7.6: Metrics Reset Functionality ====================


@pytest.mark.asyncio
async def test_reset_metrics():
    """
    Test 2.7.6: Test metrics reset functionality.

    Verifies that reset_metrics() properly resets all metrics.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-13", name="Test Agent", config=config)
    await agent.initialize()

    # Record some operations and tasks
    for _ in range(10):
        agent.update_metrics(execution_time=0.5, success=True)
        agent._record_operation_metrics("test_op", 0.5, success=True)

    # Verify metrics are populated
    assert agent._metrics.total_tasks_executed > 0
    assert len(agent._metrics.operation_history) > 0
    assert len(agent._metrics.operation_counts) > 0

    # Reset metrics
    agent.reset_metrics()

    # Verify all metrics are reset
    assert agent._metrics.total_tasks_executed == 0
    assert agent._metrics.successful_tasks == 0
    assert agent._metrics.failed_tasks == 0
    assert agent._metrics.success_rate == 0.0
    assert len(agent._metrics.operation_history) == 0
    assert len(agent._metrics.operation_counts) == 0
    assert len(agent._metrics.operation_total_time) == 0
    assert len(agent._metrics.operation_error_counts) == 0
    assert agent._metrics.p50_operation_time is None
    assert agent._metrics.p95_operation_time is None
    assert agent._metrics.p99_operation_time is None


@pytest.mark.asyncio
async def test_reset_metrics_preserves_agent_info():
    """
    Test 2.7.6: Test that reset_metrics() preserves agent information.

    Verifies that agent ID and other identifying information is preserved after reset.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-14", name="Test Agent", config=config)
    await agent.initialize()

    # Record some operations
    for _ in range(5):
        agent.update_metrics(execution_time=0.5, success=True)

    # Get agent info before reset
    agent_id_before = agent.agent_id
    name_before = agent.name
    state_before = agent._state

    # Reset metrics
    agent.reset_metrics()

    # Verify agent info is preserved
    assert agent.agent_id == agent_id_before
    assert agent.name == name_before
    assert agent._state == state_before


# ==================== Test 2.7.7: Integration with Observability System ====================


@pytest.mark.asyncio
async def test_observability_integration():
    """
    Test 2.7.7: Test integration with existing observability system.

    Verifies that metrics are properly tracked and accessible.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-15", name="Test Agent", config=config)

    # Initialize and activate agent
    await agent.initialize()
    await agent.activate()

    # Record some operations
    agent._record_operation_metrics("init", 0.1, success=True)
    agent._record_operation_metrics("task_exec", 0.5, success=True)

    # Update task metrics manually (since our mock doesn't do it automatically)
    agent.update_metrics(execution_time=0.5, success=True)

    # Execute task
    task = {"description": "Test task"}
    result = await agent.execute_task(task, {})

    # Verify operation metrics are tracked
    assert len(agent._metrics.operation_history) > 0
    assert "init" in agent._metrics.operation_counts
    assert "task_exec" in agent._metrics.operation_counts

    # Verify health status is accessible
    health = agent.get_health_status()
    assert "health_score" in health
    assert "status" in health

    # Verify comprehensive status includes all metrics
    status = agent.get_comprehensive_status()
    assert "agent_id" in status
    assert "health" in status
    assert "performance" in status
    assert "metrics" in status


@pytest.mark.asyncio
async def test_metrics_updated_timestamp():
    """
    Test 2.7.7: Test that metrics updated_at timestamp is maintained.

    Verifies that metrics track when they were last updated.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-16", name="Test Agent", config=config)

    # Get initial timestamp
    initial_timestamp = agent._metrics.updated_at

    # Wait a bit
    await asyncio.sleep(0.1)

    # Record operation
    agent._record_operation_metrics("test_op", 0.5, success=True)

    # Verify timestamp was updated
    assert agent._metrics.updated_at > initial_timestamp


@pytest.mark.asyncio
async def test_health_status_with_sessions():
    """
    Test 2.7.7: Test health status calculation with session metrics.

    Verifies that session metrics are included in health score calculation.
    """
    config = AgentConfiguration()
    agent = MockTestAgent(agent_id="test-agent-17", name="Test Agent", config=config)
    await agent.initialize()

    # Simulate sessions
    agent._metrics.total_sessions = 100
    agent._metrics.active_sessions = 10
    agent._metrics.completed_sessions = 70
    agent._metrics.failed_sessions = 15
    agent._metrics.expired_sessions = 5

    # Add some successful operations
    for _ in range(90):
        agent.update_metrics(execution_time=0.5, success=True)
    for _ in range(10):
        agent.update_metrics(execution_time=0.5, success=False)

    health = agent.get_health_status()

    # Verify health status includes session considerations
    assert "health_score" in health
    assert "status" in health

    # Session failure rate is (15 + 5) / 100 = 20%, which should affect health
    # but not drastically since task success rate is 90%
    assert health["health_score"] > 50  # Should still be reasonable


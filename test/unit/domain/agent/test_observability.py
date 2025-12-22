"""
Unit tests for agent observability.
"""

import pytest
from datetime import datetime
from aiecs.domain.agent.observability import (
    LoggingObserver,
    MetricsObserver,
    AgentController,
)
from aiecs.domain.agent.models import AgentState, AgentType, AgentConfiguration
from .test_base_agent import MockAgent


@pytest.mark.unit
class TestLoggingObserver:
    """Test LoggingObserver."""

    @pytest.fixture
    def observer(self):
        """Create logging observer."""
        return LoggingObserver()

    def test_on_state_changed(self, observer):
        """Test state change notification."""
        observer.on_state_changed(
            "agent-1",
            AgentState.CREATED,
            AgentState.ACTIVE,
            datetime.utcnow()
        )
        # Should not raise

    def test_on_task_started(self, observer):
        """Test task started notification."""
        observer.on_task_started(
            "agent-1",
            "task-1",
            {"description": "Test task"},
            datetime.utcnow()
        )
        # Should not raise

    def test_on_task_completed(self, observer):
        """Test task completed notification."""
        observer.on_task_completed(
            "agent-1",
            "task-1",
            {"output": "Result"},
            datetime.utcnow()
        )
        # Should not raise

    def test_on_task_failed(self, observer):
        """Test task failed notification."""
        observer.on_task_failed(
            "agent-1",
            "task-1",
            Exception("Test error"),
            datetime.utcnow()
        )
        # Should not raise

    def test_on_tool_called(self, observer):
        """Test tool called notification."""
        observer.on_tool_called(
            "agent-1",
            "tool-1",
            {"param": "value"},
            datetime.utcnow()
        )
        # Should not raise


@pytest.mark.unit
class TestMetricsObserver:
    """Test MetricsObserver."""

    @pytest.fixture
    def observer(self):
        """Create metrics observer."""
        return MetricsObserver()

    def test_on_state_changed(self, observer):
        """Test state change tracking."""
        observer.on_state_changed(
            "agent-1",
            AgentState.CREATED,
            AgentState.ACTIVE,
            datetime.utcnow()
        )
        metrics = observer.get_metrics()
        assert metrics["state_changes"] == 1

    def test_on_task_started(self, observer):
        """Test task started tracking."""
        observer.on_task_started(
            "agent-1",
            "task-1",
            {"description": "Test"},
            datetime.utcnow()
        )
        metrics = observer.get_metrics()
        assert metrics["task_events"] == 1

    def test_on_task_completed(self, observer):
        """Test task completed tracking."""
        observer.on_task_completed(
            "agent-1",
            "task-1",
            {"output": "Result"},
            datetime.utcnow()
        )
        metrics = observer.get_metrics()
        assert metrics["task_events"] == 1

    def test_on_tool_called(self, observer):
        """Test tool call tracking."""
        observer.on_tool_called(
            "agent-1",
            "tool-1",
            {"param": "value"},
            datetime.utcnow()
        )
        metrics = observer.get_metrics()
        assert metrics["tool_calls"] == 1

    def test_get_metrics(self, observer):
        """Test getting metrics."""
        observer.on_state_changed(
            "agent-1",
            AgentState.CREATED,
            AgentState.ACTIVE,
            datetime.utcnow()
        )
        metrics = observer.get_metrics()
        assert "state_changes" in metrics
        assert "task_events" in metrics
        assert "tool_calls" in metrics

    def test_clear_metrics(self, observer):
        """Test clearing metrics."""
        observer.on_state_changed(
            "agent-1",
            AgentState.CREATED,
            AgentState.ACTIVE,
            datetime.utcnow()
        )
        observer.clear()
        metrics = observer.get_metrics()
        assert metrics["state_changes"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
class TestAgentController:
    """Test AgentController."""

    @pytest.fixture
    def agent(self):
        """Create test agent."""
        config = AgentConfiguration()
        return MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )

    @pytest.fixture
    def controller(self, agent):
        """Create agent controller."""
        return AgentController(agent)

    def test_add_observer(self, controller):
        """Test adding observer."""
        observer = LoggingObserver()
        controller.add_observer(observer)
        assert len(controller.observers) == 1

    def test_remove_observer(self, controller):
        """Test removing observer."""
        observer = LoggingObserver()
        controller.add_observer(observer)
        controller.remove_observer(observer)
        assert len(controller.observers) == 0

    def test_notify_state_changed(self, controller):
        """Test state change notification."""
        observer = MetricsObserver()
        controller.add_observer(observer)
        controller.notify_state_changed(AgentState.CREATED, AgentState.ACTIVE)
        metrics = observer.get_metrics()
        assert metrics["state_changes"] == 1

    @pytest.mark.asyncio
    async def test_execute_task_with_observation(self, controller, agent):
        """Test executing task with observation."""
        await agent.initialize()
        await agent.activate()
        
        observer = MetricsObserver()
        controller.add_observer(observer)
        
        task = {"description": "Test task", "task_id": "task-1"}
        result = await controller.execute_task_with_observation(task, {})
        
        assert result["success"] is True
        metrics = observer.get_metrics()
        assert metrics["task_events"] >= 1  # At least started event


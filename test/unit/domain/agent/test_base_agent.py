"""
Unit tests for BaseAIAgent.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import (
    AgentState,
    AgentType,
    AgentConfiguration,
    AgentGoal,
    GoalStatus,
    GoalPriority,
    MemoryType,
)
from aiecs.domain.agent.exceptions import InvalidStateTransitionError


# Create a concrete implementation for testing
class MockAgent(BaseAIAgent):
    """Concrete agent implementation for testing."""

    async def _initialize(self) -> None:
        """Initialize test agent."""
        pass

    async def _shutdown(self) -> None:
        """Shutdown test agent."""
        pass

    async def execute_task(self, task: dict, context: dict) -> dict:
        """Execute test task."""
        return {"success": True, "output": "test result"}

    async def process_message(self, message: str, sender_id: str = None) -> dict:
        """Process test message."""
        return {"response": "test response"}


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseAIAgent:
    """Test BaseAIAgent functionality."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AgentConfiguration(
            goal="Test agent goal",
            temperature=0.7
        )

    @pytest.fixture
    def agent(self, config):
        """Create test agent."""
        return MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "test-agent-1"
        assert agent.name == "Test Agent"
        assert agent.agent_type == AgentType.CONVERSATIONAL
        assert agent.state == AgentState.CREATED
        assert agent.created_at is not None

    def test_state_transitions(self, agent):
        """Test state transitions."""
        # Valid transitions
        agent._transition_state(AgentState.INITIALIZING)
        assert agent.state == AgentState.INITIALIZING
        
        agent._transition_state(AgentState.ACTIVE)
        assert agent.state == AgentState.ACTIVE

    def test_invalid_state_transition(self, agent):
        """Test invalid state transition raises error."""
        # Cannot transition directly from CREATED to ACTIVE
        with pytest.raises(InvalidStateTransitionError):
            agent._transition_state(AgentState.ACTIVE)

    @pytest.mark.asyncio
    async def test_lifecycle_initialize(self, agent):
        """Test agent initialization lifecycle."""
        await agent.initialize()
        # After initialize, state transitions through INITIALIZING to ACTIVE
        assert agent.state == AgentState.ACTIVE

    @pytest.mark.asyncio
    async def test_lifecycle_activate(self, agent):
        """Test agent activation."""
        await agent.initialize()
        await agent.activate()
        assert agent.state == AgentState.ACTIVE

    @pytest.mark.asyncio
    async def test_lifecycle_deactivate(self, agent):
        """Test agent deactivation."""
        await agent.initialize()
        await agent.activate()
        await agent.deactivate()
        assert agent.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_lifecycle_shutdown(self, agent):
        """Test agent shutdown."""
        await agent.initialize()
        await agent.activate()
        await agent.shutdown()
        assert agent.state == AgentState.STOPPED

    @pytest.mark.asyncio
    async def test_memory_operations(self, agent):
        """Test memory operations."""
        # Add to memory - add_to_memory is async
        await agent.add_to_memory("key1", "value1", metadata={"type": "test"})
        memory = await agent.retrieve_memory("key1")
        assert memory == "value1"
        
        # Retrieve memory
        memory = await agent.retrieve_memory("key1")
        assert memory == "value1"
        
        # Clear memory - clear_memory is async
        await agent.clear_memory()
        memory = await agent.retrieve_memory("key1")
        assert memory is None

    def test_goal_management(self, agent):
        """Test goal management."""
        # Set goal - set_goal expects description string, not AgentGoal object
        goal_id = agent.set_goal(
            description="Complete task",
            priority=GoalPriority.HIGH
        )
        
        # Get goals
        goals = agent.get_goals()
        assert len(goals) == 1
        assert goals[0].goal_id == goal_id
        
        # Update goal status
        agent.update_goal_status(goal_id, GoalStatus.ACHIEVED)
        updated_goal = agent.get_goal(goal_id)
        assert updated_goal.status == GoalStatus.ACHIEVED

    def test_configuration_management(self, agent, config):
        """Test configuration management."""
        # Get config
        retrieved_config = agent.get_config()
        assert retrieved_config.goal == config.goal
        
        # Update config - update_config expects a dict
        agent.update_config({"goal": "New goal", "temperature": 0.5})
        updated_config = agent.get_config()
        assert updated_config.goal == "New goal"
        assert updated_config.temperature == 0.5

    def test_metrics_tracking(self, agent):
        """Test metrics tracking."""
        # Initial metrics
        metrics = agent.get_metrics()
        assert metrics.total_tasks_executed == 0
        
        # Update metrics
        agent.update_metrics(execution_time=1.5, success=True)
        updated_metrics = agent.get_metrics()
        assert updated_metrics.total_tasks_executed == 1
        assert updated_metrics.average_execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_task(self, agent):
        """Test task execution."""
        await agent.initialize()
        await agent.activate()
        
        task = {"description": "Test task"}
        result = await agent.execute_task(task, {})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_process_message(self, agent):
        """Test message processing."""
        await agent.initialize()
        await agent.activate()
        
        result = await agent.process_message("Hello")
        assert "response" in result

    @pytest.mark.asyncio
    async def test_serialization(self, agent):
        """Test agent serialization."""
        # Add some state - add_to_memory is async
        await agent.add_to_memory("test", "value")
        # set_goal expects description string, not AgentGoal object
        agent.set_goal(description="Test goal")
        
        # Serialize
        data = agent.to_dict()
        assert data["agent_id"] == agent.agent_id
        assert data["name"] == agent.name
        assert data["state"] == agent.state.value

    def test_capability_declaration(self, agent):
        """Test capability declaration."""
        from aiecs.domain.agent.models import CapabilityLevel
        
        # Use the method signature: declare_capability(capability_type, level, ...)
        agent.declare_capability(
            capability_type="text_generation",
            level=CapabilityLevel.ADVANCED.value,  # Pass string value
            description="Can generate text"
        )
        
        assert agent.has_capability("text_generation")
        # Get capability from internal dict
        retrieved = agent._capabilities.get("text_generation")
        assert retrieved is not None
        assert retrieved.level == CapabilityLevel.ADVANCED


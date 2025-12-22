"""
Unit tests for agent domain models.
"""

import pytest
from datetime import datetime
from aiecs.domain.agent.models import (
    AgentState,
    AgentType,
    GoalStatus,
    GoalPriority,
    CapabilityLevel,
    MemoryType,
    RetryPolicy,
    AgentConfiguration,
    AgentGoal,
    AgentCapabilityDeclaration,
    AgentMetrics,
    AgentInteraction,
    AgentMemory,
)


@pytest.mark.unit
class TestEnums:
    """Test agent enums."""

    def test_agent_state_values(self):
        """Test AgentState enum values."""
        assert AgentState.CREATED.value == "created"
        assert AgentState.INITIALIZING.value == "initializing"
        assert AgentState.ACTIVE.value == "active"
        assert AgentState.IDLE.value == "idle"
        assert AgentState.BUSY.value == "busy"
        assert AgentState.ERROR.value == "error"
        assert AgentState.STOPPED.value == "stopped"

    def test_agent_type_values(self):
        """Test AgentType enum values."""
        assert AgentType.CONVERSATIONAL.value == "conversational"
        assert AgentType.TASK_EXECUTOR.value == "task_executor"
        assert AgentType.RESEARCHER.value == "researcher"
        assert AgentType.ANALYST.value == "analyst"
        assert AgentType.CREATIVE.value == "creative"
        assert AgentType.DEVELOPER.value == "developer"
        assert AgentType.COORDINATOR.value == "coordinator"

    def test_goal_status_values(self):
        """Test GoalStatus enum values."""
        assert GoalStatus.PENDING.value == "pending"
        assert GoalStatus.IN_PROGRESS.value == "in_progress"
        assert GoalStatus.ACHIEVED.value == "achieved"
        assert GoalStatus.FAILED.value == "failed"
        assert GoalStatus.ABANDONED.value == "abandoned"


@pytest.mark.unit
class TestRetryPolicy:
    """Test RetryPolicy model."""

    def test_default_retry_policy(self):
        """Test default retry policy creation."""
        policy = RetryPolicy()
        assert policy.max_retries == 5
        assert policy.base_delay == 1.0
        assert policy.max_delay == 32.0
        assert policy.exponential_factor == 2.0
        assert policy.jitter_factor == 0.2

    def test_custom_retry_policy(self):
        """Test custom retry policy creation."""
        policy = RetryPolicy(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_factor=1.5,
            jitter_factor=0.2
        )
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.exponential_factor == 1.5
        assert policy.jitter_factor == 0.2

    def test_retry_policy_validation(self):
        """Test retry policy validation."""
        # Negative retries should fail
        with pytest.raises(Exception):  # Pydantic validation
            RetryPolicy(max_retries=-1)


@pytest.mark.unit
class TestAgentConfiguration:
    """Test AgentConfiguration model."""

    def test_default_configuration(self):
        """Test default configuration creation."""
        config = AgentConfiguration()
        assert config.temperature == 0.7
        assert config.memory_enabled is True
        assert config.verbose is False

    def test_custom_configuration(self):
        """Test custom configuration creation."""
        retry_policy = RetryPolicy(max_retries=5)
        config = AgentConfiguration(
            goal="Test goal",
            backstory="Test backstory",
            llm_model="gpt-4",
            temperature=0.5,
            max_tokens=1000,
            retry_policy=retry_policy
        )
        assert config.goal == "Test goal"
        assert config.backstory == "Test backstory"
        assert config.llm_model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.retry_policy.max_retries == 5


@pytest.mark.unit
class TestAgentGoal:
    """Test AgentGoal model."""

    def test_agent_goal_creation(self):
        """Test agent goal creation."""
        goal = AgentGoal(
            goal_id="goal-1",
            description="Complete task",
            priority=GoalPriority.HIGH,
            status=GoalStatus.PENDING
        )
        assert goal.goal_id == "goal-1"
        assert goal.description == "Complete task"
        assert goal.priority == GoalPriority.HIGH
        assert goal.status == GoalStatus.PENDING

    def test_goal_progress_tracking(self):
        """Test goal progress tracking."""
        goal = AgentGoal(
            goal_id="goal-1",
            description="Complete task",
            progress=50.0
        )
        assert goal.progress == 50.0
        goal.progress = 75.0
        assert goal.progress == 75.0


@pytest.mark.unit
class TestAgentMetrics:
    """Test AgentMetrics model."""

    def test_default_metrics(self):
        """Test default metrics initialization."""
        metrics = AgentMetrics()
        assert metrics.total_tasks_executed == 0
        assert metrics.successful_tasks == 0
        assert metrics.failed_tasks == 0
        assert metrics.average_execution_time is None
        assert metrics.total_tool_calls == 0

    def test_metrics_updates(self):
        """Test metrics updates."""
        metrics = AgentMetrics()
        metrics.total_tasks_executed = 12
        metrics.successful_tasks = 10
        metrics.failed_tasks = 2
        metrics.average_execution_time = 1.5
        assert metrics.total_tasks_executed == 12
        assert metrics.successful_tasks == 10
        assert metrics.failed_tasks == 2
        assert metrics.average_execution_time == 1.5


@pytest.mark.unit
class TestAgentCapabilityDeclaration:
    """Test AgentCapabilityDeclaration model."""

    def test_capability_declaration(self):
        """Test capability declaration."""
        capability = AgentCapabilityDeclaration(
            capability_type="text_generation",
            level=CapabilityLevel.ADVANCED,
            description="Can generate text"
        )
        assert capability.capability_type == "text_generation"
        assert capability.level == CapabilityLevel.ADVANCED
        assert capability.description == "Can generate text"


@pytest.mark.unit
class TestAgentInteraction:
    """Test AgentInteraction model."""

    def test_interaction_creation(self):
        """Test interaction creation."""
        interaction = AgentInteraction(
            interaction_id="interaction-1",
            agent_id="agent-1",
            interaction_type="task",
            content={"description": "Test interaction", "result": "success"},
            timestamp=datetime.utcnow()
        )
        assert interaction.interaction_id == "interaction-1"
        assert interaction.agent_id == "agent-1"
        assert interaction.interaction_type == "task"
        assert isinstance(interaction.content, dict)
        assert "description" in interaction.content
        assert interaction.timestamp is not None


@pytest.mark.unit
class TestAgentMemory:
    """Test AgentMemory model."""

    def test_memory_creation(self):
        """Test memory creation."""
        memory = AgentMemory(
            memory_id="memory-1",
            agent_id="agent-1",
            key="test_key",
            value="Test content",
            memory_type=MemoryType.SHORT_TERM
        )
        assert memory.memory_id == "memory-1"
        assert memory.agent_id == "agent-1"
        assert memory.key == "test_key"
        assert memory.value == "Test content"
        assert memory.memory_type == MemoryType.SHORT_TERM


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


@pytest.mark.unit
@pytest.mark.asyncio
class TestBaseAIAgentSkillScriptTools:
    """Test BaseAIAgent skill script tool management methods."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return AgentConfiguration(
            goal="Test agent goal",
            temperature=0.7
        )

    @pytest.fixture
    def registry(self):
        """Create a SkillScriptRegistry for testing."""
        from aiecs.domain.agent.tools import SkillScriptRegistry
        return SkillScriptRegistry()

    @pytest.fixture
    def agent_with_registry(self, config, registry):
        """Create test agent with SkillScriptRegistry."""
        return MockAgent(
            agent_id="test-agent-1",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config,
            skill_script_registry=registry
        )

    @pytest.fixture
    def agent_without_registry(self, config):
        """Create test agent without SkillScriptRegistry."""
        return MockAgent(
            agent_id="test-agent-2",
            name="Test Agent",
            agent_type=AgentType.CONVERSATIONAL,
            config=config
        )

    @pytest.fixture
    def sample_tool(self):
        """Create a sample Tool for testing."""
        from aiecs.domain.agent.tools import Tool

        async def sample_execute(input_data):
            return {"result": input_data.get("value", 0) * 2}

        return Tool(
            name="sample-tool",
            description="A sample tool for testing",
            execute=sample_execute,
            tags=["test", "sample"],
            source="test-skill"
        )

    def test_skill_script_registry_property(self, agent_with_registry, registry):
        """Test skill_script_registry property returns the registry."""
        assert agent_with_registry.skill_script_registry is registry

    def test_skill_script_registry_property_none(self, agent_without_registry):
        """Test skill_script_registry property returns None when not configured."""
        assert agent_without_registry.skill_script_registry is None

    def test_add_tool_success(self, agent_with_registry, sample_tool):
        """Test adding a tool to the registry."""
        agent_with_registry.add_tool(sample_tool)
        assert agent_with_registry.has_tool("sample-tool")

    def test_add_tool_without_registry_raises(self, agent_without_registry, sample_tool):
        """Test adding a tool without registry raises RuntimeError."""
        with pytest.raises(RuntimeError, match="no SkillScriptRegistry configured"):
            agent_without_registry.add_tool(sample_tool)

    def test_add_tool_replace(self, agent_with_registry, sample_tool):
        """Test replacing an existing tool."""
        from aiecs.domain.agent.tools import Tool

        agent_with_registry.add_tool(sample_tool)

        async def new_execute(input_data):
            return {"result": "new"}

        new_tool = Tool(
            name="sample-tool",
            description="Replaced tool",
            execute=new_execute
        )
        agent_with_registry.add_tool(new_tool, replace=True)

        retrieved = agent_with_registry.get_tool("sample-tool")
        assert retrieved.description == "Replaced tool"

    def test_has_tool_true(self, agent_with_registry, sample_tool):
        """Test has_tool returns True for existing tool."""
        agent_with_registry.add_tool(sample_tool)
        assert agent_with_registry.has_tool("sample-tool") is True

    def test_has_tool_false(self, agent_with_registry):
        """Test has_tool returns False for non-existing tool."""
        assert agent_with_registry.has_tool("nonexistent") is False

    def test_has_tool_without_registry(self, agent_without_registry):
        """Test has_tool returns False when no registry configured."""
        assert agent_without_registry.has_tool("any-tool") is False

    def test_get_tool_success(self, agent_with_registry, sample_tool):
        """Test getting a tool by name."""
        agent_with_registry.add_tool(sample_tool)
        retrieved = agent_with_registry.get_tool("sample-tool")
        assert retrieved is not None
        assert retrieved.name == "sample-tool"
        assert retrieved.description == "A sample tool for testing"

    def test_get_tool_not_found(self, agent_with_registry):
        """Test getting a non-existing tool returns None."""
        assert agent_with_registry.get_tool("nonexistent") is None

    def test_get_tool_without_registry(self, agent_without_registry):
        """Test getting a tool without registry returns None."""
        assert agent_without_registry.get_tool("any-tool") is None

    def test_remove_tool_success(self, agent_with_registry, sample_tool):
        """Test removing a tool."""
        agent_with_registry.add_tool(sample_tool)
        assert agent_with_registry.has_tool("sample-tool")

        result = agent_with_registry.remove_tool("sample-tool")
        assert result is True
        assert agent_with_registry.has_tool("sample-tool") is False

    def test_remove_tool_not_found(self, agent_with_registry):
        """Test removing a non-existing tool returns False."""
        result = agent_with_registry.remove_tool("nonexistent")
        assert result is False

    def test_remove_tool_without_registry_raises(self, agent_without_registry):
        """Test removing a tool without registry raises RuntimeError."""
        with pytest.raises(RuntimeError, match="no SkillScriptRegistry configured"):
            agent_without_registry.remove_tool("any-tool")

    def test_list_skill_tools_all(self, agent_with_registry, sample_tool):
        """Test listing all tools."""
        from aiecs.domain.agent.tools import Tool

        async def another_execute(input_data):
            return {}

        another_tool = Tool(
            name="another-tool",
            description="Another tool",
            execute=another_execute,
            source="other-skill"
        )

        agent_with_registry.add_tool(sample_tool)
        agent_with_registry.add_tool(another_tool)

        tools = agent_with_registry.list_skill_tools()
        assert len(tools) == 2

    def test_list_skill_tools_by_source(self, agent_with_registry, sample_tool):
        """Test listing tools filtered by source."""
        from aiecs.domain.agent.tools import Tool

        async def another_execute(input_data):
            return {}

        another_tool = Tool(
            name="another-tool",
            description="Another tool",
            execute=another_execute,
            source="other-skill"
        )

        agent_with_registry.add_tool(sample_tool)
        agent_with_registry.add_tool(another_tool)

        tools = agent_with_registry.list_skill_tools(source="test-skill")
        assert len(tools) == 1
        assert tools[0].name == "sample-tool"

    def test_list_skill_tools_by_tags(self, agent_with_registry, sample_tool):
        """Test listing tools filtered by tags."""
        from aiecs.domain.agent.tools import Tool

        async def another_execute(input_data):
            return {}

        another_tool = Tool(
            name="another-tool",
            description="Another tool",
            execute=another_execute,
            tags=["other"]
        )

        agent_with_registry.add_tool(sample_tool)
        agent_with_registry.add_tool(another_tool)

        tools = agent_with_registry.list_skill_tools(tags=["test"])
        assert len(tools) == 1
        assert tools[0].name == "sample-tool"

    def test_list_skill_tools_without_registry(self, agent_without_registry):
        """Test listing tools without registry returns empty list."""
        tools = agent_without_registry.list_skill_tools()
        assert tools == []

    async def test_tool_execution_via_agent(self, agent_with_registry, sample_tool):
        """Test executing a tool retrieved from the agent."""
        agent_with_registry.add_tool(sample_tool)
        tool = agent_with_registry.get_tool("sample-tool")
        result = await tool({"value": 5})
        assert result == {"result": 10}

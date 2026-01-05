"""
Backward Compatibility Tests for Agent Enhancements

Tests that all new features are optional and don't break existing functionality.
Covers tasks 2.1.1-2.1.5 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from aiecs.domain.agent import (
    HybridAgent,
    ToolAgent,
    LLMAgent,
    AgentConfiguration,
    AgentType,
)
from aiecs.llm import BaseLLMClient, CacheControl, LLMResponse, LLMMessage


# ==================== Mock Classes ====================


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing backward compatibility."""

    def __init__(self):
        super().__init__(provider_name="mock")

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        """Generate mock response."""
        return LLMResponse(
            content="Mock LLM response",
            provider="mock",
            model=model or "mock-model",
            tokens_used=10,
        )

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ):
        """Stream mock response."""
        for token in ["Mock", " ", "streaming", " ", "response"]:
            yield token

    async def close(self):
        """Close the client (no-op for mock)."""
        pass


# ==================== Test 2.1.1: HybridAgent with List[str] tools ====================


@pytest.mark.asyncio
async def test_hybrid_agent_with_list_tools():
    """Test HybridAgent with List[str] tools (existing behavior)."""
    # Create config
    config = AgentConfiguration(
        goal="Test agent",
        llm_model="mock-model",
        temperature=0.7,
    )

    # Create agent with list of tool names (backward compatible)
    agent = HybridAgent(
        agent_id="test_hybrid_1",
        name="Test Hybrid Agent",
        llm_client=MockLLMClient(),
        tools=["search", "calculator"],  # List[str] - backward compatible
        config=config,
    )

    # Verify agent created successfully
    assert agent.agent_id == "test_hybrid_1"
    assert agent.name == "Test Hybrid Agent"
    assert agent.agent_type == AgentType.DEVELOPER  # HybridAgent uses DEVELOPER type

    # Initialize agent
    await agent.initialize()
    assert agent.state.name == "ACTIVE"


# ==================== Test 2.1.2: HybridAgent with BaseLLMClient ====================


@pytest.mark.asyncio
async def test_hybrid_agent_with_base_llm_client():
    """Test HybridAgent with BaseLLMClient (existing behavior)."""
    config = AgentConfiguration(
        goal="Test agent",
        llm_model="mock-model",
    )

    # Create agent with BaseLLMClient (backward compatible)
    llm_client = MockLLMClient()
    agent = HybridAgent(
        agent_id="test_hybrid_2",
        name="Test Hybrid Agent 2",
        llm_client=llm_client,  # BaseLLMClient - backward compatible
        tools=["search"],
        config=config,
    )

    # Verify agent works
    assert agent.agent_id == "test_hybrid_2"
    await agent.initialize()
    assert agent.state.name == "ACTIVE"


# ==================== Test 2.1.3: ToolAgent with List[str] tools ====================


@pytest.mark.asyncio
async def test_tool_agent_with_list_tools():
    """Test ToolAgent with List[str] tools (existing behavior)."""
    config = AgentConfiguration(goal="Tool execution agent")

    # Create agent with list of tool names (backward compatible)
    agent = ToolAgent(
        agent_id="test_tool_1",
        name="Test Tool Agent",
        tools=["search", "calculator"],  # List[str] - backward compatible
        config=config,
    )

    # Verify agent created successfully
    assert agent.agent_id == "test_tool_1"
    assert agent.name == "Test Tool Agent"
    assert agent.agent_type == AgentType.TASK_EXECUTOR

    # Initialize agent
    await agent.initialize()
    assert agent.state.name == "ACTIVE"


# ==================== Test 2.1.4: LLMAgent with BaseLLMClient ====================


@pytest.mark.asyncio
async def test_llm_agent_with_base_llm_client():
    """Test LLMAgent with BaseLLMClient (existing behavior)."""
    config = AgentConfiguration(
        goal="LLM-powered agent",
        llm_model="mock-model",
        temperature=0.7,
    )

    # Create agent with BaseLLMClient (backward compatible)
    llm_client = MockLLMClient()
    agent = LLMAgent(
        agent_id="test_llm_1",
        name="Test LLM Agent",
        llm_client=llm_client,  # BaseLLMClient - backward compatible
        config=config,
    )

    # Verify agent created successfully
    assert agent.agent_id == "test_llm_1"
    assert agent.name == "Test LLM Agent"
    assert agent.agent_type == AgentType.CONVERSATIONAL

    # Initialize agent
    await agent.initialize()
    assert agent.state.name == "ACTIVE"


# ==================== Test 2.1.5: Verify existing code works without changes ====================


@pytest.mark.asyncio
async def test_existing_agent_creation_code_unchanged():
    """
    Test 2.1.5: Verify existing agent creation code still works without changes.

    This test simulates typical existing code patterns to ensure backward compatibility.
    """
    # Pattern 1: Simple HybridAgent creation (most common pattern)
    config1 = AgentConfiguration(goal="Research agent", llm_model="gpt-4")
    agent1 = HybridAgent(
        agent_id="researcher-1",
        name="Research Agent",
        llm_client=MockLLMClient(),
        tools=["search", "apisource"],
        config=config1,
    )
    await agent1.initialize()
    assert agent1.state.name == "ACTIVE"

    # Pattern 2: ToolAgent with minimal config
    config2 = AgentConfiguration(goal="Execute tools")
    agent2 = ToolAgent(
        agent_id="tool-1",
        name="Tool Agent",
        tools=["calculator"],
        config=config2,
    )
    await agent2.initialize()
    assert agent2.state.name == "ACTIVE"

    # Pattern 3: LLMAgent with custom settings
    config3 = AgentConfiguration(
        goal="Chat assistant",
        llm_model="gpt-3.5-turbo",
        temperature=0.8,
        max_tokens=2000,
    )
    agent3 = LLMAgent(
        agent_id="assistant-1",
        name="Chat Assistant",
        llm_client=MockLLMClient(),
        config=config3,
    )
    await agent3.initialize()
    assert agent3.state.name == "ACTIVE"

    # Pattern 4: HybridAgent with max_iterations
    config4 = AgentConfiguration(goal="Complex reasoning")
    agent4 = HybridAgent(
        agent_id="reasoner-1",
        name="Reasoning Agent",
        llm_client=MockLLMClient(),
        tools=["search"],
        config=config4,
        max_iterations=15,  # Custom parameter
    )
    await agent4.initialize()
    assert agent4.state.name == "ACTIVE"


# ==================== Additional Backward Compatibility Tests ====================


@pytest.mark.asyncio
async def test_agent_without_optional_parameters():
    """Test that agents work without any optional new parameters."""
    config = AgentConfiguration(goal="Test")

    # HybridAgent without new optional parameters
    agent1 = HybridAgent(
        agent_id="test1",
        name="Test1",
        llm_client=MockLLMClient(),
        tools=["search"],
        config=config,
        # No config_manager, checkpointer, context_engine, collaboration_enabled,
        # agent_registry, learning_enabled, or resource_limits
    )
    await agent1.initialize()
    assert agent1.state.name == "ACTIVE"

    # ToolAgent without new optional parameters
    agent2 = ToolAgent(
        agent_id="test2",
        name="Test2",
        tools=["calculator"],
        config=config,
        # No config_manager, checkpointer, or context_engine
    )
    await agent2.initialize()
    assert agent2.state.name == "ACTIVE"

    # LLMAgent without new optional parameters
    agent3 = LLMAgent(
        agent_id="test3",
        name="Test3",
        llm_client=MockLLMClient(),
        config=config,
        # No config_manager, checkpointer, or context_engine
    )
    await agent3.initialize()
    assert agent3.state.name == "ACTIVE"


@pytest.mark.asyncio
async def test_agent_execute_task_backward_compatible():
    """Test that execute_task works with existing code patterns."""
    config = AgentConfiguration(goal="Test", llm_model="mock")

    # Create LLM agent
    agent = LLMAgent(
        agent_id="test_exec",
        name="Test Executor",
        llm_client=MockLLMClient(),
        config=config,
    )
    await agent.initialize()

    # Execute task with existing pattern
    task = {"description": "Test task"}
    result = await agent.execute_task(task, {})

    # Verify result structure (backward compatible)
    assert "success" in result
    assert "output" in result
    assert result["success"] is True


@pytest.mark.asyncio
async def test_agent_state_transitions_backward_compatible():
    """Test that state transitions work as before."""
    config = AgentConfiguration(goal="Test")

    agent = LLMAgent(
        agent_id="test_state",
        name="Test State",
        llm_client=MockLLMClient(),
        config=config,
    )

    # Test state transitions (existing behavior)
    assert agent.state.name == "CREATED"  # Initial state is CREATED

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    await agent.deactivate()
    assert agent.state.name == "IDLE"

    await agent.activate()
    assert agent.state.name == "ACTIVE"

    await agent.shutdown()
    assert agent.state.name == "STOPPED"


@pytest.mark.asyncio
async def test_agent_metrics_backward_compatible():
    """Test that metrics tracking works as before."""
    config = AgentConfiguration(goal="Test")

    agent = LLMAgent(
        agent_id="test_metrics",
        name="Test Metrics",
        llm_client=MockLLMClient(),
        config=config,
    )
    await agent.initialize()

    # Get metrics (existing behavior)
    metrics = agent.get_metrics()

    # Verify metrics structure (backward compatible)
    # get_metrics() returns an AgentMetrics object with attributes
    assert hasattr(metrics, "total_tasks_executed")
    assert hasattr(metrics, "successful_tasks")
    assert hasattr(metrics, "failed_tasks")
    assert hasattr(metrics, "average_execution_time")

    # Verify initial values
    assert metrics.total_tasks_executed == 0
    assert metrics.successful_tasks == 0
    assert metrics.failed_tasks == 0


# ==================== Test System Prompt Precedence ====================


@pytest.mark.asyncio
async def test_llm_agent_system_prompt_takes_precedence():
    """Test that system_prompt field takes precedence over assembled fields in LLMAgent."""
    config = AgentConfiguration(
        system_prompt="Custom system prompt",
        goal="This goal should be ignored",
        backstory="This backstory should be ignored",
        llm_model="mock-model",
    )

    agent = LLMAgent(
        agent_id="test_precedence_1",
        name="Precedence Test Agent",
        llm_client=MockLLMClient(),
        config=config,
    )

    await agent.initialize()

    # Access the built system prompt via the private attribute
    assert agent._system_prompt == "Custom system prompt"
    assert "goal" not in agent._system_prompt.lower()


@pytest.mark.asyncio
async def test_llm_agent_assembled_prompt_fallback():
    """Test that assembled prompt is used when system_prompt is None."""
    config = AgentConfiguration(
        goal="Help users with tasks",
        backstory="You are an experienced assistant",
        llm_model="mock-model",
    )

    agent = LLMAgent(
        agent_id="test_fallback_1",
        name="Fallback Test Agent",
        llm_client=MockLLMClient(),
        config=config,
    )

    await agent.initialize()

    # Should contain assembled parts
    assert "Goal: Help users with tasks" in agent._system_prompt
    assert "Background: You are an experienced assistant" in agent._system_prompt


@pytest.mark.asyncio
async def test_llm_agent_default_fallback():
    """Test that default prompt is used when no prompts configured."""
    config = AgentConfiguration(llm_model="mock-model")

    agent = LLMAgent(
        agent_id="test_default_1",
        name="Default Test Agent",
        llm_client=MockLLMClient(),
        config=config,
    )

    await agent.initialize()

    assert agent._system_prompt == "You are a helpful AI assistant."


@pytest.mark.asyncio
async def test_hybrid_agent_system_prompt_with_react_instructions():
    """Test that HybridAgent uses system_prompt but still adds ReAct instructions."""
    config = AgentConfiguration(
        system_prompt="You are a specialized data analyst.",
        goal="This goal should be ignored",
        llm_model="mock-model",
    )

    agent = HybridAgent(
        agent_id="test_hybrid_precedence_1",
        name="Hybrid Precedence Test",
        llm_client=MockLLMClient(),
        tools=["search"],
        config=config,
    )

    await agent.initialize()

    # Custom prompt should be included
    assert "You are a specialized data analyst." in agent._system_prompt
    # ReAct instructions should still be appended
    assert "ReAct pattern" in agent._system_prompt
    # Goal should NOT be in the prompt (overridden by system_prompt)
    assert "This goal should be ignored" not in agent._system_prompt


@pytest.mark.asyncio
async def test_hybrid_agent_assembled_with_react():
    """Test that HybridAgent assembles from fields when system_prompt is None."""
    config = AgentConfiguration(
        goal="Analyze data",
        backstory="Expert analyst",
        llm_model="mock-model",
    )

    agent = HybridAgent(
        agent_id="test_hybrid_assembled_1",
        name="Hybrid Assembled Test",
        llm_client=MockLLMClient(),
        tools=["calculator"],
        config=config,
    )

    await agent.initialize()

    # Assembled fields should be present
    assert "Goal: Analyze data" in agent._system_prompt
    assert "Background: Expert analyst" in agent._system_prompt
    # ReAct instructions should be present
    assert "ReAct pattern" in agent._system_prompt


@pytest.mark.asyncio
async def test_enable_prompt_caching_field_accessible():
    """Test that enable_prompt_caching field is accessible on agent config."""
    config = AgentConfiguration(
        goal="Test",
        enable_prompt_caching=False,
        llm_model="mock-model",
    )

    agent = LLMAgent(
        agent_id="test_caching_1",
        name="Caching Test Agent",
        llm_client=MockLLMClient(),
        config=config,
    )

    # Config field should be accessible
    assert agent._config.enable_prompt_caching is False


@pytest.mark.asyncio
async def test_llm_agent_messages_have_cache_control_when_enabled():
    """Test that LLMAgent adds cache_control to system prompt when enabled."""
    config = AgentConfiguration(
        system_prompt="You are a test assistant.",
        enable_prompt_caching=True,
        llm_model="mock-model",
    )

    agent = LLMAgent(
        agent_id="test_cache_ctrl_1",
        name="Cache Control Test Agent",
        llm_client=MockLLMClient(),
        config=config,
    )
    await agent.initialize()

    messages = agent._build_messages("Hello", {})

    # System prompt should have cache_control
    system_msg = messages[0]
    assert system_msg.role == "system"
    assert system_msg.cache_control is not None
    assert system_msg.cache_control.type == "ephemeral"


@pytest.mark.asyncio
async def test_llm_agent_messages_no_cache_control_when_disabled():
    """Test that LLMAgent does not add cache_control when disabled."""
    config = AgentConfiguration(
        system_prompt="You are a test assistant.",
        enable_prompt_caching=False,
        llm_model="mock-model",
    )

    agent = LLMAgent(
        agent_id="test_cache_ctrl_2",
        name="Cache Control Disabled Agent",
        llm_client=MockLLMClient(),
        config=config,
    )
    await agent.initialize()

    messages = agent._build_messages("Hello", {})

    # System prompt should NOT have cache_control
    system_msg = messages[0]
    assert system_msg.role == "system"
    assert system_msg.cache_control is None


@pytest.mark.asyncio
async def test_hybrid_agent_messages_have_cache_control_when_enabled():
    """Test that HybridAgent adds cache_control to system prompt when enabled."""
    config = AgentConfiguration(
        system_prompt="You are a hybrid test assistant.",
        enable_prompt_caching=True,
        llm_model="mock-model",
    )

    agent = HybridAgent(
        agent_id="test_hybrid_cache_1",
        name="Hybrid Cache Control Test Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )
    await agent.initialize()

    messages = agent._build_initial_messages("Do something", {})

    # System prompt should have cache_control
    system_msg = messages[0]
    assert system_msg.role == "system"
    assert system_msg.cache_control is not None
    assert system_msg.cache_control.type == "ephemeral"


@pytest.mark.asyncio
async def test_hybrid_agent_messages_no_cache_control_when_disabled():
    """Test that HybridAgent does not add cache_control when disabled."""
    config = AgentConfiguration(
        system_prompt="You are a hybrid test assistant.",
        enable_prompt_caching=False,
        llm_model="mock-model",
    )

    agent = HybridAgent(
        agent_id="test_hybrid_cache_2",
        name="Hybrid Cache Disabled Agent",
        llm_client=MockLLMClient(),
        tools=[],
        config=config,
    )
    await agent.initialize()

    messages = agent._build_initial_messages("Do something", {})

    # System prompt should NOT have cache_control
    system_msg = messages[0]
    assert system_msg.role == "system"
    assert system_msg.cache_control is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

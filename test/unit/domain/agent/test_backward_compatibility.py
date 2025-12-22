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
from aiecs.llm import BaseLLMClient, LLMResponse, LLMMessage


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


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])

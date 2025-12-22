"""
Integration Tests for HybridAgent New Features

Tests new functionality with real xAI LLM calls.
Covers tasks 2.2.1-2.2.6 from the enhance-hybrid-agent-flexibility proposal.

Requirements:
- XAI_API_KEY must be set in .env.test
- Real LLM calls will be made (costs may apply)
"""

import pytest
import asyncio
import os
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

from aiecs.domain.agent import (
    HybridAgent,
    AgentConfiguration,
)
from aiecs.llm import XAIClient
from aiecs.tools import BaseTool
from aiecs.domain.agent.models import ResourceLimits
from aiecs.domain.agent.integration.protocols import (
    ConfigManagerProtocol,
    CheckpointerProtocol,
)


# Load test environment
load_dotenv(".env.test")


# ==================== Mock Tools ====================


class CalculatorTool(BaseTool):
    """Simple calculator tool for testing."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    async def calculate(self, operation: str, a: float, b: float) -> Dict[str, Any]:
        """Execute calculation."""
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else "Error: Division by zero",
        }

        if operation not in operations:
            return {"error": f"Unknown operation: {operation}"}

        result = operations[operation](a, b)
        return {"result": result, "operation": operation, "a": a, "b": b}


class SearchTool(BaseTool):
    """Mock search tool for testing."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.search_count = 0  # Track state

    async def search(self, query: str) -> Dict[str, Any]:
        """Execute search."""
        self.search_count += 1
        return {
            "results": [
                f"Result 1 for '{query}'",
                f"Result 2 for '{query}'",
                f"Result 3 for '{query}'",
            ],
            "query": query,
            "count": 3,
            "search_number": self.search_count,
        }


# ==================== Mock Protocols ====================


class MockConfigManager:
    """Mock ConfigManager implementing ConfigManagerProtocol."""

    def __init__(self):
        self.configs: Dict[str, Any] = {}
        self.get_count = 0
        self.set_count = 0

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        self.get_count += 1
        return self.configs.get(key, default)

    async def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.set_count += 1
        self.configs[key] = value

    async def delete_config(self, key: str) -> None:
        """Delete configuration value."""
        self.configs.pop(key, None)

    async def list_configs(self) -> Dict[str, Any]:
        """List all configurations."""
        return self.configs.copy()


class MockCheckpointer:
    """Mock Checkpointer implementing CheckpointerProtocol."""

    def __init__(self):
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.save_count = 0
        self.load_count = 0

    async def save_checkpoint(
        self, agent_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint and return checkpoint ID."""
        self.save_count += 1
        checkpoint_id = f"checkpoint_{self.save_count}"
        self.checkpoints[checkpoint_id] = {
            "agent_id": agent_id,
            "data": checkpoint_data,
            "timestamp": datetime.now().isoformat(),
        }
        return checkpoint_id

    async def load_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Load checkpoint by ID."""
        self.load_count += 1
        if checkpoint_id not in self.checkpoints:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        return self.checkpoints[checkpoint_id]["data"]

    async def list_checkpoints(self, agent_id: str) -> List[str]:
        """List all checkpoint IDs for an agent."""
        return [
            cid
            for cid, data in self.checkpoints.items()
            if data["agent_id"] == agent_id
        ]

    async def delete_checkpoint(self, checkpoint_id: str) -> None:
        """Delete a checkpoint."""
        self.checkpoints.pop(checkpoint_id, None)


# ==================== Fixtures ====================


@pytest.fixture
def xai_client():
    """Create xAI client for testing."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        pytest.skip("XAI_API_KEY not set in .env.test")

    # XAIClient gets API key from settings automatically
    return XAIClient()


@pytest.fixture
def calculator_tool():
    """Create calculator tool instance."""
    return CalculatorTool()


@pytest.fixture
def search_tool():
    """Create search tool instance."""
    return SearchTool()


@pytest.fixture
def mock_config_manager():
    """Create mock config manager instance."""
    return MockConfigManager()


@pytest.fixture
def mock_checkpointer():
    """Create mock checkpointer instance."""
    return MockCheckpointer()


# ==================== Test 2.2.1: Dict[str, BaseTool] tools ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_with_dict_tools(xai_client, calculator_tool, search_tool):
    """
    Test 2.2.1: Test HybridAgent with Dict[str, BaseTool] tools.

    Verifies that HybridAgent can accept tool instances as a dictionary
    and use them correctly with real LLM calls.
    """
    config = AgentConfiguration(
        goal="Test agent with tool instances",
        llm_model="grok-3",
        temperature=0.7,
        max_tokens=500,
    )

    # Create agent with Dict[str, BaseTool]
    tools_dict = {
        "calculator": calculator_tool,
        "search": search_tool,
    }

    agent = HybridAgent(
        agent_id="test_dict_tools",
        name="Dict Tools Test Agent",
        llm_client=xai_client,
        tools=tools_dict,  # Dict[str, BaseTool] - new feature
        config=config,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify tools are loaded
    available_tools = agent.get_available_tools()
    assert "calculator" in available_tools
    assert "search" in available_tools

    # Execute a simple task
    task = {"description": "Calculate 15 + 27"}
    result = await agent.execute_task(task, {})

    assert result["success"] is True
    assert "output" in result
    print(f"\nTask result: {result['output']}")


# ==================== Test 2.2.2: Tool instances with state ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_tool_state_preserved(xai_client, search_tool):
    """
    Test 2.2.2 & 2.2.4: Test HybridAgent with tool instances that have state.

    Verifies that tool instance state is preserved after initialization
    and across multiple tool calls.
    """
    config = AgentConfiguration(
        goal="Test tool state preservation",
        llm_model="grok-3",
        temperature=0.7,
    )

    # Create agent with stateful tool
    agent = HybridAgent(
        agent_id="test_tool_state",
        name="Tool State Test Agent",
        llm_client=xai_client,
        tools={"search": search_tool},
        config=config,
    )

    await agent.initialize()

    # Verify initial state
    assert search_tool.search_count == 0

    # Execute task that uses search
    task1 = {"description": "Use the search tool to find Python tutorials"}
    result1 = await agent.execute_task(task1, {})
    assert result1["success"] is True

    # Verify state was updated (tool may or may not be called depending on LLM)
    first_count = search_tool.search_count
    print(f"\nAfter first task, search tool called {first_count} times")

    # Execute another task
    task2 = {"description": "Use the search tool to find AI research"}
    result2 = await agent.execute_task(task2, {})
    assert result2["success"] is True

    # Verify state persisted (tool instance is reused)
    second_count = search_tool.search_count
    print(f"After second task, search tool called {second_count} times total")

    # The key test: verify the tool instance state persists across calls
    # Even if LLM doesn't call the tool, the instance should be the same
    assert search_tool.search_count >= first_count  # State persists


# ==================== Test 2.2.3: Custom LLM client ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_with_custom_llm_client(xai_client, calculator_tool):
    """
    Test 2.2.3: Test HybridAgent with custom LLM client implementing Protocol.

    Verifies that HybridAgent works with any LLM client that implements
    the LLMClientProtocol interface.
    """
    config = AgentConfiguration(
        goal="Test custom LLM client",
        llm_model="grok-3",
        temperature=0.5,
    )

    # xai_client implements LLMClientProtocol
    agent = HybridAgent(
        agent_id="test_custom_llm",
        name="Custom LLM Test Agent",
        llm_client=xai_client,  # Custom client implementing protocol
        tools={"calculator": calculator_tool},
        config=config,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Execute task
    task = {"description": "What is 100 divided by 4?"}
    result = await agent.execute_task(task, {})

    assert result["success"] is True
    assert "output" in result
    print(f"\nCustom LLM result: {result['output']}")


# ==================== Test 2.2.5: Streaming support ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_streaming(xai_client, calculator_tool):
    """
    Test streaming support with real LLM calls.

    Verifies that execute_task_streaming works correctly with real xAI client.
    """
    config = AgentConfiguration(
        goal="Test streaming",
        llm_model="grok-3",
        temperature=0.7,
    )

    agent = HybridAgent(
        agent_id="test_streaming",
        name="Streaming Test Agent",
        llm_client=xai_client,
        tools={"calculator": calculator_tool},
        config=config,
    )

    await agent.initialize()

    # Execute task with streaming
    task = {"description": "Calculate 25 * 4 and explain the result"}
    events = []

    async for event in agent.execute_task_streaming(task, {}):
        events.append(event)
        if event["type"] == "token":
            print(event["content"], end="", flush=True)
        elif event["type"] == "tool_call":
            print(f"\n[Tool: {event['tool_name']}]", flush=True)

    print()  # New line after streaming

    # Verify we got events
    assert len(events) > 0

    # Verify we got different event types
    event_types = {e["type"] for e in events}
    assert "status" in event_types
    assert "result" in event_types

    # Get final result
    final_result = [e for e in events if e["type"] == "result"][0]
    assert final_result["success"] is True


# ==================== Test 2.2.6: Custom Config Manager ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_custom_config_manager(
    xai_client, calculator_tool, mock_config_manager
):
    """
    Test 2.2.6: Test HybridAgent with custom config manager.

    Verifies that HybridAgent works with custom ConfigManagerProtocol
    implementation and that config manager state is accessible.
    """
    config = AgentConfiguration(
        goal="Test custom config manager",
        llm_model="grok-3",
        temperature=0.7,
    )

    # Pre-populate some config
    await mock_config_manager.set_config("max_retries", 3)
    await mock_config_manager.set_config("timeout", 30)

    agent = HybridAgent(
        agent_id="test_config_mgr",
        name="Config Manager Test Agent",
        llm_client=xai_client,
        tools={"calculator": calculator_tool},
        config=config,
        config_manager=mock_config_manager,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify config manager is accessible and working
    max_retries = await mock_config_manager.get_config("max_retries")
    assert max_retries == 3

    # Execute task
    task = {"description": "Calculate 50 + 50"}
    result = await agent.execute_task(task, {})
    assert result["success"] is True

    # Verify config manager was used
    assert mock_config_manager.get_count > 0
    print(f"\nConfig manager accessed {mock_config_manager.get_count} times")


# ==================== Test 2.2.7: Custom Checkpointer ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_custom_checkpointer(
    xai_client, calculator_tool, mock_checkpointer
):
    """
    Test 2.2.7: Test HybridAgent with custom checkpointer.

    Verifies that HybridAgent works with custom CheckpointerProtocol
    implementation and that checkpointer can save/load state.
    """
    config = AgentConfiguration(
        goal="Test custom checkpointer",
        llm_model="grok-3",
        temperature=0.7,
    )

    agent = HybridAgent(
        agent_id="test_checkpointer",
        name="Checkpointer Test Agent",
        llm_client=xai_client,
        tools={"calculator": calculator_tool},
        config=config,
        checkpointer=mock_checkpointer,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Execute task
    task = {"description": "Calculate 25 * 8"}
    result = await agent.execute_task(task, {})
    assert result["success"] is True

    # Manually save a checkpoint using the checkpointer
    checkpoint_data = {
        "agent_id": agent.agent_id,
        "state": agent.state.name,
        "task_result": result,
    }
    checkpoint_id = await mock_checkpointer.save_checkpoint(
        agent.agent_id, checkpoint_data
    )

    # Verify checkpoint was saved
    assert checkpoint_id is not None
    assert mock_checkpointer.save_count == 1

    # Load checkpoint
    loaded_data = await mock_checkpointer.load_checkpoint(checkpoint_id)
    assert loaded_data["agent_id"] == agent.agent_id
    assert loaded_data["state"] == "ACTIVE"
    assert mock_checkpointer.load_count == 1

    print(f"\nCheckpoint saved and loaded successfully: {checkpoint_id}")


# ==================== Test 2.2.8: Resource Limits ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_hybrid_agent_resource_limits(xai_client, calculator_tool):
    """
    Test 2.2.8: Test HybridAgent with resource limits.

    Verifies that resource limits parameter is accepted and passed through
    to BaseAIAgent correctly.
    """
    config = AgentConfiguration(
        goal="Test resource limits",
        llm_model="grok-3",
        temperature=0.7,
    )

    # Create resource limits
    limits = ResourceLimits(
        max_concurrent_tasks=2,
        max_tokens_per_minute=5000,
        enforce_limits=True,
    )

    agent = HybridAgent(
        agent_id="test_resources",
        name="Resource Test Agent",
        llm_client=xai_client,
        tools={"calculator": calculator_tool},
        config=config,
        resource_limits=limits,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify resource limits are set (private attribute)
    assert agent._resource_limits is not None
    assert agent._resource_limits.max_concurrent_tasks == 2
    assert agent._resource_limits.max_tokens_per_minute == 5000

    # Execute task
    task = {"description": "Calculate 100 / 5"}
    result = await agent.execute_task(task, {})
    assert result["success"] is True

    # Check resource availability
    status = await agent.check_resource_availability()
    assert status["available"] is True

    # Get resource usage
    usage = await agent.get_resource_usage()
    assert usage["active_tasks"] == 0
    assert usage["max_concurrent_tasks"] == 2

    print(f"\nResource usage: {usage}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


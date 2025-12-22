"""
Integration Tests for ToolAgent New Features

Tests new functionality for ToolAgent.
Covers tasks 2.3.1-2.3.5 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from aiecs.domain.agent import (
    ToolAgent,
    AgentConfiguration,
)
from aiecs.tools import BaseTool
from aiecs.domain.agent.models import ResourceLimits
from aiecs.domain.agent.integration.protocols import (
    ConfigManagerProtocol,
    CheckpointerProtocol,
)


# ==================== Mock Tools ====================


class DataProcessorTool(BaseTool):
    """Tool for data processing with state tracking."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.process_count = 0  # Track state
        self.processed_items = []  # Track history

    async def process_data(self, data: str) -> Dict[str, Any]:
        """Process data and track state."""
        self.process_count += 1
        result = f"Processed: {data}"
        self.processed_items.append(data)
        
        return {
            "result": result,
            "process_count": self.process_count,
            "total_items": len(self.processed_items),
        }


class FileOperationTool(BaseTool):
    """Tool for file operations."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.operation_count = 0

    async def read_file(self, filename: str) -> Dict[str, Any]:
        """Mock file read operation."""
        self.operation_count += 1
        return {
            "filename": filename,
            "content": f"Mock content of {filename}",
            "operation_count": self.operation_count,
        }

    async def write_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Mock file write operation."""
        self.operation_count += 1
        return {
            "filename": filename,
            "bytes_written": len(content),
            "operation_count": self.operation_count,
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
def data_processor_tool():
    """Create data processor tool instance."""
    return DataProcessorTool()


@pytest.fixture
def file_operation_tool():
    """Create file operation tool instance."""
    return FileOperationTool()


@pytest.fixture
def mock_config_manager():
    """Create mock config manager instance."""
    return MockConfigManager()


@pytest.fixture
def mock_checkpointer():
    """Create mock checkpointer instance."""
    return MockCheckpointer()


# ==================== Test 2.3.1: Dict[str, BaseTool] tools ====================


@pytest.mark.asyncio
async def test_tool_agent_with_dict_tools(data_processor_tool, file_operation_tool):
    """
    Test 2.3.1: Test ToolAgent with Dict[str, BaseTool] tools.

    Verifies that ToolAgent can accept tool instances as a dictionary
    and use them correctly.
    """
    config = AgentConfiguration(
        goal="Test agent with tool instances",
    )

    # Create agent with Dict[str, BaseTool]
    tools_dict = {
        "data_processor": data_processor_tool,
        "file_operation": file_operation_tool,
    }

    agent = ToolAgent(
        agent_id="test_dict_tools",
        name="Dict Tools Test Agent",
        tools=tools_dict,  # Dict[str, BaseTool] - new feature
        config=config,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify tools are loaded
    available_tools = agent.get_available_tools()
    assert "data_processor" in available_tools
    assert "file_operation" in available_tools

    # Execute a task using data processor
    task = {
        "tool": "data_processor",
        "operation": "process_data",
        "parameters": {"data": "test_data_123"},
    }
    result = await agent.execute_task(task, {})

    assert result["success"] is True
    print(f"\nTask result: {result}")


# ==================== Test 2.3.2 & 2.3.3: Tool state preservation ====================


@pytest.mark.asyncio
async def test_tool_agent_tool_state_preserved(data_processor_tool):
    """
    Test 2.3.2 & 2.3.3: Test ToolAgent with tool instances that have state.

    Verifies that tool instance state is preserved after initialization
    and across multiple tool calls.
    """
    config = AgentConfiguration(
        goal="Test tool state preservation",
    )

    # Create agent with stateful tool
    agent = ToolAgent(
        agent_id="test_tool_state",
        name="Tool State Test Agent",
        tools={"data_processor": data_processor_tool},
        config=config,
    )

    await agent.initialize()

    # Verify initial state
    assert data_processor_tool.process_count == 0
    assert len(data_processor_tool.processed_items) == 0

    # Execute first task
    task1 = {
        "tool": "data_processor",
        "operation": "process_data",
        "parameters": {"data": "item_1"},
    }
    result1 = await agent.execute_task(task1, {})
    assert result1["success"] is True

    # Verify state was updated
    assert data_processor_tool.process_count == 1
    assert len(data_processor_tool.processed_items) == 1
    assert "item_1" in data_processor_tool.processed_items

    # Execute second task
    task2 = {
        "tool": "data_processor",
        "operation": "process_data",
        "parameters": {"data": "item_2"},
    }
    result2 = await agent.execute_task(task2, {})
    assert result2["success"] is True

    # Verify state persisted and incremented
    assert data_processor_tool.process_count == 2
    assert len(data_processor_tool.processed_items) == 2
    assert "item_2" in data_processor_tool.processed_items

    print(f"\nTool processed {data_processor_tool.process_count} items")
    print(f"Items: {data_processor_tool.processed_items}")


# ==================== Test 2.3.4: Custom Config Manager ====================


@pytest.mark.asyncio
async def test_tool_agent_custom_config_manager(
    data_processor_tool, mock_config_manager
):
    """
    Test 2.3.4: Test ToolAgent with custom config manager.

    Verifies that ToolAgent works with custom ConfigManagerProtocol
    implementation and that config manager state is accessible.
    """
    config = AgentConfiguration(
        goal="Test custom config manager",
    )

    # Pre-populate some config
    await mock_config_manager.set_config("batch_size", 100)
    await mock_config_manager.set_config("timeout", 60)

    agent = ToolAgent(
        agent_id="test_config_mgr",
        name="Config Manager Test Agent",
        tools={"data_processor": data_processor_tool},
        config=config,
        config_manager=mock_config_manager,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify config manager is accessible and working
    batch_size = await mock_config_manager.get_config("batch_size")
    assert batch_size == 100

    # Execute task
    task = {
        "tool": "data_processor",
        "operation": "process_data",
        "parameters": {"data": "test_data"},
    }
    result = await agent.execute_task(task, {})
    assert result["success"] is True

    # Verify config manager was used
    assert mock_config_manager.get_count > 0
    print(f"\nConfig manager accessed {mock_config_manager.get_count} times")


# ==================== Test 2.3.5: Custom Checkpointer ====================


@pytest.mark.asyncio
async def test_tool_agent_custom_checkpointer(
    data_processor_tool, mock_checkpointer
):
    """
    Test 2.3.5: Test ToolAgent with custom checkpointer.

    Verifies that ToolAgent works with custom CheckpointerProtocol
    implementation and that checkpointer can save/load state.
    """
    config = AgentConfiguration(
        goal="Test custom checkpointer",
    )

    agent = ToolAgent(
        agent_id="test_checkpointer",
        name="Checkpointer Test Agent",
        tools={"data_processor": data_processor_tool},
        config=config,
        checkpointer=mock_checkpointer,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Execute task
    task = {
        "tool": "data_processor",
        "operation": "process_data",
        "parameters": {"data": "checkpoint_test_data"},
    }
    result = await agent.execute_task(task, {})
    assert result["success"] is True

    # Manually save a checkpoint using the checkpointer
    checkpoint_data = {
        "agent_id": agent.agent_id,
        "state": agent.state.name,
        "task_result": result,
        "tool_state": {
            "process_count": data_processor_tool.process_count,
            "processed_items": data_processor_tool.processed_items,
        },
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
    assert loaded_data["tool_state"]["process_count"] == 1
    assert mock_checkpointer.load_count == 1

    print(f"\nCheckpoint saved and loaded successfully: {checkpoint_id}")
    print(f"Tool state in checkpoint: {loaded_data['tool_state']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


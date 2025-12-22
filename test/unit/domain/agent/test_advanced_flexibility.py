"""
Advanced Flexibility Tests

Tests custom config manager injection, ContextEngineAdapter with session management,
conversation history, checkpoint storage, checkpointer Protocol implementation,
save/load checkpoint methods, and fallback to in-memory storage.
Covers tasks 2.8.1-2.8.7 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from aiecs.domain.agent.base_agent import BaseAIAgent
from aiecs.domain.agent.models import AgentConfiguration, AgentType, AgentState
from aiecs.domain.agent.integration.protocols import ConfigManagerProtocol, CheckpointerProtocol
from aiecs.domain.agent.integration import ContextEngineAdapter


# ==================== Mock Implementations ====================


class MockConfigManager:
    """Mock config manager for testing."""

    def __init__(self):
        self._config = {}

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    async def set_config(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value

    async def reload_config(self) -> None:
        """Reload configuration."""
        pass


class MockCheckpointer:
    """Mock checkpointer for testing."""

    def __init__(self):
        self._checkpoints: Dict[str, Dict[str, Any]] = {}

    async def save_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        """Save checkpoint."""
        checkpoint_id = f"checkpoint_{len(self._checkpoints)}"
        key = f"{agent_id}:{session_id}:{checkpoint_id}"
        self._checkpoints[key] = {
            "checkpoint_id": checkpoint_id,
            "agent_id": agent_id,
            "session_id": session_id,
            "data": checkpoint_data,
            "created_at": datetime.utcnow().isoformat(),
        }
        return checkpoint_id

    async def load_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Load checkpoint."""
        if checkpoint_id:
            key = f"{agent_id}:{session_id}:{checkpoint_id}"
            checkpoint = self._checkpoints.get(key)
            return checkpoint["data"] if checkpoint else None

        # Load latest
        matching = [
            cp for k, cp in self._checkpoints.items()
            if k.startswith(f"{agent_id}:{session_id}:")
        ]
        if matching:
            return matching[-1]["data"]
        return None

    async def list_checkpoints(self, agent_id: str, session_id: str) -> List[str]:
        """List checkpoints."""
        prefix = f"{agent_id}:{session_id}:"
        return [
            cp["checkpoint_id"]
            for k, cp in self._checkpoints.items()
            if k.startswith(prefix)
        ]


class MockContextEngine:
    """Mock ContextEngine for testing."""

    def __init__(self):
        self._sessions = {}
        self._conversations = {}
        self._checkpoints = {}
        self._initialized = False

    async def initialize(self):
        """Initialize the context engine."""
        self._initialized = True

    async def create_session(
        self, session_id: str, user_id: str, metadata: Optional[Dict] = None
    ):
        """Create a session."""
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        self._conversations[session_id] = []
        return self._sessions[session_id]

    async def get_session(self, session_id: str):
        """Get a session."""
        return self._sessions.get(session_id)

    async def end_session(self, session_id: str, status: str = "completed"):
        """End a session."""
        if session_id in self._sessions:
            self._sessions[session_id]["ended_at"] = datetime.utcnow()
            self._sessions[session_id]["status"] = status

    async def add_conversation_message(
        self, session_id: str, role: str, content: str, metadata: Optional[Dict] = None
    ):
        """Add a conversation message."""
        if session_id not in self._conversations:
            self._conversations[session_id] = []

        message = {
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow(),
        }
        self._conversations[session_id].append(message)

    async def get_conversation_history(
        self, session_id: str, limit: Optional[int] = None
    ):
        """Get conversation history."""
        messages = self._conversations.get(session_id, [])
        if limit:
            messages = messages[-limit:]

        # Convert to mock ConversationMessage objects
        class MockMessage:
            def __init__(self, data):
                self.role = data["role"]
                self.content = data["content"]
                self.metadata = data["metadata"]
                self.timestamp = data["timestamp"]

        return [MockMessage(msg) for msg in messages]

    async def store_checkpoint(
        self, thread_id: str, checkpoint_id: str, checkpoint_data: Dict[str, Any],
        metadata: Optional[Dict] = None
    ):
        """Store a checkpoint."""
        key = f"{thread_id}:{checkpoint_id}"
        self._checkpoints[key] = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "data": checkpoint_data,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_checkpoint(
        self, thread_id: str, checkpoint_id: Optional[str] = None
    ):
        """Get a checkpoint."""
        if checkpoint_id:
            key = f"{thread_id}:{checkpoint_id}"
            return self._checkpoints.get(key)

        # Get latest
        matching = [
            cp for k, cp in self._checkpoints.items()
            if k.startswith(f"{thread_id}:")
        ]
        if matching:
            return matching[-1]
        return None

    async def list_checkpoints(self, thread_id: str):
        """List checkpoints for a thread."""
        return [
            cp for k, cp in self._checkpoints.items()
            if k.startswith(f"{thread_id}:")
        ]


class MockTestAgent(BaseAIAgent):
    """Test agent implementation."""

    def __init__(self, agent_id: str, name: str, config: AgentConfiguration, **kwargs):
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
            **kwargs
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
        """Execute task."""
        return {"output": "Test result", "success": True}

    async def process_message(
        self, message: str, sender_id: str = None
    ) -> Dict[str, Any]:
        """Process message."""
        return {"response": "Test response", "success": True}


# ==================== Test 2.8.1: Custom Config Manager ====================


@pytest.mark.asyncio
async def test_config_manager_injection():
    """
    Test 2.8.1: Test custom config manager injection and usage.

    Verifies that custom config manager can be injected and used.
    """
    config = AgentConfiguration()
    config_manager = MockConfigManager()

    # Set some config values
    await config_manager.set_config("test_key", "test_value")
    await config_manager.set_config("max_retries", 5)

    # Create agent with config manager
    agent = MockTestAgent(
        agent_id="test-agent-1",
        name="Test Agent",
        config=config,
        config_manager=config_manager,
    )

    # Verify config manager is accessible
    assert agent.get_config_manager() is not None
    assert agent.get_config_manager() == config_manager

    # Verify config values can be retrieved
    value = await agent.get_config_manager().get_config("test_key")
    assert value == "test_value"

    retries = await agent.get_config_manager().get_config("max_retries")
    assert retries == 5

    # Test default value
    default_val = await agent.get_config_manager().get_config("nonexistent", "default")
    assert default_val == "default"


@pytest.mark.asyncio
async def test_config_manager_reload():
    """
    Test 2.8.1: Test config manager reload functionality.

    Verifies that config manager can reload configuration.
    """
    config = AgentConfiguration()
    config_manager = MockConfigManager()

    agent = MockTestAgent(
        agent_id="test-agent-2",
        name="Test Agent",
        config=config,
        config_manager=config_manager,
    )

    # Set initial config
    await config_manager.set_config("setting", "initial")

    # Reload config (should not fail)
    await agent.get_config_manager().reload_config()

    # Config should still be accessible
    value = await agent.get_config_manager().get_config("setting")
    assert value == "initial"


@pytest.mark.asyncio
async def test_agent_without_config_manager():
    """
    Test 2.8.1: Test agent without config manager.

    Verifies that agent works without config manager.
    """
    config = AgentConfiguration()

    agent = MockTestAgent(
        agent_id="test-agent-3",
        name="Test Agent",
        config=config,
    )

    # Verify config manager is None
    assert agent.get_config_manager() is None


# ==================== Test 2.8.2: ContextEngineAdapter Session Management ====================


@pytest.mark.asyncio
async def test_context_engine_adapter_session_creation():
    """
    Test 2.8.2: Test enhanced ContextEngineAdapter with session management.

    Verifies that ContextEngineAdapter can create and manage sessions.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Create session
    session_id = await adapter.acreate_session(
        user_id="test-user",
        metadata={"source": "test", "language": "en"}
    )

    assert session_id is not None
    assert session_id.startswith("session_")

    # Verify session was created
    session = await adapter.aget_session(session_id)
    assert session is not None
    assert session["user_id"] == "test-user"
    assert session["metadata"]["source"] == "test"


@pytest.mark.asyncio
async def test_context_engine_adapter_session_end():
    """
    Test 2.8.2: Test session ending.

    Verifies that ContextEngineAdapter can end sessions.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Create and end session
    session_id = await adapter.acreate_session(user_id="test-user")
    await adapter.end_session(session_id)

    # Verify session was ended
    session = await adapter.aget_session(session_id)
    assert session is not None
    assert "ended_at" in session


# ==================== Test 2.8.3: ContextEngineAdapter Conversation History ====================


@pytest.mark.asyncio
async def test_context_engine_adapter_conversation():
    """
    Test 2.8.3: Test enhanced ContextEngineAdapter with conversation history.

    Verifies that ContextEngineAdapter can manage conversation history.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Create session
    session_id = await adapter.acreate_session(user_id="test-user")

    # Add conversation messages
    await adapter.aadd_conversation_message(
        session_id=session_id,
        role="user",
        content="Hello, how are you?",
        metadata={"source": "web"}
    )

    await adapter.aadd_conversation_message(
        session_id=session_id,
        role="assistant",
        content="I'm doing well, thank you!",
        metadata={"model": "gpt-4"}
    )

    # Get conversation history
    history = await adapter.aget_conversation_history(session_id=session_id)

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello, how are you?"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "I'm doing well, thank you!"


@pytest.mark.asyncio
async def test_context_engine_adapter_conversation_limit():
    """
    Test 2.8.3: Test conversation history with limit.

    Verifies that conversation history respects limit parameter.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")
    session_id = await adapter.acreate_session(user_id="test-user")

    # Add multiple messages
    for i in range(10):
        await adapter.aadd_conversation_message(
            session_id=session_id,
            role="user" if i % 2 == 0 else "assistant",
            content=f"Message {i}"
        )

    # Get limited history
    history = await adapter.aget_conversation_history(session_id=session_id, limit=5)

    assert len(history) == 5
    # Should get the last 5 messages
    assert history[0]["content"] == "Message 5"
    assert history[4]["content"] == "Message 9"


# ==================== Test 2.8.4: ContextEngineAdapter Checkpoint Storage ====================


@pytest.mark.asyncio
async def test_context_engine_adapter_checkpoint_save():
    """
    Test 2.8.4: Test enhanced ContextEngineAdapter with checkpoint storage.

    Verifies that ContextEngineAdapter can save checkpoints.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Save checkpoint
    checkpoint_data = {
        "agent_id": "agent-1",
        "state": "active",
        "metrics": {"tasks_executed": 10},
    }

    success = await adapter.store_checkpoint(
        thread_id="agent-1",
        checkpoint_id="checkpoint-1",
        checkpoint_data=checkpoint_data
    )

    assert success is True


@pytest.mark.asyncio
async def test_context_engine_adapter_checkpoint_load():
    """
    Test 2.8.4: Test checkpoint loading.

    Verifies that ContextEngineAdapter can load checkpoints.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Save checkpoint
    checkpoint_data = {
        "agent_id": "agent-1",
        "state": "active",
        "metrics": {"tasks_executed": 10},
    }

    await adapter.store_checkpoint(
        thread_id="agent-1",
        checkpoint_id="checkpoint-1",
        checkpoint_data=checkpoint_data
    )

    # Load checkpoint
    loaded_checkpoint = await adapter.get_checkpoint(
        thread_id="agent-1",
        checkpoint_id="checkpoint-1"
    )

    assert loaded_checkpoint is not None
    loaded_data = loaded_checkpoint.get("data", loaded_checkpoint)
    assert loaded_data["agent_id"] == "agent-1"
    assert loaded_data["state"] == "active"
    assert loaded_data["metrics"]["tasks_executed"] == 10


@pytest.mark.asyncio
async def test_context_engine_adapter_checkpoint_versions():
    """
    Test 2.8.4: Test checkpoint versioning.

    Verifies that ContextEngineAdapter can list checkpoint versions.
    """
    context_engine = MockContextEngine()
    await context_engine.initialize()

    adapter = ContextEngineAdapter(context_engine, user_id="test-user")

    # Save multiple checkpoints with proper version structure
    for i in range(3):
        await adapter.store_checkpoint(
            thread_id="agent-1",
            checkpoint_id=f"checkpoint-{i}",
            checkpoint_data={
                "version": f"v{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "state": "active"
            }
        )

    # List checkpoints directly from context engine
    checkpoints = await context_engine.list_checkpoints(thread_id="agent-1")

    # Verify we have 3 checkpoints
    assert len(checkpoints) == 3


# ==================== Test 2.8.5: Checkpointer Protocol ====================


@pytest.mark.asyncio
async def test_checkpointer_protocol_implementation():
    """
    Test 2.8.5: Test checkpointer Protocol implementation.

    Verifies that custom checkpointer implements the protocol correctly.
    """
    checkpointer = MockCheckpointer()

    # Verify it implements the protocol
    assert isinstance(checkpointer, CheckpointerProtocol)

    # Test save
    checkpoint_id = await checkpointer.save_checkpoint(
        agent_id="agent-1",
        session_id="session-1",
        checkpoint_data={"test": "data"}
    )

    assert checkpoint_id is not None

    # Test load
    loaded = await checkpointer.load_checkpoint(
        agent_id="agent-1",
        session_id="session-1",
        checkpoint_id=checkpoint_id
    )

    assert loaded is not None
    assert loaded["test"] == "data"

    # Test list
    checkpoints = await checkpointer.list_checkpoints(
        agent_id="agent-1",
        session_id="session-1"
    )

    assert len(checkpoints) > 0
    assert checkpoint_id in checkpoints


# ==================== Test 2.8.6: Save/Load Checkpoint Methods ====================


@pytest.mark.asyncio
async def test_agent_save_checkpoint():
    """
    Test 2.8.6: Test save_checkpoint() method.

    Verifies that agent can save checkpoints.
    """
    config = AgentConfiguration()
    checkpointer = MockCheckpointer()

    agent = MockTestAgent(
        agent_id="test-agent-4",
        name="Test Agent",
        config=config,
        checkpointer=checkpointer,
    )

    await agent.initialize()

    # Save checkpoint
    checkpoint_id = await agent.save_checkpoint(session_id="session-1")

    assert checkpoint_id is not None
    assert checkpoint_id.startswith("checkpoint_")


@pytest.mark.asyncio
async def test_agent_load_checkpoint():
    """
    Test 2.8.6: Test load_checkpoint() method.

    Verifies that agent can load checkpoints.
    """
    config = AgentConfiguration()
    checkpointer = MockCheckpointer()

    agent = MockTestAgent(
        agent_id="test-agent-5",
        name="Test Agent",
        config=config,
        checkpointer=checkpointer,
    )

    await agent.initialize()

    # Update some state
    agent.update_metrics(execution_time=1.0, success=True)

    # Save checkpoint
    checkpoint_id = await agent.save_checkpoint(session_id="session-1")

    # Modify state
    agent.update_metrics(execution_time=2.0, success=False)

    # Load checkpoint
    success = await agent.load_checkpoint(
        session_id="session-1",
        checkpoint_id=checkpoint_id
    )

    assert success is True


@pytest.mark.asyncio
async def test_agent_checkpoint_without_checkpointer():
    """
    Test 2.8.6: Test checkpoint methods without checkpointer.

    Verifies that checkpoint methods handle missing checkpointer gracefully.
    """
    config = AgentConfiguration()

    agent = MockTestAgent(
        agent_id="test-agent-6",
        name="Test Agent",
        config=config,
    )

    await agent.initialize()

    # Try to save checkpoint (should return None)
    checkpoint_id = await agent.save_checkpoint(session_id="session-1")
    assert checkpoint_id is None

    # Try to load checkpoint (should return False)
    success = await agent.load_checkpoint(session_id="session-1")
    assert success is False


@pytest.mark.asyncio
async def test_agent_checkpoint_load_latest():
    """
    Test 2.8.6: Test loading latest checkpoint.

    Verifies that agent can load the latest checkpoint when ID not specified.
    """
    config = AgentConfiguration()
    checkpointer = MockCheckpointer()

    agent = MockTestAgent(
        agent_id="test-agent-7",
        name="Test Agent",
        config=config,
        checkpointer=checkpointer,
    )

    await agent.initialize()

    # Save multiple checkpoints
    await agent.save_checkpoint(session_id="session-1")
    await agent.save_checkpoint(session_id="session-1")
    checkpoint_id_3 = await agent.save_checkpoint(session_id="session-1")

    # Load latest (should load checkpoint_id_3)
    success = await agent.load_checkpoint(session_id="session-1")
    assert success is True


# ==================== Test 2.8.7: Fallback to In-Memory Storage ====================


@pytest.mark.asyncio
async def test_agent_without_context_engine():
    """
    Test 2.8.7: Test fallback to in-memory storage when ContextEngine not provided.

    Verifies that agent works without ContextEngine.
    """
    config = AgentConfiguration()

    agent = MockTestAgent(
        agent_id="test-agent-8",
        name="Test Agent",
        config=config,
    )

    await agent.initialize()

    # Agent should work normally
    assert agent._state == AgentState.ACTIVE

    # Can execute tasks
    result = await agent.execute_task({"test": "task"}, {})
    assert result["success"] is True


@pytest.mark.asyncio
async def test_agent_with_context_engine():
    """
    Test 2.8.7: Test agent with ContextEngine.

    Verifies that agent can use ContextEngine when provided.
    """
    config = AgentConfiguration()
    context_engine = MockContextEngine()
    await context_engine.initialize()

    agent = MockTestAgent(
        agent_id="test-agent-9",
        name="Test Agent",
        config=config,
        context_engine=context_engine,
    )

    await agent.initialize()

    # Agent should work with ContextEngine
    assert agent._state == AgentState.ACTIVE
    assert agent._context_engine is not None


@pytest.mark.asyncio
async def test_config_manager_protocol_compliance():
    """
    Test 2.8.1: Test ConfigManagerProtocol compliance.

    Verifies that MockConfigManager implements the protocol correctly.
    """
    config_manager = MockConfigManager()

    # Verify it implements the protocol
    assert isinstance(config_manager, ConfigManagerProtocol)

    # Test all protocol methods
    await config_manager.set_config("key", "value")
    value = await config_manager.get_config("key")
    assert value == "value"

    await config_manager.reload_config()


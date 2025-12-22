"""
Tests for Agent Adapter System

Comprehensive tests for AgentAdapter, StandardLLMAdapter, CustomAgentAdapter,
and AgentAdapterRegistry.
"""

import pytest
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock

from aiecs.domain.community.agent_adapter import (
    AgentAdapter,
    AgentCapability,
    StandardLLMAdapter,
    CustomAgentAdapter,
    AgentAdapterRegistry
)

logger = logging.getLogger(__name__)


# ============================================================================
# Mock Classes for Testing
# ============================================================================

class MockLLMClient:
    """Mock LLM client for testing StandardLLMAdapter."""
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.call_count = 0
    
    async def generate(self, prompt: str, model: str, **kwargs) -> str:
        """Mock generate method."""
        self.call_count += 1
        if self.should_fail:
            raise Exception("LLM generation failed")
        return f"Generated response for: {prompt[:50]}..."
    
    async def health_check(self):
        """Mock health check."""
        if self.should_fail:
            raise Exception("Health check failed")
        return {"status": "ok"}


class MockLLMClientWithComplete:
    """Mock LLM client with complete method instead of generate."""
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Mock complete method."""
        return f"Completed: {prompt[:30]}..."


class MockCustomAgent:
    """Mock custom agent for testing CustomAgentAdapter."""
    
    def __init__(self):
        self.initialized = False
        self.messages = []
    
    async def initialize(self):
        """Initialize the agent."""
        self.initialized = True
    
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Execute a task."""
        if not self.initialized:
            raise Exception("Agent not initialized")
        return f"Executed: {task}"
    
    async def send_message(self, message: str, recipient_id: Optional[str], 
                          message_type: str, **kwargs) -> Dict[str, Any]:
        """Send a message."""
        self.messages.append({
            "message": message,
            "recipient": recipient_id,
            "type": message_type
        })
        return {"status": "sent", "message_id": "msg_123"}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check."""
        return {
            "status": "healthy" if self.initialized else "not_initialized",
            "message_count": len(self.messages)
        }


class MockSyncCustomAgent:
    """Mock custom agent with synchronous methods."""
    
    def __init__(self):
        self.initialized = False
    
    def initialize(self):
        """Sync initialize."""
        self.initialized = True
    
    def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Sync execute."""
        return f"Sync executed: {task}"
    
    def health_check(self) -> Dict[str, Any]:
        """Sync health check."""
        return {"status": "healthy"}


class ConcreteAgentAdapter(AgentAdapter):
    """Concrete implementation of AgentAdapter for testing the base class."""
    
    async def initialize(self) -> bool:
        self._initialized = True
        self.capabilities = [AgentCapability.TEXT_GENERATION]
        return True
    
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        return {"status": "success", "output": f"Executed: {task}"}
    
    async def communicate(self, message: str, recipient_id: Optional[str] = None, 
                         message_type: str = "request", **kwargs) -> Dict[str, Any]:
        return {"status": "sent", "message": message}
    
    async def get_capabilities(self) -> List[AgentCapability]:
        return self.capabilities
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._initialized else "not_initialized"}


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_llm_client_failing():
    """Create a failing mock LLM client."""
    return MockLLMClient(should_fail=True)


@pytest.fixture
def mock_llm_client_with_complete():
    """Create a mock LLM client with complete method."""
    return MockLLMClientWithComplete()


@pytest.fixture
def mock_custom_agent():
    """Create a mock custom agent."""
    return MockCustomAgent()


@pytest.fixture
def mock_sync_custom_agent():
    """Create a mock synchronous custom agent."""
    return MockSyncCustomAgent()


@pytest.fixture
def agent_registry():
    """Create an agent adapter registry."""
    registry = AgentAdapterRegistry()
    logger.debug("Created AgentAdapterRegistry fixture")
    return registry


# ============================================================================
# Test AgentCapability Enum
# ============================================================================

class TestAgentCapability:
    """Tests for AgentCapability enum."""
    
    def test_capability_values(self):
        """Test that all capability values are strings."""
        logger.info("Testing AgentCapability enum values")
        
        capabilities = [
            AgentCapability.TEXT_GENERATION,
            AgentCapability.CODE_GENERATION,
            AgentCapability.DATA_ANALYSIS,
            AgentCapability.DECISION_MAKING,
            AgentCapability.KNOWLEDGE_RETRIEVAL,
            AgentCapability.TASK_PLANNING,
            AgentCapability.IMAGE_PROCESSING,
            AgentCapability.AUDIO_PROCESSING,
            AgentCapability.MULTIMODAL
        ]
        
        for cap in capabilities:
            assert isinstance(cap.value, str)
            logger.debug(f"Capability: {cap.name} = {cap.value}")
    
    def test_capability_count(self):
        """Test that we have expected number of capabilities."""
        logger.info("Testing AgentCapability count")
        
        capabilities = list(AgentCapability)
        assert len(capabilities) == 9
        logger.debug(f"Total capabilities: {len(capabilities)}")


# ============================================================================
# Test AgentAdapter Base Class
# ============================================================================

class TestAgentAdapterBase:
    """Tests for AgentAdapter base class."""
    
    @pytest.mark.asyncio
    async def test_adapter_initialization(self):
        """Test basic adapter initialization."""
        logger.info("Testing AgentAdapter base initialization")
        
        adapter = ConcreteAgentAdapter("test_agent", {"param": "value"})
        
        assert adapter.agent_id == "test_agent"
        assert adapter.config == {"param": "value"}
        assert adapter.capabilities == []
        assert adapter.metadata == {}
        assert adapter._initialized is False
        
        logger.debug(f"Adapter created with ID: {adapter.agent_id}")
    
    @pytest.mark.asyncio
    async def test_adapter_initialization_no_config(self):
        """Test adapter initialization without config."""
        logger.info("Testing AgentAdapter initialization without config")
        
        adapter = ConcreteAgentAdapter("test_agent")
        
        assert adapter.config == {}
        logger.debug("Adapter created with empty config")
    
    @pytest.mark.asyncio
    async def test_adapter_initialize_method(self):
        """Test adapter initialize method."""
        logger.info("Testing AgentAdapter initialize method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        assert len(adapter.capabilities) > 0
        logger.debug("Adapter initialized successfully")
    
    @pytest.mark.asyncio
    async def test_adapter_shutdown(self):
        """Test adapter shutdown method."""
        logger.info("Testing AgentAdapter shutdown method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        await adapter.initialize()
        
        assert adapter._initialized is True
        
        result = await adapter.shutdown()
        
        assert result is True
        assert adapter._initialized is False
        logger.debug("Adapter shutdown successfully")
    
    @pytest.mark.asyncio
    async def test_adapter_execute(self):
        """Test adapter execute method."""
        logger.info("Testing AgentAdapter execute method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        result = await adapter.execute("test task")
        
        assert result["status"] == "success"
        assert "test task" in result["output"]
        logger.debug(f"Execute result: {result}")
    
    @pytest.mark.asyncio
    async def test_adapter_communicate(self):
        """Test adapter communicate method."""
        logger.info("Testing AgentAdapter communicate method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        result = await adapter.communicate("hello", "recipient_123")
        
        assert result["status"] == "sent"
        assert result["message"] == "hello"
        logger.debug(f"Communicate result: {result}")
    
    @pytest.mark.asyncio
    async def test_adapter_get_capabilities(self):
        """Test adapter get_capabilities method."""
        logger.info("Testing AgentAdapter get_capabilities method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        await adapter.initialize()
        
        capabilities = await adapter.get_capabilities()
        
        assert isinstance(capabilities, list)
        assert AgentCapability.TEXT_GENERATION in capabilities
        logger.debug(f"Capabilities: {capabilities}")
    
    @pytest.mark.asyncio
    async def test_adapter_health_check(self):
        """Test adapter health_check method."""
        logger.info("Testing AgentAdapter health_check method")
        
        adapter = ConcreteAgentAdapter("test_agent")
        
        # Before initialization
        health = await adapter.health_check()
        assert health["status"] == "not_initialized"
        
        # After initialization
        await adapter.initialize()
        health = await adapter.health_check()
        assert health["status"] == "healthy"
        
        logger.debug(f"Health check: {health}")


# ============================================================================
# Test StandardLLMAdapter
# ============================================================================

class TestStandardLLMAdapter:
    """Tests for StandardLLMAdapter."""
    
    @pytest.mark.asyncio
    async def test_llm_adapter_creation(self, mock_llm_client):
        """Test StandardLLMAdapter creation."""
        logger.info("Testing StandardLLMAdapter creation")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4",
            config={"temperature": 0.7}
        )
        
        assert adapter.agent_id == "llm_agent_1"
        assert adapter.llm_client == mock_llm_client
        assert adapter.model_name == "gpt-4"
        assert adapter.config["temperature"] == 0.7
        assert AgentCapability.TEXT_GENERATION in adapter.capabilities
        assert AgentCapability.DECISION_MAKING in adapter.capabilities
        assert AgentCapability.KNOWLEDGE_RETRIEVAL in adapter.capabilities
        
        logger.debug(f"LLM adapter created with model: {adapter.model_name}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_initialize_success(self, mock_llm_client):
        """Test StandardLLMAdapter initialization success."""
        logger.info("Testing StandardLLMAdapter initialization success")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        logger.debug("LLM adapter initialized successfully")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_initialize_failure(self, mock_llm_client_failing):
        """Test StandardLLMAdapter initialization failure."""
        logger.info("Testing StandardLLMAdapter initialization failure")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client_failing,
            model_name="gpt-4"
        )
        
        result = await adapter.initialize()
        
        assert result is False
        assert adapter._initialized is False
        logger.debug("LLM adapter initialization failed as expected")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_initialize_no_health_check(self):
        """Test StandardLLMAdapter initialization without health_check method."""
        logger.info("Testing StandardLLMAdapter initialization without health_check")
        
        # Mock client without health_check method (using MagicMock to avoid await issues)
        mock_client = MagicMock()
        # Remove health_check attribute
        delattr(mock_client, 'health_check') if hasattr(mock_client, 'health_check') else None
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_client,
            model_name="gpt-4"
        )
        
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        logger.debug("LLM adapter initialized without health check")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_success(self, mock_llm_client):
        """Test StandardLLMAdapter execute success."""
        logger.info("Testing StandardLLMAdapter execute success")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        await adapter.initialize()
        
        result = await adapter.execute(
            task="Analyze this data",
            context={"system": "You are a helpful assistant"}
        )
        
        assert result["status"] == "success"
        assert "output" in result
        assert result["agent_id"] == "llm_agent_1"
        assert result["model"] == "gpt-4"
        assert mock_llm_client.call_count == 1
        
        logger.debug(f"Execute result: {result}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_not_initialized(self, mock_llm_client):
        """Test StandardLLMAdapter execute when not initialized."""
        logger.info("Testing StandardLLMAdapter execute when not initialized")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "error"
        assert "not initialized" in result["error"].lower()
        logger.debug("Execute correctly failed when not initialized")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_with_complete_method(self, mock_llm_client_with_complete):
        """Test StandardLLMAdapter with LLM client using complete method."""
        logger.info("Testing StandardLLMAdapter with complete method")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client_with_complete,
            model_name="gpt-3.5"
        )
        await adapter.initialize()
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "success"
        assert "Completed" in result["output"]
        logger.debug(f"Execute with complete method result: {result}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_fallback(self):
        """Test StandardLLMAdapter execute fallback."""
        logger.info("Testing StandardLLMAdapter execute fallback")
        
        # Create a simple object for fallback test
        class SimpleLLMClient:
            def __str__(self):
                return "Mock LLM Client"
        
        mock_client = SimpleLLMClient()
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_client,
            model_name="custom-model"
        )
        await adapter.initialize()
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "success"
        assert "Mock LLM Client" in result["output"]
        logger.debug("Execute used fallback successfully")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_with_context(self, mock_llm_client):
        """Test StandardLLMAdapter execute with context."""
        logger.info("Testing StandardLLMAdapter execute with context")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        await adapter.initialize()
        
        context = {
            "system": "You are a data analyst",
            "history": "Previous conversation..."
        }
        
        result = await adapter.execute(
            task="Analyze trends",
            context=context,
            max_tokens=100
        )
        
        assert result["status"] == "success"
        logger.debug(f"Execute with context result: {result}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_execute_error_handling(self, mock_llm_client_failing):
        """Test StandardLLMAdapter execute error handling."""
        logger.info("Testing StandardLLMAdapter execute error handling")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client_failing,
            model_name="gpt-4"
        )
        # Force initialization to succeed
        adapter._initialized = True
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "error"
        assert "error" in result
        logger.debug(f"Execute error handled: {result}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_communicate(self, mock_llm_client):
        """Test StandardLLMAdapter communicate method."""
        logger.info("Testing StandardLLMAdapter communicate")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await adapter.communicate(
            message="Hello, agent!",
            recipient_id="agent_2",
            message_type="request"
        )
        
        assert result["status"] == "formatted"
        assert result["message"]["from"] == "llm_agent_1"
        assert result["message"]["to"] == "agent_2"
        assert result["message"]["type"] == "request"
        assert result["message"]["content"] == "Hello, agent!"
        assert result["message"]["model"] == "gpt-4"
        
        logger.debug(f"Communicate result: {result}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_communicate_broadcast(self, mock_llm_client):
        """Test StandardLLMAdapter broadcast communication."""
        logger.info("Testing StandardLLMAdapter broadcast")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await adapter.communicate(
            message="Broadcast message",
            message_type="notification"
        )
        
        assert result["message"]["to"] == "broadcast"
        logger.debug("Broadcast message formatted")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_get_capabilities(self, mock_llm_client):
        """Test StandardLLMAdapter get_capabilities."""
        logger.info("Testing StandardLLMAdapter get_capabilities")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        capabilities = await adapter.get_capabilities()
        
        assert AgentCapability.TEXT_GENERATION in capabilities
        assert AgentCapability.DECISION_MAKING in capabilities
        assert AgentCapability.KNOWLEDGE_RETRIEVAL in capabilities
        assert len(capabilities) == 3
        
        logger.debug(f"Capabilities: {[c.value for c in capabilities]}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_health_check(self, mock_llm_client):
        """Test StandardLLMAdapter health check."""
        logger.info("Testing StandardLLMAdapter health check")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        # Before initialization
        health = await adapter.health_check()
        assert health["status"] == "not_initialized"
        
        # After initialization
        await adapter.initialize()
        health = await adapter.health_check()
        
        assert health["status"] == "healthy"
        assert health["agent_id"] == "llm_agent_1"
        assert health["model"] == "gpt-4"
        assert len(health["capabilities"]) == 3
        
        logger.debug(f"Health check: {health}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_build_prompt_no_context(self, mock_llm_client):
        """Test StandardLLMAdapter _build_prompt without context."""
        logger.info("Testing StandardLLMAdapter _build_prompt without context")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        prompt = adapter._build_prompt("Do something", None)
        
        assert "Task: Do something" in prompt
        logger.debug(f"Built prompt: {prompt}")
    
    @pytest.mark.asyncio
    async def test_llm_adapter_build_prompt_with_context(self, mock_llm_client):
        """Test StandardLLMAdapter _build_prompt with context."""
        logger.info("Testing StandardLLMAdapter _build_prompt with context")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_agent_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        context = {
            "system": "You are helpful",
            "history": "Previous messages"
        }
        
        prompt = adapter._build_prompt("Do something", context)
        
        assert "System: You are helpful" in prompt
        assert "History: Previous messages" in prompt
        assert "Task: Do something" in prompt
        
        logger.debug(f"Built prompt with context: {prompt}")


# ============================================================================
# Test CustomAgentAdapter
# ============================================================================

class TestCustomAgentAdapter:
    """Tests for CustomAgentAdapter."""
    
    @pytest.mark.asyncio
    async def test_custom_adapter_creation(self, mock_custom_agent):
        """Test CustomAgentAdapter creation."""
        logger.info("Testing CustomAgentAdapter creation")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent,
            execute_method="execute",
            capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.DATA_ANALYSIS],
            config={"param": "value"}
        )
        
        assert adapter.agent_id == "custom_agent_1"
        assert adapter.agent_instance == mock_custom_agent
        assert adapter.execute_method == "execute"
        assert len(adapter.capabilities) == 2
        assert AgentCapability.CODE_GENERATION in adapter.capabilities
        
        logger.debug(f"Custom adapter created with {len(adapter.capabilities)} capabilities")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_default_capabilities(self, mock_custom_agent):
        """Test CustomAgentAdapter with default capabilities."""
        logger.info("Testing CustomAgentAdapter default capabilities")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        
        assert len(adapter.capabilities) == 1
        assert AgentCapability.TEXT_GENERATION in adapter.capabilities
        logger.debug("Default capabilities set correctly")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_initialize_async(self, mock_custom_agent):
        """Test CustomAgentAdapter initialization with async agent."""
        logger.info("Testing CustomAgentAdapter initialization (async)")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        assert mock_custom_agent.initialized is True
        logger.debug("Custom adapter (async) initialized successfully")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_initialize_sync(self, mock_sync_custom_agent):
        """Test CustomAgentAdapter initialization with sync agent."""
        logger.info("Testing CustomAgentAdapter initialization (sync)")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_sync_custom_agent
        )
        
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        assert mock_sync_custom_agent.initialized is True
        logger.debug("Custom adapter (sync) initialized successfully")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_initialize_no_method(self):
        """Test CustomAgentAdapter initialization when agent has no initialize method."""
        logger.info("Testing CustomAgentAdapter initialization without method")
        
        mock_agent = Mock()
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_agent
        )
        
        result = await adapter.initialize()
        
        assert result is True
        assert adapter._initialized is True
        logger.debug("Custom adapter initialized without initialize method")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_initialize_failure(self):
        """Test CustomAgentAdapter initialization failure."""
        logger.info("Testing CustomAgentAdapter initialization failure")
        
        mock_agent = Mock()
        mock_agent.initialize = Mock(side_effect=Exception("Init failed"))
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_agent
        )
        
        result = await adapter.initialize()
        
        assert result is False
        assert adapter._initialized is False
        logger.debug("Custom adapter initialization failed as expected")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_execute_async(self, mock_custom_agent):
        """Test CustomAgentAdapter execute with async agent."""
        logger.info("Testing CustomAgentAdapter execute (async)")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        await adapter.initialize()
        
        result = await adapter.execute(
            task="Process data",
            context={"key": "value"}
        )
        
        assert result["status"] == "success"
        assert "Process data" in result["output"]
        assert result["agent_id"] == "custom_agent_1"
        
        logger.debug(f"Execute result: {result}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_execute_sync(self, mock_sync_custom_agent):
        """Test CustomAgentAdapter execute with sync agent."""
        logger.info("Testing CustomAgentAdapter execute (sync)")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_sync_custom_agent
        )
        await adapter.initialize()
        
        result = await adapter.execute(task="Process data")
        
        assert result["status"] == "success"
        assert "Sync executed" in result["output"]
        logger.debug(f"Execute (sync) result: {result}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_execute_not_initialized(self, mock_custom_agent):
        """Test CustomAgentAdapter execute when not initialized."""
        logger.info("Testing CustomAgentAdapter execute when not initialized")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "error"
        assert "not initialized" in result["error"].lower()
        logger.debug("Execute correctly failed when not initialized")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_execute_method_not_found(self, mock_custom_agent):
        """Test CustomAgentAdapter execute when method not found."""
        logger.info("Testing CustomAgentAdapter execute with missing method")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent,
            execute_method="nonexistent_method"
        )
        await adapter.initialize()
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()
        logger.debug("Execute correctly failed with missing method")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_execute_error_handling(self, mock_custom_agent):
        """Test CustomAgentAdapter execute error handling."""
        logger.info("Testing CustomAgentAdapter execute error handling")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        # Don't initialize the mock_custom_agent, but force adapter initialized
        adapter._initialized = True
        
        result = await adapter.execute(task="Test task")
        
        assert result["status"] == "error"
        logger.debug(f"Execute error handled: {result}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_communicate_with_method(self, mock_custom_agent):
        """Test CustomAgentAdapter communicate with send_message method."""
        logger.info("Testing CustomAgentAdapter communicate with method")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        await adapter.initialize()
        
        result = await adapter.communicate(
            message="Hello",
            recipient_id="agent_2",
            message_type="request"
        )
        
        assert result["status"] == "sent"
        assert result["message_id"] == "msg_123"
        assert len(mock_custom_agent.messages) == 1
        assert mock_custom_agent.messages[0]["message"] == "Hello"
        
        logger.debug(f"Communicate result: {result}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_communicate_sync_method(self, mock_sync_custom_agent):
        """Test CustomAgentAdapter communicate with sync send_message."""
        logger.info("Testing CustomAgentAdapter communicate (sync method)")
        
        # Add sync send_message to mock
        mock_sync_custom_agent.send_message = lambda msg, rec, mtype, **kw: {
            "status": "sent_sync"
        }
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_sync_custom_agent
        )
        
        result = await adapter.communicate(message="Test")
        
        assert result["status"] == "sent_sync"
        logger.debug("Sync communicate worked")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_communicate_default(self):
        """Test CustomAgentAdapter communicate without send_message method."""
        logger.info("Testing CustomAgentAdapter communicate default behavior")
        
        # Create simple agent without send_message method
        class SimpleAgent:
            pass
        
        mock_agent = SimpleAgent()
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_agent
        )
        
        result = await adapter.communicate(
            message="Hello",
            recipient_id="agent_2",
            message_type="request"
        )
        
        assert result["status"] == "formatted"
        assert result["message"]["from"] == "custom_agent_1"
        assert result["message"]["to"] == "agent_2"
        assert result["message"]["content"] == "Hello"
        
        logger.debug("Default communicate formatting worked")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_communicate_broadcast(self, mock_custom_agent):
        """Test CustomAgentAdapter broadcast communication."""
        logger.info("Testing CustomAgentAdapter broadcast")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        await adapter.initialize()
        
        result = await adapter.communicate(
            message="Broadcast",
            message_type="notification"
        )
        
        assert result["status"] == "sent"
        assert mock_custom_agent.messages[0]["recipient"] is None
        logger.debug("Broadcast message sent")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_get_capabilities(self, mock_custom_agent):
        """Test CustomAgentAdapter get_capabilities."""
        logger.info("Testing CustomAgentAdapter get_capabilities")
        
        capabilities = [
            AgentCapability.CODE_GENERATION,
            AgentCapability.TASK_PLANNING
        ]
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent,
            capabilities=capabilities
        )
        
        result = await adapter.get_capabilities()
        
        assert result == capabilities
        assert len(result) == 2
        logger.debug(f"Capabilities: {[c.value for c in result]}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_health_check_with_method(self, mock_custom_agent):
        """Test CustomAgentAdapter health check with method."""
        logger.info("Testing CustomAgentAdapter health check with method")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_custom_agent
        )
        await adapter.initialize()
        
        health = await adapter.health_check()
        
        assert health["status"] == "healthy"
        assert health["message_count"] == 0
        logger.debug(f"Health check: {health}")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_health_check_sync_method(self, mock_sync_custom_agent):
        """Test CustomAgentAdapter health check with sync method."""
        logger.info("Testing CustomAgentAdapter health check (sync)")
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_sync_custom_agent
        )
        await adapter.initialize()
        
        health = await adapter.health_check()
        
        assert health["status"] == "healthy"
        logger.debug("Sync health check worked")
    
    @pytest.mark.asyncio
    async def test_custom_adapter_health_check_default(self):
        """Test CustomAgentAdapter health check default behavior."""
        logger.info("Testing CustomAgentAdapter health check default")
        
        # Create simple agent without health_check method
        class SimpleAgent:
            pass
        
        mock_agent = SimpleAgent()
        
        adapter = CustomAgentAdapter(
            agent_id="custom_agent_1",
            agent_instance=mock_agent,
            capabilities=[AgentCapability.IMAGE_PROCESSING]
        )
        
        # Before initialization
        health = await adapter.health_check()
        assert health["status"] == "not_initialized"
        
        # After initialization
        await adapter.initialize()
        health = await adapter.health_check()
        
        assert health["status"] == "healthy"
        assert health["agent_id"] == "custom_agent_1"
        assert len(health["capabilities"]) == 1
        assert health["capabilities"][0] == "image_processing"
        
        logger.debug(f"Default health check: {health}")


# ============================================================================
# Test AgentAdapterRegistry
# ============================================================================

class TestAgentAdapterRegistry:
    """Tests for AgentAdapterRegistry."""
    
    def test_registry_creation(self, agent_registry):
        """Test registry creation."""
        logger.info("Testing AgentAdapterRegistry creation")
        
        assert len(agent_registry.adapters) == 0
        assert "standard_llm" in agent_registry.adapter_types
        assert "custom" in agent_registry.adapter_types
        
        logger.debug("Registry created with default adapter types")
    
    def test_registry_register_adapter_type(self, agent_registry):
        """Test registering a new adapter type."""
        logger.info("Testing adapter type registration")
        
        class NewAdapterType(AgentAdapter):
            async def initialize(self) -> bool:
                return True
            async def execute(self, task: str, context=None, **kwargs):
                return {}
            async def communicate(self, message: str, recipient_id=None, message_type="request", **kwargs):
                return {}
            async def get_capabilities(self):
                return []
            async def health_check(self):
                return {}
        
        agent_registry.register_adapter_type("new_type", NewAdapterType)
        
        assert "new_type" in agent_registry.adapter_types
        assert agent_registry.adapter_types["new_type"] == NewAdapterType
        
        logger.debug("New adapter type registered successfully")
    
    @pytest.mark.asyncio
    async def test_registry_register_adapter_success(self, agent_registry, mock_llm_client):
        """Test registering an adapter successfully."""
        logger.info("Testing adapter registration success")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await agent_registry.register_adapter(adapter, auto_initialize=True)
        
        assert result is True
        assert "llm_1" in agent_registry.adapters
        assert adapter._initialized is True
        
        logger.debug("Adapter registered and initialized")
    
    @pytest.mark.asyncio
    async def test_registry_register_adapter_no_auto_init(self, agent_registry, mock_llm_client):
        """Test registering an adapter without auto-initialization."""
        logger.info("Testing adapter registration without auto-init")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_2",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        
        result = await agent_registry.register_adapter(adapter, auto_initialize=False)
        
        assert result is True
        assert "llm_2" in agent_registry.adapters
        assert adapter._initialized is False
        
        logger.debug("Adapter registered without initialization")
    
    @pytest.mark.asyncio
    async def test_registry_register_adapter_already_initialized(self, agent_registry, mock_llm_client):
        """Test registering an already initialized adapter."""
        logger.info("Testing adapter registration when already initialized")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_3",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        await adapter.initialize()
        
        result = await agent_registry.register_adapter(adapter, auto_initialize=True)
        
        assert result is True
        assert "llm_3" in agent_registry.adapters
        
        logger.debug("Already initialized adapter registered")
    
    @pytest.mark.asyncio
    async def test_registry_register_adapter_replace(self, agent_registry, mock_llm_client):
        """Test replacing an existing adapter."""
        logger.info("Testing adapter replacement")
        
        adapter1 = StandardLLMAdapter(
            agent_id="llm_1",
            llm_client=mock_llm_client,
            model_name="gpt-3.5"
        )
        await agent_registry.register_adapter(adapter1)
        
        adapter2 = StandardLLMAdapter(
            agent_id="llm_1",
            llm_client=mock_llm_client,
            model_name="gpt-4"
        )
        await agent_registry.register_adapter(adapter2)
        
        registered_adapter = agent_registry.get_adapter("llm_1")
        assert registered_adapter.model_name == "gpt-4"
        
        logger.debug("Adapter replaced successfully")
    
    @pytest.mark.asyncio
    async def test_registry_register_adapter_init_failure(self, agent_registry, mock_llm_client_failing):
        """Test adapter registration with initialization failure."""
        logger.info("Testing adapter registration with init failure")
        
        adapter = StandardLLMAdapter(
            agent_id="llm_fail",
            llm_client=mock_llm_client_failing,
            model_name="gpt-4"
        )
        
        result = await agent_registry.register_adapter(adapter, auto_initialize=True)
        
        assert result is False
        assert "llm_fail" not in agent_registry.adapters
        
        logger.debug("Registration correctly failed on init failure")
    
    def test_registry_get_adapter_success(self, agent_registry):
        """Test getting an adapter successfully."""
        logger.info("Testing get adapter success")
        
        adapter = ConcreteAgentAdapter("test_agent")
        agent_registry.adapters["test_agent"] = adapter
        
        retrieved = agent_registry.get_adapter("test_agent")
        
        assert retrieved == adapter
        assert retrieved.agent_id == "test_agent"
        
        logger.debug("Adapter retrieved successfully")
    
    def test_registry_get_adapter_not_found(self, agent_registry):
        """Test getting a non-existent adapter."""
        logger.info("Testing get adapter not found")
        
        result = agent_registry.get_adapter("nonexistent")
        
        assert result is None
        logger.debug("Correctly returned None for non-existent adapter")
    
    def test_registry_unregister_adapter_success(self, agent_registry):
        """Test unregistering an adapter successfully."""
        logger.info("Testing unregister adapter success")
        
        adapter = ConcreteAgentAdapter("test_agent")
        agent_registry.adapters["test_agent"] = adapter
        
        result = agent_registry.unregister_adapter("test_agent")
        
        assert result is True
        assert "test_agent" not in agent_registry.adapters
        
        logger.debug("Adapter unregistered successfully")
    
    def test_registry_unregister_adapter_not_found(self, agent_registry):
        """Test unregistering a non-existent adapter."""
        logger.info("Testing unregister adapter not found")
        
        result = agent_registry.unregister_adapter("nonexistent")
        
        assert result is False
        logger.debug("Correctly returned False for non-existent adapter")
    
    @pytest.mark.asyncio
    async def test_registry_list_adapters(self, agent_registry, mock_llm_client, mock_custom_agent):
        """Test listing all adapters."""
        logger.info("Testing list adapters")
        
        adapter1 = StandardLLMAdapter("llm_1", mock_llm_client, "gpt-4")
        adapter2 = CustomAgentAdapter("custom_1", mock_custom_agent)
        adapter3 = StandardLLMAdapter("llm_2", mock_llm_client, "gpt-3.5")
        
        await agent_registry.register_adapter(adapter1)
        await agent_registry.register_adapter(adapter2)
        await agent_registry.register_adapter(adapter3)
        
        adapter_list = agent_registry.list_adapters()
        
        assert len(adapter_list) == 3
        assert "llm_1" in adapter_list
        assert "custom_1" in adapter_list
        assert "llm_2" in adapter_list
        
        logger.debug(f"Listed adapters: {adapter_list}")
    
    @pytest.mark.asyncio
    async def test_registry_list_adapters_empty(self, agent_registry):
        """Test listing adapters when registry is empty."""
        logger.info("Testing list adapters (empty)")
        
        adapter_list = agent_registry.list_adapters()
        
        assert len(adapter_list) == 0
        assert adapter_list == []
        
        logger.debug("Empty adapter list returned")
    
    @pytest.mark.asyncio
    async def test_registry_health_check_all_success(self, agent_registry, mock_llm_client, mock_custom_agent):
        """Test health check on all adapters - success."""
        logger.info("Testing health check all adapters (success)")
        
        adapter1 = StandardLLMAdapter("llm_1", mock_llm_client, "gpt-4")
        adapter2 = CustomAgentAdapter("custom_1", mock_custom_agent)
        
        await agent_registry.register_adapter(adapter1)
        await agent_registry.register_adapter(adapter2)
        
        health_statuses = await agent_registry.health_check_all()
        
        assert len(health_statuses) == 2
        assert "llm_1" in health_statuses
        assert "custom_1" in health_statuses
        assert health_statuses["llm_1"]["status"] == "healthy"
        assert health_statuses["custom_1"]["status"] == "healthy"
        
        logger.debug(f"Health statuses: {health_statuses}")
    
    @pytest.mark.asyncio
    async def test_registry_health_check_all_with_error(self, agent_registry):
        """Test health check with an adapter that raises an error."""
        logger.info("Testing health check all with error")
        
        # Create a mock adapter that fails health check
        mock_adapter = Mock(spec=AgentAdapter)
        mock_adapter.health_check = AsyncMock(side_effect=Exception("Health check failed"))
        
        agent_registry.adapters["failing_adapter"] = mock_adapter
        
        health_statuses = await agent_registry.health_check_all()
        
        assert "failing_adapter" in health_statuses
        assert health_statuses["failing_adapter"]["status"] == "error"
        assert "Health check failed" in health_statuses["failing_adapter"]["error"]
        
        logger.debug("Health check error handled correctly")
    
    @pytest.mark.asyncio
    async def test_registry_health_check_all_empty(self, agent_registry):
        """Test health check when registry is empty."""
        logger.info("Testing health check all (empty registry)")
        
        health_statuses = await agent_registry.health_check_all()
        
        assert len(health_statuses) == 0
        assert health_statuses == {}
        
        logger.debug("Empty health check returned")


# ============================================================================
# Integration Tests
# ============================================================================

class TestAgentAdapterIntegration:
    """Integration tests for the agent adapter system."""
    
    @pytest.mark.asyncio
    async def test_multiple_adapter_types_in_registry(self, agent_registry, mock_llm_client, mock_custom_agent):
        """Test managing multiple adapter types in one registry."""
        logger.info("Testing multiple adapter types integration")
        
        # Create different adapter types
        llm_adapter = StandardLLMAdapter("llm_gpt4", mock_llm_client, "gpt-4")
        custom_adapter = CustomAgentAdapter(
            "custom_analyzer",
            mock_custom_agent,
            capabilities=[AgentCapability.DATA_ANALYSIS]
        )
        
        # Register all adapters
        await agent_registry.register_adapter(llm_adapter)
        await agent_registry.register_adapter(custom_adapter)
        
        # Verify all registered
        assert len(agent_registry.list_adapters()) == 2
        
        # Execute tasks on different adapters
        llm_result = await llm_adapter.execute("Generate text")
        custom_result = await custom_adapter.execute("Analyze data")
        
        assert llm_result["status"] == "success"
        assert custom_result["status"] == "success"
        
        # Health check all
        health = await agent_registry.health_check_all()
        assert len(health) == 2
        assert all(h["status"] == "healthy" for h in health.values())
        
        logger.debug("Multiple adapter types working together")
    
    @pytest.mark.asyncio
    async def test_adapter_lifecycle(self, agent_registry, mock_llm_client):
        """Test complete adapter lifecycle."""
        logger.info("Testing adapter lifecycle")
        
        # Create adapter
        adapter = StandardLLMAdapter("lifecycle_test", mock_llm_client, "gpt-4")
        assert adapter._initialized is False
        
        # Register (auto-initialize)
        await agent_registry.register_adapter(adapter)
        assert adapter._initialized is True
        
        # Execute task
        result = await adapter.execute("Test task")
        assert result["status"] == "success"
        
        # Health check
        health = await adapter.health_check()
        assert health["status"] == "healthy"
        
        # Shutdown
        shutdown_result = await adapter.shutdown()
        assert shutdown_result is True
        assert adapter._initialized is False
        
        # Unregister
        unregister_result = agent_registry.unregister_adapter("lifecycle_test")
        assert unregister_result is True
        assert agent_registry.get_adapter("lifecycle_test") is None
        
        logger.debug("Complete lifecycle tested successfully")
    
    @pytest.mark.asyncio
    async def test_adapter_communication_workflow(self, mock_custom_agent):
        """Test communication workflow between adapters."""
        logger.info("Testing adapter communication workflow")
        
        # Create two custom adapters
        agent1 = MockCustomAgent()
        agent2 = MockCustomAgent()
        
        adapter1 = CustomAgentAdapter("agent_1", agent1)
        adapter2 = CustomAgentAdapter("agent_2", agent2)
        
        await adapter1.initialize()
        await adapter2.initialize()
        
        # Agent 1 sends message
        result1 = await adapter1.communicate(
            message="Request from agent 1",
            recipient_id="agent_2",
            message_type="request"
        )
        
        assert result1["status"] == "sent"
        
        # Agent 2 responds
        result2 = await adapter2.communicate(
            message="Response from agent 2",
            recipient_id="agent_1",
            message_type="response"
        )
        
        assert result2["status"] == "sent"
        assert len(agent1.messages) == 1
        assert len(agent2.messages) == 1
        
        logger.debug("Communication workflow completed")
    
    @pytest.mark.asyncio
    async def test_capability_based_adapter_selection(self, agent_registry, mock_llm_client, mock_custom_agent):
        """Test selecting adapters based on capabilities."""
        logger.info("Testing capability-based adapter selection")
        
        # Create adapters with different capabilities
        text_adapter = StandardLLMAdapter("text_gen", mock_llm_client, "gpt-4")
        code_adapter = CustomAgentAdapter(
            "code_gen",
            mock_custom_agent,
            capabilities=[AgentCapability.CODE_GENERATION]
        )
        data_adapter = CustomAgentAdapter(
            "data_analyzer",
            MockCustomAgent(),
            capabilities=[AgentCapability.DATA_ANALYSIS]
        )
        
        await agent_registry.register_adapter(text_adapter)
        await agent_registry.register_adapter(code_adapter)
        await agent_registry.register_adapter(data_adapter)
        
        # Get capabilities for each
        text_caps = await text_adapter.get_capabilities()
        code_caps = await code_adapter.get_capabilities()
        data_caps = await data_adapter.get_capabilities()
        
        # Verify capabilities
        assert AgentCapability.TEXT_GENERATION in text_caps
        assert AgentCapability.CODE_GENERATION in code_caps
        assert AgentCapability.DATA_ANALYSIS in data_caps
        
        # Simulate selecting adapter based on required capability
        def find_adapter_with_capability(capability: AgentCapability):
            for adapter_id in agent_registry.list_adapters():
                adapter = agent_registry.get_adapter(adapter_id)
                if capability in adapter.capabilities:
                    return adapter
            return None
        
        selected = find_adapter_with_capability(AgentCapability.CODE_GENERATION)
        assert selected is not None
        assert selected.agent_id == "code_gen"
        
        logger.debug("Capability-based selection working")
    
    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self, agent_registry, mock_llm_client_failing):
        """Test error recovery and fallback mechanisms."""
        logger.info("Testing error recovery and fallback")
        
        # Create failing and working adapters
        failing_adapter = StandardLLMAdapter("failing", mock_llm_client_failing, "gpt-4")
        failing_adapter._initialized = True  # Force initialized to test execute
        
        working_adapter = StandardLLMAdapter("working", MockLLMClient(), "gpt-4")
        
        await agent_registry.register_adapter(failing_adapter, auto_initialize=False)
        await agent_registry.register_adapter(working_adapter)
        
        # Try failing adapter first
        result1 = await failing_adapter.execute("Test task")
        assert result1["status"] == "error"
        
        # Fallback to working adapter
        result2 = await working_adapter.execute("Test task")
        assert result2["status"] == "success"
        
        logger.debug("Error recovery and fallback tested")


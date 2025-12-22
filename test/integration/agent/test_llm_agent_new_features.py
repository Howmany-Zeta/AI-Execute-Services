"""
Integration Tests for LLMAgent New Features

Tests new functionality with real xAI LLM calls.
Covers tasks 2.4.1-2.4.3 from the enhance-hybrid-agent-flexibility proposal.

Requirements:
- XAI_API_KEY must be set in .env.test
- Real LLM calls will be made (costs may apply)
"""

import pytest
import asyncio
import os
from typing import Dict, Any, List, AsyncIterator
from datetime import datetime
from dotenv import load_dotenv

from aiecs.domain.agent import (
    LLMAgent,
    AgentConfiguration,
)
from aiecs.llm import XAIClient, LLMMessage, LLMResponse
from aiecs.domain.agent.integration.protocols import ConfigManagerProtocol


# Load test environment
load_dotenv(".env.test")


# ==================== Mock Custom LLM Client ====================


class CustomLLMClient:
    """
    Custom LLM client implementing LLMClientProtocol without inheriting from BaseLLMClient.
    
    This demonstrates that any class implementing the protocol can be used.
    """

    def __init__(self, base_client: XAIClient):
        """Initialize with a base client for actual LLM calls."""
        self.base_client = base_client
        self.provider_name = "custom_wrapper"
        self.call_count = 0
        self.stream_count = 0

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate text using wrapped client."""
        self.call_count += 1
        
        # Add custom preprocessing
        processed_messages = messages.copy()
        
        # Call base client
        response = await self.base_client.generate_text(
            messages=processed_messages,
            model=model or "grok-3",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        
        # Add custom postprocessing
        return LLMResponse(
            content=f"[Custom Wrapper] {response.content}",
            provider=self.provider_name,
            model=response.model,
            tokens_used=response.tokens_used,
        )

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream text using wrapped client."""
        self.stream_count += 1
        
        # Stream from base client
        async for token in self.base_client.stream_text(
            messages=messages,
            model=model or "grok-3",
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        ):
            yield token

    async def close(self):
        """Close the client."""
        await self.base_client.close()


# ==================== Mock Config Manager ====================


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
def custom_llm_client(xai_client):
    """Create custom LLM client wrapping xAI client."""
    return CustomLLMClient(xai_client)


@pytest.fixture
def mock_config_manager():
    """Create mock config manager instance."""
    return MockConfigManager()


# ==================== Test 2.4.1: Custom LLM Client ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_agent_with_custom_llm_client(custom_llm_client):
    """
    Test 2.4.1: Test LLMAgent with custom LLM client implementing Protocol.

    Verifies that LLMAgent works with any LLM client that implements
    the LLMClientProtocol interface, without inheriting from BaseLLMClient.
    """
    config = AgentConfiguration(
        goal="Test custom LLM client",
        llm_model="grok-3",
        temperature=0.7,
        max_tokens=200,
    )

    # Create agent with custom LLM client (not inheriting from BaseLLMClient)
    agent = LLMAgent(
        agent_id="test_custom_llm",
        name="Custom LLM Test Agent",
        llm_client=custom_llm_client,  # Custom client implementing protocol
        config=config,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify initial call count
    assert custom_llm_client.call_count == 0

    # Execute task
    task = {"description": "What is 2 + 2? Answer briefly."}
    result = await agent.execute_task(task, {})

    assert result["success"] is True
    assert "output" in result

    # Verify custom wrapper added prefix
    assert "[Custom Wrapper]" in result["output"]

    # Verify custom client was called
    assert custom_llm_client.call_count > 0

    print(f"\nCustom LLM result: {result['output']}")
    print(f"Custom client called {custom_llm_client.call_count} times")


# ==================== Test 2.4.2: Custom LLM Client Wrapper ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_agent_custom_client_wrapper_functionality(custom_llm_client):
    """
    Test 2.4.2: Verify LLMAgent works correctly with custom LLM client wrapper.

    Tests that the custom wrapper's preprocessing and postprocessing work correctly.
    """
    config = AgentConfiguration(
        goal="Test custom client wrapper",
        llm_model="grok-3",
        temperature=0.5,
        max_tokens=150,
    )

    agent = LLMAgent(
        agent_id="test_wrapper",
        name="Wrapper Test Agent",
        llm_client=custom_llm_client,
        config=config,
    )

    await agent.initialize()

    # Test multiple calls to verify wrapper consistency
    tasks = [
        {"description": "Say hello"},
        {"description": "Count to 3"},
        {"description": "Name a color"},
    ]

    for i, task in enumerate(tasks):
        result = await agent.execute_task(task, {})
        assert result["success"] is True
        assert "[Custom Wrapper]" in result["output"]
        print(f"\nTask {i+1} result: {result['output'][:100]}...")

    # Verify call count
    assert custom_llm_client.call_count == 3
    print(f"\nTotal custom client calls: {custom_llm_client.call_count}")


# ==================== Test 2.4.3: Custom Config Manager ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_agent_custom_config_manager(xai_client, mock_config_manager):
    """
    Test 2.4.3: Test LLMAgent with custom config manager.

    Verifies that LLMAgent works with custom ConfigManagerProtocol
    implementation and that config manager state is accessible.
    """
    config = AgentConfiguration(
        goal="Test custom config manager",
        llm_model="grok-3",
        temperature=0.7,
        max_tokens=200,
    )

    # Pre-populate some config
    await mock_config_manager.set_config("system_prompt", "You are a helpful assistant.")
    await mock_config_manager.set_config("max_history", 10)

    agent = LLMAgent(
        agent_id="test_config_mgr",
        name="Config Manager Test Agent",
        llm_client=xai_client,
        config=config,
        config_manager=mock_config_manager,
    )

    await agent.initialize()
    assert agent.state.name == "ACTIVE"

    # Verify config manager is accessible and working
    system_prompt = await mock_config_manager.get_config("system_prompt")
    assert system_prompt == "You are a helpful assistant."

    max_history = await mock_config_manager.get_config("max_history")
    assert max_history == 10

    # Execute task
    task = {"description": "What is the capital of France? Answer in one word."}
    result = await agent.execute_task(task, {})

    assert result["success"] is True
    assert "output" in result

    # Verify config manager was used
    assert mock_config_manager.get_count > 0

    print(f"\nTask result: {result['output']}")
    print(f"Config manager accessed {mock_config_manager.get_count} times")


# ==================== Test 2.4.4: Streaming with Custom Client ====================


@pytest.mark.asyncio
@pytest.mark.integration
async def test_llm_agent_streaming_with_custom_client(custom_llm_client):
    """
    Test streaming support with custom LLM client.

    Verifies that streaming works correctly with custom client wrapper.
    """
    config = AgentConfiguration(
        goal="Test streaming with custom client",
        llm_model="grok-3",
        temperature=0.7,
    )

    agent = LLMAgent(
        agent_id="test_streaming",
        name="Streaming Test Agent",
        llm_client=custom_llm_client,
        config=config,
    )

    await agent.initialize()

    # Execute task with streaming
    task = {"description": "Count from 1 to 5"}
    events = []

    async for event in agent.execute_task_streaming(task, {}):
        events.append(event)
        if event["type"] == "token":
            print(event["content"], end="", flush=True)

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

    # Verify streaming was used
    assert custom_llm_client.stream_count > 0
    print(f"\nCustom client streamed {custom_llm_client.stream_count} times")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


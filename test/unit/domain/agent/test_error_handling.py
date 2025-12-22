"""
Error Handling Tests for Agent Flexibility Features

Tests error handling for invalid tool instances, LLM clients, config managers, and checkpointers.
Covers tasks 2.5.1-2.5.5 from the enhance-hybrid-agent-flexibility proposal.
"""

import pytest
from typing import Dict, Any, List

from aiecs.domain.agent import (
    HybridAgent,
    ToolAgent,
    LLMAgent,
    AgentConfiguration,
)
from aiecs.tools import BaseTool
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


# ==================== Invalid Tool Instances ====================


class NotAToolClass:
    """Class that doesn't inherit from BaseTool."""

    def __init__(self):
        self.name = "not_a_tool"

    async def some_method(self):
        return "I'm not a tool!"


class InvalidTool:
    """Another class that doesn't inherit from BaseTool."""

    pass


# ==================== Invalid LLM Clients ====================


class IncompleteLLMClient:
    """LLM client missing required methods."""

    provider_name = "incomplete"

    async def generate_text(self, messages, **kwargs):
        """Has generate_text but missing stream_text and close."""
        return LLMResponse(
            content="test",
            provider="incomplete",
            model="test",
            tokens_used=10,
        )


class NoMethodsLLMClient:
    """LLM client with no methods at all."""

    provider_name = "no_methods"


class WrongSignatureLLMClient:
    """LLM client with wrong method signatures."""

    provider_name = "wrong_signature"

    async def generate_text(self):  # Missing required parameters
        return "wrong"

    async def stream_text(self):  # Missing required parameters
        yield "wrong"

    async def close(self):
        pass


# ==================== Invalid Config Managers ====================


class IncompleteConfigManager:
    """Config manager missing required methods."""

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Has get_config but missing other methods."""
        return None


class NoMethodsConfigManager:
    """Config manager with no methods."""

    pass


# ==================== Invalid Checkpointers ====================


class IncompleteCheckpointer:
    """Checkpointer missing required methods."""

    async def save_checkpoint(self, agent_id: str, data: Dict[str, Any]) -> str:
        """Has save_checkpoint but missing other methods."""
        return "checkpoint_1"


class NoMethodsCheckpointer:
    """Checkpointer with no methods."""

    pass


# ==================== Mock Valid Implementations ====================


class MockLLMClient(BaseLLMClient):
    """Valid mock LLM client for testing."""

    def __init__(self):
        super().__init__(provider_name="mock")

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="Mock response",
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
        yield "Mock"
        yield " "
        yield "stream"

    async def close(self):
        pass


class ValidTool(BaseTool):
    """Valid tool for testing."""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)

    async def execute_operation(self, data: str) -> Dict[str, Any]:
        return {"result": f"Processed: {data}"}


# ==================== Test 2.5.1: Invalid Tool Instances ====================


@pytest.mark.asyncio
async def test_hybrid_agent_invalid_tool_instance():
    """
    Test 2.5.1: Test error handling for invalid tool instances in HybridAgent.

    Verifies that HybridAgent rejects tool instances that don't inherit from BaseTool.
    """
    config = AgentConfiguration(goal="Test invalid tools")
    llm_client = MockLLMClient()

    # Test with invalid tool instance
    invalid_tools = {
        "valid_tool": ValidTool(),
        "invalid_tool": NotAToolClass(),  # Not a BaseTool!
    }

    # This should work - agent creation doesn't validate tools yet
    agent = HybridAgent(
        agent_id="test_invalid_tools",
        name="Invalid Tools Test",
        llm_client=llm_client,
        tools=invalid_tools,
        config=config,
    )

    # Error should occur during initialization when tools are validated
    with pytest.raises(Exception) as exc_info:
        await agent.initialize()

    # Verify error message is helpful
    error_msg = str(exc_info.value)
    assert "tool" in error_msg.lower() or "baseTool" in error_msg or "invalid" in error_msg.lower()
    print(f"\nError message: {error_msg}")


@pytest.mark.asyncio
async def test_tool_agent_invalid_tool_instance():
    """
    Test 2.5.1: Test error handling for invalid tool instances in ToolAgent.

    Verifies that ToolAgent rejects tool instances that don't inherit from BaseTool.
    """
    config = AgentConfiguration(goal="Test invalid tools")

    # Test with completely invalid tool
    invalid_tools = {
        "invalid": InvalidTool(),  # Not a BaseTool!
    }

    agent = ToolAgent(
        agent_id="test_invalid_tools",
        name="Invalid Tools Test",
        tools=invalid_tools,
        config=config,
    )

    # Error should occur during initialization
    with pytest.raises(Exception) as exc_info:
        await agent.initialize()

    error_msg = str(exc_info.value)
    assert "tool" in error_msg.lower() or "baseTool" in error_msg or "invalid" in error_msg.lower()
    print(f"\nToolAgent error message: {error_msg}")


# ==================== Test 2.5.2: Invalid LLM Clients ====================


@pytest.mark.asyncio
async def test_hybrid_agent_invalid_llm_client_missing_methods():
    """
    Test 2.5.2: Test error handling for invalid LLM client in HybridAgent.

    Verifies that HybridAgent rejects LLM clients missing required methods.
    """
    config = AgentConfiguration(goal="Test invalid LLM client")

    # Test with incomplete LLM client (missing stream_text and close)
    incomplete_client = IncompleteLLMClient()

    agent = HybridAgent(
        agent_id="test_invalid_llm",
        name="Invalid LLM Test",
        llm_client=incomplete_client,
        tools={"valid_tool": ValidTool()},
        config=config,
    )

    # Error should occur during initialization when LLM client is validated
    with pytest.raises(Exception) as exc_info:
        await agent.initialize()

    # Verify error message mentions the missing method
    error_msg = str(exc_info.value)
    assert "stream_text" in error_msg or "method" in error_msg.lower()
    print(f"\nIncomplete LLM client error: {error_msg}")


@pytest.mark.asyncio
async def test_llm_agent_invalid_llm_client_no_methods():
    """
    Test 2.5.2: Test error handling for LLM client with no methods in LLMAgent.

    Verifies that LLMAgent rejects LLM clients with no methods.
    """
    config = AgentConfiguration(goal="Test invalid LLM client")

    # Test with LLM client that has no methods
    no_methods_client = NoMethodsLLMClient()

    agent = LLMAgent(
        agent_id="test_no_methods_llm",
        name="No Methods LLM Test",
        llm_client=no_methods_client,
        config=config,
    )

    # Error should occur during initialization when LLM client is validated
    with pytest.raises(Exception) as exc_info:
        await agent.initialize()

    # Verify error message mentions missing method
    error_msg = str(exc_info.value)
    assert "generate_text" in error_msg or "method" in error_msg.lower()
    print(f"\nNo methods LLM client error: {error_msg}")


# ==================== Test 2.5.3: Invalid Config Managers ====================


@pytest.mark.asyncio
async def test_agent_invalid_config_manager():
    """
    Test 2.5.3: Test error handling for invalid config manager.

    Verifies that agents handle config managers missing required methods.
    """
    config = AgentConfiguration(goal="Test invalid config manager")
    llm_client = MockLLMClient()

    # Test with incomplete config manager
    incomplete_config_mgr = IncompleteConfigManager()

    agent = HybridAgent(
        agent_id="test_invalid_config",
        name="Invalid Config Test",
        llm_client=llm_client,
        tools={"valid_tool": ValidTool()},
        config=config,
        config_manager=incomplete_config_mgr,
    )

    # Should work - config manager is optional and not validated at init
    await agent.initialize()
    assert agent is not None

    # Error would occur when trying to use missing methods
    # For now, we verify the agent was created
    print("\nIncomplete config manager accepted (runtime errors expected on use)")


@pytest.mark.asyncio
async def test_agent_config_manager_no_methods():
    """
    Test 2.5.3: Test error handling for config manager with no methods.

    Verifies that agents handle config managers with no methods.
    """
    config = AgentConfiguration(goal="Test config manager no methods")

    # Test with config manager that has no methods
    no_methods_config = NoMethodsConfigManager()

    agent = ToolAgent(
        agent_id="test_no_methods_config",
        name="No Methods Config Test",
        tools={"valid_tool": ValidTool()},
        config=config,
        config_manager=no_methods_config,
    )

    # Should work - config manager is optional
    await agent.initialize()
    assert agent is not None
    print("\nNo methods config manager accepted")


# ==================== Test 2.5.4: Invalid Checkpointers ====================


@pytest.mark.asyncio
async def test_agent_invalid_checkpointer():
    """
    Test 2.5.4: Test error handling for invalid checkpointer.

    Verifies that agents handle checkpointers missing required methods.
    """
    config = AgentConfiguration(goal="Test invalid checkpointer")
    llm_client = MockLLMClient()

    # Test with incomplete checkpointer
    incomplete_checkpointer = IncompleteCheckpointer()

    agent = HybridAgent(
        agent_id="test_invalid_checkpoint",
        name="Invalid Checkpoint Test",
        llm_client=llm_client,
        tools={"valid_tool": ValidTool()},
        config=config,
        checkpointer=incomplete_checkpointer,
    )

    # Should work - checkpointer is optional and not validated at init
    await agent.initialize()
    assert agent is not None
    print("\nIncomplete checkpointer accepted (runtime errors expected on use)")


@pytest.mark.asyncio
async def test_agent_checkpointer_no_methods():
    """
    Test 2.5.4: Test error handling for checkpointer with no methods.

    Verifies that agents handle checkpointers with no methods.
    """
    config = AgentConfiguration(goal="Test checkpointer no methods")

    # Test with checkpointer that has no methods
    no_methods_checkpointer = NoMethodsCheckpointer()

    agent = ToolAgent(
        agent_id="test_no_methods_checkpoint",
        name="No Methods Checkpoint Test",
        tools={"valid_tool": ValidTool()},
        config=config,
        checkpointer=no_methods_checkpointer,
    )

    # Should work - checkpointer is optional
    await agent.initialize()
    assert agent is not None
    print("\nNo methods checkpointer accepted")


# ==================== Test 2.5.5: Error Message Quality ====================


@pytest.mark.asyncio
async def test_error_messages_are_clear_and_helpful():
    """
    Test 2.5.5: Verify error messages are clear and helpful.

    Tests that error messages provide useful information about what went wrong
    and how to fix it.
    """
    config = AgentConfiguration(goal="Test error messages")

    # Test 1: Invalid tool instance error message
    invalid_tools = {"invalid": NotAToolClass()}
    agent1 = HybridAgent(
        agent_id="test_msg_1",
        name="Test",
        llm_client=MockLLMClient(),
        tools=invalid_tools,
        config=config,
    )

    try:
        await agent1.initialize()
        assert False, "Should have raised an error"
    except Exception as e:
        error_msg = str(e)
        # Error message should mention "tool" or "BaseTool"
        assert "tool" in error_msg.lower() or "basetool" in error_msg.lower()
        print(f"\n✓ Tool error message is clear: {error_msg}")

    # Test 2: Invalid LLM client error message
    agent2 = LLMAgent(
        agent_id="test_msg_2",
        name="Test",
        llm_client=NoMethodsLLMClient(),
        config=config,
    )

    try:
        await agent2.initialize()
        assert False, "Should have raised an error"
    except Exception as e:
        error_msg = str(e)
        # Error message should mention the missing method
        assert "generate_text" in error_msg or "method" in error_msg.lower()
        # Error message should be specific
        assert len(error_msg) > 10  # Not just a generic error
        print(f"\n✓ LLM client error message is clear: {error_msg}")

    # Test 3: Verify error types are appropriate
    agent3 = HybridAgent(
        agent_id="test_msg_3",
        name="Test",
        llm_client=IncompleteLLMClient(),
        tools={"valid": ValidTool()},
        config=config,
    )

    try:
        await agent3.initialize()
        assert False, "Should have raised an error"
    except Exception as e:
        # Should be a specific exception type, not just generic Exception
        assert type(e).__name__ != "Exception"
        error_msg = str(e)
        # Should mention what's missing
        assert "stream_text" in error_msg
        print(f"\n✓ Error type is specific: {type(e).__name__}")
        print(f"✓ Error message is helpful: {error_msg}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


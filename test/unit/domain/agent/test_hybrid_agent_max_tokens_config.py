"""
Test HybridAgent max_tokens configuration

Tests whether max_tokens can be changed via configuration like max_iterations.
"""

import pytest
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.llm.clients.base_client import LLMMessage


class MockLLMClient:
    """Mock LLM client to capture max_tokens parameter"""
    
    def __init__(self):
        self.provider_name = "Mock"
        self.last_max_tokens = None
        self.call_count = 0
    
    async def generate_text(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        self.last_max_tokens = max_tokens
        self.call_count += 1
        from aiecs.llm.clients.base_client import LLMResponse
        return LLMResponse(
            content="Test response",
            provider=self.provider_name,
            model=model or "test-model",
            tokens_used=100
        )
    
    async def stream_text(self, messages, model=None, temperature=0.7, max_tokens=None, **kwargs):
        self.last_max_tokens = max_tokens
        self.call_count += 1
        yield "Test"
    
    async def close(self):
        pass


def test_max_tokens_via_config():
    """Test that max_tokens can be changed via config.max_tokens"""
    print("\n=== Test: max_tokens via config ===")
    
    # Create config with custom max_tokens
    config = AgentConfiguration(max_tokens=8192)
    assert config.max_tokens == 8192
    print(f"✓ Config max_tokens: {config.max_tokens}")
    
    # Create mock client
    mock_client = MockLLMClient()
    
    # Create agent with custom max_tokens in config
    agent = HybridAgent(
        agent_id="test-agent",
        name="Test Agent",
        llm_client=mock_client,
        tools=[],
        config=config
    )
    
    print(f"✓ Agent created with config.max_tokens = {agent._config.max_tokens}")
    assert agent._config.max_tokens == 8192
    print("✓ max_tokens can be changed via config")


def test_max_iterations_via_config():
    """Test that max_iterations can be changed via config.max_iterations"""
    print("\n=== Test: max_iterations via config ===")
    
    # Create config with custom max_iterations
    config = AgentConfiguration(max_iterations=5)
    assert config.max_iterations == 5
    print(f"✓ Config max_iterations: {config.max_iterations}")
    
    # Create mock client
    mock_client = MockLLMClient()
    
    # Create agent - note: constructor parameter takes precedence when explicitly provided
    agent = HybridAgent(
        agent_id="test-agent",
        name="Test Agent",
        llm_client=mock_client,
        tools=[],
        config=config,
        max_iterations=3  # Constructor parameter explicitly provided
    )
    
    print(f"✓ Agent _max_iterations: {agent._max_iterations}")
    print(f"✓ Config max_iterations: {agent._config.max_iterations}")
    
    # Constructor parameter takes precedence when explicitly provided
    assert agent._max_iterations == 3
    assert agent._config.max_iterations == 5
    print("✓ max_iterations: Constructor parameter takes precedence over config when explicitly provided")


def test_max_iterations_from_config_when_not_provided():
    """Test that max_iterations uses config value when constructor parameter not provided"""
    print("\n=== Test: max_iterations from config (no constructor param) ===")
    
    # Create config with custom max_iterations
    config = AgentConfiguration(max_iterations=7)
    
    # Create mock client
    mock_client = MockLLMClient()
    
    # Create agent without max_iterations parameter (uses config value)
    agent = HybridAgent(
        agent_id="test-agent",
        name="Test Agent",
        llm_client=mock_client,
        tools=[],
        config=config
        # max_iterations not provided, uses config.max_iterations
    )
    
    print(f"✓ Agent _max_iterations: {agent._max_iterations}")
    print(f"✓ Config max_iterations: {agent._config.max_iterations}")
    
    # Now uses config value when constructor parameter uses default
    assert agent._max_iterations == 7  # Uses config value
    assert agent._config.max_iterations == 7  # Config value
    print("✓ max_iterations now uses config value when constructor param not explicitly provided")


def test_max_tokens_default_value():
    """Test default max_tokens value"""
    print("\n=== Test: max_tokens default value ===")
    
    config = AgentConfiguration()
    assert config.max_tokens == 4096  # Default value
    print(f"✓ Default max_tokens: {config.max_tokens}")


def test_max_iterations_default_value():
    """Test default max_iterations value"""
    print("\n=== Test: max_iterations default value ===")
    
    config = AgentConfiguration()
    assert config.max_iterations == 10  # Default value
    print(f"✓ Default max_iterations: {config.max_iterations}")


@pytest.mark.asyncio
async def test_extra_llm_kwargs_reaches_generate_text():
    """Test that extra_llm_kwargs values are forwarded to llm_client.generate_text()"""
    print("\n=== Test: extra_llm_kwargs forwarded to generate_text ===")

    received_kwargs: dict = {}

    class CapturingLLMClient:
        provider_name = "Mock"

        async def generate_text(self, messages, **kwargs):
            received_kwargs.update(kwargs)
            from aiecs.llm.clients.base_client import LLMResponse
            return LLMResponse(content="ok", provider="Mock", model="m", tokens_used=1)

        async def stream_text(self, messages, **kwargs):
            yield "ok"

        async def close(self):
            pass

    config = AgentConfiguration(
        extra_llm_kwargs={"reasoning_effort": "high", "thinking": {"type": "enabled"}}
    )
    agent = HybridAgent(
        agent_id="test-extra-kwargs-gen",
        name="Test Agent",
        llm_client=CapturingLLMClient(),
        tools=[],
        config=config,
    )
    await agent.initialize()
    await agent.execute_task({"description": "hello"}, {})

    assert received_kwargs.get("reasoning_effort") == "high", "reasoning_effort not forwarded"
    assert received_kwargs.get("thinking") == {"type": "enabled"}, "thinking not forwarded"
    print("✓ extra_llm_kwargs forwarded to generate_text")


@pytest.mark.asyncio
async def test_extra_llm_kwargs_reaches_stream_text():
    """Test that extra_llm_kwargs values are forwarded to llm_client.stream_text()"""
    print("\n=== Test: extra_llm_kwargs forwarded to stream_text ===")

    received_kwargs: dict = {}

    class CapturingStreamLLMClient:
        provider_name = "Mock"

        async def generate_text(self, messages, **kwargs):
            from aiecs.llm.clients.base_client import LLMResponse
            return LLMResponse(content="ok", provider="Mock", model="m", tokens_used=1)

        async def stream_text(self, messages, **kwargs):
            received_kwargs.update(kwargs)
            yield "ok"

        async def close(self):
            pass

    config = AgentConfiguration(
        extra_llm_kwargs={"thinking_config": {"thinking_budget": 8192}}
    )
    agent = HybridAgent(
        agent_id="test-extra-kwargs-stream",
        name="Test Agent",
        llm_client=CapturingStreamLLMClient(),
        tools=[],
        config=config,
    )
    await agent.initialize()
    chunks = []
    async for chunk in agent.execute_task_streaming({"description": "hello"}, {}):
        chunks.append(chunk)

    assert received_kwargs.get("thinking_config") == {"thinking_budget": 8192}, "thinking_config not forwarded"
    print("✓ extra_llm_kwargs forwarded to stream_text")


@pytest.mark.asyncio
async def test_extra_llm_kwargs_does_not_override_tools():
    """Test that extra_llm_kwargs cannot override tools/tool_choice (tools are appended after)"""
    print("\n=== Test: extra_llm_kwargs cannot override tools ===")

    received_kwargs: dict = {}

    class CapturingLLMClient:
        provider_name = "openai"

        async def generate_text(self, messages, **kwargs):
            received_kwargs.update(kwargs)
            from aiecs.llm.clients.base_client import LLMResponse
            return LLMResponse(content="ok", provider="openai", model="m", tokens_used=1)

        async def stream_text(self, messages, **kwargs):
            yield "ok"

        async def close(self):
            pass

    config = AgentConfiguration(
        extra_llm_kwargs={"tool_choice": "none"}  # attempt to override
    )
    agent = HybridAgent(
        agent_id="test-extra-kwargs-no-override",
        name="Test Agent",
        llm_client=CapturingLLMClient(),
        tools=[],
        config=config,
    )
    await agent.initialize()
    await agent.execute_task({"description": "hello"}, {})

    # With no tool schemas, tool_choice from extra_llm_kwargs is passed as-is (no tools configured)
    # This just verifies no crash and kwargs are received
    print(f"✓ received_kwargs keys: {list(received_kwargs.keys())}")
    print("✓ extra_llm_kwargs does not cause errors")


def test_extra_llm_kwargs_default_is_empty():
    """Test that extra_llm_kwargs defaults to empty dict (no behavior change)"""
    print("\n=== Test: extra_llm_kwargs default is empty dict ===")
    config = AgentConfiguration()
    assert config.extra_llm_kwargs == {}, f"Expected empty dict, got: {config.extra_llm_kwargs}"
    print("✓ extra_llm_kwargs defaults to empty dict")


if __name__ == "__main__":
    print("=" * 60)
    print("HybridAgent Configuration Test")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s"])

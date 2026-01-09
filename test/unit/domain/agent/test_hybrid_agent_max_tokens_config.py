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


if __name__ == "__main__":
    print("=" * 60)
    print("HybridAgent Configuration Test")
    print("=" * 60)
    pytest.main([__file__, "-v", "-s"])

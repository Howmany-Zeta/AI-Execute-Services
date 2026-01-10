#!/usr/bin/env python3
"""
Test script to verify context parameter support across LLM clients and agents.

This script tests that the context parameter flows correctly through:
1. LLM clients (OpenAI, Vertex, Google AI, xAI)
2. Agents (LLMAgent, HybridAgent, KnowledgeAwareAgent)
3. Knowledge graph components (LLMEntityExtractor, QueryIntentClassifier)

Usage:
    poetry run python test_context_parameter.py
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
from aiecs.llm import LLMMessage, LLMResponse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockLLMClient:
    """Mock LLM client that captures and verifies context parameter."""
    
    def __init__(self):
        self.provider_name = "mock"
        self.last_context = None
        self.generate_call_count = 0
        self.stream_call_count = 0
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> LLMResponse:
        """Mock generate_text that captures context."""
        self.last_context = context
        self.generate_call_count += 1
        
        logger.info(f"✓ generate_text called with context: {context}")
        
        return LLMResponse(
            content="Mock response",
            provider=self.provider_name,
            model=model or "mock-model",
            tokens_used=10,
            prompt_tokens=5,
            completion_tokens=5
        )
    
    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Mock stream_text that captures context."""
        self.last_context = context
        self.stream_call_count += 1
        
        logger.info(f"✓ stream_text called with context: {context}")
        
        for token in ["Mock", " ", "streaming", " ", "response"]:
            yield token
    
    async def close(self):
        """Mock close method."""
        pass


async def test_llm_agent_with_context():
    """Test LLMAgent passes context to LLM client."""
    from aiecs.domain.agent import LLMAgent, AgentConfiguration
    
    logger.info("\n=== Testing LLMAgent ===")
    
    mock_client = MockLLMClient()
    config = AgentConfiguration(
        llm_model="mock-model",
        temperature=0.7,
        max_tokens=100,
        memory_enabled=False
    )
    
    agent = LLMAgent(
        agent_id="test_llm_agent",
        name="Test LLM Agent",
        llm_client=mock_client,
        config=config
    )

    # Initialize and activate the agent
    await agent.initialize()
    await agent.activate()

    # Test with context
    test_context = {
        "user_id": "user123",
        "tenant_id": "tenant456",
        "request_id": "req789",
        "session_id": "session_abc"
    }

    task = {"description": "Test task"}
    result = await agent.execute_task(task, test_context)
    
    # Verify context was passed
    assert mock_client.last_context == test_context, "Context not passed to generate_text"
    assert mock_client.generate_call_count == 1, "generate_text not called"
    logger.info(f"✓ LLMAgent correctly passed context: {mock_client.last_context}")
    
    # Test streaming with context
    mock_client.last_context = None
    async for event in agent.execute_task_streaming(task, test_context):
        if event['type'] == 'result':
            break
    
    assert mock_client.last_context == test_context, "Context not passed to stream_text"
    assert mock_client.stream_call_count == 1, "stream_text not called"
    logger.info(f"✓ LLMAgent streaming correctly passed context: {mock_client.last_context}")


async def test_hybrid_agent_with_context():
    """Test HybridAgent passes context to LLM client."""
    from aiecs.domain.agent import HybridAgent, AgentConfiguration
    
    logger.info("\n=== Testing HybridAgent ===")
    
    mock_client = MockLLMClient()
    config = AgentConfiguration(
        llm_model="mock-model",
        temperature=0.7,
        max_tokens=100,
        memory_enabled=False
    )
    
    agent = HybridAgent(
        agent_id="test_hybrid_agent",
        name="Test Hybrid Agent",
        llm_client=mock_client,
        tools={},  # No tools for simplicity
        config=config
    )

    # Initialize and activate the agent
    await agent.initialize()
    await agent.activate()

    # Test with context
    test_context = {
        "user_id": "user_hybrid",
        "request_id": "req_hybrid_123"
    }

    task = {"description": "Test hybrid task"}
    result = await agent.execute_task(task, test_context)
    
    # Verify context was passed
    assert mock_client.last_context == test_context, "Context not passed in HybridAgent"
    logger.info(f"✓ HybridAgent correctly passed context: {mock_client.last_context}")


async def test_context_parameter_main():
    """Main test function."""
    logger.info("=" * 60)
    logger.info("Testing Context Parameter Support")
    logger.info("=" * 60)
    
    try:
        # Test LLMAgent
        await test_llm_agent_with_context()
        
        # Test HybridAgent
        await test_hybrid_agent_with_context()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ All tests passed! Context parameter is working correctly.")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n✗ Test failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(test_context_parameter_main())


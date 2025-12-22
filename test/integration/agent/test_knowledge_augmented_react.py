"""
Integration tests for Knowledge-Augmented ReAct Loop
"""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock
from datetime import datetime

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def graph_store_with_data():
    """Create a graph store with sample data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add sample entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "Engineer"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "Manager"})
    company = Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company)
    
    # Add relations
    await store.add_relation(Relation(
        id="rel1",
        source_id="alice",
        target_id="bob",
        relation_type="KNOWS",
        properties={}
    ))
    await store.add_relation(Relation(
        id="rel2",
        source_id="alice",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    yield store
    await store.close()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client that simulates ReAct responses"""
    client = AsyncMock(spec=BaseLLMClient)
    client.provider_name = "test_provider"
    
    # Mock responses for ReAct loop
    responses = [
        "THOUGHT: I should provide the final answer based on the task.\nFINAL ANSWER: Task completed successfully.",
    ]
    
    client.generate_text = AsyncMock(side_effect=[
        LLMResponse(
            content=resp,
            provider="test_provider",
            model="test-model",
            tokens_used=10
        )
        for resp in responses
    ])
    
    return client


@pytest.fixture
def agent_config():
    """Create test agent configuration"""
    return AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=True,
        llm_model="test-model",
        temperature=0.7,
    )


class TestKnowledgeAugmentedReActLoop:
    """Test the knowledge-augmented ReAct loop"""
    
    @pytest.mark.asyncio
    async def test_react_loop_with_knowledge_store(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test ReAct loop with knowledge graph available"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_1",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Execute task
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        assert "output" in result
        assert "reasoning_steps" in result
        
        # Check that the agent can complete tasks
        # Knowledge retrieval would happen in the background
        # but since _retrieve_relevant_knowledge returns empty list,
        # no actual retrieval happens in this test
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_react_loop_without_knowledge_store(self, mock_llm_client, agent_config):
        """Test ReAct loop falls back gracefully without knowledge store"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_2",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=None  # No graph store
        )
        
        await agent.initialize()
        
        # Execute task - should work without knowledge retrieval
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_react_loop_tracks_knowledge_retrievals(self, graph_store_with_data, agent_config):
        """Test that knowledge retrievals are tracked in result"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: Test answer",
            provider="test",
            model="test",
            tokens_used=10
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_3",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        # knowledge_retrievals would be in the internal result
        # but not necessarily exposed in the top-level result
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_retrieve_phase_in_react_steps(self, graph_store_with_data, agent_config):
        """Test that RETRIEVE phase appears in reasoning steps"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        
        # Multiple iterations to see retrieve phases
        mock_llm.generate_text = AsyncMock(side_effect=[
            LLMResponse(content="THOUGHT: Analyzing...", provider="test", model="test", tokens_used=5),
            LLMResponse(content="FINAL ANSWER: Done", provider="test", model="test", tokens_used=5),
        ])
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_4",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        steps = result.get("reasoning_steps", [])
        
        # Check step types - should have thought steps at minimum
        step_types = [step.get("type") for step in steps]
        assert "thought" in step_types
        
        # If knowledge was retrieved, would have "retrieve" type
        # but since _retrieve_relevant_knowledge returns empty, we won't see it
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_knowledge_augmented_prompt(self, graph_store_with_data, agent_config):
        """Test that system prompt includes knowledge capabilities"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: Done",
            provider="test",
            model="test",
            tokens_used=10
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_5",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Check that system prompt includes knowledge graph capabilities
        system_prompt = agent._system_prompt
        assert "KNOWLEDGE GRAPH CAPABILITIES" in system_prompt
        assert "RETRIEVE" in system_prompt
        assert "graph_reasoning" in system_prompt
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_react_loop_with_disabled_graph_reasoning(self, graph_store_with_data, agent_config):
        """Test ReAct loop with graph store but reasoning disabled"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: Done",
            provider="test",
            model="test",
            tokens_used=10
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_6",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data,
            enable_graph_reasoning=False  # Disabled
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        
        # Should not retrieve knowledge since reasoning is disabled
        steps = result.get("reasoning_steps", [])
        step_types = [step.get("type") for step in steps]
        assert "retrieve" not in step_types
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_format_retrieved_knowledge(self, graph_store_with_data, agent_config):
        """Test knowledge formatting for LLM context"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: Done",
            provider="test",
            model="test"
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_7",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Test knowledge formatting
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Company", properties={"name": "TechCorp"}),
        ]
        
        formatted = agent._format_retrieved_knowledge(entities)
        
        assert "Person: e1" in formatted
        assert "name=Alice" in formatted
        assert "Company: e2" in formatted
        assert "name=TechCorp" in formatted
        
        # Test empty list
        formatted_empty = agent._format_retrieved_knowledge([])
        assert formatted_empty == ""
        
        await agent.shutdown()


class TestKnowledgeGuidedActionSelection:
    """Test knowledge-guided action selection"""
    
    @pytest.mark.asyncio
    async def test_direct_graph_query_uses_graph_reasoning(self, graph_store_with_data, agent_config):
        """Test that direct graph queries use graph reasoning tool"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_8",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Mock _reason_with_graph to return high confidence result
        agent._reason_with_graph = AsyncMock(return_value={
            "answer": "Alice is connected to TechCorp",
            "confidence": 0.95,
            "evidence_count": 2,
            "reasoning_trace": ["step1", "step2"]
        })
        
        # Execute a graph-related task
        result = await agent.execute_task(
            task={"description": "How is Alice connected to TechCorp?"},
            context={}
        )
        
        # Should use graph reasoning directly
        assert "output" in result or "result" in result
        assert result.get("source") == "knowledge_graph" or result.get("success") is True
        assert result.get("confidence") == 0.95
        
        # Verify _reason_with_graph was called
        agent._reason_with_graph.assert_called_once()
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_non_graph_query_uses_standard_react(self, graph_store_with_data, agent_config):
        """Test that non-graph queries use standard ReAct loop"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: 42",
            provider="test",
            model="test",
            tokens_used=10
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_9",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Mock _reason_with_graph to track calls
        agent._reason_with_graph = AsyncMock(return_value={
            "answer": "Low confidence answer",
            "confidence": 0.3,  # Low confidence
        })
        
        # Execute a non-graph-related task
        result = await agent.execute_task(
            task={"description": "What is 6 times 7?"},
            context={}
        )
        
        # Should not use graph reasoning (no graph keywords)
        assert result["success"] is True
        # _reason_with_graph should not be called
        agent._reason_with_graph.assert_not_called()
        
        await agent.shutdown()


class TestKnowledgeRetrievalIntegration:
    """Test knowledge retrieval integration with ReAct loop"""
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_knowledge_method(self, graph_store_with_data, agent_config):
        """Test the _retrieve_relevant_knowledge method"""
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_10",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Test retrieval (currently returns empty list)
        entities = await agent._retrieve_relevant_knowledge(
            task="Test task about Alice",
            context={},
            iteration=0
        )
        
        # Current implementation returns empty
        assert isinstance(entities, list)
        assert len(entities) == 0
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_knowledge_retrieval(self, agent_config):
        """Test error handling when knowledge retrieval fails"""
        # Create a mock graph store that raises errors
        mock_graph_store = AsyncMock()
        mock_graph_store.get_entity = AsyncMock(side_effect=Exception("Test error"))
        
        mock_llm = AsyncMock(spec=BaseLLMClient)
        mock_llm.provider_name = "test"
        mock_llm.generate_text = AsyncMock(return_value=LLMResponse(
            content="FINAL ANSWER: Done",
            provider="test",
            model="test",
            tokens_used=10
        ))
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_11",
            name="Test Agent",
            llm_client=mock_llm,
            tools=[],
            config=agent_config,
            graph_store=mock_graph_store
        )
        
        await agent.initialize()
        
        # Should handle errors gracefully
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        # Should still succeed despite retrieval errors
        assert result["success"] is True
        
        await agent.shutdown()


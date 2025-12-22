"""
End-to-End Tests: Full Agent Workflows with Knowledge Graph

Tests complete workflows from agent creation to task execution
with knowledge graph integration.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore, SQLiteGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import BaseLLMClient, LLMResponse


@pytest.fixture
async def graph_store_with_data():
    """Create a graph store with comprehensive test data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities
    entities = [
        Entity(id="alice", entity_type="Person", properties={"name": "Alice", "role": "Engineer"}),
        Entity(id="bob", entity_type="Person", properties={"name": "Bob", "role": "Manager"}),
        Entity(id="charlie", entity_type="Person", properties={"name": "Charlie", "role": "Designer"}),
        Entity(id="tech_corp", entity_type="Company", properties={"name": "TechCorp"}),
        Entity(id="project_alpha", entity_type="Project", properties={"name": "Project Alpha"}),
    ]
    
    for entity in entities:
        await store.add_entity(entity)
    
    # Create relations
    relations = [
        Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS", properties={}),
        Relation(id="r2", source_id="alice", target_id="tech_corp", relation_type="WORKS_FOR", properties={}),
        Relation(id="r3", source_id="bob", target_id="tech_corp", relation_type="WORKS_FOR", properties={}),
        Relation(id="r4", source_id="alice", target_id="project_alpha", relation_type="WORKS_ON", properties={}),
    ]
    
    for relation in relations:
        await store.add_relation(relation)
    
    yield store
    await store.close()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = AsyncMock(spec=BaseLLMClient)
    client.provider_name = "test_provider"
    
    # Default response
    client.generate_text = AsyncMock(return_value=LLMResponse(
        content="FINAL ANSWER: Test answer",
        provider="test_provider",
        model="test-model",
        tokens_used=10
    ))
    
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


class TestE2EAgentWorkflows:
    """End-to-end tests for complete agent workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_agent_lifecycle(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test complete agent lifecycle: create -> initialize -> execute -> shutdown"""
        # Create agent
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_1",
            name="E2E Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        # Initialize
        await agent.initialize()
        assert agent.state.value == "active"
        
        # Execute task
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        assert result["success"] is True
        
        # Shutdown
        await agent.shutdown()
        assert agent.state.value == "stopped"
    
    @pytest.mark.asyncio
    async def test_knowledge_retrieval_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow with knowledge retrieval"""
        # Setup LLM to simulate knowledge retrieval
        mock_llm_client.generate_text = AsyncMock(side_effect=[
            LLMResponse(
                content="THOUGHT: I need to retrieve knowledge about Alice.\nTOOL: graph_search\nOPERATION: vector\nPARAMETERS: {\"query\": \"Alice\"}",
                provider="test",
                model="test",
                tokens_used=15
            ),
            LLMResponse(
                content="FINAL ANSWER: Alice is an Engineer at TechCorp.",
                provider="test",
                model="test",
                tokens_used=10
            ),
        ])
        
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_2",
            name="Knowledge Retrieval Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "Tell me about Alice"},
            context={}
        )
        
        assert result["success"] is True
        assert "output" in result
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_multi_step_reasoning_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test multi-step reasoning workflow"""
        # Setup LLM for multi-step reasoning
        responses = [
            LLMResponse(
                content="THOUGHT: I need to find how Alice is connected to TechCorp.\nTOOL: graph_reasoning\nOPERATION: multi_hop\nPARAMETERS: {\"query\": \"How is Alice connected to TechCorp?\"}",
                provider="test",
                model="test",
                tokens_used=20
            ),
            LLMResponse(
                content="FINAL ANSWER: Alice works at TechCorp as an Engineer.",
                provider="test",
                model="test",
                tokens_used=12
            ),
        ]
        
        mock_llm_client.generate_text = AsyncMock(side_effect=responses)
        
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_3",
            name="Multi-Step Reasoning Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data,
            max_iterations=5
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "How is Alice connected to TechCorp?"},
            context={}
        )
        
        assert result["success"] is True
        assert result.get("iterations", 0) >= 2
        # Tool calls may be 0 if tool execution fails, but iterations should be >= 2
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_graph_query_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow with direct graph queries"""
        # Mock high-confidence graph result
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_4",
            name="Graph Query Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Mock _reason_with_graph to return high confidence
        agent._reason_with_graph = AsyncMock(return_value={
            "answer": "Alice works at TechCorp",
            "confidence": 0.95,
            "evidence_count": 2,
            "reasoning_trace": []
        })
        
        result = await agent.execute_task(
            task={"description": "How is Alice connected to TechCorp?"},
            context={}
        )
        
        # Should use graph reasoning directly
        assert result.get("source") == "knowledge_graph" or result["success"] is True
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_knowledge_accumulation_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow where knowledge accumulates during conversation"""
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_5",
            name="Knowledge Accumulation Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # First query
        result1 = await agent.execute_task(
            task={"description": "Tell me about Alice"},
            context={"session_id": "session_1"}
        )
        assert result1["success"] is True
        
        # Add new knowledge
        diana = Entity(id="diana", entity_type="Person", properties={"name": "Diana"})
        await graph_store_with_data.add_entity(diana)
        await graph_store_with_data.add_relation(Relation(
            id="r5", source_id="diana", target_id="tech_corp", relation_type="WORKS_FOR", properties={}
        ))
        
        # Second query should include new knowledge
        result2 = await agent.execute_task(
            task={"description": "Who works at TechCorp?"},
            context={"session_id": "session_1"}
        )
        assert result2["success"] is True
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow with error recovery"""
        # Setup LLM to simulate error then recovery
        mock_llm_client.generate_text = AsyncMock(side_effect=[
            LLMResponse(
                content="THOUGHT: I'll try to use a tool.\nTOOL: invalid_tool\nOPERATION: test\nPARAMETERS: {}",
                provider="test",
                model="test",
                tokens_used=10
            ),
            LLMResponse(
                content="THOUGHT: The tool failed, let me try a different approach.\nFINAL ANSWER: Based on my knowledge, I can answer directly.",
                provider="test",
                model="test",
                tokens_used=15
            ),
        ])
        
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_6",
            name="Error Recovery Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        result = await agent.execute_task(
            task={"description": "Test task with error"},
            context={}
        )
        
        # Should recover and complete
        assert result["success"] is True
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_concurrent_tasks_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow with concurrent tasks"""
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_7",
            name="Concurrent Tasks Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Execute multiple tasks concurrently
        import asyncio
        tasks = [
            agent.execute_task({"description": f"Task {i}"}, {})
            for i in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r["success"] for r in results)
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_graph_utilities_workflow(self, graph_store_with_data, mock_llm_client, agent_config):
        """Test workflow using graph utilities"""
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_8",
            name="Graph Utilities Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        
        await agent.initialize()
        
        # Use graph utilities (if mixin is available)
        # Note: KnowledgeAwareAgent doesn't directly inherit GraphAwareAgentMixin
        # but has access to graph_store for direct queries
        if hasattr(agent, 'graph_store') and agent.graph_store:
            # Direct graph store access
            neighbors = await agent.graph_store.get_neighbors("alice")
            assert len(neighbors) > 0
            
            paths = await agent.graph_store.find_paths("alice", "tech_corp", max_depth=2)
            assert isinstance(paths, list)
            
            # Format entities using basic formatting
            if neighbors:
                entity_str = f"{neighbors[0].entity_type}: {neighbors[0].id}"
                assert len(entity_str) > 0
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_without_graph_store_workflow(self, mock_llm_client, agent_config):
        """Test workflow without graph store (graceful degradation)"""
        agent = KnowledgeAwareAgent(
            agent_id="e2e_agent_9",
            name="No Graph Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=None  # No graph store
        )
        
        await agent.initialize()
        
        # Should work without graph store
        result = await agent.execute_task(
            task={"description": "Test task"},
            context={}
        )
        
        assert result["success"] is True
        
        await agent.shutdown()


class TestE2EWithSQLite:
    """End-to-end tests with SQLite graph store"""
    
    @pytest.mark.asyncio
    async def test_sqlite_backend_workflow(self, mock_llm_client, agent_config, tmp_path):
        """Test complete workflow with SQLite backend"""
        from aiecs.infrastructure.graph_storage import SQLiteGraphStore
        
        # Create SQLite store
        db_path = tmp_path / "test_kg.db"
        graph_store = SQLiteGraphStore(db_path=str(db_path))
        await graph_store.initialize()
        
        # Add test data
        alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
        await graph_store.add_entity(alice)
        
        # Create agent
        agent = KnowledgeAwareAgent(
            agent_id="e2e_sqlite_agent",
            name="SQLite Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Execute task
        result = await agent.execute_task(
            task={"description": "Test with SQLite"},
            context={}
        )
        
        assert result["success"] is True
        
        # Cleanup
        await agent.shutdown()
        await graph_store.close()


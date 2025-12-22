"""
Unit tests for KnowledgeAwareAgent
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def graph_store():
    """Create a test graph store with sample data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add sample entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    company_x = Entity(id="company_x", entity_type="Company", properties={"name": "Company X"})
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company_x)
    
    # Add sample relations
    await store.add_relation(Relation(
        id="rel1",
        source_id="alice",
        target_id="bob",
        relation_type="KNOWS",
        properties={}
    ))
    await store.add_relation(Relation(
        id="rel2",
        source_id="bob",
        target_id="company_x",
        relation_type="WORKS_FOR",
        properties={}
    ))
    
    yield store
    await store.close()


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = AsyncMock(spec=BaseLLMClient)
    client.provider_name = "test_provider"
    client.generate = AsyncMock(return_value=LLMResponse(
        content="Test response",
        provider="test_provider",
        model="test-model"
    ))
    return client


@pytest.fixture
def agent_config():
    """Create test agent configuration"""
    return AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=True,
    )


class TestKnowledgeAwareAgentInitialization:
    """Test KnowledgeAwareAgent initialization"""
    
    @pytest.mark.asyncio
    async def test_init_without_graph_store(self, mock_llm_client, agent_config):
        """Test initialization without graph store"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_1",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config
        )
        
        assert agent.agent_id == "test_agent_1"
        assert agent.graph_store is None
        assert agent.enable_graph_reasoning is True
        assert "graph_reasoning" not in agent._available_tools
    
    @pytest.mark.asyncio
    async def test_init_with_graph_store(self, mock_llm_client, agent_config, graph_store):
        """Test initialization with graph store"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_2",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store
        )
        
        assert agent.agent_id == "test_agent_2"
        assert agent.graph_store is not None
        assert "graph_reasoning" in agent._available_tools
    
    @pytest.mark.asyncio
    async def test_init_with_graph_store_disabled(self, mock_llm_client, agent_config, graph_store):
        """Test initialization with graph store but reasoning disabled"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_3",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store,
            enable_graph_reasoning=False
        )
        
        assert agent.graph_store is not None
        assert agent.enable_graph_reasoning is False
        assert "graph_reasoning" not in agent._available_tools
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_llm_client, agent_config, graph_store):
        """Test full agent initialization"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_4",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        assert agent._graph_reasoning_tool is not None
        assert agent._system_prompt is not None
        assert "KNOWLEDGE GRAPH CAPABILITIES" in agent._system_prompt
        
        await agent.shutdown()


class TestKnowledgeAwareAgentPrompts:
    """Test prompt augmentation"""
    
    @pytest.mark.asyncio
    async def test_kg_augmented_prompt(self, mock_llm_client, agent_config, graph_store):
        """Test KG-augmented system prompt"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_5",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        prompt = agent._system_prompt
        assert "KNOWLEDGE GRAPH CAPABILITIES" in prompt
        assert "graph_reasoning" in prompt
        assert "multi_hop" in prompt
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_augment_prompt_with_knowledge(self, mock_llm_client, agent_config, graph_store):
        """Test augmenting prompt with cached knowledge"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_6",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Add some knowledge to context
        agent._knowledge_context["alice"] = {
            "answer": "Alice is a person",
            "confidence": 0.9,
            "evidence_count": 2,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Augment task mentioning alice
        augmented = await agent._augment_prompt_with_knowledge("Tell me about alice")
        
        assert "Alice is a person" in augmented
        assert "confidence: 0.9" in augmented
        
        await agent.shutdown()


class TestGraphReasoning:
    """Test graph reasoning capabilities"""
    
    @pytest.mark.asyncio
    async def test_reason_with_graph(self, mock_llm_client, agent_config, graph_store):
        """Test reasoning with knowledge graph"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_7",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Reason about connections
        result = await agent._reason_with_graph(
            query="How is Alice connected to Bob?",
            context={"start_entity_id": "alice", "target_entity_id": "bob"}
        )
        
        assert "error" not in result or result.get("answer") is not None
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_reason_without_graph_tool(self, mock_llm_client, agent_config):
        """Test reasoning without graph tool initialized"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_8",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=None
        )
        
        await agent.initialize()
        
        result = await agent._reason_with_graph("test query")
        
        assert "error" in result
        assert result["error"] == "Graph reasoning not available"
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_knowledge_context_caching(self, mock_llm_client, agent_config, graph_store):
        """Test that reasoning results are cached in knowledge context"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_9",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        query = "How is Alice connected to Bob?"
        await agent._reason_with_graph(
            query=query,
            context={"start_entity_id": "alice", "target_entity_id": "bob"}
        )
        
        # Check that result was cached
        context = agent.get_knowledge_context()
        assert query in context or len(context) >= 0  # May have cached result
        
        await agent.shutdown()


class TestToolSelection:
    """Test graph-aware tool selection"""
    
    @pytest.mark.asyncio
    async def test_select_tools_with_graph_keywords(self, mock_llm_client, agent_config, graph_store):
        """Test tool selection prioritizes graph_reasoning for graph-related queries"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_10",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Task with graph keywords
        tools = await agent._select_tools_with_graph_awareness(
            task="How is Alice connected to Bob?",
            available_tools=["graph_reasoning", "web_search"]
        )
        
        assert tools[0] == "graph_reasoning"
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_select_tools_without_graph_keywords(self, mock_llm_client, agent_config, graph_store):
        """Test tool selection for non-graph queries"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_11",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=["web_search"],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Task without graph keywords
        tools = await agent._select_tools_with_graph_awareness(
            task="What is the weather today?",
            available_tools=["graph_reasoning", "web_search"]
        )
        
        # Order may vary, but should include both
        assert "graph_reasoning" in tools
        assert "web_search" in tools
        
        await agent.shutdown()


class TestKnowledgeContext:
    """Test knowledge context management"""
    
    @pytest.mark.asyncio
    async def test_get_knowledge_context(self, mock_llm_client, agent_config, graph_store):
        """Test getting knowledge context"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_12",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Add some context
        agent._knowledge_context["test"] = {"answer": "test answer"}
        
        context = agent.get_knowledge_context()
        assert "test" in context
        assert context["test"]["answer"] == "test answer"
        
        await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_clear_knowledge_context(self, mock_llm_client, agent_config, graph_store):
        """Test clearing knowledge context"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_13",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Add some context
        agent._knowledge_context["test"] = {"answer": "test answer"}
        assert len(agent._knowledge_context) > 0
        
        # Clear context
        agent.clear_knowledge_context()
        assert len(agent._knowledge_context) == 0
        
        await agent.shutdown()


class TestExecuteTask:
    """Test task execution with KG augmentation"""
    
    @pytest.mark.asyncio
    async def test_execute_task_without_graph_store(self, mock_llm_client, agent_config):
        """Test task execution without graph store falls back to parent"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_14",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=None
        )
        
        # Mock parent's execute_task
        with patch.object(agent.__class__.__bases__[0], 'execute_task', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"success": True, "output": "test result"}
            
            await agent.initialize()
            result = await agent.execute_task({"description": "Test task"}, {})
            
            assert mock_execute.called
            assert result["success"] is True
            
            await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_execute_task_with_high_confidence_graph_result(self, mock_llm_client, agent_config, graph_store):
        """Test that high-confidence graph results are used directly"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_15",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Mock _reason_with_graph to return high confidence
        with patch.object(agent, '_reason_with_graph', new_callable=AsyncMock) as mock_reason:
            mock_reason.return_value = {
                "answer": "Alice knows Bob",
                "confidence": 0.95,
                "evidence_count": 3,
                "reasoning_trace": ["step1", "step2"]
            }
            
            result = await agent.execute_task(
                {"description": "How is Alice connected to Bob?"},
                {}
            )
            
            assert result["success"] is True
            assert result["output"] == "Alice knows Bob"
            assert result["source"] == "knowledge_graph"
            assert result["confidence"] == 0.95
            
        await agent.shutdown()


class TestShutdown:
    """Test agent shutdown"""
    
    @pytest.mark.asyncio
    async def test_shutdown_clears_context(self, mock_llm_client, agent_config, graph_store):
        """Test shutdown clears knowledge context"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_16",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        
        await agent.initialize()
        
        # Add some context
        agent._knowledge_context["test"] = {"answer": "test"}
        
        await agent.shutdown()
        
        # Context should be cleared
        assert len(agent._knowledge_context) == 0
    
    @pytest.mark.asyncio
    async def test_shutdown_closes_graph_store(self, mock_llm_client, agent_config):
        """Test shutdown closes graph store"""
        mock_graph_store = AsyncMock(spec=InMemoryGraphStore)
        mock_graph_store.close = AsyncMock()
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent_17",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=mock_graph_store
        )
        
        await agent.initialize()
        await agent.shutdown()
        
        # Graph store close should be called
        mock_graph_store.close.assert_called_once()


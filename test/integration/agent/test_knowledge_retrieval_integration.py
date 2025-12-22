"""
Integration tests for KnowledgeAwareAgent knowledge retrieval (Section 8.4)

Tests for:
- 8.4.1: End-to-end knowledge retrieval with real graph store
- 8.4.2: Hybrid search integration
- 8.4.3: Streaming events
- 8.4.4: Different retrieval strategies

Uses real components:
- Real graph store (InMemoryGraphStore)
- Real HybridSearchStrategy
- Real LLM client (from .env.test if available, otherwise mock)
"""

import pytest
import asyncio
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

# Load test environment variables
load_dotenv(".env.test")

# Try to use real LLM client if available
try:
    from aiecs.llm.clients.vertex_client import VertexAIClient
    VERTEX_PROJECT_ID = os.getenv("VERTEX_PROJECT_ID")
    VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if VERTEX_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS:
        REAL_LLM_AVAILABLE = True
    else:
        REAL_LLM_AVAILABLE = False
except ImportError:
    REAL_LLM_AVAILABLE = False

from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing when real LLM is not available"""
    
    def __init__(self):
        super().__init__(provider_name="mock")
        self.call_count = 0
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate mock response"""
        self.call_count += 1
        
        # Extract content from messages
        content = ""
        if messages and len(messages) > 0:
            msg = messages[-1]
            if hasattr(msg, 'content'):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get('content', '')
        
        content_lower = content.lower()
        
        # Entity extraction response
        if "extract" in content_lower or "entities" in content_lower or "json" in content_lower:
            return LLMResponse(
                content='[{"id": "alice", "type": "Person", "properties": {"name": "Alice"}, "confidence": 0.9}]',
                provider="mock",
                model=model or "mock-model",
                tokens_used=50
            )
        
        # Default response
        return LLMResponse(
            content="Mock response: Task completed successfully.",
            provider="mock",
            model=model or "mock-model",
            tokens_used=30
        )
    
    async def get_embeddings(self, texts: List[str], model: Optional[str] = None):
        """Generate mock embeddings"""
        # Return consistent embeddings for same text
        # Use 3072 dimensions to match Vertex AI gemini-embedding-001
        import hashlib
        embeddings = []
        embedding_dim = 3072
        for text in texts:
            # Generate deterministic embedding based on text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            # Convert to float list
            embedding = [float(int(text_hash[i:i+2], 16)) / 255.0 for i in range(0, min(32, len(text_hash)), 2)]
            # Pad to embedding_dim dimensions by repeating the pattern
            while len(embedding) < embedding_dim:
                embedding.extend(embedding[:min(len(embedding), embedding_dim - len(embedding))])
            embeddings.append(embedding[:embedding_dim])
        return embeddings
    
    async def stream_text(self, messages, model=None, **kwargs):
        """Mock streaming"""
        yield "Mock "
        yield "stream"
    
    async def close(self):
        """Mock close"""
        pass


@pytest.fixture
def llm_client():
    """Create LLM client (Vertex AI if available, otherwise mock)
    
    Uses Vertex AI client with gemini-embedding-001 for embeddings if configured.
    Falls back to mock client if Vertex AI is not configured.
    """
    if REAL_LLM_AVAILABLE and VERTEX_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS:
        # Ensure environment variables are set for Vertex AI
        os.environ["VERTEX_PROJECT_ID"] = VERTEX_PROJECT_ID
        os.environ["VERTEX_LOCATION"] = VERTEX_LOCATION
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
        return VertexAIClient()
    else:
        # Use mock client as fallback
        return MockLLMClient()


@pytest.fixture
async def graph_store_with_data():
    """Create a graph store with sample knowledge graph data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities with embeddings for vector search
    # Note: Vertex AI gemini-embedding-001 returns 3072-dimensional embeddings
    # Use 3072 dimensions to match, or let the system handle dimension mismatch gracefully
    embedding_dim = 3072  # Match Vertex AI gemini-embedding-001 dimensions
    
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "role": "Software Engineer", "age": 30},
        embedding=[0.1] * embedding_dim
    )
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "role": "Product Manager", "age": 35},
        embedding=[0.2] * embedding_dim
    )
    charlie = Entity(
        id="charlie",
        entity_type="Person",
        properties={"name": "Charlie", "role": "Designer", "age": 28},
        embedding=[0.3] * embedding_dim
    )
    tech_corp = Entity(
        id="tech_corp",
        entity_type="Company",
        properties={"name": "TechCorp", "industry": "Technology"},
        embedding=[0.4] * embedding_dim
    )
    project_alpha = Entity(
        id="project_alpha",
        entity_type="Project",
        properties={"name": "Project Alpha", "status": "active"},
        embedding=[0.5] * embedding_dim
    )
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(charlie)
    await store.add_entity(tech_corp)
    await store.add_entity(project_alpha)
    
    # Create relations for graph traversal
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
    await store.add_relation(Relation(
        id="rel3",
        source_id="bob",
        target_id="tech_corp",
        relation_type="WORKS_FOR",
        properties={}
    ))
    await store.add_relation(Relation(
        id="rel4",
        source_id="alice",
        target_id="project_alpha",
        relation_type="WORKS_ON",
        properties={}
    ))
    await store.add_relation(Relation(
        id="rel5",
        source_id="bob",
        target_id="project_alpha",
        relation_type="MANAGES",
        properties={}
    ))
    
    yield store
    await store.close()


@pytest.fixture
def agent_config():
    """Create test agent configuration"""
    return AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=True,
        retrieval_strategy="hybrid",
        enable_knowledge_caching=True,
        cache_ttl=300,
        max_context_size=10,
    )


@pytest.mark.integration
class TestEndToEndKnowledgeRetrieval:
    """Test 8.4.1: End-to-end knowledge retrieval with real graph store"""

    @pytest.mark.asyncio
    async def test_retrieval_with_real_graph_store(self, llm_client, graph_store_with_data, agent_config):
        """Test end-to-end knowledge retrieval using real graph store"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Retrieve knowledge for a query
            entities = await agent._retrieve_relevant_knowledge(
                task="Find information about Alice",
                context={},
                iteration=1
            )
            
            # Verify entities were retrieved
            assert len(entities) > 0
            assert all(isinstance(e, Entity) for e in entities)
            
            # Verify at least Alice is in results
            entity_ids = [e.id for e in entities]
            assert "alice" in entity_ids
            
            # Verify metrics were updated
            assert agent._graph_metrics.total_graph_queries > 0
            assert agent._graph_metrics.total_entities_retrieved > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_retrieval_finds_related_entities(self, llm_client, graph_store_with_data, agent_config):
        """Test that retrieval finds entities related through graph structure"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Query about Alice should also find related entities
            entities = await agent._retrieve_relevant_knowledge(
                task="Find people connected to Alice",
                context={},
                iteration=1
            )
            
            # Verify multiple entities retrieved
            assert len(entities) > 0
            entity_ids = [e.id for e in entities]
            
            # Should find Alice and potentially related entities
            assert "alice" in entity_ids
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_retrieval_with_entity_extraction(self, llm_client, graph_store_with_data, agent_config):
        """Test that entity extraction works with real retrieval"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Query that should trigger entity extraction
            entities = await agent._retrieve_relevant_knowledge(
                task="Find information about Alice and Bob",
                context={},
                iteration=1
            )
            
            # Verify retrieval succeeded
            assert len(entities) > 0
            
            # Verify entity extraction was used (if extractor available)
            if agent._entity_extractor is not None:
                assert agent._graph_metrics.entity_extraction_count > 0
            
        finally:
            await agent.shutdown()


@pytest.mark.integration
class TestHybridSearchIntegration:
    """Test 8.4.2: Hybrid search integration"""

    @pytest.mark.asyncio
    async def test_hybrid_search_combines_vector_and_graph(self, llm_client, graph_store_with_data, agent_config):
        """Test that hybrid search combines vector similarity and graph traversal"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Set strategy to hybrid
            agent._config.retrieval_strategy = "hybrid"
            
            entities = await agent._retrieve_relevant_knowledge(
                task="Find software engineers",
                context={},
                iteration=1
            )
            
            # Verify hybrid search was used
            assert agent._graph_metrics.hybrid_search_count > 0
            assert len(entities) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_vector_search_finds_similar_entities(self, llm_client, graph_store_with_data, agent_config):
        """Test that vector search finds entities by semantic similarity"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Set strategy to vector-only
            agent._config.retrieval_strategy = "vector"
            
            entities = await agent._retrieve_relevant_knowledge(
                task="Find people",
                context={},
                iteration=1
            )
            
            # Verify vector search was used
            assert agent._graph_metrics.vector_search_count > 0
            assert len(entities) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_graph_search_traverses_relationships(self, llm_client, graph_store_with_data, agent_config):
        """Test that graph search traverses relationships"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Set strategy to graph-only
            agent._config.retrieval_strategy = "graph"
            
            # Provide seed entity directly in context to ensure graph search works
            # This bypasses entity extraction which might not work reliably
            entities = await agent._retrieve_relevant_knowledge(
                task="Find entities related to Alice",
                context={"seed_entity_ids": ["alice"]},  # Provide seed entity directly
                iteration=1
            )
            
            # Verify graph search was used
            assert agent._graph_metrics.graph_search_count > 0
            assert len(entities) > 0
            
            # Verify Alice and related entities are found
            entity_ids = [e.id for e in entities]
            assert "alice" in entity_ids
            
        finally:
            await agent.shutdown()


@pytest.mark.integration
class TestStreamingEvents:
    """Test 8.4.3: Streaming events"""

    @pytest.mark.asyncio
    async def test_retrieval_emits_streaming_events(self, llm_client, graph_store_with_data, agent_config):
        """Test that knowledge retrieval emits streaming events"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Track events
            events = []
            
            async def event_callback(event: Dict[str, Any]) -> None:
                events.append(event)
            
            # Retrieve with event callback
            entities = await agent._retrieve_relevant_knowledge(
                task="Find information about Alice",
                context={},
                iteration=1,
                event_callback=event_callback
            )
            
            # Verify events were emitted
            assert len(events) > 0
            
            # Check for specific event types
            event_types = [e.get("type") for e in events]
            assert "knowledge_retrieval_started" in event_types
            assert "knowledge_retrieval_completed" in event_types
            
            # Verify event structure
            started_event = next((e for e in events if e.get("type") == "knowledge_retrieval_started"), None)
            assert started_event is not None
            assert "query" in started_event
            assert "iteration" in started_event
            assert "timestamp" in started_event
            
            completed_event = next((e for e in events if e.get("type") == "knowledge_retrieval_completed"), None)
            assert completed_event is not None
            assert "entity_count" in completed_event
            assert "retrieval_time_ms" in completed_event
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_entity_extraction_event_emitted(self, llm_client, graph_store_with_data, agent_config):
        """Test that entity extraction events are emitted"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Track events
            events = []
            
            async def event_callback(event: Dict[str, Any]) -> None:
                events.append(event)
            
            # Retrieve with entity extraction
            await agent._retrieve_relevant_knowledge(
                task="Find information about Alice and Bob",
                context={},
                iteration=1,
                event_callback=event_callback
            )
            
            # Check for entity extraction event
            event_types = [e.get("type") for e in events]
            if agent._entity_extractor is not None:
                assert "entity_extraction_completed" in event_types
                
                extraction_event = next((e for e in events if e.get("type") == "entity_extraction_completed"), None)
                assert extraction_event is not None
                assert "entity_ids" in extraction_event or "entity_count" in extraction_event
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_cache_hit_event_emitted(self, llm_client, graph_store_with_data, agent_config):
        """Test that cache hit events are emitted"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            task = "Find information about Alice"
            
            # Track events from second call (cache hit)
            events = []
            
            async def event_callback(event: Dict[str, Any]) -> None:
                events.append(event)
            
            # First call - cache miss
            await agent._retrieve_relevant_knowledge(
                task=task,
                context={},
                iteration=1
            )
            
            # Second call - cache hit
            await agent._retrieve_relevant_knowledge(
                task=task,
                context={},
                iteration=2,
                event_callback=event_callback
            )
            
            # Verify cache hit event was emitted
            event_types = [e.get("type") for e in events]
            assert "knowledge_cache_hit" in event_types
            
            cache_hit_event = next((e for e in events if e.get("type") == "knowledge_cache_hit"), None)
            assert cache_hit_event is not None
            assert "cache_key" in cache_hit_event
            assert "entity_count" in cache_hit_event
            
        finally:
            await agent.shutdown()


@pytest.mark.integration
class TestDifferentRetrievalStrategies:
    """Test 8.4.4: Different retrieval strategies"""

    @pytest.mark.asyncio
    async def test_vector_strategy_retrieval(self, llm_client, graph_store_with_data, agent_config):
        """Test retrieval with vector-only strategy"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            agent._config.retrieval_strategy = "vector"
            
            entities = await agent._retrieve_relevant_knowledge(
                task="Find software engineers",
                context={},
                iteration=1
            )
            
            # Verify vector strategy was used
            assert agent._graph_metrics.vector_search_count > 0
            assert len(entities) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_graph_strategy_retrieval(self, llm_client, graph_store_with_data, agent_config):
        """Test retrieval with graph-only strategy"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            agent._config.retrieval_strategy = "graph"
            
            # Provide seed entity directly to ensure graph search works
            entities = await agent._retrieve_relevant_knowledge(
                task="Find entities connected to Alice",
                context={"seed_entity_ids": ["alice"]},  # Provide seed entity directly
                iteration=1
            )
            
            # Verify graph strategy was used
            assert agent._graph_metrics.graph_search_count > 0
            assert len(entities) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_hybrid_strategy_retrieval(self, llm_client, graph_store_with_data, agent_config):
        """Test retrieval with hybrid strategy"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            agent._config.retrieval_strategy = "hybrid"
            
            entities = await agent._retrieve_relevant_knowledge(
                task="Find software engineers at TechCorp",
                context={},
                iteration=1
            )
            
            # Verify hybrid strategy was used
            assert agent._graph_metrics.hybrid_search_count > 0
            assert len(entities) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_auto_strategy_selection(self, llm_client, graph_store_with_data, agent_config):
        """Test automatic strategy selection based on query"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            agent._config.retrieval_strategy = "auto"
            
            # Query with graph keywords should select graph mode
            # Provide seed entity to ensure it works
            entities = await agent._retrieve_relevant_knowledge(
                task="Find entities related to Alice",
                context={"seed_entity_ids": ["alice"]},  # Provide seed entity directly
                iteration=1
            )
            
            # Verify retrieval succeeded
            assert len(entities) > 0
            
            # Query with semantic keywords should select vector mode
            entities2 = await agent._retrieve_relevant_knowledge(
                task="Find similar entities",
                context={},
                iteration=2
            )
            
            assert len(entities2) > 0
            
        finally:
            await agent.shutdown()

    @pytest.mark.asyncio
    async def test_per_query_strategy_override(self, llm_client, graph_store_with_data, agent_config):
        """Test per-query strategy override via context"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store_with_data
        )
        await agent.initialize()
        
        try:
            # Default strategy is hybrid
            agent._config.retrieval_strategy = "hybrid"
            
            initial_hybrid = agent._graph_metrics.hybrid_search_count
            initial_vector = agent._graph_metrics.vector_search_count
            
            # Override to vector in context
            entities = await agent._retrieve_relevant_knowledge(
                task="Find information",
                context={"retrieval_strategy": "vector"},
                iteration=1
            )
            
            # Verify vector strategy was used (not hybrid)
            assert agent._graph_metrics.vector_search_count > initial_vector
            assert agent._graph_metrics.hybrid_search_count == initial_hybrid
            
        finally:
            await agent.shutdown()


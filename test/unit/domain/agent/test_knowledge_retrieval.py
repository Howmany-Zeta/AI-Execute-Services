"""
Unit tests for KnowledgeAwareAgent knowledge retrieval functionality (Section 8.1)

Tests for:
- 8.1.1: _retrieve_relevant_knowledge() with mock graph store
- 8.1.2: Entity extraction integration
- 8.1.3: Strategy selection logic
- 8.1.4: Error handling and fallbacks
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import List, Tuple

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMResponse
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.error_handling import (
    GraphStoreConnectionError,
    GraphStoreQueryError,
    GraphStoreTimeoutError,
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client with embedding support"""
    client = AsyncMock(spec=BaseLLMClient)
    client.provider_name = "test_provider"
    client.generate_text = AsyncMock(return_value=LLMResponse(
        content="Test response",
        provider="test_provider",
        model="test-model",
        tokens_used=10
    ))
    # Mock embedding generation
    client.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5] * 20])  # 100-dim embedding
    return client


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


@pytest.fixture
async def graph_store():
    """Create a test graph store with sample data"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Add sample entities with embeddings
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "age": 30},
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 20
    )
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "age": 25},
        embedding=[0.2, 0.3, 0.4, 0.5, 0.6] * 20
    )
    company_x = Entity(
        id="company_x",
        entity_type="Company",
        properties={"name": "Company X"},
        embedding=[0.3, 0.4, 0.5, 0.6, 0.7] * 20
    )
    
    await store.add_entity(alice)
    await store.add_entity(bob)
    await store.add_entity(company_x)
    
    yield store
    await store.close()


@pytest.fixture
async def agent_with_graph_store(mock_llm_client, agent_config, graph_store):
    """Create a KnowledgeAwareAgent with graph store initialized"""
    agent = KnowledgeAwareAgent(
        agent_id="test_agent",
        name="Test Agent",
        llm_client=mock_llm_client,
        tools=[],
        config=agent_config,
        graph_store=graph_store
    )
    await agent.initialize()
    yield agent
    await agent.shutdown()


class TestRetrieveRelevantKnowledge:
    """Test 8.1.1: _retrieve_relevant_knowledge() with mock graph store"""

    @pytest.mark.asyncio
    async def test_retrieve_with_hybrid_search_success(self, agent_with_graph_store):
        """Test successful knowledge retrieval using hybrid search"""
        agent = agent_with_graph_store
        
        # Mock the hybrid search to return entities
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
            (Entity(id="bob", entity_type="Person", properties={"name": "Bob"}), 0.85),
        ]
        
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning to return entities as-is (for testing)
        original_prioritize = agent._prioritize_knowledge_context
        original_prune = agent._prune_knowledge_context
        
        def mock_prioritize(entities, **kwargs):
            return entities
        
        def mock_prune(entities, **kwargs):
            return entities
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Call _retrieve_relevant_knowledge
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Restore original methods
        agent._prioritize_knowledge_context = original_prioritize
        agent._prune_knowledge_context = original_prune
        
        # Verify results (entities are extracted from tuples, so they should be Entity objects)
        assert len(entities) > 0
        assert all(isinstance(e, Entity) for e in entities)
        # Verify hybrid search was called
        agent._hybrid_search.search.assert_called_once()
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        assert "query_embedding" in call_args.kwargs
        assert "config" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_retrieve_without_graph_store(self, mock_llm_client, agent_config):
        """Test retrieval returns empty when graph store is None"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=None
        )
        await agent.initialize()
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        assert entities == []
        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_retrieve_without_hybrid_search(self, mock_llm_client, agent_config, graph_store):
        """Test retrieval returns empty when hybrid search is not initialized"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store,
            enable_graph_reasoning=False  # This prevents hybrid search initialization
        )
        await agent.initialize()
        
        # Manually set hybrid_search to None to simulate initialization failure
        agent._hybrid_search = None
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        assert entities == []
        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_retrieve_with_cache_hit(self, agent_with_graph_store):
        """Test retrieval uses cache when available"""
        agent = agent_with_graph_store
        
        # Mock cache to return entities
        cached_entities = [
            Entity(id="cached_1", entity_type="Person", properties={"name": "Cached"}),
            Entity(id="cached_2", entity_type="Person", properties={"name": "Cached2"}),
        ]
        agent._get_cached_knowledge = AsyncMock(return_value=cached_entities)
        
        # Mock hybrid search to track if it's called
        agent._hybrid_search.search = AsyncMock()
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify cache was checked
        agent._get_cached_knowledge.assert_called_once()
        # Verify hybrid search was NOT called (cache hit)
        agent._hybrid_search.search.assert_not_called()
        # Verify cached entities were returned
        assert len(entities) == len(cached_entities)

    @pytest.mark.asyncio
    async def test_retrieve_emits_events(self, agent_with_graph_store):
        """Test that retrieval emits streaming events"""
        agent = agent_with_graph_store
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Track events
        events = []
        async def event_callback(event):
            events.append(event)
        
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1,
            event_callback=event_callback
        )
        
        # Verify events were emitted
        assert len(events) > 0
        event_types = [e.get("type") for e in events]
        assert "knowledge_retrieval_started" in event_types
        assert "knowledge_retrieval_completed" in event_types

    @pytest.mark.asyncio
    async def test_retrieve_updates_metrics(self, agent_with_graph_store):
        """Test that retrieval updates graph metrics"""
        agent = agent_with_graph_store
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
            (Entity(id="bob", entity_type="Person", properties={"name": "Bob"}), 0.85),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        initial_queries = agent._graph_metrics.total_graph_queries
        
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify metrics were updated
        assert agent._graph_metrics.total_graph_queries > initial_queries
        assert agent._graph_metrics.total_entities_retrieved > 0


class TestEntityExtractionIntegration:
    """Test 8.1.2: Entity extraction integration"""

    @pytest.mark.asyncio
    async def test_entity_extraction_before_retrieval(self, agent_with_graph_store):
        """Test that entities are extracted before retrieval"""
        agent = agent_with_graph_store
        
        # Mock entity extractor
        mock_entities = [
            Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="bob", entity_type="Person", properties={"name": "Bob"}),
        ]
        agent._entity_extractor = AsyncMock()
        agent._entity_extractor.extract_entities = AsyncMock(return_value=mock_entities)
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice and Bob",
            context={},
            iteration=1
        )
        
        # Verify entity extraction was called
        agent._entity_extractor.extract_entities.assert_called_once_with("Find information about Alice and Bob")
        # Verify seed entities were passed to search
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        assert "seed_entity_ids" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_entity_extraction_caching(self, agent_with_graph_store):
        """Test that entity extraction results are cached"""
        agent = agent_with_graph_store
        
        # Mock entity extractor
        mock_entities = [
            Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
        ]
        agent._entity_extractor = AsyncMock()
        agent._entity_extractor.extract_entities = AsyncMock(return_value=mock_entities)
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        task = "Find information about Alice"
        
        # First call
        await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=1
        )
        
        # Second call with same task
        await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=2
        )
        
        # Verify entity extraction was called only once (cached on second call)
        assert agent._entity_extractor.extract_entities.call_count == 1

    @pytest.mark.asyncio
    async def test_entity_extraction_fallback_when_none(self, agent_with_graph_store):
        """Test that retrieval works when entity extraction returns no entities"""
        agent = agent_with_graph_store
        
        # Mock entity extractor to return empty list
        agent._entity_extractor = AsyncMock()
        agent._entity_extractor.extract_entities = AsyncMock(return_value=[])
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about something",
            context={},
            iteration=1
        )
        
        # Verify retrieval still works without seed entities
        assert len(entities) > 0
        # Verify search was called with None or empty seed_entity_ids
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_entity_extraction_without_extractor(self, agent_with_graph_store):
        """Test that retrieval works when entity extractor is not available"""
        agent = agent_with_graph_store
        
        # Set entity extractor to None
        agent._entity_extractor = None
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify retrieval still works
        assert len(entities) > 0


class TestStrategySelectionLogic:
    """Test 8.1.3: Strategy selection logic"""

    @pytest.mark.asyncio
    async def test_strategy_vector_mode(self, agent_with_graph_store):
        """Test vector-only strategy selection"""
        agent = agent_with_graph_store
        agent._config.retrieval_strategy = "vector"
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        await agent._retrieve_relevant_knowledge(
            task="Find similar entities",
            context={},
            iteration=1
        )
        
        # Verify search was called with vector mode
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        config: HybridSearchConfig = call_args.kwargs.get("config")
        assert config is not None
        assert config.mode == SearchMode.VECTOR_ONLY

    @pytest.mark.asyncio
    async def test_strategy_graph_mode(self, agent_with_graph_store):
        """Test graph-only strategy selection"""
        agent = agent_with_graph_store
        agent._config.retrieval_strategy = "graph"
        
        # Mock entity extractor to provide seed entities
        mock_entities = [
            Entity(id="alice", entity_type="Person", properties={"name": "Alice"}),
        ]
        agent._entity_extractor = AsyncMock()
        agent._entity_extractor.extract_entities = AsyncMock(return_value=mock_entities)
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        await agent._retrieve_relevant_knowledge(
            task="Find related entities",
            context={},
            iteration=1
        )
        
        # Verify search was called with graph mode
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        config: HybridSearchConfig = call_args.kwargs.get("config")
        assert config is not None
        assert config.mode == SearchMode.GRAPH_ONLY

    @pytest.mark.asyncio
    async def test_strategy_hybrid_mode(self, agent_with_graph_store):
        """Test hybrid strategy selection"""
        agent = agent_with_graph_store
        agent._config.retrieval_strategy = "hybrid"
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify search was called with hybrid mode
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        config: HybridSearchConfig = call_args.kwargs.get("config")
        assert config is not None
        assert config.mode == SearchMode.HYBRID

    @pytest.mark.asyncio
    async def test_strategy_auto_mode(self, agent_with_graph_store):
        """Test auto strategy selection"""
        agent = agent_with_graph_store
        agent._config.retrieval_strategy = "auto"
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Test with graph keywords
        await agent._retrieve_relevant_knowledge(
            task="Find entities related to Alice",
            context={},
            iteration=1
        )
        
        # Verify auto-selection was used
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        config: HybridSearchConfig = call_args.kwargs.get("config")
        assert config is not None
        # Should select based on keywords

    @pytest.mark.asyncio
    async def test_strategy_context_override(self, agent_with_graph_store):
        """Test per-query strategy override via context"""
        agent = agent_with_graph_store
        agent._config.retrieval_strategy = "hybrid"  # Default
        
        # Mock hybrid search
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Override strategy in context
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={"retrieval_strategy": "vector"},
            iteration=1
        )
        
        # Verify context override was used
        call_args = agent._hybrid_search.search.call_args
        assert call_args is not None
        config: HybridSearchConfig = call_args.kwargs.get("config")
        assert config is not None
        assert config.mode == SearchMode.VECTOR_ONLY


class TestErrorHandlingAndFallbacks:
    """Test 8.1.4: Error handling and fallbacks"""

    @pytest.mark.asyncio
    async def test_retrieval_handles_connection_error(self, agent_with_graph_store):
        """Test that connection errors are handled gracefully"""
        agent = agent_with_graph_store
        
        # Mock hybrid search to raise connection error
        agent._hybrid_search.search = AsyncMock(side_effect=GraphStoreConnectionError("Connection failed"))
        
        # Should return empty list instead of raising exception
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert entities == []

    @pytest.mark.asyncio
    async def test_retrieval_handles_query_error(self, agent_with_graph_store):
        """Test that query errors are handled gracefully"""
        agent = agent_with_graph_store
        
        # Mock hybrid search to raise query error
        agent._hybrid_search.search = AsyncMock(side_effect=GraphStoreQueryError("Query failed"))
        
        # Should return empty list instead of raising exception
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert entities == []

    @pytest.mark.asyncio
    async def test_retrieval_handles_timeout_error(self, agent_with_graph_store):
        """Test that timeout errors are handled gracefully"""
        agent = agent_with_graph_store
        
        # Mock hybrid search to raise timeout error
        agent._hybrid_search.search = AsyncMock(side_effect=GraphStoreTimeoutError("Query timeout"))
        
        # Should return empty list instead of raising exception
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert entities == []

    @pytest.mark.asyncio
    async def test_retrieval_handles_generic_exception(self, agent_with_graph_store):
        """Test that generic exceptions are handled gracefully"""
        agent = agent_with_graph_store
        
        # Mock hybrid search to raise generic exception
        agent._hybrid_search.search = AsyncMock(side_effect=Exception("Unexpected error"))
        
        # Should return empty list instead of raising exception
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert entities == []

    @pytest.mark.asyncio
    async def test_retrieval_handles_embedding_failure(self, agent_with_graph_store):
        """Test that embedding generation failure is handled"""
        agent = agent_with_graph_store
        
        # Mock embedding generation to return None
        agent._get_query_embedding = AsyncMock(return_value=None)
        
        # Should return empty list when embedding fails
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert entities == []

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self, agent_with_graph_store):
        """Test that circuit breaker opens after threshold failures"""
        agent = agent_with_graph_store
        
        # Mock hybrid search to always fail
        agent._hybrid_search.search = AsyncMock(side_effect=GraphStoreConnectionError("Connection failed"))
        
        # Trigger failures up to threshold
        threshold = agent._circuit_breaker_threshold
        for i in range(threshold):
            entities = await agent._retrieve_relevant_knowledge(
                task="Find information",
                context={},
                iteration=i + 1
            )
            assert entities == []
        
        # Verify circuit breaker is open
        assert agent._circuit_breaker_open is True
        
        # Next call should return empty immediately without calling search
        agent._hybrid_search.search.reset_mock()
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=threshold + 1
        )
        
        assert entities == []
        # Verify search was not called (circuit breaker open)
        agent._hybrid_search.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, agent_with_graph_store):
        """Test that circuit breaker resets after successful retrieval"""
        agent = agent_with_graph_store
        
        # First, trigger some failures
        agent._hybrid_search.search = AsyncMock(side_effect=GraphStoreConnectionError("Connection failed"))
        for i in range(2):
            await agent._retrieve_relevant_knowledge(
                task="Find information",
                context={},
                iteration=i + 1
            )
        
        # Verify circuit breaker is not open yet (below threshold)
        assert agent._circuit_breaker_open is False
        assert agent._circuit_breaker_failures == 2
        
        # Now succeed
        mock_results: List[Tuple[Entity, float]] = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=3
        )
        
        # Verify circuit breaker was reset
        assert agent._circuit_breaker_failures == 0

    @pytest.mark.asyncio
    async def test_retry_logic_on_transient_errors(self, agent_with_graph_store):
        """Test that retry logic is applied on transient errors"""
        agent = agent_with_graph_store
        
        # Mock search to fail twice then succeed
        call_count = 0
        async def mock_search(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise GraphStoreConnectionError("Transient error")
            return [(Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95)]
        
        agent._hybrid_search.search = AsyncMock(side_effect=mock_search)
        
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify retry was attempted (search called multiple times)
        assert call_count >= 2
        # Verify eventually succeeded
        assert len(entities) > 0


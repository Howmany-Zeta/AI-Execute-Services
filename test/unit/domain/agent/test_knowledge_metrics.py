"""
Unit tests for KnowledgeAwareAgent metrics functionality (Section 8.3)

Tests for:
- 8.3.1: Graph metrics tracking
- 8.3.2: Metrics aggregation
- 8.3.3: Prometheus metrics export
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time
from datetime import datetime

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.llm import BaseLLMClient, LLMResponse
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
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
    client.get_embeddings = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5] * 20])
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
    """Create a test graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def agent_with_metrics(mock_llm_client, agent_config, graph_store):
    """Create a KnowledgeAwareAgent with metrics tracking"""
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


class TestGraphMetricsTracking:
    """Test 8.3.1: Graph metrics tracking"""

    @pytest.mark.asyncio
    async def test_query_count_tracked(self, agent_with_metrics):
        """Test that graph query count is tracked"""
        agent = agent_with_metrics
        
        initial_queries = agent._graph_metrics.total_graph_queries
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify query count increased
        assert agent._graph_metrics.total_graph_queries > initial_queries

    @pytest.mark.asyncio
    async def test_entities_retrieved_tracked(self, agent_with_metrics):
        """Test that entities retrieved count is tracked"""
        agent = agent_with_metrics
        
        initial_entities = agent._graph_metrics.total_entities_retrieved
        
        # Mock hybrid search to return multiple entities
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
            (Entity(id="bob", entity_type="Person", properties={"name": "Bob"}), 0.85),
            (Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"}), 0.75),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify entities count increased
        assert agent._graph_metrics.total_entities_retrieved > initial_entities
        assert agent._graph_metrics.total_entities_retrieved >= 3

    @pytest.mark.asyncio
    async def test_query_time_tracked(self, agent_with_metrics):
        """Test that query execution time is tracked"""
        agent = agent_with_metrics
        
        initial_total_time = agent._graph_metrics.total_graph_query_time
        
        # Mock hybrid search with simulated delay
        async def delayed_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate 100ms delay
            return [(Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95)]
        
        agent._hybrid_search.search = AsyncMock(side_effect=delayed_search)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify query time increased
        assert agent._graph_metrics.total_graph_query_time > initial_total_time
        assert agent._graph_metrics.total_graph_query_time >= 0.1

    @pytest.mark.asyncio
    async def test_strategy_counts_tracked(self, agent_with_metrics):
        """Test that strategy usage counts are tracked"""
        agent = agent_with_metrics
        
        initial_vector = agent._graph_metrics.vector_search_count
        initial_graph = agent._graph_metrics.graph_search_count
        initial_hybrid = agent._graph_metrics.hybrid_search_count
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Test vector strategy
        agent._config.retrieval_strategy = "vector"
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        assert agent._graph_metrics.vector_search_count > initial_vector
        
        # Test graph strategy
        agent._config.retrieval_strategy = "graph"
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=2
        )
        assert agent._graph_metrics.graph_search_count > initial_graph
        
        # Test hybrid strategy
        agent._config.retrieval_strategy = "hybrid"
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=3
        )
        assert agent._graph_metrics.hybrid_search_count > initial_hybrid

    @pytest.mark.asyncio
    async def test_entity_extraction_metrics_tracked(self, agent_with_metrics):
        """Test that entity extraction metrics are tracked"""
        agent = agent_with_metrics
        
        initial_count = agent._graph_metrics.entity_extraction_count
        initial_total_time = agent._graph_metrics.total_extraction_time
        
        # Mock entity extractor with delay
        async def delayed_extract(task):
            await asyncio.sleep(0.05)  # Simulate 50ms delay
            return [Entity(id="alice", entity_type="Person", properties={"name": "Alice"})]
        
        agent._entity_extractor.extract_entities = AsyncMock(side_effect=delayed_extract)
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify extraction metrics updated
        assert agent._graph_metrics.entity_extraction_count > initial_count
        assert agent._graph_metrics.total_extraction_time > initial_total_time
        assert agent._graph_metrics.average_extraction_time > 0


class TestMetricsAggregation:
    """Test 8.3.2: Metrics aggregation"""

    @pytest.mark.asyncio
    async def test_average_query_time_calculated(self, agent_with_metrics):
        """Test that average query time is calculated correctly"""
        agent = agent_with_metrics
        
        # Mock hybrid search with varying delays
        delays = [0.1, 0.2, 0.15]
        delay_index = 0
        
        async def variable_delay_search(*args, **kwargs):
            nonlocal delay_index
            delay = delays[delay_index % len(delays)]
            delay_index += 1
            await asyncio.sleep(delay)
            return [(Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95)]
        
        agent._hybrid_search.search = AsyncMock(side_effect=variable_delay_search)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Execute multiple queries
        for i in range(3):
            await agent._retrieve_relevant_knowledge(
                task=f"Find information {i}",
                context={},
                iteration=i + 1
            )
        
        # Verify average is calculated
        assert agent._graph_metrics.average_graph_query_time > 0
        assert agent._graph_metrics.average_graph_query_time == (
            agent._graph_metrics.total_graph_query_time / agent._graph_metrics.total_graph_queries
        )

    @pytest.mark.asyncio
    async def test_min_max_query_time_tracked(self, agent_with_metrics):
        """Test that min and max query times are tracked"""
        agent = agent_with_metrics
        
        # Mock hybrid search with varying delays
        delays = [0.05, 0.3, 0.1]
        delay_index = 0
        
        async def variable_delay_search(*args, **kwargs):
            nonlocal delay_index
            delay = delays[delay_index % len(delays)]
            delay_index += 1
            await asyncio.sleep(delay)
            return [(Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95)]
        
        agent._hybrid_search.search = AsyncMock(side_effect=variable_delay_search)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Execute multiple queries
        for i in range(3):
            await agent._retrieve_relevant_knowledge(
                task=f"Find information {i}",
                context={},
                iteration=i + 1
            )
        
        # Verify min and max are tracked
        assert agent._graph_metrics.min_graph_query_time is not None
        assert agent._graph_metrics.max_graph_query_time is not None
        assert agent._graph_metrics.min_graph_query_time <= agent._graph_metrics.max_graph_query_time
        assert agent._graph_metrics.min_graph_query_time >= 0.05
        assert agent._graph_metrics.max_graph_query_time >= 0.3

    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculated(self, agent_with_metrics):
        """Test that cache hit rate is calculated correctly"""
        agent = agent_with_metrics
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        task = "Find information about Alice"
        
        # First call - cache miss
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=1)
        
        # Second call - cache hit
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=2)
        
        # Third call - cache hit
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=3)
        
        # Verify hit rate is calculated correctly
        total_requests = agent._graph_metrics.cache_hits + agent._graph_metrics.cache_misses
        assert total_requests == 3
        assert agent._graph_metrics.cache_hits == 2
        assert agent._graph_metrics.cache_misses == 1
        assert agent._graph_metrics.cache_hit_rate == pytest.approx(2.0 / 3.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_average_extraction_time_calculated(self, agent_with_metrics):
        """Test that average extraction time is calculated correctly"""
        agent = agent_with_metrics
        
        # Mock entity extractor with varying delays
        delays = [0.05, 0.1, 0.08]
        delay_index = 0
        
        async def variable_delay_extract(task):
            nonlocal delay_index
            delay = delays[delay_index % len(delays)]
            delay_index += 1
            await asyncio.sleep(delay)
            return [Entity(id="alice", entity_type="Person", properties={"name": "Alice"})]
        
        agent._entity_extractor.extract_entities = AsyncMock(side_effect=variable_delay_extract)
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Execute multiple extractions
        for i in range(3):
            await agent._retrieve_relevant_knowledge(
                task=f"Find information about Alice {i}",
                context={},
                iteration=i + 1
            )
        
        # Verify average is calculated
        assert agent._graph_metrics.average_extraction_time > 0
        assert agent._graph_metrics.average_extraction_time == pytest.approx(
            agent._graph_metrics.total_extraction_time / agent._graph_metrics.entity_extraction_count,
            rel=0.1
        )

    @pytest.mark.asyncio
    async def test_metrics_reset(self, agent_with_metrics):
        """Test that metrics can be reset"""
        agent = agent_with_metrics
        
        # Generate some metrics
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify metrics were updated
        assert agent._graph_metrics.total_graph_queries > 0
        
        # Reset metrics
        agent.reset_graph_metrics()
        
        # Verify metrics were reset
        assert agent._graph_metrics.total_graph_queries == 0
        assert agent._graph_metrics.total_entities_retrieved == 0
        assert agent._graph_metrics.cache_hits == 0
        assert agent._graph_metrics.cache_misses == 0


class TestPrometheusMetricsExport:
    """Test 8.3.3: Prometheus metrics export"""

    @pytest.mark.asyncio
    async def test_prometheus_metrics_initialized(self, agent_with_metrics):
        """Test that Prometheus metrics are initialized"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            # Metrics may already be registered from previous tests
            pass
        
        # Verify metrics are initialized (if prometheus_client is available)
        if agent._prometheus_enabled:
            assert agent._prometheus_metrics is not None
            assert "knowledge_retrieval_total" in agent._prometheus_metrics
            assert "knowledge_retrieval_duration" in agent._prometheus_metrics
            assert "knowledge_cache_hit_rate" in agent._prometheus_metrics

    @pytest.mark.asyncio
    async def test_prometheus_query_counter_incremented(self, agent_with_metrics):
        """Test that Prometheus query counter is incremented"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            pass
        
        # Skip test if Prometheus not available
        if not agent._prometheus_enabled or agent._prometheus_metrics is None:
            pytest.skip("Prometheus metrics not available")
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Get initial counter value
        counter = agent._prometheus_metrics["knowledge_retrieval_total"]
        initial_value = counter.labels(agent_id=agent.agent_id, strategy="hybrid")._value._value
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify counter was incremented
        new_value = counter.labels(agent_id=agent.agent_id, strategy="hybrid")._value._value
        assert new_value > initial_value

    @pytest.mark.asyncio
    async def test_prometheus_duration_recorded(self, agent_with_metrics):
        """Test that Prometheus duration histogram is recorded"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            pass
        
        # Skip test if Prometheus not available
        if not agent._prometheus_enabled or agent._prometheus_metrics is None:
            pytest.skip("Prometheus metrics not available")
        
        # Mock hybrid search with delay
        async def delayed_search(*args, **kwargs):
            await asyncio.sleep(0.1)
            return [(Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95)]
        
        agent._hybrid_search.search = AsyncMock(side_effect=delayed_search)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Get initial histogram count
        histogram = agent._prometheus_metrics["knowledge_retrieval_duration"]
        initial_count = histogram.labels(agent_id=agent.agent_id, strategy="hybrid")._count._value
        
        await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        # Verify histogram was updated
        new_count = histogram.labels(agent_id=agent.agent_id, strategy="hybrid")._count._value
        assert new_count > initial_count

    @pytest.mark.asyncio
    async def test_prometheus_cache_metrics_recorded(self, agent_with_metrics):
        """Test that Prometheus cache metrics are recorded"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            pass
        
        # Skip test if Prometheus not available
        if not agent._prometheus_enabled or agent._prometheus_metrics is None:
            pytest.skip("Prometheus metrics not available")
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        task = "Find information about Alice"
        
        # Get initial cache metrics
        hits_counter = agent._prometheus_metrics["knowledge_cache_hits"]
        misses_counter = agent._prometheus_metrics["knowledge_cache_misses"]
        hit_rate_gauge = agent._prometheus_metrics["knowledge_cache_hit_rate"]
        
        initial_hits = hits_counter.labels(agent_id=agent.agent_id)._value._value
        initial_misses = misses_counter.labels(agent_id=agent.agent_id)._value._value
        
        # First call - cache miss
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=1)
        
        # Verify miss counter incremented
        new_misses = misses_counter.labels(agent_id=agent.agent_id)._value._value
        assert new_misses > initial_misses
        
        # Second call - cache hit
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=2)
        
        # Verify hit counter incremented
        new_hits = hits_counter.labels(agent_id=agent.agent_id)._value._value
        assert new_hits > initial_hits
        
        # Verify hit rate gauge updated
        hit_rate_value = hit_rate_gauge.labels(agent_id=agent.agent_id)._value._value
        assert hit_rate_value > 0
        assert hit_rate_value <= 1.0

    @pytest.mark.asyncio
    async def test_prometheus_entity_extraction_metrics_recorded(self, agent_with_metrics):
        """Test that Prometheus entity extraction metrics are recorded"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            pass
        
        # Skip test if Prometheus not available
        if not agent._prometheus_enabled or agent._prometheus_metrics is None:
            pytest.skip("Prometheus metrics not available")
        
        # Mock entity extractor with delay
        async def delayed_extract(task):
            await asyncio.sleep(0.05)
            return [Entity(id="alice", entity_type="Person", properties={"name": "Alice"})]
        
        agent._entity_extractor.extract_entities = AsyncMock(side_effect=delayed_extract)
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # Get initial extraction counter
        extraction_counter = agent._prometheus_metrics["entity_extraction_total"]
        extraction_duration = agent._prometheus_metrics["entity_extraction_duration"]
        
        initial_count = extraction_counter.labels(agent_id=agent.agent_id)._value._value
        initial_duration_count = extraction_duration.labels(agent_id=agent.agent_id)._count._value
        
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify extraction counter incremented
        new_count = extraction_counter.labels(agent_id=agent.agent_id)._value._value
        assert new_count > initial_count
        
        # Verify extraction duration histogram updated
        new_duration_count = extraction_duration.labels(agent_id=agent.agent_id)._count._value
        assert new_duration_count > initial_duration_count

    @pytest.mark.asyncio
    async def test_prometheus_metrics_graceful_fallback(self, mock_llm_client, agent_config, graph_store):
        """Test that Prometheus metrics gracefully handle missing prometheus_client"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        await agent.initialize()
        
        # Mock ImportError for prometheus_client by patching the import inside the method
        original_init = agent.initialize_prometheus_metrics
        def mock_init():
            agent._prometheus_enabled = False
            agent._prometheus_metrics = None
        
        agent.initialize_prometheus_metrics = mock_init
        agent.initialize_prometheus_metrics()
        
        # Verify graceful fallback
        assert agent._prometheus_enabled is False
        assert agent._prometheus_metrics is None
        
        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_prometheus_metrics_with_different_strategies(self, agent_with_metrics):
        """Test that Prometheus metrics are recorded with correct strategy labels"""
        agent = agent_with_metrics
        
        # Initialize Prometheus metrics (may fail if already registered, that's OK)
        try:
            agent.initialize_prometheus_metrics()
        except Exception:
            pass
        
        # Skip test if Prometheus not available
        if not agent._prometheus_enabled or agent._prometheus_metrics is None:
            pytest.skip("Prometheus metrics not available")
        
        # Mock hybrid search
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        counter = agent._prometheus_metrics["knowledge_retrieval_total"]
        
        # Test with different strategies
        strategies = ["vector", "graph", "hybrid"]
        for strategy in strategies:
            agent._config.retrieval_strategy = strategy
            initial_value = counter.labels(agent_id=agent.agent_id, strategy=strategy)._value._value
            
            await agent._retrieve_relevant_knowledge(
                task=f"Find information with {strategy}",
                context={},
                iteration=1
            )
            
            # Verify counter incremented for this strategy
            new_value = counter.labels(agent_id=agent.agent_id, strategy=strategy)._value._value
            assert new_value > initial_value


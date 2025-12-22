"""
Unit tests for KnowledgeAwareAgent caching functionality (Section 8.2)

Tests for:
- 8.2.1: Cache hit/miss scenarios
- 8.2.2: Cache TTL expiration
- 8.2.3: Cache invalidation
- 8.2.4: Cache metrics tracking
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
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
    """Create test agent configuration with caching enabled"""
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
async def agent_with_cache(mock_llm_client, agent_config, graph_store):
    """Create a KnowledgeAwareAgent with caching enabled"""
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


class TestCacheHitMissScenarios:
    """Test 8.2.1: Cache hit/miss scenarios"""

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_retrieval(self, agent_with_cache):
        """Test that cache miss triggers actual retrieval"""
        agent = agent_with_cache
        
        # Mock hybrid search to return entities
        mock_results = [
            (Entity(id="alice", entity_type="Person", properties={"name": "Alice"}), 0.95),
            (Entity(id="bob", entity_type="Person", properties={"name": "Bob"}), 0.85),
        ]
        agent._hybrid_search.search = AsyncMock(return_value=mock_results)
        
        # Mock prioritization and pruning to return entities as-is
        def mock_prioritize(entities, **kwargs):
            return entities
        def mock_prune(entities, **kwargs):
            return [(e if isinstance(e, Entity) else e[0], 1.0) for e in entities]
        
        agent._prioritize_knowledge_context = mock_prioritize
        agent._prune_knowledge_context = mock_prune
        
        # First call - should be cache miss
        entities1 = await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        # Verify hybrid search was called (cache miss)
        assert agent._hybrid_search.search.called
        assert len(entities1) > 0
        
        # Verify cache miss was tracked
        assert agent._cache_misses > 0

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_results(self, agent_with_cache):
        """Test that cache hit returns cached results without retrieval"""
        agent = agent_with_cache
        
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
        
        # First call - cache miss, should cache results
        entities1 = await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=1
        )
        
        # Reset mock call count
        agent._hybrid_search.search.reset_mock()
        initial_misses = agent._cache_misses
        initial_hits = agent._cache_hits
        
        # Second call with same task - should be cache hit
        entities2 = await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=2
        )
        
        # Verify hybrid search was NOT called (cache hit)
        agent._hybrid_search.search.assert_not_called()
        
        # Verify cache hit was tracked
        assert agent._cache_hits > initial_hits
        assert agent._cache_misses == initial_misses
        
        # Verify same entities returned
        assert len(entities1) == len(entities2)
        assert entities1[0].id == entities2[0].id

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, agent_with_cache):
        """Test that cache keys are generated correctly"""
        agent = agent_with_cache
        
        # Generate cache key for a task
        cache_key1 = agent._generate_cache_key("knowledge_retrieval", {
            "task": "Find Alice",
            "strategy": "hybrid"
        })
        
        # Same task and strategy should generate same key
        cache_key2 = agent._generate_cache_key("knowledge_retrieval", {
            "task": "Find Alice",
            "strategy": "hybrid"
        })
        
        assert cache_key1 == cache_key2
        
        # Different strategy should generate different key
        cache_key3 = agent._generate_cache_key("knowledge_retrieval", {
            "task": "Find Alice",
            "strategy": "vector"
        })
        
        assert cache_key1 != cache_key3
        
        # Different task should generate different key
        cache_key4 = agent._generate_cache_key("knowledge_retrieval", {
            "task": "Find Bob",
            "strategy": "hybrid"
        })
        
        assert cache_key1 != cache_key4

    @pytest.mark.asyncio
    async def test_cache_without_cache_initialized(self, mock_llm_client, agent_config, graph_store):
        """Test that retrieval works when cache is not initialized"""
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=graph_store
        )
        await agent.initialize()
        
        # Manually set cache to None
        agent._graph_cache = None
        
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
        
        # Should work without cache
        entities = await agent._retrieve_relevant_knowledge(
            task="Find information",
            context={},
            iteration=1
        )
        
        assert len(entities) > 0
        await agent.shutdown()


class TestCacheTTLExpiration:
    """Test 8.2.2: Cache TTL expiration"""

    @pytest.mark.asyncio
    async def test_cache_expires_after_ttl(self, agent_with_cache):
        """Test that cached entries expire after TTL"""
        agent = agent_with_cache
        
        # Set a very short TTL for testing
        agent._config.cache_ttl = 1  # 1 second
        
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
        entities1 = await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=1
        )
        
        # Reset mock
        agent._hybrid_search.search.reset_mock()
        
        # Second call immediately - should be cache hit
        entities2 = await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=2
        )
        
        agent._hybrid_search.search.assert_not_called()
        
        # Wait for TTL to expire
        await asyncio.sleep(1.5)
        
        # Third call after expiration - should be cache miss
        entities3 = await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=3
        )
        
        # Verify hybrid search was called again (cache expired)
        agent._hybrid_search.search.assert_called()

    @pytest.mark.asyncio
    async def test_cache_respects_configured_ttl(self, mock_llm_client, graph_store):
        """Test that cache respects configured TTL"""
        # Create config with specific TTL
        config = AgentConfiguration(
            max_retries=3,
            timeout_seconds=30,
            enable_logging=True,
            retrieval_strategy="hybrid",
            enable_knowledge_caching=True,
            cache_ttl=5,  # 5 seconds
            max_context_size=10,
        )
        
        agent = KnowledgeAwareAgent(
            agent_id="test_agent",
            name="Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=config,
            graph_store=graph_store
        )
        await agent.initialize()
        
        # Verify TTL is set correctly
        assert agent._graph_cache is not None
        assert agent._graph_cache.config.ttl == 5
        
        await agent.shutdown()


class TestCacheInvalidation:
    """Test 8.2.3: Cache invalidation"""

    @pytest.mark.asyncio
    async def test_cache_invalidation_clears_entry(self, agent_with_cache):
        """Test that cache invalidation clears specific entry"""
        agent = agent_with_cache
        
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
        await agent._retrieve_relevant_knowledge(
            task=task,
            context={},
            iteration=1
        )
        
        # Generate cache key
        cache_key = agent._generate_cache_key("knowledge_retrieval", {
            "task": task,
            "strategy": "hybrid"
        })
        
        # Verify entry is cached
        cached = await agent._get_cached_knowledge(cache_key)
        assert cached is not None
        
        # Invalidate cache
        if agent._graph_cache and agent._graph_cache.backend:
            await agent._graph_cache.backend.delete(cache_key)
        
        # Verify entry is no longer cached
        cached_after = await agent._get_cached_knowledge(cache_key)
        assert cached_after is None

    @pytest.mark.asyncio
    async def test_cache_clear_removes_all_entries(self, agent_with_cache):
        """Test that cache clear removes all entries"""
        agent = agent_with_cache
        
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
        
        # Cache multiple entries
        task1 = "Find information about Alice"
        task2 = "Find information about Bob"
        
        await agent._retrieve_relevant_knowledge(task=task1, context={}, iteration=1)
        await agent._retrieve_relevant_knowledge(task=task2, context={}, iteration=1)
        
        cache_key1 = agent._generate_cache_key("knowledge_retrieval", {
            "task": task1,
            "strategy": "hybrid"
        })
        cache_key2 = agent._generate_cache_key("knowledge_retrieval", {
            "task": task2,
            "strategy": "hybrid"
        })
        
        # Verify both are cached
        assert await agent._get_cached_knowledge(cache_key1) is not None
        assert await agent._get_cached_knowledge(cache_key2) is not None
        
        # Clear all cache
        if agent._graph_cache and agent._graph_cache.backend:
            await agent._graph_cache.backend.clear()
        
        # Verify both are cleared
        assert await agent._get_cached_knowledge(cache_key1) is None
        assert await agent._get_cached_knowledge(cache_key2) is None


class TestCacheMetricsTracking:
    """Test 8.2.4: Cache metrics tracking"""

    @pytest.mark.asyncio
    async def test_cache_hits_tracked(self, agent_with_cache):
        """Test that cache hits are tracked in metrics"""
        agent = agent_with_cache
        
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
        
        initial_hits = agent._cache_hits
        initial_misses = agent._cache_misses
        
        # First call - cache miss
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=1)
        
        assert agent._cache_misses > initial_misses
        assert agent._cache_hits == initial_hits
        
        # Second call - cache hit
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=2)
        
        assert agent._cache_hits > initial_hits

    @pytest.mark.asyncio
    async def test_cache_misses_tracked(self, agent_with_cache):
        """Test that cache misses are tracked in metrics"""
        agent = agent_with_cache
        
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
        
        initial_misses = agent._cache_misses
        
        # First call - cache miss
        await agent._retrieve_relevant_knowledge(
            task="Find information about Alice",
            context={},
            iteration=1
        )
        
        assert agent._cache_misses > initial_misses

    @pytest.mark.asyncio
    async def test_cache_hit_rate_calculated(self, agent_with_cache):
        """Test that cache hit rate is calculated correctly"""
        agent = agent_with_cache
        
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
        
        # First call - cache miss (1 miss)
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=1)
        
        # Second call - cache hit (1 hit)
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=2)
        
        # Third call - cache hit (2 hits)
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=3)
        
        # Verify hit rate is calculated
        total_requests = agent._cache_hits + agent._cache_misses
        assert total_requests == 3
        assert agent._cache_hits == 2
        assert agent._cache_misses == 1
        
        # Verify hit rate in graph metrics
        hit_rate = agent._graph_metrics.cache_hit_rate
        assert hit_rate > 0
        assert hit_rate <= 1.0

    @pytest.mark.asyncio
    async def test_cache_metrics_exposed_via_get_metrics(self, agent_with_cache):
        """Test that cache metrics are exposed via get_metrics()"""
        agent = agent_with_cache
        
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
        
        # Generate some cache activity
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=1)
        await agent._retrieve_relevant_knowledge(task=task, context={}, iteration=2)
        
        # Get graph metrics (separate method for graph-specific metrics)
        graph_metrics = agent.get_graph_metrics()
        
        # Verify cache metrics are included in graph metrics
        assert "cache_hit_rate" in graph_metrics
        assert "cache_hits" in graph_metrics
        assert "cache_misses" in graph_metrics
        
        # Verify cache hit rate is available
        assert agent._graph_metrics.cache_hit_rate is not None
        assert agent._graph_metrics.cache_hits >= 0
        assert agent._graph_metrics.cache_misses >= 0
        
        # Also verify cache metrics via dedicated method
        cache_metrics = agent.get_cache_metrics()
        assert "cache_hits" in cache_metrics
        assert "cache_misses" in cache_metrics
        assert "hit_rate" in cache_metrics


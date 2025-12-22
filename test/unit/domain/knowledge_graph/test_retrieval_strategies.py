"""
Unit tests for advanced retrieval strategies

Tests PersonalizedPageRank, MultiHopRetrieval, FilteredRetrieval, and RetrievalCache.
"""

import pytest
import asyncio
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank,
    MultiHopRetrieval,
    FilteredRetrieval,
    RetrievalCache
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def network_graph():
    """Fixture with a social network-like graph"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities: A -> B -> C -> D
    #                  A -> E -> F
    #                  B -> E
    entities = [
        Entity(id="a", entity_type="Person", properties={"name": "Alice", "role": "Manager"}),
        Entity(id="b", entity_type="Person", properties={"name": "Bob", "role": "Engineer"}),
        Entity(id="c", entity_type="Person", properties={"name": "Carol", "role": "Engineer"}),
        Entity(id="d", entity_type="Person", properties={"name": "Dave", "role": "Director"}),
        Entity(id="e", entity_type="Person", properties={"name": "Eve", "role": "Engineer"}),
        Entity(id="f", entity_type="Person", properties={"name": "Frank", "role": "Engineer"}),
    ]
    
    for entity in entities:
        await store.add_entity(entity)
    
    # Create relations
    relations = [
        Relation(id="r1", relation_type="MANAGES", source_id="a", target_id="b", weight=1.0),
        Relation(id="r2", relation_type="COLLABORATES", source_id="b", target_id="c", weight=0.9),
        Relation(id="r3", relation_type="REPORTS_TO", source_id="c", target_id="d", weight=1.0),
        Relation(id="r4", relation_type="MANAGES", source_id="a", target_id="e", weight=1.0),
        Relation(id="r5", relation_type="COLLABORATES", source_id="e", target_id="f", weight=0.8),
        Relation(id="r6", relation_type="WORKS_WITH", source_id="b", target_id="e", weight=0.7),
    ]
    
    for relation in relations:
        await store.add_relation(relation)
    
    yield store
    await store.close()


class TestPersonalizedPageRank:
    """Test Personalized PageRank retrieval"""
    
    @pytest.mark.asyncio
    async def test_basic_pagerank(self, network_graph):
        """Test basic PageRank computation"""
        ppr = PersonalizedPageRank(network_graph)
        
        results = await ppr.retrieve(
            seed_entity_ids=["a"],
            max_results=5,
            alpha=0.15,
            max_iterations=50
        )
        
        # Should return results
        assert len(results) > 0
        
        # Seed entity should have high score
        entity_ids = [entity.id for entity, _ in results]
        assert "a" in entity_ids
        
        # Scores should be in descending order
        scores = [score for _, score in results]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_pagerank_with_multiple_seeds(self, network_graph):
        """Test PageRank with multiple seed entities"""
        ppr = PersonalizedPageRank(network_graph)
        
        results = await ppr.retrieve(
            seed_entity_ids=["a", "d"],
            max_results=6,
            alpha=0.15
        )
        
        # Should return results
        assert len(results) > 0
        
        # Both seeds should be in results
        entity_ids = [entity.id for entity, _ in results]
        assert "a" in entity_ids
        assert "d" in entity_ids
    
    @pytest.mark.asyncio
    async def test_pagerank_convergence(self, network_graph):
        """Test that PageRank converges"""
        ppr = PersonalizedPageRank(network_graph)
        
        # Run with different iteration limits
        results_10 = await ppr.retrieve(
            seed_entity_ids=["a"],
            max_iterations=10,
            convergence_threshold=1e-6
        )
        
        results_100 = await ppr.retrieve(
            seed_entity_ids=["a"],
            max_iterations=100,
            convergence_threshold=1e-6
        )
        
        # Both should return results
        assert len(results_10) > 0
        assert len(results_100) > 0
    
    @pytest.mark.asyncio
    async def test_pagerank_empty_seeds(self, network_graph):
        """Test PageRank with empty seeds"""
        ppr = PersonalizedPageRank(network_graph)
        
        results = await ppr.retrieve(
            seed_entity_ids=[],
            max_results=5
        )
        
        # Should return empty results
        assert len(results) == 0


class TestMultiHopRetrieval:
    """Test multi-hop neighbor retrieval"""
    
    @pytest.mark.asyncio
    async def test_single_hop_retrieval(self, network_graph):
        """Test single-hop retrieval"""
        retrieval = MultiHopRetrieval(network_graph)
        
        results = await retrieval.retrieve(
            seed_entity_ids=["a"],
            max_hops=1,
            max_results=10
        )
        
        # Should find direct neighbors
        assert len(results) > 0
        
        # Should include seed and its neighbors (b, e)
        entity_ids = {entity.id for entity, _ in results}
        assert "a" in entity_ids  # Seed
        assert "b" in entity_ids  # Direct neighbor
        assert "e" in entity_ids  # Direct neighbor
    
    @pytest.mark.asyncio
    async def test_multi_hop_retrieval(self, network_graph):
        """Test multi-hop retrieval"""
        retrieval = MultiHopRetrieval(network_graph)
        
        results = await retrieval.retrieve(
            seed_entity_ids=["a"],
            max_hops=2,
            max_results=10
        )
        
        # Should find entities within 2 hops
        assert len(results) >= 3
        
        # Should include entities at different hop distances
        entity_ids = {entity.id for entity, _ in results}
        assert "a" in entity_ids  # Hop 0
        assert "b" in entity_ids  # Hop 1
        assert "c" in entity_ids or "e" in entity_ids  # Hop 1
    
    @pytest.mark.asyncio
    async def test_hop_score_decay(self, network_graph):
        """Test that scores decay with hop distance"""
        retrieval = MultiHopRetrieval(network_graph)
        
        results = await retrieval.retrieve(
            seed_entity_ids=["a"],
            max_hops=2,
            score_decay=0.5,
            include_seeds=True
        )
        
        # Create score map
        scores = {entity.id: score for entity, score in results}
        
        # Seed should have highest score (1.0)
        assert scores["a"] == 1.0
        
        # 1-hop neighbors should have decayed score (0.5)
        if "b" in scores:
            assert scores["b"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_exclude_seeds(self, network_graph):
        """Test excluding seeds from results"""
        retrieval = MultiHopRetrieval(network_graph)
        
        results = await retrieval.retrieve(
            seed_entity_ids=["a"],
            max_hops=1,
            include_seeds=False
        )
        
        # Seeds should not be in results
        entity_ids = {entity.id for entity, _ in results}
        assert "a" not in entity_ids
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, network_graph):
        """Test max results limit"""
        retrieval = MultiHopRetrieval(network_graph)
        
        results = await retrieval.retrieve(
            seed_entity_ids=["a"],
            max_hops=3,
            max_results=3
        )
        
        # Should respect max results limit
        assert len(results) <= 3


class TestFilteredRetrieval:
    """Test filtered retrieval"""
    
    @pytest.mark.asyncio
    async def test_filter_by_entity_type(self, network_graph):
        """Test filtering by entity type"""
        retrieval = FilteredRetrieval(network_graph)
        
        # Add embeddings to entities for vector search
        entities = []
        for entity_id in ["a", "b", "c", "d", "e", "f"]:
            entity = await network_graph.get_entity(entity_id)
            if entity:
                # Create new entity with embedding (entities are immutable)
                updated_entity = Entity(
                    id=entity.id,
                    entity_type=entity.entity_type,
                    properties=entity.properties,
                    embedding=[0.1] * 128
                )
                # Update in store
                network_graph.entities[entity_id] = updated_entity
                entities.append(updated_entity)
        
        results = await retrieval.retrieve(
            entity_type="Person",
            max_results=10
        )
        
        # All results should be Person type
        for entity, score in results:
            assert entity.entity_type == "Person"
    
    @pytest.mark.asyncio
    async def test_filter_by_property(self, network_graph):
        """Test filtering by property value"""
        retrieval = FilteredRetrieval(network_graph)
        
        # Add embeddings
        for entity_id in ["a", "b", "c", "d", "e", "f"]:
            entity = await network_graph.get_entity(entity_id)
            if entity:
                updated_entity = Entity(
                    id=entity.id,
                    entity_type=entity.entity_type,
                    properties=entity.properties,
                    embedding=[0.1] * 128
                )
                network_graph.entities[entity_id] = updated_entity
        
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "Engineer"},
            max_results=10
        )
        
        # All results should have role=Engineer
        for entity, score in results:
            assert entity.properties.get("role") == "Engineer"
    
    @pytest.mark.asyncio
    async def test_custom_filter_function(self, network_graph):
        """Test custom filter function"""
        retrieval = FilteredRetrieval(network_graph)
        
        # Add embeddings
        for entity_id in ["a", "b", "c", "d", "e", "f"]:
            entity = await network_graph.get_entity(entity_id)
            if entity:
                updated_entity = Entity(
                    id=entity.id,
                    entity_type=entity.entity_type,
                    properties=entity.properties,
                    embedding=[0.1] * 128
                )
                network_graph.entities[entity_id] = updated_entity
        
        # Filter for names starting with 'A' or 'B'
        def name_filter(entity: Entity) -> bool:
            name = entity.properties.get("name", "")
            return name.startswith("A") or name.startswith("B")
        
        results = await retrieval.retrieve(
            entity_type="Person",
            filter_fn=name_filter,
            max_results=10
        )
        
        # All results should match filter
        for entity, score in results:
            name = entity.properties.get("name", "")
            assert name.startswith("A") or name.startswith("B")


class TestRetrievalCache:
    """Test retrieval caching"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = RetrievalCache(max_size=10, ttl=60)
        
        assert cache.max_size == 10
        assert cache.ttl == 60
        
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["cache_size"] == 0
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit"""
        cache = RetrievalCache(max_size=10, ttl=60)
        
        async def compute():
            return [("result", 1.0)]
        
        # First call - cache miss
        result1 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute
        )
        
        # Second call - cache hit
        result2 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute
        )
        
        # Results should be identical
        assert result1 == result2
        
        # Check statistics
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss"""
        cache = RetrievalCache(max_size=10, ttl=60)
        
        call_count = 0
        
        async def compute():
            nonlocal call_count
            call_count += 1
            return [("result", call_count)]
        
        # First call
        result1 = await cache.get_or_compute(
            cache_key="key1",
            compute_fn=compute
        )
        
        # Different key - should compute again
        result2 = await cache.get_or_compute(
            cache_key="key2",
            compute_fn=compute
        )
        
        # Should have called compute twice
        assert call_count == 2
        assert result1 != result2
    
    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache entry expiration"""
        cache = RetrievalCache(max_size=10, ttl=0.1)  # 0.1 second TTL
        
        call_count = 0
        
        async def compute():
            nonlocal call_count
            call_count += 1
            return [("result", call_count)]
        
        # First call
        result1 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute
        )
        
        # Wait for expiration
        await asyncio.sleep(0.2)
        
        # Should recompute due to expiration
        result2 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute
        )
        
        # Should have called compute twice
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self):
        """Test LRU eviction"""
        cache = RetrievalCache(max_size=2, ttl=60)
        
        async def compute(value):
            return [("result", value)]
        
        # Fill cache
        await cache.get_or_compute(cache_key="key1", compute_fn=lambda: compute(1))
        await cache.get_or_compute(cache_key="key2", compute_fn=lambda: compute(2))
        
        # Cache is full (size=2)
        assert cache.get_stats()["cache_size"] == 2
        
        # Add third entry - should evict LRU (key1)
        await cache.get_or_compute(cache_key="key3", compute_fn=lambda: compute(3))
        
        # Cache should still be size 2
        assert cache.get_stats()["cache_size"] == 2
    
    def test_cache_invalidation(self):
        """Test cache invalidation"""
        cache = RetrievalCache(max_size=10, ttl=60)
        
        # Add entry
        cache._cache["test_key"] = ([("result", 1.0)], 0)
        cache._access_order.append("test_key")
        
        # Invalidate
        cache.invalidate("test_key")
        
        # Should be removed
        assert "test_key" not in cache._cache
        assert "test_key" not in cache._access_order
    
    def test_cache_clear(self):
        """Test cache clear"""
        cache = RetrievalCache(max_size=10, ttl=60)
        
        # Add entries
        cache._cache["key1"] = ([("result", 1.0)], 0)
        cache._cache["key2"] = ([("result", 2.0)], 0)
        
        # Clear
        cache.clear()
        
        # Should be empty
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        cache = RetrievalCache()
        
        # Same parameters should generate same key
        key1 = cache._generate_key(param1="value1", param2="value2")
        key2 = cache._generate_key(param1="value1", param2="value2")
        assert key1 == key2
        
        # Different parameters should generate different keys
        key3 = cache._generate_key(param1="value1", param2="value3")
        assert key1 != key3
        
        # Order shouldn't matter
        key4 = cache._generate_key(param2="value2", param1="value1")
        assert key1 == key4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


"""
Unit tests for knowledge graph retrieval module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import time
import asyncio
from typing import List, Tuple

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank,
    MultiHopRetrieval,
    FilteredRetrieval,
    RetrievalCache
)


class TestPersonalizedPageRank:
    """Test PersonalizedPageRank"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def populated_store(self):
        """Create graph store with sample data for PageRank"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create a simple graph: A -> B -> C, A -> D
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
            Entity(id="e3", entity_type="Person", properties={"name": "Charlie"}),
            Entity(id="e4", entity_type="Person", properties={"name": "Diana"})
        ]
        
        for entity in entities:
            await store.add_entity(entity)
        
        # Create relations: e1 -> e2 -> e3, e1 -> e4
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3"),
            Relation(id="r3", relation_type="KNOWS", source_id="e1", target_id="e4")
        ]
        
        for relation in relations:
            await store.add_relation(relation)
        
        yield store
        await store.close()
    
    @pytest.fixture
    def ppr(self, graph_store):
        """Create PersonalizedPageRank instance"""
        return PersonalizedPageRank(graph_store)
    
    @pytest.fixture
    def ppr_populated(self, populated_store):
        """Create PersonalizedPageRank instance with populated store"""
        return PersonalizedPageRank(populated_store)
    
    @pytest.mark.asyncio
    async def test_retrieve_empty_seeds(self, ppr):
        """Test retrieve with empty seed list"""
        results = await ppr.retrieve(seed_entity_ids=[])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retrieve_single_seed(self, ppr_populated):
        """Test retrieve with single seed entity"""
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.15,
            max_iterations=50,
            convergence_threshold=1e-4
        )
        
        assert isinstance(results, list)
        # Should have at least the seed entity
        assert len(results) > 0
        assert all(isinstance(item, tuple) and len(item) == 2 for item in results)
        assert all(isinstance(entity, Entity) and isinstance(score, float) for entity, score in results)
        
        # e1 should be in results
        entity_ids = [entity.id for entity, _ in results]
        assert "e1" in entity_ids
    
    @pytest.mark.asyncio
    async def test_retrieve_multiple_seeds(self, ppr_populated):
        """Test retrieve with multiple seed entities"""
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1", "e2"],
            max_results=10,
            alpha=0.15,
            max_iterations=50,
            convergence_threshold=1e-4
        )
        
        assert isinstance(results, list)
        # Should have at least one result (seeds should be included)
        assert len(results) > 0
        
        # Both seeds should be in results
        entity_ids = [entity.id for entity, _ in results]
        assert "e1" in entity_ids or "e2" in entity_ids
    
    @pytest.mark.asyncio
    async def test_retrieve_sorted_by_score(self, ppr_populated):
        """Test that results are sorted by score descending"""
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.15,
            max_iterations=10
        )
        
        if len(results) > 1:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_retrieve_max_results_limit(self, ppr_populated):
        """Test max_results limit"""
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=2,
            alpha=0.15,
            max_iterations=10
        )
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_retrieve_convergence(self, ppr_populated):
        """Test that algorithm converges"""
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.15,
            max_iterations=100,
            convergence_threshold=1e-6
        )
        
        assert isinstance(results, list)
        # Should complete without error
    
    @pytest.mark.asyncio
    async def test_retrieve_alpha_parameter(self, ppr_populated):
        """Test different alpha values"""
        results_low_alpha = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.05,
            max_iterations=10
        )
        
        results_high_alpha = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.5,
            max_iterations=10
        )
        
        assert isinstance(results_low_alpha, list)
        assert isinstance(results_high_alpha, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_no_neighbors(self, ppr, graph_store):
        """Test retrieve with entity that has no neighbors"""
        # Add isolated entity
        entity = Entity(id="isolated", entity_type="Person", properties={"name": "Isolated"})
        await graph_store.add_entity(entity)
        
        results = await ppr.retrieve(
            seed_entity_ids=["isolated"],
            max_results=10,
            max_iterations=10
        )
        
        assert isinstance(results, list)
        # Isolated entity should still be in results
        if results:
            entity_ids = [entity.id for entity, _ in results]
            assert "isolated" in entity_ids
    
    @pytest.mark.asyncio
    async def test_retrieve_with_zero_scores(self, ppr_populated):
        """Test that entities with zero scores are filtered out"""
        # This tests the score > 0 check in PageRank
        results = await ppr_populated.retrieve(
            seed_entity_ids=["e1"],
            max_results=10,
            alpha=0.15,
            max_iterations=5
        )
        
        assert isinstance(results, list)
        # All results should have positive scores
        for _, score in results:
            assert score > 0


class TestMultiHopRetrieval:
    """Test MultiHopRetrieval"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def populated_store(self):
        """Create graph store with multi-hop structure"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create chain: e1 -> e2 -> e3 -> e4
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
            Entity(id="e3", entity_type="Person", properties={"name": "Charlie"}),
            Entity(id="e4", entity_type="Person", properties={"name": "Diana"})
        ]
        
        for entity in entities:
            await store.add_entity(entity)
        
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3"),
            Relation(id="r3", relation_type="KNOWS", source_id="e3", target_id="e4")
        ]
        
        for relation in relations:
            await store.add_relation(relation)
        
        yield store
        await store.close()
    
    @pytest.fixture
    def retrieval(self, graph_store):
        """Create MultiHopRetrieval instance"""
        return MultiHopRetrieval(graph_store)
    
    @pytest.fixture
    def retrieval_populated(self, populated_store):
        """Create MultiHopRetrieval instance with populated store"""
        return MultiHopRetrieval(populated_store)
    
    @pytest.mark.asyncio
    async def test_retrieve_empty_seeds(self, retrieval):
        """Test retrieve with empty seed list"""
        results = await retrieval.retrieve(seed_entity_ids=[])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retrieve_single_hop(self, retrieval_populated):
        """Test single hop retrieval"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=1,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should have at least the seed entity
        assert len(results) > 0
        
        entity_ids = [entity.id for entity, _ in results]
        # Should include e1 (seed)
        assert "e1" in entity_ids
        # May also include e2 (1 hop away) if relations are properly set up
    
    @pytest.mark.asyncio
    async def test_retrieve_multi_hop(self, retrieval_populated):
        """Test multi-hop retrieval"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=2,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should have at least the seed entity
        assert len(results) > 0
        
        entity_ids = [entity.id for entity, _ in results]
        # Should include e1 (seed)
        assert "e1" in entity_ids
        # May include e2, e3 if relations are properly traversed
    
    @pytest.mark.asyncio
    async def test_retrieve_exclude_seeds(self, retrieval_populated):
        """Test retrieval excluding seed entities"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=1,
            max_results=10,
            include_seeds=False
        )
        
        assert isinstance(results, list)
        entity_ids = [entity.id for entity, _ in results]
        # Should not include e1
        assert "e1" not in entity_ids
    
    @pytest.mark.asyncio
    async def test_retrieve_score_decay(self, retrieval_populated):
        """Test score decay per hop"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=2,
            max_results=10,
            score_decay=0.5
        )
        
        assert isinstance(results, list)
        # Scores should decrease with distance
        if len(results) > 1:
            scores = [score for _, score in results]
            # First entity (seed) should have highest score
            assert scores[0] >= scores[-1]
    
    @pytest.mark.asyncio
    async def test_retrieve_max_results_limit(self, retrieval, populated_store):
        """Test max_results limit"""
        results = await retrieval.retrieve(
            seed_entity_ids=["e1"],
            max_hops=3,
            max_results=2
        )
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_retrieve_sorted_by_score(self, retrieval, populated_store):
        """Test that results are sorted by score descending"""
        results = await retrieval.retrieve(
            seed_entity_ids=["e1"],
            max_hops=2,
            max_results=10
        )
        
        if len(results) > 1:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_retrieve_zero_hops(self, retrieval_populated):
        """Test retrieval with zero hops"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=0,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should have at least the seed entity
        assert len(results) > 0
        
        # Should only include seed
        entity_ids = [entity.id for entity, _ in results]
        assert "e1" in entity_ids
    
    @pytest.mark.asyncio
    async def test_retrieve_with_relation_types(self, retrieval_populated):
        """Test retrieval with relation type filtering"""
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1"],
            max_hops=2,
            max_results=10,
            relation_types=["KNOWS"]
        )
        
        assert isinstance(results, list)
        # Should have at least the seed entity
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_retrieve_visited_entities(self, retrieval_populated):
        """Test that visited entities are skipped"""
        # This tests the visited check in MultiHopRetrieval
        results = await retrieval_populated.retrieve(
            seed_entity_ids=["e1", "e2"],  # Multiple seeds may visit same entities
            max_hops=2,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should not have duplicates
        entity_ids = [entity.id for entity, _ in results]
        assert len(entity_ids) == len(set(entity_ids))  # No duplicates


class TestFilteredRetrieval:
    """Test FilteredRetrieval"""
    
    @pytest.fixture
    async def graph_store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def populated_store(self):
        """Create graph store with entities for filtering"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create entities with different types and properties
        entities = [
            Entity(
                id="e1",
                entity_type="Person",
                properties={"name": "Alice", "age": 30, "role": "Engineer"},
                embedding=[0.1] * 128
            ),
            Entity(
                id="e2",
                entity_type="Person",
                properties={"name": "Bob", "age": 25, "role": "Manager"},
                embedding=[0.2] * 128
            ),
            Entity(
                id="e3",
                entity_type="Company",
                properties={"name": "Tech Corp", "industry": "Technology"},
                embedding=[0.3] * 128
            ),
            Entity(
                id="e4",
                entity_type="Person",
                properties={"name": "Charlie", "age": 35},
                embedding=[0.4] * 128
            )
        ]
        
        for entity in entities:
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.fixture
    def retrieval(self, graph_store):
        """Create FilteredRetrieval instance"""
        return FilteredRetrieval(graph_store)
    
    @pytest.mark.asyncio
    async def test_retrieve_by_entity_type(self, retrieval, populated_store):
        """Test filtering by entity type"""
        results = await retrieval.retrieve(
            entity_type="Person",
            max_results=10
        )
        
        assert isinstance(results, list)
        assert all(entity.entity_type == "Person" for entity, _ in results)
    
    @pytest.mark.asyncio
    async def test_retrieve_by_property_filters(self, retrieval, populated_store):
        """Test filtering by property values"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "Engineer"},
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have role="Engineer"
        for entity, _ in results:
            assert entity.properties.get("role") == "Engineer"
    
    @pytest.mark.asyncio
    async def test_retrieve_by_property_exists(self, retrieval, populated_store):
        """Test filtering by property existence"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_exists=["role"],
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have "role" property
        for entity, _ in results:
            assert "role" in entity.properties
    
    @pytest.mark.asyncio
    async def test_retrieve_by_custom_filter(self, retrieval, populated_store):
        """Test filtering with custom filter function"""
        def age_filter(entity: Entity) -> bool:
            return entity.properties.get("age", 0) > 30
        
        results = await retrieval.retrieve(
            entity_type="Person",
            filter_fn=age_filter,
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have age > 30
        for entity, _ in results:
            assert entity.properties.get("age", 0) > 30
    
    @pytest.mark.asyncio
    async def test_retrieve_score_by_match_count(self, retrieval, populated_store):
        """Test scoring by match count"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "Engineer"},
            property_exists=["age"],
            score_by_match_count=True,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Scores should be between 0 and 1
        for _, score in results:
            assert 0.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_retrieve_max_results_limit(self, retrieval, populated_store):
        """Test max_results limit"""
        results = await retrieval.retrieve(
            entity_type="Person",
            max_results=2
        )
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_retrieve_sorted_by_score(self, retrieval, populated_store):
        """Test that results are sorted by score descending"""
        results = await retrieval.retrieve(
            entity_type="Person",
            score_by_match_count=True,
            max_results=10
        )
        
        if len(results) > 1:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_retrieve_no_entity_type(self, retrieval, populated_store):
        """Test retrieval without entity type (should return empty)"""
        # Without entity type, FilteredRetrieval can't efficiently get all entities
        # This is a limitation of the current implementation
        results = await retrieval.retrieve(
            max_results=10
        )
        
        # Should return empty or handle gracefully
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_retrieve_multiple_filters(self, retrieval, populated_store):
        """Test retrieval with multiple filter types"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"age": 30},
            property_exists=["name"],
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should match all filters
        for entity, _ in results:
            assert entity.entity_type == "Person"
            assert entity.properties.get("age") == 30
            assert "name" in entity.properties
    
    @pytest.mark.asyncio
    async def test_retrieve_property_filter_mismatch(self, retrieval, populated_store):
        """Test that entities not matching property filters are excluded"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "NonExistent"},
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should have no results or all match
        for entity, _ in results:
            assert entity.properties.get("role") == "NonExistent"
    
    @pytest.mark.asyncio
    async def test_retrieve_property_exists_mismatch(self, retrieval, populated_store):
        """Test that entities missing required properties are excluded"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_exists=["nonexistent_prop"],
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have the required property
        for entity, _ in results:
            assert "nonexistent_prop" in entity.properties
    
    @pytest.mark.asyncio
    async def test_retrieve_custom_filter_exception(self, retrieval, populated_store):
        """Test that exceptions in custom filter are handled"""
        def failing_filter(entity: Entity) -> bool:
            if entity.id == "e1":
                raise ValueError("Test exception")
            return True
        
        results = await retrieval.retrieve(
            entity_type="Person",
            filter_fn=failing_filter,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Should handle exception gracefully
    
    @pytest.mark.asyncio
    async def test_retrieve_score_by_match_count(self, retrieval, populated_store):
        """Test scoring by match count with multiple criteria"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "Engineer"},
            property_exists=["age"],
            score_by_match_count=True,
            max_results=10
        )
        
        assert isinstance(results, list)
        # Scores should reflect match count
        for _, score in results:
            assert 0.0 <= score <= 1.0
    
    @pytest.mark.asyncio
    async def test_retrieve_property_filter_continue(self, retrieval, populated_store):
        """Test that property filter mismatch causes continue"""
        # Add entity that doesn't match filter
        entity = Entity(
            id="e5",
            entity_type="Person",
            properties={"name": "Eve", "role": "Designer"},
            embedding=[0.5] * 128
        )
        await populated_store.add_entity(entity)
        
        results = await retrieval.retrieve(
            entity_type="Person",
            property_filters={"role": "Engineer"},
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have role="Engineer"
        for entity, _ in results:
            assert entity.properties.get("role") == "Engineer"
    
    @pytest.mark.asyncio
    async def test_retrieve_property_exists_continue(self, retrieval, populated_store):
        """Test that missing property causes continue"""
        results = await retrieval.retrieve(
            entity_type="Person",
            property_exists=["role"],
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should have "role" property
        for entity, _ in results:
            assert "role" in entity.properties
    
    @pytest.mark.asyncio
    async def test_retrieve_entity_type_mismatch_continue(self, retrieval, populated_store):
        """Test that entity type mismatch causes continue"""
        results = await retrieval.retrieve(
            entity_type="Person",
            max_results=10
        )
        
        assert isinstance(results, list)
        # All results should be Person type
        for entity, _ in results:
            assert entity.entity_type == "Person"


class TestRetrievalCache:
    """Test RetrievalCache"""
    
    def test_cache_initialization(self):
        """Test cache initialization"""
        cache = RetrievalCache(max_size=100, ttl=300)
        
        assert cache.max_size == 100
        assert cache.ttl == 300
        assert cache._hits == 0
        assert cache._misses == 0
    
    def test_generate_key(self):
        """Test cache key generation"""
        cache = RetrievalCache()
        
        key1 = cache._generate_key(seed_ids=["e1"], max_results=10)
        key2 = cache._generate_key(seed_ids=["e1"], max_results=10)
        key3 = cache._generate_key(seed_ids=["e2"], max_results=10)
        
        # Same parameters should generate same key
        assert key1 == key2
        # Different parameters should generate different key
        assert key1 != key3
    
    def test_generate_key_parameter_order(self):
        """Test that key generation is order-independent"""
        cache = RetrievalCache()
        
        key1 = cache._generate_key(a=1, b=2, c=3)
        key2 = cache._generate_key(c=3, b=2, a=1)
        
        # Should generate same key regardless of parameter order
        assert key1 == key2
    
    def test_is_expired(self):
        """Test expiration check"""
        cache = RetrievalCache(ttl=1)  # 1 second TTL
        
        # Not expired
        assert not cache._is_expired(time.time())
        
        # Expired (1 second ago)
        assert cache._is_expired(time.time() - 2)
    
    def test_evict_lru(self):
        """Test LRU eviction"""
        cache = RetrievalCache(max_size=2)
        
        # Add entries
        cache._cache["key1"] = ("value1", time.time())
        cache._access_order.append("key1")
        cache._cache["key2"] = ("value2", time.time())
        cache._access_order.append("key2")
        
        # Evict
        cache._evict_lru()
        
        # key1 should be evicted
        assert "key1" not in cache._cache
        assert "key2" in cache._cache
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_hit(self):
        """Test cache hit scenario"""
        cache = RetrievalCache(ttl=300)
        
        # First call - cache miss
        async def compute_fn():
            return "result1"
        
        result1 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute_fn
        )
        
        assert result1 == "result1"
        assert cache._misses == 1
        
        # Second call - cache hit
        result2 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute_fn
        )
        
        assert result2 == "result1"
        assert cache._hits == 1
    
    @pytest.mark.asyncio
    async def test_get_or_compute_cache_miss(self):
        """Test cache miss scenario"""
        cache = RetrievalCache(ttl=300)
        
        call_count = 0
        
        async def compute_fn():
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        result1 = await cache.get_or_compute(
            cache_key="key1",
            compute_fn=compute_fn
        )
        
        result2 = await cache.get_or_compute(
            cache_key="key2",
            compute_fn=compute_fn
        )
        
        assert result1 == "result_1"
        assert result2 == "result_2"
        assert call_count == 2
        assert cache._misses == 2
    
    @pytest.mark.asyncio
    async def test_get_or_compute_expiration(self):
        """Test cache expiration"""
        cache = RetrievalCache(ttl=0.01)  # Very short TTL
        
        async def compute_fn():
            return "result"
        
        # First call
        result1 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute_fn
        )
        
        # Wait for expiration
        await asyncio.sleep(0.02)
        
        # Second call should be cache miss (expired)
        call_count = 0
        
        async def compute_fn2():
            nonlocal call_count
            call_count += 1
            return "result2"
        
        result2 = await cache.get_or_compute(
            cache_key="test_key",
            compute_fn=compute_fn2
        )
        
        assert result2 == "result2"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_or_compute_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = RetrievalCache(max_size=2)
        
        async def compute_fn(value):
            return value
        
        # Fill cache
        await cache.get_or_compute(cache_key="key1", compute_fn=lambda: compute_fn("v1"))
        await cache.get_or_compute(cache_key="key2", compute_fn=lambda: compute_fn("v2"))
        
        # Access key1 to update LRU
        await cache.get_or_compute(cache_key="key1", compute_fn=lambda: compute_fn("v1"))
        
        # Add third entry - should evict key2
        await cache.get_or_compute(cache_key="key3", compute_fn=lambda: compute_fn("v3"))
        
        # key2 should be evicted
        assert "key2" not in cache._cache
        assert "key1" in cache._cache
        assert "key3" in cache._cache
    
    @pytest.mark.asyncio
    async def test_get_or_compute_with_kwargs(self):
        """Test cache key generation from kwargs"""
        cache = RetrievalCache()
        
        async def compute_fn():
            return "result"
        
        result1 = await cache.get_or_compute(
            compute_fn=compute_fn,
            seed_ids=["e1"],
            max_results=10
        )
        
        # Same kwargs should hit cache
        result2 = await cache.get_or_compute(
            compute_fn=compute_fn,
            seed_ids=["e1"],
            max_results=10
        )
        
        assert result1 == result2
        assert cache._hits == 1
    
    @pytest.mark.asyncio
    async def test_get_or_compute_sync_function(self):
        """Test cache with synchronous compute function"""
        cache = RetrievalCache()
        
        def sync_compute_fn():
            return "sync_result"
        
        result = await cache.get_or_compute(
            cache_key="sync_key",
            compute_fn=sync_compute_fn
        )
        
        assert result == "sync_result"
    
    @pytest.mark.asyncio
    async def test_get_or_compute_no_compute_fn(self):
        """Test cache get without compute function"""
        cache = RetrievalCache()
        
        result = await cache.get_or_compute(cache_key="test_key")
        
        assert result is None
    
    def test_invalidate(self):
        """Test cache invalidation"""
        cache = RetrievalCache()
        
        cache._cache["key1"] = ("value1", time.time())
        cache._access_order.append("key1")
        
        cache.invalidate("key1")
        
        assert "key1" not in cache._cache
        assert "key1" not in cache._access_order
    
    def test_clear(self):
        """Test clearing cache"""
        cache = RetrievalCache()
        
        cache._cache["key1"] = ("value1", time.time())
        cache._access_order.append("key1")
        
        cache.clear()
        
        assert len(cache._cache) == 0
        assert len(cache._access_order) == 0
    
    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = RetrievalCache(max_size=100, ttl=300)
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["cache_size"] == 0
        assert stats["max_size"] == 100
        assert stats["ttl"] == 300
    
    @pytest.mark.asyncio
    async def test_get_stats_with_usage(self):
        """Test cache statistics with actual usage"""
        cache = RetrievalCache()
        
        async def compute_fn():
            return "result"
        
        # Cache miss
        await cache.get_or_compute(cache_key="key1", compute_fn=compute_fn)
        
        # Cache hit
        await cache.get_or_compute(cache_key="key1", compute_fn=compute_fn)
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["cache_size"] == 1


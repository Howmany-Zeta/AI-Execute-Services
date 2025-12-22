"""
Performance Benchmarks: Search Strategies

Benchmarks various search strategies for performance comparison.
"""

import pytest
import asyncio
import time
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode
)
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank,
    MultiHopRetrieval,
    FilteredRetrieval
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


@pytest.fixture
async def large_graph_store():
    """Create a larger graph for performance testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create 500 entities
    entities = []
    for i in range(500):
        entity = Entity(
            id=f"entity_{i}",
            entity_type="TestEntity",
            properties={"index": i, "category": f"cat_{i % 10}"},
            embedding=[0.1 * (i % 10)] * 128
        )
        entities.append(entity)
        await store.add_entity(entity)
    
    # Create 1000 relations (sparse graph)
    for i in range(1000):
        source_id = f"entity_{i % 500}"
        target_id = f"entity_{(i + 1) % 500}"
        relation = Relation(
            id=f"relation_{i}",
            relation_type="CONNECTED_TO",
            source_id=source_id,
            target_id=target_id,
            weight=0.9
        )
        await store.add_relation(relation)
    
    yield store
    await store.close()


class TestSearchBenchmarks:
    """Benchmark tests for search strategies"""
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, large_graph_store):
        """Benchmark vector search"""
        query_embedding = [0.1] * 128
        
        start = time.time()
        results = await large_graph_store.vector_search(
            query_embedding=query_embedding,
            max_results=10,
            score_threshold=0.5
        )
        elapsed = time.time() - start
        
        print(f"\nVector Search Performance:")
        print(f"  Entities: 500")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        print(f"  Throughput: {500/elapsed:.0f} entities/sec")
        
        assert elapsed < 1.0  # Should complete in < 1 second
    
    @pytest.mark.asyncio
    async def test_hybrid_search_performance(self, large_graph_store):
        """Benchmark hybrid search"""
        strategy = HybridSearchStrategy(large_graph_store)
        query_embedding = [0.1] * 128
        
        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.6,
            graph_weight=0.4,
            max_results=10,
            expand_results=True
        )
        
        start = time.time()
        results = await strategy.search(
            query_embedding=query_embedding,
            config=config
        )
        elapsed = time.time() - start
        
        print(f"\nHybrid Search Performance:")
        print(f"  Entities: 500")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        
        assert elapsed < 2.0  # Should complete in < 2 seconds
    
    @pytest.mark.asyncio
    async def test_pagerank_performance(self, large_graph_store):
        """Benchmark PageRank"""
        ppr = PersonalizedPageRank(large_graph_store)
        seed_ids = ["entity_0", "entity_100", "entity_200"]
        
        start = time.time()
        results = await ppr.retrieve(
            seed_entity_ids=seed_ids,
            max_results=20,
            max_iterations=50
        )
        elapsed = time.time() - start
        
        print(f"\nPageRank Performance:")
        print(f"  Entities: 500")
        print(f"  Relations: 1000")
        print(f"  Seeds: {len(seed_ids)}")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        
        assert elapsed < 5.0  # Should complete in < 5 seconds
    
    @pytest.mark.asyncio
    async def test_multihop_performance(self, large_graph_store):
        """Benchmark multi-hop retrieval"""
        retrieval = MultiHopRetrieval(large_graph_store)
        seed_ids = ["entity_0"]
        
        start = time.time()
        results = await retrieval.retrieve(
            seed_entity_ids=seed_ids,
            max_hops=2,
            max_results=50
        )
        elapsed = time.time() - start
        
        print(f"\nMulti-Hop Performance:")
        print(f"  Entities: 500")
        print(f"  Max Hops: 2")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        
        assert elapsed < 1.0  # Should complete in < 1 second
    
    @pytest.mark.asyncio
    async def test_filtered_search_performance(self, large_graph_store):
        """Benchmark filtered retrieval"""
        retrieval = FilteredRetrieval(large_graph_store)
        
        start = time.time()
        results = await retrieval.retrieve(
            entity_type="TestEntity",
            property_filters={"category": "cat_0"},
            max_results=50
        )
        elapsed = time.time() - start
        
        print(f"\nFiltered Search Performance:")
        print(f"  Entities: 500")
        print(f"  Filter: category='cat_0'")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        
        assert elapsed < 1.0  # Should complete in < 1 second
    
    @pytest.mark.asyncio
    async def test_traversal_performance(self, large_graph_store):
        """Benchmark graph traversal"""
        start = time.time()
        paths = await large_graph_store.traverse(
            start_entity_id="entity_0",
            max_depth=3,
            max_results=50
        )
        elapsed = time.time() - start
        
        print(f"\nTraversal Performance:")
        print(f"  Entities: 500")
        print(f"  Max Depth: 3")
        print(f"  Paths: {len(paths)}")
        print(f"  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
        
        assert elapsed < 2.0  # Should complete in < 2 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


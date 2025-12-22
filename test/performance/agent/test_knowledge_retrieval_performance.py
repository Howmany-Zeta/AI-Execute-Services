"""
Performance tests for KnowledgeAwareAgent knowledge retrieval (Section 8.5)

Tests for:
- 8.5.1: Benchmark retrieval latency
- 8.5.2: Measure cache hit rate improvement
- 8.5.3: Test with large knowledge graphs (10K+ entities)
"""

import pytest
import time
import statistics
from typing import List, Tuple

from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for performance testing"""
    
    def __init__(self):
        super().__init__(provider_name="mock")
        self.call_count = 0
    
    async def generate_text(
        self,
        messages: List[LLMMessage],
        model=None,
        temperature: float = 0.7,
        max_tokens=None,
        **kwargs,
    ) -> LLMResponse:
        """Generate mock response"""
        self.call_count += 1
        
        content = ""
        if messages and len(messages) > 0:
            msg = messages[-1]
            if hasattr(msg, 'content'):
                content = msg.content
            elif isinstance(msg, dict):
                content = msg.get('content', '')
        
        content_lower = content.lower()
        
        if "extract" in content_lower or "entities" in content_lower or "json" in content_lower:
            return LLMResponse(
                content='[{"id": "entity_1", "type": "Person", "properties": {"name": "Test"}, "confidence": 0.9}]',
                provider="mock",
                model=model or "mock-model",
                tokens_used=50
            )
        
        return LLMResponse(
            content="Mock response: Task completed successfully.",
            provider="mock",
            model=model or "mock-model",
            tokens_used=30
        )
    
    async def get_embeddings(self, texts: List[str], model=None):
        """Generate mock embeddings"""
        import hashlib
        embeddings = []
        embedding_dim = 3072
        for text in texts:
            text_hash = hashlib.md5(text.encode()).hexdigest()
            embedding = [float(int(text_hash[i:i+2], 16)) / 255.0 for i in range(0, min(32, len(text_hash)), 2)]
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


def generate_large_graph_store(num_entities: int, num_relations: int = None) -> Tuple[InMemoryGraphStore, List[Entity], List[Relation]]:
    """Generate a large graph store with specified number of entities"""
    if num_relations is None:
        num_relations = num_entities * 2
    
    store = InMemoryGraphStore()
    entities = []
    
    embedding_dim = 3072
    for i in range(num_entities):
        entity = Entity(
            id=f"entity_{i}",
            entity_type="Person" if i % 2 == 0 else "Company",
            properties={
                "name": f"Entity {i}",
                "index": i,
                "category": "A" if i % 3 == 0 else "B" if i % 3 == 1 else "C"
            },
            embedding=[float(i % 100) / 100.0] * embedding_dim
        )
        entities.append(entity)
    
    relations = []
    for i in range(min(num_relations, num_entities * (num_entities - 1) // 2)):
        source_idx = i % num_entities
        target_idx = (i + 1) % num_entities
        if source_idx != target_idx:
            relations.append(Relation(
                id=f"relation_{i}",
                source_id=f"entity_{source_idx}",
                target_id=f"entity_{target_idx}",
                relation_type="KNOWS" if i % 2 == 0 else "WORKS_FOR",
                properties={}
            ))
    
    return store, entities, relations


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client"""
    return MockLLMClient()


@pytest.fixture
def agent_config():
    """Create test agent configuration"""
    return AgentConfiguration(
        max_retries=3,
        timeout_seconds=30,
        enable_logging=False,
        retrieval_strategy="hybrid",
        enable_knowledge_caching=True,
        cache_ttl=300,
        max_context_size=10,
    )


@pytest.mark.performance
class TestRetrievalLatencyBenchmark:
    """Test 8.5.1: Benchmark retrieval latency"""

    @pytest.mark.asyncio
    async def test_benchmark_retrieval_latency_small_graph(self, mock_llm_client, agent_config):
        """Benchmark retrieval latency with small graph (100 entities)"""
        store, entities, relations = generate_large_graph_store(100, 200)
        await store.initialize()
        
        for entity in entities:
            await store.add_entity(entity)
        for relation in relations:
            await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            await agent._retrieve_relevant_knowledge("warmup query", {}, 1)
            
            latencies = []
            num_iterations = 10
            
            for i in range(num_iterations):
                query = f"Find information about entity_{i % 100}"
                start_time = time.time()
                await agent._retrieve_relevant_knowledge(query, {}, i + 1)
                latency = time.time() - start_time
                latencies.append(latency)
            
            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            assert avg_latency > 0
            assert min_latency > 0
            assert max_latency > 0
            
            print(f"\n{'='*60}")
            print(f"Retrieval Latency Benchmark (100 entities)")
            print(f"{'='*60}")
            print(f"Average latency: {avg_latency*1000:.2f} ms")
            print(f"Median latency: {median_latency*1000:.2f} ms")
            print(f"Min latency: {min_latency*1000:.2f} ms")
            print(f"Max latency: {max_latency*1000:.2f} ms")
            print(f"P95 latency: {p95_latency*1000:.2f} ms")
            print(f"{'='*60}\n")
            
        finally:
            await agent.shutdown()
            await store.close()

    @pytest.mark.asyncio
    async def test_benchmark_retrieval_latency_medium_graph(self, mock_llm_client, agent_config):
        """Benchmark retrieval latency with medium graph (1K entities)"""
        store, entities, relations = generate_large_graph_store(1000, 2000)
        await store.initialize()
        
        batch_size = 100
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i+batch_size]
            for entity in batch:
                await store.add_entity(entity)
        
        for i in range(0, len(relations), batch_size):
            batch = relations[i:i+batch_size]
            for relation in batch:
                await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            await agent._retrieve_relevant_knowledge("warmup query", {}, 1)
            
            latencies = []
            num_iterations = 10
            
            for i in range(num_iterations):
                query = f"Find information about entity_{i % 1000}"
                start_time = time.time()
                await agent._retrieve_relevant_knowledge(query, {}, i + 1)
                latency = time.time() - start_time
                latencies.append(latency)
            
            avg_latency = statistics.mean(latencies)
            median_latency = statistics.median(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            
            print(f"\n{'='*60}")
            print(f"Retrieval Latency Benchmark (1K entities)")
            print(f"{'='*60}")
            print(f"Average latency: {avg_latency*1000:.2f} ms")
            print(f"Median latency: {median_latency*1000:.2f} ms")
            print(f"P95 latency: {p95_latency*1000:.2f} ms")
            print(f"{'='*60}\n")
            
            assert avg_latency > 0
            
        finally:
            await agent.shutdown()
            await store.close()

    @pytest.mark.asyncio
    async def test_benchmark_different_strategies(self, mock_llm_client, agent_config):
        """Benchmark latency for different retrieval strategies"""
        store, entities, relations = generate_large_graph_store(500, 1000)
        await store.initialize()
        
        for entity in entities:
            await store.add_entity(entity)
        for relation in relations:
            await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            strategies = ["vector", "graph", "hybrid"]
            results = {}
            
            for strategy in strategies:
                agent._config.retrieval_strategy = strategy
                
                await agent._retrieve_relevant_knowledge("warmup", {}, 1)
                
                latencies = []
                for i in range(5):
                    query = f"Find entity_{i % 500}"
                    start_time = time.time()
                    await agent._retrieve_relevant_knowledge(query, {"seed_entity_ids": [f"entity_{i % 500}"]}, i + 1)
                    latency = time.time() - start_time
                    latencies.append(latency)
                
                results[strategy] = {
                    "avg": statistics.mean(latencies),
                    "median": statistics.median(latencies)
                }
            
            print(f"\n{'='*60}")
            print(f"Strategy Comparison (500 entities)")
            print(f"{'='*60}")
            for strategy, stats in results.items():
                print(f"{strategy:10s}: avg={stats['avg']*1000:6.2f} ms, median={stats['median']*1000:6.2f} ms")
            print(f"{'='*60}\n")
            
            for strategy, stats in results.items():
                assert stats['avg'] > 0
                
        finally:
            await agent.shutdown()
            await store.close()


@pytest.mark.performance
class TestCacheHitRateImprovement:
    """Test 8.5.2: Measure cache hit rate improvement"""

    @pytest.mark.asyncio
    async def test_cache_hit_rate_with_repeated_queries(self, mock_llm_client, agent_config):
        """Measure cache hit rate with repeated queries"""
        store, entities, relations = generate_large_graph_store(100, 200)
        await store.initialize()
        
        for entity in entities:
            await store.add_entity(entity)
        for relation in relations:
            await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            queries = [
                "Find information about entity_1",
                "Find information about entity_2",
                "Find information about entity_3",
            ]
            
            for query in queries:
                await agent._retrieve_relevant_knowledge(query, {}, 1)
            
            initial_cache_hits = agent._graph_metrics.cache_hits
            initial_cache_misses = agent._graph_metrics.cache_misses
            
            for query in queries:
                await agent._retrieve_relevant_knowledge(query, {}, 2)
            
            final_cache_hits = agent._graph_metrics.cache_hits
            final_cache_misses = agent._graph_metrics.cache_misses
            cache_hit_rate = agent._graph_metrics.cache_hit_rate
            
            assert final_cache_hits > initial_cache_hits
            assert final_cache_misses == initial_cache_misses
            
            print(f"\n{'='*60}")
            print(f"Cache Hit Rate Test")
            print(f"{'='*60}")
            print(f"Initial cache misses: {initial_cache_misses}")
            print(f"Final cache hits: {final_cache_hits}")
            print(f"Cache hit rate: {cache_hit_rate*100:.2f}%")
            print(f"{'='*60}\n")
            
        finally:
            await agent.shutdown()
            await store.close()

    @pytest.mark.asyncio
    async def test_cache_performance_improvement(self, mock_llm_client, agent_config):
        """Measure performance improvement from caching"""
        store, entities, relations = generate_large_graph_store(100, 200)
        await store.initialize()
        
        for entity in entities:
            await store.add_entity(entity)
        for relation in relations:
            await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            # First query - cache miss
            query1 = "Find information about entity_1"
            start_time = time.time()
            await agent._retrieve_relevant_knowledge(query1, {}, 1)
            cache_miss_time = time.time() - start_time
            
            # Second query - same query, should be cache hit
            start_time = time.time()
            await agent._retrieve_relevant_knowledge(query1, {}, 2)
            cache_hit_time = time.time() - start_time
            
            # Verify cache hit occurred
            assert agent._graph_metrics.cache_hits > 0
            
            speedup = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 1.0
            
            print(f"\n{'='*60}")
            print(f"Cache Performance")
            print(f"{'='*60}")
            print(f"Cache miss time: {cache_miss_time*1000:.2f} ms")
            print(f"Cache hit time: {cache_hit_time*1000:.2f} ms")
            print(f"Speedup: {speedup:.2f}x")
            print(f"{'='*60}\n")
            
            # Cache hit should be faster or at least not slower (allowing for timing variance)
            # In practice, cache hits are typically faster, but we allow for small variance
            assert cache_hit_time <= cache_miss_time * 1.5  # Allow 50% variance
            
        finally:
            await agent.shutdown()
            await store.close()


@pytest.mark.performance
class TestLargeKnowledgeGraph:
    """Test 8.5.3: Test with large knowledge graphs (10K+ entities)"""

    @pytest.mark.asyncio
    async def test_retrieval_with_10k_entities(self, mock_llm_client, agent_config):
        """Test retrieval performance with 10K entities"""
        print("\nGenerating 10K entity graph store...")
        store, entities, relations = generate_large_graph_store(10000, 20000)
        await store.initialize()
        
        print("Adding entities to store...")
        batch_size = 500
        for i in range(0, len(entities), batch_size):
            batch = entities[i:i+batch_size]
            for entity in batch:
                await store.add_entity(entity)
            if (i // batch_size) % 10 == 0:
                print(f"  Added {i + len(batch)} entities...")
        
        print("Adding relations to store...")
        for i in range(0, len(relations), batch_size):
            batch = relations[i:i+batch_size]
            for relation in batch:
                await store.add_relation(relation)
        
        agent = KnowledgeAwareAgent(
            agent_id="perf_agent",
            name="Performance Test Agent",
            llm_client=mock_llm_client,
            tools=[],
            config=agent_config,
            graph_store=store
        )
        await agent.initialize()
        
        try:
            print("Warming up...")
            await agent._retrieve_relevant_knowledge("warmup query", {}, 1)
            
            print("Benchmarking retrieval...")
            latencies = []
            num_queries = 5
            
            for i in range(num_queries):
                query = f"Find information about entity_{i * 1000}"
                start_time = time.time()
                entities_retrieved = await agent._retrieve_relevant_knowledge(
                    query,
                    {"seed_entity_ids": [f"entity_{i * 1000}"]},
                    i + 1
                )
                latency = time.time() - start_time
                latencies.append(latency)
                
                print(f"  Query {i+1}: {latency*1000:.2f} ms, retrieved {len(entities_retrieved)} entities")
            
            avg_latency = statistics.mean(latencies)
            max_latency = max(latencies)
            
            print(f"\n{'='*60}")
            print(f"Large Graph Performance (10K entities)")
            print(f"{'='*60}")
            print(f"Average latency: {avg_latency*1000:.2f} ms")
            print(f"Max latency: {max_latency*1000:.2f} ms")
            print(f"{'='*60}\n")
            
            assert avg_latency > 0
            assert len(entities_retrieved) > 0
            assert agent._graph_metrics.total_graph_queries > 0
            assert agent._graph_metrics.total_entities_retrieved > 0
            
        finally:
            await agent.shutdown()
            await store.close()

    @pytest.mark.asyncio
    async def test_retrieval_scalability(self, mock_llm_client, agent_config):
        """Test retrieval scalability across different graph sizes"""
        graph_sizes = [100, 1000, 5000, 10000]
        results = {}
        
        for size in graph_sizes:
            print(f"\nTesting with {size} entities...")
            store, entities, relations = generate_large_graph_store(size, size * 2)
            await store.initialize()
            
            batch_size = min(500, size)
            for i in range(0, len(entities), batch_size):
                batch = entities[i:i+batch_size]
                for entity in batch:
                    await store.add_entity(entity)
            
            agent = KnowledgeAwareAgent(
                agent_id="perf_agent",
                name="Performance Test Agent",
                llm_client=mock_llm_client,
                tools=[],
                config=agent_config,
                graph_store=store
            )
            await agent.initialize()
            
            try:
                await agent._retrieve_relevant_knowledge("warmup", {}, 1)
                
                start_time = time.time()
                await agent._retrieve_relevant_knowledge(
                    "Find entity_1",
                    {"seed_entity_ids": ["entity_1"]},
                    2
                )
                latency = time.time() - start_time
                
                results[size] = latency
                
            finally:
                await agent.shutdown()
                await store.close()
        
        print(f"\n{'='*60}")
        print(f"Scalability Results")
        print(f"{'='*60}")
        print(f"{'Graph Size':<15} {'Latency (ms)':<15}")
        print(f"{'-'*30}")
        for size, latency in sorted(results.items()):
            print(f"{size:<15} {latency*1000:<15.2f}")
        print(f"{'='*60}\n")
        
        assert len(results) == len(graph_sizes)
        for size, latency in results.items():
            assert latency > 0

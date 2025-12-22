"""
Performance Benchmarks for Graph Storage Backends

Compares performance of InMemory, SQLite, and PostgreSQL implementations
across various operations and workloads.
"""

import pytest
import asyncio
import time
import random
import string
from typing import List, Dict, Any
from pathlib import Path

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage import (
    InMemoryGraphStore,
    SQLiteGraphStore,
    PostgresGraphStore
)


# Benchmark configuration
ENTITY_COUNTS = [100, 1000, 10000]
RELATION_COUNTS = [200, 2000, 20000]
BATCH_SIZES = [100, 500, 1000]


class BenchmarkResult:
    """Container for benchmark results"""
    
    def __init__(self, name: str):
        self.name = name
        self.results: Dict[str, Dict[str, float]] = {}
    
    def add_result(self, backend: str, operation: str, duration_ms: float):
        """Add a benchmark result"""
        if backend not in self.results:
            self.results[backend] = {}
        self.results[backend][operation] = duration_ms
    
    def print_report(self):
        """Print formatted benchmark report"""
        print(f"\n{'='*80}")
        print(f"Benchmark: {self.name}")
        print(f"{'='*80}")
        
        # Get all operations
        operations = set()
        for backend_results in self.results.values():
            operations.update(backend_results.keys())
        
        # Print header
        backends = list(self.results.keys())
        print(f"\n{'Operation':<30} {' '.join(f'{b:>15}' for b in backends)}")
        print(f"{'-'*30} {' '.join('-'*15 for _ in backends)}")
        
        # Print results
        for op in sorted(operations):
            values = [self.results.get(b, {}).get(op, 0) for b in backends]
            print(f"{op:<30} {' '.join(f'{v:>12.2f} ms' for v in values)}")
        
        print(f"{'='*80}\n")


def generate_random_entities(count: int, entity_type: str = "TestEntity") -> List[Entity]:
    """Generate random test entities"""
    entities = []
    for i in range(count):
        entities.append(Entity(
            id=f"entity_{i}",
            entity_type=entity_type,
            properties={
                "name": f"Entity {i}",
                "value": random.randint(0, 1000),
                "data": ''.join(random.choices(string.ascii_letters, k=50))
            }
        ))
    return entities


def generate_random_relations(
    entities: List[Entity],
    count: int,
    relation_type: str = "TEST_REL"
) -> List[Relation]:
    """Generate random test relations"""
    relations = []
    entity_ids = [e.id for e in entities]
    
    for i in range(count):
        source = random.choice(entity_ids)
        target = random.choice(entity_ids)
        if source != target:  # Avoid self-loops
            relations.append(Relation(
                id=f"relation_{i}",
                source_id=source,
                target_id=target,
                relation_type=relation_type,
                properties={"weight": random.random()},
                weight=random.random()
            ))
    
    return relations


@pytest.mark.benchmark
class TestGraphStorageBenchmarks:
    """Performance benchmarks for graph storage backends"""
    
    @pytest.fixture
    async def inmemory_store(self):
        """Create in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def sqlite_store(self, tmp_path):
        """Create SQLite graph store"""
        db_path = tmp_path / "bench_graph.db"
        store = SQLiteGraphStore(str(db_path))
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def postgres_store(self):
        """Create PostgreSQL graph store"""
        import os
        from dotenv import load_dotenv
        
        # Try to load PostgreSQL config
        env_path = Path(__file__).parent.parent.parent / ".env.PostgreSQL"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        
        # Check if PostgreSQL is available
        if not os.getenv('DB_HOST'):
            pytest.skip("PostgreSQL not configured")
        
        try:
            store = PostgresGraphStore(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT', '5432')),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME')
            )
            await store.initialize()
            
            # Clean up any existing data
            async with store.pool.acquire() as conn:
                await conn.execute("TRUNCATE graph_relations, graph_entities CASCADE")
            
            yield store
            await store.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    @pytest.mark.asyncio
    async def test_single_entity_operations(
        self,
        inmemory_store,
        sqlite_store,
        postgres_store
    ):
        """Benchmark single entity CRUD operations"""
        result = BenchmarkResult("Single Entity CRUD Operations")
        
        for backend_name, store in [
            ("InMemory", inmemory_store),
            ("SQLite", sqlite_store),
            ("PostgreSQL", postgres_store)
        ]:
            # Add entity
            entity = Entity(
                id="test_entity",
                entity_type="TestEntity",
                properties={"name": "Test", "value": 42}
            )
            
            start = time.time()
            await store.add_entity(entity)
            result.add_result(backend_name, "add_entity", (time.time() - start) * 1000)
            
            # Get entity
            start = time.time()
            retrieved = await store.get_entity("test_entity")
            result.add_result(backend_name, "get_entity", (time.time() - start) * 1000)
            assert retrieved is not None
            
            # Update entity
            entity.properties["updated"] = True
            start = time.time()
            if hasattr(store, 'update_entity'):
                await store.update_entity(entity)
            else:
                await store.add_entity(entity)  # Upsert
            result.add_result(backend_name, "update_entity", (time.time() - start) * 1000)
            
            # Delete entity (if supported)
            if hasattr(store, 'delete_entity'):
                start = time.time()
                await store.delete_entity("test_entity")
                result.add_result(backend_name, "delete_entity", (time.time() - start) * 1000)
        
        result.print_report()
    
    @pytest.mark.asyncio
    async def test_bulk_entity_insertion(
        self,
        inmemory_store,
        sqlite_store,
        postgres_store
    ):
        """Benchmark bulk entity insertion"""
        result = BenchmarkResult("Bulk Entity Insertion")
        
        for entity_count in ENTITY_COUNTS:
            entities = generate_random_entities(entity_count)
            
            for backend_name, store in [
                ("InMemory", inmemory_store),
                ("SQLite", sqlite_store),
                ("PostgreSQL", postgres_store)
            ]:
                start = time.time()
                for entity in entities:
                    await store.add_entity(entity)
                duration = (time.time() - start) * 1000
                
                result.add_result(
                    backend_name,
                    f"insert_{entity_count}_entities",
                    duration
                )
                
                # Clean up
                if hasattr(store, 'batch_delete_entities'):
                    await store.batch_delete_entities([e.id for e in entities])
                elif hasattr(store, 'delete_entity'):
                    for entity in entities:
                        try:
                            await store.delete_entity(entity.id)
                        except:
                            pass
        
        result.print_report()
    
    @pytest.mark.asyncio
    async def test_batch_operations(self, postgres_store):
        """Benchmark batch operations (PostgreSQL only)"""
        if not hasattr(postgres_store, 'batch_add_entities'):
            pytest.skip("Batch operations not available")
        
        result = BenchmarkResult("Batch Operations (PostgreSQL)")
        
        for entity_count in [1000, 5000, 10000]:
            entities = generate_random_entities(entity_count)
            
            # Individual inserts
            start = time.time()
            for entity in entities:
                await postgres_store.add_entity(entity)
            individual_time = (time.time() - start) * 1000
            result.add_result("Individual", f"{entity_count}_entities", individual_time)
            
            # Clean up
            await postgres_store.batch_delete_entities([e.id for e in entities])
            
            # Batch insert
            start = time.time()
            await postgres_store.batch_add_entities(entities, batch_size=1000)
            batch_time = (time.time() - start) * 1000
            result.add_result("Batch", f"{entity_count}_entities", batch_time)
            
            # Calculate speedup
            speedup = individual_time / batch_time if batch_time > 0 else 0
            print(f"Batch insert {entity_count} entities: {speedup:.2f}x faster")
        
        result.print_report()
    
    @pytest.mark.asyncio
    async def test_neighbor_queries(
        self,
        inmemory_store,
        sqlite_store,
        postgres_store
    ):
        """Benchmark neighbor queries"""
        result = BenchmarkResult("Neighbor Queries")
        
        # Create test data
        entities = generate_random_entities(1000)
        relations = generate_random_relations(entities, 2000)
        
        for backend_name, store in [
            ("InMemory", inmemory_store),
            ("SQLite", sqlite_store),
            ("PostgreSQL", postgres_store)
        ]:
            # Setup data
            for entity in entities:
                await store.add_entity(entity)
            for relation in relations:
                await store.add_relation(relation)
            
            # Benchmark neighbor queries
            test_entity_ids = [f"entity_{i}" for i in range(0, 100, 10)]
            
            start = time.time()
            for entity_id in test_entity_ids:
                neighbors = await store.get_neighbors(entity_id, direction="outgoing")
            duration = (time.time() - start) * 1000
            result.add_result(backend_name, "get_neighbors_10x", duration)
        
        result.print_report()
    
    @pytest.mark.asyncio
    async def test_path_finding(
        self,
        inmemory_store,
        sqlite_store,
        postgres_store
    ):
        """Benchmark path finding operations"""
        result = BenchmarkResult("Path Finding")
        
        # Create chain: entity_0 -> entity_1 -> ... -> entity_99
        entities = generate_random_entities(100)
        relations = [
            Relation(
                id=f"rel_{i}",
                source_id=f"entity_{i}",
                target_id=f"entity_{i+1}",
                relation_type="NEXT",
                properties={},
                weight=1.0
            )
            for i in range(99)
        ]
        
        for backend_name, store in [
            ("InMemory", inmemory_store),
            ("SQLite", sqlite_store),
            ("PostgreSQL", postgres_store)
        ]:
            # Setup data
            for entity in entities:
                await store.add_entity(entity)
            for relation in relations:
                await store.add_relation(relation)
            
            # Benchmark path finding
            start = time.time()
            paths = await store.find_paths("entity_0", "entity_10", max_depth=15)
            duration = (time.time() - start) * 1000
            result.add_result(backend_name, "find_paths_depth_10", duration)
            
            start = time.time()
            paths = await store.find_paths("entity_0", "entity_50", max_depth=55)
            duration = (time.time() - start) * 1000
            result.add_result(backend_name, "find_paths_depth_50", duration)
        
        result.print_report()
    
    @pytest.mark.asyncio
    async def test_graph_stats(
        self,
        inmemory_store,
        sqlite_store,
        postgres_store
    ):
        """Benchmark graph statistics queries"""
        result = BenchmarkResult("Graph Statistics")
        
        # Create test data
        entities = generate_random_entities(1000)
        relations = generate_random_relations(entities, 2000)
        
        for backend_name, store in [
            ("InMemory", inmemory_store),
            ("SQLite", sqlite_store),
            ("PostgreSQL", postgres_store)
        ]:
            # Setup data
            for entity in entities:
                await store.add_entity(entity)
            for relation in relations:
                await store.add_relation(relation)
            
            # Benchmark stats query
            start = time.time()
            stats = await store.get_stats()
            duration = (time.time() - start) * 1000
            result.add_result(backend_name, "get_stats", duration)
            
            assert stats.get('entity_count') or stats.get('nodes') >= 1000
        
        result.print_report()


@pytest.mark.benchmark
class TestCachingPerformance:
    """Benchmark caching performance"""
    
    @pytest.mark.asyncio
    async def test_cache_hit_vs_miss(self):
        """Benchmark cache hit vs miss performance"""
        from aiecs.infrastructure.graph_storage.cache import (
            GraphStoreCache,
            GraphStoreCacheConfig
        )
        
        result = BenchmarkResult("Cache Performance")
        
        # Test with in-memory cache
        cache = GraphStoreCache(GraphStoreCacheConfig(
            enabled=True,
            ttl=300,
            redis_url=None  # Use in-memory
        ))
        await cache.initialize()
        
        # Simulate database fetch (slow)
        async def slow_fetch():
            await asyncio.sleep(0.01)  # 10ms
            return {"data": "result"}
        
        # Cache miss (first call)
        start = time.time()
        result1 = await cache.get_or_set("test_key", slow_fetch, ttl=300)
        cache_miss_time = (time.time() - start) * 1000
        result.add_result("Cache", "miss", cache_miss_time)
        
        # Cache hit (second call)
        start = time.time()
        result2 = await cache.get_or_set("test_key", slow_fetch, ttl=300)
        cache_hit_time = (time.time() - start) * 1000
        result.add_result("Cache", "hit", cache_hit_time)
        
        # Calculate speedup
        speedup = cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0
        print(f"Cache hit {speedup:.2f}x faster than cache miss")
        
        await cache.close()
        result.print_report()


if __name__ == "__main__":
    # Run benchmarks with pytest-benchmark plugin
    pytest.main([
        __file__,
        "-v",
        "-m", "benchmark",
        "--benchmark-only",
        "--benchmark-columns=min,max,mean,stddev"
    ])


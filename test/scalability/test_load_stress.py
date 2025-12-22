"""
Load and Stress Testing for Graph Storage

Tests graph storage backends under heavy load:
- Load testing: 1M+ entities, 10M+ relations
- Stress testing: Concurrent access, high-throughput scenarios
"""

import pytest
import asyncio
import time
import random
import os
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage import PostgresGraphStore


# Test configuration
LOAD_TEST_ENTITIES = 1_000_000  # 1M entities
LOAD_TEST_RELATIONS = 10_000_000  # 10M relations
STRESS_TEST_CONCURRENT = 100  # Concurrent operations
STRESS_TEST_DURATION = 60  # 60 seconds


def generate_entities(count: int, prefix: str = "entity") -> List[Entity]:
    """Generate test entities efficiently"""
    return [
        Entity(
            id=f"{prefix}_{i}",
            entity_type="TestEntity",
            properties={"index": i, "value": f"value_{i % 100}"}
        )
        for i in range(count)
    ]


def generate_relations(entity_count: int, relation_count: int) -> List[Relation]:
    """Generate test relations"""
    relations = []
    for i in range(relation_count):
        source = random.randint(0, entity_count - 1)
        target = random.randint(0, entity_count - 1)
        if source != target:
            relations.append(Relation(
                id=f"rel_{i}",
                source_id=f"entity_{source}",
                target_id=f"entity_{target}",
                relation_type="CONNECTS",
                properties={"index": i},
                weight=random.random()
            ))
    return relations


@pytest.mark.load_test
@pytest.mark.skipif(not os.getenv('RUN_LOAD_TESTS'), reason="Load tests disabled (set RUN_LOAD_TESTS=1)")
class TestLoadTesting:
    """Load testing with 1M+ entities and 10M+ relations"""
    
    @pytest.fixture
    async def postgres_store(self):
        """PostgreSQL store for load testing"""
        from dotenv import load_dotenv
        
        env_path = Path(__file__).parent.parent.parent / ".env.PostgreSQL"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        
        if not os.getenv('DB_HOST'):
            pytest.skip("PostgreSQL not configured")
        
        try:
            store = PostgresGraphStore(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT', '5432')),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME'),
                min_pool_size=10,
                max_pool_size=50
            )
            await store.initialize()
            
            # Clean up
            async with store.pool.acquire() as conn:
                await conn.execute("TRUNCATE graph_relations, graph_entities CASCADE")
            
            yield store
            await store.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    @pytest.mark.asyncio
    async def test_load_1m_entities(self, postgres_store):
        """Load test: Insert 1M entities"""
        if not hasattr(postgres_store, 'batch_add_entities'):
            pytest.skip("Batch operations required")
        
        print(f"\n{'='*60}")
        print(f"Load Test: 1M Entities")
        print(f"{'='*60}")
        
        batch_size = 50_000
        num_batches = LOAD_TEST_ENTITIES // batch_size
        
        total_time = 0
        start_mem = self._get_memory_mb()
        
        for batch_num in range(num_batches):
            offset = batch_num * batch_size
            entities = generate_entities(batch_size, prefix=f"entity_{offset}")
            
            start = time.time()
            await postgres_store.batch_add_entities(entities, batch_size=10_000, use_copy=True)
            batch_time = time.time() - start
            total_time += batch_time
            
            completed = (batch_num + 1) * batch_size
            print(f"  Progress: {completed:,}/{LOAD_TEST_ENTITIES:,} ({completed/LOAD_TEST_ENTITIES*100:.1f}%) - {batch_time:.2f}s")
        
        end_mem = self._get_memory_mb()
        mem_increase = end_mem - start_mem
        
        # Verify
        stats = await postgres_store.get_stats()
        actual_count = stats.get('entity_count', 0)
        
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Entities inserted: {actual_count:,}")
        print(f"  Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        print(f"  Average rate: {actual_count/total_time:.0f} entities/sec")
        print(f"  Memory increase: +{mem_increase:.1f}MB")
        print(f"{'='*60}\n")
        
        assert actual_count >= LOAD_TEST_ENTITIES * 0.99  # Allow 1% margin
    
    @pytest.mark.asyncio
    async def test_load_10m_relations(self, postgres_store):
        """Load test: Insert 10M relations"""
        if not hasattr(postgres_store, 'batch_add_relations'):
            pytest.skip("Batch operations required")
        
        # First, ensure we have entities
        print(f"\n{'='*60}")
        print(f"Load Test: 10M Relations")
        print(f"{'='*60}")
        
        # Create 100K entities for relations
        entity_count = 100_000
        entities = generate_entities(entity_count)
        await postgres_store.batch_add_entities(entities, batch_size=10_000)
        print(f"Created {entity_count:,} entities for relations")
        
        # Generate and insert relations
        batch_size = 100_000
        num_batches = LOAD_TEST_RELATIONS // batch_size
        
        total_time = 0
        
        for batch_num in range(num_batches):
            relations = generate_relations(entity_count, batch_size)
            
            start = time.time()
            await postgres_store.batch_add_relations(relations, batch_size=10_000, use_copy=True)
            batch_time = time.time() - start
            total_time += batch_time
            
            completed = (batch_num + 1) * batch_size
            print(f"  Progress: {completed:,}/{LOAD_TEST_RELATIONS:,} ({completed/LOAD_TEST_RELATIONS*100:.1f}%) - {batch_time:.2f}s")
        
        # Verify
        stats = await postgres_store.get_stats()
        actual_relations = stats.get('relation_count', 0)
        
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Relations inserted: {actual_relations:,}")
        print(f"  Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        print(f"  Average rate: {actual_relations/total_time:.0f} relations/sec")
        print(f"{'='*60}\n")
        
        assert actual_relations >= LOAD_TEST_RELATIONS * 0.99
    
    @pytest.mark.asyncio
    async def test_query_performance_at_scale(self, postgres_store):
        """Test query performance with 1M entities"""
        # Setup: Insert 1M entities
        if not hasattr(postgres_store, 'batch_add_entities'):
            pytest.skip("Batch operations required")
        
        print(f"\n{'='*60}")
        print(f"Query Performance Test: 1M Entities")
        print(f"{'='*60}")
        
        # Insert entities in batches
        batch_size = 100_000
        num_batches = 10  # 1M entities
        
        for batch_num in range(num_batches):
            offset = batch_num * batch_size
            entities = generate_entities(batch_size, prefix=f"entity_{offset}")
            await postgres_store.batch_add_entities(entities, batch_size=10_000)
            print(f"  Inserted batch {batch_num+1}/{num_batches}")
        
        # Test various queries
        test_queries = [
            ("get_entity", lambda: postgres_store.get_entity("entity_500000")),
            ("get_stats", lambda: postgres_store.get_stats()),
            ("get_neighbors", lambda: postgres_store.get_neighbors("entity_500000", direction="outgoing")),
        ]
        
        results = {}
        for name, query_func in test_queries:
            times = []
            for _ in range(10):
                start = time.time()
                await query_func()
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            results[name] = avg_time
            print(f"  {name}: {avg_time:.2f}ms avg (min: {min(times):.2f}ms, max: {max(times):.2f}ms)")
        
        print(f"{'='*60}\n")
        
        # Assert reasonable performance
        assert results['get_entity'] < 100  # Should be < 100ms
        assert results['get_stats'] < 1000  # Should be < 1s
    
    def _get_memory_mb(self) -> float:
        """Get current process memory usage"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0


@pytest.mark.stress_test
@pytest.mark.skipif(not os.getenv('RUN_STRESS_TESTS'), reason="Stress tests disabled (set RUN_STRESS_TESTS=1)")
class TestStressTesting:
    """Stress testing with concurrent access and high throughput"""
    
    @pytest.fixture
    async def postgres_store(self):
        """PostgreSQL store for stress testing"""
        from dotenv import load_dotenv
        
        env_path = Path(__file__).parent.parent.parent / ".env.PostgreSQL"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        
        if not os.getenv('DB_HOST'):
            pytest.skip("PostgreSQL not configured")
        
        try:
            store = PostgresGraphStore(
                host=os.getenv('DB_HOST'),
                port=int(os.getenv('DB_PORT', '5432')),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD', ''),
                database=os.getenv('DB_NAME'),
                min_pool_size=20,
                max_pool_size=100  # Higher pool for stress testing
            )
            await store.initialize()
            
            # Setup test data
            entities = generate_entities(10_000)
            await store.batch_add_entities(entities, batch_size=1000)
            
            yield store
            await store.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")
    
    @pytest.mark.asyncio
    async def test_concurrent_reads(self, postgres_store):
        """Stress test: 100 concurrent read operations"""
        print(f"\n{'='*60}")
        print(f"Stress Test: Concurrent Reads ({STRESS_TEST_CONCURRENT} concurrent)")
        print(f"{'='*60}")
        
        async def read_entity(entity_id: str):
            """Read a single entity"""
            return await postgres_store.get_entity(entity_id)
        
        # Create concurrent read tasks
        start = time.time()
        tasks = [
            read_entity(f"entity_{random.randint(0, 9999)}")
            for _ in range(STRESS_TEST_CONCURRENT)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start
        
        # Count successes and failures
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"  Completed: {successes} successes, {failures} failures")
        print(f"  Total time: {duration:.2f}s")
        print(f"  Throughput: {STRESS_TEST_CONCURRENT/duration:.0f} ops/sec")
        print(f"{'='*60}\n")
        
        # Should have high success rate
        assert successes >= STRESS_TEST_CONCURRENT * 0.95  # 95% success rate
    
    @pytest.mark.asyncio
    async def test_concurrent_writes(self, postgres_store):
        """Stress test: Concurrent write operations"""
        print(f"\n{'='*60}")
        print(f"Stress Test: Concurrent Writes ({STRESS_TEST_CONCURRENT} concurrent)")
        print(f"{'='*60}")
        
        async def write_entity(index: int):
            """Write a single entity"""
            entity = Entity(
                id=f"stress_entity_{index}",
                entity_type="StressTest",
                properties={"index": index}
            )
            return await postgres_store.add_entity(entity)
        
        # Create concurrent write tasks
        start = time.time()
        tasks = [
            write_entity(i)
            for i in range(STRESS_TEST_CONCURRENT)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start
        
        # Count successes and failures
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"  Completed: {successes} successes, {failures} failures")
        print(f"  Total time: {duration:.2f}s")
        print(f"  Throughput: {STRESS_TEST_CONCURRENT/duration:.0f} ops/sec")
        print(f"{'='*60}\n")
        
        # Should handle concurrent writes
        assert successes >= STRESS_TEST_CONCURRENT * 0.90  # 90% success rate
    
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, postgres_store):
        """Stress test: Sustained high throughput for 60 seconds"""
        print(f"\n{'='*60}")
        print(f"Stress Test: Sustained Throughput ({STRESS_TEST_DURATION}s)")
        print(f"{'='*60}")
        
        operation_count = 0
        error_count = 0
        start_time = time.time()
        end_time = start_time + STRESS_TEST_DURATION
        
        async def operation():
            """Single operation"""
            nonlocal operation_count, error_count
            try:
                entity_id = f"entity_{random.randint(0, 9999)}"
                await postgres_store.get_entity(entity_id)
                operation_count += 1
            except Exception:
                error_count += 1
        
        # Run operations for duration
        while time.time() < end_time:
            # Run batch of concurrent operations
            tasks = [operation() for _ in range(10)]
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.sleep(0.1)  # Small delay
        
        duration = time.time() - start_time
        throughput = operation_count / duration
        
        print(f"  Operations: {operation_count:,}")
        print(f"  Errors: {error_count}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {throughput:.0f} ops/sec")
        print(f"  Error rate: {error_count/operation_count*100:.2f}%" if operation_count > 0 else "  Error rate: N/A")
        print(f"{'='*60}\n")
        
        # Should maintain reasonable throughput
        assert throughput > 100  # At least 100 ops/sec
        assert error_count / operation_count < 0.05 if operation_count > 0 else True  # < 5% error rate
    
    @pytest.mark.asyncio
    async def test_mixed_workload(self, postgres_store):
        """Stress test: Mixed read/write workload"""
        print(f"\n{'='*60}")
        print(f"Stress Test: Mixed Workload")
        print(f"{'='*60}")
        
        read_count = 0
        write_count = 0
        error_count = 0
        
        async def read_op():
            """Read operation"""
            nonlocal read_count, error_count
            try:
                await postgres_store.get_entity(f"entity_{random.randint(0, 9999)}")
                read_count += 1
            except Exception:
                error_count += 1
        
        async def write_op(index: int):
            """Write operation"""
            nonlocal write_count, error_count
            try:
                entity = Entity(
                    id=f"mixed_entity_{index}",
                    entity_type="MixedTest",
                    properties={"index": index}
                )
                await postgres_store.add_entity(entity)
                write_count += 1
            except Exception:
                error_count += 1
        
        # Run mixed workload
        start = time.time()
        tasks = []
        
        # 70% reads, 30% writes
        for i in range(STRESS_TEST_CONCURRENT):
            if random.random() < 0.7:
                tasks.append(read_op())
            else:
                tasks.append(write_op(i))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        duration = time.time() - start
        
        print(f"  Reads: {read_count}")
        print(f"  Writes: {write_count}")
        print(f"  Errors: {error_count}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Total throughput: {(read_count + write_count)/duration:.0f} ops/sec")
        print(f"{'='*60}\n")
        
        # Should handle mixed workload
        assert (read_count + write_count) >= STRESS_TEST_CONCURRENT * 0.90


if __name__ == "__main__":
    # Run load tests
    # RUN_LOAD_TESTS=1 pytest test/scalability/test_load_stress.py -v -m load_test
    
    # Run stress tests
    # RUN_STRESS_TESTS=1 pytest test/scalability/test_load_stress.py -v -m stress_test
    
    pytest.main([__file__, "-v"])


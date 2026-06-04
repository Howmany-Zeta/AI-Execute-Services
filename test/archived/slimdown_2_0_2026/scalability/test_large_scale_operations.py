"""
Scalability Tests for Graph Storage

Tests graph storage backends with large datasets (1M+ entities)
to validate performance and memory usage at scale.

WARNING: These tests require significant resources:
- Memory: 4GB+ RAM
- Disk: 10GB+ free space
- Time: 10-30 minutes per test

Run with: pytest test/scalability/ -v -m scalability
"""

import pytest
import asyncio
import time
import psutil
import os
from pathlib import Path
from typing import List

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage import (
    InMemoryGraphStore,
    SQLiteGraphStore,
    PostgresGraphStore
)


# Test configuration
SMALL_SCALE = 10_000  # 10K entities
MEDIUM_SCALE = 100_000  # 100K entities
LARGE_SCALE = 1_000_000  # 1M entities

# Skip large tests by default (enable with --run-large flag)
RUN_LARGE_TESTS = False  # Set to True for full scale testing


def get_memory_usage_mb() -> float:
    """Get current process memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


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


def generate_relations(entity_count: int, relations_per_entity: int = 2) -> List[Relation]:
    """Generate test relations"""
    relations = []
    for i in range(entity_count):
        for j in range(relations_per_entity):
            target = (i + j + 1) % entity_count
            relations.append(Relation(
                id=f"rel_{i}_{j}",
                source_id=f"entity_{i}",
                target_id=f"entity_{target}",
                relation_type="CONNECTS",
                properties={"index": len(relations)},
                weight=1.0
            ))
    return relations


@pytest.mark.scalability
class TestSmallScaleOperations:
    """Test with 10K entities (runs quickly for CI/CD)"""
    
    @pytest.fixture
    async def inmemory_store(self):
        """In-memory store for small scale"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.fixture
    async def sqlite_store(self, tmp_path):
        """SQLite store for small scale"""
        db_path = tmp_path / "small_scale.db"
        store = SQLiteGraphStore(str(db_path))
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_inmemory_10k_entities(self, inmemory_store):
        """Test in-memory store with 10K entities"""
        entities = generate_entities(SMALL_SCALE)
        
        # Measure insertion time and memory
        start_mem = get_memory_usage_mb()
        start_time = time.time()
        
        for entity in entities:
            await inmemory_store.add_entity(entity)
        
        duration = time.time() - start_time
        mem_increase = get_memory_usage_mb() - start_mem
        
        # Verify
        stats = await inmemory_store.get_stats()
        assert stats.get('nodes', 0) >= SMALL_SCALE
        
        print(f"\nInMemory 10K entities:")
        print(f"  Time: {duration:.2f}s")
        print(f"  Memory: +{mem_increase:.1f}MB")
        print(f"  Rate: {SMALL_SCALE/duration:.0f} entities/sec")
    
    @pytest.mark.asyncio
    async def test_sqlite_10k_entities(self, sqlite_store):
        """Test SQLite store with 10K entities"""
        entities = generate_entities(SMALL_SCALE)
        
        start_time = time.time()
        
        for entity in entities:
            await sqlite_store.add_entity(entity)
        
        duration = time.time() - start_time
        
        # Verify
        stats = await sqlite_store.get_stats()
        assert stats.get('entity_count', 0) >= SMALL_SCALE
        
        print(f"\nSQLite 10K entities:")
        print(f"  Time: {duration:.2f}s")
        print(f"  Rate: {SMALL_SCALE/duration:.0f} entities/sec")


@pytest.mark.scalability
@pytest.mark.skipif(not RUN_LARGE_TESTS, reason="Large scale tests disabled")
class TestMediumScaleOperations:
    """Test with 100K entities"""
    
    @pytest.fixture
    async def sqlite_store(self, tmp_path):
        """SQLite store for medium scale"""
        db_path = tmp_path / "medium_scale.db"
        store = SQLiteGraphStore(str(db_path))
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_sqlite_100k_entities(self, sqlite_store):
        """Test SQLite with 100K entities"""
        print(f"\n{'='*60}")
        print(f"Medium Scale Test: 100K Entities")
        print(f"{'='*60}")
        
        # Generate in batches to avoid memory issues
        batch_size = 10_000
        total_time = 0
        
        for batch_num in range(MEDIUM_SCALE // batch_size):
            entities = generate_entities(batch_size, prefix=f"entity_{batch_num}")
            
            start_time = time.time()
            for entity in entities:
                await sqlite_store.add_entity(entity)
            
            batch_time = time.time() - start_time
            total_time += batch_time
            
            print(f"  Batch {batch_num+1}/{MEDIUM_SCALE//batch_size}: {batch_time:.2f}s")
        
        # Verify
        stats = await sqlite_store.get_stats()
        assert stats.get('entity_count', 0) >= MEDIUM_SCALE
        
        print(f"\nTotal time: {total_time:.2f}s")
        print(f"Average rate: {MEDIUM_SCALE/total_time:.0f} entities/sec")
    
    @pytest.mark.asyncio
    async def test_batch_operations_100k(self, sqlite_store):
        """Test batch operations with 100K entities"""
        if not hasattr(sqlite_store, 'batch_add_entities'):
            pytest.skip("Batch operations not available")
        
        print(f"\n{'='*60}")
        print(f"Batch Operations Test: 100K Entities")
        print(f"{'='*60}")
        
        entities = generate_entities(MEDIUM_SCALE)
        
        start_time = time.time()
        await sqlite_store.batch_add_entities(entities, batch_size=10_000)
        duration = time.time() - start_time
        
        stats = await sqlite_store.get_stats()
        assert stats.get('entity_count', 0) >= MEDIUM_SCALE
        
        print(f"Batch insert time: {duration:.2f}s")
        print(f"Rate: {MEDIUM_SCALE/duration:.0f} entities/sec")


@pytest.mark.scalability
@pytest.mark.skipif(not RUN_LARGE_TESTS, reason="Large scale tests disabled")
class TestLargeScaleOperations:
    """Test with 1M+ entities (requires PostgreSQL)"""
    
    @pytest.fixture
    async def postgres_store(self):
        """PostgreSQL store for large scale"""
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
                database=os.getenv('DB_NAME')
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
    async def test_postgres_1m_entities(self, postgres_store):
        """Test PostgreSQL with 1M entities using batch operations"""
        print(f"\n{'='*60}")
        print(f"Large Scale Test: 1M Entities")
        print(f"{'='*60}")
        
        if not hasattr(postgres_store, 'batch_add_entities'):
            pytest.skip("Batch operations required for this test")
        
        batch_size = 50_000
        num_batches = LARGE_SCALE // batch_size
        total_time = 0
        start_mem = get_memory_usage_mb()
        
        for batch_num in range(num_batches):
            # Generate batch
            offset = batch_num * batch_size
            entities = generate_entities(batch_size, prefix=f"entity_{offset}")
            
            # Insert batch
            start_time = time.time()
            await postgres_store.batch_add_entities(entities, batch_size=10_000, use_copy=True)
            batch_time = time.time() - start_time
            total_time += batch_time
            
            # Progress
            completed = (batch_num + 1) * batch_size
            print(f"  Progress: {completed:,}/{LARGE_SCALE:,} entities ({completed/LARGE_SCALE*100:.1f}%) - {batch_time:.2f}s")
            
            # Clear batch from memory
            del entities
        
        mem_increase = get_memory_usage_mb() - start_mem
        
        # Verify
        stats = await postgres_store.get_stats()
        actual_count = stats.get('entity_count', 0)
        assert actual_count >= LARGE_SCALE
        
        print(f"\n{'='*60}")
        print(f"RESULTS:")
        print(f"  Total entities: {actual_count:,}")
        print(f"  Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
        print(f"  Average rate: {actual_count/total_time:.0f} entities/sec")
        print(f"  Memory increase: +{mem_increase:.1f}MB")
        print(f"{'='*60}")
    
    @pytest.mark.asyncio
    async def test_query_performance_at_scale(self, postgres_store):
        """Test query performance with large dataset"""
        # First, insert test data (smaller set for this test)
        test_size = 100_000
        entities = generate_entities(test_size)
        
        if hasattr(postgres_store, 'batch_add_entities'):
            await postgres_store.batch_add_entities(entities, batch_size=10_000)
        else:
            pytest.skip("Batch operations required")
        
        print(f"\n{'='*60}")
        print(f"Query Performance at Scale: {test_size:,} entities")
        print(f"{'='*60}")
        
        # Test get_entity
        start = time.time()
        for i in range(0, 1000, 10):
            entity = await postgres_store.get_entity(f"entity_{i}")
            assert entity is not None
        duration = time.time() - start
        print(f"  100 get_entity(): {duration*1000:.1f}ms ({duration*10:.2f}ms avg)")
        
        # Test get_stats
        start = time.time()
        stats = await postgres_store.get_stats()
        duration = time.time() - start
        print(f"  get_stats(): {duration*1000:.1f}ms")
        assert stats.get('entity_count', 0) >= test_size


@pytest.mark.scalability
class TestPaginationAtScale:
    """Test pagination with large datasets"""
    
    @pytest.fixture
    async def populated_store(self, tmp_path):
        """SQLite store with 50K entities"""
        db_path = tmp_path / "pagination_test.db"
        store = SQLiteGraphStore(str(db_path))
        await store.initialize()
        
        # Add test data
        entities = generate_entities(50_000)
        for entity in entities:
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_cursor_pagination_performance(self, populated_store):
        """Test cursor-based pagination performance"""
        if not hasattr(populated_store, 'paginate_entities'):
            pytest.skip("Pagination not available")
        
        print(f"\n{'='*60}")
        print(f"Pagination Test: 50K entities")
        print(f"{'='*60}")
        
        page_size = 1000
        page_count = 0
        total_entities = 0
        
        start_time = time.time()
        cursor = None
        
        while True:
            page = await populated_store.paginate_entities(
                page_size=page_size,
                cursor=cursor
            )
            
            total_entities += len(page.items)
            page_count += 1
            
            if not page.page_info.has_next_page:
                break
            
            cursor = page.page_info.end_cursor
        
        duration = time.time() - start_time
        
        print(f"  Pages: {page_count}")
        print(f"  Total entities: {total_entities:,}")
        print(f"  Time: {duration:.2f}s")
        print(f"  Avg time per page: {duration/page_count*1000:.1f}ms")


@pytest.mark.scalability
class TestStreamingAtScale:
    """Test streaming export/import with large datasets"""
    
    @pytest.fixture
    async def store_with_data(self, tmp_path):
        """Store with 20K entities for streaming tests"""
        db_path = tmp_path / "streaming_test.db"
        store = SQLiteGraphStore(str(db_path))
        await store.initialize()
        
        entities = generate_entities(20_000)
        for entity in entities:
            await store.add_entity(entity)
        
        yield store, tmp_path
        await store.close()
    
    @pytest.mark.asyncio
    async def test_streaming_export(self, store_with_data):
        """Test streaming export performance"""
        store, tmp_path = store_with_data
        
        from aiecs.infrastructure.graph_storage.streaming import GraphStreamExporter
        
        exporter = GraphStreamExporter(store)
        export_file = tmp_path / "export.jsonl"
        
        start_time = time.time()
        stats = await exporter.export_to_file(
            str(export_file),
            format="jsonl",
            compress=False,
            batch_size=1000
        )
        duration = time.time() - start_time
        
        print(f"\nStreaming Export:")
        print(f"  Entities: {stats['entity_count']:,}")
        print(f"  Time: {duration:.2f}s")
        print(f"  Rate: {stats['entity_count']/duration:.0f} entities/sec")
        print(f"  File size: {export_file.stat().st_size / 1024 / 1024:.1f}MB")


if __name__ == "__main__":
    # Run small scale tests
    pytest.main([
        __file__,
        "-v",
        "-m", "scalability",
        "-k", "Small"
    ])


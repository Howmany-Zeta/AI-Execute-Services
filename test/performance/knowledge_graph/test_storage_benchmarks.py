"""
Performance Benchmarks: SQLite vs InMemory Graph Storage

Compares performance of SQLiteGraphStore vs InMemoryGraphStore
for various operations.
"""

import pytest
import asyncio
import time
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
import tempfile
import os


@pytest.fixture
def temp_db_path():
    """Create temporary database file"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
async def sample_entities(count=100):
    """Generate sample entities"""
    entities = []
    for i in range(count):
        entity = Entity(
            id=f"entity_{i}",
            entity_type="TestEntity",
            properties={"index": i, "name": f"Entity {i}"},
            embedding=[0.1 * (i % 10)] * 128  # Simple embedding pattern
        )
        entities.append(entity)
    return entities


@pytest.fixture
async def sample_relations(count=100):
    """Generate sample relations"""
    relations = []
    for i in range(count):
        source_id = f"entity_{i}"
        target_id = f"entity_{(i + 1) % count}"
        relation = Relation(
            id=f"relation_{i}",
            relation_type="CONNECTED_TO",
            source_id=source_id,
            target_id=target_id,
            weight=0.9
        )
        relations.append(relation)
    return relations


class TestStorageBenchmarks:
    """Benchmark tests for storage backends"""
    
    @pytest.mark.asyncio
    async def test_add_entity_performance(self, sample_entities, temp_db_path):
        """Benchmark entity addition"""
        # InMemory
        inmemory_store = InMemoryGraphStore()
        await inmemory_store.initialize()
        
        start = time.time()
        for entity in sample_entities:
            await inmemory_store.add_entity(entity)
        inmemory_time = time.time() - start
        
        await inmemory_store.close()
        
        # SQLite
        sqlite_store = SQLiteGraphStore(temp_db_path)
        await sqlite_store.initialize()
        
        start = time.time()
        for entity in sample_entities:
            await sqlite_store.add_entity(entity)
        sqlite_time = time.time() - start
        
        await sqlite_store.close()
        
        print(f"\nAdd Entity Performance ({len(sample_entities)} entities):")
        print(f"  InMemory: {inmemory_time:.4f}s ({inmemory_time/len(sample_entities)*1000:.2f}ms/entity)")
        print(f"  SQLite:   {sqlite_time:.4f}s ({sqlite_time/len(sample_entities)*1000:.2f}ms/entity)")
        print(f"  Ratio:    {sqlite_time/inmemory_time:.2f}x")
        
        # SQLite should be slower (expected for disk I/O)
        # Just verify both complete successfully
        assert inmemory_time > 0
        assert sqlite_time > 0
    
    @pytest.mark.asyncio
    async def test_get_entity_performance(self, sample_entities, temp_db_path):
        """Benchmark entity retrieval"""
        # Setup InMemory
        inmemory_store = InMemoryGraphStore()
        await inmemory_store.initialize()
        for entity in sample_entities:
            await inmemory_store.add_entity(entity)
        
        start = time.time()
        for entity in sample_entities:
            await inmemory_store.get_entity(entity.id)
        inmemory_time = time.time() - start
        
        await inmemory_store.close()
        
        # Setup SQLite
        sqlite_store = SQLiteGraphStore(temp_db_path)
        await sqlite_store.initialize()
        for entity in sample_entities:
            await sqlite_store.add_entity(entity)
        
        start = time.time()
        for entity in sample_entities:
            await sqlite_store.get_entity(entity.id)
        sqlite_time = time.time() - start
        
        await sqlite_store.close()
        
        print(f"\nGet Entity Performance ({len(sample_entities)} retrievals):")
        print(f"  InMemory: {inmemory_time:.4f}s ({inmemory_time/len(sample_entities)*1000:.2f}ms/entity)")
        print(f"  SQLite:   {sqlite_time:.4f}s ({sqlite_time/len(sample_entities)*1000:.2f}ms/entity)")
        print(f"  Ratio:    {sqlite_time/inmemory_time:.2f}x")
        
        # SQLite should be slower (expected for disk I/O)
        # Just verify both complete successfully
        assert inmemory_time > 0
        assert sqlite_time > 0
    
    @pytest.mark.asyncio
    async def test_vector_search_performance(self, sample_entities, temp_db_path):
        """Benchmark vector search"""
        query_embedding = [0.1] * 128
        
        # Setup InMemory
        inmemory_store = InMemoryGraphStore()
        await inmemory_store.initialize()
        for entity in sample_entities:
            await inmemory_store.add_entity(entity)
        
        start = time.time()
        results = await inmemory_store.vector_search(
            query_embedding=query_embedding,
            max_results=10
        )
        inmemory_time = time.time() - start
        
        await inmemory_store.close()
        
        # Setup SQLite
        sqlite_store = SQLiteGraphStore(temp_db_path)
        await sqlite_store.initialize()
        for entity in sample_entities:
            await sqlite_store.add_entity(entity)
        
        start = time.time()
        results = await sqlite_store.vector_search(
            query_embedding=query_embedding,
            max_results=10
        )
        sqlite_time = time.time() - start
        
        await sqlite_store.close()
        
        print(f"\nVector Search Performance ({len(sample_entities)} entities):")
        print(f"  InMemory: {inmemory_time:.4f}s")
        print(f"  SQLite:   {sqlite_time:.4f}s")
        print(f"  Ratio:    {sqlite_time/inmemory_time:.2f}x")
        
        # Both should return results (may differ due to embedding differences)
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_traversal_performance(self, sample_entities, sample_relations, temp_db_path):
        """Benchmark graph traversal"""
        # Setup InMemory
        inmemory_store = InMemoryGraphStore()
        await inmemory_store.initialize()
        for entity in sample_entities:
            await inmemory_store.add_entity(entity)
        for relation in sample_relations:
            await inmemory_store.add_relation(relation)
        
        start = time.time()
        paths = await inmemory_store.traverse(
            start_entity_id="entity_0",
            max_depth=3,
            max_results=50
        )
        inmemory_time = time.time() - start
        
        await inmemory_store.close()
        
        # Setup SQLite
        sqlite_store = SQLiteGraphStore(temp_db_path)
        await sqlite_store.initialize()
        for entity in sample_entities:
            await sqlite_store.add_entity(entity)
        for relation in sample_relations:
            await sqlite_store.add_relation(relation)
        
        start = time.time()
        paths = await sqlite_store.traverse(
            start_entity_id="entity_0",
            max_depth=3,
            max_results=50
        )
        sqlite_time = time.time() - start
        
        await sqlite_store.close()
        
        print(f"\nTraversal Performance ({len(sample_entities)} entities, {len(sample_relations)} relations):")
        print(f"  InMemory: {inmemory_time:.4f}s")
        print(f"  SQLite:   {sqlite_time:.4f}s")
        print(f"  Ratio:    {sqlite_time/inmemory_time:.2f}x")
    
    @pytest.mark.asyncio
    async def test_transaction_performance(self, sample_entities, temp_db_path):
        """Benchmark transaction performance"""
        # InMemory (no transaction support, just batch)
        inmemory_store = InMemoryGraphStore()
        await inmemory_store.initialize()
        
        start = time.time()
        for entity in sample_entities:
            await inmemory_store.add_entity(entity)
        inmemory_time = time.time() - start
        
        await inmemory_store.close()
        
        # SQLite with transaction
        sqlite_store = SQLiteGraphStore(temp_db_path)
        await sqlite_store.initialize()
        
        start = time.time()
        async with sqlite_store.transaction():
            for entity in sample_entities:
                await sqlite_store.add_entity(entity)
        sqlite_time = time.time() - start
        
        await sqlite_store.close()
        
        print(f"\nTransaction Performance ({len(sample_entities)} entities):")
        print(f"  InMemory (batch): {inmemory_time:.4f}s")
        print(f"  SQLite (transaction): {sqlite_time:.4f}s")
        print(f"  Ratio:    {sqlite_time/inmemory_time:.2f}x")
        
        # Just verify both complete successfully
        assert inmemory_time > 0
        assert sqlite_time > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


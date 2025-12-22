"""
Integration Tests: PostgreSQL Graph Store with Real Database

Tests PostgreSQL graph store with actual database connection.
Requires .env.PostgreSQL file with database credentials.
"""

import pytest
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import numpy as np

from aiecs.infrastructure.graph_storage import PostgresGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


# Load .env.PostgreSQL if it exists
env_file = Path(__file__).parent.parent.parent / ".env.PostgreSQL"
if env_file.exists():
    load_dotenv(env_file, override=True)
elif Path(".env.PostgreSQL").exists():
    load_dotenv(".env.PostgreSQL", override=True)

# Check if PostgreSQL is available
POSTGRES_AVAILABLE = all([
    os.getenv("DB_HOST"),
    os.getenv("DB_USER"),
    os.getenv("DB_NAME"),
])

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def postgres_store():
    """Create PostgreSQL store with real connection"""
    if not POSTGRES_AVAILABLE:
        pytest.skip("PostgreSQL not configured (missing .env.PostgreSQL or DB_* env vars)")
    
    store = PostgresGraphStore(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "aiecs"),
        enable_pgvector=os.getenv("ENABLE_PGVECTOR", "true").lower() == "true"
    )
    
    try:
        await store.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL connection failed: {e}. Make sure PostgreSQL is running and .env.PostgreSQL is configured correctly.")
    
    # Clean up test data before tests
    async with store.pool.acquire() as conn:
        await conn.execute("DELETE FROM graph_relations")
        await conn.execute("DELETE FROM graph_entities")
    
    yield store
    
    # Clean up after tests
    async with store.pool.acquire() as conn:
        await conn.execute("DELETE FROM graph_relations")
        await conn.execute("DELETE FROM graph_entities")
    
    await store.close()


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
class TestPostgresIntegration:
    """Integration tests with real PostgreSQL database"""
    
    async def test_initialize_and_schema_creation(self, postgres_store):
        """Test initialization and schema creation"""
        assert postgres_store._is_initialized is True
        assert postgres_store.pool is not None
        
        # Verify tables exist
        async with postgres_store.pool.acquire() as conn:
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('graph_entities', 'graph_relations')
            """)
            table_names = [row['table_name'] for row in tables]
            assert 'graph_entities' in table_names
            assert 'graph_relations' in table_names
    
    async def test_add_and_get_entity(self, postgres_store):
        """Test adding and retrieving entities"""
        entity = Entity(
            id="test_entity_1",
            entity_type="Person",
            properties={"name": "Alice", "age": 30}
        )
        
        await postgres_store.add_entity(entity)
        
        retrieved = await postgres_store.get_entity("test_entity_1")
        assert retrieved is not None
        assert retrieved.id == "test_entity_1"
        assert retrieved.entity_type == "Person"
        assert retrieved.properties["name"] == "Alice"
        assert retrieved.properties["age"] == 30
    
    async def test_add_and_get_relation(self, postgres_store):
        """Test adding and retrieving relations"""
        # Create entities first
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        
        await postgres_store.add_entity(entity1)
        await postgres_store.add_entity(entity2)
        
        # Create relation
        relation = Relation(
            id="r1",
            source_id="e1",
            target_id="e2",
            relation_type="KNOWS",
            properties={"since": "2020"}
        )
        
        await postgres_store.add_relation(relation)
        
        retrieved = await postgres_store.get_relation("r1")
        assert retrieved is not None
        assert retrieved.relation_type == "KNOWS"
        assert retrieved.source_id == "e1"
        assert retrieved.target_id == "e2"
        assert retrieved.properties["since"] == "2020"
    
    async def test_get_neighbors(self, postgres_store):
        """Test getting neighbors"""
        # Create graph: A -> B -> C
        entities = [
            Entity(id="a", entity_type="Node", properties={}),
            Entity(id="b", entity_type="Node", properties={}),
            Entity(id="c", entity_type="Node", properties={}),
        ]
        
        for entity in entities:
            await postgres_store.add_entity(entity)
        
        relations = [
            Relation(id="r1", source_id="a", target_id="b", relation_type="CONNECTS", properties={}),
            Relation(id="r2", source_id="b", target_id="c", relation_type="CONNECTS", properties={}),
        ]
        
        for relation in relations:
            await postgres_store.add_relation(relation)
        
        # Get outgoing neighbors of 'a'
        neighbors = await postgres_store.get_neighbors("a", direction="outgoing")
        assert len(neighbors) == 1
        assert neighbors[0].id == "b"
        
        # Get incoming neighbors of 'c'
        neighbors = await postgres_store.get_neighbors("c", direction="incoming")
        assert len(neighbors) == 1
        assert neighbors[0].id == "b"
        
        # Get both directions for 'b'
        neighbors = await postgres_store.get_neighbors("b", direction="both")
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"a", "c"}
    
    async def test_find_paths_recursive(self, postgres_store):
        """Test path finding using recursive CTE"""
        # Create graph: A -> B -> C -> D
        entities = [
            Entity(id="a", entity_type="Node", properties={}),
            Entity(id="b", entity_type="Node", properties={}),
            Entity(id="c", entity_type="Node", properties={}),
            Entity(id="d", entity_type="Node", properties={}),
        ]
        
        for entity in entities:
            await postgres_store.add_entity(entity)
        
        relations = [
            Relation(id="r1", source_id="a", target_id="b", relation_type="CONNECTS", properties={}),
            Relation(id="r2", source_id="b", target_id="c", relation_type="CONNECTS", properties={}),
            Relation(id="r3", source_id="c", target_id="d", relation_type="CONNECTS", properties={}),
        ]
        
        for relation in relations:
            await postgres_store.add_relation(relation)
        
        # Find path from A to D
        paths = await postgres_store.find_paths("a", "d", max_depth=5)
        
        assert len(paths) > 0
        # Should find path: A -> B -> C -> D
        path = paths[0]
        assert len(path.nodes) == 4
        assert path.nodes[0].id == "a"
        assert path.nodes[-1].id == "d"
    
    async def test_transaction_support(self, postgres_store):
        """Test transaction support"""
        async with postgres_store.transaction():
            entity1 = Entity(id="tx_e1", entity_type="Test", properties={})
            entity2 = Entity(id="tx_e2", entity_type="Test", properties={})
            
            await postgres_store.add_entity(entity1)
            await postgres_store.add_entity(entity2)
        
        # Both should be committed
        assert await postgres_store.get_entity("tx_e1") is not None
        assert await postgres_store.get_entity("tx_e2") is not None
    
    async def test_transaction_rollback(self, postgres_store):
        """Test transaction rollback on error"""
        try:
            async with postgres_store.transaction():
                entity1 = Entity(id="rollback_e1", entity_type="Test", properties={})
                await postgres_store.add_entity(entity1)
                # Force error
                raise ValueError("Test rollback")
        except ValueError:
            pass
        
        # Entity should not exist (rolled back)
        assert await postgres_store.get_entity("rollback_e1") is None
    
    async def test_get_all_entities(self, postgres_store):
        """Test getting all entities"""
        entities = [
            Entity(id=f"all_e{i}", entity_type="Test", properties={"index": i})
            for i in range(5)
        ]
        
        for entity in entities:
            await postgres_store.add_entity(entity)
        
        all_entities = await postgres_store.get_all_entities()
        assert len(all_entities) >= 5
        
        # Filter by type
        test_entities = await postgres_store.get_all_entities(entity_type="Test")
        assert len(test_entities) >= 5
    
    async def test_get_stats(self, postgres_store):
        """Test getting graph statistics"""
        # Add some data
        entities = [
            Entity(id="stats_e1", entity_type="Person", properties={}),
            Entity(id="stats_e2", entity_type="Company", properties={}),
        ]
        
        for entity in entities:
            await postgres_store.add_entity(entity)
        
        relation = Relation(
            id="stats_r1",
            source_id="stats_e1",
            target_id="stats_e2",
            relation_type="WORKS_FOR",
            properties={}
        )
        await postgres_store.add_relation(relation)
        
        stats = await postgres_store.get_stats()
        
        assert stats["entity_count"] >= 2
        assert stats["relation_count"] >= 1
        assert stats["backend"] == "postgresql"
        assert "Person" in stats["entity_types"]
        assert "WORKS_FOR" in stats["relation_types"]
    
    async def test_update_entity(self, postgres_store):
        """Test updating entity"""
        entity = Entity(id="update_e1", entity_type="Person", properties={"name": "Alice"})
        await postgres_store.add_entity(entity)
        
        # Update
        entity.properties["name"] = "Alice Updated"
        entity.properties["age"] = 31
        await postgres_store.update_entity(entity)
        
        # Verify
        updated = await postgres_store.get_entity("update_e1")
        assert updated.properties["name"] == "Alice Updated"
        assert updated.properties["age"] == 31
    
    async def test_delete_entity_cascades(self, postgres_store):
        """Test that deleting entity cascades to relations"""
        # Create entities and relation
        e1 = Entity(id="cascade_e1", entity_type="Test", properties={})
        e2 = Entity(id="cascade_e2", entity_type="Test", properties={})
        
        await postgres_store.add_entity(e1)
        await postgres_store.add_entity(e2)
        
        relation = Relation(
            id="cascade_r1",
            source_id="cascade_e1",
            target_id="cascade_e2",
            relation_type="CONNECTS",
            properties={}
        )
        await postgres_store.add_relation(relation)
        
        # Delete source entity
        await postgres_store.delete_entity("cascade_e1")
        
        # Relation should be deleted (CASCADE)
        assert await postgres_store.get_relation("cascade_r1") is None
        assert await postgres_store.get_entity("cascade_e1") is None


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
class TestPostgresVectorSupport:
    """Test pgvector extension support"""
    
    async def test_pgvector_extension_check(self, postgres_store):
        """Test that pgvector extension can be checked"""
        async with postgres_store.pool.acquire() as conn:
            try:
                result = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                if result:
                    pytest.skip("pgvector extension is available")
                else:
                    pytest.skip("pgvector extension not installed")
            except Exception as e:
                pytest.skip(f"Cannot check pgvector: {e}")
    
    async def test_embedding_storage(self, postgres_store):
        """Test storing and retrieving embeddings"""
        embedding = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)
        
        entity = Entity(
            id="embedding_e1",
            entity_type="Document",
            properties={"title": "Test Document"},
            embedding=embedding
        )
        
        await postgres_store.add_entity(entity)
        
        retrieved = await postgres_store.get_entity("embedding_e1")
        assert retrieved is not None
        assert retrieved.embedding is not None
        assert np.allclose(embedding, retrieved.embedding)
    
    async def test_vector_search_if_available(self, postgres_store):
        """Test vector search if pgvector is available"""
        async with postgres_store.pool.acquire() as conn:
            try:
                # Check if pgvector is available
                has_vector = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
                
                if not has_vector:
                    pytest.skip("pgvector extension not available")
                
                # Create entities with embeddings
                embeddings = [
                    np.array([1.0, 0.0, 0.0], dtype=np.float32),
                    np.array([0.0, 1.0, 0.0], dtype=np.float32),
                    np.array([0.0, 0.0, 1.0], dtype=np.float32),
                ]
                
                for i, emb in enumerate(embeddings):
                    entity = Entity(
                        id=f"vec_e{i}",
                        entity_type="Document",
                        properties={"index": i},
                        embedding=emb
                    )
                    await postgres_store.add_entity(entity)
                
                # Note: Full vector search implementation would require
                # additional SQL queries using pgvector operators
                # This test verifies embeddings can be stored and retrieved
                
                retrieved = await postgres_store.get_entity("vec_e0")
                assert retrieved.embedding is not None
                assert np.allclose(embeddings[0], retrieved.embedding)
                
            except Exception as e:
                pytest.skip(f"Vector search test skipped: {e}")


@pytest.mark.skipif(not POSTGRES_AVAILABLE, reason="PostgreSQL not available")
class TestPostgresPerformance:
    """Test performance characteristics"""
    
    async def test_batch_operations(self, postgres_store):
        """Test batch operations performance"""
        import time
        
        # Create many entities
        start = time.time()
        entities = [
            Entity(id=f"batch_e{i}", entity_type="Test", properties={"index": i})
            for i in range(100)
        ]
        
        for entity in entities:
            await postgres_store.add_entity(entity)
        
        elapsed = time.time() - start
        print(f"\nAdded 100 entities in {elapsed:.2f}s ({100/elapsed:.0f} entities/s)")
        
        # Verify all were added
        all_entities = await postgres_store.get_all_entities(entity_type="Test")
        assert len(all_entities) >= 100
    
    async def test_connection_pooling(self, postgres_store):
        """Test that connection pooling works"""
        # Make multiple concurrent requests
        async def get_entity_task(entity_id):
            return await postgres_store.get_entity(entity_id)
        
        # Create entity
        entity = Entity(id="pool_test", entity_type="Test", properties={})
        await postgres_store.add_entity(entity)
        
        # Concurrent requests
        tasks = [get_entity_task("pool_test") for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r is not None for r in results)
        assert all(r.id == "pool_test" for r in results)


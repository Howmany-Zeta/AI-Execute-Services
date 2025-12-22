"""
Integration tests for SQLiteGraphStore

Tests the SQLite implementation of the GraphStore interface:
- Tier 1 methods are implemented with SQL
- Tier 2 methods work via defaults and optimizations
- Persistence across sessions
- Transaction support
"""

import pytest
import tempfile
import os
from pathlib import Path

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore


@pytest.fixture
async def graph_store():
    """Fixture providing initialized SQLite graph store (in-memory)"""
    store = SQLiteGraphStore(":memory:")
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def file_based_store():
    """Fixture providing file-based SQLite graph store"""
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        store = SQLiteGraphStore(db_path)
        await store.initialize()
        yield store
        await store.close()
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


@pytest.fixture
async def populated_store(graph_store):
    """Fixture with pre-populated graph"""
    # Create entities
    alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    charlie = Entity(id="charlie", entity_type="Person", properties={"name": "Charlie"})
    dave = Entity(id="dave", entity_type="Person", properties={"name": "Dave"})
    
    await graph_store.add_entity(alice)
    await graph_store.add_entity(bob)
    await graph_store.add_entity(charlie)
    await graph_store.add_entity(dave)
    
    # Create relations: alice -> bob -> charlie -> dave
    await graph_store.add_relation(Relation(
        id="r1", relation_type="KNOWS", source_id="alice", target_id="bob"
    ))
    await graph_store.add_relation(Relation(
        id="r2", relation_type="KNOWS", source_id="bob", target_id="charlie"
    ))
    await graph_store.add_relation(Relation(
        id="r3", relation_type="KNOWS", source_id="charlie", target_id="dave"
    ))
    
    # Add a branch: alice -> dave (direct connection)
    await graph_store.add_relation(Relation(
        id="r4", relation_type="FRIENDS", source_id="alice", target_id="dave"
    ))
    
    return graph_store


class TestSQLiteStoreTier1:
    """Test Tier 1 (Basic) operations"""
    
    @pytest.mark.asyncio
    async def test_initialize_and_close(self):
        """Test store initialization and cleanup"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        assert store._is_initialized is True
        
        await store.close()
        assert store._is_initialized is False
    
    @pytest.mark.asyncio
    async def test_add_and_get_entity(self, graph_store):
        """Test entity CRUD operations"""
        entity = Entity(
            id="test_1",
            entity_type="Person",
            properties={"name": "Test User"}
        )
        
        # Add entity
        await graph_store.add_entity(entity)
        
        # Get entity
        retrieved = await graph_store.get_entity("test_1")
        assert retrieved is not None
        assert retrieved.id == "test_1"
        assert retrieved.properties["name"] == "Test User"
        
        # Get non-existent entity
        none_entity = await graph_store.get_entity("non_existent")
        assert none_entity is None
    
    @pytest.mark.asyncio
    async def test_add_duplicate_entity(self, graph_store):
        """Test that duplicate entity IDs raise error"""
        entity1 = Entity(id="test_1", entity_type="Person")
        entity2 = Entity(id="test_1", entity_type="Person")
        
        await graph_store.add_entity(entity1)
        
        with pytest.raises(ValueError, match="already exists"):
            await graph_store.add_entity(entity2)
    
    @pytest.mark.asyncio
    async def test_add_and_get_relation(self, graph_store):
        """Test relation CRUD operations"""
        # Add entities first
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        await graph_store.add_entity(entity1)
        await graph_store.add_entity(entity2)
        
        # Add relation
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        await graph_store.add_relation(relation)
        
        # Get relation
        retrieved = await graph_store.get_relation("r1")
        assert retrieved is not None
        assert retrieved.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_add_relation_invalid_entities(self, graph_store):
        """Test that adding relation with non-existent entities fails"""
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="non_existent_1",
            target_id="non_existent_2"
        )
        
        with pytest.raises(ValueError, match="does not exist"):
            await graph_store.add_relation(relation)
    
    @pytest.mark.asyncio
    async def test_get_neighbors(self, populated_store):
        """Test getting neighboring entities"""
        # Get Bob's outgoing neighbors (should be Charlie)
        neighbors = await populated_store.get_neighbors("bob", direction="outgoing")
        assert len(neighbors) == 1
        assert neighbors[0].id == "charlie"
        
        # Get Charlie's incoming neighbors (should be Bob)
        neighbors = await populated_store.get_neighbors("charlie", direction="incoming")
        assert len(neighbors) == 1
        assert neighbors[0].id == "bob"
        
        # Get Alice's neighbors both ways
        neighbors = await populated_store.get_neighbors("alice", direction="both")
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert "bob" in neighbor_ids
        assert "dave" in neighbor_ids
    
    @pytest.mark.asyncio
    async def test_get_neighbors_filtered(self, populated_store):
        """Test getting neighbors filtered by relation type"""
        # Alice has both KNOWS and FRIENDS relations
        # Filter for KNOWS only
        neighbors = await populated_store.get_neighbors(
            "alice",
            relation_type="KNOWS",
            direction="outgoing"
        )
        assert len(neighbors) == 1
        assert neighbors[0].id == "bob"
        
        # Filter for FRIENDS only
        neighbors = await populated_store.get_neighbors(
            "alice",
            relation_type="FRIENDS",
            direction="outgoing"
        )
        assert len(neighbors) == 1
        assert neighbors[0].id == "dave"
    
    @pytest.mark.asyncio
    async def test_entity_with_embedding(self, graph_store):
        """Test entity with vector embedding"""
        entity = Entity(
            id="e1",
            entity_type="Document",
            properties={"title": "Test Doc"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        
        await graph_store.add_entity(entity)
        
        retrieved = await graph_store.get_entity("e1")
        assert retrieved is not None
        assert retrieved.embedding is not None
        assert len(retrieved.embedding) == 5
        assert abs(retrieved.embedding[0] - 0.1) < 0.001


class TestSQLiteStoreTier2:
    """Test Tier 2 (Advanced) operations"""
    
    @pytest.mark.asyncio
    async def test_traverse(self, populated_store):
        """Test graph traversal (Tier 2 method)"""
        # Traverse from Alice, should find Bob, Charlie, Dave
        paths = await populated_store.traverse(
            start_entity_id="alice",
            max_depth=3,
            max_results=10
        )
        
        assert len(paths) > 0
        # Should have found paths to downstream entities
        entity_ids_in_paths = set()
        for path in paths:
            entity_ids_in_paths.update(path.get_entity_ids())
        
        # At minimum should include alice's direct neighbors
        assert "bob" in entity_ids_in_paths or "dave" in entity_ids_in_paths
    
    @pytest.mark.asyncio
    async def test_find_paths(self, populated_store):
        """Test path finding between entities (Tier 2 method)"""
        # Find paths from alice to dave
        paths = await populated_store.find_paths(
            source_entity_id="alice",
            target_entity_id="dave",
            max_depth=5,
            max_paths=10
        )
        
        assert len(paths) > 0
        
        # Should find at least the direct path: alice -> dave (FRIENDS)
        # The default BFS implementation may or may not find all paths
        path_lengths = [path.length for path in paths]
        assert 1 in path_lengths  # Direct path must be found
        
        # Verify all paths are valid
        for path in paths:
            assert path.start_entity.id == "alice"
            assert path.end_entity.id == "dave"
            # Path length should be reasonable
            assert path.length > 0 and path.length <= 5
    
    @pytest.mark.asyncio
    async def test_subgraph_query(self, populated_store):
        """Test subgraph extraction (Tier 2 method)"""
        # Extract subgraph with alice, bob, charlie
        entities, relations = await populated_store.subgraph_query(
            entity_ids=["alice", "bob", "charlie"],
            include_relations=True
        )
        
        assert len(entities) == 3
        entity_ids = {e.id for e in entities}
        assert entity_ids == {"alice", "bob", "charlie"}
        
        # Should have relations between them
        assert len(relations) > 0
    
    @pytest.mark.asyncio
    async def test_vector_search(self, graph_store):
        """Test vector search (Tier 2 method with SQL optimization)"""
        # Add entities with embeddings
        e1 = Entity(id="e1", entity_type="Doc", properties={}, embedding=[1.0, 0.0, 0.0])
        e2 = Entity(id="e2", entity_type="Doc", properties={}, embedding=[0.9, 0.1, 0.0])
        e3 = Entity(id="e3", entity_type="Doc", properties={}, embedding=[0.0, 1.0, 0.0])
        
        await graph_store.add_entity(e1)
        await graph_store.add_entity(e2)
        await graph_store.add_entity(e3)
        
        # Search for vectors similar to [1.0, 0.0, 0.0]
        results = await graph_store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            max_results=2
        )
        
        assert len(results) == 2
        # e1 should be most similar, e2 second
        assert results[0][0].id == "e1"
        assert results[1][0].id == "e2"
    
    @pytest.mark.asyncio
    async def test_execute_query_entity_lookup(self, populated_store):
        """Test executing entity lookup query (Tier 2 method)"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="alice"
        )
        
        result = await populated_store.execute_query(query)
        
        assert result.has_results
        assert result.entity_count == 1
        assert result.entities[0].id == "alice"
        assert result.execution_time_ms is not None


class TestSQLitePersistence:
    """Test SQLite persistence across sessions"""
    
    @pytest.mark.asyncio
    async def test_persistence_across_sessions(self):
        """Test that data persists across store open/close cycles"""
        # Create temporary database file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
            db_path = f.name
        
        try:
            # Session 1: Create store, add data, close
            store1 = SQLiteGraphStore(db_path)
            await store1.initialize()
            
            entity = Entity(id="e1", entity_type="Test", properties={"value": 42})
            await store1.add_entity(entity)
            
            await store1.close()
            
            # Session 2: Open same database, verify data exists
            store2 = SQLiteGraphStore(db_path)
            await store2.initialize()
            
            retrieved = await store2.get_entity("e1")
            assert retrieved is not None
            assert retrieved.id == "e1"
            assert retrieved.properties["value"] == 42
            
            await store2.close()
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestSQLiteTransactions:
    """Test transaction support"""
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self, graph_store):
        """Test successful transaction commits all changes"""
        e1 = Entity(id="e1", entity_type="Test")
        e2 = Entity(id="e2", entity_type="Test")
        
        async with graph_store.transaction():
            await graph_store.add_entity(e1)
            await graph_store.add_entity(e2)
        
        # Verify both entities were added
        assert await graph_store.get_entity("e1") is not None
        assert await graph_store.get_entity("e2") is not None
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, graph_store):
        """Test failed transaction rolls back all changes"""
        e1 = Entity(id="e1", entity_type="Test")
        e2 = Entity(id="e2", entity_type="Test")
        
        try:
            async with graph_store.transaction():
                await graph_store.add_entity(e1)
                # This should cause a rollback
                raise ValueError("Simulated error")
                await graph_store.add_entity(e2)
        except ValueError:
            pass
        
        # Verify entity was rolled back
        assert await graph_store.get_entity("e1") is None
        assert await graph_store.get_entity("e2") is None


class TestSQLiteStoreUtilities:
    """Test utility methods"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, populated_store):
        """Test getting graph statistics"""
        stats = await populated_store.get_stats()
        
        assert stats["entity_count"] == 4  # alice, bob, charlie, dave
        assert stats["relation_count"] == 4  # r1, r2, r3, r4
        assert stats["storage_type"] == "sqlite"
    
    @pytest.mark.asyncio
    async def test_clear(self, populated_store):
        """Test clearing all data"""
        # Verify data exists
        stats_before = await populated_store.get_stats()
        assert stats_before["entity_count"] > 0
        
        # Clear
        await populated_store.clear()
        
        # Verify empty
        stats_after = await populated_store.get_stats()
        assert stats_after["entity_count"] == 0
        assert stats_after["relation_count"] == 0
    
    @pytest.mark.asyncio
    async def test_update_entity(self, graph_store):
        """Test updating entity"""
        # Add entity
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await graph_store.add_entity(entity)
        
        # Update entity
        updated = Entity(id="e1", entity_type="Person", properties={"name": "Alice Smith"})
        await graph_store.update_entity(updated)
        
        # Verify update
        retrieved = await graph_store.get_entity("e1")
        assert retrieved.properties["name"] == "Alice Smith"
    
    @pytest.mark.asyncio
    async def test_delete_entity(self, graph_store):
        """Test deleting entity"""
        # Add entity
        entity = Entity(id="e1", entity_type="Test")
        await graph_store.add_entity(entity)
        
        # Verify exists
        assert await graph_store.get_entity("e1") is not None
        
        # Delete
        await graph_store.delete_entity("e1")
        
        # Verify deleted
        assert await graph_store.get_entity("e1") is None
    
    @pytest.mark.asyncio
    async def test_delete_entity_cascades_relations(self, graph_store):
        """Test that deleting entity cascades to relations"""
        # Add entities and relation
        e1 = Entity(id="e1", entity_type="Test")
        e2 = Entity(id="e2", entity_type="Test")
        await graph_store.add_entity(e1)
        await graph_store.add_entity(e2)
        
        rel = Relation(id="r1", relation_type="TEST", source_id="e1", target_id="e2")
        await graph_store.add_relation(rel)
        
        # Delete source entity
        await graph_store.delete_entity("e1")
        
        # Verify relation was also deleted (foreign key cascade)
        assert await graph_store.get_relation("r1") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


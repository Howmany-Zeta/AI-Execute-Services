"""
Unit tests for SQLite graph storage module

Tests use real components (SQLiteGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import tempfile
import os
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestSQLiteGraphStoreInitialization:
    """Test SQLiteGraphStore initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize_in_memory(self):
        """Test store initialization with in-memory database"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        
        assert store._is_initialized is True
        assert store.conn is not None
        
        await store.close()
    
    @pytest.mark.asyncio
    async def test_initialize_file_database(self):
        """Test store initialization with file database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            store = SQLiteGraphStore(db_path)
            await store.initialize()
            
            assert store._is_initialized is True
            assert store.conn is not None
            assert os.path.exists(db_path)
            
            await store.close()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test store close"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        await store.close()
        
        assert store._is_initialized is False
        assert store.conn is None


class TestSQLiteGraphStoreEntityOperations:
    """Test entity CRUD operations"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_entity(self, store):
        """Test adding an entity"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)
        
        # Verify entity was added
        retrieved = await store.get_entity("e1")
        assert retrieved is not None
        assert retrieved.id == "e1"
        assert retrieved.entity_type == "Person"
        assert retrieved.properties == {"name": "Alice"}
    
    @pytest.mark.asyncio
    async def test_add_entity_duplicate(self, store):
        """Test adding duplicate entity"""
        entity = Entity(id="e1", entity_type="Person", properties={})
        await store.add_entity(entity)
        
        with pytest.raises(ValueError, match="already exists"):
            await store.add_entity(entity)
    
    @pytest.mark.asyncio
    async def test_get_entity_exists(self, store):
        """Test getting existing entity"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)
        
        retrieved = await store.get_entity("e1")
        
        assert retrieved is not None
        assert retrieved.id == "e1"
        assert retrieved.entity_type == "Person"
    
    @pytest.mark.asyncio
    async def test_get_entity_not_exists(self, store):
        """Test getting non-existent entity"""
        result = await store.get_entity("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_add_entity_with_embedding(self, store):
        """Test adding entity with embedding"""
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={},
            embedding=[0.1, 0.2, 0.3]
        )
        await store.add_entity(entity)
        
        retrieved = await store.get_entity("e1")
        assert retrieved is not None
        assert retrieved.embedding is not None
        assert len(retrieved.embedding) == 3
        # Allow for floating point precision differences
        assert abs(retrieved.embedding[0] - 0.1) < 0.001
        assert abs(retrieved.embedding[1] - 0.2) < 0.001
        assert abs(retrieved.embedding[2] - 0.3) < 0.001


class TestSQLiteGraphStoreRelationOperations:
    """Test relation CRUD operations"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with entities"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        
        # Add entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await store.add_entity(e1)
        await store.add_entity(e2)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_relation(self, store):
        """Test adding a relation"""
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(relation)
        
        # Verify relation was added
        retrieved = await store.get_relation("r1")
        assert retrieved is not None
        assert retrieved.id == "r1"
        assert retrieved.relation_type == "KNOWS"
        assert retrieved.source_id == "e1"
        assert retrieved.target_id == "e2"
    
    @pytest.mark.asyncio
    async def test_add_relation_duplicate(self, store):
        """Test adding duplicate relation"""
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(relation)
        
        with pytest.raises(ValueError, match="already exists"):
            await store.add_relation(relation)
    
    @pytest.mark.asyncio
    async def test_add_relation_source_not_exists(self, store):
        """Test adding relation with non-existent source"""
        relation = Relation(id="r1", relation_type="KNOWS", source_id="nonexistent", target_id="e2")
        
        with pytest.raises(ValueError, match="Source entity"):
            await store.add_relation(relation)
    
    @pytest.mark.asyncio
    async def test_add_relation_target_not_exists(self, store):
        """Test adding relation with non-existent target"""
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="nonexistent")
        
        with pytest.raises(ValueError, match="Target entity"):
            await store.add_relation(relation)
    
    @pytest.mark.asyncio
    async def test_get_relation_exists(self, store):
        """Test getting existing relation"""
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(relation)
        
        retrieved = await store.get_relation("r1")
        
        assert retrieved is not None
        assert retrieved.id == "r1"
        assert retrieved.relation_type == "KNOWS"
    
    @pytest.mark.asyncio
    async def test_get_relation_not_exists(self, store):
        """Test getting non-existent relation"""
        result = await store.get_relation("nonexistent")
        
        assert result is None


class TestSQLiteGraphStoreGetNeighbors:
    """Test get_neighbors method"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with graph"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        
        # Create graph: e1 -> e2 -> e3, e1 -> e4
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        e3 = Entity(id="e3", entity_type="Person", properties={})
        e4 = Entity(id="e4", entity_type="Person", properties={})
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_entity(e3)
        await store.add_entity(e4)
        
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        r2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        r3 = Relation(id="r3", relation_type="WORKS_WITH", source_id="e1", target_id="e4")
        
        await store.add_relation(r1)
        await store.add_relation(r2)
        await store.add_relation(r3)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_get_neighbors_outgoing(self, store):
        """Test getting outgoing neighbors"""
        neighbors = await store.get_neighbors("e1", direction="outgoing")
        
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"e2", "e4"}
    
    @pytest.mark.asyncio
    async def test_get_neighbors_incoming(self, store):
        """Test getting incoming neighbors"""
        neighbors = await store.get_neighbors("e2", direction="incoming")
        
        assert len(neighbors) == 1
        assert neighbors[0].id == "e1"
    
    @pytest.mark.asyncio
    async def test_get_neighbors_both(self, store):
        """Test getting neighbors in both directions"""
        neighbors = await store.get_neighbors("e2", direction="both")
        
        assert len(neighbors) == 2
        neighbor_ids = {n.id for n in neighbors}
        assert neighbor_ids == {"e1", "e3"}
    
    @pytest.mark.asyncio
    async def test_get_neighbors_with_relation_type(self, store):
        """Test getting neighbors filtered by relation type"""
        neighbors = await store.get_neighbors("e1", relation_type="KNOWS", direction="outgoing")
        
        assert len(neighbors) == 1
        assert neighbors[0].id == "e2"
    
    @pytest.mark.asyncio
    async def test_get_neighbors_nonexistent_entity(self, store):
        """Test getting neighbors for non-existent entity"""
        neighbors = await store.get_neighbors("nonexistent", direction="outgoing")
        
        assert neighbors == []


class TestSQLiteGraphStoreTransactions:
    """Test transaction support"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store"""
        store = SQLiteGraphStore(":memory:")
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_transaction_commit(self, store):
        """Test transaction commit"""
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        
        async with store.transaction():
            await store.add_entity(e1)
            await store.add_entity(e2)
        
        # Both entities should be persisted
        assert await store.get_entity("e1") is not None
        assert await store.get_entity("e2") is not None
    
    @pytest.mark.asyncio
    async def test_transaction_rollback(self, store):
        """Test transaction rollback on error"""
        e1 = Entity(id="e1", entity_type="Person", properties={})
        
        try:
            async with store.transaction():
                await store.add_entity(e1)
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Entity should not be persisted
        assert await store.get_entity("e1") is None
    
    @pytest.mark.asyncio
    async def test_transaction_not_initialized(self):
        """Test transaction when not initialized"""
        store = SQLiteGraphStore(":memory:")
        
        with pytest.raises(RuntimeError, match="not initialized"):
            async with store.transaction():
                pass


"""
Unit tests for in-memory graph storage module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
import numpy as np
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestInMemoryGraphStoreInitialization:
    """Test InMemoryGraphStore initialization"""
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test store initialization"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        assert store._initialized is True
        assert store.graph is not None
        assert store.entities == {}
        assert store.relations == {}
    
    @pytest.mark.asyncio
    async def test_initialize_idempotent(self):
        """Test that initialize can be called multiple times"""
        store = InMemoryGraphStore()
        await store.initialize()
        await store.initialize()  # Second call should not fail
        
        assert store._initialized is True
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test store close"""
        store = InMemoryGraphStore()
        await store.initialize()
        await store.close()
        
        assert store._initialized is False
        assert store.graph is None
        assert store.entities == {}
        assert store.relations == {}


class TestInMemoryGraphStoreEntityOperations:
    """Test entity CRUD operations"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_add_entity(self, store):
        """Test adding an entity"""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)
        
        assert "e1" in store.entities
        assert store.entities["e1"] == entity
        assert store.graph.has_node("e1")
    
    @pytest.mark.asyncio
    async def test_add_entity_not_initialized(self):
        """Test adding entity when not initialized"""
        store = InMemoryGraphStore()
        entity = Entity(id="e1", entity_type="Person", properties={})
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await store.add_entity(entity)
    
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
    async def test_get_entity_not_initialized(self):
        """Test getting entity when not initialized"""
        store = InMemoryGraphStore()
        
        result = await store.get_entity("e1")
        
        assert result is None


class TestInMemoryGraphStoreRelationOperations:
    """Test relation CRUD operations"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with entities"""
        store = InMemoryGraphStore()
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
        
        assert "r1" in store.relations
        assert store.relations["r1"] == relation
        assert store.graph.has_edge("e1", "e2")
    
    @pytest.mark.asyncio
    async def test_add_relation_not_initialized(self):
        """Test adding relation when not initialized"""
        store = InMemoryGraphStore()
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await store.add_relation(relation)
    
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
    
    @pytest.mark.asyncio
    async def test_get_relation_not_initialized(self):
        """Test getting relation when not initialized"""
        store = InMemoryGraphStore()
        
        result = await store.get_relation("r1")
        
        assert result is None


class TestInMemoryGraphStoreGetNeighbors:
    """Test get_neighbors method"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with graph"""
        store = InMemoryGraphStore()
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
    
    @pytest.mark.asyncio
    async def test_get_neighbors_not_initialized(self):
        """Test getting neighbors when not initialized"""
        store = InMemoryGraphStore()
        
        neighbors = await store.get_neighbors("e1", direction="outgoing")
        
        assert neighbors == []


class TestInMemoryGraphStoreVectorSearch:
    """Test vector search method"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with entities with embeddings"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entities with embeddings
        e1 = Entity(id="e1", entity_type="Person", properties={}, embedding=[1.0, 0.0, 0.0])
        e2 = Entity(id="e2", entity_type="Person", properties={}, embedding=[0.0, 1.0, 0.0])
        e3 = Entity(id="e3", entity_type="Company", properties={}, embedding=[0.0, 0.0, 1.0])
        e4 = Entity(id="e4", entity_type="Person", properties={})  # No embedding
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_entity(e3)
        await store.add_entity(e4)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_vector_search_basic(self, store):
        """Test basic vector search"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await store.vector_search(query_embedding, max_results=10)
        
        assert len(results) > 0
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        assert all(isinstance(score, float) for _, score in results)
        # e1 should have highest similarity
        assert results[0][0].id == "e1"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type(self, store):
        """Test vector search filtered by entity type"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await store.vector_search(query_embedding, entity_type="Person", max_results=10)
        
        assert len(results) > 0
        assert all(entity.entity_type == "Person" for entity, _ in results)
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, store):
        """Test vector search with score threshold"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await store.vector_search(query_embedding, score_threshold=0.5, max_results=10)
        
        assert all(score >= 0.5 for _, score in results)
    
    @pytest.mark.asyncio
    async def test_vector_search_max_results(self, store):
        """Test vector search respects max_results"""
        query_embedding = [1.0, 0.0, 0.0]
        
        results = await store.vector_search(query_embedding, max_results=2)
        
        assert len(results) <= 2
    
    @pytest.mark.asyncio
    async def test_vector_search_empty_embedding(self, store):
        """Test vector search with empty embedding"""
        with pytest.raises(ValueError, match="cannot be empty"):
            await store.vector_search([], max_results=10)
    
    @pytest.mark.asyncio
    async def test_vector_search_zero_norm(self, store):
        """Test vector search with zero norm query"""
        query_embedding = [0.0, 0.0, 0.0]
        
        results = await store.vector_search(query_embedding, max_results=10)
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_vector_search_not_initialized(self):
        """Test vector search when not initialized"""
        store = InMemoryGraphStore()
        
        results = await store.vector_search([1.0, 0.0, 0.0], max_results=10)
        
        assert results == []


class TestInMemoryGraphStoreFindPaths:
    """Test optimized find_paths method"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with path graph"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create path: e1 -> e2 -> e3
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        e3 = Entity(id="e3", entity_type="Person", properties={})
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_entity(e3)
        
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        r2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        
        await store.add_relation(r1)
        await store.add_relation(r2)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_find_paths_existing(self, store):
        """Test finding paths between connected entities"""
        paths = await store.find_paths("e1", "e3", max_depth=3, max_paths=10)
        
        assert len(paths) > 0
        assert all(path.start_entity.id == "e1" for path in paths)
        assert all(path.end_entity.id == "e3" for path in paths)
    
    @pytest.mark.asyncio
    async def test_find_paths_no_path(self, store):
        """Test finding paths when no path exists"""
        e4 = Entity(id="e4", entity_type="Person", properties={})
        await store.add_entity(e4)
        
        paths = await store.find_paths("e1", "e4", max_depth=3, max_paths=10)
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_find_paths_max_paths(self, store):
        """Test find_paths respects max_paths"""
        paths = await store.find_paths("e1", "e3", max_depth=3, max_paths=1)
        
        assert len(paths) <= 1
    
    @pytest.mark.asyncio
    async def test_find_paths_not_initialized(self):
        """Test find_paths when not initialized"""
        store = InMemoryGraphStore()
        
        paths = await store.find_paths("e1", "e2", max_depth=3, max_paths=10)
        
        assert paths == []


class TestInMemoryGraphStoreUtilities:
    """Test utility methods"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize store with data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await store.add_entity(e1)
        await store.add_entity(e2)
        
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(r1)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_get_stats(self, store):
        """Test getting graph statistics"""
        stats = store.get_stats()
        
        assert stats["nodes"] == 2
        assert stats["edges"] == 1
        assert stats["entities"] == 2
        assert stats["relations"] == 1
    
    @pytest.mark.asyncio
    async def test_get_stats_not_initialized(self):
        """Test get_stats when not initialized"""
        store = InMemoryGraphStore()
        
        stats = store.get_stats()
        
        assert stats == {"nodes": 0, "edges": 0, "entities": 0, "relations": 0}
    
    @pytest.mark.asyncio
    async def test_clear(self, store):
        """Test clearing the graph"""
        store.clear()
        
        assert len(store.entities) == 0
        assert len(store.relations) == 0
        assert store.graph.number_of_nodes() == 0
    
    def test_str_representation(self, store):
        """Test string representation"""
        result = str(store)
        
        assert "InMemoryGraphStore" in result
        assert "entities" in result.lower()
        assert "relations" in result.lower()
    
    def test_repr_representation(self, store):
        """Test repr representation"""
        result = repr(store)
        
        assert "InMemoryGraphStore" in result


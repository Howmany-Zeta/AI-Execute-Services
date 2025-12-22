"""
Integration tests for InMemoryGraphStore

Tests the two-tier interface design:
- Tier 1 methods are implemented
- Tier 2 methods work automatically via defaults
"""

import pytest
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def graph_store():
    """Fixture providing initialized graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


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


class TestInMemoryStoreTier1:
    """Test Tier 1 (Basic) operations"""
    
    @pytest.mark.asyncio
    async def test_initialize_and_close(self):
        """Test store initialization and cleanup"""
        store = InMemoryGraphStore()
        await store.initialize()
        assert store._initialized is True
        
        await store.close()
        assert store._initialized is False
    
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
        
        with pytest.raises(ValueError, match="not found"):
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


class TestInMemoryStoreTier2:
    """Test Tier 2 (Advanced) operations - work via defaults!"""
    
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
        """Test path finding between entities (Tier 2 method, OPTIMIZED)"""
        # Find paths from alice to dave
        paths = await populated_store.find_paths(
            source_entity_id="alice",
            target_entity_id="dave",
            max_depth=5,
            max_paths=10
        )
        
        assert len(paths) > 0
        
        # Should find both paths:
        # 1. alice -> dave (direct, FRIENDS)
        # 2. alice -> bob -> charlie -> dave (KNOWS chain)
        path_lengths = [path.length for path in paths]
        assert 1 in path_lengths  # Direct path
        assert 3 in path_lengths  # Three-hop path
        
        # Verify paths are valid
        for path in paths:
            assert path.start_entity.id == "alice"
            assert path.end_entity.id == "dave"
    
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
    
    @pytest.mark.asyncio
    async def test_execute_query_traversal(self, populated_store):
        """Test executing traversal query (Tier 2 method)"""
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="alice",
            relation_type="KNOWS",
            max_depth=2,
            max_results=10
        )
        
        result = await populated_store.execute_query(query)
        
        assert result.has_results
        # Should find entities reachable via KNOWS relations
        entity_ids = result.get_entity_ids()
        # At minimum should find bob (direct neighbor)
        assert "bob" in entity_ids or len(entity_ids) > 0


class TestTwoTierDesign:
    """Test that the two-tier design works as expected"""
    
    @pytest.mark.asyncio
    async def test_tier1_only_implementation_works(self):
        """
        Demonstrate that implementing only Tier 1 gives you Tier 2 for free
        
        InMemoryGraphStore only implements:
        - add_entity(), get_entity()
        - add_relation(), get_relation()
        - get_neighbors()
        - initialize(), close()
        
        But we get these for free:
        - traverse()
        - find_paths()
        - subgraph_query()
        - vector_search()
        - execute_query()
        """
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add simple graph
        e1 = Entity(id="e1", entity_type="Test")
        e2 = Entity(id="e2", entity_type="Test")
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_relation(Relation(
            id="r1", relation_type="TEST", source_id="e1", target_id="e2"
        ))
        
        # All Tier 2 methods work!
        paths = await store.traverse("e1", max_depth=2)
        assert isinstance(paths, list)
        
        found_paths = await store.find_paths("e1", "e2")
        assert isinstance(found_paths, list)
        
        entities, relations = await store.subgraph_query(["e1", "e2"])
        assert isinstance(entities, list)
        assert isinstance(relations, list)
        
        query = GraphQuery(query_type=QueryType.ENTITY_LOOKUP, entity_id="e1")
        result = await store.execute_query(query)
        assert result.has_results
        
        await store.close()


class TestGraphStoreUtilities:
    """Test utility methods"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, populated_store):
        """Test getting graph statistics"""
        stats = populated_store.get_stats()
        
        assert stats["entities"] == 4  # alice, bob, charlie, dave
        assert stats["relations"] == 4  # r1, r2, r3, r4
        assert stats["nodes"] == 4
        assert stats["edges"] == 4
    
    @pytest.mark.asyncio
    async def test_get_stats_not_initialized(self):
        """Test get_stats when store is not initialized"""
        store = InMemoryGraphStore()
        stats = store.get_stats()
        assert stats["entities"] == 0
        assert stats["relations"] == 0
        assert stats["nodes"] == 0
        assert stats["edges"] == 0
    
    @pytest.mark.asyncio
    async def test_clear(self, populated_store):
        """Test clearing all data"""
        # Verify data exists
        stats_before = populated_store.get_stats()
        assert stats_before["entities"] > 0
        
        # Clear
        populated_store.clear()
        
        # Verify empty
        stats_after = populated_store.get_stats()
        assert stats_after["entities"] == 0
        assert stats_after["relations"] == 0
    
    @pytest.mark.asyncio
    async def test_clear_not_initialized(self):
        """Test clear when store is not initialized"""
        store = InMemoryGraphStore()
        # Should not raise error
        store.clear()
        stats = store.get_stats()
        assert stats["entities"] == 0
    
    @pytest.mark.asyncio
    async def test_string_representations(self, populated_store):
        """Test string representations"""
        str_repr = str(populated_store)
        assert "InMemoryGraphStore" in str_repr
        assert "entities" in str_repr.lower()
        
        repr_str = repr(populated_store)
        assert "InMemoryGraphStore" in repr_str


class TestVectorSearch:
    """Test vector search functionality"""
    
    @pytest.mark.asyncio
    async def test_vector_search_basic(self, graph_store):
        """Test basic vector search"""
        # Add entities with embeddings
        entity1 = Entity(
            id="e1",
            entity_type="Document",
            embedding=[1.0, 0.0, 0.0]  # Unit vector in x direction
        )
        entity2 = Entity(
            id="e2",
            entity_type="Document",
            embedding=[0.0, 1.0, 0.0]  # Unit vector in y direction
        )
        entity3 = Entity(
            id="e3",
            entity_type="Person",  # Different type
            embedding=[0.0, 0.0, 1.0]  # Unit vector in z direction
        )
        
        await graph_store.add_entity(entity1)
        await graph_store.add_entity(entity2)
        await graph_store.add_entity(entity3)
        
        # Search for vector similar to entity1
        results = await graph_store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            max_results=2
        )
        
        assert len(results) > 0
        # Should find entity1 as most similar
        assert results[0][0].id == "e1"
        assert results[0][1] > 0.9  # High similarity
    
    @pytest.mark.asyncio
    async def test_vector_search_with_type_filter(self, graph_store):
        """Test vector search with entity type filter"""
        entity1 = Entity(
            id="e1",
            entity_type="Document",
            embedding=[1.0, 0.0, 0.0]
        )
        entity2 = Entity(
            id="e2",
            entity_type="Person",
            embedding=[1.0, 0.0, 0.0]  # Same embedding but different type
        )
        
        await graph_store.add_entity(entity1)
        await graph_store.add_entity(entity2)
        
        # Search only for Document entities
        results = await graph_store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            entity_type="Document",
            max_results=10
        )
        
        assert len(results) == 1
        assert results[0][0].id == "e1"
        assert results[0][0].entity_type == "Document"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(self, graph_store):
        """Test vector search with score threshold"""
        entity1 = Entity(
            id="e1",
            entity_type="Document",
            embedding=[1.0, 0.0, 0.0]
        )
        entity2 = Entity(
            id="e2",
            entity_type="Document",
            embedding=[0.0, 1.0, 0.0]  # Orthogonal (low similarity)
        )
        
        await graph_store.add_entity(entity1)
        await graph_store.add_entity(entity2)
        
        # Search with high threshold
        results = await graph_store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            score_threshold=0.8,
            max_results=10
        )
        
        # Should only return entity1 (high similarity)
        assert len(results) == 1
        assert results[0][0].id == "e1"
    
    @pytest.mark.asyncio
    async def test_vector_search_no_embeddings(self, graph_store):
        """Test vector search when entities have no embeddings"""
        entity1 = Entity(id="e1", entity_type="Document")  # No embedding
        await graph_store.add_entity(entity1)
        
        results = await graph_store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            max_results=10
        )
        
        # Should return empty (no entities with embeddings)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_vector_search_empty_query(self, graph_store):
        """Test vector search with empty query embedding"""
        with pytest.raises(ValueError, match="Query embedding cannot be empty"):
            await graph_store.vector_search(
                query_embedding=[],
                max_results=10
            )
    
    @pytest.mark.asyncio
    async def test_vector_search_not_initialized(self):
        """Test vector search when store is not initialized"""
        store = InMemoryGraphStore()
        results = await store.vector_search(
            query_embedding=[1.0, 0.0, 0.0],
            max_results=10
        )
        assert results == []


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_add_entity_not_initialized(self):
        """Test adding entity when store is not initialized"""
        store = InMemoryGraphStore()
        entity = Entity(id="e1", entity_type="Person")
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await store.add_entity(entity)
    
    @pytest.mark.asyncio
    async def test_get_entity_not_initialized(self):
        """Test getting entity when store is not initialized"""
        store = InMemoryGraphStore()
        result = await store.get_entity("e1")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_add_relation_not_initialized(self):
        """Test adding relation when store is not initialized"""
        store = InMemoryGraphStore()
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        
        with pytest.raises(RuntimeError, match="not initialized"):
            await store.add_relation(relation)
    
    @pytest.mark.asyncio
    async def test_get_neighbors_invalid_entity(self, graph_store):
        """Test getting neighbors for non-existent entity"""
        neighbors = await graph_store.get_neighbors("non_existent")
        assert neighbors == []
    
    @pytest.mark.asyncio
    async def test_get_neighbors_not_initialized(self):
        """Test getting neighbors when store is not initialized"""
        store = InMemoryGraphStore()
        neighbors = await store.get_neighbors("e1")
        assert neighbors == []
    
    @pytest.mark.asyncio
    async def test_duplicate_relation_id(self, graph_store):
        """Test adding duplicate relation ID"""
        entity1 = Entity(id="e1", entity_type="Person")
        entity2 = Entity(id="e2", entity_type="Person")
        await graph_store.add_entity(entity1)
        await graph_store.add_entity(entity2)
        
        relation1 = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        await graph_store.add_relation(relation1)
        
        # Try to add another relation with same ID
        relation2 = Relation(
            id="r1",  # Same ID
            relation_type="FRIENDS",
            source_id="e1",
            target_id="e2"
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await graph_store.add_relation(relation2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


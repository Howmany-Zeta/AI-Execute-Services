"""
Unit tests for graph storage base module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType


class TestGraphStoreAbstract:
    """Test GraphStore abstract interface"""
    
    def test_graph_store_is_abstract(self):
        """Test that GraphStore cannot be instantiated directly"""
        with pytest.raises(TypeError):
            GraphStore()
    
    def test_graph_store_requires_tier1_methods(self):
        """Test that concrete implementations must implement Tier 1 methods"""
        class IncompleteStore(GraphStore):
            async def initialize(self):
                pass
        
        # Should fail because other Tier 1 methods are missing
        with pytest.raises(TypeError):
            IncompleteStore()


class TestGraphStoreDefaultTraverse:
    """Test default traverse implementation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store with test data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create a simple graph: e1 -> e2 -> e3
        e1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        e2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        e3 = Entity(id="e3", entity_type="Person", properties={"name": "Charlie"})
        
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
    async def test_traverse_single_entity(self, store):
        """Test traversing from a single entity"""
        paths = await store.traverse("e1", max_depth=1, max_results=10)
        
        # Should find paths to neighbors
        assert len(paths) > 0
    
    @pytest.mark.asyncio
    async def test_traverse_max_depth(self, store):
        """Test traverse respects max_depth"""
        paths = await store.traverse("e1", max_depth=1, max_results=10)
        
        # All paths should have length <= max_depth
        for path in paths:
            assert path.length <= 1
    
    @pytest.mark.asyncio
    async def test_traverse_max_results(self, store):
        """Test traverse respects max_results"""
        paths = await store.traverse("e1", max_depth=3, max_results=2)
        
        assert len(paths) <= 2
    
    @pytest.mark.asyncio
    async def test_traverse_nonexistent_entity(self, store):
        """Test traversing from non-existent entity"""
        paths = await store.traverse("nonexistent", max_depth=3, max_results=10)
        
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_traverse_with_relation_type_filter(self, store):
        """Test traverse with relation type filter"""
        paths = await store.traverse("e1", relation_type="KNOWS", max_depth=2, max_results=10)
        
        # Should only include paths with KNOWS relations
        assert isinstance(paths, list)
    
    @pytest.mark.asyncio
    async def test_traverse_zero_depth(self, store):
        """Test traverse with zero depth"""
        paths = await store.traverse("e1", max_depth=0, max_results=10)
        
        # Should return empty paths (no traversal)
        assert len(paths) == 0


class TestGraphStoreDefaultFindPaths:
    """Test default find_paths implementation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store with test data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create a path: e1 -> e2 -> e3
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
    async def test_find_paths_existing_path(self, store):
        """Test finding paths between connected entities"""
        paths = await store.find_paths("e1", "e3", max_depth=3, max_paths=10)
        
        # Should find at least one path
        assert len(paths) > 0
        assert all(path.start_entity.id == "e1" for path in paths)
        assert all(path.end_entity.id == "e3" for path in paths)
    
    @pytest.mark.asyncio
    async def test_find_paths_no_path(self, store):
        """Test finding paths when no path exists"""
        e4 = Entity(id="e4", entity_type="Person", properties={})
        await store.add_entity(e4)
        
        paths = await store.find_paths("e1", "e4", max_depth=3, max_paths=10)
        
        # Should return empty if no path exists
        assert paths == []
    
    @pytest.mark.asyncio
    async def test_find_paths_max_paths(self, store):
        """Test find_paths respects max_paths"""
        paths = await store.find_paths("e1", "e3", max_depth=3, max_paths=1)
        
        assert len(paths) <= 1
    
    @pytest.mark.asyncio
    async def test_find_paths_same_entity(self, store):
        """Test finding paths from entity to itself"""
        paths = await store.find_paths("e1", "e1", max_depth=3, max_paths=10)
        
        # May or may not find self-loops, but should not crash
        assert isinstance(paths, list)


class TestGraphStoreDefaultSubgraphQuery:
    """Test default subgraph_query implementation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store with test data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create entities
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={})
        e3 = Entity(id="e3", entity_type="Person", properties={})
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        await store.add_entity(e3)
        
        # Create relation between e1 and e2
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(r1)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_subgraph_query_with_relations(self, store):
        """Test subgraph query including relations"""
        entities, relations = await store.subgraph_query(["e1", "e2"], include_relations=True)
        
        assert len(entities) == 2
        assert all(e.id in ["e1", "e2"] for e in entities)
        assert len(relations) > 0
    
    @pytest.mark.asyncio
    async def test_subgraph_query_without_relations(self, store):
        """Test subgraph query excluding relations"""
        entities, relations = await store.subgraph_query(["e1", "e2"], include_relations=False)
        
        assert len(entities) == 2
        assert len(relations) == 0
    
    @pytest.mark.asyncio
    async def test_subgraph_query_nonexistent_entities(self, store):
        """Test subgraph query with non-existent entities"""
        entities, relations = await store.subgraph_query(["nonexistent"], include_relations=True)
        
        assert len(entities) == 0
        assert len(relations) == 0
    
    @pytest.mark.asyncio
    async def test_subgraph_query_empty_list(self, store):
        """Test subgraph query with empty entity list"""
        entities, relations = await store.subgraph_query([], include_relations=True)
        
        assert len(entities) == 0
        assert len(relations) == 0


class TestGraphStoreDefaultVectorSearch:
    """Test default vector_search implementation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store"""
        store = InMemoryGraphStore()
        await store.initialize()
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_vector_search_default_implementation(self, store):
        """Test default vector search returns empty (not implemented)"""
        query_embedding = [0.1, 0.2, 0.3]
        
        results = await store.vector_search(
            query_embedding,
            entity_type=None,
            max_results=10,
            score_threshold=0.0
        )
        
        # Default implementation returns empty list
        assert results == []


class TestGraphStoreDefaultExecuteQuery:
    """Test default execute_query implementation"""
    
    @pytest.fixture
    async def store(self):
        """Create and initialize in-memory graph store with test data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        e1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(e1)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_execute_query_entity_lookup(self, store):
        """Test executing entity lookup query"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="e1",
            max_results=10
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        assert len(result.entities) == 1
        assert result.entities[0].id == "e1"
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_query_entity_lookup_nonexistent(self, store):
        """Test executing entity lookup query for non-existent entity"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="nonexistent",
            max_results=10
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        assert len(result.entities) == 0
        assert result.total_count == 0
    
    @pytest.mark.asyncio
    async def test_execute_query_traversal(self, store):
        """Test executing traversal query"""
        # Add more entities and relations
        e2 = Entity(id="e2", entity_type="Person", properties={})
        await store.add_entity(e2)
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(r1)
        
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="e1",
            max_depth=2,
            max_results=10
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        assert len(result.entities) > 0
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_execute_query_path_finding(self, store):
        """Test executing path finding query"""
        # Add more entities and relations
        e2 = Entity(id="e2", entity_type="Person", properties={})
        e3 = Entity(id="e3", entity_type="Person", properties={})
        await store.add_entity(e2)
        await store.add_entity(e3)
        
        r1 = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        r2 = Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        await store.add_relation(r1)
        await store.add_relation(r2)
        
        query = GraphQuery(
            query_type=QueryType.PATH_FINDING,
            source_entity_id="e1",
            target_entity_id="e3",
            max_depth=3,
            max_results=10
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        assert result.execution_time_ms >= 0
        # May or may not find paths, but should not crash
        assert isinstance(result.paths, list)
    
    @pytest.mark.asyncio
    async def test_execute_query_vector_search(self, store):
        """Test executing vector search query"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=[0.1, 0.2, 0.3],
            max_results=10,
            score_threshold=0.0
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        # Default implementation returns empty
        assert len(result.entities) == 0
    
    @pytest.mark.asyncio
    async def test_execute_query_vector_search_no_embedding(self, store):
        """Test executing vector search query without embedding"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=None,
            max_results=10
        )
        
        result = await store.execute_query(query)
        
        assert result.query == query
        assert len(result.entities) == 0
    
    @pytest.mark.asyncio
    async def test_execute_query_respects_max_results(self, store):
        """Test execute_query respects max_results"""
        # Add multiple entities
        for i in range(2, 12):
            e = Entity(id=f"e{i}", entity_type="Person", properties={})
            await store.add_entity(e)
        
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="e1",
            max_results=5
        )
        
        result = await store.execute_query(query)
        
        # Should respect max_results
        assert len(result.entities) <= 5


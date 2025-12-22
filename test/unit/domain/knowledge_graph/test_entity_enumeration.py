"""
Unit tests for GraphStore entity enumeration

Tests get_all_entities() functionality including:
- Basic entity enumeration
- Entity type filtering
- Tenant context filtering
- Pagination support
- Integration with vector search
"""

import pytest
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext


@pytest.fixture
async def graph_store():
    """Create and initialize a test graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def sample_entities():
    """Create sample entities of different types"""
    return [
        Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice", "age": 30}
        ),
        Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob", "age": 25}
        ),
        Entity(
            id="company_1",
            entity_type="Company",
            properties={"name": "Acme Corp"}
        ),
        Entity(
            id="company_2",
            entity_type="Company",
            properties={"name": "Tech Inc"}
        ),
        Entity(
            id="product_1",
            entity_type="Product",
            properties={"name": "Widget"}
        ),
    ]


class TestEntityEnumeration:
    """Test entity enumeration functionality"""
    
    @pytest.mark.asyncio
    async def test_get_all_entities_basic(self, graph_store, sample_entities):
        """Test basic entity enumeration"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get all entities
        all_entities = await graph_store.get_all_entities()
        
        assert len(all_entities) == len(sample_entities)
        entity_ids = {e.id for e in all_entities}
        assert entity_ids == {e.id for e in sample_entities}
    
    @pytest.mark.asyncio
    async def test_get_all_entities_with_entity_type_filter(self, graph_store, sample_entities):
        """Test entity enumeration with entity type filtering"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get only Person entities
        people = await graph_store.get_all_entities(entity_type="Person")
        
        assert len(people) == 2
        assert all(e.entity_type == "Person" for e in people)
        assert {e.id for e in people} == {"person_1", "person_2"}
        
        # Get only Company entities
        companies = await graph_store.get_all_entities(entity_type="Company")
        
        assert len(companies) == 2
        assert all(e.entity_type == "Company" for e in companies)
        assert {e.id for e in companies} == {"company_1", "company_2"}
    
    @pytest.mark.asyncio
    async def test_get_all_entities_with_limit(self, graph_store, sample_entities):
        """Test entity enumeration with limit"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get first 3 entities
        entities = await graph_store.get_all_entities(limit=3)
        
        assert len(entities) == 3
    
    @pytest.mark.asyncio
    async def test_get_all_entities_with_offset(self, graph_store, sample_entities):
        """Test entity enumeration with offset (pagination)"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get first page
        page1 = await graph_store.get_all_entities(limit=2, offset=0)
        assert len(page1) == 2
        
        # Get second page
        page2 = await graph_store.get_all_entities(limit=2, offset=2)
        assert len(page2) == 2
        
        # Pages should not overlap
        page1_ids = {e.id for e in page1}
        page2_ids = {e.id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)
    
    @pytest.mark.asyncio
    async def test_get_all_entities_with_tenant_context(self, graph_store, sample_entities):
        """Test entity enumeration with tenant context filtering"""
        # Add entities to global namespace
        for entity in sample_entities[:3]:
            await graph_store.add_entity(entity)
        
        # Add entities to tenant namespace
        tenant_context = TenantContext(tenant_id="tenant_1")
        for entity in sample_entities[3:]:
            await graph_store.add_entity(entity, context=tenant_context)
        
        # Get entities from global namespace
        global_entities = await graph_store.get_all_entities()
        assert len(global_entities) == 3
        
        # Get entities from tenant namespace
        tenant_entities = await graph_store.get_all_entities(context=tenant_context)
        assert len(tenant_entities) == 2
    
    @pytest.mark.asyncio
    async def test_get_all_entities_combines_filters(self, graph_store, sample_entities):
        """Test entity enumeration with multiple filters combined"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get Person entities with limit
        people = await graph_store.get_all_entities(entity_type="Person", limit=1)
        
        assert len(people) == 1
        assert all(e.entity_type == "Person" for e in people)
    
    @pytest.mark.asyncio
    async def test_get_all_entities_empty_store(self, graph_store):
        """Test entity enumeration on empty store"""
        entities = await graph_store.get_all_entities()
        
        assert len(entities) == 0
        assert entities == []
    
    @pytest.mark.asyncio
    async def test_get_all_entities_no_matching_type(self, graph_store, sample_entities):
        """Test entity enumeration with entity type that doesn't exist"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get entities of non-existent type
        entities = await graph_store.get_all_entities(entity_type="NonExistent")
        
        assert len(entities) == 0
    
    @pytest.mark.asyncio
    async def test_get_all_entities_large_offset(self, graph_store, sample_entities):
        """Test entity enumeration with offset larger than total entities"""
        # Add entities
        for entity in sample_entities:
            await graph_store.add_entity(entity)
        
        # Get entities with offset beyond total
        entities = await graph_store.get_all_entities(offset=100)
        
        assert len(entities) == 0
    
    @pytest.mark.asyncio
    async def test_vector_search_uses_enumeration(self, graph_store, sample_entities):
        """Test that vector_search uses get_all_entities for enumeration"""
        # Add entities with embeddings
        entities_with_embeddings = [
            Entity(
                id="person_1",
                entity_type="Person",
                properties={"name": "Alice"},
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
            ),
            Entity(
                id="person_2",
                entity_type="Person",
                properties={"name": "Bob"},
                embedding=[0.15, 0.25, 0.35, 0.45, 0.55]
            ),
            Entity(
                id="company_1",
                entity_type="Company",
                properties={"name": "Acme"},
                embedding=[0.2, 0.3, 0.4, 0.5, 0.6]
            ),
        ]
        
        for entity in entities_with_embeddings:
            await graph_store.add_entity(entity)
        
        # Perform vector search
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = await graph_store.vector_search(
            query_embedding=query_embedding,
            max_results=10,
            score_threshold=0.0
        )
        
        # Should find entities with embeddings
        assert len(results) > 0
        assert all(isinstance(result, tuple) and len(result) == 2 for result in results)
        assert all(isinstance(score, float) for _, score in results)
    
    @pytest.mark.asyncio
    async def test_vector_search_with_entity_type_filter(self, graph_store):
        """Test vector_search with entity type filter uses enumeration correctly"""
        # Add entities with embeddings
        entities_with_embeddings = [
            Entity(
                id="person_1",
                entity_type="Person",
                properties={"name": "Alice"},
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
            ),
            Entity(
                id="company_1",
                entity_type="Company",
                properties={"name": "Acme"},
                embedding=[0.1, 0.2, 0.3, 0.4, 0.5]  # Same embedding
            ),
        ]
        
        for entity in entities_with_embeddings:
            await graph_store.add_entity(entity)
        
        # Perform vector search filtered to Person
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = await graph_store.vector_search(
            query_embedding=query_embedding,
            entity_type="Person",
            max_results=10,
            score_threshold=0.0
        )
        
        # Should only return Person entities
        assert len(results) == 1
        assert results[0][0].entity_type == "Person"
        assert results[0][0].id == "person_1"
    
    @pytest.mark.asyncio
    async def test_vector_search_respects_score_threshold(self, graph_store):
        """Test that vector_search respects score threshold"""
        # Add entity with embedding
        entity = Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        await graph_store.add_entity(entity)
        
        # Search with high threshold (should return nothing)
        query_embedding = [0.9, 0.9, 0.9, 0.9, 0.9]  # Very different embedding
        results = await graph_store.vector_search(
            query_embedding=query_embedding,
            max_results=10,
            score_threshold=0.9  # High threshold
        )
        
        # Should return empty or low-scoring results filtered out
        assert all(score >= 0.9 for _, score in results) if results else True
    
    @pytest.mark.asyncio
    async def test_vector_search_skips_entities_without_embeddings(self, graph_store):
        """Test that vector_search skips entities without embeddings"""
        # Add entity without embedding
        entity_no_embedding = Entity(
            id="person_1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        await graph_store.add_entity(entity_no_embedding)
        
        # Add entity with embedding
        entity_with_embedding = Entity(
            id="person_2",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=[0.1, 0.2, 0.3, 0.4, 0.5]
        )
        await graph_store.add_entity(entity_with_embedding)
        
        # Perform vector search
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        results = await graph_store.vector_search(
            query_embedding=query_embedding,
            max_results=10,
            score_threshold=0.0
        )
        
        # Should only return entity with embedding
        assert len(results) == 1
        assert results[0][0].id == "person_2"

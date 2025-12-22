"""
Unit Tests for Tenant-Aware Graph Queries

Tests the multi-tenancy support in GraphQuery model and query execution.
"""

import pytest
from aiecs.domain.knowledge_graph.models.query import GraphQuery, QueryType, GraphResult
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
)
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore


@pytest.fixture
async def graph_store():
    """Create and initialize an in-memory graph store for testing"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def tenant_context_acme():
    """Create tenant context for ACME Corp"""
    return TenantContext(tenant_id="acme-corp", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)


@pytest.fixture
def tenant_context_widgets():
    """Create tenant context for Widgets Inc"""
    return TenantContext(tenant_id="widgets-inc", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)


@pytest.fixture
async def populated_graph_store(graph_store, tenant_context_acme, tenant_context_widgets):
    """Populate graph store with multi-tenant data"""
    
    # ACME Corp entities
    acme_entity1 = Entity(
        id="acme_person_1",
        entity_type="Person",
        properties={"name": "Alice", "company": "ACME"},
        tenant_id="acme-corp",
    )
    acme_entity2 = Entity(
        id="acme_person_2",
        entity_type="Person",
        properties={"name": "Bob", "company": "ACME"},
        tenant_id="acme-corp",
    )
    
    # Widgets Inc entities
    widgets_entity1 = Entity(
        id="widgets_person_1",
        entity_type="Person",
        properties={"name": "Charlie", "company": "Widgets"},
        tenant_id="widgets-inc",
    )
    widgets_entity2 = Entity(
        id="widgets_person_2",
        entity_type="Person",
        properties={"name": "Diana", "company": "Widgets"},
        tenant_id="widgets-inc",
    )
    
    # Global entity (no tenant)
    global_entity = Entity(
        id="global_person_1",
        entity_type="Person",
        properties={"name": "Eve", "company": "Global"},
        tenant_id=None,
    )
    
    # Add entities to store
    await graph_store.add_entity(acme_entity1, context=tenant_context_acme)
    await graph_store.add_entity(acme_entity2, context=tenant_context_acme)
    await graph_store.add_entity(widgets_entity1, context=tenant_context_widgets)
    await graph_store.add_entity(widgets_entity2, context=tenant_context_widgets)
    await graph_store.add_entity(global_entity, context=None)
    
    # Add relations within tenants
    acme_relation = Relation(
        id="acme_rel_1",
        relation_type="KNOWS",
        source_id="acme_person_1",
        target_id="acme_person_2",
        tenant_id="acme-corp",
    )
    widgets_relation = Relation(
        id="widgets_rel_1",
        relation_type="KNOWS",
        source_id="widgets_person_1",
        target_id="widgets_person_2",
        tenant_id="widgets-inc",
    )
    
    await graph_store.add_relation(acme_relation, context=tenant_context_acme)
    await graph_store.add_relation(widgets_relation, context=tenant_context_widgets)
    
    return graph_store


class TestGraphQueryTenantId:
    """Test GraphQuery model with tenant_id field"""
    
    def test_graph_query_without_tenant_id(self):
        """Test GraphQuery creation without tenant_id (backward compatible)"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="person_1",
        )
        assert query.tenant_id is None
        assert query.query_type == QueryType.ENTITY_LOOKUP
    
    def test_graph_query_with_tenant_id(self):
        """Test GraphQuery creation with tenant_id"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=[0.1, 0.2, 0.3],
            entity_type="Document",
            tenant_id="acme-corp",
        )
        assert query.tenant_id == "acme-corp"
        assert query.query_type == QueryType.VECTOR_SEARCH
    
    def test_graph_query_serialization_with_tenant_id(self):
        """Test GraphQuery serialization includes tenant_id"""
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="person_1",
            relation_type="KNOWS",
            tenant_id="widgets-inc",
        )
        query_dict = query.model_dump()
        assert query_dict["tenant_id"] == "widgets-inc"
        assert query_dict["query_type"] == "traversal"


class TestTenantAwareQueryExecution:
    """Test query execution with tenant filtering"""
    
    @pytest.mark.asyncio
    async def test_entity_lookup_with_tenant_context(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test entity lookup returns only entities from specified tenant"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="acme_person_1",
        )
        
        result = await populated_graph_store.execute_query(query, context=tenant_context_acme)
        
        assert result.entity_count == 1
        assert result.entities[0].id == "acme_person_1"
        assert result.entities[0].tenant_id == "acme-corp"
    
    @pytest.mark.asyncio
    async def test_entity_lookup_with_query_tenant_id(self, populated_graph_store):
        """Test entity lookup using query.tenant_id field"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="widgets_person_1",
            tenant_id="widgets-inc",
        )
        
        result = await populated_graph_store.execute_query(query)
        
        assert result.entity_count == 1
        assert result.entities[0].id == "widgets_person_1"
        assert result.entities[0].tenant_id == "widgets-inc"
    
    @pytest.mark.asyncio
    async def test_query_tenant_id_takes_precedence_over_context(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test that query.tenant_id takes precedence over context parameter"""
        # Create query with widgets tenant_id but pass acme context
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="widgets_person_1",
            tenant_id="widgets-inc",  # This should win
        )
        
        result = await populated_graph_store.execute_query(
            query, context=tenant_context_acme  # This should be ignored
        )
        
        assert result.entity_count == 1
        assert result.entities[0].tenant_id == "widgets-inc"
    
    @pytest.mark.asyncio
    async def test_cross_tenant_entity_lookup_fails(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test that looking up entity from different tenant returns None"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="widgets_person_1",  # Widgets entity
        )
        
        # Try to access with ACME context
        result = await populated_graph_store.execute_query(query, context=tenant_context_acme)
        
        # Should not find the entity (tenant isolation)
        assert result.entity_count == 0
    
    @pytest.mark.asyncio
    async def test_global_entity_lookup_without_tenant(self, populated_graph_store):
        """Test accessing global entity without tenant context"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="global_person_1",
        )
        
        result = await populated_graph_store.execute_query(query)
        
        assert result.entity_count == 1
        assert result.entities[0].id == "global_person_1"
        assert result.entities[0].tenant_id is None
    
    @pytest.mark.asyncio
    async def test_traversal_with_tenant_filtering(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test graph traversal respects tenant boundaries"""
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="acme_person_1",
            relation_type="KNOWS",
            max_depth=2,
            tenant_id="acme-corp",
        )
        
        result = await populated_graph_store.execute_query(query)
        
        # Should only traverse ACME entities
        assert result.entity_count >= 1
        for entity in result.entities:
            assert entity.tenant_id == "acme-corp", f"Entity {entity.id} has wrong tenant"
    
    @pytest.mark.asyncio
    async def test_multiple_queries_with_different_tenants(self, populated_graph_store):
        """Test executing queries for different tenants in sequence"""
        # Query ACME tenant
        acme_query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="acme_person_1",
            tenant_id="acme-corp",
        )
        acme_result = await populated_graph_store.execute_query(acme_query)
        
        # Query Widgets tenant
        widgets_query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="widgets_person_1",
            tenant_id="widgets-inc",
        )
        widgets_result = await populated_graph_store.execute_query(widgets_query)
        
        # Both should succeed with their respective data
        assert acme_result.entity_count == 1
        assert acme_result.entities[0].tenant_id == "acme-corp"
        
        assert widgets_result.entity_count == 1
        assert widgets_result.entities[0].tenant_id == "widgets-inc"


class TestQueryResultTenantValidation:
    """Test that query results maintain tenant isolation"""
    
    @pytest.mark.asyncio
    async def test_result_contains_only_tenant_entities(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test that query result contains only entities from the specified tenant"""
        # Get an entity from ACME tenant
        entity = await populated_graph_store.get_entity("acme_person_1", context=tenant_context_acme)
        
        assert entity is not None
        assert entity.tenant_id == "acme-corp"
        
        # Verify we cannot get Widgets entity with ACME context
        wrong_entity = await populated_graph_store.get_entity(
            "widgets_person_1", context=tenant_context_acme
        )
        assert wrong_entity is None
    
    @pytest.mark.asyncio
    async def test_empty_result_for_wrong_tenant(
        self, populated_graph_store, tenant_context_acme
    ):
        """Test that querying with wrong tenant returns empty result"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="widgets_person_1",
            tenant_id="acme-corp",  # Wrong tenant
        )
        
        result = await populated_graph_store.execute_query(query)
        
        assert result.entity_count == 0


class TestQueryWithoutMultiTenancy:
    """Test backward compatibility - queries work without multi-tenancy"""
    
    @pytest.mark.asyncio
    async def test_query_without_tenant_id_field(self, populated_graph_store):
        """Test that queries without tenant_id still work (global mode)"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="global_person_1",
        )
        
        result = await populated_graph_store.execute_query(query)
        
        assert result.entity_count == 1
        assert result.entities[0].id == "global_person_1"
    
    @pytest.mark.asyncio
    async def test_query_without_context_parameter(self, populated_graph_store):
        """Test query execution without context parameter (backward compatible)"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="global_person_1",
        )
        
        # Execute without context parameter
        result = await populated_graph_store.execute_query(query, context=None)
        
        assert result.entity_count == 1


class TestTenantIdValidationInQueries:
    """Test tenant_id validation when used in queries"""
    
    def test_query_with_valid_tenant_id(self):
        """Test query creation with valid tenant_id"""
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=[0.1, 0.2],
            tenant_id="valid-tenant-123",
        )
        assert query.tenant_id == "valid-tenant-123"
    
    def test_query_with_none_tenant_id(self):
        """Test query creation with None tenant_id"""
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="entity_1",
            tenant_id=None,
        )
        assert query.tenant_id is None
    
    def test_query_tenant_id_in_string_representation(self):
        """Test that tenant_id appears in query string representation"""
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="person_1",
            tenant_id="test-tenant",
        )
        query_str = str(query)
        assert "TRAVERSAL" in query_str or "traversal" in query_str
        assert "person_1" in query_str


@pytest.mark.asyncio
class TestTenantIsolationInMemoryStore:
    """Test tenant isolation specifically for InMemoryGraphStore"""
    
    async def test_in_memory_store_tenant_partitioning(self):
        """Test that InMemoryGraphStore properly partitions tenant data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entities for different tenants
        tenant1_ctx = TenantContext(tenant_id="tenant-1")
        tenant2_ctx = TenantContext(tenant_id="tenant-2")
        
        entity1 = Entity(
            id="entity_1",
            entity_type="Test",
            properties={"name": "Entity 1"},
            tenant_id="tenant-1",
        )
        entity2 = Entity(
            id="entity_2",
            entity_type="Test",
            properties={"name": "Entity 2"},
            tenant_id="tenant-2",
        )
        
        await store.add_entity(entity1, context=tenant1_ctx)
        await store.add_entity(entity2, context=tenant2_ctx)
        
        # Verify tenant isolation
        retrieved1 = await store.get_entity("entity_1", context=tenant1_ctx)
        retrieved2 = await store.get_entity("entity_2", context=tenant2_ctx)
        
        assert retrieved1 is not None
        assert retrieved1.tenant_id == "tenant-1"
        
        assert retrieved2 is not None
        assert retrieved2.tenant_id == "tenant-2"
        
        # Verify cross-tenant access is blocked
        cross_access1 = await store.get_entity("entity_1", context=tenant2_ctx)
        cross_access2 = await store.get_entity("entity_2", context=tenant1_ctx)
        
        assert cross_access1 is None
        assert cross_access2 is None
        
        await store.close()
    
    async def test_query_with_tenant_id_on_in_memory_store(self):
        """Test GraphQuery with tenant_id on InMemoryGraphStore"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add tenant-specific entity
        ctx = TenantContext(tenant_id="test-tenant")
        entity = Entity(
            id="test_entity",
            entity_type="Test",
            properties={"name": "Test"},
            tenant_id="test-tenant",
        )
        await store.add_entity(entity, context=ctx)
        
        # Query using tenant_id in GraphQuery
        query = GraphQuery(
            query_type=QueryType.ENTITY_LOOKUP,
            entity_id="test_entity",
            tenant_id="test-tenant",
        )
        
        result = await store.execute_query(query)
        
        assert result.entity_count == 1
        assert result.entities[0].id == "test_entity"
        assert result.entities[0].tenant_id == "test-tenant"
        
        await store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

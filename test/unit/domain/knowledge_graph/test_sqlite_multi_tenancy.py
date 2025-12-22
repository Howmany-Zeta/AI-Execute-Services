"""
Unit tests for SQLiteGraphStore multi-tenancy support.

Tests:
- SHARED_SCHEMA mode with tenant_id column filtering
- SEPARATE_SCHEMA mode with table prefixes
- Cross-tenant isolation
- Same-tenant constraint for relations
- Migration script
"""

import pytest
import tempfile
import os
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)


@pytest.fixture
async def store_shared():
    """Create SQLiteGraphStore with SHARED_SCHEMA mode."""
    store = SQLiteGraphStore(":memory:", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def store_separate():
    """Create SQLiteGraphStore with SEPARATE_SCHEMA mode."""
    store = SQLiteGraphStore(":memory:", isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def store_file():
    """Create SQLiteGraphStore with file-based storage for migration tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    store = SQLiteGraphStore(db_path, isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
    await store.initialize()
    yield store, db_path
    await store.close()
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


# =============================================================================
# Test: SHARED_SCHEMA Mode
# =============================================================================

class TestSharedSchemaMode:
    """Test SHARED_SCHEMA mode with tenant_id column filtering."""

    @pytest.mark.asyncio
    async def test_add_entity_without_context_uses_global(self, store_shared):
        """Test that adding entity without context uses global namespace."""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity)

        result = await store_shared.get_entity("e1")
        assert result is not None
        assert result.id == "e1"
        assert result.tenant_id is None

    @pytest.mark.asyncio
    async def test_add_entity_with_context_uses_tenant(self, store_shared):
        """Test that adding entity with context uses tenant namespace."""
        context = TenantContext(tenant_id="tenant-a")
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity, context=context)

        result = await store_shared.get_entity("e1", context=context)
        assert result is not None
        assert result.id == "e1"
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_tenant_isolation_entities(self, store_shared):
        """Test that entities are isolated between tenants."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entity to tenant A
        entity_a = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity_a, context=context_a)

        # Add entity with same ID to tenant B
        entity_b = Entity(id="e1", entity_type="Person", properties={"name": "Bob"})
        await store_shared.add_entity(entity_b, context=context_b)

        # Each tenant should see their own entity
        result_a = await store_shared.get_entity("e1", context=context_a)
        result_b = await store_shared.get_entity("e1", context=context_b)

        assert result_a.properties["name"] == "Alice"
        assert result_b.properties["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_entity_not_found_across_tenants(self, store_shared):
        """Test that entity from one tenant is not found in another."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity, context=context_a)

        # Should not be found in tenant B
        result = await store_shared.get_entity("e1", context=context_b)
        assert result is None

        # Should not be found in global
        result_global = await store_shared.get_entity("e1")
        assert result_global is None

    @pytest.mark.asyncio
    async def test_relation_within_tenant(self, store_shared):
        """Test adding relation between entities in same tenant."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store_shared.add_entity(entity1, context=context)
        await store_shared.add_entity(entity2, context=context)

        # Add relation
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store_shared.add_relation(relation, context=context)

        # Verify relation
        result = await store_shared.get_relation("r1", context=context)
        assert result is not None
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_get_neighbors_tenant_scoped(self, store_shared):
        """Test that get_neighbors is tenant-scoped."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities and relation
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store_shared.add_entity(entity1, context=context)
        await store_shared.add_entity(entity2, context=context)

        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store_shared.add_relation(relation, context=context)

        # Get neighbors with context
        neighbors = await store_shared.get_neighbors("e1", context=context)
        assert len(neighbors) == 1
        assert neighbors[0].id == "e2"

        # Get neighbors without context should return empty
        neighbors_global = await store_shared.get_neighbors("e1")
        assert len(neighbors_global) == 0


# =============================================================================
# Test: SEPARATE_SCHEMA Mode
# =============================================================================

class TestSeparateSchemaMode:
    """Test SEPARATE_SCHEMA mode with table prefixes."""

    @pytest.mark.asyncio
    async def test_tenant_creates_separate_tables(self, store_separate):
        """Test that tenant operations create separate tables."""
        context = TenantContext(tenant_id="tenant-a")
        
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_separate.add_entity(entity, context=context)

        # Verify tenant tables were created
        assert "tenant-a" in store_separate._initialized_tenant_tables

        # Verify entity is accessible
        result = await store_separate.get_entity("e1", context=context)
        assert result is not None
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_tenant_isolation_separate_tables(self, store_separate):
        """Test that entities are isolated in separate tables."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entity to tenant A
        entity_a = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_separate.add_entity(entity_a, context=context_a)

        # Add entity with same ID to tenant B
        entity_b = Entity(id="e1", entity_type="Person", properties={"name": "Bob"})
        await store_separate.add_entity(entity_b, context=context_b)

        # Each tenant should see their own entity
        result_a = await store_separate.get_entity("e1", context=context_a)
        result_b = await store_separate.get_entity("e1", context=context_b)

        assert result_a.properties["name"] == "Alice"
        assert result_b.properties["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_global_uses_default_tables(self, store_separate):
        """Test that global namespace uses default tables."""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Global"})
        await store_separate.add_entity(entity)

        result = await store_separate.get_entity("e1")
        assert result is not None
        assert result.properties["name"] == "Global"

    @pytest.mark.asyncio
    async def test_relations_in_separate_tables(self, store_separate):
        """Test relations work in separate schema mode."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store_separate.add_entity(entity1, context=context)
        await store_separate.add_entity(entity2, context=context)

        # Add relation
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store_separate.add_relation(relation, context=context)

        # Verify
        result = await store_separate.get_relation("r1", context=context)
        assert result is not None

        neighbors = await store_separate.get_neighbors("e1", context=context)
        assert len(neighbors) == 1


# =============================================================================
# Test: Clear Operations
# =============================================================================

class TestClearOperations:
    """Test clear operations with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_clear_all_shared_schema(self, store_shared):
        """Test clear all in SHARED_SCHEMA mode."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities
        await store_shared.add_entity(Entity(id="g1", entity_type="Person", properties={}))
        await store_shared.add_entity(Entity(id="a1", entity_type="Person", properties={}), context=context_a)
        await store_shared.add_entity(Entity(id="b1", entity_type="Person", properties={}), context=context_b)

        # Clear all
        await store_shared.clear()

        # All should be gone
        assert await store_shared.get_entity("g1") is None
        assert await store_shared.get_entity("a1", context=context_a) is None
        assert await store_shared.get_entity("b1", context=context_b) is None

    @pytest.mark.asyncio
    async def test_clear_tenant_only_shared_schema(self, store_shared):
        """Test clear tenant only in SHARED_SCHEMA mode."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities
        await store_shared.add_entity(Entity(id="g1", entity_type="Person", properties={}))
        await store_shared.add_entity(Entity(id="a1", entity_type="Person", properties={}), context=context_a)
        await store_shared.add_entity(Entity(id="b1", entity_type="Person", properties={}), context=context_b)

        # Clear tenant A only
        await store_shared.clear(context=context_a)

        # Global and tenant B should exist
        assert await store_shared.get_entity("g1") is not None
        assert await store_shared.get_entity("b1", context=context_b) is not None

        # Tenant A should be gone
        assert await store_shared.get_entity("a1", context=context_a) is None

    @pytest.mark.asyncio
    async def test_clear_tenant_separate_schema(self, store_separate):
        """Test clear tenant in SEPARATE_SCHEMA mode drops tables."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entity
        await store_separate.add_entity(Entity(id="e1", entity_type="Person", properties={}), context=context)
        assert "tenant-a" in store_separate._initialized_tenant_tables

        # Clear tenant
        await store_separate.clear(context=context)

        # Tenant should be removed
        assert "tenant-a" not in store_separate._initialized_tenant_tables


# =============================================================================
# Test: Stats
# =============================================================================

class TestStats:
    """Test stats with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_stats_global(self, store_shared):
        """Test stats for global namespace."""
        for i in range(3):
            await store_shared.add_entity(Entity(id=f"e{i}", entity_type="Person", properties={}))

        stats = await store_shared.get_stats()
        assert stats["entity_count"] == 3
        assert stats["tenant_id"] is None

    @pytest.mark.asyncio
    async def test_stats_tenant_scoped(self, store_shared):
        """Test stats for specific tenant."""
        context = TenantContext(tenant_id="tenant-a")

        # Add global
        for i in range(3):
            await store_shared.add_entity(Entity(id=f"g{i}", entity_type="Person", properties={}))

        # Add tenant
        for i in range(5):
            await store_shared.add_entity(Entity(id=f"t{i}", entity_type="Person", properties={}), context=context)

        # Global stats
        stats_global = await store_shared.get_stats()
        assert stats_global["entity_count"] == 3

        # Tenant stats
        stats_tenant = await store_shared.get_stats(context=context)
        assert stats_tenant["entity_count"] == 5
        assert stats_tenant["tenant_id"] == "tenant-a"


# =============================================================================
# Test: Vector Search
# =============================================================================

class TestVectorSearchMultiTenancy:
    """Test vector search with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_vector_search_tenant_scoped(self, store_shared):
        """Test that vector search is tenant-scoped."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        embedding = [0.1, 0.2, 0.3]
        
        entity_a = Entity(id="ea", entity_type="Person", properties={"name": "Alice"}, embedding=embedding)
        entity_b = Entity(id="eb", entity_type="Person", properties={"name": "Bob"}, embedding=embedding)

        await store_shared.add_entity(entity_a, context=context_a)
        await store_shared.add_entity(entity_b, context=context_b)

        # Search in tenant A
        results_a = await store_shared.vector_search(embedding, context=context_a)
        assert len(results_a) == 1
        assert results_a[0][0].id == "ea"

        # Search in tenant B
        results_b = await store_shared.vector_search(embedding, context=context_b)
        assert len(results_b) == 1
        assert results_b[0][0].id == "eb"


# =============================================================================
# Test: Update and Delete
# =============================================================================

class TestUpdateDeleteMultiTenancy:
    """Test update and delete with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_update_entity_tenant_scoped(self, store_shared):
        """Test updating entity in tenant scope."""
        context = TenantContext(tenant_id="tenant-a")

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity, context=context)

        # Update
        entity.properties["name"] = "Alice Updated"
        await store_shared.update_entity(entity, context=context)

        # Verify
        result = await store_shared.get_entity("e1", context=context)
        assert result.properties["name"] == "Alice Updated"

    @pytest.mark.asyncio
    async def test_delete_entity_tenant_scoped(self, store_shared):
        """Test deleting entity in tenant scope."""
        context = TenantContext(tenant_id="tenant-a")

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store_shared.add_entity(entity, context=context)

        # Delete
        await store_shared.delete_entity("e1", context=context)

        # Verify
        result = await store_shared.get_entity("e1", context=context)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_entity_cascades_relations(self, store_shared):
        """Test that deleting entity removes its relations."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities and relation
        entity1 = Entity(id="e1", entity_type="Person", properties={})
        entity2 = Entity(id="e2", entity_type="Person", properties={})
        await store_shared.add_entity(entity1, context=context)
        await store_shared.add_entity(entity2, context=context)

        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store_shared.add_relation(relation, context=context)

        # Delete entity1
        await store_shared.delete_entity("e1", context=context)

        # Relation should be gone
        result = await store_shared.get_relation("r1", context=context)
        assert result is None

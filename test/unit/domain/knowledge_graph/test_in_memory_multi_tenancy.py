"""
Unit tests for InMemoryGraphStore multi-tenancy support.

Tests:
- Tenant-partitioned storage
- LRU eviction behavior
- Cross-tenant isolation
- Same-tenant constraint for relations
"""

import pytest
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)


@pytest.fixture
async def store():
    """Create and initialize an InMemoryGraphStore."""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def store_with_lru():
    """Create an InMemoryGraphStore with small LRU limit for testing eviction."""
    store = InMemoryGraphStore(max_tenant_graphs=3)
    await store.initialize()
    yield store
    await store.close()


# =============================================================================
# Test: Basic Multi-Tenancy Operations
# =============================================================================

class TestBasicMultiTenancy:
    """Test basic multi-tenancy operations."""

    @pytest.mark.asyncio
    async def test_add_entity_without_context_uses_global(self, store):
        """Test that adding entity without context uses global namespace."""
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        # Should be accessible without context
        result = await store.get_entity("e1")
        assert result is not None
        assert result.id == "e1"

    @pytest.mark.asyncio
    async def test_add_entity_with_context_uses_tenant(self, store):
        """Test that adding entity with context uses tenant namespace."""
        context = TenantContext(tenant_id="tenant-a")
        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity, context=context)

        # Should be accessible with same context
        result = await store.get_entity("e1", context=context)
        assert result is not None
        assert result.id == "e1"
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_tenant_isolation_entities(self, store):
        """Test that entities are isolated between tenants."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entity to tenant A
        entity_a = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity_a, context=context_a)

        # Add entity with same ID to tenant B
        entity_b = Entity(id="e1", entity_type="Person", properties={"name": "Bob"})
        await store.add_entity(entity_b, context=context_b)

        # Each tenant should see their own entity
        result_a = await store.get_entity("e1", context=context_a)
        result_b = await store.get_entity("e1", context=context_b)

        assert result_a.properties["name"] == "Alice"
        assert result_b.properties["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_global_isolation_from_tenants(self, store):
        """Test that global namespace is isolated from tenants."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entity to global
        global_entity = Entity(id="e1", entity_type="Person", properties={"name": "Global"})
        await store.add_entity(global_entity)

        # Add entity to tenant
        tenant_entity = Entity(id="e1", entity_type="Person", properties={"name": "Tenant"})
        await store.add_entity(tenant_entity, context=context)

        # Should be isolated
        result_global = await store.get_entity("e1")
        result_tenant = await store.get_entity("e1", context=context)

        assert result_global.properties["name"] == "Global"
        assert result_tenant.properties["name"] == "Tenant"

    @pytest.mark.asyncio
    async def test_entity_not_found_across_tenants(self, store):
        """Test that entity from one tenant is not found in another."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity, context=context_a)

        # Should not be found in tenant B
        result = await store.get_entity("e1", context=context_b)
        assert result is None

        # Should not be found in global
        result_global = await store.get_entity("e1")
        assert result_global is None


# =============================================================================
# Test: Relations with Multi-Tenancy
# =============================================================================

class TestRelationsMultiTenancy:
    """Test relation operations with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_add_relation_within_tenant(self, store):
        """Test adding relation between entities in same tenant."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store.add_entity(entity1, context=context)
        await store.add_entity(entity2, context=context)

        # Add relation
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
        )
        await store.add_relation(relation, context=context)

        # Should be accessible
        result = await store.get_relation("r1", context=context)
        assert result is not None
        assert result.tenant_id == "tenant-a"

    @pytest.mark.asyncio
    async def test_relation_source_not_found_in_tenant(self, store):
        """Test that relation fails if source entity not in tenant."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add source in tenant A, target in tenant B
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store.add_entity(entity1, context=context_a)
        await store.add_entity(entity2, context=context_b)

        # Try to add relation in tenant B (source e1 doesn't exist there)
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2",
        )
        with pytest.raises(ValueError, match="Source entity .* not found"):
            await store.add_relation(relation, context=context_b)

    @pytest.mark.asyncio
    async def test_relation_isolation_between_tenants(self, store):
        """Test that relations are isolated between tenants."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Setup tenant A
        entity_a1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity_a2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store.add_entity(entity_a1, context=context_a)
        await store.add_entity(entity_a2, context=context_a)
        relation_a = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(relation_a, context=context_a)

        # Setup tenant B with same IDs
        entity_b1 = Entity(id="e1", entity_type="Person", properties={"name": "Charlie"})
        entity_b2 = Entity(id="e2", entity_type="Person", properties={"name": "Diana"})
        await store.add_entity(entity_b1, context=context_b)
        await store.add_entity(entity_b2, context=context_b)
        relation_b = Relation(id="r1", relation_type="WORKS_WITH", source_id="e1", target_id="e2")
        await store.add_relation(relation_b, context=context_b)

        # Verify isolation
        result_a = await store.get_relation("r1", context=context_a)
        result_b = await store.get_relation("r1", context=context_b)

        assert result_a.relation_type == "KNOWS"
        assert result_b.relation_type == "WORKS_WITH"


# =============================================================================
# Test: LRU Eviction
# =============================================================================

class TestLRUEviction:
    """Test LRU eviction behavior."""

    @pytest.mark.asyncio
    async def test_tenant_count_increases(self, store_with_lru):
        """Test that tenant count increases as tenants are added."""
        assert store_with_lru.get_tenant_count() == 0

        for i in range(3):
            context = TenantContext(tenant_id=f"tenant-{i}")
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            await store_with_lru.add_entity(entity, context=context)

        assert store_with_lru.get_tenant_count() == 3

    @pytest.mark.asyncio
    async def test_lru_eviction_when_max_exceeded(self, store_with_lru):
        """Test that LRU eviction happens when max_tenant_graphs exceeded."""
        # Add 3 tenants (max is 3)
        for i in range(3):
            context = TenantContext(tenant_id=f"tenant-{i}")
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            await store_with_lru.add_entity(entity, context=context)

        assert store_with_lru.get_tenant_count() == 3
        assert "tenant-0" in store_with_lru.get_tenant_ids()

        # Add 4th tenant - should evict tenant-0 (LRU)
        context = TenantContext(tenant_id="tenant-3")
        entity = Entity(id="e3", entity_type="Person", properties={"name": "Person3"})
        await store_with_lru.add_entity(entity, context=context)

        assert store_with_lru.get_tenant_count() == 3
        assert "tenant-0" not in store_with_lru.get_tenant_ids()
        assert "tenant-3" in store_with_lru.get_tenant_ids()

    @pytest.mark.asyncio
    async def test_lru_access_updates_order(self, store_with_lru):
        """Test that accessing a tenant updates its LRU position."""
        # Add 3 tenants
        for i in range(3):
            context = TenantContext(tenant_id=f"tenant-{i}")
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            await store_with_lru.add_entity(entity, context=context)

        # Access tenant-0 to make it most recently used
        context_0 = TenantContext(tenant_id="tenant-0")
        await store_with_lru.get_entity("e0", context=context_0)

        # Add tenant-3 - should evict tenant-1 (now LRU)
        context = TenantContext(tenant_id="tenant-3")
        entity = Entity(id="e3", entity_type="Person", properties={"name": "Person3"})
        await store_with_lru.add_entity(entity, context=context)

        # tenant-0 should still exist, tenant-1 should be evicted
        assert "tenant-0" in store_with_lru.get_tenant_ids()
        assert "tenant-1" not in store_with_lru.get_tenant_ids()
        assert "tenant-2" in store_with_lru.get_tenant_ids()
        assert "tenant-3" in store_with_lru.get_tenant_ids()

    @pytest.mark.asyncio
    async def test_global_graph_never_evicted(self, store_with_lru):
        """Test that global graph is never evicted."""
        # Add entity to global
        global_entity = Entity(id="global", entity_type="Person", properties={"name": "Global"})
        await store_with_lru.add_entity(global_entity)

        # Fill up tenant slots and cause evictions
        for i in range(5):
            context = TenantContext(tenant_id=f"tenant-{i}")
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            await store_with_lru.add_entity(entity, context=context)

        # Global entity should still be accessible
        result = await store_with_lru.get_entity("global")
        assert result is not None
        assert result.properties["name"] == "Global"

    @pytest.mark.asyncio
    async def test_evicted_tenant_data_cleared(self, store_with_lru):
        """Test that evicted tenant's data is completely cleared."""
        # Add tenant-0 with entity and relation
        context_0 = TenantContext(tenant_id="tenant-0")
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store_with_lru.add_entity(entity1, context=context_0)
        await store_with_lru.add_entity(entity2, context=context_0)
        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store_with_lru.add_relation(relation, context=context_0)

        # Add more tenants to trigger eviction
        for i in range(1, 4):
            context = TenantContext(tenant_id=f"tenant-{i}")
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"Person{i}"})
            await store_with_lru.add_entity(entity, context=context)

        # tenant-0 should be evicted
        assert "tenant-0" not in store_with_lru.get_tenant_ids()

        # Re-adding tenant-0 should start fresh
        context_0_new = TenantContext(tenant_id="tenant-0")
        new_entity = Entity(id="new", entity_type="Person", properties={"name": "New"})
        await store_with_lru.add_entity(new_entity, context=context_0_new)

        # Old entities should not exist
        assert await store_with_lru.get_entity("e1", context=context_0_new) is None
        assert await store_with_lru.get_entity("e2", context=context_0_new) is None
        assert await store_with_lru.get_relation("r1", context=context_0_new) is None

        # New entity should exist
        assert await store_with_lru.get_entity("new", context=context_0_new) is not None


# =============================================================================
# Test: Query Operations with Multi-Tenancy
# =============================================================================

class TestQueryMultiTenancy:
    """Test query operations with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_get_all_entities_tenant_scoped(self, store):
        """Test that get_all_entities is tenant-scoped."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities to different tenants
        for i in range(3):
            entity = Entity(id=f"a{i}", entity_type="Person", properties={"name": f"A{i}"})
            await store.add_entity(entity, context=context_a)

        for i in range(2):
            entity = Entity(id=f"b{i}", entity_type="Person", properties={"name": f"B{i}"})
            await store.add_entity(entity, context=context_b)

        # Verify scoped results
        entities_a = await store.get_all_entities(context=context_a)
        entities_b = await store.get_all_entities(context=context_b)

        assert len(entities_a) == 3
        assert len(entities_b) == 2

    @pytest.mark.asyncio
    async def test_get_neighbors_tenant_scoped(self, store):
        """Test that get_neighbors is tenant-scoped."""
        context = TenantContext(tenant_id="tenant-a")

        # Add entities and relation
        entity1 = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        entity2 = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        await store.add_entity(entity1, context=context)
        await store.add_entity(entity2, context=context)

        relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
        await store.add_relation(relation, context=context)

        # Get neighbors with context
        neighbors = await store.get_neighbors("e1", context=context)
        assert len(neighbors) == 1
        assert neighbors[0].id == "e2"

        # Get neighbors without context should return empty (different namespace)
        neighbors_global = await store.get_neighbors("e1")
        assert len(neighbors_global) == 0

    @pytest.mark.asyncio
    async def test_find_paths_tenant_scoped(self, store):
        """Test that find_paths is tenant-scoped."""
        context = TenantContext(tenant_id="tenant-a")

        # Build a simple path: e1 -> e2 -> e3
        entities = [
            Entity(id=f"e{i}", entity_type="Person", properties={"name": f"P{i}"})
            for i in range(3)
        ]
        for entity in entities:
            await store.add_entity(entity, context=context)

        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e0", target_id="e1"),
            Relation(id="r2", relation_type="KNOWS", source_id="e1", target_id="e2"),
        ]
        for relation in relations:
            await store.add_relation(relation, context=context)

        # Find paths with context
        paths = await store.find_paths("e0", "e2", context=context)
        assert len(paths) == 1
        assert len(paths[0].nodes) == 3

        # Find paths without context should return empty
        paths_global = await store.find_paths("e0", "e2")
        assert len(paths_global) == 0


# =============================================================================
# Test: Clear Operations with Multi-Tenancy
# =============================================================================

class TestClearMultiTenancy:
    """Test clear operations with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_clear_all_clears_global_and_tenants(self, store):
        """Test that clear without context clears all data."""
        # Add global entity
        global_entity = Entity(id="global", entity_type="Person", properties={"name": "Global"})
        await store.add_entity(global_entity)

        # Add tenant entity
        context = TenantContext(tenant_id="tenant-a")
        tenant_entity = Entity(id="tenant", entity_type="Person", properties={"name": "Tenant"})
        await store.add_entity(tenant_entity, context=context)

        # Clear all
        await store.clear()

        # Both should be gone
        assert await store.get_entity("global") is None
        assert await store.get_entity("tenant", context=context) is None
        assert store.get_tenant_count() == 0

    @pytest.mark.asyncio
    async def test_clear_tenant_only_clears_tenant(self, store):
        """Test that clear with context only clears that tenant."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities
        global_entity = Entity(id="global", entity_type="Person", properties={"name": "Global"})
        await store.add_entity(global_entity)

        entity_a = Entity(id="ea", entity_type="Person", properties={"name": "A"})
        await store.add_entity(entity_a, context=context_a)

        entity_b = Entity(id="eb", entity_type="Person", properties={"name": "B"})
        await store.add_entity(entity_b, context=context_b)

        # Clear tenant A only
        await store.clear(context=context_a)

        # Global and tenant B should still exist
        assert await store.get_entity("global") is not None
        assert await store.get_entity("eb", context=context_b) is not None

        # Tenant A should be gone
        assert await store.get_entity("ea", context=context_a) is None
        assert "tenant-a" not in store.get_tenant_ids()


# =============================================================================
# Test: Environment Variable Configuration
# =============================================================================

class TestEnvironmentConfiguration:
    """Test environment variable configuration."""

    @pytest.mark.asyncio
    async def test_max_tenant_graphs_from_param(self):
        """Test that max_tenant_graphs can be set via parameter."""
        store = InMemoryGraphStore(max_tenant_graphs=5)
        assert store._max_tenant_graphs == 5

    @pytest.mark.asyncio
    async def test_default_max_tenant_graphs(self):
        """Test default max_tenant_graphs value."""
        store = InMemoryGraphStore()
        assert store._max_tenant_graphs == 100


# =============================================================================
# Test: Vector Search with Multi-Tenancy
# =============================================================================

class TestVectorSearchMultiTenancy:
    """Test vector search with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_vector_search_tenant_scoped(self, store):
        """Test that vector search is tenant-scoped."""
        context_a = TenantContext(tenant_id="tenant-a")
        context_b = TenantContext(tenant_id="tenant-b")

        # Add entities with embeddings
        embedding = [0.1, 0.2, 0.3]
        entity_a = Entity(
            id="ea",
            entity_type="Person",
            properties={"name": "Alice"},
            embedding=embedding,
        )
        entity_b = Entity(
            id="eb",
            entity_type="Person",
            properties={"name": "Bob"},
            embedding=embedding,
        )

        await store.add_entity(entity_a, context=context_a)
        await store.add_entity(entity_b, context=context_b)

        # Search in tenant A
        results_a = await store.vector_search(embedding, context=context_a)
        assert len(results_a) == 1
        assert results_a[0][0].id == "ea"

        # Search in tenant B
        results_b = await store.vector_search(embedding, context=context_b)
        assert len(results_b) == 1
        assert results_b[0][0].id == "eb"


# =============================================================================
# Test: Stats with Multi-Tenancy
# =============================================================================

class TestStatsMultiTenancy:
    """Test stats with multi-tenancy."""

    @pytest.mark.asyncio
    async def test_stats_global(self, store):
        """Test stats for global namespace."""
        # Add global entities
        for i in range(3):
            entity = Entity(id=f"e{i}", entity_type="Person", properties={"name": f"P{i}"})
            await store.add_entity(entity)

        stats = store.get_stats()
        assert stats["entities"] == 3

    @pytest.mark.asyncio
    async def test_stats_tenant_scoped(self, store):
        """Test stats for specific tenant."""
        context = TenantContext(tenant_id="tenant-a")

        # Add global entities
        for i in range(3):
            entity = Entity(id=f"g{i}", entity_type="Person", properties={"name": f"G{i}"})
            await store.add_entity(entity)

        # Add tenant entities
        for i in range(5):
            entity = Entity(id=f"t{i}", entity_type="Person", properties={"name": f"T{i}"})
            await store.add_entity(entity, context=context)

        # Global stats
        stats_global = store.get_stats()
        assert stats_global["entities"] == 3

        # Tenant stats
        stats_tenant = store.get_stats(context=context)
        assert stats_tenant["entities"] == 5

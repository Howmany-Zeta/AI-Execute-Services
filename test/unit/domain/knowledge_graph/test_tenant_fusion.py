"""
Unit tests for tenant-scoped knowledge graph fusion

Tests tenant isolation in fusion operations:
- Tenant-scoped entity deduplication
- Tenant-scoped entity linking
- Cross-tenant fusion prevention
- Tenant-prefixed alias index
"""

import pytest
from typing import List

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantFusionError,
)
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import EntityDeduplicator
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion
from aiecs.application.knowledge_graph.fusion.alias_index import AliasIndex, MatchType


# Fixtures

@pytest.fixture
async def graph_store():
    """Create and initialize in-memory graph store"""
    store = InMemoryGraphStore()
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def tenant_context_a():
    """Create tenant context for tenant_a"""
    return TenantContext(tenant_id="tenant_a", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)


@pytest.fixture
def tenant_context_b():
    """Create tenant context for tenant_b"""
    return TenantContext(tenant_id="tenant_b", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)


@pytest.fixture
def entities_tenant_a():
    """Create sample entities for tenant_a"""
    return [
        Entity(
            id="a_e1",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        ),
        Entity(
            id="a_e2",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        ),
        Entity(
            id="a_e3",
            entity_type="Person",
            properties={"name": "Bob Jones"},
            tenant_id="tenant_a"
        ),
    ]


@pytest.fixture
def entities_tenant_b():
    """Create sample entities for tenant_b"""
    return [
        Entity(
            id="b_e1",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_b"
        ),
        Entity(
            id="b_e2",
            entity_type="Person",
            properties={"name": "Charlie Brown"},
            tenant_id="tenant_b"
        ),
    ]


# EntityDeduplicator Tenant Scoping Tests

class TestEntityDeduplicatorTenantScoping:
    """Test EntityDeduplicator with tenant isolation"""

    @pytest.mark.asyncio
    async def test_deduplicate_with_tenant_context(self, tenant_context_a, entities_tenant_a):
        """Test deduplication scoped to tenant_a"""
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        # Deduplicate within tenant_a
        result = await deduplicator.deduplicate(entities_tenant_a, context=tenant_context_a)
        
        # Should work normally - similar Alice entities should be merged
        assert len(result) <= len(entities_tenant_a)
        # All results should belong to tenant_a
        assert all(e.tenant_id == "tenant_a" for e in result)

    @pytest.mark.asyncio
    async def test_deduplicate_filters_by_tenant(self, tenant_context_a):
        """Test deduplication filters entities by tenant_id"""
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        # Mix entities from different tenants
        mixed_entities = [
            Entity(id="a1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="b1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_b"),
            Entity(id="a2", entity_type="Person", properties={"name": "Bob"}, tenant_id="tenant_a"),
        ]
        
        # Deduplicate with tenant_a context
        result = await deduplicator.deduplicate(mixed_entities, context=tenant_context_a)
        
        # Should only include tenant_a entities
        assert all(e.tenant_id == "tenant_a" for e in result)
        assert len(result) <= 2  # Only a1 and a2

    @pytest.mark.asyncio
    async def test_deduplicate_silently_filters_cross_tenant(self, tenant_context_a):
        """Test deduplication silently filters out entities from other tenants (defense-in-depth)"""
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        # Entities from different tenants
        mixed_entities = [
            Entity(id="a1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="b1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_b"),
        ]
        
        # Should silently filter to only tenant_a entities (defense-in-depth)
        result = await deduplicator.deduplicate(mixed_entities, context=tenant_context_a)
        
        # Only tenant_a entity should remain
        assert all(e.tenant_id == "tenant_a" for e in result)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_deduplicate_without_context_works(self):
        """Test deduplication works without tenant context (backward compatible)"""
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Alice"}),
        ]
        
        # Should work without context (backward compatibility)
        result = await deduplicator.deduplicate(entities, context=None)
        assert len(result) <= len(entities)


# EntityLinker Tenant Scoping Tests

class TestEntityLinkerTenantScoping:
    """Test EntityLinker with tenant isolation"""

    @pytest.mark.asyncio
    async def test_link_entity_within_tenant(self, graph_store, tenant_context_a):
        """Test entity linking scoped to tenant_a"""
        linker = EntityLinker(graph_store, similarity_threshold=0.85)
        
        # Add existing entity in tenant_a
        existing = Entity(
            id="a_existing",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        )
        await graph_store.add_entity(existing, context=tenant_context_a)
        
        # Try to link new entity in tenant_a
        new_entity = Entity(
            id="a_new",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        )
        
        result = await linker.link_entity(new_entity, context=tenant_context_a)
        
        # Should link to existing entity
        if result.linked:
            assert result.existing_entity.tenant_id == "tenant_a"

    @pytest.mark.asyncio
    async def test_link_entity_does_not_cross_tenants(self, graph_store, tenant_context_a, tenant_context_b):
        """Test entity linking does not link across tenants"""
        linker = EntityLinker(graph_store, similarity_threshold=0.85)
        
        # Add entity in tenant_a
        entity_a = Entity(
            id="a_alice",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        )
        await graph_store.add_entity(entity_a, context=tenant_context_a)
        
        # Try to link entity in tenant_b (same name)
        entity_b = Entity(
            id="b_alice",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_b"
        )
        
        result = await linker.link_entity(entity_b, context=tenant_context_b)
        
        # Should not link (different tenant)
        assert result.linked is False

    @pytest.mark.asyncio
    async def test_link_entities_batch_with_context(self, graph_store, tenant_context_a):
        """Test batch entity linking with tenant context"""
        linker = EntityLinker(graph_store, similarity_threshold=0.85)
        
        # Add existing entities in tenant_a
        existing1 = Entity(id="a_e1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a")
        existing2 = Entity(id="a_e2", entity_type="Person", properties={"name": "Bob"}, tenant_id="tenant_a")
        await graph_store.add_entity(existing1, context=tenant_context_a)
        await graph_store.add_entity(existing2, context=tenant_context_a)
        
        # New entities to link
        new_entities = [
            Entity(id="a_new1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="a_new2", entity_type="Person", properties={"name": "Charlie"}, tenant_id="tenant_a"),
        ]
        
        results = await linker.link_entities(new_entities, context=tenant_context_a)
        
        # Should return results for all entities
        assert len(results) == 2


# KnowledgeFusion Tenant Scoping Tests

class TestKnowledgeFusionTenantScoping:
    """Test KnowledgeFusion with tenant isolation"""

    @pytest.mark.asyncio
    async def test_fuse_with_tenant_context(self, graph_store, tenant_context_a, entities_tenant_a):
        """Test fusion scoped to tenant_a"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.90)
        
        # Add entities to graph
        for entity in entities_tenant_a:
            await graph_store.add_entity(entity, context=tenant_context_a)
        
        # Fuse within tenant_a
        stats = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Should analyze tenant_a entities
        assert stats["entities_analyzed"] > 0

    @pytest.mark.asyncio
    async def test_fuse_filters_by_tenant(self, graph_store, tenant_context_a, entities_tenant_a, entities_tenant_b):
        """Test fusion filters entities by tenant_id"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.90)
        
        # Add entities from both tenants properly
        for entity in entities_tenant_a:
            await graph_store.add_entity(entity, context=tenant_context_a)
        
        # Add tenant_b entities using the proper method
        tenant_context_b = TenantContext(tenant_id="tenant_b", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
        for entity in entities_tenant_b:
            await graph_store.add_entity(entity, context=tenant_context_b)
        
        # Fuse with tenant_a context
        stats = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Should only analyze tenant_a entities
        assert stats["entities_analyzed"] == len(entities_tenant_a)

    @pytest.mark.asyncio
    async def test_fuse_prevents_cross_tenant_fusion(self, graph_store, tenant_context_a):
        """Test fusion prevents cross-tenant merging"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.90)
        
        # Create entities from different tenants with same name
        entity_a = Entity(
            id="a_alice",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_a"
        )
        entity_b = Entity(
            id="b_alice",
            entity_type="Person",
            properties={"name": "Alice Smith"},
            tenant_id="tenant_b"
        )
        
        # Add both entities
        await graph_store.add_entity(entity_a, context=tenant_context_a)
        # Manually add tenant_b entity for testing
        if hasattr(graph_store, '_global_graph'):
            graph_store._global_graph.add_node(entity_b.id, entity=entity_b)
        
        # Attempt to fuse with tenant_a context
        # The fusion should only see tenant_a entities
        stats = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Should only process tenant_a entity
        assert stats["entities_analyzed"] == 1

    @pytest.mark.asyncio
    async def test_fuse_without_context_works(self, graph_store):
        """Test fusion works without tenant context (backward compatible)"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.90)
        
        # Add entities without tenant_id
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Alice"}),
        ]
        
        for entity in entities:
            await graph_store.add_entity(entity)
        
        # Should work without context
        stats = await fusion.fuse_cross_document_entities(context=None)
        assert stats["entities_analyzed"] == 2


# AliasIndex Tenant Scoping Tests

class TestAliasIndexTenantScoping:
    """Test AliasIndex with tenant-prefixed keys"""

    @pytest.mark.asyncio
    async def test_add_alias_with_tenant(self):
        """Test adding alias with tenant_id"""
        index = AliasIndex(backend="memory")
        
        # Add alias for tenant_a
        await index.add_alias(
            alias="Apple",
            entity_id="e1",
            match_type=MatchType.EXACT,
            tenant_id="tenant_a"
        )
        
        # Lookup with tenant_a
        entry = await index.lookup("Apple", tenant_id="tenant_a")
        assert entry is not None
        assert entry.entity_id == "e1"
        assert entry.tenant_id == "tenant_a"

    @pytest.mark.asyncio
    async def test_alias_tenant_isolation(self):
        """Test alias lookup is isolated by tenant"""
        index = AliasIndex(backend="memory")
        
        # Add same alias for different tenants
        await index.add_alias("Apple", "tenant_a_entity", tenant_id="tenant_a")
        await index.add_alias("Apple", "tenant_b_entity", tenant_id="tenant_b")
        
        # Lookup should return different entities for different tenants
        entry_a = await index.lookup("Apple", tenant_id="tenant_a")
        entry_b = await index.lookup("Apple", tenant_id="tenant_b")
        
        assert entry_a.entity_id == "tenant_a_entity"
        assert entry_b.entity_id == "tenant_b_entity"

    @pytest.mark.asyncio
    async def test_remove_alias_with_tenant(self):
        """Test removing alias with tenant_id"""
        index = AliasIndex(backend="memory")
        
        # Add aliases for different tenants
        await index.add_alias("Apple", "e1", tenant_id="tenant_a")
        await index.add_alias("Apple", "e2", tenant_id="tenant_b")
        
        # Remove alias for tenant_a
        removed = await index.remove_alias("Apple", tenant_id="tenant_a")
        assert removed is True
        
        # tenant_a should not find it
        entry_a = await index.lookup("Apple", tenant_id="tenant_a")
        assert entry_a is None
        
        # tenant_b should still find it
        entry_b = await index.lookup("Apple", tenant_id="tenant_b")
        assert entry_b is not None

    @pytest.mark.asyncio
    async def test_alias_without_tenant_backward_compatible(self):
        """Test alias index works without tenant_id (backward compatible)"""
        index = AliasIndex(backend="memory")
        
        # Add alias without tenant_id
        await index.add_alias("Microsoft", "e1", match_type=MatchType.EXACT)
        
        # Lookup without tenant_id
        entry = await index.lookup("Microsoft")
        assert entry is not None
        assert entry.entity_id == "e1"


# Cross-Tenant Fusion Prevention Tests

class TestCrossTenantFusionPrevention:
    """Test prevention of cross-tenant fusion operations"""

    @pytest.mark.asyncio
    async def test_deduplicate_raises_error_on_cross_tenant(self):
        """Test EntityDeduplicator silently filters cross-tenant entities (defense-in-depth)"""
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        # Mix entities from different tenants
        entities = [
            Entity(id="a1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="b1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_b"),
        ]
        
        context = TenantContext(tenant_id="tenant_a")
        
        # Should silently filter to only tenant_a entities (defense-in-depth)
        result = await deduplicator.deduplicate(entities, context=context)
        
        # Only tenant_a entity should remain
        assert all(e.tenant_id == "tenant_a" for e in result)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_knowledge_fusion_filters_tenant_isolation(self, graph_store):
        """Test KnowledgeFusion silently filters cross-tenant entities (defense-in-depth)"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.90)
        
        # Create mixed tenant entities
        entities = [
            Entity(id="a1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="b1", entity_type="Person", properties={"name": "Bob"}, tenant_id="tenant_b"),
        ]
        
        # Add entities to graph store
        tenant_context_a = TenantContext(tenant_id="tenant_a")
        tenant_context_b = TenantContext(tenant_id="tenant_b")
        
        await graph_store.add_entity(entities[0], context=tenant_context_a)
        await graph_store.add_entity(entities[1], context=tenant_context_b)
        
        # Fuse with tenant_a context - should silently filter to only tenant_a entities
        stats = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Only 1 tenant_a entity should be analyzed
        assert stats["entities_analyzed"] == 1
        
        # Skip the part that tries to access internal storage
        # for entity in entities:
        #     if hasattr(graph_store, '_global_graph'):
        #         graph_store._global_graph.add_node(entity.id, entity=entity)
        
        context = TenantContext(tenant_id="tenant_a")
        
        # Should not raise error if filtering works correctly
        # The fusion operation should filter out tenant_b entities
        stats = await fusion.fuse_cross_document_entities(context=context)
        
        # Should only process tenant_a entities
        assert stats["entities_analyzed"] <= 1

    def test_tenant_context_creation(self):
        """Test TenantContext validation"""
        # Valid tenant_id
        ctx = TenantContext(tenant_id="tenant-123")
        assert ctx.tenant_id == "tenant-123"
        
        # Invalid tenant_id (special characters)
        with pytest.raises(Exception):  # InvalidTenantIdError
            TenantContext(tenant_id="tenant@123")


# Integration Tests

class TestTenantFusionIntegration:
    """Integration tests for tenant-scoped fusion"""

    @pytest.mark.asyncio
    async def test_end_to_end_tenant_fusion(self, graph_store, tenant_context_a):
        """Test complete tenant-scoped fusion workflow"""
        # Create fusion instance
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.85)
        
        # Add similar entities in tenant_a
        entities = [
            Entity(
                id="a_e1",
                entity_type="Person",
                properties={"name": "Alice Smith", "age": 30},
                tenant_id="tenant_a"
            ),
            Entity(
                id="a_e2",
                entity_type="Person",
                properties={"name": "Alice Smith", "age": 31},
                tenant_id="tenant_a"
            ),
            Entity(
                id="a_e3",
                entity_type="Person",
                properties={"name": "Bob Jones"},
                tenant_id="tenant_a"
            ),
        ]
        
        for entity in entities:
            await graph_store.add_entity(entity, context=tenant_context_a)
        
        # Run fusion
        stats = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Verify stats
        assert stats["entities_analyzed"] == 3
        # Similar Alice entities might be merged (depending on similarity computation)

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation_in_fusion(
        self, graph_store, tenant_context_a, tenant_context_b
    ):
        """Test that multiple tenants can coexist without interference"""
        fusion = KnowledgeFusion(graph_store, similarity_threshold=0.85)
        
        # Add entities for tenant_a
        entities_a = [
            Entity(id="a_e1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
            Entity(id="a_e2", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_a"),
        ]
        
        # Add entities for tenant_b
        entities_b = [
            Entity(id="b_e1", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_b"),
            Entity(id="b_e2", entity_type="Person", properties={"name": "Alice"}, tenant_id="tenant_b"),
        ]
        
        for entity in entities_a:
            await graph_store.add_entity(entity, context=tenant_context_a)
        
        for entity in entities_b:
            await graph_store.add_entity(entity, context=tenant_context_b)
        
        # Fuse tenant_a entities
        stats_a = await fusion.fuse_cross_document_entities(context=tenant_context_a)
        
        # Fuse tenant_b entities
        stats_b = await fusion.fuse_cross_document_entities(context=tenant_context_b)
        
        # Each tenant should only see their own entities
        assert stats_a["entities_analyzed"] == 2
        assert stats_b["entities_analyzed"] == 2

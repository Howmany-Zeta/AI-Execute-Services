"""
Multi-Tenant Knowledge Graph Usage Examples

This example demonstrates how to use the Knowledge Graph module in a multi-tenant environment.
"""

import asyncio
from typing import Optional
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
    CrossTenantRelationError,
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.query import GraphQuery
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion


# ============================================================================
# Example 1: Basic Multi-Tenant Operations
# ============================================================================


async def example_basic_multi_tenant():
    """Basic multi-tenant operations with PostgreSQL"""
    print("\n=== Example 1: Basic Multi-Tenant Operations ===\n")
    
    # Initialize store with RLS enabled
    store = PostgresGraphStore(
        connection_string="postgresql://user:pass@localhost/knowledge_graph",
        enable_rls=True
    )
    await store.initialize()
    
    # Create tenant contexts
    tenant_a = TenantContext(tenant_id="acme-corp")
    tenant_b = TenantContext(tenant_id="globex-inc")
    
    # Add entities for Tenant A
    alice = Entity(
        id="alice",
        entity_type="Person",
        properties={"name": "Alice", "role": "Engineer"}
    )
    await store.add_entity(alice, context=tenant_a)
    print(f"✓ Added Alice to tenant: {tenant_a.tenant_id}")
    
    # Add entities for Tenant B
    bob = Entity(
        id="bob",
        entity_type="Person",
        properties={"name": "Bob", "role": "Manager"}
    )
    await store.add_entity(bob, context=tenant_b)
    print(f"✓ Added Bob to tenant: {tenant_b.tenant_id}")
    
    # Query within tenant scope
    tenant_a_people = await store.query(
        GraphQuery(entity_type="Person"),
        context=tenant_a
    )
    print(f"\nTenant A has {len(tenant_a_people)} person(s): {[e.properties['name'] for e in tenant_a_people]}")
    
    tenant_b_people = await store.query(
        GraphQuery(entity_type="Person"),
        context=tenant_b
    )
    print(f"Tenant B has {len(tenant_b_people)} person(s): {[e.properties['name'] for e in tenant_b_people]}")
    
    await store.close()


# ============================================================================
# Example 2: Isolation Modes Comparison
# ============================================================================


async def example_isolation_modes():
    """Compare different isolation modes"""
    print("\n=== Example 2: Isolation Modes Comparison ===\n")
    
    # SHARED_SCHEMA mode (default)
    print("1. SHARED_SCHEMA Mode (tenant_id column filtering)")
    shared_context = TenantContext(
        tenant_id="tenant-shared",
        isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )
    
    store_shared = PostgresGraphStore(
        connection_string="postgresql://user:pass@localhost/knowledge_graph",
        enable_rls=True  # RLS for defense-in-depth
    )
    await store_shared.initialize()
    
    entity = Entity(id="e1", entity_type="Product", properties={"name": "Widget"})
    await store_shared.add_entity(entity, context=shared_context)
    print(f"   ✓ Entity stored with tenant_id={shared_context.tenant_id}")
    await store_shared.close()
    
    # SEPARATE_SCHEMA mode
    print("\n2. SEPARATE_SCHEMA Mode (PostgreSQL schemas)")
    separate_context = TenantContext(
        tenant_id="tenant-separate",
        isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
    )
    
    store_separate = PostgresGraphStore(
        connection_string="postgresql://user:pass@localhost/knowledge_graph"
    )
    await store_separate.initialize()
    
    entity = Entity(id="e2", entity_type="Product", properties={"name": "Gadget"})
    await store_separate.add_entity(entity, context=separate_context)
    print(f"   ✓ Entity stored in schema: tenant_{separate_context.tenant_id}")
    await store_separate.close()
    
    # DISABLED mode (single-tenant)
    print("\n3. DISABLED Mode (backward compatible)")
    entity = Entity(id="e3", entity_type="Product", properties={"name": "Tool"})
    
    store_disabled = InMemoryGraphStore()
    await store_disabled.initialize()
    await store_disabled.add_entity(entity)  # No context = single-tenant
    print("   ✓ Entity stored in global namespace (tenant_id=None)")


# ============================================================================
# Example 3: Cross-Tenant Isolation Enforcement
# ============================================================================


async def example_cross_tenant_protection():
    """Demonstrate cross-tenant relation prevention"""
    print("\n=== Example 3: Cross-Tenant Isolation Enforcement ===\n")
    
    store = InMemoryGraphStore()
    await store.initialize()
    
    # Create entities in different tenants
    tenant_a = TenantContext(tenant_id="tenant-a")
    tenant_b = TenantContext(tenant_id="tenant-b")
    
    entity_a = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
    entity_b = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
    
    await store.add_entity(entity_a, context=tenant_a)
    await store.add_entity(entity_b, context=tenant_b)
    
    print("✓ Created entities in different tenants")
    
    # Try to create cross-tenant relation (should fail)
    try:
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="alice",
            target_id="bob",
            properties={}
        )
        await store.add_relation(relation, context=tenant_a)
        print("❌ ERROR: Cross-tenant relation was allowed!")
    except CrossTenantRelationError as e:
        print(f"✓ Cross-tenant relation prevented: {e}")


# ============================================================================
# Example 4: Multi-Tenant Graph Building
# ============================================================================


async def example_multi_tenant_graph_building():
    """Build knowledge graphs for multiple tenants"""
    print("\n=== Example 4: Multi-Tenant Graph Building ===\n")
    
    store = InMemoryGraphStore()
    await store.initialize()
    
    builder = GraphBuilder(store)
    
    # Build graph for Tenant A
    tenant_a = TenantContext(tenant_id="acme-corp")
    text_a = "Alice works at Acme Corp. She is the CTO. Bob reports to Alice."
    
    entities_a = await builder.build_from_text(text_a, context=tenant_a)
    print(f"✓ Built graph for {tenant_a.tenant_id}: {len(entities_a)} entities")
    
    # Build graph for Tenant B
    tenant_b = TenantContext(tenant_id="globex-inc")
    text_b = "Carol is the CEO of Globex Inc. Dave is the CFO."
    
    entities_b = await builder.build_from_text(text_b, context=tenant_b)
    print(f"✓ Built graph for {tenant_b.tenant_id}: {len(entities_b)} entities")
    
    # Verify isolation
    results_a = await store.query(GraphQuery(entity_type="Person"), context=tenant_a)
    results_b = await store.query(GraphQuery(entity_type="Person"), context=tenant_b)
    
    print(f"\n{tenant_a.tenant_id} has {len(results_a)} people")
    print(f"{tenant_b.tenant_id} has {len(results_b)} people")


# ============================================================================
# Example 5: Multi-Tenant Knowledge Fusion
# ============================================================================


async def example_multi_tenant_fusion():
    """Fuse entities within tenant boundaries"""
    print("\n=== Example 5: Multi-Tenant Knowledge Fusion ===\n")
    
    store = InMemoryGraphStore()
    await store.initialize()
    
    fusion = KnowledgeFusion(store)
    tenant_a = TenantContext(tenant_id="tenant-a")
    
    # Create duplicate entities within tenant
    alice1 = Entity(
        id="alice1",
        entity_type="Person",
        properties={"name": "Alice Smith", "email": "alice@example.com"}
    )
    alice2 = Entity(
        id="alice2",
        entity_type="Person",
        properties={"name": "A. Smith", "email": "alice@example.com"}
    )
    
    await store.add_entity(alice1, context=tenant_a)
    await store.add_entity(alice2, context=tenant_a)
    
    print(f"✓ Created 2 entities for {tenant_a.tenant_id}")
    
    # Fuse entities within tenant scope
    entities = [alice1, alice2]
    fused = await fusion.fuse_cross_document_entities(entities, context=tenant_a)
    
    print(f"✓ Fused to {len(fused)} entity (merged duplicates)")
    
    # Verify fusion only affected tenant A
    tenant_a_count = len(await store.query(GraphQuery(entity_type="Person"), context=tenant_a))
    print(f"   Tenant A now has {tenant_a_count} person(s)")


# ============================================================================
# Example 6: SQLite Multi-Tenancy
# ============================================================================


async def example_sqlite_multi_tenancy():
    """Multi-tenancy with SQLite backend"""
    print("\n=== Example 6: SQLite Multi-Tenancy ===\n")
    
    # SHARED_SCHEMA mode: Single database file
    print("1. SQLite SHARED_SCHEMA Mode")
    store_shared = SQLiteGraphStore(
        db_path="/tmp/knowledge_graph.db",
        isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )
    await store_shared.initialize()
    
    tenant_a = TenantContext(tenant_id="tenant-a", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
    entity = Entity(id="e1", entity_type="Product", properties={"name": "Widget"})
    await store_shared.add_entity(entity, context=tenant_a)
    print(f"   ✓ Entity stored in /tmp/knowledge_graph.db with tenant_id column")
    await store_shared.close()
    
    # SEPARATE_SCHEMA mode: Separate database files
    print("\n2. SQLite SEPARATE_SCHEMA Mode")
    store_separate = SQLiteGraphStore(
        db_path="/tmp/knowledge_graph.db",
        isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
    )
    await store_separate.initialize()
    
    tenant_b = TenantContext(tenant_id="tenant-b", isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA)
    entity = Entity(id="e2", entity_type="Product", properties={"name": "Gadget"})
    await store_separate.add_entity(entity, context=tenant_b)
    print(f"   ✓ Entity stored in /tmp/tenant_tenant-b.db (separate file)")
    await store_separate.close()


# ============================================================================
# Example 7: InMemory with LRU Eviction
# ============================================================================


async def example_inmemory_lru():
    """InMemory store with LRU tenant eviction"""
    print("\n=== Example 7: InMemory with LRU Eviction ===\n")
    
    # Configure with small max_tenant_graphs for demo
    store = InMemoryGraphStore(max_tenant_graphs=3)
    await store.initialize()
    
    # Create entities for 5 tenants (exceeds max of 3)
    for i in range(1, 6):
        tenant = TenantContext(tenant_id=f"tenant-{i}")
        entity = Entity(
            id=f"e{i}",
            entity_type="Product",
            properties={"name": f"Product {i}"}
        )
        await store.add_entity(entity, context=tenant)
        
        current_count = store.get_tenant_count()
        print(f"   Added entity for tenant-{i}, active tenants: {current_count}")
    
    # Least recently used tenants (1 and 2) should be evicted
    print(f"\n✓ LRU eviction kept only 3 most recent tenants in memory")


# ============================================================================
# Example 8: Request Context Integration
# ============================================================================


class TenantAwareApp:
    """Example web application with tenant-aware operations"""
    
    def __init__(self, store):
        self.store = store
    
    def get_tenant_from_request(self, request_headers: dict) -> Optional[str]:
        """Extract tenant_id from request (e.g., JWT, header, subdomain)"""
        # Method 1: HTTP header
        if "X-Tenant-ID" in request_headers:
            return request_headers["X-Tenant-ID"]
        
        # Method 2: JWT claim
        # token = request_headers.get("Authorization", "").replace("Bearer ", "")
        # claims = decode_jwt(token)
        # return claims.get("tenant_id")
        
        # Method 3: Subdomain
        # host = request_headers.get("Host", "")
        # subdomain = host.split(".")[0]
        # return subdomain if subdomain != "www" else None
        
        return None
    
    async def add_entity(self, entity: Entity, request_headers: dict):
        """Add entity with tenant context from request"""
        tenant_id = self.get_tenant_from_request(request_headers)
        
        if tenant_id:
            context = TenantContext(tenant_id=tenant_id)
            await self.store.add_entity(entity, context=context)
        else:
            # Fallback to single-tenant mode
            await self.store.add_entity(entity)
    
    async def query_entities(self, query: GraphQuery, request_headers: dict):
        """Query entities within tenant scope"""
        tenant_id = self.get_tenant_from_request(request_headers)
        
        if tenant_id:
            context = TenantContext(tenant_id=tenant_id)
            return await self.store.query(query, context=context)
        else:
            return await self.store.query(query)


async def example_request_context_integration():
    """Integrate tenant context with web request"""
    print("\n=== Example 8: Request Context Integration ===\n")
    
    store = InMemoryGraphStore()
    await store.initialize()
    
    app = TenantAwareApp(store)
    
    # Simulate requests from different tenants
    request_tenant_a = {"X-Tenant-ID": "acme-corp"}
    request_tenant_b = {"X-Tenant-ID": "globex-inc"}
    
    # Add entities via request context
    entity_a = Entity(id="e1", entity_type="Product", properties={"name": "Widget"})
    await app.add_entity(entity_a, request_tenant_a)
    print(f"✓ Added entity for tenant: acme-corp")
    
    entity_b = Entity(id="e2", entity_type="Product", properties={"name": "Gadget"})
    await app.add_entity(entity_b, request_tenant_b)
    print(f"✓ Added entity for tenant: globex-inc")
    
    # Query via request context
    results_a = await app.query_entities(GraphQuery(entity_type="Product"), request_tenant_a)
    results_b = await app.query_entities(GraphQuery(entity_type="Product"), request_tenant_b)
    
    print(f"\nTenant acme-corp sees {len(results_a)} product(s)")
    print(f"Tenant globex-inc sees {len(results_b)} product(s)")


# ============================================================================
# Main: Run All Examples
# ============================================================================


async def main():
    """Run all multi-tenant examples"""
    print("=" * 70)
    print("Multi-Tenant Knowledge Graph Examples")
    print("=" * 70)
    
    # Run examples
    await example_basic_multi_tenant()
    await example_isolation_modes()
    await example_cross_tenant_protection()
    await example_multi_tenant_graph_building()
    await example_multi_tenant_fusion()
    await example_sqlite_multi_tenancy()
    await example_inmemory_lru()
    await example_request_context_integration()
    
    print("\n" + "=" * 70)
    print("✓ All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())

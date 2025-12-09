# Multi-Tenancy Setup Guide

## Overview

The Knowledge Graph module provides comprehensive multi-tenancy support, allowing multiple tenants to share the same infrastructure while maintaining strict data isolation. This guide covers setup, configuration, and best practices for multi-tenant deployments.

## Table of Contents

- [Quick Start](#quick-start)
- [Isolation Modes](#isolation-modes)
- [Backend Configuration](#backend-configuration)
- [Migration Guide](#migration-guide)
- [Code Examples](#code-examples)
- [Security Best Practices](#security-best-practices)
- [Performance Considerations](#performance-considerations)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Enable Multi-Tenancy

Multi-tenancy is enabled by passing a `TenantContext` when performing graph operations:

```python
from aiecs.infrastructure.graph_storage.tenant import TenantContext, TenantIsolationMode
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity

# Initialize store
store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/graph"
)
await store.initialize()

# Create tenant context
context = TenantContext(
    tenant_id="acme-corp",
    isolation_mode=TenantIsolationMode.SHARED_SCHEMA
)

# Add entity for specific tenant
entity = Entity(
    id="person_1",
    entity_type="Person",
    properties={"name": "Alice"}
)
await store.add_entity(entity, context=context)

# Query within tenant scope
results = await store.query(
    GraphQuery(entity_type="Person"),
    context=context
)
```

### Backward Compatibility

Single-tenant deployments continue to work without changes:

```python
# No context = single-tenant mode (backward compatible)
entity = Entity(id="e1", entity_type="Person", properties={"name": "Bob"})
await store.add_entity(entity)  # Works as before
```

## Isolation Modes

The Knowledge Graph supports three isolation modes:

### 1. DISABLED (Default for Backward Compatibility)

No tenant isolation. All data shares the same namespace.

```python
# No context or DISABLED mode
entity.tenant_id = None  # Global namespace
```

**Use Cases:**
- Single-tenant applications
- Development/testing
- Legacy deployments

### 2. SHARED_SCHEMA

Shared database schema with `tenant_id` column filtering. Optional Row-Level Security (RLS) for PostgreSQL.

```python
context = TenantContext(
    tenant_id="acme-corp",
    isolation_mode=TenantIsolationMode.SHARED_SCHEMA
)
```

**Storage Strategy:**
- **PostgreSQL**: Single schema with `tenant_id` column + optional RLS policies
- **SQLite**: Single database with `tenant_id` column filtering
- **InMemory**: Partitioned graphs in memory

**Pros:**
- Simple deployment (single database)
- Easy backup and maintenance
- Good for many small tenants
- Lower storage overhead

**Cons:**
- Requires careful query filtering
- RLS may have slight performance overhead
- All tenants share same schema/indexes

**Recommended For:**
- SaaS applications with many small tenants
- Applications where tenants share similar data schemas
- Cost-sensitive deployments

### 3. SEPARATE_SCHEMA

Separate database schemas/files per tenant. Strongest isolation.

```python
context = TenantContext(
    tenant_id="acme-corp",
    isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
)
```

**Storage Strategy:**
- **PostgreSQL**: Separate PostgreSQL schemas (`tenant_acme`, `tenant_xyz`)
- **SQLite**: Separate database files per tenant (`tenant_acme.db`, `tenant_xyz.db`)
- **InMemory**: Separate NetworkX graphs per tenant

**Pros:**
- Strongest isolation (complete separation)
- Better performance (no RLS overhead, no tenant_id filtering)
- Easier tenant-specific operations (backup, restore, migrate)
- Can customize schema per tenant

**Cons:**
- More complex deployment
- Higher storage overhead
- More database connections (PostgreSQL)

**Recommended For:**
- Enterprise tenants with large data volumes
- Applications requiring strict compliance/auditing
- Tenants with custom schema requirements
- High-performance requirements

## Backend Configuration

### PostgreSQL with SHARED_SCHEMA + RLS

Recommended for most multi-tenant SaaS applications.

```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore

store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/graph",
    enable_rls=True  # Enable Row-Level Security
)
await store.initialize()
```

**Setup Steps:**

1. Create database and enable RLS:
```sql
-- Run initialization SQL
CREATE DATABASE knowledge_graph;

-- Enable RLS (done automatically by initialize())
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations ENABLE ROW LEVEL SECURITY;
```

2. Use with tenant context:
```python
context = TenantContext(
    tenant_id="acme-corp",
    isolation_mode=TenantIsolationMode.SHARED_SCHEMA
)
await store.add_entity(entity, context=context)
```

**How It Works:**
- Each operation sets `app.current_tenant_id` session variable
- RLS policies automatically filter rows: `WHERE tenant_id = current_setting('app.current_tenant_id')`
- Defense-in-depth: Even if application code fails to filter, RLS enforces isolation

### PostgreSQL with SEPARATE_SCHEMA

Recommended for enterprise tenants or high-performance requirements.

```python
store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/graph"
)
await store.initialize()

# Use SEPARATE_SCHEMA mode
context = TenantContext(
    tenant_id="enterprise-client",
    isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
)
```

**How It Works:**
- Each tenant gets a PostgreSQL schema: `CREATE SCHEMA tenant_acme`
- Connection sets search_path: `SET search_path = tenant_acme, public`
- All queries automatically route to tenant schema
- No tenant_id column filtering needed

**Benefits:**
- Better query performance (no RLS overhead)
- Complete isolation at database level
- Easier per-tenant operations

### SQLite with SHARED_SCHEMA

Simple file-based multi-tenancy.

```python
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore

store = SQLiteGraphStore(
    db_path="/data/graph.db",
    isolation_mode=TenantIsolationMode.SHARED_SCHEMA
)
await store.initialize()

context = TenantContext(tenant_id="acme", isolation_mode=TenantIsolationMode.SHARED_SCHEMA)
await store.add_entity(entity, context=context)
```

**How It Works:**
- Single SQLite database file
- `tenant_id` column with indexes
- All queries include: `WHERE tenant_id = ?`

### SQLite with SEPARATE_SCHEMA

Separate database file per tenant.

```python
store = SQLiteGraphStore(
    db_path="/data/graph.db",  # Base path
    isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
)
await store.initialize()

context = TenantContext(tenant_id="acme", isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA)
# Uses /data/tenant_acme.db
await store.add_entity(entity, context=context)
```

**How It Works:**
- Each tenant gets separate database file
- Resolver creates: `/data/tenant_{tenant_id}.db`
- Complete file-level isolation

### InMemory with LRU Eviction

In-memory graphs with automatic tenant eviction.

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore(
    max_tenant_graphs=100  # Keep max 100 tenant graphs in memory
)
await store.initialize()

context = TenantContext(tenant_id="acme")
await store.add_entity(entity, context=context)
```

**How It Works:**
- Each tenant gets separate NetworkX graph
- LRU (Least Recently Used) eviction when limit exceeded
- Global graph (tenant_id=None) never evicted
- Configure via `max_tenant_graphs` or `KG_INMEMORY_MAX_TENANTS` env var

**⚠️ Warning:** Evicted tenant data is lost! Use persistent backend (PostgreSQL/SQLite) for production.

## Migration Guide

### Migrating from Single-Tenant to Multi-Tenant

See [MULTI_TENANCY_MIGRATION.md](./MULTI_TENANCY_MIGRATION.md) for detailed migration steps.

**Quick Overview:**

1. **Add tenant_id columns** (backward compatible):
```sql
ALTER TABLE graph_entities ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
ALTER TABLE graph_relations ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
```

2. **Backfill existing data** (assign to default tenant):
```sql
UPDATE graph_entities SET tenant_id = 'default' WHERE tenant_id = '';
UPDATE graph_relations SET tenant_id = 'default' WHERE tenant_id = '';
```

3. **Create indexes**:
```sql
CREATE INDEX CONCURRENTLY idx_entities_tenant ON graph_entities(tenant_id);
CREATE INDEX CONCURRENTLY idx_relations_tenant ON graph_relations(tenant_id);
```

4. **Enable RLS** (optional, PostgreSQL only):
```sql
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON graph_entities
    USING (tenant_id = current_setting('app.current_tenant_id', true));
```

5. **Update application code** (pass context):
```python
# Before
await store.add_entity(entity)

# After
context = TenantContext(tenant_id=get_current_tenant())
await store.add_entity(entity, context=context)
```

## Code Examples

### Basic Multi-Tenant Operations

```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.query import GraphQuery

# Initialize store
store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/graph",
    enable_rls=True
)
await store.initialize()

# Tenant A operations
tenant_a = TenantContext(tenant_id="tenant-a")

alice = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
await store.add_entity(alice, context=tenant_a)

# Tenant B operations (completely isolated)
tenant_b = TenantContext(tenant_id="tenant-b")

bob = Entity(id="bob", entity_type="Person", properties={"name": "Bob"})
await store.add_entity(bob, context=tenant_b)

# Query within tenant scope
tenant_a_entities = await store.query(
    GraphQuery(entity_type="Person"),
    context=tenant_a
)
# Returns only Alice (tenant A entities)

tenant_b_entities = await store.query(
    GraphQuery(entity_type="Person"),
    context=tenant_b
)
# Returns only Bob (tenant B entities)
```

### Multi-Tenant Graph Building

```python
from aiecs.application.knowledge_graph.builder.graph_builder import GraphBuilder

# Build graph for specific tenant
builder = GraphBuilder(store)
context = TenantContext(tenant_id="acme-corp")

entities = await builder.build_from_text(
    text="Alice works at Acme Corp. Bob manages the engineering team.",
    context=context  # All entities/relations tagged with tenant_id
)
```

### Multi-Tenant Knowledge Fusion

```python
from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion

fusion = KnowledgeFusion(store)
context = TenantContext(tenant_id="acme-corp")

# Fuses entities only within tenant scope
fused_entities = await fusion.fuse_cross_document_entities(
    entities=[entity1, entity2, entity3],
    context=context  # Prevents cross-tenant fusion
)
```

### Retrieving Tenant Metadata

```python
# Get tenant count (InMemoryGraphStore)
tenant_count = store.get_tenant_count()
print(f"Active tenants in memory: {tenant_count}")

# Check if entity belongs to tenant
entity = await store.get_entity("alice", context=tenant_a)
if entity and entity.tenant_id == tenant_a.tenant_id:
    print(f"Entity belongs to {tenant_a.tenant_id}")
```

### Cross-Tenant Operations (Admin Use Case)

For administrative operations, you can query without context:

```python
# Admin: Query all entities across all tenants
all_entities = await store.query(GraphQuery(entity_type="*"))
# Returns entities from all tenants (tenant_id column included)

# Filter by tenant in application layer
tenant_a_entities = [e for e in all_entities if e.tenant_id == "tenant-a"]
```

⚠️ **Warning:** Cross-tenant queries should only be used for administrative purposes with proper authorization checks.

## Security Best Practices

### 1. Always Use TenantContext

Never rely on application-level filtering alone:

```python
# ❌ BAD: Manual filtering
entities = await store.query(GraphQuery(entity_type="*"))
my_entities = [e for e in entities if e.tenant_id == current_tenant]

# ✅ GOOD: Use TenantContext
context = TenantContext(tenant_id=current_tenant)
my_entities = await store.query(GraphQuery(entity_type="*"), context=context)
```

### 2. Enable RLS for Defense-in-Depth

For PostgreSQL, enable RLS even if application code filters correctly:

```python
store = PostgresGraphStore(
    connection_string=conn_str,
    enable_rls=True  # RLS as additional security layer
)
```

### 3. Validate Tenant IDs

Tenant IDs are validated automatically:

```python
# Valid tenant IDs (alphanumeric, hyphens, underscores)
TenantContext(tenant_id="acme-corp-123")  # ✅
TenantContext(tenant_id="tenant_456")      # ✅

# Invalid tenant IDs (raises InvalidTenantIdError)
TenantContext(tenant_id="acme@corp")       # ❌
TenantContext(tenant_id="tenant 123")      # ❌
TenantContext(tenant_id="")                # ❌
```

### 4. Prevent Cross-Tenant Relations

The framework automatically prevents relations between entities from different tenants:

```python
# Entity from tenant A
alice = Entity(id="alice", tenant_id="tenant-a", ...)

# Entity from tenant B
bob = Entity(id="bob", tenant_id="tenant-b", ...)

# Attempting cross-tenant relation raises CrossTenantRelationError
relation = Relation(
    id="r1",
    relation_type="KNOWS",
    source_id="alice",
    target_id="bob"
)
await store.add_relation(relation, context=tenant_a)  # ❌ Raises error
```

### 5. Audit Logging

Log all tenant operations for compliance:

```python
import logging

logger = logging.getLogger("tenant_operations")

async def add_entity_with_audit(store, entity, context):
    logger.info(f"Tenant {context.tenant_id}: Adding entity {entity.id}")
    await store.add_entity(entity, context=context)
    logger.info(f"Tenant {context.tenant_id}: Entity {entity.id} added successfully")
```

### 6. Rate Limiting Per Tenant

Implement rate limiting to prevent resource exhaustion:

```python
from collections import defaultdict
from datetime import datetime, timedelta

class TenantRateLimiter:
    def __init__(self, max_requests_per_minute=100):
        self.limits = defaultdict(list)
        self.max_requests = max_requests_per_minute
    
    def check_rate_limit(self, tenant_id: str) -> bool:
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        
        # Remove old requests
        self.limits[tenant_id] = [
            t for t in self.limits[tenant_id] if t > cutoff
        ]
        
        # Check limit
        if len(self.limits[tenant_id]) >= self.max_requests:
            return False
        
        self.limits[tenant_id].append(now)
        return True
```

## Performance Considerations

### Index Optimization

Ensure proper indexes exist for multi-tenant queries:

```sql
-- PostgreSQL indexes for SHARED_SCHEMA mode
CREATE INDEX CONCURRENTLY idx_entities_tenant_type 
    ON graph_entities(tenant_id, entity_type);

CREATE INDEX CONCURRENTLY idx_relations_tenant_source 
    ON graph_relations(tenant_id, source_id);

CREATE INDEX CONCURRENTLY idx_relations_tenant_target 
    ON graph_relations(tenant_id, target_id);
```

### Connection Pooling

Use connection pooling for better performance:

```python
store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/graph",
    pool_size=20,          # Connection pool size
    max_overflow=10,       # Additional connections if needed
    pool_timeout=30,       # Timeout waiting for connection
)
```

### Query Optimization

For SHARED_SCHEMA mode, always include tenant_id in WHERE clauses (done automatically):

```sql
-- Efficient query (uses index)
SELECT * FROM graph_entities 
WHERE tenant_id = 'acme' AND entity_type = 'Person';

-- Inefficient query (full table scan)
SELECT * FROM graph_entities 
WHERE entity_type = 'Person';  -- Missing tenant_id filter
```

### Choose Right Isolation Mode

| Scenario | Recommended Mode | Reason |
|----------|-----------------|--------|
| 100+ small tenants | SHARED_SCHEMA | Lower overhead, simpler management |
| 5-10 large tenants | SEPARATE_SCHEMA | Better performance, stronger isolation |
| Mixed workload | SHARED_SCHEMA + selective SEPARATE_SCHEMA | Flexible per-tenant configuration |
| Development/testing | DISABLED or InMemory | Simplicity |

### InMemory LRU Configuration

Tune `max_tenant_graphs` based on available RAM:

```python
# Small deployment (low RAM)
store = InMemoryGraphStore(max_tenant_graphs=50)

# Large deployment (high RAM)
store = InMemoryGraphStore(max_tenant_graphs=500)

# Environment variable
import os
os.environ['KG_INMEMORY_MAX_TENANTS'] = '200'
```

## Troubleshooting

See [MULTI_TENANCY_TROUBLESHOOTING.md](./MULTI_TENANCY_TROUBLESHOOTING.md) for detailed troubleshooting guide.

### Common Issues

**Issue: Entities not visible for tenant**
```python
# Check tenant_id is set correctly
entity = await store.get_entity("e1", context=context)
print(f"Entity tenant_id: {entity.tenant_id}")
print(f"Context tenant_id: {context.tenant_id}")
```

**Issue: RLS not working**
```sql
-- Verify RLS is enabled
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'graph_entities';

-- Check policies exist
SELECT * FROM pg_policies WHERE tablename = 'graph_entities';
```

**Issue: InMemory tenant eviction**
```python
# Monitor tenant count
print(f"Active tenants: {store.get_tenant_count()}")

# Increase max_tenant_graphs or use persistent backend
store = InMemoryGraphStore(max_tenant_graphs=500)
```

## Next Steps

- [Migration Guide](./MULTI_TENANCY_MIGRATION.md) - Migrate existing deployments
- [Troubleshooting](./MULTI_TENANCY_TROUBLESHOOTING.md) - Common issues and solutions
- [RLS Setup](./MULTI_TENANCY_RLS_SETUP.md) - Detailed PostgreSQL RLS configuration
- [Separate Schema Setup](./MULTI_TENANCY_SEPARATE_SCHEMA_SETUP.md) - PostgreSQL separate schema configuration

## References

- [TenantContext API Documentation](../API_REFERENCE.md#tenantcontext)
- [GraphStore Interface](../API_REFERENCE.md#graphstore)
- [Knowledge Fusion with Multi-Tenancy](../tutorials/MULTI_TENANT_FUSION_TUTORIAL.md)

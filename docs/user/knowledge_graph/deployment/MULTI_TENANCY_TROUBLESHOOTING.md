# Multi-Tenancy Troubleshooting Guide

## Overview

This guide provides solutions to common issues when working with multi-tenant Knowledge Graph deployments.

## Table of Contents

- [Data Visibility Issues](#data-visibility-issues)
- [Cross-Tenant Access Problems](#cross-tenant-access-problems)
- [Performance Issues](#performance-issues)
- [Migration Problems](#migration-problems)
- [Configuration Errors](#configuration-errors)
- [RLS-Specific Issues](#rls-specific-issues)
- [SEPARATE_SCHEMA Issues](#separate_schema-issues)
- [Connection and Pool Issues](#connection-and-pool-issues)

## Data Visibility Issues

### Entities Not Visible for Tenant

**Symptom:** Queries return empty results even though data exists

**Diagnosis:**
```python
# Check if entity exists
entity = await store.get_entity("entity_id", context=None)  # Query without context
if entity:
    print(f"Entity exists with tenant_id: {entity.tenant_id}")
    print(f"Your context tenant_id: {context.tenant_id}")
else:
    print("Entity does not exist")
```

**Common Causes:**

1. **Wrong tenant_id in context**
   ```python
   # ❌ Wrong tenant
   context = TenantContext(tenant_id="wrong-tenant")
   
   # ✅ Correct tenant
   context = TenantContext(tenant_id="correct-tenant")
   ```

2. **Entity has different tenant_id**
   ```sql
   -- Check entity tenant_id
   SELECT id, tenant_id FROM graph_entities WHERE id = 'entity_id';
   ```

3. **Tenant_id is NULL/empty**
   ```sql
   -- Find entities without tenant_id
   SELECT COUNT(*) FROM graph_entities WHERE tenant_id IS NULL OR tenant_id = '';
   
   -- Fix: Assign to default tenant
   UPDATE graph_entities SET tenant_id = 'default' WHERE tenant_id IS NULL OR tenant_id = '';
   ```

### Seeing Data from All Tenants

**Symptom:** Query returns data from multiple tenants

**Diagnosis:**
```python
# Check if context is being used
results = await store.query(GraphQuery(entity_type="Person"), context=context)
for entity in results:
    print(f"Entity {entity.id} tenant_id: {entity.tenant_id}")
```

**Common Causes:**

1. **Context not passed to query**
   ```python
   # ❌ BAD: No context
   results = await store.query(query)
   
   # ✅ GOOD: With context
   results = await store.query(query, context=context)
   ```

2. **RLS not enabled (PostgreSQL)**
   ```sql
   -- Check if RLS is enabled
   SELECT tablename, rowsecurity FROM pg_tables 
   WHERE tablename IN ('graph_entities', 'graph_relations');
   
   -- Enable RLS if needed
   ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
   ```

3. **Wrong isolation mode**
   ```python
   # Check isolation mode
   print(f"Isolation mode: {context.isolation_mode}")
   
   # Ensure correct mode
   context = TenantContext(
       tenant_id="acme",
       isolation_mode=TenantIsolationMode.SHARED_SCHEMA
   )
   ```

## Cross-Tenant Access Problems

### CrossTenantRelationError When Creating Relations

**Symptom:** `CrossTenantRelationError: Cannot create relation across tenants`

**Diagnosis:**
```python
# Check entity tenant_ids
source_entity = await store.get_entity(relation.source_id, context=None)
target_entity = await store.get_entity(relation.target_id, context=None)

print(f"Source tenant: {source_entity.tenant_id}")
print(f"Target tenant: {target_entity.tenant_id}")
print(f"Relation context: {context.tenant_id}")
```

**Solutions:**

1. **Ensure entities are in same tenant**
   ```python
   # Both entities must have same tenant_id
   entity_a = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
   entity_b = Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
   
   # Add both to same tenant
   await store.add_entity(entity_a, context=context)
   await store.add_entity(entity_b, context=context)
   
   # Now relation works
   relation = Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")
   await store.add_relation(relation, context=context)
   ```

2. **Migrate entity to correct tenant**
   ```python
   # Read entity
   entity = await store.get_entity("entity_id", context=None)
   
   # Update tenant_id
   entity.tenant_id = "correct-tenant"
   
   # Re-add with new tenant
   correct_context = TenantContext(tenant_id="correct-tenant")
   await store.add_entity(entity, context=correct_context)
   ```

### Accidental Cross-Tenant Data Leak

**Symptom:** Data from one tenant visible to another tenant

**Immediate Response:**
1. Stop application immediately
2. Check logs for affected tenants
3. Verify RLS is enabled (PostgreSQL)
4. Audit recent changes

**Investigation:**
```sql
-- PostgreSQL: Check if RLS is active
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename = 'graph_entities';

-- Check for entities with wrong tenant_id
SELECT e1.id, e1.tenant_id, r.relation_type, e2.id, e2.tenant_id
FROM graph_entities e1
JOIN graph_relations r ON e1.id = r.source_id
JOIN graph_entities e2 ON r.target_id = e2.id
WHERE e1.tenant_id != e2.tenant_id;
```

**Prevention:**
```python
# Always use context
# Enable RLS for defense-in-depth
store = PostgresGraphStore(
    connection_string=conn_str,
    enable_rls=True  # Critical for production
)

# Add validation middleware
async def validate_tenant_access(user_id: str, tenant_id: str) -> bool:
    # Check user has permission for tenant
    return await check_user_tenant_membership(user_id, tenant_id)
```

## Performance Issues

### Slow Queries After Enabling Multi-Tenancy

**Diagnosis:**
```sql
-- PostgreSQL: Check query plans
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM graph_entities 
WHERE tenant_id = 'acme' AND entity_type = 'Person';

-- Should use index scan, not sequential scan
```

**Common Causes:**

1. **Missing indexes**
   ```sql
   -- Check if tenant indexes exist
   SELECT indexname FROM pg_indexes 
   WHERE tablename = 'graph_entities' 
     AND indexname LIKE '%tenant%';
   
   -- Create indexes if missing
   CREATE INDEX CONCURRENTLY idx_entities_tenant 
       ON graph_entities(tenant_id);
   CREATE INDEX CONCURRENTLY idx_entities_tenant_type 
       ON graph_entities(tenant_id, entity_type);
   ```

2. **Outdated statistics**
   ```sql
   -- Update table statistics
   ANALYZE graph_entities;
   ANALYZE graph_relations;
   ```

3. **RLS overhead**
   ```sql
   -- Benchmark RLS impact
   -- Disable RLS temporarily
   ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
   EXPLAIN ANALYZE SELECT * FROM graph_entities WHERE tenant_id = 'acme';
   
   -- Re-enable RLS
   ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
   EXPLAIN ANALYZE SELECT * FROM graph_entities WHERE tenant_id = 'acme';
   
   -- Compare execution times
   ```

**Solutions:**

1. **Add proper indexes** (see above)
2. **Use SEPARATE_SCHEMA mode** for better performance
3. **Optimize connection pooling**:
   ```python
   store = PostgresGraphStore(
       connection_string=conn_str,
       pool_size=20,
       max_overflow=10
   )
   ```

### InMemory Tenant Eviction Too Aggressive

**Symptom:** Frequent "Evicted inactive tenant graph" warnings

**Diagnosis:**
```python
# Check active tenant count
print(f"Active tenants: {store.get_tenant_count()}")
print(f"Max allowed: {store._max_tenant_graphs}")
```

**Solutions:**

1. **Increase max_tenant_graphs**
   ```python
   store = InMemoryGraphStore(max_tenant_graphs=500)  # Increase limit
   ```

2. **Use environment variable**
   ```bash
   export KG_INMEMORY_MAX_TENANTS=500
   ```

3. **Switch to persistent backend**
   ```python
   # InMemory not recommended for production
   # Use PostgreSQL or SQLite instead
   store = PostgresGraphStore(connection_string=conn_str)
   ```

## Migration Problems

### Migration Script Fails: "Column already exists"

**Symptom:** `ERROR: column "tenant_id" of relation "graph_entities" already exists`

**Diagnosis:**
```sql
-- Check if column exists
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'graph_entities' 
  AND column_name = 'tenant_id';
```

**Solution:**
```sql
-- Migration scripts should be idempotent
-- Use IF NOT EXISTS
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'graph_entities' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE graph_entities ADD COLUMN tenant_id TEXT;
    END IF;
END $$;
```

### Backfill Script Timeout

**Symptom:** Backfill takes too long or times out

**Diagnosis:**
```sql
-- Check table size
SELECT 
    pg_size_pretty(pg_total_relation_size('graph_entities')) as size,
    COUNT(*) as row_count
FROM graph_entities;
```

**Solutions:**

1. **Batch processing**
   ```sql
   -- Update in batches
   UPDATE graph_entities 
   SET tenant_id = 'default'
   WHERE tenant_id = ''
     AND ctid IN (
         SELECT ctid FROM graph_entities 
         WHERE tenant_id = ''
         LIMIT 10000
     );
   -- Repeat until all rows updated
   ```

2. **Disable autovacuum during migration**
   ```sql
   ALTER TABLE graph_entities SET (autovacuum_enabled = false);
   -- Run migration
   UPDATE graph_entities SET tenant_id = 'default' WHERE tenant_id = '';
   -- Re-enable
   ALTER TABLE graph_entities SET (autovacuum_enabled = true);
   ```

3. **Increase statement timeout**
   ```sql
   SET statement_timeout = '1h';
   UPDATE graph_entities SET tenant_id = 'default' WHERE tenant_id = '';
   ```

### Index Creation Stuck

**Symptom:** `CREATE INDEX CONCURRENTLY` never completes

**Diagnosis:**
```sql
-- Check for blocking queries
SELECT 
    pid,
    usename,
    state,
    query,
    wait_event_type,
    wait_event
FROM pg_stat_activity
WHERE query LIKE '%CREATE INDEX%';
```

**Solutions:**

1. **Kill blocking transactions**
   ```sql
   -- Identify blockers
   SELECT pid, query FROM pg_stat_activity 
   WHERE state = 'idle in transaction';
   
   -- Terminate blocking session
   SELECT pg_terminate_backend(pid);
   ```

2. **Use regular CREATE INDEX during maintenance window**
   ```sql
   -- Faster but locks table
   CREATE INDEX idx_entities_tenant ON graph_entities(tenant_id);
   ```

## Configuration Errors

### InvalidTenantIdError

**Symptom:** `InvalidTenantIdError: Invalid tenant_id format: 'invalid@tenant'`

**Valid Format:**
- Alphanumeric characters
- Hyphens (-)
- Underscores (_)
- 1-255 characters

**Examples:**
```python
# ✅ Valid
TenantContext(tenant_id="acme-corp")
TenantContext(tenant_id="tenant_123")
TenantContext(tenant_id="org-456_789")

# ❌ Invalid
TenantContext(tenant_id="acme@corp")      # @ not allowed
TenantContext(tenant_id="tenant 123")     # spaces not allowed
TenantContext(tenant_id="")               # empty not allowed
TenantContext(tenant_id="a" * 300)        # too long (>255 chars)
```

**Solution:**
```python
# Sanitize tenant_id
import re

def sanitize_tenant_id(tenant_id: str) -> str:
    """Convert to valid tenant_id format"""
    # Remove invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', tenant_id)
    # Truncate if too long
    sanitized = sanitized[:255]
    return sanitized

# Usage
raw_tenant_id = "Acme Corp. (Main)"
tenant_id = sanitize_tenant_id(raw_tenant_id)  # "Acme-Corp---Main-"
context = TenantContext(tenant_id=tenant_id)
```

### Wrong Isolation Mode

**Symptom:** Data not isolated properly or performance issues

**Diagnosis:**
```python
# Check current mode
print(f"Isolation mode: {context.isolation_mode}")

# Verify store configuration
print(f"Store type: {type(store).__name__}")
if isinstance(store, PostgresGraphStore):
    print(f"RLS enabled: {store.enable_rls}")
```

**Solutions:**

Choose correct mode based on requirements:

| Scenario | Recommended Mode |
|----------|------------------|
| 100+ small tenants | SHARED_SCHEMA |
| 5-10 large tenants | SEPARATE_SCHEMA |
| Compliance requirements | SEPARATE_SCHEMA or SHARED_SCHEMA + RLS |
| Development/testing | DISABLED or InMemory |

## RLS-Specific Issues

### RLS Not Filtering Data

**Symptom:** Seeing all tenant data despite RLS enabled

**Diagnosis:**
```sql
-- Check if RLS is enabled and forced
SELECT tablename, rowsecurity FROM pg_tables 
WHERE tablename = 'graph_entities';

-- Check if policies exist
SELECT policyname, qual FROM pg_policies 
WHERE tablename = 'graph_entities';

-- Check tenant context
SELECT current_setting('app.current_tenant_id', true);
```

**Solutions:**

1. **Enable FORCE RLS**
   ```sql
   ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
   ```

2. **Verify policy is correct**
   ```sql
   DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
   
   CREATE POLICY tenant_isolation_entities ON graph_entities
       USING (tenant_id = current_setting('app.current_tenant_id', true));
   ```

3. **Set tenant context correctly**
   ```python
   # Ensure store sets context
   store = PostgresGraphStore(
       connection_string=conn_str,
       enable_rls=True  # This sets app.current_tenant_id
   )
   ```

### RLS Blocks All Queries

**Symptom:** All queries return 0 rows

**Diagnosis:**
```sql
-- Check if tenant context is set
SELECT current_setting('app.current_tenant_id', true);
-- If NULL or wrong value, queries will return empty
```

**Solutions:**

1. **Set tenant context**
   ```sql
   SET app.current_tenant_id = 'correct-tenant';
   ```

2. **Check policy definition**
   ```sql
   -- Policy should handle NULL case
   CREATE POLICY tenant_isolation_entities ON graph_entities
       USING (
           tenant_id = COALESCE(
               current_setting('app.current_tenant_id', true),
               ''  -- Fallback for backward compatibility
           )
       );
   ```

## SEPARATE_SCHEMA Issues

### Schema Not Found

**Symptom:** `ERROR: schema "tenant_acme" does not exist`

**Diagnosis:**
```sql
-- Check if schema exists
SELECT schema_name FROM information_schema.schemata 
WHERE schema_name = 'tenant_acme';

-- Check search_path
SHOW search_path;
```

**Solutions:**

1. **Create schema**
   ```sql
   CREATE SCHEMA IF NOT EXISTS tenant_acme;
   ```

2. **Application should create automatically**
   ```python
   # Store should create schema on first access
   context = TenantContext(
       tenant_id="acme",
       isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
   )
   # First operation creates schema
   await store.add_entity(entity, context=context)
   ```

3. **Check user permissions**
   ```sql
   -- Verify user can create schemas
   SELECT has_database_privilege('app_user', 'knowledge_graph', 'CREATE');
   
   -- Grant if needed
   GRANT CREATE ON DATABASE knowledge_graph TO app_user;
   ```

### Wrong Schema in Search Path

**Symptom:** Queries access wrong tenant's data

**Diagnosis:**
```sql
-- Check current schema
SELECT current_schema();

-- Check search_path
SHOW search_path;
```

**Solutions:**

```python
# Ensure search_path is set correctly per request
async with store._get_connection() as conn:
    schema_name = f"tenant_{context.tenant_id}"
    await conn.execute(f"SET search_path = {schema_name}, public")
    # Execute queries...
```

## Connection and Pool Issues

### Too Many Connections

**Symptom:** `FATAL: too many connections`

**Diagnosis:**
```sql
-- Check current connections
SELECT COUNT(*) FROM pg_stat_activity;

-- Check max connections
SHOW max_connections;

-- Check connections per tenant (SEPARATE_SCHEMA)
SELECT 
    application_name,
    COUNT(*) as connection_count
FROM pg_stat_activity
GROUP BY application_name;
```

**Solutions:**

1. **Increase max_connections**
   ```sql
   -- In postgresql.conf
   max_connections = 200
   
   -- Restart PostgreSQL
   ```

2. **Reduce pool size per tenant**
   ```python
   store = PostgresGraphStore(
       connection_string=conn_str,
       pool_size=5,  # Reduce from default
       max_overflow=5
   )
   ```

3. **Use connection pooler (PgBouncer)**
   ```bash
   # Install PgBouncer
   apt-get install pgbouncer
   
   # Configure connection pooling
   # Connect through PgBouncer: localhost:6432
   ```

### Connection Pool Exhaustion

**Symptom:** `TimeoutError: pool exhausted`

**Diagnosis:**
```python
# Check pool status
print(f"Pool size: {store._pool.get_size()}")
print(f"Free connections: {store._pool.get_idle_size()}")
```

**Solutions:**

1. **Increase pool size**
   ```python
   store = PostgresGraphStore(
       connection_string=conn_str,
       pool_size=50,  # Increase
       max_overflow=20
   )
   ```

2. **Add connection timeout**
   ```python
   store = PostgresGraphStore(
       connection_string=conn_str,
       pool_timeout=60  # Wait up to 60s for connection
   )
   ```

3. **Close connections properly**
   ```python
   try:
       async with store._get_connection() as conn:
           # Use connection
           pass
   finally:
       # Connection automatically returned to pool
       pass
   ```

## Getting Help

If you can't resolve the issue:

1. **Check logs** for detailed error messages
2. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Collect diagnostics**:
   ```python
   # System info
   print(f"Python version: {sys.version}")
   print(f"Store type: {type(store).__name__}")
   print(f"Isolation mode: {context.isolation_mode}")
   
   # Database info (PostgreSQL)
   print(f"PostgreSQL version: {await conn.fetchval('SELECT version()')}")
   ```

4. **Review documentation**:
   - [Setup Guide](./MULTI_TENANCY_GUIDE.md)
   - [Migration Guide](./MULTI_TENANCY_MIGRATION.md)
   - [RLS Setup](./MULTI_TENANCY_RLS_SETUP.md)
   - [SEPARATE_SCHEMA Setup](./MULTI_TENANCY_SEPARATE_SCHEMA_SETUP.md)

5. **Contact support** with:
   - Error messages
   - Logs (sanitized)
   - Configuration details
   - Steps to reproduce

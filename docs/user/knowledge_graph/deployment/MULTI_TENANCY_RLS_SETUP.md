# PostgreSQL Row-Level Security (RLS) Setup Guide

## Overview

Row-Level Security (RLS) provides defense-in-depth tenant isolation by enforcing tenant filtering at the PostgreSQL database level. Even if application code fails to filter by tenant_id, RLS policies ensure data isolation.

## When to Use RLS

**Recommended For:**
- Production SaaS applications with strict compliance requirements
- Applications where tenant isolation is critical (healthcare, finance, etc.)
- Defense-in-depth security architecture
- SHARED_SCHEMA mode deployments

**Not Needed For:**
- SEPARATE_SCHEMA mode (already isolated at schema level)
- Single-tenant deployments
- Development/testing environments
- Applications where performance is critical over security

## RLS Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer                                            │
│ ┌──────────────────────────────────────────────────────┐   │
│ │ GraphStore.query(..., context=TenantContext("acme")) │   │
│ └────────────────────────┬─────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL Connection                                        │
│ SET app.current_tenant_id = 'acme'                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL RLS Policy                                        │
│ WHERE tenant_id = current_setting('app.current_tenant_id')  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ Filtered Results (only tenant 'acme' data)                  │
└─────────────────────────────────────────────────────────────┘
```

### Key Concepts

1. **Session Variables**: Connection sets `app.current_tenant_id` before each operation
2. **RLS Policies**: Automatically filter rows based on session variable
3. **FORCE RLS**: Applies even to table owners and superusers
4. **Defense-in-Depth**: Works even if application code forgets to filter

## Step-by-Step Setup

### Prerequisites

- PostgreSQL 9.5+ (RLS introduced in 9.5)
- Database user with `ALTER TABLE` and `CREATE POLICY` permissions
- Existing graph tables with `tenant_id` columns

### Step 1: Enable RLS on Tables

```sql
-- Enable Row-Level Security
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (IMPORTANT for production!)
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
ALTER TABLE graph_relations FORCE ROW LEVEL SECURITY;
```

**Verify:**
```sql
SELECT 
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables 
WHERE tablename IN ('graph_entities', 'graph_relations');
```

Expected output:
```
 schemaname |   tablename      | rls_enabled 
------------+------------------+-------------
 public     | graph_entities   | t
 public     | graph_relations  | t
```

### Step 2: Create RLS Policies

```sql
-- Policy for entities table
CREATE POLICY tenant_isolation_entities ON graph_entities
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            ''  -- Empty string for backward compatibility
        )
    );

-- Policy for relations table
CREATE POLICY tenant_isolation_relations ON graph_relations
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            ''
        )
    );
```

**Policy Breakdown:**
- `USING` clause: Defines which rows are visible
- `current_setting('app.current_tenant_id', true)`: Gets session variable
  - Second parameter `true` = missing-ok (returns NULL if not set)
- `COALESCE(..., '')`: Returns empty string if variable not set

**Verify:**
```sql
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename IN ('graph_entities', 'graph_relations');
```

### Step 3: Test RLS Enforcement

```sql
-- Test with tenant context
SET app.current_tenant_id = 'test-tenant';
SELECT COUNT(*) FROM graph_entities;  -- Should only see test-tenant entities

-- Test without tenant context (backward compatible)
SET app.current_tenant_id = '';
SELECT COUNT(*) FROM graph_entities;  -- Should see entities with tenant_id=''

-- Reset
RESET app.current_tenant_id;
```

### Step 4: Configure Application

Enable RLS in your application:

```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore

store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/knowledge_graph",
    enable_rls=True  # Enables RLS policy enforcement
)
await store.initialize()
```

**What `enable_rls=True` does:**
1. Sets `app.current_tenant_id` session variable before each operation
2. Ensures all queries are automatically filtered by RLS policy
3. Provides defense-in-depth even if context parameter is missed

## Advanced RLS Configuration

### Multiple Policies (INSERT, UPDATE, DELETE)

The basic setup only filters `SELECT` queries. For complete protection, add policies for all operations:

```sql
-- Read policy (already covered)
CREATE POLICY tenant_isolation_entities_select ON graph_entities
    FOR SELECT
    USING (tenant_id = current_setting('app.current_tenant_id', true));

-- Insert policy (ensure new rows have correct tenant_id)
CREATE POLICY tenant_isolation_entities_insert ON graph_entities
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- Update policy (prevent changing to different tenant)
CREATE POLICY tenant_isolation_entities_update ON graph_entities
    FOR UPDATE
    USING (tenant_id = current_setting('app.current_tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true));

-- Delete policy
CREATE POLICY tenant_isolation_entities_delete ON graph_entities
    FOR DELETE
    USING (tenant_id = current_setting('app.current_tenant_id', true));
```

### Admin Bypass Policy

Allow admin users to see all tenants:

```sql
-- Create admin bypass policy
CREATE POLICY tenant_isolation_admin_bypass ON graph_entities
    TO admin_role  -- PostgreSQL role for admins
    USING (true);  -- No filtering for admins

-- Grant admin role to admin users
GRANT admin_role TO admin_user;
```

### Per-Tenant Database Users

For strongest isolation, create separate PostgreSQL users per tenant:

```sql
-- Create tenant-specific user
CREATE USER tenant_acme WITH PASSWORD 'secure_password';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON graph_entities TO tenant_acme;
GRANT SELECT, INSERT, UPDATE, DELETE ON graph_relations TO tenant_acme;

-- Create tenant-specific policy
CREATE POLICY tenant_acme_policy ON graph_entities
    TO tenant_acme
    USING (tenant_id = 'acme');
```

Then connect with tenant-specific credentials:

```python
store = PostgresGraphStore(
    connection_string="postgresql://tenant_acme:secure_password@localhost/knowledge_graph"
)
```

## Performance Considerations

### Index Requirements

RLS policies require proper indexes for good performance:

```sql
-- Essential indexes for RLS
CREATE INDEX CONCURRENTLY idx_entities_tenant 
    ON graph_entities(tenant_id);

CREATE INDEX CONCURRENTLY idx_entities_tenant_type 
    ON graph_entities(tenant_id, entity_type);

CREATE INDEX CONCURRENTLY idx_relations_tenant_source 
    ON graph_relations(tenant_id, source_id);

CREATE INDEX CONCURRENTLY idx_relations_tenant_target 
    ON graph_relations(tenant_id, target_id);
```

**Verify index usage:**
```sql
EXPLAIN ANALYZE
SELECT * FROM graph_entities 
WHERE entity_type = 'Person';

-- Should show "Index Scan using idx_entities_tenant_type"
```

### RLS Overhead

Typical RLS overhead: **5-15%** query time increase with proper indexes.

**Benchmark RLS impact:**
```sql
-- Without RLS (disable temporarily)
ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM graph_entities WHERE entity_type = 'Person';

-- With RLS
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
SET app.current_tenant_id = 'test-tenant';
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM graph_entities WHERE entity_type = 'Person';
```

### When RLS is Too Slow

If RLS adds unacceptable overhead:

1. **Switch to SEPARATE_SCHEMA mode** (better performance, stronger isolation)
2. **Optimize indexes** (ensure all queries use tenant-aware indexes)
3. **Use connection pooling** (reduce SET overhead)
4. **Consider partition tables** by tenant_id for very large tables

## Monitoring and Debugging

### Check Current Tenant Context

```sql
-- In psql session
SHOW app.current_tenant_id;

-- Or
SELECT current_setting('app.current_tenant_id', true);
```

### Monitor RLS Performance

```sql
-- Check if RLS is causing slow queries
SELECT 
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%graph_entities%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Debug RLS Filtering

```sql
-- See actual query with RLS applied
EXPLAIN (VERBOSE)
SELECT * FROM graph_entities 
WHERE entity_type = 'Person';

-- Should show RLS filter: (tenant_id = current_setting(...))
```

### Audit RLS Bypass Attempts

Log when users try to access data from other tenants:

```sql
-- Enable query logging
ALTER DATABASE knowledge_graph SET log_statement = 'all';

-- Check logs for RLS violations
-- Look for queries that return 0 rows (blocked by RLS)
```

## Security Best Practices

### 1. Always Use FORCE ROW LEVEL SECURITY

```sql
-- ❌ BAD: Superusers can bypass RLS
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;

-- ✅ GOOD: RLS applies to everyone
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
```

### 2. Set Tenant Context in Transaction

```python
async def execute_with_tenant_context(conn, tenant_id: str, operation):
    """Execute operation with tenant context in transaction"""
    async with conn.transaction():
        await conn.execute("SET app.current_tenant_id = $1", tenant_id)
        result = await operation(conn)
        # Context automatically reset at transaction end
        return result
```

### 3. Validate Tenant Access

Before setting tenant context, validate user has access:

```python
def validate_tenant_access(user_id: str, tenant_id: str) -> bool:
    """Check if user has access to tenant"""
    # Query user_tenant_access table
    # Return True if user is member of tenant
    pass

async def query_entities(tenant_id: str, user_id: str):
    if not validate_tenant_access(user_id, tenant_id):
        raise PermissionError(f"User {user_id} cannot access tenant {tenant_id}")
    
    context = TenantContext(tenant_id=tenant_id)
    return await store.query(GraphQuery(entity_type="*"), context=context)
```

### 4. Audit Tenant Context Changes

Log all tenant context changes for compliance:

```python
import logging

logger = logging.getLogger("tenant_security")

async def set_tenant_context(conn, tenant_id: str, user_id: str):
    """Set tenant context with audit logging"""
    logger.info(f"User {user_id} accessing tenant {tenant_id}")
    await conn.execute("SET app.current_tenant_id = $1", tenant_id)
```

## Troubleshooting

### Issue: RLS blocks all queries

**Symptom:** All queries return 0 rows

**Solution:**
```sql
-- Check if tenant context is set
SELECT current_setting('app.current_tenant_id', true);

-- If NULL or wrong tenant, set correctly
SET app.current_tenant_id = 'correct-tenant';
```

### Issue: RLS doesn't filter data

**Symptom:** Seeing data from all tenants

**Solution:**
```sql
-- Verify RLS is enabled and forced
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'graph_entities';

-- If rowsecurity = false, enable it
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
```

### Issue: Performance degradation

**Symptom:** Queries are much slower with RLS

**Solution:**
```sql
-- Check if indexes exist
SELECT indexname FROM pg_indexes 
WHERE tablename = 'graph_entities' 
  AND indexname LIKE '%tenant%';

-- If missing, create indexes
CREATE INDEX CONCURRENTLY idx_entities_tenant ON graph_entities(tenant_id);
```

## Migration from Non-RLS

If you have an existing deployment without RLS:

1. **Test on staging first** with production data
2. **Benchmark performance** before and after
3. **Create indexes** before enabling RLS
4. **Enable during low-traffic window**
5. **Monitor for errors** after deployment

```bash
# Migration script
psql -U postgres -d knowledge_graph << 'EOF'
-- 1. Create indexes (no downtime)
CREATE INDEX CONCURRENTLY idx_entities_tenant ON graph_entities(tenant_id);

-- 2. Enable RLS (no downtime, but performance impact)
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;

-- 3. Create policy
CREATE POLICY tenant_isolation_entities ON graph_entities
    USING (tenant_id = current_setting('app.current_tenant_id', true));

-- 4. Verify
SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'graph_entities';
EOF
```

## Additional Resources

- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Multi-Tenancy Setup Guide](./MULTI_TENANCY_GUIDE.md)
- [Migration Guide](./MULTI_TENANCY_MIGRATION.md)
- [Troubleshooting Guide](./MULTI_TENANCY_TROUBLESHOOTING.md)

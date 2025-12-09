# Multi-Tenancy Migration Guide

## Overview

This guide provides step-by-step instructions for migrating existing single-tenant Knowledge Graph deployments to multi-tenant mode.

## Table of Contents

- [Pre-Migration Checklist](#pre-migration-checklist)
- [Migration Strategies](#migration-strategies)
- [Step-by-Step Migration](#step-by-step-migration)
- [Rollback Procedures](#rollback-procedures)
- [Post-Migration Verification](#post-migration-verification)

## Pre-Migration Checklist

Before starting migration:

- [ ] **Backup all data** (database, SQLite files, etc.)
- [ ] **Test migration on staging/development environment first**
- [ ] **Review current data volume** (estimate migration time)
- [ ] **Plan maintenance window** (for production migration)
- [ ] **Verify application compatibility** (update code to use TenantContext)
- [ ] **Choose isolation mode** (SHARED_SCHEMA or SEPARATE_SCHEMA)
- [ ] **Prepare rollback plan** (see Rollback Procedures section)

## Migration Strategies

### Strategy 1: Zero-Downtime Migration (Recommended)

Gradual migration with backward compatibility:

1. Add tenant_id columns with defaults (no downtime)
2. Backfill existing data to 'default' or 'legacy' tenant
3. Add indexes concurrently (PostgreSQL) or during low traffic (SQLite)
4. Deploy application code that supports both modes
5. Enable RLS policies (optional)
6. Gradually migrate tenants to multi-tenant mode

**Pros:** No downtime, low risk
**Cons:** Longer migration process

### Strategy 2: Maintenance Window Migration

Complete migration during scheduled downtime:

1. Schedule maintenance window
2. Stop application
3. Run all migration steps
4. Test thoroughly
5. Deploy updated application
6. Resume operations

**Pros:** Faster, simpler
**Cons:** Requires downtime

## Step-by-Step Migration

### PostgreSQL Migration

#### Step 1: Add tenant_id Columns

**Script:** `migrations/001_add_tenant_id_column.sql`

```sql
-- Add tenant_id column to entities table
-- Uses empty string '' as default for backward compatibility
ALTER TABLE graph_entities 
ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '';

-- Add tenant_id column to relations table
ALTER TABLE graph_relations 
ADD COLUMN IF NOT EXISTS tenant_id TEXT NOT NULL DEFAULT '';

-- Verify columns added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name IN ('graph_entities', 'graph_relations') 
  AND column_name = 'tenant_id';
```

**Rollback:**
```sql
-- Remove tenant_id columns
ALTER TABLE graph_entities DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE graph_relations DROP COLUMN IF EXISTS tenant_id;
```

**Execution:**
```bash
# Test on staging first
psql -U postgres -d knowledge_graph_staging -f migrations/001_add_tenant_id_column.sql

# Production (with backup)
pg_dump knowledge_graph > backup_before_migration.sql
psql -U postgres -d knowledge_graph -f migrations/001_add_tenant_id_column.sql
```

#### Step 2: Backfill Historical Data

**Script:** `migrations/002_backfill_tenant_id.sql`

```sql
-- Option A: Assign all existing data to 'default' tenant
UPDATE graph_entities 
SET tenant_id = 'default' 
WHERE tenant_id = '';

UPDATE graph_relations 
SET tenant_id = 'default' 
WHERE tenant_id = '';

-- Option B: Assign to 'legacy' tenant
UPDATE graph_entities 
SET tenant_id = 'legacy_default' 
WHERE tenant_id = '';

UPDATE graph_relations 
SET tenant_id = 'legacy_default' 
WHERE tenant_id = '';

-- Verify backfill
SELECT 
    tenant_id, 
    COUNT(*) as entity_count 
FROM graph_entities 
GROUP BY tenant_id;

SELECT 
    tenant_id, 
    COUNT(*) as relation_count 
FROM graph_relations 
GROUP BY tenant_id;
```

**Rollback:**
```sql
-- Reset to empty string default
UPDATE graph_entities SET tenant_id = '' WHERE tenant_id IN ('default', 'legacy_default');
UPDATE graph_relations SET tenant_id = '' WHERE tenant_id IN ('default', 'legacy_default');
```

**Execution:**
```bash
# Test row count before
psql -U postgres -d knowledge_graph -c "SELECT COUNT(*) FROM graph_entities WHERE tenant_id = '';"

# Run backfill
psql -U postgres -d knowledge_graph -f migrations/002_backfill_tenant_id.sql

# Verify no rows left with empty tenant_id
psql -U postgres -d knowledge_graph -c "SELECT COUNT(*) FROM graph_entities WHERE tenant_id = '';"
```

#### Step 3: Create Indexes

**Script:** `migrations/003_create_tenant_indexes.sql`

```sql
-- Create indexes CONCURRENTLY (no table locks, no downtime)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_tenant 
    ON graph_entities(tenant_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_tenant_type 
    ON graph_entities(tenant_id, entity_type);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant 
    ON graph_relations(tenant_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant_source 
    ON graph_relations(tenant_id, source_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant_target 
    ON graph_relations(tenant_id, target_id);

-- Verify indexes created
SELECT 
    schemaname, 
    tablename, 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename IN ('graph_entities', 'graph_relations')
  AND indexname LIKE '%tenant%';
```

**Rollback:**
```sql
DROP INDEX IF EXISTS idx_entities_tenant;
DROP INDEX IF EXISTS idx_entities_tenant_type;
DROP INDEX IF EXISTS idx_relations_tenant;
DROP INDEX IF EXISTS idx_relations_tenant_source;
DROP INDEX IF EXISTS idx_relations_tenant_target;
```

**Execution:**
```bash
# Run concurrently (no downtime)
psql -U postgres -d knowledge_graph -f migrations/003_create_tenant_indexes.sql

# Monitor index creation progress
psql -U postgres -d knowledge_graph -c "
SELECT 
    now()::time(0), 
    query, 
    state, 
    wait_event_type, 
    wait_event 
FROM pg_stat_activity 
WHERE query LIKE '%CREATE INDEX%';
"
```

#### Step 4: Update Primary Keys (Optional)

If you want composite primary keys (id, tenant_id):

**Script:** `migrations/004_update_primary_keys.sql`

```sql
-- ⚠️ WARNING: This requires table locks. Do during maintenance window.

-- Drop existing primary key constraints
ALTER TABLE graph_entities DROP CONSTRAINT IF EXISTS graph_entities_pkey;
ALTER TABLE graph_relations DROP CONSTRAINT IF EXISTS graph_relations_pkey;

-- Create new composite primary keys
ALTER TABLE graph_entities ADD PRIMARY KEY (id, tenant_id);
ALTER TABLE graph_relations ADD PRIMARY KEY (id, tenant_id);

-- Verify
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    conrelid::regclass AS table_name
FROM pg_constraint
WHERE conrelid IN ('graph_entities'::regclass, 'graph_relations'::regclass)
  AND contype = 'p';
```

**⚠️ Note:** This step requires table locks. Schedule during maintenance window.

**Rollback:**
```sql
ALTER TABLE graph_entities DROP CONSTRAINT IF EXISTS graph_entities_pkey;
ALTER TABLE graph_entities ADD PRIMARY KEY (id);

ALTER TABLE graph_relations DROP CONSTRAINT IF EXISTS graph_relations_pkey;
ALTER TABLE graph_relations ADD PRIMARY KEY (id);
```

#### Step 5: Enable RLS Policies (Optional)

**Script:** `migrations/005_enable_rls.sql`

```sql
-- Enable Row-Level Security
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;
ALTER TABLE graph_relations FORCE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY tenant_isolation_entities ON graph_entities
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_isolation_relations ON graph_relations
    USING (tenant_id = current_setting('app.current_tenant_id', true));

-- Verify RLS enabled
SELECT 
    schemaname, 
    tablename, 
    rowsecurity AS rls_enabled 
FROM pg_tables 
WHERE tablename IN ('graph_entities', 'graph_relations');

-- Verify policies created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    qual
FROM pg_policies
WHERE tablename IN ('graph_entities', 'graph_relations');
```

**Rollback:**
```sql
-- Drop RLS policies
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;

-- Disable RLS
ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations DISABLE ROW LEVEL SECURITY;
```

**Testing RLS:**
```sql
-- Test isolation works
SET app.current_tenant_id = 'tenant-a';
SELECT COUNT(*) FROM graph_entities;  -- Should only see tenant-a entities

SET app.current_tenant_id = 'tenant-b';
SELECT COUNT(*) FROM graph_entities;  -- Should only see tenant-b entities

-- Reset session variable
RESET app.current_tenant_id;
```

### SQLite Migration

#### Step 1: Add tenant_id Columns

**Script:** `migrations/sqlite_001_add_tenant_id.sql`

```sql
-- SQLite doesn't support ADD COLUMN IF NOT EXISTS
-- Check if column exists first

-- Add tenant_id to entities
ALTER TABLE entities ADD COLUMN tenant_id TEXT;

-- Add tenant_id to relations
ALTER TABLE relations ADD COLUMN tenant_id TEXT;

-- Verify
PRAGMA table_info(entities);
PRAGMA table_info(relations);
```

**Execution:**
```python
import sqlite3
import shutil

# Backup database
shutil.copy("knowledge_graph.db", "knowledge_graph_backup.db")

# Run migration
conn = sqlite3.connect("knowledge_graph.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE entities ADD COLUMN tenant_id TEXT")
    cursor.execute("ALTER TABLE relations ADD COLUMN tenant_id TEXT")
    conn.commit()
    print("Migration successful")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("Columns already exist")
    else:
        raise
finally:
    conn.close()
```

#### Step 2: Backfill Data

**Script:** `migrations/sqlite_002_backfill.sql`

```sql
-- Assign existing data to default tenant
UPDATE entities 
SET tenant_id = 'default' 
WHERE tenant_id IS NULL;

UPDATE relations 
SET tenant_id = 'default' 
WHERE tenant_id IS NULL;

-- Verify
SELECT tenant_id, COUNT(*) as count FROM entities GROUP BY tenant_id;
SELECT tenant_id, COUNT(*) as count FROM relations GROUP BY tenant_id;
```

#### Step 3: Create Indexes

**Script:** `migrations/sqlite_003_create_indexes.sql`

```sql
-- Create indexes for tenant-scoped queries
CREATE INDEX IF NOT EXISTS idx_entities_tenant 
    ON entities(tenant_id);

CREATE INDEX IF NOT EXISTS idx_entities_tenant_type 
    ON entities(tenant_id, entity_type);

CREATE INDEX IF NOT EXISTS idx_relations_tenant 
    ON relations(tenant_id);

CREATE INDEX IF NOT EXISTS idx_relations_tenant_source 
    ON relations(tenant_id, source_id);

CREATE INDEX IF NOT EXISTS idx_relations_tenant_target 
    ON relations(tenant_id, target_id);

-- Verify
SELECT name, sql FROM sqlite_master 
WHERE type = 'index' 
  AND name LIKE '%tenant%';
```

#### Step 4: Update Primary Keys (Requires Table Rebuild)

**⚠️ Warning:** SQLite requires rebuilding tables to change primary keys.

**Script:** `migrations/sqlite_004_rebuild_tables.sql`

```sql
-- Backup tables
CREATE TABLE entities_backup AS SELECT * FROM entities;
CREATE TABLE relations_backup AS SELECT * FROM relations;

-- Drop original tables
DROP TABLE entities;
DROP TABLE relations;

-- Recreate with composite primary keys
CREATE TABLE entities (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    entity_type TEXT NOT NULL,
    properties TEXT NOT NULL,
    embedding BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

CREATE TABLE relations (
    id TEXT NOT NULL,
    tenant_id TEXT NOT NULL DEFAULT 'default',
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, tenant_id)
);

-- Restore data
INSERT INTO entities SELECT * FROM entities_backup;
INSERT INTO relations SELECT * FROM relations_backup;

-- Drop backups
DROP TABLE entities_backup;
DROP TABLE relations_backup;

-- Recreate indexes
CREATE INDEX idx_entities_tenant ON entities(tenant_id);
CREATE INDEX idx_entities_tenant_type ON entities(tenant_id, entity_type);
CREATE INDEX idx_relations_tenant ON relations(tenant_id);
CREATE INDEX idx_relations_tenant_source ON relations(tenant_id, source_id);
CREATE INDEX idx_relations_tenant_target ON relations(tenant_id, target_id);
```

**Execution:**
```python
import sqlite3
import shutil

# Full backup
shutil.copy("knowledge_graph.db", f"knowledge_graph_backup_{datetime.now().isoformat()}.db")

# Run in transaction
conn = sqlite3.connect("knowledge_graph.db")
try:
    with open("migrations/sqlite_004_rebuild_tables.sql") as f:
        conn.executescript(f.read())
    print("Table rebuild successful")
except Exception as e:
    print(f"Error: {e}")
    print("Restore from backup!")
finally:
    conn.close()
```

## Application Code Migration

### Update Code to Use TenantContext

**Before (single-tenant):**
```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore

store = PostgresGraphStore(connection_string=conn_str)
await store.initialize()

entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
await store.add_entity(entity)
```

**After (multi-tenant):**
```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext

store = PostgresGraphStore(connection_string=conn_str, enable_rls=True)
await store.initialize()

# Get tenant from request context (example)
def get_current_tenant() -> str:
    # Implement based on your auth system
    return request.headers.get("X-Tenant-ID", "default")

context = TenantContext(tenant_id=get_current_tenant())

entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
await store.add_entity(entity, context=context)
```

### Gradual Migration Pattern

Support both modes during transition:

```python
from typing import Optional

class TenantAwareStore:
    def __init__(self, store: GraphStore, multi_tenancy_enabled: bool = False):
        self.store = store
        self.multi_tenancy_enabled = multi_tenancy_enabled
    
    def get_context(self, tenant_id: Optional[str] = None) -> Optional[TenantContext]:
        if not self.multi_tenancy_enabled or tenant_id is None:
            return None
        return TenantContext(tenant_id=tenant_id)
    
    async def add_entity(self, entity: Entity, tenant_id: Optional[str] = None):
        context = self.get_context(tenant_id)
        await self.store.add_entity(entity, context=context)

# Usage
store = TenantAwareStore(graph_store, multi_tenancy_enabled=True)

# Works with tenant_id
await store.add_entity(entity, tenant_id="acme")

# Works without tenant_id (backward compatible)
await store.add_entity(entity)
```

## Rollback Procedures

### Complete Rollback (PostgreSQL)

```bash
#!/bin/bash
# rollback_complete.sh

set -e

echo "Rolling back multi-tenancy migration..."

# Step 1: Disable RLS
psql -U postgres -d knowledge_graph -c "
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;
ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations DISABLE ROW LEVEL SECURITY;
"

# Step 2: Drop tenant indexes
psql -U postgres -d knowledge_graph -c "
DROP INDEX IF EXISTS idx_entities_tenant;
DROP INDEX IF EXISTS idx_entities_tenant_type;
DROP INDEX IF EXISTS idx_relations_tenant;
DROP INDEX IF EXISTS idx_relations_tenant_source;
DROP INDEX IF EXISTS idx_relations_tenant_target;
"

# Step 3: Remove tenant_id columns
psql -U postgres -d knowledge_graph -c "
ALTER TABLE graph_entities DROP COLUMN IF EXISTS tenant_id;
ALTER TABLE graph_relations DROP COLUMN IF EXISTS tenant_id;
"

echo "Rollback complete!"
```

### Partial Rollback (Keep Columns, Disable RLS)

```sql
-- Keep tenant_id columns but disable RLS
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;
ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations DISABLE ROW LEVEL SECURITY;

-- Reset tenant_id to empty/NULL
UPDATE graph_entities SET tenant_id = '';
UPDATE graph_relations SET tenant_id = '';
```

### Restore from Backup

```bash
#!/bin/bash
# restore_from_backup.sh

BACKUP_FILE="backup_before_migration.sql"

echo "Restoring from backup: $BACKUP_FILE"

# PostgreSQL
pg_restore -U postgres -d knowledge_graph -c $BACKUP_FILE

# SQLite
# cp knowledge_graph_backup.db knowledge_graph.db

echo "Restore complete!"
```

## Post-Migration Verification

### Verification Checklist

- [ ] All existing data accessible via 'default' tenant
- [ ] Tenant isolation working (tenants cannot see each other's data)
- [ ] RLS policies enforcing isolation (if enabled)
- [ ] Indexes created and being used by queries
- [ ] Application code using TenantContext correctly
- [ ] Performance acceptable (query times within SLA)
- [ ] No errors in application logs

### Verification Scripts

**Test Tenant Isolation:**
```python
import asyncio
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext
from aiecs.domain.knowledge_graph.models.entity import Entity

async def verify_isolation():
    store = PostgresGraphStore(connection_string=conn_str, enable_rls=True)
    await store.initialize()
    
    # Add entity for tenant A
    ctx_a = TenantContext(tenant_id="tenant-a")
    entity_a = Entity(id="e1", entity_type="Test", properties={"tenant": "A"})
    await store.add_entity(entity_a, context=ctx_a)
    
    # Add entity for tenant B
    ctx_b = TenantContext(tenant_id="tenant-b")
    entity_b = Entity(id="e2", entity_type="Test", properties={"tenant": "B"})
    await store.add_entity(entity_b, context=ctx_b)
    
    # Verify isolation
    results_a = await store.query(GraphQuery(entity_type="Test"), context=ctx_a)
    results_b = await store.query(GraphQuery(entity_type="Test"), context=ctx_b)
    
    assert len(results_a) == 1 and results_a[0].properties["tenant"] == "A"
    assert len(results_b) == 1 and results_b[0].properties["tenant"] == "B"
    
    print("✅ Tenant isolation verified!")

asyncio.run(verify_isolation())
```

**Check Index Usage:**
```sql
-- PostgreSQL: Verify indexes are used
EXPLAIN ANALYZE
SELECT * FROM graph_entities 
WHERE tenant_id = 'tenant-a' AND entity_type = 'Person';

-- Should show "Index Scan using idx_entities_tenant_type"
```

**Monitor RLS Performance:**
```sql
-- Check RLS overhead
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM graph_entities 
WHERE tenant_id = 'tenant-a' 
LIMIT 100;
```

## Migration Timeline Example

### Small Database (< 1M entities)

| Phase | Duration | Downtime |
|-------|----------|----------|
| Backup | 5 min | No |
| Add columns | 1 min | No |
| Backfill data | 10 min | No |
| Create indexes | 15 min | No |
| Update app code | N/A | No |
| Enable RLS | 1 min | No |
| **Total** | **32 min** | **0 min** |

### Large Database (> 10M entities)

| Phase | Duration | Downtime |
|-------|----------|----------|
| Backup | 30 min | No |
| Add columns | 2 min | No |
| Backfill data | 2 hours | No |
| Create indexes | 1 hour | No |
| Update primary keys | 30 min | **Yes** |
| Update app code | N/A | No |
| Enable RLS | 2 min | No |
| **Total** | **4 hours** | **30 min** |

**Recommendation:** For large databases, skip primary key updates and run during maintenance window if necessary.

## Support

If you encounter issues during migration:

1. Check [Troubleshooting Guide](./MULTI_TENANCY_TROUBLESHOOTING.md)
2. Review application logs for errors
3. Verify database schema with verification scripts
4. Restore from backup if needed
5. Contact support with migration logs

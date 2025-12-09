# PostgreSQL SEPARATE_SCHEMA Setup Guide

## Overview

SEPARATE_SCHEMA mode provides the strongest tenant isolation by giving each tenant its own PostgreSQL schema. This approach offers better performance than RLS and complete logical separation of tenant data.

## When to Use SEPARATE_SCHEMA

**Recommended For:**
- Enterprise customers with large data volumes (>1M entities)
- Applications requiring strongest isolation (compliance, auditing)
- Per-tenant schema customization requirements
- High-performance requirements (no RLS overhead)
- Tenants with significantly different data sizes

**Not Recommended For:**
- Applications with hundreds/thousands of small tenants (management overhead)
- Shared hosting environments with limited resources
- Simple SaaS applications (SHARED_SCHEMA is simpler)

## Architecture

### Schema Separation

```
knowledge_graph database
├── public schema (shared infrastructure)
│   ├── user_accounts
│   ├── tenant_metadata
│   └── system_config
│
├── tenant_acme schema
│   ├── graph_entities
│   ├── graph_relations
│   └── (tenant-specific tables)
│
├── tenant_globex schema
│   ├── graph_entities
│   ├── graph_relations
│   └── (tenant-specific tables)
│
└── tenant_xyz schema
    ├── graph_entities
    ├── graph_relations
    └── (tenant-specific tables)
```

### How It Works

1. **Schema Creation**: Each tenant gets a PostgreSQL schema (`tenant_{tenant_id}`)
2. **Search Path**: Connection sets `search_path = tenant_acme, public`
3. **Automatic Routing**: All queries automatically route to tenant schema
4. **No Filtering Needed**: No tenant_id column filtering required

## Step-by-Step Setup

### Prerequisites

- PostgreSQL 9.3+ (schemas supported in all versions)
- Database user with `CREATE SCHEMA` permission
- Sufficient disk space for per-tenant tables

### Step 1: Create Base Schema Template

Create a template schema that will be replicated for each tenant:

```sql
-- Create template schema (optional, for consistency)
CREATE SCHEMA IF NOT EXISTS tenant_template;

-- Create tables in template
CREATE TABLE tenant_template.graph_entities (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding BYTEA,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tenant_template.graph_relations (
    id TEXT PRIMARY KEY,
    relation_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    weight REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_entities_type ON tenant_template.graph_entities(entity_type);
CREATE INDEX idx_relations_source ON tenant_template.graph_relations(source_id);
CREATE INDEX idx_relations_target ON tenant_template.graph_relations(target_id);
```

### Step 2: Create Tenant Schema Function

Automate tenant schema creation:

```sql
-- Function to create new tenant schema
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_name TEXT)
RETURNS void AS $$
BEGIN
    -- Create schema
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', tenant_name);
    
    -- Create entities table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.graph_entities (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            properties JSONB NOT NULL DEFAULT ''{}''::jsonb,
            embedding BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )', tenant_name);
    
    -- Create relations table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.graph_relations (
            id TEXT PRIMARY KEY,
            relation_type TEXT NOT NULL,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            properties JSONB NOT NULL DEFAULT ''{}''::jsonb,
            weight REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )', tenant_name);
    
    -- Create indexes
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_entities_type ON %I.graph_entities(entity_type)', tenant_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_relations_source ON %I.graph_relations(source_id)', tenant_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_relations_target ON %I.graph_relations(target_id)', tenant_name);
    
    RAISE NOTICE 'Created schema for tenant: %', tenant_name;
END;
$$ LANGUAGE plpgsql;

-- Usage
SELECT create_tenant_schema('tenant_acme');
SELECT create_tenant_schema('tenant_globex');
```

### Step 3: Create Tenant on First Access

The application can create schemas automatically on first access:

```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    TenantIsolationMode,
)

# Initialize store
store = PostgresGraphStore(
    connection_string="postgresql://user:pass@localhost/knowledge_graph"
)
await store.initialize()

# Context with SEPARATE_SCHEMA mode
context = TenantContext(
    tenant_id="acme-corp",
    isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
)

# First operation creates schema automatically
entity = Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
await store.add_entity(entity, context=context)
# Internally:
# 1. CREATE SCHEMA IF NOT EXISTS tenant_acme
# 2. SET search_path = tenant_acme, public
# 3. INSERT INTO graph_entities ...
```

### Step 4: Verify Schema Creation

```sql
-- List all tenant schemas
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name LIKE 'tenant_%'
ORDER BY schema_name;

-- Check tables in specific tenant schema
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'tenant_acme';

-- Verify data isolation
SET search_path = tenant_acme, public;
SELECT COUNT(*) FROM graph_entities;  -- Tenant A entities

SET search_path = tenant_globex, public;
SELECT COUNT(*) FROM graph_entities;  -- Tenant B entities
```

## Advanced Configuration

### Per-Tenant Customization

Each tenant can have custom tables/columns:

```sql
-- Tenant A needs custom fields
ALTER TABLE tenant_acme.graph_entities 
ADD COLUMN custom_field TEXT;

-- Tenant B has different structure
CREATE TABLE tenant_globex.custom_analytics (
    entity_id TEXT REFERENCES tenant_globex.graph_entities(id),
    metric_name TEXT,
    metric_value REAL
);
```

### Schema Cloning

Clone existing tenant schema for new tenant:

```sql
-- Clone schema structure (PostgreSQL 15+)
CREATE SCHEMA tenant_new AUTHORIZATION app_user;

-- Copy tables and data
CREATE TABLE tenant_new.graph_entities 
    (LIKE tenant_template.graph_entities INCLUDING ALL);

CREATE TABLE tenant_new.graph_relations 
    (LIKE tenant_template.graph_relations INCLUDING ALL);
```

For older PostgreSQL versions, use pg_dump:

```bash
# Export template schema
pg_dump -U postgres -d knowledge_graph \
    --schema=tenant_template \
    --schema-only \
    > tenant_schema.sql

# Modify for new tenant
sed 's/tenant_template/tenant_new/g' tenant_schema.sql > tenant_new.sql

# Import
psql -U postgres -d knowledge_graph -f tenant_new.sql
```

### Schema-Level Permissions

Grant per-tenant access control:

```sql
-- Create tenant-specific role
CREATE ROLE tenant_acme_user LOGIN PASSWORD 'secure_password';

-- Grant schema access
GRANT USAGE ON SCHEMA tenant_acme TO tenant_acme_user;
GRANT ALL ON ALL TABLES IN SCHEMA tenant_acme TO tenant_acme_user;

-- Prevent access to other tenants
REVOKE ALL ON SCHEMA tenant_globex FROM tenant_acme_user;

-- Connect as tenant-specific user
-- psql -U tenant_acme_user -d knowledge_graph
```

## Performance Optimization

### Connection Pooling

Use separate connection pools per tenant:

```python
from aiecs.infrastructure.graph_storage.postgres import PostgresGraphStore

class TenantConnectionManager:
    def __init__(self, base_connection_string: str):
        self.base_connection_string = base_connection_string
        self.tenant_stores: Dict[str, PostgresGraphStore] = {}
    
    async def get_store(self, tenant_id: str) -> PostgresGraphStore:
        """Get or create store for tenant"""
        if tenant_id not in self.tenant_stores:
            store = PostgresGraphStore(
                connection_string=self.base_connection_string,
                pool_size=10  # Per-tenant pool
            )
            await store.initialize()
            self.tenant_stores[tenant_id] = store
        
        return self.tenant_stores[tenant_id]
```

### Maintenance Per Schema

Run maintenance operations per tenant:

```sql
-- Vacuum specific tenant schema
VACUUM ANALYZE tenant_acme.graph_entities;
VACUUM ANALYZE tenant_acme.graph_relations;

-- Reindex tenant schema
REINDEX SCHEMA tenant_acme;
```

### Schema-Level Statistics

Collect statistics per tenant:

```sql
-- Get tenant schema sizes
SELECT 
    schema_name,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))) as schema_size
FROM pg_tables 
WHERE schemaname LIKE 'tenant_%'
GROUP BY schema_name
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;

-- Get row counts per tenant
SELECT 
    table_schema,
    SUM((SELECT COUNT(*) FROM (SELECT 1 FROM graph_entities) sub)) as entity_count
FROM information_schema.tables
WHERE table_schema LIKE 'tenant_%'
GROUP BY table_schema;
```

## Migration Strategies

### From SHARED_SCHEMA to SEPARATE_SCHEMA

Migrate tenants from SHARED_SCHEMA to SEPARATE_SCHEMA:

```sql
-- Create migration function
CREATE OR REPLACE FUNCTION migrate_tenant_to_separate_schema(
    source_tenant_id TEXT
)
RETURNS void AS $$
DECLARE
    schema_name TEXT := 'tenant_' || source_tenant_id;
BEGIN
    -- 1. Create new schema
    PERFORM create_tenant_schema(schema_name);
    
    -- 2. Copy entities
    EXECUTE format('
        INSERT INTO %I.graph_entities 
        SELECT id, entity_type, properties, embedding, created_at, updated_at
        FROM public.graph_entities
        WHERE tenant_id = %L
    ', schema_name, source_tenant_id);
    
    -- 3. Copy relations
    EXECUTE format('
        INSERT INTO %I.graph_relations 
        SELECT id, relation_type, source_id, target_id, properties, weight, created_at, updated_at
        FROM public.graph_relations
        WHERE tenant_id = %L
    ', schema_name, source_tenant_id);
    
    -- 4. Verify counts match
    -- 5. Delete from shared tables (after verification)
    
    RAISE NOTICE 'Migrated tenant % to separate schema', source_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- Migrate tenant
SELECT migrate_tenant_to_separate_schema('acme-corp');
```

### Gradual Migration

Migrate one tenant at a time:

```python
async def migrate_tenant_gradual(tenant_id: str):
    """Migrate single tenant to SEPARATE_SCHEMA"""
    
    # 1. Read all data for tenant from SHARED_SCHEMA
    shared_context = TenantContext(
        tenant_id=tenant_id,
        isolation_mode=TenantIsolationMode.SHARED_SCHEMA
    )
    
    entities = await store.query(
        GraphQuery(entity_type="*"),
        context=shared_context
    )
    
    # 2. Write to SEPARATE_SCHEMA
    separate_context = TenantContext(
        tenant_id=tenant_id,
        isolation_mode=TenantIsolationMode.SEPARATE_SCHEMA
    )
    
    for entity in entities:
        await store.add_entity(entity, context=separate_context)
    
    # 3. Verify counts
    # 4. Delete from SHARED_SCHEMA
    # 5. Update application config to use SEPARATE_SCHEMA
```

## Monitoring and Management

### Schema Discovery

```sql
-- List all tenant schemas with metadata
SELECT 
    s.schema_name,
    pg_size_pretty(SUM(pg_total_relation_size(t.schemaname||'.'||t.tablename))) as size,
    MAX(t.schemaname) as schema_exists
FROM information_schema.schemata s
LEFT JOIN pg_tables t ON s.schema_name = t.schemaname
WHERE s.schema_name LIKE 'tenant_%'
GROUP BY s.schema_name
ORDER BY s.schema_name;
```

### Automated Cleanup

Remove inactive tenant schemas:

```python
async def cleanup_inactive_tenants(days_inactive: int = 90):
    """Remove schemas for tenants inactive > N days"""
    
    # Query tenant metadata
    inactive_tenants = await get_inactive_tenants(days_inactive)
    
    for tenant_id in inactive_tenants:
        schema_name = f"tenant_{tenant_id}"
        
        # Backup before deletion
        await backup_tenant_schema(schema_name)
        
        # Drop schema
        await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        
        print(f"Cleaned up schema: {schema_name}")
```

### Backup and Restore

Backup individual tenant:

```bash
#!/bin/bash
TENANT_ID="acme-corp"
SCHEMA_NAME="tenant_${TENANT_ID}"

# Backup tenant schema
pg_dump -U postgres -d knowledge_graph \
    --schema=${SCHEMA_NAME} \
    --format=custom \
    --file=${TENANT_ID}_backup_$(date +%Y%m%d).dump

# Restore tenant schema
pg_restore -U postgres -d knowledge_graph \
    --clean --if-exists \
    ${TENANT_ID}_backup_20241208.dump
```

## Security Considerations

### Schema Permissions

Ensure tenants cannot access other schemas:

```sql
-- Revoke default public access
REVOKE ALL ON SCHEMA tenant_acme FROM PUBLIC;

-- Grant specific access
GRANT USAGE ON SCHEMA tenant_acme TO app_user;
GRANT ALL ON ALL TABLES IN SCHEMA tenant_acme TO app_user;

-- Prevent cross-schema access
REVOKE ALL ON SCHEMA tenant_globex FROM app_user;
```

### Search Path Security

Be careful with search_path to prevent SQL injection:

```python
# ❌ BAD: SQL injection risk
tenant_id = "acme; DROP SCHEMA tenant_globex CASCADE; --"
await conn.execute(f"SET search_path = tenant_{tenant_id}, public")

# ✅ GOOD: Use parameterized queries
from aiecs.infrastructure.graph_storage.tenant import validate_tenant_id
validate_tenant_id(tenant_id)  # Validates format
schema_name = f"tenant_{tenant_id}"
await conn.execute("SET search_path = $1, public", schema_name)
```

### Cross-Schema Queries

Explicitly prevent cross-schema references:

```sql
-- Prevent foreign keys to other tenants
-- (Not possible across schemas by default, but be aware)

-- Audit cross-schema queries
SELECT 
    query,
    calls,
    mean_exec_time
FROM pg_stat_statements
WHERE query LIKE '%tenant_%' 
  AND query ~ 'tenant_[a-z]+\..*tenant_[a-z]+'  -- Cross-schema pattern
ORDER BY calls DESC;
```

## Troubleshooting

### Issue: Schema not created

**Symptom:** Error "schema does not exist"

**Solution:**
```sql
-- Check if user has CREATE SCHEMA permission
SELECT has_database_privilege('app_user', 'knowledge_graph', 'CREATE');

-- If false, grant permission
GRANT CREATE ON DATABASE knowledge_graph TO app_user;
```

### Issue: Wrong search_path

**Symptom:** Queries see no data or wrong tenant data

**Solution:**
```sql
-- Check current search_path
SHOW search_path;

-- Set correct path
SET search_path = tenant_acme, public;

-- Verify
SELECT current_schema();  -- Should be tenant_acme
```

### Issue: Performance degradation

**Symptom:** Queries slower than SHARED_SCHEMA

**Solution:**
- Check if indexes exist in tenant schema
- Verify statistics are up to date: `ANALYZE tenant_acme.graph_entities`
- Check connection pool configuration

### Issue: Disk space exhausted

**Symptom:** Cannot create new tenant schemas

**Solution:**
```sql
-- Check disk usage per tenant
SELECT 
    schema_name,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))) as size
FROM pg_tables 
WHERE schemaname LIKE 'tenant_%'
GROUP BY schema_name
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;

-- Clean up inactive tenants or increase disk space
```

## Best Practices

1. **Schema Naming Convention**: Use consistent prefix (`tenant_`) for easy management
2. **Automated Creation**: Create schemas automatically on first access
3. **Template Schema**: Maintain template for consistency
4. **Backup Strategy**: Regular per-tenant backups for easy restoration
5. **Monitoring**: Track schema sizes and growth rates
6. **Cleanup Policy**: Archive/delete inactive tenant schemas
7. **Access Control**: Use schema-level permissions for strongest isolation

## Comparison: SHARED_SCHEMA vs SEPARATE_SCHEMA

| Aspect | SHARED_SCHEMA + RLS | SEPARATE_SCHEMA |
|--------|---------------------|-----------------|
| **Isolation** | Application + RLS | Database-level |
| **Performance** | 5-15% RLS overhead | No overhead |
| **Scalability** | 1000s of tenants | 10s-100s of tenants |
| **Management** | Simple (one schema) | Complex (many schemas) |
| **Backup** | Full database | Per-tenant backups |
| **Customization** | Same schema for all | Per-tenant schemas |
| **Cost** | Lower storage | Higher storage |

## Additional Resources

- [PostgreSQL Schema Documentation](https://www.postgresql.org/docs/current/ddl-schemas.html)
- [Multi-Tenancy Setup Guide](./MULTI_TENANCY_GUIDE.md)
- [RLS Setup Guide](./MULTI_TENANCY_RLS_SETUP.md)
- [Migration Guide](./MULTI_TENANCY_MIGRATION.md)
- [Troubleshooting Guide](./MULTI_TENANCY_TROUBLESHOOTING.md)

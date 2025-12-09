# Multi-Tenancy Migration Scripts

This directory contains SQL migration scripts for adding multi-tenancy support to existing Knowledge Graph deployments.

## Script Overview

| Script | Description | Downtime | Rollback |
|--------|-------------|----------|----------|
| `001_add_tenant_id_column.sql` | Add tenant_id columns | No | `rollback_001_remove_tenant_id.sql` |
| `002_backfill_tenant_id.sql` | Backfill existing data | No | `rollback_002_reset_tenant_id.sql` |
| `003_create_tenant_indexes.sql` | Create performance indexes | No | `rollback_003_drop_tenant_indexes.sql` |
| `004_enable_rls_policies.sql` | Enable RLS (optional) | No | `rollback_004_disable_rls.sql` |

## Execution Order

Run scripts in numerical order:

```bash
# PostgreSQL
psql -U postgres -d knowledge_graph -f 001_add_tenant_id_column.sql
psql -U postgres -d knowledge_graph -f 002_backfill_tenant_id.sql
psql -U postgres -d knowledge_graph -f 003_create_tenant_indexes.sql
psql -U postgres -d knowledge_graph -f 004_enable_rls_policies.sql  # Optional
```

## Pre-Migration Checklist

- [ ] Backup database: `pg_dump knowledge_graph > backup.sql`
- [ ] Test on staging environment first
- [ ] Review and adjust tenant_id in backfill script (`legacy_default` vs `default`)
- [ ] Verify disk space for indexes
- [ ] Schedule migration during low-traffic period (for large databases)

## Safety Features

- All scripts use `IF NOT EXISTS` / `IF EXISTS` for idempotence
- Script 003 uses `CREATE INDEX CONCURRENTLY` (no table locks)
- Scripts include verification queries
- Each script has corresponding rollback script

## Rollback

To rollback, run rollback scripts in reverse order:

```bash
psql -U postgres -d knowledge_graph -f rollback_004_disable_rls.sql
psql -U postgres -d knowledge_graph -f rollback_003_drop_tenant_indexes.sql
psql -U postgres -d knowledge_graph -f rollback_002_reset_tenant_id.sql
psql -U postgres -d knowledge_graph -f rollback_001_remove_tenant_id.sql
```

Or restore from backup:

```bash
pg_restore -U postgres -d knowledge_graph -c backup.sql
```

## Monitoring Progress

### Check Index Creation Progress

```sql
SELECT 
    now()::time(0),
    query,
    state,
    wait_event_type,
    wait_event
FROM pg_stat_activity 
WHERE query LIKE '%CREATE INDEX%';
```

### Check Table Sizes

```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename IN ('graph_entities', 'graph_relations');
```

### Verify Migration Status

```sql
-- Check if tenant_id columns exist
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name IN ('graph_entities', 'graph_relations')
  AND column_name = 'tenant_id';

-- Check tenant distribution
SELECT tenant_id, COUNT(*) 
FROM graph_entities 
GROUP BY tenant_id;

-- Check if indexes exist
SELECT indexname FROM pg_indexes 
WHERE indexname LIKE '%tenant%';

-- Check if RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE tablename IN ('graph_entities', 'graph_relations');
```

## Troubleshooting

### Script Fails with "column already exists"

The scripts are idempotent - this message means the migration was already run. Verify with:

```sql
\d graph_entities
```

### Index creation is slow

Index creation time depends on table size. For very large tables (>10M rows), consider:

- Running during maintenance window
- Increasing `maintenance_work_mem`:
  ```sql
  SET maintenance_work_mem = '2GB';
  ```

### RLS causes performance issues

If RLS adds unacceptable overhead, disable it and rely on application-level filtering:

```bash
psql -U postgres -d knowledge_graph -f rollback_004_disable_rls.sql
```

Or switch to SEPARATE_SCHEMA mode for better performance.

## Support

For detailed documentation:
- [Migration Guide](../../../../docs/user/knowledge_graph/deployment/MULTI_TENANCY_MIGRATION.md)
- [Setup Guide](../../../../docs/user/knowledge_graph/deployment/MULTI_TENANCY_GUIDE.md)
- [Troubleshooting](../../../../docs/user/knowledge_graph/deployment/MULTI_TENANCY_TROUBLESHOOTING.md)

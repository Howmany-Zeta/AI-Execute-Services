-- Rollback: Drop tenant indexes
-- Description: Removes indexes created for multi-tenant queries
-- Database: PostgreSQL

-- Drop indexes (CONCURRENTLY to avoid locks)
DROP INDEX CONCURRENTLY IF EXISTS idx_entities_tenant;
DROP INDEX CONCURRENTLY IF EXISTS idx_entities_tenant_type;
DROP INDEX CONCURRENTLY IF EXISTS idx_relations_tenant;
DROP INDEX CONCURRENTLY IF EXISTS idx_relations_tenant_source;
DROP INDEX CONCURRENTLY IF EXISTS idx_relations_tenant_target;

-- Verify indexes removed
SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes 
WHERE tablename IN ('graph_entities', 'graph_relations')
  AND indexname LIKE '%tenant%';

-- Should return no rows if successful

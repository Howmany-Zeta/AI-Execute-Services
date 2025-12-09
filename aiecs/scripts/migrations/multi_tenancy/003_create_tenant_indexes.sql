-- Migration: Create indexes for tenant-scoped queries
-- Description: Adds indexes to optimize multi-tenant query performance
-- Database: PostgreSQL
-- Safe to run: Yes (uses CREATE INDEX CONCURRENTLY - no table locks)
-- Rollback: See rollback_003_drop_tenant_indexes.sql

-- Note: CREATE INDEX CONCURRENTLY cannot run inside a transaction block
-- Run this script outside of BEGIN/COMMIT

-- Index on tenant_id for entities
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_tenant 
    ON graph_entities(tenant_id);

-- Composite index on (tenant_id, entity_type) for filtered type queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_entities_tenant_type 
    ON graph_entities(tenant_id, entity_type);

-- Index on tenant_id for relations
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant 
    ON graph_relations(tenant_id);

-- Composite index on (tenant_id, source_id) for outgoing relation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant_source 
    ON graph_relations(tenant_id, source_id);

-- Composite index on (tenant_id, target_id) for incoming relation queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_relations_tenant_target 
    ON graph_relations(tenant_id, target_id);

-- Verify all indexes were created
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename IN ('graph_entities', 'graph_relations')
  AND indexname LIKE '%tenant%'
ORDER BY tablename, indexname;

-- Check index sizes
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%tenant%'
ORDER BY tablename, indexrelname;

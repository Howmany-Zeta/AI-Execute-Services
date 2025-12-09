-- Migration: Enable Row-Level Security (RLS) policies
-- Description: Enables RLS for defense-in-depth tenant isolation
-- Database: PostgreSQL
-- Safe to run: Yes (but may affect query performance - test first)
-- Rollback: See rollback_004_disable_rls.sql

-- Enable Row-Level Security on entities table
ALTER TABLE graph_entities ENABLE ROW LEVEL SECURITY;

-- Force RLS even for table owners (important for superuser connections)
ALTER TABLE graph_entities FORCE ROW LEVEL SECURITY;

-- Enable Row-Level Security on relations table
ALTER TABLE graph_relations ENABLE ROW LEVEL SECURITY;

-- Force RLS for relations
ALTER TABLE graph_relations FORCE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;

-- Create RLS policy for entities
-- Uses session variable 'app.current_tenant_id' to filter rows
-- Empty string matches rows without tenant context (backward compatible)
CREATE POLICY tenant_isolation_entities ON graph_entities
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            ''
        )
    );

-- Create RLS policy for relations
CREATE POLICY tenant_isolation_relations ON graph_relations
    USING (
        tenant_id = COALESCE(
            current_setting('app.current_tenant_id', true),
            ''
        )
    );

-- Verify RLS is enabled
SELECT 
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables 
WHERE tablename IN ('graph_entities', 'graph_relations');

-- Verify policies were created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename IN ('graph_entities', 'graph_relations')
ORDER BY tablename, policyname;

-- Test RLS enforcement
DO $$
DECLARE
    count_with_tenant INTEGER;
    count_without_tenant INTEGER;
BEGIN
    -- Set tenant context
    PERFORM set_config('app.current_tenant_id', 'legacy_default', false);
    SELECT COUNT(*) INTO count_with_tenant FROM graph_entities;
    
    -- Reset tenant context
    PERFORM set_config('app.current_tenant_id', '', false);
    
    RAISE NOTICE '✓ RLS policies created and active';
    RAISE NOTICE '  Entities visible with tenant context: %', count_with_tenant;
END $$;

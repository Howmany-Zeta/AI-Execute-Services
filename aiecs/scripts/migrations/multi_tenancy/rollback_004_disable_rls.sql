-- Rollback: Disable Row-Level Security
-- Description: Removes RLS policies and disables RLS
-- Database: PostgreSQL

-- Drop RLS policies
DROP POLICY IF EXISTS tenant_isolation_entities ON graph_entities;
DROP POLICY IF EXISTS tenant_isolation_relations ON graph_relations;

-- Disable Row-Level Security
ALTER TABLE graph_entities DISABLE ROW LEVEL SECURITY;
ALTER TABLE graph_relations DISABLE ROW LEVEL SECURITY;

-- Remove FORCE RLS
ALTER TABLE graph_entities NO FORCE ROW LEVEL SECURITY;
ALTER TABLE graph_relations NO FORCE ROW LEVEL SECURITY;

-- Verify RLS is disabled
SELECT 
    schemaname,
    tablename,
    rowsecurity AS rls_enabled
FROM pg_tables 
WHERE tablename IN ('graph_entities', 'graph_relations');

-- Verify policies are removed
SELECT 
    tablename,
    policyname
FROM pg_policies
WHERE tablename IN ('graph_entities', 'graph_relations');

-- Both queries should show RLS disabled and no policies

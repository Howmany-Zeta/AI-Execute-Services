-- Rollback: Remove tenant_id columns
-- Description: Removes tenant_id columns from graph tables
-- Database: PostgreSQL
-- ⚠️ WARNING: This will delete tenant isolation data!

-- Remove tenant_id column from entities
ALTER TABLE graph_entities DROP COLUMN IF EXISTS tenant_id;

-- Remove tenant_id column from relations
ALTER TABLE graph_relations DROP COLUMN IF EXISTS tenant_id;

-- Verify columns removed
SELECT 
    table_name,
    column_name
FROM information_schema.columns 
WHERE table_name IN ('graph_entities', 'graph_relations')
  AND column_name = 'tenant_id';

-- Should return no rows if successful

-- Rollback: Reset tenant_id to empty string
-- Description: Resets all tenant_id values to empty string (default)
-- Database: PostgreSQL

-- Reset entities to empty string
UPDATE graph_entities SET tenant_id = '';

-- Reset relations to empty string
UPDATE graph_relations SET tenant_id = '';

-- Verify reset
SELECT 
    'graph_entities' as table_name,
    tenant_id,
    COUNT(*) as count
FROM graph_entities
GROUP BY tenant_id
UNION ALL
SELECT 
    'graph_relations' as table_name,
    tenant_id,
    COUNT(*) as count
FROM graph_relations
GROUP BY tenant_id
ORDER BY table_name, tenant_id;

-- Should show all rows with tenant_id = ''

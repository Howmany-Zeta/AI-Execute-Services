-- Migration: Backfill tenant_id for existing data
-- Description: Assigns all existing entities/relations to 'legacy_default' tenant
-- Database: PostgreSQL
-- Safe to run: Yes (uses WHERE clause to only update empty tenant_ids)
-- Rollback: See rollback_002_reset_tenant_id.sql

-- Show current state before backfill
DO $$
DECLARE
    empty_entities INTEGER;
    empty_relations INTEGER;
BEGIN
    SELECT COUNT(*) INTO empty_entities FROM graph_entities WHERE tenant_id = '';
    SELECT COUNT(*) INTO empty_relations FROM graph_relations WHERE tenant_id = '';
    
    RAISE NOTICE 'Entities with empty tenant_id: %', empty_entities;
    RAISE NOTICE 'Relations with empty tenant_id: %', empty_relations;
END $$;

-- Backfill entities
UPDATE graph_entities 
SET tenant_id = 'legacy_default' 
WHERE tenant_id = '';

-- Backfill relations
UPDATE graph_relations 
SET tenant_id = 'legacy_default' 
WHERE tenant_id = '';

-- Show results after backfill
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

-- Verify no empty tenant_ids remain
DO $$
DECLARE
    empty_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO empty_count 
    FROM (
        SELECT 1 FROM graph_entities WHERE tenant_id = ''
        UNION ALL
        SELECT 1 FROM graph_relations WHERE tenant_id = ''
    ) sub;
    
    IF empty_count > 0 THEN
        RAISE WARNING 'Found % rows with empty tenant_id', empty_count;
    ELSE
        RAISE NOTICE '✓ All rows have tenant_id assigned';
    END IF;
END $$;

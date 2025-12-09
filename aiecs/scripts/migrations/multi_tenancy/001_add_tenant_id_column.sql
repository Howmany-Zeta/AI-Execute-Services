-- Migration: Add tenant_id columns to graph tables
-- Description: Adds tenant_id column with empty string default for backward compatibility
-- Database: PostgreSQL
-- Safe to run: Yes (uses ALTER TABLE ADD COLUMN IF NOT EXISTS)
-- Rollback: See rollback_001_remove_tenant_id.sql

-- Add tenant_id column to entities table
-- Uses empty string '' as default for backward compatibility with existing data
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'graph_entities' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE graph_entities 
        ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
        
        RAISE NOTICE 'Added tenant_id column to graph_entities';
    ELSE
        RAISE NOTICE 'tenant_id column already exists in graph_entities';
    END IF;
END $$;

-- Add tenant_id column to relations table
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'graph_relations' AND column_name = 'tenant_id'
    ) THEN
        ALTER TABLE graph_relations 
        ADD COLUMN tenant_id TEXT NOT NULL DEFAULT '';
        
        RAISE NOTICE 'Added tenant_id column to graph_relations';
    ELSE
        RAISE NOTICE 'tenant_id column already exists in graph_relations';
    END IF;
END $$;

-- Verify columns were added
SELECT 
    table_name,
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('graph_entities', 'graph_relations') 
  AND column_name = 'tenant_id';

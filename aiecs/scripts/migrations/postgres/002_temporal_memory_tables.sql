-- L1 Temporal Memory — Postgres backend (Phase 5, TM-088)
-- Apply: psql "$TM_POSTGRES_URL" -f aiecs/scripts/migrations/postgres/002_temporal_memory_tables.sql

CREATE TABLE IF NOT EXISTS tm_episode (
    episode_id UUID PRIMARY KEY,
    group_id VARCHAR(256) NOT NULL,
    name VARCHAR(512) NOT NULL,
    body_redacted TEXT NOT NULL,
    source VARCHAR(32) NOT NULL,
    reference_time TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tm_episode_group_id ON tm_episode (group_id);

CREATE TABLE IF NOT EXISTS tm_fact (
    fact_id UUID PRIMARY KEY,
    group_id VARCHAR(256) NOT NULL,
    text TEXT NOT NULL,
    valid_at TIMESTAMPTZ,
    invalid_at TIMESTAMPTZ,
    confidence REAL,
    source_episode_id UUID REFERENCES tm_episode (episode_id),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_tm_fact_group_valid ON tm_fact (group_id, valid_at);

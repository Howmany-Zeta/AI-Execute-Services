-- PostgreSQL schema for ContextEngine permanent storage (dual-write with Redis)
-- Run: psql -U postgres -d your_db -f 001_context_permanent_tables.sql
-- Or use PostgresPermanentBackend with auto_create_tables=True (default)

CREATE TABLE IF NOT EXISTS context_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_sessions_session_created
    ON context_sessions (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_conversations_session_created
    ON context_conversations (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_task_contexts (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    context_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_task_contexts_session_created
    ON context_task_contexts (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_checkpoints (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_checkpoints_thread_created
    ON context_checkpoints (thread_id, created_at);

CREATE TABLE IF NOT EXISTS context_checkpoint_writes (
    id BIGSERIAL PRIMARY KEY,
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    writes_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_checkpoint_writes_thread_created
    ON context_checkpoint_writes (thread_id, created_at);

CREATE TABLE IF NOT EXISTS context_conversation_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_key TEXT NOT NULL,
    session_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_conversation_sessions_key_created
    ON context_conversation_sessions (session_key, created_at);

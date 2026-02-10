-- ClickHouse schema for ContextEngine permanent storage (dual-write with Redis)
-- Run: clickhouse-client --multiquery < 001_context_tables.sql
-- Or use ClickHousePermanentBackend.ensure_tables() which runs these automatically

CREATE TABLE IF NOT EXISTS context_sessions (
    session_id String,
    user_id String,
    event_type LowCardinality(String),
    payload String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_conversations (
    session_id String,
    role LowCardinality(String),
    content String,
    metadata String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_task_contexts (
    session_id String,
    context_data String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (session_id, created_at);

CREATE TABLE IF NOT EXISTS context_checkpoints (
    thread_id String,
    checkpoint_id String,
    data String,
    metadata String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (thread_id, created_at);

CREATE TABLE IF NOT EXISTS context_checkpoint_writes (
    thread_id String,
    checkpoint_id String,
    task_id String,
    writes_data String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (thread_id, created_at);

CREATE TABLE IF NOT EXISTS context_conversation_sessions (
    session_key String,
    session_data String,
    created_at DateTime64(3)
) ENGINE = MergeTree()
ORDER BY (session_key, created_at);

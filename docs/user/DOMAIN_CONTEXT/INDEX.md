# DOMAIN_CONTEXT Documentation Index

ContextEngine and conversation model documentation for the AIECS context management domain.

## Documents

| Document | Description |
|----------|-------------|
| [CONTENT_ENGINE.md](./CONTENT_ENGINE.md) | ContextEngine technical documentation - session management, conversation history, checkpoints, Redis/ClickHouse dual-write |
| [CONVERSATION_MODELS.md](./CONVERSATION_MODELS.md) | Conversation models - ConversationParticipant, ConversationSession, AgentCommunicationMessage |

## Quick Reference

### ContextEngine Initialization

```python
# Application-wide (recommended)
from aiecs.infrastructure.persistence import (
    initialize_redis_client,
    initialize_context_engine,
    get_context_engine,
)
await initialize_redis_client()
await initialize_context_engine()
engine = get_context_engine()
```

### Direct Instantiation

```python
from aiecs.domain.context import ContextEngine

engine = ContextEngine()
await engine.initialize()
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `CLICKHOUSE_ENABLED` | Enable dual-write to ClickHouse (true/false) |
| `CLICKHOUSE_HOST`, `CLICKHOUSE_PORT`, etc. | ClickHouse connection |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` | Redis connection |

## Related

- [ContextEngine Integration](../DOMAIN_AGENT/CONTEXTENGINE_INTEGRATION.md) - Agent integration patterns
- [Storage Interfaces](../CORE/STORAGE_INTERFACES.md) - IStorageBackend, IPermanentStorageBackend

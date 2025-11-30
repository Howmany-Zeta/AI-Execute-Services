# ContextEngine Integration Patterns

This guide covers comprehensive patterns for integrating ContextEngine with AIECS agents for persistent conversation history, session management, and context storage.

## Table of Contents

1. [Overview](#overview)
2. [Basic Integration](#basic-integration)
3. [Session Management Patterns](#session-management-patterns)
4. [Conversation History Patterns](#conversation-history-patterns)
5. [Context Storage Patterns](#context-storage-patterns)
6. [Multi-Agent Patterns](#multi-agent-patterns)
7. [Production Patterns](#production-patterns)
8. [Best Practices](#best-practices)

## Overview

ContextEngine provides persistent storage and management for:
- **Conversation History**: Multi-turn conversations that persist across agent restarts
- **Session Management**: Track user sessions with metrics and lifecycle
- **Context Storage**: Store and retrieve arbitrary context data
- **Compression**: Automatic conversation compression to manage token limits

### Key Benefits

- ✅ **Persistence**: Conversations survive agent restarts
- ✅ **Scalability**: Redis backend for distributed systems
- ✅ **Session Tracking**: Monitor user sessions with metrics
- ✅ **Context Management**: Store and retrieve context data
- ✅ **Compression**: Automatic conversation compression

## Basic Integration

### Pattern 1: Simple Agent Integration

Basic integration with ContextEngine for persistent memory.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.domain.context import ContextEngine
from aiecs.llm import OpenAIClient

# Initialize ContextEngine
context_engine = ContextEngine()
await context_engine.initialize()

# Create agent with ContextEngine
agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration(goal="Help users"),
    context_engine=context_engine  # Enable persistent memory
)

await agent.initialize()

# Conversation history persists automatically
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": "user-123"}
)

# Agent restarts...
# Previous conversation still available!
```

### Pattern 2: ContextEngine with Redis

Use Redis backend for distributed systems.

```python
from aiecs.domain.context import ContextEngine
from aiecs.infrastructure.persistence.redis_client import get_redis_client

# Get Redis client
redis_client = await get_redis_client()

# Initialize ContextEngine with Redis
context_engine = ContextEngine(redis_client=redis_client)
await context_engine.initialize()

# Use with agent
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)
```

### Pattern 3: In-Memory Fallback

ContextEngine falls back to in-memory storage if Redis unavailable.

```python
# ContextEngine automatically falls back to memory if Redis unavailable
context_engine = ContextEngine()
await context_engine.initialize()

# Works with or without Redis
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)
```

## Session Management Patterns

### Pattern 1: Session Lifecycle

Complete session lifecycle management.

```python
from aiecs.domain.context import ContextEngine

context_engine = ContextEngine()
await context_engine.initialize()

# Create session
session_metrics = await context_engine.create_session(
    session_id="session-123",
    user_id="user-456",
    metadata={"source": "web", "device": "mobile"}
)

# Update session metrics
await context_engine.update_session(
    session_id="session-123",
    increment_requests=True,
    add_processing_time=1.5,
    mark_error=False
)

# Get session
session = await context_engine.get_session("session-123")
print(f"Requests: {session.request_count}")
print(f"Errors: {session.error_count}")
print(f"Avg time: {session.total_processing_time / session.request_count}s")

# End session
await context_engine.end_session("session-123", status="completed")
```

### Pattern 2: Session Tracking with Agents

Track sessions automatically with agent execution.

```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Agent automatically tracks sessions
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": "user-123"}  # Session tracked automatically
)

# Get session metrics
session = await context_engine.get_session("user-123")
print(f"Session requests: {session.request_count}")
```

### Pattern 3: Session Cleanup

Clean up inactive sessions automatically.

```python
# Clean up sessions inactive for more than 30 minutes
cleaned_count = await context_engine.cleanup_inactive_sessions(
    max_idle_seconds=1800
)

print(f"Cleaned up {cleaned_count} inactive sessions")
```

### Pattern 4: Session Metrics Aggregation

Aggregate metrics across multiple sessions.

```python
# Get all active sessions
active_sessions = await context_engine.list_sessions(status="active")

# Aggregate metrics
total_requests = sum(s.request_count for s in active_sessions)
total_errors = sum(s.error_count for s in active_sessions)
total_time = sum(s.total_processing_time for s in active_sessions)

print(f"Total requests: {total_requests}")
print(f"Total errors: {total_errors}")
print(f"Average time: {total_time / total_requests}s")
```

## Conversation History Patterns

### Pattern 1: Persistent Conversation History

Conversations persist across agent restarts.

```python
# First run: Create conversation
context_engine = ContextEngine()
await context_engine.initialize()

agent1 = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

await agent1.initialize()

# Add conversation
result1 = await agent1.execute_task(
    {"description": "What's the weather?"},
    {"session_id": "user-123"}
)

result2 = await agent1.execute_task(
    {"description": "What about tomorrow?"},
    {"session_id": "user-123"}
)

# Agent restarts...

# Second run: Conversation persists!
agent2 = HybridAgent(
    agent_id="agent-1",  # Same agent ID
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

await agent2.initialize()

# Previous conversation still available!
result3 = await agent2.execute_task(
    {"description": "What did I ask about?"},
    {"session_id": "user-123"}  # Same session ID
)
# Agent remembers previous conversation!
```

### Pattern 2: Conversation History Retrieval

Retrieve and format conversation history.

```python
# Get conversation history
history = await context_engine.get_conversation_history(
    session_id="user-123",
    limit=50  # Last 50 messages
)

# Format for LLM prompts
formatted = await context_engine.format_conversation_history(
    session_id="user-123",
    format="messages"  # or "string", "dict"
)

# Use in agent
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Agent automatically uses conversation history
result = await agent.execute_task(
    {"description": "Continue conversation"},
    {"session_id": "user-123"}
)
```

### Pattern 3: Conversation History with Compression

Use compression to manage long conversations.

```python
from aiecs.domain.context import CompressionConfig

# Configure compression
compression_config = CompressionConfig(
    strategy="summarize",
    keep_recent=10,
    auto_compress_enabled=True,
    auto_compress_threshold=50
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()

# Compression happens automatically when threshold exceeded
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Long conversation automatically compressed
for i in range(60):
    result = await agent.execute_task(
        {"description": f"Message {i}"},
        {"session_id": "user-123"}
    )
    # Compression triggered at 50 messages
```

## Context Storage Patterns

### Pattern 1: Store and Retrieve Context

Store arbitrary context data.

```python
# Store context
await context_engine.set_context(
    session_id="user-123",
    key="user_preferences",
    value={"theme": "dark", "language": "en"}
)

# Retrieve context
preferences = await context_engine.get_context(
    session_id="user-123",
    key="user_preferences"
)

# Use in agent
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

# Agent can access context
result = await agent.execute_task(
    {"description": "What are my preferences?"},
    {"session_id": "user-123"}
)
```

### Pattern 2: Context Updates

Update context incrementally.

```python
# Set initial context
await context_engine.set_context(
    session_id="user-123",
    key="shopping_cart",
    value={"items": [], "total": 0}
)

# Update context
cart = await context_engine.get_context(
    session_id="user-123",
    key="shopping_cart"
)
cart["items"].append("product-1")
cart["total"] += 10.99

await context_engine.set_context(
    session_id="user-123",
    key="shopping_cart",
    value=cart
)
```

### Pattern 3: Context Listing

List all context keys for a session.

```python
# List all context keys
keys = await context_engine.list_contexts(
    session_id="user-123",
    limit=100
)

# Retrieve multiple contexts
contexts = {}
for key in keys:
    contexts[key] = await context_engine.get_context(
        session_id="user-123",
        key=key
    )
```

## Multi-Agent Patterns

### Pattern 1: Shared ContextEngine

Multiple agents share the same ContextEngine.

```python
context_engine = ContextEngine()
await context_engine.initialize()

# Create multiple agents sharing ContextEngine
agent1 = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client1,
    tools=["search"],
    config=config1,
    context_engine=context_engine  # Shared
)

agent2 = HybridAgent(
    agent_id="agent-2",
    llm_client=llm_client2,
    tools=["calculator"],
    config=config2,
    context_engine=context_engine  # Shared
)

# Both agents share conversation history
result1 = await agent1.execute_task(
    {"description": "Hello"},
    {"session_id": "user-123"}
)

result2 = await agent2.execute_task(
    {"description": "What did I say?"},
    {"session_id": "user-123"}  # Same session
)
# Agent2 can see conversation from agent1!
```

### Pattern 2: Agent-Specific Context

Each agent has its own ContextEngine instance.

```python
# Separate ContextEngine for each agent
context_engine1 = ContextEngine()
await context_engine1.initialize()

context_engine2 = ContextEngine()
await context_engine2.initialize()

agent1 = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client1,
    tools=["search"],
    config=config1,
    context_engine=context_engine1  # Separate
)

agent2 = HybridAgent(
    agent_id="agent-2",
    llm_client=llm_client2,
    tools=["calculator"],
    config=config2,
    context_engine=context_engine2  # Separate
)

# Each agent has isolated conversation history
```

## Production Patterns

### Pattern 1: Redis Configuration

Configure Redis for production.

```python
from aiecs.infrastructure.persistence.redis_client import get_redis_client

# Get Redis client with configuration
redis_client = await get_redis_client(
    host="redis.example.com",
    port=6379,
    db=0,
    password="your-password",
    ssl=True
)

context_engine = ContextEngine(redis_client=redis_client)
await context_engine.initialize()

# Use with agent
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)
```

### Pattern 2: Compression Configuration

Configure compression for production.

```python
from aiecs.domain.context import CompressionConfig

# Production compression config
compression_config = CompressionConfig(
    strategy="hybrid",
    hybrid_strategies=["truncate", "summarize"],
    keep_recent=20,
    auto_compress_enabled=True,
    auto_compress_threshold=100,
    auto_compress_target=50,
    summary_max_tokens=500,
    compression_timeout=30
)

context_engine = ContextEngine(compression_config=compression_config)
await context_engine.initialize()
```

### Pattern 3: Error Handling

Handle ContextEngine errors gracefully.

```python
try:
    context_engine = ContextEngine()
    await context_engine.initialize()
except Exception as e:
    logger.error(f"Failed to initialize ContextEngine: {e}")
    # Fall back to in-memory mode
    context_engine = None

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine  # None = in-memory fallback
)

# Agent works with or without ContextEngine
```

### Pattern 4: Monitoring

Monitor ContextEngine health and metrics.

```python
# Get global metrics
metrics = context_engine.get_global_metrics()

print(f"Total sessions: {metrics['total_sessions']}")
print(f"Active sessions: {metrics['active_sessions']}")
print(f"Total messages: {metrics['total_messages']}")
print(f"Total context operations: {metrics['total_context_operations']}")

# Monitor session health
active_sessions = await context_engine.list_sessions(status="active")
for session in active_sessions:
    if session.error_count > 10:
        logger.warning(f"Session {session.session_id} has high error count")
```

## Best Practices

### 1. Always Initialize ContextEngine

Always call `initialize()` before use:

```python
context_engine = ContextEngine()
await context_engine.initialize()  # Don't forget this!
```

### 2. Use Consistent Session IDs

Use consistent session IDs across requests:

```python
# Good: Consistent session ID
session_id = f"user-{user_id}"

# Bad: Random session IDs
session_id = str(uuid.uuid4())  # Don't do this!
```

### 3. Clean Up Inactive Sessions

Regularly clean up inactive sessions:

```python
# Clean up sessions inactive for 30 minutes
await context_engine.cleanup_inactive_sessions(max_idle_seconds=1800)
```

### 4. Configure Compression

Configure compression for long conversations:

```python
compression_config = CompressionConfig(
    auto_compress_enabled=True,
    auto_compress_threshold=50
)
```

### 5. Handle Errors Gracefully

Always handle ContextEngine errors:

```python
try:
    await context_engine.add_conversation_message(...)
except Exception as e:
    logger.error(f"Failed to add message: {e}")
    # Fall back to in-memory or retry
```

### 6. Monitor Performance

Monitor ContextEngine performance:

```python
# Track operation times
start = time.time()
await context_engine.get_conversation_history(...)
duration = time.time() - start

if duration > 1.0:
    logger.warning(f"Slow ContextEngine operation: {duration}s")
```

### 7. Use Redis for Production

Use Redis backend for production deployments:

```python
# Production: Use Redis
redis_client = await get_redis_client()
context_engine = ContextEngine(redis_client=redis_client)

# Development: Can use in-memory
context_engine = ContextEngine()  # Falls back to memory
```

## Summary

ContextEngine integration provides:
- ✅ Persistent conversation history
- ✅ Session management with metrics
- ✅ Context storage and retrieval
- ✅ Automatic compression
- ✅ Redis backend for scalability
- ✅ Graceful fallback to in-memory

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Compression Strategies](./COMPRESSION_GUIDE.md)
- [Session Management](./SESSION_MANAGEMENT.md)


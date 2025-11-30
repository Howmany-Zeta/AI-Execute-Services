# Session Management Best Practices

This guide covers best practices for managing conversation sessions with AIECS agents, including lifecycle management, metrics tracking, cleanup strategies, and production patterns.

## Table of Contents

1. [Overview](#overview)
2. [Session Lifecycle](#session-lifecycle)
3. [Session Identification](#session-identification)
4. [Metrics Tracking](#metrics-tracking)
5. [Session Cleanup](#session-cleanup)
6. [Error Handling](#error-handling)
7. [Production Patterns](#production-patterns)
8. [Best Practices](#best-practices)

## Overview

Sessions provide:
- **Conversation Isolation**: Each user gets their own conversation history
- **Lifecycle Management**: Track session states (active, completed, failed, expired)
- **Metrics Tracking**: Monitor request count, errors, processing time
- **Automatic Cleanup**: Remove inactive sessions automatically

### Session States

- **active**: Session is active and receiving requests
- **completed**: Session ended successfully
- **failed**: Session ended due to error
- **expired**: Session expired due to inactivity

## Session Lifecycle

### Pattern 1: Basic Lifecycle

Standard session lifecycle management.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.domain.context import ContextEngine
from aiecs.llm import OpenAIClient

context_engine = ContextEngine()
await context_engine.initialize()

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration(),
    context_engine=context_engine
)

await agent.initialize()

# 1. Create session (automatic on first request)
session_id = "user-123"
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session_id}
)
# Session created automatically if doesn't exist

# 2. Use session for multiple requests
for i in range(5):
    result = await agent.execute_task(
        {"description": f"Request {i}"},
        {"session_id": session_id}
    )
    # All requests tracked in same session

# 3. End session explicitly
await context_engine.end_session(session_id, status="completed")
```

### Pattern 2: Explicit Session Creation

Create sessions explicitly for better control.

```python
# Create session explicitly
session_metrics = await context_engine.create_session(
    session_id="user-123",
    user_id="user-456",
    metadata={
        "source": "web",
        "device": "mobile",
        "ip_address": "192.168.1.1"
    }
)

# Use session
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine
)

result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": "user-123"}
)

# End session
await context_engine.end_session("user-123", status="completed")
```

### Pattern 3: Session Status Management

Manage session status throughout lifecycle.

```python
# Create session
session = await context_engine.create_session(
    session_id="user-123",
    user_id="user-456"
)

# Check status
assert session.status == "active"

# Process requests
for i in range(10):
    result = await agent.execute_task(
        {"description": f"Request {i}"},
        {"session_id": "user-123"}
    )

# Check if session expired
session = await context_engine.get_session("user-123")
if session.is_expired(max_idle_seconds=1800):
    await context_engine.end_session("user-123", status="expired")

# End session explicitly
await context_engine.end_session("user-123", status="completed")
```

## Session Identification

### Pattern 1: User-Based Sessions

Use user ID as session identifier.

```python
# Good: User-based session ID
user_id = "user-456"
session_id = f"user-{user_id}"

# Use consistent session ID
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session_id}
)
```

### Pattern 2: Device-Based Sessions

Use device ID for multi-device support.

```python
# Device-based session ID
user_id = "user-456"
device_id = "device-789"
session_id = f"user-{user_id}-device-{device_id}"

# Each device gets its own session
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session_id}
)
```

### Pattern 3: Application-Based Sessions

Use application context for session ID.

```python
# Application-based session ID
user_id = "user-456"
app_id = "web-app"
session_id = f"user-{user_id}-app-{app_id}"

# Different apps get different sessions
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": session_id}
)
```

### Pattern 4: Temporary Sessions

Use temporary sessions for one-off interactions.

```python
import uuid

# Temporary session for one-off interaction
temp_session_id = f"temp-{uuid.uuid4()}"

result = await agent.execute_task(
    {"description": "One-time question"},
    {"session_id": temp_session_id}
)

# Clean up temporary session
await context_engine.end_session(temp_session_id, status="completed")
```

## Metrics Tracking

### Pattern 1: Request Tracking

Track requests automatically with agent execution.

```python
# Agent automatically tracks requests
for i in range(10):
    result = await agent.execute_task(
        {"description": f"Request {i}"},
        {"session_id": "user-123"}
    )
    # Each request tracked automatically

# Get session metrics
session = await context_engine.get_session("user-123")
print(f"Request count: {session.request_count}")  # 10
print(f"Error count: {session.error_count}")
print(f"Total processing time: {session.total_processing_time}s")
```

### Pattern 2: Manual Metrics Update

Update metrics manually for custom tracking.

```python
# Update session metrics manually
await context_engine.update_session(
    session_id="user-123",
    increment_requests=True,
    add_processing_time=1.5,
    mark_error=False
)

# Track error
await context_engine.update_session(
    session_id="user-123",
    increment_requests=True,
    add_processing_time=0.1,
    mark_error=True
)

# Get metrics
session = await context_engine.get_session("user-123")
print(f"Requests: {session.request_count}")
print(f"Errors: {session.error_count}")
print(f"Error rate: {session.error_count / session.request_count * 100}%")
```

### Pattern 3: Metrics Aggregation

Aggregate metrics across multiple sessions.

```python
# Get all sessions for a user
all_sessions = await context_engine.list_sessions(user_id="user-456")

# Aggregate metrics
total_requests = sum(s.request_count for s in all_sessions)
total_errors = sum(s.error_count for s in all_sessions)
total_time = sum(s.total_processing_time for s in all_sessions)

print(f"Total requests: {total_requests}")
print(f"Total errors: {total_errors}")
print(f"Average time: {total_time / total_requests}s")
print(f"Error rate: {total_errors / total_requests * 100}%")
```

### Pattern 4: Performance Monitoring

Monitor session performance metrics.

```python
# Track processing time
import time

start = time.time()
result = await agent.execute_task(
    {"description": "Complex task"},
    {"session_id": "user-123"}
)
duration = time.time() - start

# Update metrics with processing time
await context_engine.update_session(
    session_id="user-123",
    increment_requests=True,
    add_processing_time=duration,
    mark_error=False
)

# Get performance metrics
session = await context_engine.get_session("user-123")
avg_time = session.total_processing_time / session.request_count
print(f"Average processing time: {avg_time}s")
```

## Session Cleanup

### Pattern 1: Automatic Cleanup

Use automatic cleanup for inactive sessions.

```python
# Clean up sessions inactive for 30 minutes
cleaned_count = await context_engine.cleanup_inactive_sessions(
    max_idle_seconds=1800
)

print(f"Cleaned up {cleaned_count} inactive sessions")
```

### Pattern 2: Scheduled Cleanup

Schedule cleanup at regular intervals.

```python
import asyncio

async def cleanup_sessions_periodically():
    """Clean up inactive sessions every hour"""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        
        cleaned_count = await context_engine.cleanup_inactive_sessions(
            max_idle_seconds=1800  # 30 minutes
        )
        
        logger.info(f"Cleaned up {cleaned_count} inactive sessions")

# Start cleanup task
asyncio.create_task(cleanup_sessions_periodically())
```

### Pattern 3: Custom Cleanup Logic

Implement custom cleanup logic.

```python
# Get all sessions
all_sessions = await context_engine.list_sessions()

# Custom cleanup: Remove sessions with high error rate
for session in all_sessions:
    if session.request_count > 0:
        error_rate = session.error_count / session.request_count
        if error_rate > 0.5:  # More than 50% errors
            await context_engine.end_session(
                session.session_id,
                status="failed"
            )
            logger.warning(
                f"Ended session {session.session_id} "
                f"due to high error rate: {error_rate}"
            )
```

### Pattern 4: Cleanup by Age

Clean up sessions older than a certain age.

```python
from datetime import datetime, timedelta

# Get all sessions
all_sessions = await context_engine.list_sessions()

# Clean up sessions older than 7 days
cutoff_date = datetime.utcnow() - timedelta(days=7)
cleaned_count = 0

for session in all_sessions:
    if session.created_at < cutoff_date:
        await context_engine.end_session(
            session.session_id,
            status="expired"
        )
        cleaned_count += 1

print(f"Cleaned up {cleaned_count} old sessions")
```

## Error Handling

### Pattern 1: Error Tracking

Track errors in sessions.

```python
try:
    result = await agent.execute_task(
        {"description": "Task"},
        {"session_id": "user-123"}
    )
except Exception as e:
    # Track error in session
    await context_engine.update_session(
        session_id="user-123",
        increment_requests=True,
        add_processing_time=0.1,
        mark_error=True
    )
    logger.error(f"Task failed: {e}")
    raise
```

### Pattern 2: Error Recovery

Recover from errors and continue session.

```python
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        result = await agent.execute_task(
            {"description": "Task"},
            {"session_id": "user-123"}
        )
        break  # Success
    except Exception as e:
        retry_count += 1
        await context_engine.update_session(
            session_id="user-123",
            increment_requests=True,
            mark_error=True
        )
        
        if retry_count >= max_retries:
            # End session on failure
            await context_engine.end_session(
                "user-123",
                status="failed"
            )
            raise
```

### Pattern 3: Session Health Monitoring

Monitor session health and take action.

```python
# Get session
session = await context_engine.get_session("user-123")

# Check health
if session.request_count > 0:
    error_rate = session.error_count / session.request_count
    
    if error_rate > 0.3:  # More than 30% errors
        logger.warning(
            f"Session {session.session_id} has high error rate: {error_rate}"
        )
        
        # Take action: End session or alert
        if error_rate > 0.5:
            await context_engine.end_session(
                session.session_id,
                status="failed"
            )
```

## Production Patterns

### Pattern 1: Session Limits

Enforce session limits to prevent resource exhaustion.

```python
# Check session count before creating new session
active_sessions = await context_engine.list_sessions(status="active")

if len(active_sessions) >= MAX_SESSIONS:
    # Clean up oldest inactive sessions
    await context_engine.cleanup_inactive_sessions(
        max_idle_seconds=900  # 15 minutes
    )
    
    # Check again
    active_sessions = await context_engine.list_sessions(status="active")
    if len(active_sessions) >= MAX_SESSIONS:
        raise Exception("Maximum session limit reached")

# Create session
session = await context_engine.create_session(
    session_id="user-123",
    user_id="user-456"
)
```

### Pattern 2: Session Timeout

Implement session timeout.

```python
# Check if session expired
session = await context_engine.get_session("user-123")

if session and session.is_expired(max_idle_seconds=1800):
    # Session expired, create new session
    await context_engine.end_session("user-123", status="expired")
    session = await context_engine.create_session(
        session_id="user-123-new",
        user_id="user-456"
    )
```

### Pattern 3: Session Pooling

Reuse sessions for better performance.

```python
# Session pool
session_pool = {}

async def get_or_create_session(user_id: str) -> str:
    """Get existing session or create new one"""
    session_id = f"user-{user_id}"
    
    if session_id not in session_pool:
        session = await context_engine.get_session(session_id)
        
        if not session or session.is_expired(max_idle_seconds=1800):
            # Create new session
            session = await context_engine.create_session(
                session_id=session_id,
                user_id=user_id
            )
        
        session_pool[session_id] = session
    
    return session_id

# Use session pool
session_id = await get_or_create_session("user-456")
result = await agent.execute_task(
    {"description": "Task"},
    {"session_id": session_id}
)
```

## Best Practices

### 1. Use Consistent Session IDs

Always use consistent session IDs:

```python
# Good: Consistent session ID
session_id = f"user-{user_id}"

# Bad: Random session IDs
session_id = str(uuid.uuid4())  # Don't do this!
```

### 2. End Sessions Explicitly

Always end sessions when done:

```python
try:
    # Use session
    result = await agent.execute_task(
        {"description": "Task"},
        {"session_id": session_id}
    )
finally:
    # End session
    await context_engine.end_session(session_id, status="completed")
```

### 3. Track Metrics

Track metrics for monitoring:

```python
# Update metrics after each request
await context_engine.update_session(
    session_id=session_id,
    increment_requests=True,
    add_processing_time=duration,
    mark_error=is_error
)
```

### 4. Clean Up Inactive Sessions

Regularly clean up inactive sessions:

```python
# Clean up sessions inactive for 30 minutes
await context_engine.cleanup_inactive_sessions(max_idle_seconds=1800)
```

### 5. Monitor Session Health

Monitor session health and take action:

```python
session = await context_engine.get_session(session_id)
if session.error_count > 10:
    logger.warning(f"Session {session_id} has high error count")
```

### 6. Handle Errors Gracefully

Always handle errors:

```python
try:
    result = await agent.execute_task(
        {"description": "Task"},
        {"session_id": session_id}
    )
except Exception as e:
    # Track error
    await context_engine.update_session(
        session_id=session_id,
        mark_error=True
    )
    # Handle error
    logger.error(f"Task failed: {e}")
```

### 7. Use Appropriate Timeouts

Set appropriate timeouts for sessions:

```python
# Check expiration with appropriate timeout
if session.is_expired(max_idle_seconds=1800):  # 30 minutes
    await context_engine.end_session(session_id, status="expired")
```

## Summary

Session management best practices:
- ✅ Use consistent session IDs
- ✅ Track metrics for monitoring
- ✅ Clean up inactive sessions regularly
- ✅ Monitor session health
- ✅ Handle errors gracefully
- ✅ End sessions explicitly
- ✅ Use appropriate timeouts

For more details, see:
- [ContextEngine Integration](./CONTEXTENGINE_INTEGRATION.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)


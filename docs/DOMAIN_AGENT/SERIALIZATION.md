# Serialization Best Practices

This guide covers best practices for serializing and deserializing agent state, including handling non-serializable objects, state persistence, and checkpointing.

## Table of Contents

1. [Overview](#overview)
2. [Basic Serialization](#basic-serialization)
3. [State Persistence](#state-persistence)
4. [Handling Non-Serializable Objects](#handling-non-serializable-objects)
5. [Checkpointing](#checkpointing)
6. [Best Practices](#best-practices)

## Overview

Agent serialization provides:
- **State Persistence**: Save and restore agent state
- **Checkpointing**: Create checkpoints for recovery
- **State Transfer**: Move agent state between instances
- **Backup and Recovery**: Backup agent state for disaster recovery

### Serialization Features

- Automatic handling of non-serializable objects (Queue, ChainMap, datetime)
- JSON-compatible serialization
- State sanitization for safe storage
- Checkpoint support for LangGraph integration

## Basic Serialization

### Pattern 1: Serialize Agent State

Serialize agent state to JSON.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration()
)

await agent.initialize()

# Serialize agent state
state = agent.serialize_state()

# Save to file
import json
with open("agent_state.json", "w") as f:
    json.dump(state, f, indent=2)
```

### Pattern 2: Deserialize Agent State

Deserialize agent state from JSON.

```python
# Load state from file
with open("agent_state.json", "r") as f:
    state = json.load(f)

# Create new agent instance
agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration()
)

# Deserialize state
agent.deserialize_state(state)
await agent.initialize()

# Agent state restored!
```

### Pattern 3: State Transfer

Transfer state between agent instances.

```python
# Serialize from source agent
source_state = source_agent.serialize_state()

# Deserialize to target agent
target_agent.deserialize_state(source_state)
await target_agent.initialize()

# State transferred!
```

## State Persistence

### Pattern 1: Save State to File

Save agent state to file for persistence.

```python
import json
from pathlib import Path

async def save_agent_state(agent, filepath: str):
    """Save agent state to file"""
    state = agent.serialize_state()
    
    # Ensure directory exists
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Save to file
    with open(filepath, "w") as f:
        json.dump(state, f, indent=2)
    
    logger.info(f"Saved agent state to {filepath}")

async def load_agent_state(agent, filepath: str):
    """Load agent state from file"""
    with open(filepath, "r") as f:
        state = json.load(f)
    
    agent.deserialize_state(state)
    await agent.initialize()
    
    logger.info(f"Loaded agent state from {filepath}")

# Usage
await save_agent_state(agent, "backup/agent_state.json")
await load_agent_state(agent, "backup/agent_state.json")
```

### Pattern 2: Save State to Database

Save agent state to database.

```python
import asyncpg

async def save_state_to_db(agent, db_pool):
    """Save agent state to database"""
    state = agent.serialize_state()
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO agent_states (agent_id, state_data, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (agent_id) DO UPDATE
            SET state_data = $2, updated_at = NOW()
            """,
            agent.agent_id,
            json.dumps(state)
        )

async def load_state_from_db(agent, db_pool):
    """Load agent state from database"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT state_data FROM agent_states WHERE agent_id = $1",
            agent.agent_id
        )
        
        if row:
            state = json.loads(row["state_data"])
            agent.deserialize_state(state)
            await agent.initialize()

# Usage
await save_state_to_db(agent, db_pool)
await load_state_from_db(agent, db_pool)
```

### Pattern 3: Periodic State Backup

Backup agent state periodically.

```python
import asyncio

async def backup_state_periodically(agent, backup_dir: str):
    """Backup agent state every hour"""
    while True:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filepath = f"{backup_dir}/agent_{agent.agent_id}_{timestamp}.json"
        
        await save_agent_state(agent, filepath)
        
        await asyncio.sleep(3600)  # 1 hour

# Start backup
asyncio.create_task(backup_state_periodically(agent, "backups"))
```

## Handling Non-Serializable Objects

### Pattern 1: Automatic Sanitization

Agent automatically handles non-serializable objects.

```python
from collections import ChainMap, deque
from datetime import datetime

# Agent state may contain non-serializable objects
agent._some_queue = deque([1, 2, 3])
agent._some_chainmap = ChainMap({"a": 1}, {"b": 2})
agent._some_datetime = datetime.utcnow()

# Serialization automatically handles these
state = agent.serialize_state()

# Non-serializable objects are converted to serializable format
# Queue -> list
# ChainMap -> dict
# datetime -> ISO string
```

### Pattern 2: Custom Serialization

Implement custom serialization for complex objects.

```python
class CustomSerializable:
    def __init__(self, data):
        self.data = data
    
    def to_dict(self):
        """Convert to dictionary"""
        return {"data": self.data}
    
    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        return cls(data["data"])

# Use custom serializable objects
agent._custom_obj = CustomSerializable({"key": "value"})

# Serialize (custom object converted to dict)
state = agent.serialize_state()

# Deserialize (custom object restored)
agent.deserialize_state(state)
```

### Pattern 3: Exclude Non-Serializable Objects

Exclude objects that can't be serialized.

```python
# Exclude non-serializable objects from serialization
state = agent.serialize_state(exclude=["_llm_client", "_redis_client"])

# These objects won't be serialized
# They'll need to be recreated on deserialization
```

## Checkpointing

### Pattern 1: Basic Checkpointing

Create and restore checkpoints.

```python
# Create checkpoint
checkpoint_id = await agent.save_checkpoint("session-123")

# Restore checkpoint
state = await agent.load_checkpoint("session-123", checkpoint_id)

# Agent state restored to checkpoint
```

### Pattern 2: Checkpoint with Custom Checkpointer

Use custom checkpointer for checkpointing.

```python
from aiecs.domain.agent.integration import CheckpointerProtocol

class RedisCheckpointer:
    async def save_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_data: Dict[str, Any]
    ) -> str:
        checkpoint_id = str(uuid.uuid4())
        await redis.set(
            f"checkpoint:{agent_id}:{session_id}:{checkpoint_id}",
            json.dumps(checkpoint_data)
        )
        return checkpoint_id
    
    async def load_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if checkpoint_id:
            data = await redis.get(
                f"checkpoint:{agent_id}:{session_id}:{checkpoint_id}"
            )
            return json.loads(data) if data else None
        return None

# Use custom checkpointer
checkpointer = RedisCheckpointer()
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    checkpointer=checkpointer
)

# Create checkpoint
checkpoint_id = await agent.save_checkpoint("session-123")

# Restore checkpoint
state = await agent.load_checkpoint("session-123", checkpoint_id)
```

### Pattern 3: LangGraph Integration

Use checkpointing for LangGraph integration.

```python
from langgraph.graph import StateGraph

# Agent checkpointer compatible with LangGraph
checkpointer = agent.get_checkpointer()

# Use with LangGraph
graph = StateGraph(...)
compiled_graph = graph.compile(checkpointer=checkpointer)

# LangGraph uses same checkpoints as agent
```

## Best Practices

### 1. Serialize Regularly

Serialize agent state regularly for persistence:

```python
# Serialize after important operations
result = await agent.execute_task(task, context)
state = agent.serialize_state()
await save_state(state)
```

### 2. Handle Serialization Errors

Always handle serialization errors:

```python
try:
    state = agent.serialize_state()
except Exception as e:
    logger.error(f"Serialization failed: {e}")
    # Fall back to minimal state or retry
```

### 3. Exclude Large Objects

Exclude large objects from serialization:

```python
# Exclude large objects
state = agent.serialize_state(exclude=["_large_cache", "_big_data"])
```

### 4. Validate Deserialized State

Validate deserialized state:

```python
agent.deserialize_state(state)

# Validate state
if agent.agent_id != expected_id:
    raise ValueError("Agent ID mismatch")

if not agent.is_initialized():
    await agent.initialize()
```

### 5. Use Checkpoints for Recovery

Use checkpoints for recovery:

```python
# Create checkpoint before risky operation
checkpoint_id = await agent.save_checkpoint("session-123")

try:
    result = await agent.execute_risky_operation()
except Exception:
    # Restore checkpoint on failure
    await agent.load_checkpoint("session-123", checkpoint_id)
    raise
```

### 6. Backup State Regularly

Backup state regularly:

```python
# Backup every hour
async def backup():
    while True:
        state = agent.serialize_state()
        await save_backup(state)
        await asyncio.sleep(3600)
```

### 7. Compress Large States

Compress large states:

```python
import gzip

# Serialize and compress
state = agent.serialize_state()
compressed = gzip.compress(json.dumps(state).encode())

# Save compressed state
with open("agent_state.json.gz", "wb") as f:
    f.write(compressed)
```

## Summary

Serialization best practices:
- ✅ Serialize regularly for persistence
- ✅ Handle non-serializable objects automatically
- ✅ Use checkpoints for recovery
- ✅ Validate deserialized state
- ✅ Backup state regularly
- ✅ Compress large states
- ✅ Handle errors gracefully

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [State Persistence](./CONTEXTENGINE_INTEGRATION.md)


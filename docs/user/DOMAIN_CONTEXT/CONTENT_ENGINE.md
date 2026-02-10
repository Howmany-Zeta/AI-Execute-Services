# ContextEngine Technical Documentation

## Overview

### Design Motivation and Problem Background

When building large-scale AI application systems, context and session management face the following core challenges:

**1. Multi-Session Management Complexity**
- Need to support concurrent management of multiple user sessions
- Session state needs to maintain consistency across multiple requests
- Lack of unified session lifecycle management mechanism

**2. Conversation History Management Difficulties**
- Large amounts of conversation messages require efficient storage and retrieval
- Conversation context needs to maintain continuity over long periods
- Lack of conversation history optimization and compression mechanisms

**3. Checkpoint and State Persistence**
- Complex workflows need to support checkpoints and state recovery
- State data needs to remain available after system restarts
- Lack of unified checkpoint management mechanism

**4. Performance and Scalability Challenges**
- Large numbers of concurrent sessions require high-performance storage support
- Memory usage needs optimization to avoid resource exhaustion
- Lack of effective caching and cleanup mechanisms

**ContextEngine's Solution**:
- **Unified Session Management**: Provides complete session lifecycle management
- **Multi-Backend Storage Support**: Supports automatic switching between Redis and memory storage
- **Dual-Write Architecture**: Optional ClickHouse for permanent cold storage (Redis hot + ClickHouse cold)
- **Conversation History Optimization**: Intelligent conversation history management and compression
- **Checkpoint Integration**: Deep integration with LangGraph checkpoint system
- **Performance Monitoring**: Provides detailed performance metrics and health checks

### Component Positioning

`context_engine.py` is a core domain service of the AIECS system, located in the Domain Layer, implementing storage interfaces and checkpoint backend interfaces. As the system's context management core, it provides advanced session management, conversation tracking, and persistent storage capabilities.

## Component Type and Positioning

### Component Type
**Domain Service Component** - Located in the Domain Layer, belongs to the business logic layer

### Architecture Layers
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← Components using ContextEngine
│  (BaseAIService, ServiceLayer)          │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← ContextEngine layer
│  (ContextEngine, Business Logic)        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← Components ContextEngine depends on
│  (RedisClient, ClickHousePermanentBackend) │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Services               │  ← External storage systems
│  (Redis, ClickHouse, FileSystem)        │
└─────────────────────────────────────────┘
```

## Upstream Components (Consumers)

### 1. AI Service Layer
- **BaseAIService** (if exists)
- **ServiceLayer** (if exists)
- **AgentService** (if exists)

### 2. Application Layer Services
- **TaskService** (if exists)
- **ExecutionService** (if exists)
- **ConversationService** (if exists)

### 3. Workflow Engine
- **LangGraph Workflows** (via checkpoint interface)
- **BaseServiceCheckpointer** (if exists)
- **Workflow Executors** (if exists)

## Downstream Components (Dependencies)

### 1. Storage Interfaces
- **IStorageBackend** (`core/interface/storage_interface.py`)
- **ICheckpointerBackend** (`core/interface/storage_interface.py`)

### 2. Infrastructure Layer
- **RedisClient** (`infrastructure/persistence/redis_client.py`)
- **ClickHousePermanentBackend** (`infrastructure/persistence/clickhouse_permanent_backend.py`) - Optional dual-write for permanent storage
- **ClickHouseClient** (`infrastructure/persistence/clickhouse_client.py`)
- **ContextEngine Client** (`infrastructure/persistence/context_engine_client.py`) - Global singleton initialization

### 3. Domain Models
- **TaskContext** (`domain/task/task_context.py`)
- **SessionMetrics** (internally defined)
- **ConversationMessage** (internally defined)

### 4. Conversation Models
- **ConversationParticipant** (`domain/context/conversation_models.py`)
- **ConversationSession** (`domain/context/conversation_models.py`)
- **AgentCommunicationMessage** (`domain/context/conversation_models.py`)

## Core Functionality

### 1. Session Management

#### Session Creation and Lifecycle
```python
async def create_session(
    self,
    session_id: str,
    user_id: str,
    metadata: Dict[str, Any] = None
) -> SessionMetrics:
    """Create a new session"""
    now = datetime.utcnow()
    session = SessionMetrics(
        session_id=session_id,
        user_id=user_id,
        created_at=now,
        last_activity=now,
        status="active"
    )
    await self._store_session(session)
    return session
```

**Features**:
- **Unique Session Identifier**: Supports custom or auto-generated session IDs
- **User Association**: Each session is associated with a specific user
- **Metadata Support**: Supports custom session metadata
- **State Tracking**: Real-time tracking of session state and activity

#### Session Updates and Metrics Tracking
```python
async def update_session(
    self,
    session_id: str,
    updates: Dict[str, Any] = None,
    increment_requests: bool = False,
    add_processing_time: float = 0.0,
    mark_error: bool = False
) -> bool:
    """Update session information and metrics"""
    session = await self.get_session(session_id)
    if not session:
        return False
    
    # Update metrics
    if increment_requests:
        session.request_count += 1
    if add_processing_time > 0:
        session.total_processing_time += add_processing_time
    if mark_error:
        session.error_count += 1
    
    session.last_activity = datetime.utcnow()
    await self._store_session(session)
    return True
```

**Features**:
- **Request Counting**: Automatically tracks session request count
- **Processing Time Statistics**: Accumulates session processing time
- **Error Statistics**: Tracks session error count
- **Activity Time Updates**: Automatically updates last activity time

### 2. Conversation History Management

#### Conversation Message Storage
```python
async def add_conversation_message(
    self,
    session_id: str,
    role: str,
    content: str,
    metadata: Dict[str, Any] = None
) -> bool:
    """Add a conversation message"""
    message = ConversationMessage(
        role=role,
        content=content,
        timestamp=datetime.utcnow(),
        metadata=metadata or {}
    )
    await self._store_conversation_message(session_id, message)
    return True
```

**Features**:
- **Structured Messages**: Supports role, content, timestamp, metadata
- **Sequential Storage**: Maintains message chronological order
- **Metadata Support**: Supports message-level custom metadata
- **Automatic Timestamps**: Automatically records message creation time

#### Conversation History Retrieval
```python
async def get_conversation_history(
    self,
    session_id: str,
    limit: int = 50
) -> List[ConversationMessage]:
    """Get conversation history"""
    if self.redis_client:
        # Redis implementation
        key = f"conversation:{session_id}"
        messages_data = await self.redis_client.lrange(key, 0, limit - 1)
        return [ConversationMessage.from_dict(json.loads(msg)) for msg in messages_data]
    else:
        # Memory implementation
        messages = self._memory_conversations.get(session_id, [])
        return messages[-limit:] if limit > 0 else messages
```

**Features**:
- **Pagination Support**: Supports limiting returned message count
- **Sequential Retrieval**: Returns messages in chronological order
- **Multi-Backend Storage**: Supports Redis and memory storage
- **Data Deserialization**: Automatically handles data format conversion

### 3. Task Context Management

#### Context Storage and Retrieval
```python
async def store_task_context(self, session_id: str, context: Any) -> bool:
    """Store task context"""
    if isinstance(context, TaskContext):
        await self._store_task_context(session_id, context)
        return True
    return False

async def get_task_context(self, session_id: str) -> Optional[TaskContext]:
    """Get task context"""
    if self.redis_client:
        # Redis implementation
        key = f"context:{session_id}"
        context_data = await self.redis_client.get(key)
        if context_data:
            return TaskContext.from_dict(json.loads(context_data))
    else:
        # Memory implementation
        return self._memory_contexts.get(session_id)
    return None
```

**Features**:
- **Type Safety**: Supports TaskContext type checking
- **Serialization Support**: Automatically handles context serialization and deserialization
- **Persistent Storage**: Supports persistent context storage
- **Fast Retrieval**: Provides efficient context retrieval

### 4. Checkpoint Management

#### LangGraph Checkpoint Integration
```python
async def store_checkpoint(
    self,
    thread_id: str,
    checkpoint_id: str,
    checkpoint_data: Dict[str, Any],
    metadata: Dict[str, Any] = None
) -> bool:
    """Store checkpoint data"""
    checkpoint_key = f"checkpoint:{thread_id}:{checkpoint_id}"
    checkpoint_info = {
        "checkpoint_id": checkpoint_id,
        "thread_id": thread_id,
        "data": checkpoint_data,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat()
    }
    
    if self.redis_client:
        await self.redis_client.setex(
            checkpoint_key, 
            self.checkpoint_ttl, 
            json.dumps(checkpoint_info)
        )
    else:
        self._memory_checkpoints[checkpoint_key] = checkpoint_info
    
    return True
```

**Features**:
- **LangGraph Compatible**: Fully compatible with LangGraph checkpoint interface
- **Thread Isolation**: Supports checkpoint isolation for multi-threaded workflows
- **Metadata Support**: Supports checkpoint-level metadata
- **TTL Support**: Supports automatic checkpoint expiration

### 5. Multi-Backend Storage Support

#### Storage Backend Automatic Switching
```python
async def initialize(self) -> bool:
    """Initialize storage backend"""
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available, using memory storage")
        return True
    
    try:
        if self.use_existing_redis and get_redis_client:
            # Use existing Redis client
            redis_client_instance = await get_redis_client()
            self.redis_client = await redis_client_instance.get_client()
            await self.redis_client.ping()
            return True
        else:
            # Direct Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            self.redis_client = redis.from_url(redis_url)
            await self.redis_client.ping()
            return True
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.warning("Falling back to memory storage")
        self.redis_client = None
        return False
```

**Features**:
- **Automatic Fallback**: Automatically switches to memory storage when Redis is unavailable
- **Connection Reuse**: Supports using existing Redis connection pools
- **Flexible Configuration**: Supports environment variable configuration for Redis connection
- **Error Handling**: Comprehensive error handling and logging

### 6. ClickHouse Dual-Write (Permanent Storage)

When `CLICKHOUSE_ENABLED=true`, ContextEngine uses dual-write: Redis (hot cache) + ClickHouse (cold archive). Writes to ClickHouse are fire-and-forget; failures do not block the primary Redis path.

#### Environment Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CLICKHOUSE_ENABLED` | Enable dual-write to ClickHouse | `false` |
| `CLICKHOUSE_HOST` | ClickHouse server host | `localhost` |
| `CLICKHOUSE_PORT` | ClickHouse HTTP port | `8123` |
| `CLICKHOUSE_USER` | ClickHouse username | `default` |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | (empty) |
| `CLICKHOUSE_DATABASE` | Database name | `default` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database index | `1` |
| `REDIS_PASSWORD` | Redis password | (empty) |

#### ClickHouse Tables (Auto-Created)

- `context_sessions` - Session create/update/end events
- `context_conversations` - Conversation messages
- `context_task_contexts` - Task context snapshots
- `context_checkpoints` - LangGraph checkpoints
- `context_checkpoint_writes` - Checkpoint intermediate writes
- `context_conversation_sessions` - Conversation session metadata

### 7. Initialization via Infrastructure

For application-wide singleton ContextEngine, use the infrastructure persistence module:

```python
from aiecs.infrastructure.persistence import (
    initialize_redis_client,
    initialize_context_engine,
    close_context_engine,
    get_context_engine,
)

# During application startup (e.g., FastAPI lifespan)
await initialize_redis_client()
await initialize_context_engine()

# In any component
engine = get_context_engine()
if engine:
    await engine.add_conversation_message(session_id, "assistant", content)

# During shutdown
await close_context_engine()
```

## Data Model Details

### 1. SessionMetrics - Session Metrics Model

```python
@dataclass
class SessionMetrics:
    """Session-level performance metrics"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    request_count: int = 0
    error_count: int = 0
    total_processing_time: float = 0.0
    status: str = "active"  # active, completed, failed, expired
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            **asdict(self),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetrics':
        """Create instance from dictionary"""
        data = data.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)
```

**Field Descriptions**:
- **session_id**: Unique session identifier
- **user_id**: User identifier
- **created_at**: Session creation time
- **last_activity**: Last activity time
- **request_count**: Request count
- **error_count**: Error count
- **total_processing_time**: Total processing time
- **status**: Session status

### 2. ConversationMessage - Conversation Message Model

```python
@dataclass
class ConversationMessage:
    """Structured conversation message"""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMessage':
        """Create instance from dictionary"""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
```

**Field Descriptions**:
- **role**: Message role (user, assistant, system)
- **content**: Message content
- **timestamp**: Message timestamp
- **metadata**: Message metadata

## Design Patterns Explained

### 1. Adapter Pattern
```python
class ContextEngine(IStorageBackend, ICheckpointerBackend):
    """Adapter Pattern - Adapts storage interface and checkpoint interface"""
    
    async def create_session(self, session_id: str, user_id: str, metadata: Dict[str, Any] = None):
        # Implements IStorageBackend interface
        pass
    
    async def put_checkpoint(self, thread_id: str, checkpoint_id: str, checkpoint_data: Dict[str, Any]):
        # Implements ICheckpointerBackend interface
        pass
```

**Advantages**:
- **Unified Interface**: Unifies implementations of different storage interfaces
- **Backward Compatibility**: Maintains compatibility with existing interfaces
- **Function Integration**: Integrates related functionality into a unified implementation

### 2. Strategy Pattern
```python
async def _store_session(self, session: SessionMetrics):
    """Storage Strategy - Selects storage method based on available backend"""
    if self.redis_client:
        # Redis storage strategy
        key = f"session:{session.session_id}"
        await self.redis_client.setex(key, self.session_ttl, json.dumps(session.to_dict()))
    else:
        # Memory storage strategy
        self._memory_sessions[session.session_id] = session
```

**Advantages**:
- **Algorithm Encapsulation**: Encapsulates storage algorithms in concrete implementations
- **Dynamic Switching**: Can switch storage strategies at runtime
- **Easy Extension**: Adding new storage strategies doesn't require modifying existing code

### 3. Template Method Pattern
```python
async def _store_conversation_message(self, session_id: str, message: ConversationMessage):
    """Template Method - Defines common flow for storing conversation messages"""
    # 1. Serialize message
    message_data = message.to_dict()
    
    # 2. Select storage backend
    if self.redis_client:
        # Redis storage implementation
        key = f"conversation:{session_id}"
        await self.redis_client.lpush(key, json.dumps(message_data))
        await self.redis_client.expire(key, self.session_ttl)
    else:
        # Memory storage implementation
        if session_id not in self._memory_conversations:
            self._memory_conversations[session_id] = []
        self._memory_conversations[session_id].append(message)
    
    # 3. Update metrics
    self._global_metrics["total_messages"] += 1
```

**Advantages**:
- **Unified Flow**: Defines unified storage flow
- **Step Reuse**: Common steps can be reused in subclasses
- **Easy Maintenance**: Modifying flow only requires modifying template method

## Usage Examples

### 1. Basic Session Management

```python
from aiecs.domain.context import ContextEngine

# Initialize ContextEngine (creates own RedisClient per instance)
engine = ContextEngine(use_existing_redis=True)
await engine.initialize()

# Create session
session = await engine.create_session(
    session_id="user_123_session_001",
    user_id="user_123",
    metadata={"source": "web", "version": "1.0"}
)

# Update session metrics
await engine.update_session(
    session_id="user_123_session_001",
    increment_requests=True,
    add_processing_time=1.5,
    mark_error=False
)

# End session
await engine.end_session("user_123_session_001", status="completed")
```

### 2. Conversation History Management

```python
# Add conversation messages
await engine.add_conversation_message(
    session_id="user_123_session_001",
    role="user",
    content="Hello, I need help with data analysis",
    metadata={"message_type": "query", "priority": "normal"}
)

await engine.add_conversation_message(
    session_id="user_123_session_001",
    role="assistant",
    content="I'd be happy to help you with data analysis. What specific data do you have?",
    metadata={"message_type": "response", "confidence": 0.95}
)

# Get conversation history
history = await engine.get_conversation_history(
    session_id="user_123_session_001",
    limit=10
)

for message in history:
    print(f"{message.role}: {message.content}")
```

### 3. Task Context Management

```python
from aiecs.domain.task.task_context import TaskContext

# Create task context
context = TaskContext(
    {"user_id": "user_123", "chat_id": "session_001", "metadata": {"task_type": "analysis"}}
)

# Store context
await engine.store_task_context("user_123_session_001", context)

# Retrieve context
retrieved_context = await engine.get_task_context("user_123_session_001")
if retrieved_context:
    print(f"Task mode: {retrieved_context.mode}")
    print(f"Service: {retrieved_context.service}")
```

### 4. Checkpoint Management

```python
# Store checkpoint
checkpoint_data = {
    "workflow_state": "data_processing",
    "current_step": "data_cleaning",
    "processed_records": 1000,
    "errors": []
}

await engine.store_checkpoint(
    thread_id="workflow_001",
    checkpoint_id="checkpoint_001",
    checkpoint_data=checkpoint_data,
    metadata={"workflow_version": "1.0", "created_by": "system"}
)

# Get checkpoint
checkpoint = await engine.get_checkpoint(
    thread_id="workflow_001",
    checkpoint_id="checkpoint_001"
)

if checkpoint:
    print(f"Workflow state: {checkpoint['data']['workflow_state']}")
    print(f"Current step: {checkpoint['data']['current_step']}")
```

### 5. Advanced Conversation Session Management

```python
from aiecs.domain.context.conversation_models import ConversationParticipant

# Create conversation session (participants as dict list)
session_key = await engine.create_conversation_session(
    session_id="session_001",
    participants=[
        {"id": "user_123", "type": "user", "role": "user"},
        {"id": "agent_001", "type": "agent", "role": "assistant", "metadata": {}}
    ],
    session_type="user_to_agent",
    metadata={"project": "sales_analysis", "priority": "high"}
)

# Add agent communication message
await engine.add_agent_communication_message(
    session_key=session_key,
    sender_id="agent_001",
    sender_type="agent",
    sender_role="data_analyst",
    content="I've analyzed your sales data and found some interesting patterns.",
    message_type="analysis_result",
    metadata={"analysis_id": "analysis_001", "confidence": 0.92}
)

# Get agent conversation history
agent_history = await engine.get_agent_conversation_history(
    session_key=session_key,
    limit=20
)
```

## Maintenance Guide

### 1. Daily Maintenance

#### Health Checks
```python
async def check_engine_health(engine: ContextEngine):
    """Check content engine health status"""
    health_status = await engine.health_check()
    
    print(f"Engine Status: {health_status['status']}")
    print(f"Storage Backend: {health_status['storage_backend']}")
    print(f"Active Sessions: {health_status['active_sessions']}")
    print(f"Total Messages: {health_status['total_messages']}")
    
    if health_status['status'] != 'healthy':
        print(f"Health Issues: {health_status.get('issues', [])}")
    
    return health_status['status'] == 'healthy'
```

#### Performance Monitoring
```python
async def monitor_engine_performance(engine: ContextEngine):
    """Monitor content engine performance"""
    metrics = await engine.get_metrics()
    
    print("=== Content Engine Metrics ===")
    print(f"Total Sessions: {metrics['total_sessions']}")
    print(f"Active Sessions: {metrics['active_sessions']}")
    print(f"Total Messages: {metrics['total_messages']}")
    print(f"Total Checkpoints: {metrics['total_checkpoints']}")
    
    # Check memory usage
    if 'memory_usage' in metrics:
        print(f"Memory Usage: {metrics['memory_usage']}")
    
    # Check storage performance
    if 'storage_performance' in metrics:
        perf = metrics['storage_performance']
        print(f"Average Response Time: {perf['avg_response_time']:.3f}s")
        print(f"Cache Hit Rate: {perf['cache_hit_rate']:.2%}")
```

### 2. Troubleshooting

#### Common Issue Diagnosis

**Issue 1: Redis Connection Failure**
```python
async def diagnose_redis_connection(engine: ContextEngine):
    """Diagnose Redis connection issues"""
    try:
        # Check Redis client status
        if engine.redis_client:
            await engine.redis_client.ping()
            print("✅ Redis connection is healthy")
        else:
            print("⚠️ Redis client is None, using memory storage")
        
        # Check health status
        health = await engine.health_check()
        print(f"Health status: {health['status']}")
        
        if health['status'] != 'healthy':
            print(f"Health issues: {health.get('issues', [])}")
            
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        
        # Check environment variables
        import os
        redis_url = os.getenv('REDIS_URL')
        print(f"REDIS_URL: {redis_url}")
        
        # Check network connection
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            print(f"Network connectivity: {'ok' if result == 0 else 'failed'}")
        except Exception as net_e:
            print(f"Network check failed: {net_e}")
```

**Issue 2: Session Data Inconsistency**
```python
async def diagnose_session_consistency(engine: ContextEngine, session_id: str):
    """Diagnose session data consistency issues"""
    try:
        # Get session
        session = await engine.get_session(session_id)
        if not session:
            print(f"❌ Session {session_id} not found")
            return
        
        print(f"✅ Session found: {session.session_id}")
        print(f"User ID: {session.user_id}")
        print(f"Status: {session.status}")
        print(f"Request Count: {session.request_count}")
        print(f"Error Count: {session.error_count}")
        
        # Check conversation history
        history = await engine.get_conversation_history(session_id, limit=5)
        print(f"Recent messages: {len(history)}")
        
        # Check task context
        context = await engine.get_task_context(session_id)
        if context:
            print(f"Task context: {context.mode} - {context.service}")
        else:
            print("No task context found")
        
        # Check checkpoints
        checkpoints = await engine.list_checkpoints(session_id, limit=5)
        print(f"Checkpoints: {len(checkpoints)}")
        
    except Exception as e:
        print(f"❌ Session consistency check failed: {e}")
```

### 3. Performance Optimization

#### Memory Usage Optimization
```python
async def optimize_memory_usage(engine: ContextEngine):
    """Optimize memory usage"""
    # Clean up expired sessions
    cleaned_count = await engine.cleanup_expired_sessions(max_idle_hours=24)
    print(f"Cleaned up {cleaned_count} expired sessions")
    
    # Check memory usage
    metrics = await engine.get_metrics()
    if 'memory_usage' in metrics:
        memory_usage = metrics['memory_usage']
        print(f"Current memory usage: {memory_usage}")
        
        # If memory usage is high, perform cleanup
        if memory_usage > 0.8:  # 80% threshold
            print("Memory usage high, performing cleanup...")
            # Perform additional cleanup operations
            await engine.cleanup_expired_sessions(max_idle_hours=12)
```

#### Storage Performance Optimization
```python
async def optimize_storage_performance(engine: ContextEngine):
    """Optimize storage performance"""
    # Check storage performance metrics
    metrics = await engine.get_metrics()
    
    if 'storage_performance' in metrics:
        perf = metrics['storage_performance']
        
        # Check response time
        if perf['avg_response_time'] > 0.1:  # 100ms threshold
            print("Storage response time is high, checking connection...")
            health = await engine.health_check()
            print(f"Storage health: {health}")
        
        # Check cache hit rate
        if perf['cache_hit_rate'] < 0.8:  # 80% threshold
            print("Cache hit rate is low, consider increasing cache size")
```

### 4. Data Migration

#### Session Data Migration
```python
async def migrate_session_data(source_engine: ContextEngine, target_engine: ContextEngine):
    """Migrate session data"""
    print("Starting session data migration...")
    
    # Get all sessions (need to implement list_sessions method)
    # Here we assume there's a method to get all sessions
    sessions = await source_engine.list_all_sessions()
    
    migrated_count = 0
    for session in sessions:
        try:
            # Migrate session
            await target_engine.create_session(
                session.session_id,
                session.user_id,
                session.metadata
            )
            
            # Migrate conversation history
            history = await source_engine.get_conversation_history(session.session_id)
            for message in history:
                await target_engine.add_conversation_message(
                    session.session_id,
                    message.role,
                    message.content,
                    message.metadata
                )
            
            # Migrate task context
            context = await source_engine.get_task_context(session.session_id)
            if context:
                await target_engine.store_task_context(session.session_id, context)
            
            migrated_count += 1
            print(f"Migrated session: {session.session_id}")
            
        except Exception as e:
            print(f"Failed to migrate session {session.session_id}: {e}")
    
    print(f"Migration completed: {migrated_count} sessions migrated")
```

## Monitoring and Logging

### Performance Monitoring
```python
import time
from typing import Dict, Any

class ContentEngineMonitor:
    """Content Engine Monitor"""
    
    def __init__(self, engine: ContextEngine):
        self.engine = engine
        self.operation_metrics = {
            "session_operations": [],
            "conversation_operations": [],
            "checkpoint_operations": []
        }
    
    async def record_operation(self, operation_type: str, operation: str, 
                             latency: float, success: bool):
        """Record operation metrics"""
        metric = {
            "operation_type": operation_type,
            "operation": operation,
            "latency": latency,
            "success": success,
            "timestamp": time.time()
        }
        
        self.operation_metrics[f"{operation_type}_operations"].append(metric)
        
        # Keep last 1000 records
        if len(self.operation_metrics[f"{operation_type}_operations"]) > 1000:
            self.operation_metrics[f"{operation_type}_operations"] = \
                self.operation_metrics[f"{operation_type}_operations"][-1000:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        report = {}
        
        for operation_type, metrics in self.operation_metrics.items():
            if not metrics:
                continue
            
            latencies = [m["latency"] for m in metrics]
            successes = [m["success"] for m in metrics]
            
            report[operation_type] = {
                "total_operations": len(metrics),
                "success_rate": sum(successes) / len(successes) if successes else 0,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "min_latency": min(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0
            }
        
        return report
```

### Logging
```python
import logging
from typing import Dict, Any

class ContentEngineLogger:
    """Content Engine Logger"""
    
    def __init__(self, engine: ContextEngine):
        self.engine = engine
        self.logger = logging.getLogger(__name__)
    
    async def log_session_operation(self, operation: str, session_id: str, 
                                  success: bool, latency: float, error: str = None):
        """Log session operation"""
        log_data = {
            "operation": operation,
            "session_id": session_id,
            "success": success,
            "latency": latency,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            log_data["error"] = error
        
        if success:
            self.logger.info(f"Session operation completed: {log_data}")
        else:
            self.logger.error(f"Session operation failed: {log_data}")
    
    async def log_conversation_operation(self, operation: str, session_id: str,
                                       message_count: int, success: bool):
        """Log conversation operation"""
        log_data = {
            "operation": operation,
            "session_id": session_id,
            "message_count": message_count,
            "success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if success:
            self.logger.info(f"Conversation operation completed: {log_data}")
        else:
            self.logger.error(f"Conversation operation failed: {log_data}")
```

## Version History

- **v1.0.0**: Initial version, basic session management functionality
- **v1.1.0**: Added conversation history management
- **v1.2.0**: Added task context management
- **v1.3.0**: Added checkpoint management
- **v1.4.0**: Added multi-backend storage support
- **v1.5.0**: Added advanced conversation session management
- **v1.6.0**: Added performance monitoring and logging
- **v1.7.0**: Added ClickHouse dual-write for permanent storage; infrastructure persistence init

## Integration Tests

ContextEngine ClickHouse integration tests are in `test/integration/context/test_context_clickhouse.py`

Prerequisites: Redis and ClickHouse running, configured in `.env.test`:
- `CLICKHOUSE_ENABLED=true`
- `REDIS_*`, `CLICKHOUSE_*` environment variables

Run: `poetry run pytest test/integration/context/test_context_clickhouse.py -v`

## Related Documentation

- [AIECS Project Overview](../PROJECT_SUMMARY.md)
- [Storage Interfaces Documentation](../CORE/STORAGE_INTERFACES.md)
- [Execution Interfaces Documentation](../CORE/EXECUTION_INTERFACES.md)
- [Configuration Management Documentation](../CONFIG/CONFIG_MANAGEMENT.md)
- [Redis Client](../INFRASTRUCTURE_PERSISTENCE/REDIS_CLIENT.md)

# Storage Interfaces Technical Documentation

## Overview

### Design Motivation and Problem Background

When building large-scale AI application systems, data storage faces the following core challenges:

**1. Diverse Storage Requirements**
- Different types of data: session data, conversation history, checkpoints, task context, etc.
- Different data have different storage characteristics (temporary, persistent, query requirements)
- Lack of unified storage abstraction layer leads to scattered storage logic

**2. Storage Backend Heterogeneity**
- Support multiple storage backends (Redis, PostgreSQL, file system, cloud storage)
- Different storage backends have different APIs and characteristics
- Switching storage backends requires extensive code modifications

**3. Data Consistency and Reliability**
- Data consistency guarantees in distributed environments
- Data backup and recovery mechanisms
- Degradation and recovery strategies when storage fails

**4. Performance and Scalability Challenges**
- Performance optimization under heavy concurrent access
- Data sharding and load balancing
- Caching strategies and query optimization

**Storage Interface System Solution**:
- **Interface Segregation Principle**: Separate different storage responsibilities into independent interfaces
- **Unified Abstraction Layer**: Provide unified storage operation interfaces
- **Dependency Inversion**: High-level modules depend on abstract interfaces, low-level modules implement interfaces
- **Plugin Support**: Support dynamic switching of multiple storage backends
- **Type Safety**: Interface definitions based on Python type system

### Component Positioning

`storage_interface.py` is the storage interface definition of the AIECS system, located in the Domain Layer, defining all abstract interfaces related to storage. As the storage contract layer of the system, it provides type-safe, clearly-responsible storage operation specifications.

## Component Type and Positioning

### Component Type
**Domain Interface Component** - Located in the Domain Layer, belongs to system contract definitions

### Architecture Layers
```
┌─────────────────────────────────────────┐
│         Application Layer               │  ← Components using storage interfaces
│  (ContextEngine, ServiceLayer)         │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         Domain Layer                    │  ← Storage interfaces layer
│  (Storage Interfaces, Data Contracts)  │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│       Infrastructure Layer              │  ← Components implementing storage interfaces
│  (Redis, PostgreSQL, FileStorage)      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         External Storage                │  ← External storage systems
│  (Redis, PostgreSQL, GCS, S3)          │
└─────────────────────────────────────────┘
```

## Upstream Components (Consumers)

### 1. Domain Services
- **ContextEngine** (`domain/context/context_engine.py`)
- **SessionManager** (if exists)
- **ConversationManager** (if exists)

### 2. Application Layer Services
- **TaskService** (if exists)
- **ExecutionService** (if exists)
- **AnalyticsService** (if exists)

### 3. Infrastructure Layer Implementations
- **DatabaseManager** (`infrastructure/persistence/database_manager.py`)
- **RedisClient** (`infrastructure/persistence/redis_client.py`)
- **FileStorage** (`infrastructure/persistence/file_storage.py`)

## Downstream Components (Dependencies)

### 1. Python ABC System
- **Purpose**: Provide abstract base class support
- **Functionality**: Interface definition, abstract method declaration
- **Dependency Type**: Language feature dependency

### 2. Domain Models
- **TaskContext** (`domain/task/task_context.py`)
- **Session** (if exists)
- **Conversation** (if exists)

### 3. Type System
- **Purpose**: Provide type checking and type safety
- **Functionality**: Parameter type validation, return value type checking
- **Dependency Type**: Python type system

## Core Interfaces Explained

### 1. ISessionStorage - Session Storage Interface

```python
class ISessionStorage(ABC):
    """Session storage interface - Domain layer abstraction"""
    
    @abstractmethod
    async def create_session(
        self,
        session_id: str,
        user_id: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create new session"""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        pass
    
    @abstractmethod
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any] = None,
        increment_requests: bool = False,
        add_processing_time: float = 0.0,
        mark_error: bool = False
    ) -> bool:
        """Update session information and metrics"""
        pass
    
    @abstractmethod
    async def end_session(self, session_id: str, status: str = "completed") -> bool:
        """End session and update metrics"""
        pass
```

**Responsibilities**:
- **Session Lifecycle Management**: Create, get, update, end sessions
- **Session Metrics Tracking**: Request counting, processing time, error statistics
- **Session Metadata Management**: Store and update session-related metadata

**Implementation Requirements**:
- Must support complete session lifecycle management
- Must provide session metrics and statistics functionality
- Should support concurrent access control for sessions

### 2. IConversationStorage - Conversation Storage Interface

```python
class IConversationStorage(ABC):
    """Conversation storage interface - Domain layer abstraction"""
    
    @abstractmethod
    async def add_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Add conversation message"""
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get conversation history"""
        pass
```

**Responsibilities**:
- **Conversation Message Management**: Add and retrieve conversation messages
- **Conversation History Query**: Support pagination and limit queries
- **Conversation Context Maintenance**: Maintain conversation continuity and context

**Implementation Requirements**:
- Must support chronological storage and retrieval of messages
- Must provide efficient history query functionality
- Should support conversation persistence and recovery

### 3. ICheckpointStorage - Checkpoint Storage Interface

```python
class ICheckpointStorage(ABC):
    """Checkpoint storage interface - Domain layer abstraction"""
    
    @abstractmethod
    async def store_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store checkpoint data"""
        pass
    
    @abstractmethod
    async def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get checkpoint data"""
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List checkpoints"""
        pass
```

**Responsibilities**:
- **Checkpoint Management**: Store and retrieve workflow checkpoints
- **State Recovery**: Support workflow state recovery from checkpoints
- **Version Control**: Manage checkpoint versions and history

**Implementation Requirements**:
- Must support atomic checkpoint storage
- Must provide fast checkpoint retrieval functionality
- Should support checkpoint version management and cleanup

### 4. ITaskContextStorage - Task Context Storage Interface

```python
class ITaskContextStorage(ABC):
    """Task context storage interface - Domain layer abstraction"""
    
    @abstractmethod
    async def get_task_context(self, session_id: str) -> Optional[Any]:
        """Get task context"""
        pass
    
    @abstractmethod
    async def store_task_context(self, session_id: str, context: Any) -> bool:
        """Store task context"""
        pass
```

**Responsibilities**:
- **Task Context Management**: Store and retrieve task execution context
- **State Persistence**: Support persistent storage of task state
- **Context Sharing**: Support cross-session context sharing

**Implementation Requirements**:
- Must support context serialization and deserialization
- Must provide fast context access functionality
- Should support context version management

### 5. IStorageBackend - Unified Storage Backend Interface

```python
class IStorageBackend(
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage
):
    """Unified storage backend interface - Domain layer abstraction"""
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize storage backend"""
        pass
    
    @abstractmethod
    async def close(self):
        """Close storage backend"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        pass
    
    @abstractmethod
    async def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self, max_idle_hours: int = 24) -> int:
        """Cleanup expired sessions"""
        pass
```

**Responsibilities**:
- **Unified Storage Interface**: Integrate all storage functionality
- **Lifecycle Management**: Initialize and close storage backend
- **Health Monitoring**: Provide health checks and metrics monitoring
- **Data Cleanup**: Support automatic cleanup of expired data

### 6. ICheckpointerBackend - Checkpoint Backend Interface

```python
class ICheckpointerBackend(ABC):
    """Checkpoint backend interface - LangGraph integration"""
    
    @abstractmethod
    async def put_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        checkpoint_data: Dict[str, Any],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Store LangGraph workflow checkpoint"""
        pass
    
    @abstractmethod
    async def get_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve LangGraph workflow checkpoint"""
        pass
    
    @abstractmethod
    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List LangGraph workflow checkpoints"""
        pass
    
    @abstractmethod
    async def put_writes(
        self,
        thread_id: str,
        checkpoint_id: str,
        task_id: str,
        writes_data: List[tuple]
    ) -> bool:
        """Store intermediate writes for checkpoint"""
        pass
    
    @abstractmethod
    async def get_writes(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> List[tuple]:
        """Get intermediate writes for checkpoint"""
        pass
```

**Responsibilities**:
- **LangGraph Integration**: Support checkpoint functionality for LangGraph workflows
- **Intermediate State Management**: Store and retrieve workflow intermediate states
- **Workflow Recovery**: Support workflow recovery from any checkpoint

## Design Patterns Explained

### 1. Interface Segregation Principle
```python
# Separate different storage responsibilities into independent interfaces
class ISessionStorage(ABC):        # Session storage
class IConversationStorage(ABC):   # Conversation storage
class ICheckpointStorage(ABC):     # Checkpoint storage
class ITaskContextStorage(ABC):    # Task context storage
```

**Advantages**:
- **Single Responsibility**: Each interface is responsible for only specific type of storage
- **Easy to Implement**: Implementation classes can selectively implement relevant interfaces
- **Easy to Test**: Can test each storage functionality independently

### 2. Dependency Inversion Principle
```python
# High-level modules depend on abstract interfaces
class ContextEngine:
    def __init__(self, storage_backend: IStorageBackend):
        self.storage = storage_backend
```

**Advantages**:
- **Loose Coupling**: High-level modules don't depend on specific storage implementations
- **Extensible**: Can easily replace storage backends
- **Testable**: Can use mock objects for testing

### 3. Composition Pattern
```python
# Form unified interface by composing multiple interfaces
class IStorageBackend(
    ISessionStorage,
    IConversationStorage,
    ICheckpointStorage,
    ITaskContextStorage
):
    # Unified storage interface
```

**Advantages**:
- **Function Integration**: Integrate related functionality into unified interface
- **Backward Compatibility**: Maintain compatibility with existing code
- **Easy to Use**: Provide unified storage operation interface

## Interface Implementation Standards

### 1. Basic Implementation Requirements

#### Async Operation Support
```python
class StorageBackendImpl(IStorageBackend):
    async def create_session(self, session_id: str, user_id: str, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Async create session"""
        # Implementation logic
        pass
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Async get session"""
        # Implementation logic
        pass
```

#### Error Handling Standards
```python
class StorageError(Exception):
    """Storage error base class"""
    pass

class SessionNotFoundError(StorageError):
    """Session not found error"""
    pass

class StorageConnectionError(StorageError):
    """Storage connection error"""
    pass

class StorageBackendImpl(IStorageBackend):
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            # Storage operation
            return session_data
        except ConnectionError as e:
            raise StorageConnectionError(f"Failed to connect to storage: {e}") from e
        except KeyError:
            raise SessionNotFoundError(f"Session {session_id} not found")
```

### 2. Data Serialization Standards

#### Session Data Format
```python
def serialize_session(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize session data"""
    return {
        "session_id": session_data["session_id"],
        "user_id": session_data["user_id"],
        "created_at": session_data["created_at"].isoformat(),
        "updated_at": session_data["updated_at"].isoformat(),
        "status": session_data["status"],
        "metadata": session_data.get("metadata", {}),
        "metrics": {
            "request_count": session_data.get("request_count", 0),
            "total_processing_time": session_data.get("total_processing_time", 0.0),
            "error_count": session_data.get("error_count", 0)
        }
    }

def deserialize_session(data: Dict[str, Any]) -> Dict[str, Any]:
    """Deserialize session data"""
    return {
        "session_id": data["session_id"],
        "user_id": data["user_id"],
        "created_at": datetime.fromisoformat(data["created_at"]),
        "updated_at": datetime.fromisoformat(data["updated_at"]),
        "status": data["status"],
        "metadata": data.get("metadata", {}),
        "request_count": data.get("metrics", {}).get("request_count", 0),
        "total_processing_time": data.get("metrics", {}).get("total_processing_time", 0.0),
        "error_count": data.get("metrics", {}).get("error_count", 0)
    }
```

#### Conversation Message Format
```python
def serialize_message(role: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Serialize conversation message"""
    return {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": metadata or {}
    }
```

### 3. Performance Optimization Standards

#### Batch Operation Support
```python
class OptimizedStorageBackend(IStorageBackend):
    async def batch_create_sessions(self, sessions: List[Dict[str, Any]]) -> List[bool]:
        """Batch create sessions"""
        # Implement batch operation logic
        pass
    
    async def batch_get_sessions(self, session_ids: List[str]) -> List[Optional[Dict[str, Any]]]:
        """Batch get sessions"""
        # Implement batch query logic
        pass
```

#### Caching Strategy
```python
from functools import lru_cache
import asyncio

class CachedStorageBackend(IStorageBackend):
    def __init__(self, underlying_storage: IStorageBackend, cache_size: int = 1000):
        self.storage = underlying_storage
        self._cache = {}
        self._cache_size = cache_size
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session with caching"""
        if session_id in self._cache:
            return self._cache[session_id]
        
        session = await self.storage.get_session(session_id)
        if session:
            self._cache[session_id] = session
            if len(self._cache) > self._cache_size:
                # Simple LRU cleanup
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
        
        return session
```

## Usage Examples

### 1. Basic Storage Implementation

#### Redis Storage Implementation
```python
import redis.asyncio as redis
from aiecs.core.interface.storage_interface import IStorageBackend

class RedisStorageBackend(IStorageBackend):
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.prefix = "aiecs:"
    
    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        try:
            await self.redis.ping()
            return True
        except Exception as e:
            print(f"Failed to initialize Redis: {e}")
            return False
    
    async def create_session(self, session_id: str, user_id: str, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create session"""
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
            "metadata": metadata or {},
            "request_count": 0,
            "total_processing_time": 0.0,
            "error_count": 0
        }
        
        key = f"{self.prefix}session:{session_id}"
        await self.redis.hset(key, mapping=session_data)
        await self.redis.expire(key, 86400)  # 24 hour expiration
        
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session"""
        key = f"{self.prefix}session:{session_id}"
        data = await self.redis.hgetall(key)
        
        if not data:
            return None
        
        # Convert data types
        data["request_count"] = int(data.get("request_count", 0))
        data["total_processing_time"] = float(data.get("total_processing_time", 0.0))
        data["error_count"] = int(data.get("error_count", 0))
        
        return data
    
    async def add_conversation_message(self, session_id: str, role: str, 
                                     content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add conversation message"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        key = f"{self.prefix}conversation:{session_id}"
        await self.redis.lpush(key, json.dumps(message))
        await self.redis.expire(key, 86400)  # 24 hour expiration
        
        return True
    
    async def get_conversation_history(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history"""
        key = f"{self.prefix}conversation:{session_id}"
        messages = await self.redis.lrange(key, 0, limit - 1)
        
        return [json.loads(msg) for msg in messages]
    
    async def close(self):
        """Close connection"""
        await self.redis.close()
```

#### PostgreSQL Storage Implementation
```python
import asyncpg
from aiecs.core.interface.storage_interface import IStorageBackend

class PostgreSQLStorageBackend(IStorageBackend):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool"""
        try:
            self.pool = await asyncpg.create_pool(self.connection_string)
            
            # Create table structure
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id VARCHAR(255) PRIMARY KEY,
                        user_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW(),
                        status VARCHAR(50) DEFAULT 'active',
                        metadata JSONB,
                        request_count INTEGER DEFAULT 0,
                        total_processing_time FLOAT DEFAULT 0.0,
                        error_count INTEGER DEFAULT 0
                    )
                """)
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT NOW(),
                        metadata JSONB,
                        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                    )
                """)
            
            return True
        except Exception as e:
            print(f"Failed to initialize PostgreSQL: {e}")
            return False
    
    async def create_session(self, session_id: str, user_id: str, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create session"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO sessions (session_id, user_id, metadata)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id) DO UPDATE SET
                    user_id = EXCLUDED.user_id,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, session_id, user_id, json.dumps(metadata or {}))
            
            # Get created session
            row = await conn.fetchrow("""
                SELECT * FROM sessions WHERE session_id = $1
            """, session_id)
            
            return dict(row)
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
```

### 2. Storage Factory Pattern

```python
from enum import Enum
from typing import Union

class StorageType(Enum):
    REDIS = "redis"
    POSTGRESQL = "postgresql"
    MEMORY = "memory"

class StorageFactory:
    """Storage backend factory"""
    
    @staticmethod
    def create_storage_backend(
        storage_type: StorageType,
        config: Dict[str, Any]
    ) -> IStorageBackend:
        """Create storage backend instance"""
        if storage_type == StorageType.REDIS:
            return RedisStorageBackend(config["redis_url"])
        elif storage_type == StorageType.POSTGRESQL:
            return PostgreSQLStorageBackend(config["postgresql_url"])
        elif storage_type == StorageType.MEMORY:
            return MemoryStorageBackend()
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")

# Usage example
config = {
    "redis_url": "redis://localhost:6379/0",
    "postgresql_url": "postgresql://user:password@localhost/aiecs"
}

# Create Redis storage backend
redis_storage = StorageFactory.create_storage_backend(
    StorageType.REDIS, config
)

# Create PostgreSQL storage backend
postgres_storage = StorageFactory.create_storage_backend(
    StorageType.POSTGRESQL, config
)
```

### 3. Storage Adapter Pattern

```python
class StorageAdapter(IStorageBackend):
    """Storage adapter - Support multiple storage backends"""
    
    def __init__(self, primary_storage: IStorageBackend, 
                 fallback_storage: IStorageBackend = None):
        self.primary = primary_storage
        self.fallback = fallback_storage
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session - Support failover"""
        try:
            return await self.primary.get_session(session_id)
        except Exception as e:
            if self.fallback:
                print(f"Primary storage failed, using fallback: {e}")
                return await self.fallback.get_session(session_id)
            raise
    
    async def create_session(self, session_id: str, user_id: str, 
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create session - Dual-write strategy"""
        result = await self.primary.create_session(session_id, user_id, metadata)
        
        if self.fallback:
            try:
                await self.fallback.create_session(session_id, user_id, metadata)
            except Exception as e:
                print(f"Fallback storage failed: {e}")
        
        return result
```

## Maintenance Guide

### 1. Daily Maintenance

#### Storage Health Check
```python
class StorageHealthChecker:
    """Storage health checker"""
    
    def __init__(self, storage_backend: IStorageBackend):
        self.storage = storage_backend
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check storage connection
        try:
            await self.storage.health_check()
            health_status["checks"]["connection"] = "ok"
        except Exception as e:
            health_status["checks"]["connection"] = f"error: {e}"
            health_status["status"] = "unhealthy"
        
        # Check storage performance
        try:
            start_time = time.time()
            await self.storage.get_metrics()
            response_time = time.time() - start_time
            health_status["checks"]["performance"] = f"ok ({response_time:.3f}s)"
        except Exception as e:
            health_status["checks"]["performance"] = f"error: {e}"
            health_status["status"] = "unhealthy"
        
        return health_status
```

#### Data Migration Tool
```python
class StorageMigrator:
    """Storage migration tool"""
    
    def __init__(self, source_storage: IStorageBackend, 
                 target_storage: IStorageBackend):
        self.source = source_storage
        self.target = target_storage
    
    async def migrate_sessions(self, batch_size: int = 100) -> int:
        """Migrate session data"""
        migrated_count = 0
        
        # Get all session IDs (need to implement list_sessions method)
        session_ids = await self._get_all_session_ids()
        
        for i in range(0, len(session_ids), batch_size):
            batch = session_ids[i:i + batch_size]
            
            for session_id in batch:
                try:
                    # Get data from source storage
                    session_data = await self.source.get_session(session_id)
                    if session_data:
                        # Write to target storage
                        await self.target.create_session(
                            session_data["session_id"],
                            session_data["user_id"],
                            session_data.get("metadata")
                        )
                        migrated_count += 1
                except Exception as e:
                    print(f"Failed to migrate session {session_id}: {e}")
        
        return migrated_count
    
    async def _get_all_session_ids(self) -> List[str]:
        """Get all session IDs (need to adjust based on specific implementation)"""
        # This needs to get all session IDs based on specific storage implementation
        # For example, from Redis KEYS command or PostgreSQL SELECT query
        pass
```

### 2. Troubleshooting

#### Common Issue Diagnosis

**Issue 1: Storage Connection Failed**
```python
# Error message
StorageConnectionError: Failed to connect to storage: Connection refused

# Diagnosis steps
async def diagnose_connection_issue(storage_backend: IStorageBackend):
    """Diagnose storage connection issue"""
    try:
        # Check storage initialization
        initialized = await storage_backend.initialize()
        print(f"Storage initialized: {initialized}")
        
        # Check health status
        health = await storage_backend.health_check()
        print(f"Health check: {health}")
        
        # Check metrics
        metrics = await storage_backend.get_metrics()
        print(f"Metrics: {metrics}")
        
    except Exception as e:
        print(f"Connection diagnosis failed: {e}")
        
        # Check network connection
        import socket
        try:
            # Assume Redis connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 6379))
            sock.close()
            print(f"Network connectivity: {'ok' if result == 0 else 'failed'}")
        except Exception as net_e:
            print(f"Network check failed: {net_e}")
```

**Issue 2: Data Consistency Issue**
```python
async def diagnose_data_consistency(storage_backend: IStorageBackend):
    """Diagnose data consistency issue"""
    # Create test session
    test_session_id = "test_consistency"
    test_user_id = "test_user"
    
    try:
        # Create session
        session = await storage_backend.create_session(
            test_session_id, test_user_id
        )
        print(f"Session created: {session}")
        
        # Immediately read session
        retrieved_session = await storage_backend.get_session(test_session_id)
        print(f"Session retrieved: {retrieved_session}")
        
        # Compare data
        if session == retrieved_session:
            print("Data consistency: OK")
        else:
            print("Data consistency: FAILED")
            print(f"Created: {session}")
            print(f"Retrieved: {retrieved_session}")
        
        # Cleanup test data
        await storage_backend.end_session(test_session_id)
        
    except Exception as e:
        print(f"Consistency check failed: {e}")
```

### 3. Performance Optimization

#### Connection Pool Management
```python
class OptimizedStorageBackend(IStorageBackend):
    def __init__(self, connection_config: Dict[str, Any]):
        self.connection_config = connection_config
        self.pool = None
        self.pool_size = connection_config.get("pool_size", 10)
        self.max_overflow = connection_config.get("max_overflow", 20)
    
    async def initialize(self) -> bool:
        """Initialize connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_config["url"],
                min_size=self.pool_size,
                max_size=self.pool_size + self.max_overflow
            )
            return True
        except Exception as e:
            print(f"Failed to initialize connection pool: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session using connection pool"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM sessions WHERE session_id = $1", 
                session_id
            )
            return dict(row) if row else None
```

#### Batch Operation Optimization
```python
class BatchOptimizedStorageBackend(IStorageBackend):
    def __init__(self, underlying_storage: IStorageBackend):
        self.storage = underlying_storage
        self.batch_size = 100
        self.batch_timeout = 1.0  # seconds
        self._batch_queue = []
        self._batch_lock = asyncio.Lock()
    
    async def add_conversation_message(self, session_id: str, role: str, 
                                     content: str, metadata: Dict[str, Any] = None) -> bool:
        """Batch add conversation messages"""
        message = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        async with self._batch_lock:
            self._batch_queue.append(message)
            
            if len(self._batch_queue) >= self.batch_size:
                await self._flush_batch()
        
        return True
    
    async def _flush_batch(self):
        """Flush batch queue"""
        if not self._batch_queue:
            return
        
        # Execute batch insert
        await self._execute_batch_insert(self._batch_queue)
        self._batch_queue.clear()
    
    async def _execute_batch_insert(self, messages: List[Dict[str, Any]]):
        """Execute batch insert"""
        # Implement batch insert logic
        pass
```

## Monitoring and Logging

### Storage Monitoring Metrics
```python
class StorageMonitor:
    """Storage monitor"""
    
    def __init__(self, storage_backend: IStorageBackend):
        self.storage = storage_backend
        self.metrics = {
            "operations": defaultdict(int),
            "errors": defaultdict(int),
            "latencies": defaultdict(list)
        }
    
    async def record_operation(self, operation: str, latency: float, success: bool):
        """Record operation metrics"""
        self.metrics["operations"][operation] += 1
        self.metrics["latencies"][operation].append(latency)
        
        if not success:
            self.metrics["errors"][operation] += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report"""
        report = {}
        
        for operation in self.metrics["operations"]:
            latencies = self.metrics["latencies"][operation]
            errors = self.metrics["errors"][operation]
            operations = self.metrics["operations"][operation]
            
            report[operation] = {
                "total_operations": operations,
                "error_count": errors,
                "error_rate": errors / operations if operations > 0 else 0,
                "avg_latency": sum(latencies) / len(latencies) if latencies else 0,
                "min_latency": min(latencies) if latencies else 0,
                "max_latency": max(latencies) if latencies else 0
            }
        
        return report
```

### Storage Logging
```python
import logging
from typing import Dict, Any

class StorageLogger:
    """Storage logger"""
    
    def __init__(self, storage_backend: IStorageBackend):
        self.storage = storage_backend
        self.logger = logging.getLogger(__name__)
    
    async def log_operation(self, operation: str, session_id: str, 
                          success: bool, latency: float, error: str = None):
        """Log storage operation"""
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
            self.logger.info(f"Storage operation completed: {log_data}")
        else:
            self.logger.error(f"Storage operation failed: {log_data}")
    
    async def log_health_check(self, health_status: Dict[str, Any]):
        """Log health check"""
        self.logger.info(f"Storage health check: {health_status}")
        
        if health_status.get("status") != "healthy":
            self.logger.warning(f"Storage health issues detected: {health_status}")
```

## Version History

- **v1.0.0**: Initial version, basic storage interface definitions
- **v1.1.0**: Added session storage interface
- **v1.2.0**: Added conversation storage interface
- **v1.3.0**: Added checkpoint storage interface
- **v1.4.0**: Added task context storage interface
- **v1.5.0**: Added unified storage backend interface
- **v1.6.0**: Added LangGraph checkpoint backend interface

## Related Documentation

- [AIECS Project Overview](../PROJECT_SUMMARY.md)
- [Execution Interfaces Documentation](./EXECUTION_INTERFACES.md)
- [Configuration Management Documentation](../CONFIG/CONFIG_MANAGEMENT.md)
- [Database Manager Documentation](../INFRASTRUCTURE_PERSISTENCE/DATABASE_MANAGER.md)

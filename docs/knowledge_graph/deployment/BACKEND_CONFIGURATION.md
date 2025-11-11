# Backend Configuration Guide

Complete guide for selecting and configuring graph storage backends in AIECS Knowledge Graph.

---

## Backend Selection Matrix

| Backend | Use Case | Max Entities | Concurrency | Persistence | Production Ready |
|---------|----------|--------------|-------------|-------------|------------------|
| **InMemory** | Development, Testing | < 100K | Low | ❌ No | ❌ No |
| **SQLite** | Small apps, Embedded | < 1M | Low-Medium | ✅ Yes | ⚠️ Limited |
| **PostgreSQL** | Production, Large scale | > 100M | High | ✅ Yes | ✅ Yes |

---

## InMemoryGraphStore

### When to Use

✅ **Use for**:
- Development and testing
- Prototyping
- Small datasets (< 100K entities)
- Temporary data
- Unit tests

❌ **Don't use for**:
- Production deployments
- Persistent data
- Large graphs
- Multi-user applications

### Configuration

```python
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

# Simple initialization
store = InMemoryGraphStore()
await store.initialize()

# No configuration needed - it's in-memory!
```

### Characteristics

- **Speed**: Fastest for small graphs
- **Memory**: Limited by RAM
- **Persistence**: None (data lost on restart)
- **Concurrency**: Single-threaded (Python GIL)
- **Features**: Full GraphStore interface

---

## SQLiteGraphStore

### When to Use

✅ **Use for**:
- Small to medium applications (< 1M entities)
- Single-user or low-concurrency
- Embedded systems
- Desktop applications
- Simple deployment (single file)

❌ **Don't use for**:
- High-concurrency production
- Large graphs (> 1M entities)
- Multi-user web applications
- Write-heavy workloads

### Configuration

```python
from aiecs.infrastructure.graph_storage import SQLiteGraphStore

# File-based storage
store = SQLiteGraphStore("knowledge_graph.db")
await store.initialize()

# In-memory (for testing)
store = SQLiteGraphStore(":memory:")
await store.initialize()

# With options
store = SQLiteGraphStore(
    "graph.db",
    timeout=30.0,  # Connection timeout
    check_same_thread=False  # For async
)
await store.initialize()
```

### Performance Tuning

**SQLite Configuration**:
```python
# After initialization, optimize SQLite
async with store.conn.execute("PRAGMA journal_mode = WAL"):
    pass
async with store.conn.execute("PRAGMA synchronous = NORMAL"):
    pass
async with store.conn.execute("PRAGMA cache_size = -64000"):  # 64MB
    pass
```

### Characteristics

- **Speed**: Fast for small-medium graphs
- **Storage**: Single file database
- **Persistence**: ✅ Yes
- **Concurrency**: Limited (file locking)
- **Features**: Full GraphStore interface
- **Scalability**: Up to ~1M entities

---

## PostgresGraphStore

### When to Use

✅ **Use for**:
- Production deployments
- Large graphs (1M+ entities)
- High concurrency
- Multi-user applications
- ACID transactions required
- Advanced features (JSONB, pgvector)

❌ **Don't use for**:
- Simple single-user apps
- Embedded systems
- Minimal deployment requirements

### Configuration

**Basic Configuration**:
```python
from aiecs.infrastructure.graph_storage import PostgresGraphStore

store = PostgresGraphStore(
    host="localhost",
    port=5432,
    user="graph_user",
    password="secure_password",
    database="knowledge_graph"
)
await store.initialize()
```

**With Connection Pooling**:
```python
store = PostgresGraphStore(
    host="localhost",
    port=5432,
    user="graph_user",
    password="secure_password",
    database="knowledge_graph",
    min_pool_size=5,   # Minimum connections
    max_pool_size=20    # Maximum connections
)
await store.initialize()
```

**With SSL**:
```python
store = PostgresGraphStore(
    host="postgres.example.com",
    port=5432,
    user="graph_user",
    password="secure_password",
    database="knowledge_graph",
    ssl=True,
    sslmode="require"
)
await store.initialize()
```

**Reusing Existing Connection Pool**:
```python
from aiecs.infrastructure.persistence.database_manager import DatabaseManager

# Reuse AIECS DatabaseManager pool
db_manager = DatabaseManager(...)
await db_manager.initialize()

store = PostgresGraphStore(
    pool=db_manager.pool,  # Reuse existing pool
    database_manager=db_manager
)
await store.initialize()
```

**With pgvector** (for vector search):
```python
store = PostgresGraphStore(
    ...,
    enable_pgvector=True  # Enable vector extension
)
await store.initialize()
```

### Environment Variables

```bash
# .env file
DB_HOST=localhost
DB_PORT=5432
DB_USER=graph_user
DB_PASSWORD=secure_password
DB_NAME=knowledge_graph
ENABLE_PGVECTOR=true
```

```python
import os
from dotenv import load_dotenv

load_dotenv()

store = PostgresGraphStore(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', '5432')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    enable_pgvector=os.getenv('ENABLE_PGVECTOR', 'false').lower() == 'true'
)
await store.initialize()
```

### Characteristics

- **Speed**: Fast, scales well
- **Storage**: Enterprise-grade database
- **Persistence**: ✅ Yes, ACID transactions
- **Concurrency**: High (connection pooling)
- **Features**: Full GraphStore + advanced features
- **Scalability**: 100M+ entities

---

## Backend Selection Decision Tree

```
Start
  ↓
Need persistence?
  ├─ No → InMemoryGraphStore
  └─ Yes
      ↓
    Production?
      ├─ No → SQLiteGraphStore
      └─ Yes
          ↓
        Graph size?
          ├─ < 1M entities → SQLiteGraphStore (simple) or PostgresGraphStore (future-proof)
          └─ > 1M entities → PostgresGraphStore
```

---

## Migration Between Backends

### Using GraphStorageMigrator

```python
from aiecs.infrastructure.graph_storage.migration import GraphStorageMigrator

# Migrate from SQLite to PostgreSQL
source = SQLiteGraphStore("old_graph.db")
target = PostgresGraphStore(...)

migrator = GraphStorageMigrator()
await migrator.migrate(source, target, batch_size=1000)
```

### Manual Migration

```python
# Export from source
from aiecs.infrastructure.graph_storage.streaming import GraphStreamExporter

exporter = GraphStreamExporter(source_store)
await exporter.export_to_file("migration.jsonl.gz", compress=True)

# Import to target
from aiecs.infrastructure.graph_storage.streaming import GraphStreamImporter

importer = GraphStreamImporter(target_store)
await importer.import_from_file("migration.jsonl.gz", batch_size=1000)
```

---

## Configuration Examples

### Development Environment

```python
# Use InMemory for fast iteration
store = InMemoryGraphStore()
await store.initialize()
```

### Testing Environment

```python
# Use SQLite for test isolation
store = SQLiteGraphStore(":memory:")  # In-memory for tests
await store.initialize()
```

### Staging Environment

```python
# Use PostgreSQL matching production
store = PostgresGraphStore(
    host=os.getenv('STAGING_DB_HOST'),
    ...
)
await store.initialize()
```

### Production Environment

```python
# Full production configuration
store = PostgresGraphStore(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT', '5432')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    min_pool_size=10,
    max_pool_size=50,
    enable_pgvector=True
)
await store.initialize()
```

---

## Backend-Specific Features

### InMemoryGraphStore

- ✅ Fastest for small graphs
- ✅ No setup required
- ✅ Full interface support
- ❌ No persistence
- ❌ Limited by RAM

### SQLiteGraphStore

- ✅ Single file database
- ✅ Easy deployment
- ✅ Full interface support
- ✅ ACID transactions
- ⚠️ Limited concurrency
- ⚠️ File locking

### PostgresGraphStore

- ✅ Production-grade
- ✅ High concurrency
- ✅ Advanced features (JSONB, pgvector)
- ✅ Connection pooling
- ✅ Read replicas support
- ⚠️ Requires PostgreSQL server

---

## Performance Comparison

| Operation | InMemory | SQLite | PostgreSQL |
|-----------|----------|--------|------------|
| add_entity (1K) | 10ms | 500ms | 300ms |
| get_entity | 0.01ms | 3ms | 2ms |
| find_paths (depth=5) | 10ms | 200ms | 50ms |
| Batch insert (10K) | 150ms | 5s | 300ms |

*Note: Actual performance depends on data size, hardware, and configuration*

---

## Best Practices

### 1. Choose the Right Backend

- **Development**: InMemoryGraphStore
- **Testing**: SQLiteGraphStore (in-memory)
- **Small Production**: SQLiteGraphStore
- **Large Production**: PostgresGraphStore

### 2. Connection Pooling (PostgreSQL)

```python
# Size pool based on expected load
# Rule of thumb: max_pool_size = (expected_concurrent_requests / 2)
store = PostgresGraphStore(
    ...,
    min_pool_size=5,   # Keep minimum connections warm
    max_pool_size=20   # Scale up for load
)
```

### 3. Environment-Specific Configuration

```python
import os

def get_graph_store():
    env = os.getenv('ENVIRONMENT', 'development')
    
    if env == 'production':
        return PostgresGraphStore(...)
    elif env == 'staging':
        return PostgresGraphStore(...)  # Staging DB
    elif env == 'testing':
        return SQLiteGraphStore(":memory:")
    else:
        return InMemoryGraphStore()
```

### 4. Graceful Degradation

```python
from aiecs.infrastructure.graph_storage.graceful_degradation import GracefulDegradationStore

primary = PostgresGraphStore(...)
store = GracefulDegradationStore(primary, enable_fallback=True)
await store.initialize()

# Automatically falls back to in-memory if PostgreSQL fails
```

---

## Troubleshooting

### SQLite: Database Locked

**Problem**: Multiple processes accessing SQLite
**Solution**: Use PostgreSQL for multi-process applications

### PostgreSQL: Connection Pool Exhausted

**Problem**: Too many concurrent connections
**Solution**: Increase `max_pool_size` or reduce concurrent requests

### InMemory: Out of Memory

**Problem**: Graph too large for RAM
**Solution**: Switch to SQLite or PostgreSQL

---

## Summary

- **InMemoryGraphStore**: Development and testing only
- **SQLiteGraphStore**: Small-medium production (< 1M entities)
- **PostgresGraphStore**: Large-scale production (1M+ entities)

Choose based on your use case, scale, and requirements!


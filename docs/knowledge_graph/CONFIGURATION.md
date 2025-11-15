# Knowledge Graph Configuration Guide

This guide explains how to configure the knowledge graph capabilities in AIECS.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Storage Backends](#storage-backends)
3. [Environment Variables](#environment-variables)
4. [Configuration Properties](#configuration-properties)
5. [Backend-Specific Configuration](#backend-specific-configuration)
6. [Query Configuration](#query-configuration)
7. [Cache Configuration](#cache-configuration)
8. [Validation](#validation)
9. [Examples](#examples)

## Quick Start

### Minimal Configuration (In-Memory)

No configuration needed! The default settings use in-memory storage:

```python
from aiecs.config import get_settings

settings = get_settings()
# Uses inmemory backend by default
```

### Development Configuration (SQLite)

Add to your `.env` file:

```bash
KG_STORAGE_BACKEND=sqlite
KG_SQLITE_DB_PATH=./storage/knowledge_graph.db
```

### Production Configuration (PostgreSQL)

Add to your `.env` file:

```bash
KG_STORAGE_BACKEND=postgresql
# Use main database (default)
# OR use a separate database:
KG_DB_HOST=localhost
KG_DB_PORT=5432
KG_DB_USER=kg_user
KG_DB_PASSWORD=your_password
KG_DB_NAME=aiecs_knowledge_graph
```

## Storage Backends

AIECS supports three storage backends for knowledge graphs:

### 1. In-Memory (Default)

- **Use Case**: Development, testing, small graphs
- **Pros**: Fast, no setup required
- **Cons**: Data lost on restart, limited by RAM
- **Max Nodes**: 100,000 (configurable)

```bash
KG_STORAGE_BACKEND=inmemory
```

### 2. SQLite

- **Use Case**: Development, embedded applications, file-based persistence
- **Pros**: Simple, portable, ACID transactions
- **Cons**: Single-writer, limited concurrency
- **Best For**: Single-user applications, up to ~1M nodes

```bash
KG_STORAGE_BACKEND=sqlite
KG_SQLITE_DB_PATH=./storage/knowledge_graph.db
```

### 3. PostgreSQL (Recommended for Production)

- **Use Case**: Production, multi-user, large-scale graphs
- **Pros**: Scalable, concurrent, ACID transactions, connection pooling
- **Cons**: Requires database setup
- **Best For**: Production applications, millions of nodes

```bash
KG_STORAGE_BACKEND=postgresql
```

## Environment Variables

### Core Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_STORAGE_BACKEND` | string | `inmemory` | Storage backend: `inmemory`, `sqlite`, or `postgresql` |

### SQLite Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_SQLITE_DB_PATH` | string | `./storage/knowledge_graph.db` | Path to SQLite database file |

### PostgreSQL Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_POSTGRES_URL` | string | `""` | PostgreSQL connection string (DSN) |
| `KG_DB_HOST` | string | `""` | Database host (falls back to main `DB_HOST`) |
| `KG_DB_PORT` | int | `5432` | Database port |
| `KG_DB_USER` | string | `""` | Database user (falls back to main `DB_USER`) |
| `KG_DB_PASSWORD` | string | `""` | Database password (falls back to main `DB_PASSWORD`) |
| `KG_DB_NAME` | string | `""` | Database name (default: `aiecs_knowledge_graph`) |
| `KG_MIN_POOL_SIZE` | int | `5` | Minimum connection pool size |
| `KG_MAX_POOL_SIZE` | int | `20` | Maximum connection pool size |
| `KG_ENABLE_PGVECTOR` | bool | `false` | Enable pgvector extension for optimized vector search |

### In-Memory Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_INMEMORY_MAX_NODES` | int | `100000` | Maximum number of nodes for in-memory storage |

### Query Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_DEFAULT_SEARCH_LIMIT` | int | `10` | Default number of results to return in searches |
| `KG_MAX_TRAVERSAL_DEPTH` | int | `5` | Maximum depth for graph traversal queries (1-10) |
| `KG_VECTOR_DIMENSION` | int | `1536` | Dimension of embedding vectors (OpenAI ada-002 default) |

### Cache Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KG_ENABLE_QUERY_CACHE` | bool | `true` | Enable caching of query results |
| `KG_CACHE_TTL_SECONDS` | int | `300` | Time-to-live for cached query results (seconds) |

## Configuration Properties

Access configuration programmatically:

```python
from aiecs.config import get_settings

settings = get_settings()

# Get database configuration for current backend
db_config = settings.kg_database_config
# Returns different config based on backend:
# - PostgreSQL: {"host": ..., "port": ..., "user": ..., etc.}
# - SQLite: {"db_path": ...}
# - In-memory: {"max_nodes": ...}

# Get query configuration
query_config = settings.kg_query_config
# Returns: {
#   "default_search_limit": 10,
#   "max_traversal_depth": 5,
#   "vector_dimension": 1536
# }

# Get cache configuration
cache_config = settings.kg_cache_config
# Returns: {
#   "enable_query_cache": True,
#   "cache_ttl_seconds": 300
# }
```

## Backend-Specific Configuration

### PostgreSQL: Using Main Database

By default, if you don't set KG-specific database parameters, the knowledge graph uses your main AIECS database:

```bash
# Main database config
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=aiecs

# Knowledge graph uses main DB
KG_STORAGE_BACKEND=postgresql
```

The knowledge graph creates its own tables (`graph_entities`, `graph_relations`) within the main database.

### PostgreSQL: Separate Database

For better isolation, use a separate database:

```bash
# Main database config
DB_HOST=localhost
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=aiecs

# Separate knowledge graph database
KG_STORAGE_BACKEND=postgresql
KG_DB_HOST=localhost
KG_DB_USER=kg_user
KG_DB_PASSWORD=kg_password
KG_DB_NAME=aiecs_knowledge_graph
```

### PostgreSQL: Cloud Database (Connection String)

For cloud databases (e.g., Google Cloud SQL, AWS RDS):

```bash
KG_STORAGE_BACKEND=postgresql
KG_POSTGRES_URL=postgresql://user:password@host:5432/dbname?sslmode=require
```

### PostgreSQL: Connection Pooling

Optimize for your workload:

```bash
# For high-concurrency applications
KG_MIN_POOL_SIZE=10
KG_MAX_POOL_SIZE=50

# For low-concurrency applications
KG_MIN_POOL_SIZE=2
KG_MAX_POOL_SIZE=10
```

### PostgreSQL: pgvector Extension

Enable optimized vector search (requires pgvector installed):

```bash
KG_ENABLE_PGVECTOR=true
```

**Prerequisites**:
1. Install pgvector extension in your PostgreSQL database
2. The extension will be automatically used for vector similarity search

### SQLite: Memory vs. File

```bash
# File-based persistence (recommended)
KG_SQLITE_DB_PATH=./storage/knowledge_graph.db

# In-memory SQLite (no persistence)
KG_SQLITE_DB_PATH=:memory:
```

## Query Configuration

### Search Limits

Control the number of results returned:

```bash
# Return more results (e.g., for comprehensive search)
KG_DEFAULT_SEARCH_LIMIT=50

# Return fewer results (e.g., for quick queries)
KG_DEFAULT_SEARCH_LIMIT=5
```

### Traversal Depth

Control how deep graph traversals can go:

```bash
# Shallow traversals (faster, less comprehensive)
KG_MAX_TRAVERSAL_DEPTH=3

# Deep traversals (slower, more comprehensive)
KG_MAX_TRAVERSAL_DEPTH=7
```

**Warning**: Values > 10 may cause performance issues.

### Vector Dimensions

Match your embedding model:

```bash
# OpenAI ada-002 (default)
KG_VECTOR_DIMENSION=1536

# OpenAI text-embedding-3-small
KG_VECTOR_DIMENSION=1536

# OpenAI text-embedding-3-large
KG_VECTOR_DIMENSION=3072

# Sentence Transformers (various)
KG_VECTOR_DIMENSION=384  # all-MiniLM-L6-v2
KG_VECTOR_DIMENSION=768  # all-mpnet-base-v2
```

## Cache Configuration

### Enable/Disable Caching

```bash
# Enable caching (recommended for production)
KG_ENABLE_QUERY_CACHE=true

# Disable caching (for development/debugging)
KG_ENABLE_QUERY_CACHE=false
```

### Cache TTL

Control how long cached results remain valid:

```bash
# Short TTL (frequently changing data)
KG_CACHE_TTL_SECONDS=60

# Long TTL (stable data)
KG_CACHE_TTL_SECONDS=3600
```

## Validation

### Automatic Validation

Configuration is automatically validated when settings are loaded:

```python
from aiecs.config import get_settings

try:
    settings = get_settings()
except ValueError as e:
    print(f"Configuration error: {e}")
```

### Manual Validation

Validate configuration for specific operations:

```python
from aiecs.config import validate_required_settings

# Validate knowledge graph configuration
try:
    validate_required_settings("knowledge_graph")
    print("Knowledge graph configuration is valid")
except ValueError as e:
    print(f"Missing configuration: {e}")
```

### Validation Rules

1. **KG_STORAGE_BACKEND**: Must be `inmemory`, `sqlite`, or `postgresql`
2. **KG_SQLITE_DB_PATH**: Parent directory is automatically created
3. **KG_MAX_TRAVERSAL_DEPTH**: Must be ≥ 1; warning if > 10
4. **KG_VECTOR_DIMENSION**: Must be ≥ 1; warning if not a common dimension
5. **PostgreSQL**: At least one of KG_POSTGRES_URL, KG_DB_HOST, or main DB_PASSWORD must be set

## Examples

### Example 1: Development Setup (SQLite)

`.env`:
```bash
# SQLite for development
KG_STORAGE_BACKEND=sqlite
KG_SQLITE_DB_PATH=./dev_knowledge_graph.db

# Disable caching for development
KG_ENABLE_QUERY_CACHE=false

# More verbose search
KG_DEFAULT_SEARCH_LIMIT=20
```

### Example 2: Production Setup (PostgreSQL)

`.env`:
```bash
# PostgreSQL for production
KG_STORAGE_BACKEND=postgresql
KG_POSTGRES_URL=postgresql://kg_user:password@db.example.com:5432/aiecs_kg?sslmode=require

# Optimize connection pooling
KG_MIN_POOL_SIZE=10
KG_MAX_POOL_SIZE=50

# Enable pgvector
KG_ENABLE_PGVECTOR=true

# Production query settings
KG_DEFAULT_SEARCH_LIMIT=10
KG_MAX_TRAVERSAL_DEPTH=5

# Enable caching
KG_ENABLE_QUERY_CACHE=true
KG_CACHE_TTL_SECONDS=600
```

### Example 3: Testing Setup (In-Memory)

`.env.test`:
```bash
# In-memory for fast tests
KG_STORAGE_BACKEND=inmemory
KG_INMEMORY_MAX_NODES=10000

# Disable caching for predictable tests
KG_ENABLE_QUERY_CACHE=false
```

### Example 4: Programmatic Configuration

```python
from aiecs.infrastructure.graph_storage import (
    InMemoryGraphStore,
    SQLiteGraphStore,
    PostgresGraphStore
)
from aiecs.config import get_settings

settings = get_settings()

# Create store based on backend configuration
if settings.kg_storage_backend == "inmemory":
    store = InMemoryGraphStore()
elif settings.kg_storage_backend == "sqlite":
    config = settings.kg_database_config
    store = SQLiteGraphStore(db_path=config["db_path"])
elif settings.kg_storage_backend == "postgresql":
    config = settings.kg_database_config
    store = PostgresGraphStore(**config)

await store.initialize()

# Use the store
# ...

await store.close()
```

### Example 5: Multi-Environment Setup

Use different `.env` files for different environments:

**`.env.development`**:
```bash
KG_STORAGE_BACKEND=sqlite
KG_SQLITE_DB_PATH=./dev_kg.db
```

**`.env.staging`**:
```bash
KG_STORAGE_BACKEND=postgresql
KG_POSTGRES_URL=postgresql://user:pass@staging-db:5432/aiecs_kg
```

**`.env.production`**:
```bash
KG_STORAGE_BACKEND=postgresql
KG_POSTGRES_URL=postgresql://user:pass@prod-db:5432/aiecs_kg
KG_MIN_POOL_SIZE=20
KG_MAX_POOL_SIZE=100
KG_ENABLE_PGVECTOR=true
```

Load the appropriate file:
```bash
# Development
export ENV_FILE=.env.development
python -m aiecs

# Staging
export ENV_FILE=.env.staging
python -m aiecs

# Production
export ENV_FILE=.env.production
python -m aiecs
```

## Troubleshooting

### Issue: PostgreSQL connection fails

**Solution**: Check your connection parameters:
```python
from aiecs.config import get_settings

settings = get_settings()
print(settings.kg_database_config)
# Verify host, port, user, password, database are correct
```

### Issue: SQLite file not found

**Solution**: The parent directory is automatically created, but ensure the path is writable:
```bash
mkdir -p ./storage
chmod 755 ./storage
```

### Issue: Vector search returns no results

**Solution**: Check vector dimensions match your embeddings:
```bash
# If using OpenAI ada-002
KG_VECTOR_DIMENSION=1536

# If using different model, adjust accordingly
```

### Issue: Queries are slow

**Solution**: Optimize configuration:
```bash
# Reduce traversal depth
KG_MAX_TRAVERSAL_DEPTH=3

# Enable caching
KG_ENABLE_QUERY_CACHE=true

# For PostgreSQL: enable pgvector
KG_ENABLE_PGVECTOR=true
```

## Best Practices

1. **Use PostgreSQL for production**: Scalable, concurrent, reliable
2. **Use SQLite for development**: Simple, portable, fast iteration
3. **Use in-memory for testing**: Fast, isolated, reproducible
4. **Enable caching in production**: Improves performance
5. **Match vector dimensions to your embedding model**: Prevents dimension mismatches
6. **Set reasonable traversal depth**: Balance comprehensiveness vs. performance
7. **Use separate database for KG in production**: Better isolation and resource management
8. **Monitor connection pool usage**: Adjust min/max based on workload
9. **Enable pgvector for large-scale vector search**: Significantly faster than brute-force

## Migration

When changing backends, use the migration tools:

```python
from aiecs.infrastructure.graph_storage.migration import migrate_sqlite_to_postgres

# Migrate from SQLite to PostgreSQL
await migrate_sqlite_to_postgres(
    sqlite_path="./dev_kg.db",
    postgres_config=None,  # Uses config from settings
    batch_size=1000,
    show_progress=True
)
```

See `docs/knowledge_graph/MIGRATION.md` for more details.

## See Also

- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Examples](examples/)
- [Migration Guide](MIGRATION.md)


# Knowledge Graph Configuration Guide

## Overview

This guide covers all configuration options for the AIECS Knowledge Graph system, including storage backends, feature flags, and performance tuning.

## Table of Contents

1. [Storage Configuration](#storage-configuration)
2. [Feature Flags](#feature-flags)
3. [Knowledge Fusion Configuration](#knowledge-fusion-configuration)
4. [Reranking Configuration](#reranking-configuration)
5. [Cache Configuration](#cache-configuration)
6. [Query Optimization](#query-optimization)
7. [Environment Variables](#environment-variables)
8. [Configuration Examples](#configuration-examples)

## Storage Configuration

### Backend Selection

Choose the appropriate storage backend based on your use case:

```bash
# In-memory (default) - Fast, no persistence
KG_STORAGE_BACKEND=inmemory

# SQLite - File-based persistence, single-user
KG_STORAGE_BACKEND=sqlite

# PostgreSQL - Production-ready, multi-user
KG_STORAGE_BACKEND=postgresql
```

### In-Memory Configuration

```bash
# Maximum number of nodes (default: 100000)
KG_INMEMORY_MAX_NODES=100000
```

**Use Cases:**
- Development and testing
- Temporary graphs
- Small to medium datasets (<100K nodes)

### SQLite Configuration

```bash
# Database file path (default: ./storage/knowledge_graph.db)
KG_SQLITE_DB_PATH=./storage/knowledge_graph.db
```

**Use Cases:**
- Single-user applications
- File-based persistence
- Medium datasets (<1M nodes)

### PostgreSQL Configuration

```bash
# PostgreSQL connection settings
KG_POSTGRES_HOST=localhost
KG_POSTGRES_PORT=5432
KG_POSTGRES_USER=postgres
KG_POSTGRES_PASSWORD=your_password
KG_POSTGRES_DATABASE=knowledge_graph

# Connection pool settings
KG_MIN_POOL_SIZE=5
KG_MAX_POOL_SIZE=20

# Enable pgvector for optimized vector search (requires pgvector extension)
KG_ENABLE_PGVECTOR=false
```

**Use Cases:**
- Production deployments
- Multi-user applications
- Large datasets (>1M nodes)
- High concurrency

## Feature Flags

Control which features are enabled in your deployment:

### Runnable Pattern

```bash
# Enable Runnable pattern for composable operations (default: true)
KG_ENABLE_RUNNABLE_PATTERN=true
```

**Benefits:**
- Composable graph operations
- Pipeline chaining
- Async/sync compatibility

**When to disable:**
- Legacy code compatibility
- Simplified debugging

### Knowledge Fusion

```bash
# Enable cross-document entity merging (default: true)
KG_ENABLE_KNOWLEDGE_FUSION=true
```

**Benefits:**
- Merge duplicate entities across documents
- Resolve property conflicts
- Track provenance

**When to disable:**
- Single-document graphs
- No duplicate entities expected

### Result Reranking

```bash
# Enable search result reranking (default: true)
KG_ENABLE_RERANKING=true
```

**Benefits:**
- Improved search relevance
- Multiple ranking signals
- Better precision

**When to disable:**
- Performance-critical applications
- Simple search requirements

### Logical Queries

```bash
# Enable logical query parsing (default: true)
KG_ENABLE_LOGICAL_QUERIES=true
```

**Benefits:**
- Natural language to structured queries
- Query validation
- Execution planning

**When to disable:**
- Simple query patterns only
- No NLP requirements

### Structured Data Import

```bash
# Enable CSV/JSON import (default: true)
KG_ENABLE_STRUCTURED_IMPORT=true
```

**Benefits:**
- Import from CSV/JSON files
- Schema mapping
- Bulk data loading

**When to disable:**
- Text-only extraction
- No structured data sources

## Knowledge Fusion Configuration

### Similarity Threshold

```bash
# Similarity threshold for entity fusion (0.0-1.0, default: 0.85)
KG_FUSION_SIMILARITY_THRESHOLD=0.85
```

**Guidelines:**
- **0.95-1.0**: Very strict, only near-identical entities
- **0.85-0.95**: Balanced (recommended)
- **0.70-0.85**: Lenient, more merges
- **<0.70**: Very lenient, risk of false positives

### Conflict Resolution Strategy

```bash
# Strategy for resolving property conflicts (default: most_complete)
KG_FUSION_CONFLICT_RESOLUTION=most_complete
```

**Available Strategies:**

1. **most_complete**: Prefer non-empty, longer values (default)
   - Best for: General use, data enrichment
   
2. **most_recent**: Prefer values from most recent timestamp
   - Best for: Time-sensitive data, news articles
   
3. **most_confident**: Prefer values from most confident sources
   - Best for: Weighted sources, quality-ranked data
   
4. **longest**: Prefer longest string values
   - Best for: Descriptions, detailed text
   
5. **keep_all**: Keep all conflicting values as a list
   - Best for: Preserving all information, manual review

## Reranking Configuration

### Default Strategy

```bash
# Default reranking strategy (default: hybrid)
KG_RERANKING_DEFAULT_STRATEGY=hybrid
```

**Available Strategies:**

1. **text**: BM25-based text similarity
   - Fast, keyword-focused
   
2. **semantic**: Deep semantic similarity
   - Slower, meaning-focused
   
3. **structural**: Graph importance signals
   - Graph-aware, centrality-based
   
4. **hybrid**: Combines all signals (recommended)
   - Best results, slightly slower

### Top-K Configuration

```bash
# Number of results to fetch before reranking (default: 100)
KG_RERANKING_TOP_K=100
```

**Guidelines:**
- Higher values: Better recall, slower
- Lower values: Faster, may miss relevant results
- Recommended: 2-10x your final result count

## Cache Configuration

### Query Cache

```bash
# Enable query result caching (default: true)
KG_ENABLE_QUERY_CACHE=true

# Cache TTL in seconds (default: 300 = 5 minutes)
KG_CACHE_TTL_SECONDS=300
```

**Benefits:**
- Faster repeated queries
- Reduced database load
- Better performance

**When to disable:**
- Real-time data requirements
- Frequently changing graphs

### Schema Cache

```bash
# Enable schema caching (default: true)
KG_ENABLE_SCHEMA_CACHE=true

# Schema cache TTL in seconds (default: 3600 = 1 hour)
KG_SCHEMA_CACHE_TTL_SECONDS=3600
```

**Benefits:**
- Faster schema operations
- Reduced metadata queries
- Better type inference

**When to disable:**
- Frequently changing schemas
- Development/testing

## Query Optimization

### Enable Optimization

```bash
# Enable query optimization (default: true)
KG_ENABLE_QUERY_OPTIMIZATION=true
```

**Benefits:**
- Faster query execution
- Better resource utilization
- Automatic query planning

### Optimization Strategy

```bash
# Optimization strategy (default: balanced)
KG_QUERY_OPTIMIZATION_STRATEGY=balanced
```

**Available Strategies:**

1. **cost**: Minimize computational cost
   - Best for: Resource-constrained environments

2. **latency**: Minimize query latency
   - Best for: Real-time applications

3. **balanced**: Balance cost and latency (recommended)
   - Best for: General use

## Environment Variables

### Complete Reference

```bash
# =====================================
# Storage Configuration
# =====================================
KG_STORAGE_BACKEND=inmemory
KG_SQLITE_DB_PATH=./storage/knowledge_graph.db
KG_POSTGRES_HOST=localhost
KG_POSTGRES_PORT=5432
KG_POSTGRES_USER=postgres
KG_POSTGRES_PASSWORD=your_password
KG_POSTGRES_DATABASE=knowledge_graph
KG_MIN_POOL_SIZE=5
KG_MAX_POOL_SIZE=20
KG_ENABLE_PGVECTOR=false
KG_INMEMORY_MAX_NODES=100000

# =====================================
# Vector and Query Configuration
# =====================================
KG_VECTOR_DIMENSION=1536
KG_DEFAULT_SEARCH_LIMIT=10
KG_MAX_TRAVERSAL_DEPTH=5

# =====================================
# Cache Configuration
# =====================================
KG_ENABLE_QUERY_CACHE=true
KG_CACHE_TTL_SECONDS=300
KG_ENABLE_SCHEMA_CACHE=true
KG_SCHEMA_CACHE_TTL_SECONDS=3600

# =====================================
# Feature Flags
# =====================================
KG_ENABLE_RUNNABLE_PATTERN=true
KG_ENABLE_KNOWLEDGE_FUSION=true
KG_ENABLE_RERANKING=true
KG_ENABLE_LOGICAL_QUERIES=true
KG_ENABLE_STRUCTURED_IMPORT=true

# =====================================
# Knowledge Fusion Configuration
# =====================================
KG_FUSION_SIMILARITY_THRESHOLD=0.85
KG_FUSION_CONFLICT_RESOLUTION=most_complete

# =====================================
# Reranking Configuration
# =====================================
KG_RERANKING_DEFAULT_STRATEGY=hybrid
KG_RERANKING_TOP_K=100

# =====================================
# Query Optimization
# =====================================
KG_ENABLE_QUERY_OPTIMIZATION=true
KG_QUERY_OPTIMIZATION_STRATEGY=balanced
```

## Configuration Examples

### Development Setup

Fast iteration with in-memory storage:

```bash
# .env.development
KG_STORAGE_BACKEND=inmemory
KG_INMEMORY_MAX_NODES=50000
KG_ENABLE_QUERY_CACHE=false
KG_ENABLE_SCHEMA_CACHE=false
KG_ENABLE_QUERY_OPTIMIZATION=false
```

### Testing Setup

File-based persistence for reproducible tests:

```bash
# .env.test
KG_STORAGE_BACKEND=sqlite
KG_SQLITE_DB_PATH=./test_data/test_graph.db
KG_ENABLE_QUERY_CACHE=true
KG_CACHE_TTL_SECONDS=60
KG_ENABLE_QUERY_OPTIMIZATION=true
```

### Production Setup

PostgreSQL with all optimizations:

```bash
# .env.production
KG_STORAGE_BACKEND=postgresql
KG_POSTGRES_HOST=db.example.com
KG_POSTGRES_PORT=5432
KG_POSTGRES_USER=kg_user
KG_POSTGRES_PASSWORD=secure_password
KG_POSTGRES_DATABASE=knowledge_graph
KG_MIN_POOL_SIZE=10
KG_MAX_POOL_SIZE=50
KG_ENABLE_PGVECTOR=true

# Enable all features
KG_ENABLE_RUNNABLE_PATTERN=true
KG_ENABLE_KNOWLEDGE_FUSION=true
KG_ENABLE_RERANKING=true
KG_ENABLE_LOGICAL_QUERIES=true
KG_ENABLE_STRUCTURED_IMPORT=true

# Optimize for production
KG_ENABLE_QUERY_CACHE=true
KG_CACHE_TTL_SECONDS=600
KG_ENABLE_SCHEMA_CACHE=true
KG_SCHEMA_CACHE_TTL_SECONDS=7200
KG_ENABLE_QUERY_OPTIMIZATION=true
KG_QUERY_OPTIMIZATION_STRATEGY=balanced

# Reranking for best results
KG_RERANKING_DEFAULT_STRATEGY=hybrid
KG_RERANKING_TOP_K=200

# Fusion for data quality
KG_FUSION_SIMILARITY_THRESHOLD=0.85
KG_FUSION_CONFLICT_RESOLUTION=most_complete
```

### High-Performance Setup

Optimized for speed:

```bash
# .env.performance
KG_STORAGE_BACKEND=postgresql
KG_ENABLE_PGVECTOR=true
KG_MAX_POOL_SIZE=100

# Aggressive caching
KG_ENABLE_QUERY_CACHE=true
KG_CACHE_TTL_SECONDS=1800
KG_ENABLE_SCHEMA_CACHE=true
KG_SCHEMA_CACHE_TTL_SECONDS=14400

# Latency optimization
KG_ENABLE_QUERY_OPTIMIZATION=true
KG_QUERY_OPTIMIZATION_STRATEGY=latency

# Disable expensive features
KG_ENABLE_RERANKING=false
KG_ENABLE_KNOWLEDGE_FUSION=false
```

### Data Quality Setup

Optimized for accuracy:

```bash
# .env.quality
KG_STORAGE_BACKEND=postgresql

# Enable all quality features
KG_ENABLE_KNOWLEDGE_FUSION=true
KG_ENABLE_RERANKING=true
KG_ENABLE_LOGICAL_QUERIES=true

# Strict fusion
KG_FUSION_SIMILARITY_THRESHOLD=0.90
KG_FUSION_CONFLICT_RESOLUTION=most_confident

# Best reranking
KG_RERANKING_DEFAULT_STRATEGY=hybrid
KG_RERANKING_TOP_K=500

# Balanced optimization
KG_QUERY_OPTIMIZATION_STRATEGY=balanced
```

## Best Practices

### 1. Start Simple

Begin with default settings and adjust based on your needs:

```bash
# Minimal configuration
KG_STORAGE_BACKEND=inmemory
```

### 2. Monitor Performance

Track key metrics:
- Query latency
- Cache hit rate
- Fusion merge rate
- Reranking impact

### 3. Tune Gradually

Adjust one parameter at a time:
1. Choose storage backend
2. Enable/disable features
3. Tune cache settings
4. Optimize queries

### 4. Environment-Specific Configs

Use different configurations for different environments:
- `.env.development` - Fast iteration
- `.env.test` - Reproducible tests
- `.env.staging` - Production-like
- `.env.production` - Optimized for scale

### 5. Security Considerations

- Never commit `.env` files to version control
- Use strong passwords for PostgreSQL
- Restrict database access
- Enable SSL for production databases

## Troubleshooting

### Slow Queries

**Problem**: Queries are taking too long

**Solutions:**
1. Enable query optimization: `KG_ENABLE_QUERY_OPTIMIZATION=true`
2. Increase cache TTL: `KG_CACHE_TTL_SECONDS=600`
3. Use PostgreSQL with pgvector: `KG_ENABLE_PGVECTOR=true`
4. Reduce reranking top-K: `KG_RERANKING_TOP_K=50`

### High Memory Usage

**Problem**: Application using too much memory

**Solutions:**
1. Switch to SQLite or PostgreSQL: `KG_STORAGE_BACKEND=sqlite`
2. Reduce in-memory max nodes: `KG_INMEMORY_MAX_NODES=50000`
3. Disable caching: `KG_ENABLE_QUERY_CACHE=false`
4. Reduce cache TTL: `KG_CACHE_TTL_SECONDS=60`

### Too Many Duplicate Entities

**Problem**: Fusion is merging too many entities

**Solutions:**
1. Increase similarity threshold: `KG_FUSION_SIMILARITY_THRESHOLD=0.90`
2. Change conflict resolution: `KG_FUSION_CONFLICT_RESOLUTION=keep_all`
3. Review entity extraction quality

### Poor Search Results

**Problem**: Search results are not relevant

**Solutions:**
1. Enable reranking: `KG_ENABLE_RERANKING=true`
2. Use hybrid strategy: `KG_RERANKING_DEFAULT_STRATEGY=hybrid`
3. Increase reranking top-K: `KG_RERANKING_TOP_K=200`
4. Adjust vector dimension: `KG_VECTOR_DIMENSION=1536`

## See Also

- [Storage Backend Guide](../../developer/knowledge_graph/storage/SQLITE_BACKEND.md)
- [Performance Guide](./performance/PERFORMANCE_GUIDE.md)
- [Reranking Strategies Guide](./reasoning/reranking-strategies-guide.md)
- [Schema Caching Guide](./reasoning/schema-caching-guide.md)
- [Production Deployment](./deployment/PRODUCTION_DEPLOYMENT.md)



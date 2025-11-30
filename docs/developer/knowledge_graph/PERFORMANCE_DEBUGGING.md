# Performance Debugging Guide

## Overview

This guide provides tools and techniques for debugging performance issues in the AIECS Knowledge Graph system.

## Table of Contents

1. [Query Profiling](#query-profiling)
2. [Performance Metrics](#performance-metrics)
3. [Query Plan Analysis](#query-plan-analysis)
4. [Common Performance Issues](#common-performance-issues)
5. [Debugging Tools](#debugging-tools)
6. [Best Practices](#best-practices)

## Query Profiling

### Using QueryProfiler

The `QueryProfiler` provides detailed timing information for query execution.

```python
from aiecs.application.knowledge_graph.profiling import QueryProfiler

# Initialize profiler
profiler = QueryProfiler()

# Profile a query
async with profiler.profile("search_001", "vector_search") as profile:
    # Step 1: Embedding lookup
    async with profiler.step(profile, "embedding_lookup"):
        embedding = await get_embedding(query)
    
    # Step 2: Vector search
    async with profiler.step(profile, "vector_search"):
        results = await store.vector_search(embedding, max_results=20)
    
    # Step 3: Reranking
    async with profiler.step(profile, "reranking"):
        reranked = await reranker.rerank(query, results, top_k=10)

# Get profile data
profile_data = profiler.get_profile("search_001")
print(f"Total duration: {profile_data.duration_ms:.2f}ms")

for step in profile_data.steps:
    print(f"  {step['name']}: {step['duration_ms']:.2f}ms")
```

**Output:**
```
Total duration: 245.32ms
  embedding_lookup: 15.23ms
  vector_search: 180.45ms
  reranking: 49.64ms
```

### Profiling Statistics

Get aggregate statistics across multiple queries:

```python
# Get profiling stats
stats = profiler.get_stats()

print(f"Total queries: {stats['total_queries']}")
print(f"Average duration: {stats['avg_duration_ms']:.2f}ms")
print(f"Min duration: {stats['min_duration_ms']:.2f}ms")
print(f"Max duration: {stats['max_duration_ms']:.2f}ms")

# Query type breakdown
for query_type, count in stats['query_types'].items():
    print(f"  {query_type}: {count} queries")
```

## Performance Metrics

### Using MetricsCollector

Track detailed performance metrics:

```python
from aiecs.infrastructure.graph_storage.metrics import MetricsCollector

collector = MetricsCollector()

# Record latency
collector.record_latency("get_entity", 12.5)
collector.record_latency("get_neighbors", 45.2)

# Record cache hits/misses
collector.record_cache_hit()
collector.record_cache_miss()

# Record errors
collector.record_error("connection_timeout")

# Get metrics
metrics = collector.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
print(f"Average latency: {metrics['avg_latency']:.2f}ms")
```

### Metric Types

**Latency Metrics:**
- `get_entity` - Entity retrieval time
- `get_neighbors` - Neighbor lookup time
- `vector_search` - Vector search time
- `graph_traverse` - Graph traversal time

**Cache Metrics:**
- `cache_hits` - Number of cache hits
- `cache_misses` - Number of cache misses
- `cache_hit_rate` - Hit rate percentage

**Error Metrics:**
- `connection_errors` - Connection failures
- `timeout_errors` - Operation timeouts
- `validation_errors` - Data validation failures

## Query Plan Analysis

### Visualizing Query Plans

Use the `QueryPlanVisualizer` to understand query execution:

```python
from aiecs.application.knowledge_graph.profiling import QueryPlanVisualizer
from aiecs.application.knowledge_graph.reasoning.query_optimizer import QueryOptimizer

# Create query plan
optimizer = QueryOptimizer()
plan = optimizer.create_plan(query)

# Visualize plan
visualizer = QueryPlanVisualizer()
plan_viz = visualizer.visualize_plan(plan, show_costs=True)
print(plan_viz)
```

**Output:**
```
============================================================
QUERY PLAN
============================================================
Total Estimated Cost: 650.00

Step 1: SCAN
  Entity Type: Person
  Estimated Cost: 100.00
  Filters: 2
    - age > 25
    - city = 'San Francisco'

Step 2: JOIN
  Entity Type: Company
  Estimated Cost: 500.00

Step 3: FILTER
  Entity Type: Person
  Estimated Cost: 50.00

============================================================
```

### Visualizing Execution Profiles

```python
# Visualize execution profile
profile_viz = visualizer.visualize_profile(profile_data, show_steps=True)
print(profile_viz)
```

**Output:**
```
============================================================
QUERY EXECUTION PROFILE
============================================================
Query ID: search_001
Query Type: vector_search
Total Duration: 245.32ms

Execution Steps:
------------------------------------------------------------
1. embedding_lookup
   Duration: 15.23ms (6.2%)
   [███                                               ]

2. vector_search
   Duration: 180.45ms (73.6%)
   [████████████████████████████████████              ]

3. reranking
   Duration: 49.64ms (20.2%)
   [██████████                                        ]

============================================================
```

### Comparing Queries

Compare multiple query executions:

```python
profiles = [
    profiler.get_profile("search_001"),
    profiler.get_profile("search_002"),
    profiler.get_profile("search_003")
]

comparison = visualizer.visualize_comparison(profiles)
print(comparison)
```

## Common Performance Issues

### Issue 1: Slow Vector Search

**Symptoms:**
- Vector search takes >200ms
- High latency for similarity queries

**Diagnosis:**
```python
async with profiler.profile("debug_search", "vector_search") as profile:
    async with profiler.step(profile, "vector_search"):
        results = await store.vector_search(embedding, max_results=100)

# Check if vector search is the bottleneck
profile_data = profiler.get_profile("debug_search")
for step in profile_data.steps:
    if step['duration_ms'] > 100:
        print(f"Slow step: {step['name']} - {step['duration_ms']:.2f}ms")
```

**Solutions:**
1. Enable pgvector for PostgreSQL
2. Reduce max_results
3. Add vector indexes
4. Use approximate nearest neighbor (ANN)

### Issue 2: Cache Misses

**Symptoms:**
- Low cache hit rate (<50%)
- Repeated queries are slow

**Diagnosis:**
```python
metrics = collector.get_metrics()
print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")

if metrics['cache_hit_rate'] < 0.5:
    print("Low cache hit rate detected!")
    print(f"Hits: {metrics['cache_hits']}")
    print(f"Misses: {metrics['cache_misses']}")
```

**Solutions:**
1. Increase cache TTL
2. Increase cache size
3. Enable Redis for distributed caching
4. Review cache invalidation strategy

### Issue 3: Slow Reranking

**Symptoms:**
- Reranking takes >300ms
- High overhead for search

**Diagnosis:**
```python
async with profiler.step(profile, "reranking", {"strategy": "hybrid"}):
    results = await reranker.rerank(query, entities, top_k=20)

# Check reranking time
for step in profile.steps:
    if step['name'] == 'reranking':
        print(f"Reranking: {step['duration_ms']:.2f}ms")
        print(f"Strategy: {step['metadata']['strategy']}")
```

**Solutions:**
1. Use faster strategy (text instead of hybrid)
2. Reduce top_k
3. Reduce number of entities to rerank
4. Disable reranking for simple queries

## Debugging Tools

### 1. Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("aiecs.application.knowledge_graph")
logger.setLevel(logging.DEBUG)
```

### 2. Profile Decorator

Create a decorator for automatic profiling:

```python
from functools import wraps
import time

def profile_async(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = await func(*args, **kwargs)
        end = time.perf_counter()
        duration_ms = (end - start) * 1000
        print(f"{func.__name__}: {duration_ms:.2f}ms")
        return result
    return wrapper

@profile_async
async def my_query():
    return await store.get_entity("e1")
```

### 3. Memory Profiling

Track memory usage:

```python
import tracemalloc

tracemalloc.start()

# Your code here
await store.vector_search(embedding, max_results=1000)

current, peak = tracemalloc.get_traced_memory()
print(f"Current memory: {current / 1024 / 1024:.2f} MB")
print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")

tracemalloc.stop()
```

## Best Practices

### 1. Profile in Production-Like Environment

- Use realistic data volumes
- Test with production query patterns
- Include network latency

### 2. Establish Baselines

```python
# Record baseline performance
baseline_stats = profiler.get_stats()

# After optimization
optimized_stats = profiler.get_stats()

improvement = (baseline_stats['avg_duration_ms'] - optimized_stats['avg_duration_ms']) / baseline_stats['avg_duration_ms']
print(f"Performance improvement: {improvement:.1%}")
```

### 3. Monitor Continuously

- Set up alerts for slow queries (>500ms)
- Track cache hit rates
- Monitor error rates

### 4. Use Sampling for High-Volume Systems

```python
import random

# Profile 10% of queries
if random.random() < 0.1:
    async with profiler.profile(query_id, query_type):
        result = await execute_query()
```

## See Also

- [Performance Guide](./PERFORMANCE_GUIDE.md)
- [Configuration Guide](./CONFIGURATION_GUIDE.md)
- [Troubleshooting Guide](./TROUBLESHOOTING.md)


# Knowledge Retrieval Metrics and Monitoring

This guide documents the metrics and monitoring capabilities for knowledge retrieval in `KnowledgeAwareAgent`.

## Table of Contents

1. [Overview](#overview)
2. [Available Metrics](#available-metrics)
3. [Accessing Metrics](#accessing-metrics)
4. [Monitoring Patterns](#monitoring-patterns)
5. [Performance Analysis](#performance-analysis)
6. [Examples](#examples)

---

## Overview

The `KnowledgeAwareAgent` tracks comprehensive metrics for knowledge retrieval operations, including:

- Query counts and performance
- Cache hit/miss rates
- Strategy usage statistics
- Entity extraction metrics
- Relationship traversal metrics

All metrics are exposed through the `GraphMetrics` model and can be accessed via `agent.get_metrics()`.

---

## Available Metrics

### Query Metrics

#### `total_graph_queries`
**Type**: `int`  
**Description**: Total number of graph queries executed  
**Incremented**: On each knowledge retrieval call

#### `total_entities_retrieved`
**Type**: `int`  
**Description**: Total number of entities retrieved across all queries  
**Incremented**: Sum of entities returned from each query

#### `total_relationships_traversed`
**Type**: `int`  
**Description**: Total number of relationships traversed during graph searches  
**Incremented**: During graph traversal operations

---

### Performance Metrics

#### `average_graph_query_time`
**Type**: `float`  
**Description**: Average graph query time in seconds  
**Calculated**: `total_graph_query_time / total_graph_queries`

#### `total_graph_query_time`
**Type**: `float`  
**Description**: Cumulative time spent on graph queries in seconds

#### `min_graph_query_time`
**Type**: `Optional[float]`  
**Description**: Minimum graph query time in seconds

#### `max_graph_query_time`
**Type**: `Optional[float]`  
**Description**: Maximum graph query time in seconds

---

### Cache Metrics

#### `cache_hits`
**Type**: `int`  
**Description**: Number of cache hits  
**Incremented**: When cached knowledge is returned

#### `cache_misses`
**Type**: `int`  
**Description**: Number of cache misses  
**Incremented**: When knowledge is retrieved from graph store

#### `cache_hit_rate`
**Type**: `float`  
**Description**: Cache hit rate (0.0 to 1.0)  
**Calculated**: `cache_hits / (cache_hits + cache_misses)`

**Example**: `0.75` means 75% of queries hit the cache

---

### Strategy Metrics

#### `vector_search_count`
**Type**: `int`  
**Description**: Number of vector-only searches performed

#### `graph_search_count`
**Type**: `int`  
**Description**: Number of graph-only searches performed

#### `hybrid_search_count`
**Type**: `int`  
**Description**: Number of hybrid searches performed

---

### Entity Extraction Metrics

#### `entity_extraction_count`
**Type**: `int`  
**Description**: Number of entity extractions performed

#### `average_extraction_time`
**Type**: `float`  
**Description**: Average entity extraction time in seconds  
**Calculated**: `total_extraction_time / entity_extraction_count`

#### `total_extraction_time`
**Type**: `float`  
**Description**: Cumulative time spent on entity extraction

---

## Accessing Metrics

### Method 1: Via `get_metrics()`

```python
# Get all agent metrics (includes graph metrics)
metrics = agent.get_metrics()

# Access graph metrics
graph_metrics = metrics.graph_metrics

print(f"Total queries: {graph_metrics.total_graph_queries}")
print(f"Cache hit rate: {graph_metrics.cache_hit_rate:.2%}")
print(f"Average query time: {graph_metrics.average_graph_query_time:.3f}s")
```

### Method 2: Direct Access

```python
# Access graph metrics directly
graph_metrics = agent._graph_metrics

print(f"Vector searches: {graph_metrics.vector_search_count}")
print(f"Graph searches: {graph_metrics.graph_search_count}")
print(f"Hybrid searches: {graph_metrics.hybrid_search_count}")
```

### Method 3: Via `get_graph_metrics()`

```python
# Get graph metrics explicitly
graph_metrics = agent.get_graph_metrics()

print(f"Entities retrieved: {graph_metrics.total_entities_retrieved}")
print(f"Relationships traversed: {graph_metrics.total_relationships_traversed}")
```

---

## Monitoring Patterns

### Pattern 1: Basic Metrics Tracking

```python
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore

# Create agent
agent = KnowledgeAwareAgent(
    agent_id="monitored_agent",
    name="Monitored Agent",
    llm_client=llm_client,
    tools=[],
    config=AgentConfiguration(),
    graph_store=graph_store
)
await agent.initialize()

# Execute some tasks
for i in range(10):
    await agent.execute_task({"description": f"Query {i}"})

# Get metrics
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

# Print summary
print(f"Total queries: {graph_metrics.total_graph_queries}")
print(f"Cache hit rate: {graph_metrics.cache_hit_rate:.2%}")
print(f"Average query time: {graph_metrics.average_graph_query_time*1000:.2f} ms")
print(f"Entities retrieved: {graph_metrics.total_entities_retrieved}")
```

---

### Pattern 2: Performance Monitoring

```python
import time

# Track performance over time
start_time = time.time()

# Execute operations
for query in queries:
    await agent.execute_task({"description": query})

elapsed_time = time.time() - start_time

# Get metrics
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

# Calculate throughput
queries_per_second = graph_metrics.total_graph_queries / elapsed_time
entities_per_second = graph_metrics.total_entities_retrieved / elapsed_time

print(f"Throughput: {queries_per_second:.2f} queries/second")
print(f"Entity retrieval rate: {entities_per_second:.2f} entities/second")
print(f"Average latency: {graph_metrics.average_graph_query_time*1000:.2f} ms")
```

---

### Pattern 3: Cache Effectiveness Monitoring

```python
# Monitor cache performance
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

cache_hits = graph_metrics.cache_hits
cache_misses = graph_metrics.cache_misses
total_requests = cache_hits + cache_misses

if total_requests > 0:
    hit_rate = graph_metrics.cache_hit_rate
    miss_rate = 1.0 - hit_rate
    
    print(f"Cache Performance:")
    print(f"  Hit rate: {hit_rate:.2%}")
    print(f"  Miss rate: {miss_rate:.2%}")
    print(f"  Total requests: {total_requests}")
    print(f"  Hits: {cache_hits}")
    print(f"  Misses: {cache_misses}")
```

```


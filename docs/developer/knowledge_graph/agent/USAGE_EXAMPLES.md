# Knowledge Retrieval Usage Examples

This guide provides practical examples for using knowledge retrieval in `KnowledgeAwareAgent`.

## Table of Contents

1. [Basic Knowledge Retrieval](#basic-knowledge-retrieval)
2. [Custom Retrieval Strategy](#custom-retrieval-strategy)
3. [Monitoring and Metrics](#monitoring-and-metrics)
4. [Advanced Patterns](#advanced-patterns)

---

## Basic Knowledge Retrieval

### Example 1: Simple Knowledge Query

```python
from aiecs.domain.agent import KnowledgeAwareAgent, AgentConfiguration
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.llm import MockLLMClient

# Create graph store with sample data
graph_store = InMemoryGraphStore()
await graph_store.initialize()

# Add sample entities
from aiecs.domain.knowledge_graph.models.entity import Entity

alice = Entity(
    id="alice",
    entity_type="Person",
    properties={"name": "Alice", "role": "Engineer"},
    embedding=[0.1] * 3072
)
await graph_store.add_entity(alice)

# Create agent
config = AgentConfiguration(
    retrieval_strategy="hybrid",
    enable_knowledge_caching=True
)

agent = KnowledgeAwareAgent(
    agent_id="example_agent",
    name="Example Agent",
    llm_client=MockLLMClient(),
    tools=[],
    config=config,
    graph_store=graph_store
)
await agent.initialize()

# Execute task - knowledge will be automatically retrieved
result = await agent.execute_task({
    "description": "Find information about Alice"
})

# Knowledge retrieval happens automatically during ReAct loop
print(result)
```

---

### Example 2: Using Different Retrieval Strategies

```python
# Vector-only search
config_vector = AgentConfiguration(
    retrieval_strategy="vector",
    max_context_size=10
)

agent_vector = KnowledgeAwareAgent(
    agent_id="vector_agent",
    name="Vector Search Agent",
    llm_client=llm_client,
    tools=[],
    config=config_vector,
    graph_store=graph_store
)
await agent_vector.initialize()

# Graph-only search
config_graph = AgentConfiguration(
    retrieval_strategy="graph",
    max_context_size=20
)

agent_graph = KnowledgeAwareAgent(
    agent_id="graph_agent",
    name="Graph Search Agent",
    llm_client=llm_client,
    tools=[],
    config=config_graph,
    graph_store=graph_store
)
await agent_graph.initialize()

# Hybrid search
config_hybrid = AgentConfiguration(
    retrieval_strategy="hybrid",
    max_context_size=15
)

agent_hybrid = KnowledgeAwareAgent(
    agent_id="hybrid_agent",
    name="Hybrid Search Agent",
    llm_client=llm_client,
    tools=[],
    config=config_hybrid,
    graph_store=graph_store
)
await agent_hybrid.initialize()
```

---

### Example 3: Manual Knowledge Retrieval

```python
# Retrieve knowledge manually (outside of ReAct loop)
entities = await agent._retrieve_relevant_knowledge(
    task="Find information about Alice",
    context={},
    iteration=1
)

# Use retrieved entities
for entity in entities:
    print(f"Found: {entity.id} ({entity.entity_type})")
    print(f"Properties: {entity.properties}")
```

---

## Custom Retrieval Strategy

### Example 1: Per-Query Strategy Override

```python
# Override strategy for specific query via context
result = await agent.execute_task(
    task={"description": "Find people connected to Alice"},
    context={"retrieval_strategy": "graph"}  # Override to graph-only
)
```

---

### Example 2: Providing Seed Entities

```python
# Provide seed entities directly for graph traversal
entities = await agent._retrieve_relevant_knowledge(
    task="Find related entities",
    context={"seed_entity_ids": ["alice", "bob"]},  # Provide seeds directly
    iteration=1
)
```

---

### Example 3: Custom Cache Configuration

```python
# Configure caching for specific use case
config = AgentConfiguration(
    retrieval_strategy="hybrid",
    enable_knowledge_caching=True,
    cache_ttl=600,  # 10 minutes for stable knowledge
    max_context_size=30
)

agent = KnowledgeAwareAgent(
    agent_id="cached_agent",
    name="Cached Agent",
    llm_client=llm_client,
    tools=[],
    config=config,
    graph_store=graph_store
)
```

---

## Monitoring and Metrics

### Example 1: Basic Metrics Tracking

```python
# Execute multiple queries
queries = [
    "Find information about Alice",
    "Find people at TechCorp",
    "Find information about Bob"
]

for query in queries:
    await agent.execute_task({"description": query})

# Get metrics
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

# Print metrics summary
print("="*60)
print("Knowledge Retrieval Metrics")
print("="*60)
print(f"Total queries: {graph_metrics.total_graph_queries}")
print(f"Total entities retrieved: {graph_metrics.total_entities_retrieved}")
print(f"Average query time: {graph_metrics.average_graph_query_time*1000:.2f} ms")
print(f"Cache hit rate: {graph_metrics.cache_hit_rate:.2%}")
print(f"Cache hits: {graph_metrics.cache_hits}")
print(f"Cache misses: {graph_metrics.cache_misses}")
print("="*60)
```

---

### Example 2: Strategy Usage Analysis

```python
# Track which strategies are being used
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

print("Strategy Usage:")
print(f"  Vector searches: {graph_metrics.vector_search_count}")
print(f"  Graph searches: {graph_metrics.graph_search_count}")
print(f"  Hybrid searches: {graph_metrics.hybrid_search_count}")

total_searches = (
    graph_metrics.vector_search_count +
    graph_metrics.graph_search_count +
    graph_metrics.hybrid_search_count
)

if total_searches > 0:
    print(f"\nStrategy Distribution:")
    print(f"  Vector: {graph_metrics.vector_search_count/total_searches:.1%}")
    print(f"  Graph: {graph_metrics.graph_search_count/total_searches:.1%}")
    print(f"  Hybrid: {graph_metrics.hybrid_search_count/total_searches:.1%}")
```

---

### Example 3: Performance Monitoring

```python
import time

# Monitor performance over time
start_time = time.time()

# Execute operations
for i in range(10):
    await agent.execute_task({
        "description": f"Query {i}: Find entity_{i}"
    })

elapsed_time = time.time() - start_time

# Get metrics
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

# Calculate performance metrics
queries_per_second = graph_metrics.total_graph_queries / elapsed_time
avg_latency_ms = graph_metrics.average_graph_query_time * 1000

print(f"Performance Summary:")
print(f"  Total queries: {graph_metrics.total_graph_queries}")
print(f"  Elapsed time: {elapsed_time:.2f}s")
print(f"  Throughput: {queries_per_second:.2f} queries/second")
print(f"  Average latency: {avg_latency_ms:.2f} ms")
print(f"  Min latency: {graph_metrics.min_graph_query_time*1000:.2f} ms")
print(f"  Max latency: {graph_metrics.max_graph_query_time*1000:.2f} ms")
```

---

### Example 4: Entity Extraction Metrics

```python
# Track entity extraction performance
metrics = agent.get_metrics()
graph_metrics = metrics.graph_metrics

print("Entity Extraction Metrics:")
print(f"  Total extractions: {graph_metrics.entity_extraction_count}")
print(f"  Average extraction time: {graph_metrics.average_extraction_time*1000:.2f} ms")
print(f"  Total extraction time: {graph_metrics.total_extraction_time:.2f}s")
```

---

## Advanced Patterns

### Example 1: Streaming Events

```python
# Track knowledge retrieval events
events = []

async def event_callback(event):
    events.append(event)
    print(f"Event: {event['type']}")

# Execute task with event callback
result = await agent.execute_task_streaming(
    task={"description": "Find information about Alice"},
    context={},
    event_callback=event_callback
)

# Process events
for event in events:
    if event['type'] == 'knowledge_retrieval_completed':
        print(f"Retrieved {event['entity_count']} entities")
        print(f"Retrieval time: {event['retrieval_time_ms']:.2f} ms")
```

---

### Example 2: Cache Performance Analysis

```python
# Measure cache effectiveness
# First round - cache misses
queries = ["Query 1", "Query 2", "Query 3"]
for query in queries:
    await agent.execute_task({"description": query})

initial_misses = agent._graph_metrics.cache_misses

# Second round - should have cache hits
for query in queries:
    await agent.execute_task({"description": query})

final_hits = agent._graph_metrics.cache_hits
final_misses = agent._graph_metrics.cache_misses
hit_rate = agent._graph_metrics.cache_hit_rate

print(f"Cache Analysis:")
print(f"  Initial misses: {initial_misses}")
print(f"  Final hits: {final_hits}")
print(f"  Final misses: {final_misses}")
print(f"  Hit rate: {hit_rate:.2%}")
```

---

### Example 3: Strategy Comparison

```python
# Compare different strategies on same query
query = "Find information about Alice"

strategies = ["vector", "graph", "hybrid"]
results = {}

for strategy in strategies:
    config = AgentConfiguration(retrieval_strategy=strategy)
    agent = KnowledgeAwareAgent(
        agent_id=f"agent_{strategy}",
        name=f"{strategy} Agent",
        llm_client=llm_client,
        tools=[],
        config=config,
        graph_store=graph_store
    )
    await agent.initialize()
    
    start_time = time.time()
    entities = await agent._retrieve_relevant_knowledge(query, {}, 1)
    latency = time.time() - start_time
    
    results[strategy] = {
        "latency": latency,
        "entity_count": len(entities)
    }
    
    await agent.shutdown()

# Print comparison
print("Strategy Comparison:")
for strategy, stats in results.items():
    print(f"  {strategy:10s}: {stats['latency']*1000:6.2f} ms, {stats['entity_count']:2d} entities")
```

---

### Example 4: Error Handling and Fallback

```python
try:
    # Attempt knowledge retrieval
    entities = await agent._retrieve_relevant_knowledge(
        task="Find information",
        context={},
        iteration=1
    )
    
    if not entities:
        # Fallback if no entities found
        print("No entities found, using fallback strategy")
        # Use alternative approach
    
except Exception as e:
    # Handle errors gracefully
    print(f"Knowledge retrieval failed: {e}")
    # Fallback to standard behavior
    pass
```

---

## Best Practices

### 1. Choose Appropriate Strategy

- Use `vector` for semantic similarity queries
- Use `graph` for relationship exploration
- Use `hybrid` for comprehensive search
- Use `auto` for dynamic query handling

### 2. Configure Caching Wisely

- Enable caching for repeated queries
- Set appropriate TTL based on data stability
- Monitor cache hit rates

### 3. Monitor Performance

- Track query latency
- Monitor cache effectiveness
- Analyze strategy usage
- Measure entity extraction performance

### 4. Handle Errors Gracefully

- Always handle retrieval failures
- Provide fallback mechanisms
- Log errors for debugging

---

## Related Documentation

- [Configuration Guide](./KNOWLEDGE_RETRIEVAL_CONFIGURATION.md)
- [Metrics and Monitoring](./METRICS_AND_MONITORING.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Search Strategies Guide](../search/SEARCH_STRATEGIES.md)


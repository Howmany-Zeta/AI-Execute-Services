# Performance Optimization Guide

This comprehensive guide covers strategies and techniques for optimizing agent performance, including caching, parallel execution, streaming, resource management, and monitoring.

## Table of Contents

1. [Overview](#overview)
2. [Caching Strategies](#caching-strategies)
3. [Parallel Execution](#parallel-execution)
4. [Streaming Optimization](#streaming-optimization)
5. [Resource Optimization](#resource-optimization)
6. [Memory Optimization](#memory-optimization)
7. [Monitoring and Profiling](#monitoring-and-profiling)
8. [Best Practices](#best-practices)

## Overview

Performance optimization techniques:

- **Tool Caching**: 30-50% cost reduction, faster responses
- **Parallel Execution**: 3-5x performance improvement
- **Streaming**: Better UX, progressive results
- **Resource Management**: Prevent overload, ensure stability
- **Memory Optimization**: Reduce memory usage
- **Monitoring**: Identify bottlenecks

## Caching Strategies

### Pattern 1: Aggressive Caching

Cache expensive operations aggressively.

```python
from aiecs.domain.agent import CacheConfig

cache_config = CacheConfig(
    enabled=True,
    default_ttl=3600,  # 1 hour default
    tool_specific_ttl={
        "search": 7200,  # 2 hours for search
        "translation": 86400,  # 24 hours for translation
        "calculator": 0  # Don't cache calculator
    },
    max_cache_size=5000
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search", "translation", "calculator"],
    config=config,
    cache_config=cache_config
)
```

### Pattern 2: Selective Caching

Cache only expensive operations.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=0,  # Don't cache by default
    tool_specific_ttl={
        "expensive_api": 3600,  # Cache expensive API
        "slow_operation": 1800  # Cache slow operations
    }
)
```

### Pattern 3: Cache Invalidation

Invalidate cache when data changes.

```python
# Invalidate cache after data update
agent.invalidate_cache(tool_name="search")

# Invalidate by pattern
agent.invalidate_cache(pattern="query:Python*")
```

## Parallel Execution

### Pattern 1: Maximize Parallelism

Execute maximum independent tools in parallel.

```python
# Execute many tools in parallel
tool_calls = [
    {"tool_name": "search", "parameters": {"query": "Python"}},
    {"tool_name": "weather", "parameters": {"location": "NYC"}},
    {"tool_name": "calculator", "parameters": {"operation": "add", "a": 1, "b": 2}},
    {"tool_name": "translator", "parameters": {"text": "Hello", "target": "es"}}
]

results = await agent.execute_tools_parallel(
    tool_calls,
    max_concurrency=10  # High concurrency
)
```

### Pattern 2: Batch Processing

Process tasks in batches for better throughput.

```python
# Process tasks in batches
tasks = [task1, task2, task3, ...]

batch_size = 10
for i in range(0, len(tasks), batch_size):
    batch = tasks[i:i+batch_size]
    results = await asyncio.gather(*[
        agent.execute_task(task, context) for task in batch
    ])
```

## Streaming Optimization

### Pattern 1: Progressive Display

Use streaming for better UX.

```python
# Stream results progressively
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        # Display tokens as they arrive
        display_token(event['content'])
    elif event['type'] == 'tool_result':
        # Display tool results immediately
        display_result(event['result'])
```

### Pattern 2: Buffer Optimization

Optimize buffer size for smooth streaming.

```python
# Buffer tokens for smooth display
buffer = []
buffer_size = 20

async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        buffer.append(event['content'])
        if len(buffer) >= buffer_size:
            display(''.join(buffer))
            buffer.clear()
```

## Resource Optimization

### Pattern 1: Optimal Rate Limits

Set rate limits based on API constraints.

```python
from aiecs.domain.agent.models import ResourceLimits

# Match API rate limits
resource_limits = ResourceLimits(
    max_tokens_per_minute=60000,  # Match API limit
    max_tool_calls_per_minute=500,  # Match tool API limit
    token_burst_size=120000  # Allow 2x burst
)
```

### Pattern 2: Concurrent Task Optimization

Optimize concurrent tasks based on resources.

```python
import os

# Set based on CPU cores
cpu_count = os.cpu_count() or 4
max_concurrent = cpu_count * 2  # 2x CPU cores

resource_limits = ResourceLimits(
    max_concurrent_tasks=max_concurrent
)
```

## Memory Optimization

### Pattern 1: Conversation Compression

Use compression to reduce memory usage.

```python
from aiecs.domain.context import CompressionConfig

compression_config = CompressionConfig(
    strategy="summarize",
    auto_compress_enabled=True,
    auto_compress_threshold=50,
    auto_compress_target=30
)

context_engine = ContextEngine(compression_config=compression_config)
```

### Pattern 2: Cache Size Limits

Limit cache size to control memory.

```python
cache_config = CacheConfig(
    enabled=True,
    max_cache_size=1000,  # Limit cache entries
    max_memory_mb=100  # Limit cache memory
)
```

## Monitoring and Profiling

### Pattern 1: Performance Profiling

Profile agent performance.

```python
import time

# Profile execution time
start = time.time()
result = await agent.execute_task(task, context)
duration = time.time() - start

print(f"Execution time: {duration:.2f}s")

# Profile specific operations
with agent.track_operation_time("data_processing"):
    result = await agent.execute_task(task, context)
```

### Pattern 2: Metrics Analysis

Analyze performance metrics.

```python
# Get performance metrics
metrics = agent.get_performance_metrics()

print(f"Average response time: {metrics['avg_response_time']}s")
print(f"P95 response time: {metrics['p95_response_time']}s")
print(f"P99 response time: {metrics['p99_response_time']}s")

# Identify bottlenecks
if metrics['p95_response_time'] > 3.0:
    logger.warning("P95 response time exceeds threshold")
```

### Pattern 3: Cache Performance

Monitor cache performance.

```python
stats = agent.get_cache_stats()

print(f"Cache hit rate: {stats['hit_rate']:.1%}")
print(f"Cache size: {stats['size']}")

if stats['hit_rate'] < 0.3:
    logger.warning("Low cache hit rate - consider adjusting TTL")
```

## Best Practices

### 1. Combine Optimization Techniques

Combine multiple optimization techniques:

```python
# Optimized agent configuration
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,
    tool_specific_ttl={"search": 600}
)

resource_limits = ResourceLimits(
    max_concurrent_tasks=10,
    max_tokens_per_minute=50000
)

compression_config = CompressionConfig(
    auto_compress_enabled=True,
    auto_compress_threshold=50
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    cache_config=cache_config,
    resource_limits=resource_limits,
    context_engine=ContextEngine(compression_config=compression_config),
    enable_parallel_execution=True,
    enable_streaming=True
)
```

### 2. Monitor and Adjust

Continuously monitor and adjust:

```python
# Monitor performance
metrics = agent.get_performance_metrics()
cache_stats = agent.get_cache_stats()

# Adjust based on metrics
if metrics['avg_response_time'] > 2.0:
    # Increase caching
    cache_config.default_ttl = 600
    
if cache_stats['hit_rate'] < 0.3:
    # Adjust cache TTL
    cache_config.default_ttl = 1800
```

### 3. Profile Before Optimizing

Profile to identify bottlenecks:

```python
# Profile before optimizing
with agent.track_operation_time("full_execution"):
    result = await agent.execute_task(task, context)

# Get operation metrics
operation_metrics = agent.get_operation_metrics("full_execution")
print(f"Operation time: {operation_metrics['avg_time']}s")

# Optimize based on profiling results
```

## Summary

Performance optimization provides:
- ✅ 30-50% cost reduction (caching)
- ✅ 3-5x speed improvement (parallel execution)
- ✅ Better UX (streaming)
- ✅ Resource stability (rate limiting)
- ✅ Memory efficiency (compression)

**Key Optimization Techniques**:
- Cache expensive operations
- Execute tools in parallel
- Stream for better UX
- Set appropriate rate limits
- Compress conversations
- Monitor and adjust

For more details, see:
- [Tool Caching](./TOOL_CACHING.md)
- [Parallel Tool Execution](./PARALLEL_TOOL_EXECUTION.md)
- [Streaming](./STREAMING.md)
- [Resource Management](./RESOURCE_MANAGEMENT.md)


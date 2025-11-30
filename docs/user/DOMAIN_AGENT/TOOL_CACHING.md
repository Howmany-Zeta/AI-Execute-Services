# Tool Result Caching Best Practices

This guide covers how to use tool result caching to reduce API calls, improve performance, and lower costs by caching tool execution results.

## Table of Contents

1. [Overview](#overview)
2. [Basic Caching](#basic-caching)
3. [Cache Configuration](#cache-configuration)
4. [Per-Tool TTL Configuration](#per-tool-ttl-configuration)
5. [Cache Management](#cache-management)
6. [Cache Invalidation](#cache-invalidation)
7. [Performance Monitoring](#performance-monitoring)
8. [Best Practices](#best-practices)

## Overview

Tool result caching provides:

- **Cost Reduction**: 30-50% reduction in API costs by avoiding redundant calls
- **Performance Improvement**: Faster responses for cached results
- **Configurable TTL**: Different cache durations for different tools
- **Automatic Cleanup**: Automatic cache cleanup when capacity threshold reached
- **Memory Management**: Size limits to prevent memory exhaustion

### When to Use Caching

- ✅ Expensive API calls (search, weather, translation)
- ✅ Results don't change frequently
- ✅ Same queries repeated often
- ✅ Cost reduction is important

### When NOT to Use Caching

- ❌ Time-sensitive data (real-time prices, live data)
- ❌ Results change frequently
- ❌ Unique queries each time
- ❌ Memory constraints

## Basic Caching

### Pattern 1: Enable Caching

Enable caching with default configuration.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration, CacheConfig
from aiecs.llm import OpenAIClient

# Configure caching
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300  # 5 minutes default
)

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator", "weather"],
    config=AgentConfiguration(),
    cache_config=cache_config
)

await agent.initialize()

# First call - executes tool and caches result
result1 = await agent.execute_tool_with_cache("search", {"query": "Python"})

# Second call with same parameters - uses cache!
result2 = await agent.execute_tool_with_cache("search", {"query": "Python"})
# No API call made - result from cache
```

### Pattern 2: Disable Caching

Disable caching for specific use cases.

```python
# Disable caching
cache_config = CacheConfig(enabled=False)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    cache_config=cache_config
)

# All tool calls execute directly (no caching)
result = await agent.execute_tool_with_cache("search", {"query": "Python"})
```

### Pattern 3: Automatic Caching

Agent automatically caches tool results when caching is enabled.

```python
# Agent automatically caches results
result = await agent.execute_task(
    {"description": "Search for Python"},
    {}
)
# Tool result cached automatically
```

## Cache Configuration

### Pattern 1: Basic Configuration

Configure basic caching settings.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,  # 5 minutes
    max_cache_size=1000,  # Maximum 1000 cached entries
    max_memory_mb=100  # Maximum 100MB cache memory
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    cache_config=cache_config
)
```

### Pattern 2: Aggressive Caching

Configure aggressive caching for expensive operations.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=3600,  # 1 hour default
    max_cache_size=5000,  # Larger cache
    max_memory_mb=500,  # More memory
    cleanup_threshold=0.95  # Cleanup at 95% capacity
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    cache_config=cache_config
)
```

### Pattern 3: Conservative Caching

Configure conservative caching for frequently changing data.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=60,  # 1 minute (short TTL)
    max_cache_size=100,  # Small cache
    cleanup_threshold=0.8  # Cleanup at 80% capacity
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["weather"],  # Weather changes frequently
    config=config,
    cache_config=cache_config
)
```

## Per-Tool TTL Configuration

### Pattern 1: Tool-Specific TTL

Configure different TTL for different tools.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,  # 5 minutes default
    tool_specific_ttl={
        "search": 600,  # Search cached for 10 minutes
        "calculator": 3600,  # Calculator cached for 1 hour
        "weather": 1800,  # Weather cached for 30 minutes
        "translation": 7200  # Translation cached for 2 hours
    }
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search", "calculator", "weather", "translation"],
    config=config,
    cache_config=cache_config
)
```

### Pattern 2: Disable Caching for Specific Tools

Disable caching for specific tools.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,
    tool_specific_ttl={
        "live_data": 0,  # Disable caching (0 TTL)
        "real_time": 0
    }
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search", "live_data", "real_time"],
    config=config,
    cache_config=cache_config
)
```

### Pattern 3: Long-Term Caching

Configure long-term caching for stable data.

```python
cache_config = CacheConfig(
    enabled=True,
    default_ttl=300,
    tool_specific_ttl={
        "dictionary": 86400,  # 24 hours
        "encyclopedia": 86400,  # 24 hours
        "historical_data": 604800  # 7 days
    }
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["dictionary", "encyclopedia", "historical_data"],
    config=config,
    cache_config=cache_config
)
```

## Cache Management

### Pattern 1: Cache Statistics

Get cache statistics to monitor performance.

```python
# Get cache statistics
stats = agent.get_cache_stats()

print(f"Cache size: {stats['size']}")
print(f"Cache hits: {stats['hits']}")
print(f"Cache misses: {stats['misses']}")
print(f"Hit rate: {stats['hit_rate']:.1%}")
print(f"Memory usage: {stats['memory_mb']:.1f}MB")
```

### Pattern 2: Cache Cleanup

Manually trigger cache cleanup.

```python
# Clean up expired entries
cleaned_count = agent.cleanup_cache()

print(f"Cleaned up {cleaned_count} expired entries")
```

### Pattern 3: Cache Size Monitoring

Monitor cache size and trigger cleanup when needed.

```python
stats = agent.get_cache_stats()

if stats['size'] > cache_config.max_cache_size * 0.9:
    # Cache approaching limit - cleanup
    cleaned_count = agent.cleanup_cache()
    print(f"Cleaned up {cleaned_count} entries")
```

## Cache Invalidation

### Pattern 1: Invalidate Specific Tool

Invalidate cache for a specific tool.

```python
# Invalidate all cache entries for "search" tool
invalidated_count = agent.invalidate_cache(tool_name="search")

print(f"Invalidated {invalidated_count} cache entries")
```

### Pattern 2: Invalidate by Pattern

Invalidate cache entries matching a pattern.

```python
# Invalidate cache entries matching pattern
invalidated_count = agent.invalidate_cache(pattern="query:Python*")

print(f"Invalidated {invalidated_count} cache entries")
```

### Pattern 3: Clear All Cache

Clear entire cache.

```python
# Clear all cache
invalidated_count = agent.invalidate_cache()

print(f"Cleared {invalidated_count} cache entries")
```

### Pattern 4: Time-Based Invalidation

Invalidate cache based on age.

```python
import time

# Invalidate entries older than 1 hour
stats = agent.get_cache_stats()
current_time = time.time()

# Get cache timestamps and invalidate old entries
# (Implementation depends on agent's cache structure)
```

## Performance Monitoring

### Pattern 1: Cache Hit Rate Monitoring

Monitor cache hit rate to optimize configuration.

```python
# Get cache statistics
stats = agent.get_cache_stats()

if stats['hit_rate'] < 0.5:  # Less than 50% hit rate
    logger.warning("Low cache hit rate - consider adjusting TTL")
elif stats['hit_rate'] > 0.9:  # More than 90% hit rate
    logger.info("High cache hit rate - caching is effective")
```

### Pattern 2: Cost Savings Calculation

Calculate cost savings from caching.

```python
stats = agent.get_cache_stats()

# Estimate cost savings
api_call_cost = 0.01  # $0.01 per API call
cache_hits = stats['hits']
cost_saved = cache_hits * api_call_cost

print(f"Cache hits: {cache_hits}")
print(f"Estimated cost saved: ${cost_saved:.2f}")
```

### Pattern 3: Performance Impact

Measure performance impact of caching.

```python
import time

# Without cache
start = time.time()
result1 = await agent.execute_tool("search", {"query": "Python"})
time_without_cache = time.time() - start

# With cache (second call)
start = time.time()
result2 = await agent.execute_tool_with_cache("search", {"query": "Python"})
time_with_cache = time.time() - start

speedup = time_without_cache / time_with_cache
print(f"Speedup: {speedup:.1f}x faster with cache")
```

## Best Practices

### 1. Configure Appropriate TTL

Set TTL based on data freshness requirements:

```python
# Stable data: Long TTL
cache_config = CacheConfig(
    tool_specific_ttl={
        "dictionary": 86400,  # 24 hours
        "encyclopedia": 86400
    }
)

# Frequently changing data: Short TTL
cache_config = CacheConfig(
    tool_specific_ttl={
        "weather": 1800,  # 30 minutes
        "stock_prices": 60  # 1 minute
    }
)
```

### 2. Monitor Cache Performance

Regularly monitor cache performance:

```python
stats = agent.get_cache_stats()

if stats['hit_rate'] < 0.3:
    # Low hit rate - consider disabling caching or adjusting TTL
    logger.warning("Low cache hit rate")
```

### 3. Set Appropriate Cache Size

Set cache size based on available memory:

```python
cache_config = CacheConfig(
    max_cache_size=1000,  # Adjust based on memory
    max_memory_mb=100  # Monitor memory usage
)
```

### 4. Invalidate Stale Data

Invalidate cache when data changes:

```python
# After updating data
agent.invalidate_cache(tool_name="search")
```

### 5. Use for Expensive Operations

Use caching for expensive operations:

```python
# Good: Expensive API calls
cache_config = CacheConfig(
    tool_specific_ttl={
        "search": 600,  # Cache expensive search
        "translation": 3600  # Cache expensive translation
    }
)

# Less useful: Cheap operations
cache_config = CacheConfig(
    tool_specific_ttl={
        "calculator": 0  # Don't cache cheap calculations
    }
)
```

### 6. Handle Cache Errors Gracefully

Handle cache errors without breaking functionality:

```python
try:
    result = await agent.execute_tool_with_cache("search", {"query": "Python"})
except CacheError as e:
    logger.error(f"Cache error: {e}")
    # Fall back to direct execution
    result = await agent.execute_tool("search", {"query": "Python"})
```

## Summary

Tool result caching provides:
- ✅ 30-50% cost reduction
- ✅ Faster responses for cached results
- ✅ Configurable TTL per tool
- ✅ Automatic cleanup
- ✅ Memory management

**Key Takeaways**:
- Use for expensive operations
- Configure appropriate TTL
- Monitor cache performance
- Invalidate stale data
- Set appropriate cache size

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Parallel Tool Execution](./PARALLEL_TOOL_EXECUTION.md)


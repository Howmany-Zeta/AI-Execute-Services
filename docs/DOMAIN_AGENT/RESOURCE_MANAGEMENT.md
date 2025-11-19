# Resource Management Configuration

This guide covers how to configure and use resource management features including rate limiting, quotas, and throttling to ensure stable operation in production environments.

## Table of Contents

1. [Overview](#overview)
2. [Basic Configuration](#basic-configuration)
3. [Rate Limiting](#rate-limiting)
4. [Concurrent Task Limits](#concurrent-task-limits)
5. [Memory Limits](#memory-limits)
6. [Timeout Configuration](#timeout-configuration)
7. [Enforcement Modes](#enforcement-modes)
8. [Resource Monitoring](#resource-monitoring)
9. [Best Practices](#best-practices)

## Overview

Resource management provides:

- **Rate Limiting**: Token bucket algorithm for token and tool call rate limiting
- **Concurrent Limits**: Maximum concurrent task execution limits
- **Memory Limits**: Memory usage constraints
- **Timeouts**: Task execution timeouts
- **Enforcement**: Configurable enforcement (enforce vs monitor)
- **Throttling**: Automatic throttling when limits approached

### When to Use Resource Management

- ✅ Production deployments
- ✅ API rate limit compliance
- ✅ Resource exhaustion prevention
- ✅ Cost control
- ✅ Stability requirements

## Basic Configuration

### Pattern 1: Basic Rate Limiting

Configure basic rate limiting.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.domain.agent.models import ResourceLimits
from aiecs.llm import OpenAIClient

# Configure resource limits
resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    max_tokens_per_minute=10000,
    max_tool_calls_per_minute=100
)

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration(),
    resource_limits=resource_limits
)

await agent.initialize()
```

### Pattern 2: Production Configuration

Configure strict limits for production.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=10,
    max_tokens_per_minute=50000,
    max_tokens_per_hour=2000000,
    max_tool_calls_per_minute=500,
    max_tool_calls_per_hour=30000,
    max_memory_mb=2048,
    task_timeout_seconds=300,
    enforce_limits=True,
    reject_on_limit=True  # Reject instead of waiting
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)
```

### Pattern 3: Monitoring Mode

Monitor resources without enforcement.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=10,
    max_tokens_per_minute=10000,
    enforce_limits=False  # Monitor but don't enforce
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)
```

## Rate Limiting

### Pattern 1: Token Rate Limiting

Configure token rate limits.

```python
resource_limits = ResourceLimits(
    max_tokens_per_minute=10000,  # 10K tokens per minute
    max_tokens_per_hour=500000  # 500K tokens per hour
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Agent automatically enforces token limits
result = await agent.execute_task(task, context)
```

### Pattern 2: Token Bucket with Burst

Configure token bucket with burst support.

```python
resource_limits = ResourceLimits(
    max_tokens_per_minute=10000,
    token_burst_size=20000  # Allow 2x burst (20K tokens)
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Burst allows temporary over-limit usage
```

### Pattern 3: Tool Call Rate Limiting

Configure tool call rate limits.

```python
resource_limits = ResourceLimits(
    max_tool_calls_per_minute=100,
    max_tool_calls_per_hour=5000
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search", "calculator"],
    config=config,
    resource_limits=resource_limits
)
```

## Concurrent Task Limits

### Pattern 1: Basic Concurrent Limits

Set maximum concurrent tasks.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=5  # Maximum 5 concurrent tasks
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Agent enforces concurrent task limit
```

### Pattern 2: Check Resource Availability

Check resources before executing.

```python
# Check if resources are available
status = await agent.check_resource_availability()

if status['available']:
    result = await agent.execute_task(task, context)
else:
    print(f"Resources unavailable: {status['reason']}")
    # Wait for resources or reject
```

### Pattern 3: Wait for Resources

Wait for resources to become available.

```python
# Wait for resources with timeout
available = await agent.wait_for_resources(timeout=30.0)

if available:
    result = await agent.execute_task(task, context)
else:
    print("Resources not available within timeout")
```

## Memory Limits

### Pattern 1: Memory Constraints

Configure memory limits.

```python
resource_limits = ResourceLimits(
    max_memory_mb=1024  # Maximum 1GB memory
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)
```

### Pattern 2: Memory Monitoring

Monitor memory usage.

```python
# Get resource status
status = await agent.check_resource_availability()

if 'memory_usage_mb' in status:
    print(f"Memory usage: {status['memory_usage_mb']}MB")
    print(f"Memory limit: {status['memory_limit_mb']}MB")
```

## Timeout Configuration

### Pattern 1: Task Timeout

Configure task execution timeout.

```python
resource_limits = ResourceLimits(
    task_timeout_seconds=300  # 5 minute timeout
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Tasks timeout after 5 minutes
```

### Pattern 2: Resource Wait Timeout

Configure resource wait timeout.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    resource_wait_timeout_seconds=120  # Wait up to 2 minutes for resources
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)
```

## Enforcement Modes

### Pattern 1: Enforce Limits

Enforce limits strictly.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    max_tokens_per_minute=10000,
    enforce_limits=True,  # Enforce limits
    reject_on_limit=True  # Reject when limit reached
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Requests rejected when limits exceeded
```

### Pattern 2: Wait Mode

Wait for resources instead of rejecting.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    max_tokens_per_minute=10000,
    enforce_limits=True,
    reject_on_limit=False,  # Wait instead of reject
    resource_wait_timeout_seconds=60
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Requests wait for resources to become available
```

### Pattern 3: Monitor Only

Monitor without enforcement.

```python
resource_limits = ResourceLimits(
    max_concurrent_tasks=10,
    max_tokens_per_minute=10000,
    enforce_limits=False  # Monitor but don't enforce
)

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    resource_limits=resource_limits
)

# Limits monitored but not enforced
```

## Resource Monitoring

### Pattern 1: Check Resource Status

Check current resource status.

```python
# Check resource availability
status = await agent.check_resource_availability()

print(f"Available: {status['available']}")
print(f"Active tasks: {status.get('active_tasks', 0)}")
print(f"Max tasks: {status.get('max_tasks', 0)}")

if not status['available']:
    print(f"Reason: {status['reason']}")
```

### Pattern 2: Monitor Resource Usage

Monitor resource usage over time.

```python
import asyncio

async def monitor_resources():
    """Monitor resource usage every minute"""
    while True:
        status = await agent.check_resource_availability()
        
        print(f"Active tasks: {status.get('active_tasks', 0)}/{status.get('max_tasks', 0)}")
        
        if not status['available']:
            logger.warning(f"Resource limit reached: {status['reason']}")
        
        await asyncio.sleep(60)  # Check every minute

# Start monitoring
asyncio.create_task(monitor_resources())
```

### Pattern 3: Resource Alerts

Alert when resources are constrained.

```python
status = await agent.check_resource_availability()

# Alert when approaching limits
if status.get('active_tasks', 0) >= status.get('max_tasks', 0) * 0.8:
    logger.warning("Approaching concurrent task limit")

if not status['available']:
    await send_alert(f"Resource limit reached: {status['reason']}")
```

## Best Practices

### 1. Set Appropriate Limits

Set limits based on your infrastructure:

```python
# Production limits
resource_limits = ResourceLimits(
    max_concurrent_tasks=10,  # Based on CPU cores
    max_tokens_per_minute=50000,  # Based on API limits
    max_memory_mb=2048  # Based on available memory
)
```

### 2. Use Token Bucket for Burst

Use token bucket for burst handling:

```python
resource_limits = ResourceLimits(
    max_tokens_per_minute=10000,
    token_burst_size=20000  # Allow 2x burst
)
```

### 3. Monitor Before Enforcing

Start with monitoring mode:

```python
# Development: Monitor only
resource_limits = ResourceLimits(
    enforce_limits=False
)

# Production: Enforce limits
resource_limits = ResourceLimits(
    enforce_limits=True,
    reject_on_limit=True
)
```

### 4. Handle Resource Unavailability

Handle resource unavailability gracefully:

```python
status = await agent.check_resource_availability()

if not status['available']:
    if resource_limits.reject_on_limit:
        # Reject request
        raise ResourceLimitExceeded(status['reason'])
    else:
        # Wait for resources
        await agent.wait_for_resources(timeout=30.0)
```

### 5. Set Appropriate Timeouts

Set timeouts based on task complexity:

```python
# Short timeout for simple tasks
resource_limits = ResourceLimits(
    task_timeout_seconds=60
)

# Long timeout for complex tasks
resource_limits = ResourceLimits(
    task_timeout_seconds=600
)
```

## Summary

Resource management provides:
- ✅ Rate limiting (tokens, tool calls)
- ✅ Concurrent task limits
- ✅ Memory constraints
- ✅ Timeout configuration
- ✅ Enforcement modes
- ✅ Resource monitoring

**Key Takeaways**:
- Set limits based on infrastructure
- Use token bucket for burst handling
- Monitor before enforcing
- Handle unavailability gracefully
- Set appropriate timeouts

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Performance Monitoring](./PERFORMANCE_MONITORING.md)


# Performance Monitoring and Health Status

This guide covers how to monitor agent performance, track metrics, and use health status for production monitoring and alerting.

## Table of Contents

1. [Overview](#overview)
2. [Performance Metrics](#performance-metrics)
3. [Health Status](#health-status)
4. [Operation-Level Tracking](#operation-level-tracking)
5. [Monitoring Patterns](#monitoring-patterns)
6. [Alerting Patterns](#alerting-patterns)
7. [Best Practices](#best-practices)

## Overview

AIECS agents provide comprehensive performance monitoring and health status tracking:

- **Performance Metrics**: Track execution times, success rates, token usage, tool calls
- **Health Status**: Calculate health scores (0-100) based on multiple factors
- **Operation-Level Tracking**: Track individual operations with percentile calculations
- **Session Metrics**: Track session-level performance metrics

### Key Metrics

- Task execution metrics (total, successful, failed, success rate)
- Execution time metrics (average, min, max, percentiles)
- Resource usage (tokens, tool calls, API costs)
- Error tracking (count, types)
- Session metrics (request count, error count, processing time)

## Performance Metrics

### Pattern 1: Basic Metrics Retrieval

Get basic performance metrics from an agent.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration()
)

await agent.initialize()

# Execute some tasks
for i in range(10):
    result = await agent.execute_task(
        {"description": f"Task {i}"},
        {}
    )

# Get metrics
metrics = agent.get_metrics()

print(f"Total tasks: {metrics.total_tasks_executed}")
print(f"Successful tasks: {metrics.successful_tasks}")
print(f"Failed tasks: {metrics.failed_tasks}")
print(f"Success rate: {metrics.success_rate}%")
print(f"Average execution time: {metrics.average_execution_time}s")
print(f"Total tokens used: {metrics.total_tokens_used}")
print(f"Total tool calls: {metrics.total_tool_calls}")
```

### Pattern 2: Detailed Performance Metrics

Get detailed performance metrics including percentiles.

```python
# Get detailed performance metrics
performance = agent.get_performance_metrics()

print(f"Average response time: {performance['avg_response_time']}s")
print(f"P50 response time: {performance['p50_response_time']}s")
print(f"P95 response time: {performance['p95_response_time']}s")
print(f"P99 response time: {performance['p99_response_time']}s")
print(f"Min response time: {performance['min_response_time']}s")
print(f"Max response time: {performance['max_response_time']}s")
```

### Pattern 3: Operation-Level Tracking

Track individual operations with context managers.

```python
# Track operation performance
with agent.track_operation_time("data_processing"):
    result = await agent.execute_task(
        {"description": "Process data"},
        {}
    )

# Get operation-specific metrics
operation_metrics = agent.get_operation_metrics("data_processing")
print(f"Operation count: {operation_metrics['count']}")
print(f"Average time: {operation_metrics['avg_time']}s")
print(f"P95 time: {operation_metrics['p95_time']}s")
```

### Pattern 4: Metrics Export

Export metrics for external monitoring systems.

```python
# Get metrics as dictionary
metrics_dict = agent.get_metrics().model_dump()

# Export to monitoring system
import json
metrics_json = json.dumps(metrics_dict)

# Send to monitoring endpoint
await send_to_monitoring(metrics_json)
```

## Health Status

### Pattern 1: Basic Health Check

Get agent health status.

```python
# Get health status
health = agent.get_health_status()

print(f"Health score: {health['health_score']}/100")
print(f"Status: {health['status']}")  # healthy, degraded, unhealthy
print(f"Issues: {health['issues']}")
print(f"Last check: {health['last_check_time']}")
```

### Pattern 2: Health Status Monitoring

Monitor health status over time.

```python
import asyncio

async def monitor_health():
    """Monitor agent health every minute"""
    while True:
        health = agent.get_health_status()
        
        if health['status'] == 'unhealthy':
            logger.critical(
                f"Agent {agent.agent_id} is unhealthy! "
                f"Score: {health['health_score']}, "
                f"Issues: {', '.join(health['issues'])}"
            )
            # Send alert
            await send_alert(health)
        elif health['status'] == 'degraded':
            logger.warning(
                f"Agent {agent.agent_id} is degraded. "
                f"Score: {health['health_score']}"
            )
        
        await asyncio.sleep(60)  # Check every minute

# Start monitoring
asyncio.create_task(monitor_health())
```

### Pattern 3: Health-Based Actions

Take actions based on health status.

```python
health = agent.get_health_status()

if health['status'] == 'unhealthy':
    # Take corrective action
    if 'High error rate' in health['issues']:
        # Reduce load or restart agent
        await agent.shutdown()
        await agent.initialize()
    elif 'Low success rate' in health['issues']:
        # Adjust configuration
        await agent.get_config_manager().set_config('temperature', 0.7)
elif health['status'] == 'degraded':
    # Log warning
    logger.warning(f"Agent health degraded: {health['health_score']}")
```

### Pattern 4: Health Score Calculation

Understand how health score is calculated.

```python
health = agent.get_health_status()

# Health score factors:
# - Success rate (40% weight)
# - Error rate (30% weight)
# - Performance (20% weight)
# - Session health (10% weight)

metrics = agent.get_metrics()

# Calculate success rate component
success_rate_score = metrics.success_rate * 0.4

# Calculate error rate component
error_rate = (metrics.failed_tasks / metrics.total_tasks_executed) * 100 if metrics.total_tasks_executed > 0 else 0
error_rate_score = max(0, 100 - error_rate) * 0.3

# Calculate performance component
performance_score = min(100, (1.0 / metrics.average_execution_time) * 100) * 0.2 if metrics.average_execution_time else 50 * 0.2

# Total health score
total_score = success_rate_score + error_rate_score + performance_score

print(f"Calculated health score: {total_score}")
print(f"Actual health score: {health['health_score']}")
```

## Operation-Level Tracking

### Pattern 1: Track Specific Operations

Track performance of specific operations.

```python
# Track data processing operations
with agent.track_operation_time("data_processing"):
    result = await agent.execute_task(
        {"description": "Process data"},
        {}
    )

# Track search operations
with agent.track_operation_time("search"):
    result = await agent.execute_task(
        {"description": "Search for information"},
        {}
    )

# Get operation metrics
data_metrics = agent.get_operation_metrics("data_processing")
search_metrics = agent.get_operation_metrics("search")

print(f"Data processing: {data_metrics['avg_time']}s")
print(f"Search: {search_metrics['avg_time']}s")
```

### Pattern 2: Percentile Tracking

Track percentiles for operations.

```python
# Execute multiple operations
for i in range(100):
    with agent.track_operation_time("operation"):
        await agent.execute_task(
            {"description": f"Task {i}"},
            {}
        )

# Get percentile metrics
metrics = agent.get_operation_metrics("operation")
print(f"P50: {metrics['p50_time']}s")
print(f"P95: {metrics['p95_time']}s")
print(f"P99: {metrics['p99_time']}s")
```

## Monitoring Patterns

### Pattern 1: Periodic Metrics Collection

Collect metrics periodically for monitoring.

```python
import asyncio
from datetime import datetime

async def collect_metrics_periodically():
    """Collect metrics every 5 minutes"""
    while True:
        metrics = agent.get_metrics()
        health = agent.get_health_status()
        
        # Store metrics
        await store_metrics({
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": agent.agent_id,
            "metrics": metrics.model_dump(),
            "health": health
        })
        
        await asyncio.sleep(300)  # 5 minutes

# Start collection
asyncio.create_task(collect_metrics_periodically())
```

### Pattern 2: Metrics Aggregation

Aggregate metrics across multiple agents.

```python
# Get metrics from multiple agents
all_metrics = []
for agent_id in agent_registry.list_agent_ids():
    agent = agent_registry.get_agent(agent_id)
    metrics = agent.get_metrics()
    all_metrics.append({
        "agent_id": agent_id,
        "metrics": metrics
    })

# Aggregate
total_tasks = sum(m["metrics"].total_tasks_executed for m in all_metrics)
total_successful = sum(m["metrics"].successful_tasks for m in all_metrics)
total_failed = sum(m["metrics"].failed_tasks for m in all_metrics)
overall_success_rate = (total_successful / total_tasks * 100) if total_tasks > 0 else 0

print(f"Overall success rate: {overall_success_rate}%")
```

### Pattern 3: Performance Dashboards

Create performance dashboards from metrics.

```python
# Get metrics for dashboard
metrics = agent.get_metrics()
health = agent.get_health_status()
performance = agent.get_performance_metrics()

# Create dashboard data
dashboard_data = {
    "agent_id": agent.agent_id,
    "health": {
        "score": health['health_score'],
        "status": health['status'],
        "issues": health['issues']
    },
    "performance": {
        "avg_response_time": performance['avg_response_time'],
        "p95_response_time": performance['p95_response_time'],
        "success_rate": metrics.success_rate
    },
    "usage": {
        "total_tasks": metrics.total_tasks_executed,
        "total_tokens": metrics.total_tokens_used,
        "total_tool_calls": metrics.total_tool_calls
    }
}

# Send to dashboard
await update_dashboard(dashboard_data)
```

## Alerting Patterns

### Pattern 1: Health-Based Alerts

Send alerts based on health status.

```python
health = agent.get_health_status()

if health['status'] == 'unhealthy':
    await send_alert({
        "level": "critical",
        "agent_id": agent.agent_id,
        "message": f"Agent is unhealthy: {health['health_score']}/100",
        "issues": health['issues']
    })
elif health['status'] == 'degraded':
    await send_alert({
        "level": "warning",
        "agent_id": agent.agent_id,
        "message": f"Agent health degraded: {health['health_score']}/100"
    })
```

### Pattern 2: Performance-Based Alerts

Send alerts based on performance metrics.

```python
metrics = agent.get_metrics()
performance = agent.get_performance_metrics()

# Alert on high error rate
if metrics.total_tasks_executed > 0:
    error_rate = (metrics.failed_tasks / metrics.total_tasks_executed) * 100
    if error_rate > 20:
        await send_alert({
            "level": "warning",
            "agent_id": agent.agent_id,
            "message": f"High error rate: {error_rate}%"
        })

# Alert on slow performance
if performance['p95_response_time'] > 5.0:
    await send_alert({
        "level": "warning",
        "agent_id": agent.agent_id,
        "message": f"Slow P95 response time: {performance['p95_response_time']}s"
    })
```

### Pattern 3: Threshold-Based Alerts

Set thresholds for alerts.

```python
THRESHOLDS = {
    "error_rate": 10.0,  # 10%
    "p95_response_time": 3.0,  # 3 seconds
    "health_score": 70.0  # 70/100
}

metrics = agent.get_metrics()
performance = agent.get_performance_metrics()
health = agent.get_health_status()

# Check thresholds
if metrics.total_tasks_executed > 0:
    error_rate = (metrics.failed_tasks / metrics.total_tasks_executed) * 100
    if error_rate > THRESHOLDS["error_rate"]:
        await send_alert(f"Error rate threshold exceeded: {error_rate}%")

if performance['p95_response_time'] > THRESHOLDS["p95_response_time"]:
    await send_alert(f"P95 response time threshold exceeded: {performance['p95_response_time']}s")

if health['health_score'] < THRESHOLDS["health_score"]:
    await send_alert(f"Health score below threshold: {health['health_score']}")
```

## Best Practices

### 1. Monitor Regularly

Monitor metrics and health status regularly:

```python
# Check health every minute
async def monitor():
    while True:
        health = agent.get_health_status()
        if health['status'] != 'healthy':
            logger.warning(f"Health issue: {health}")
        await asyncio.sleep(60)
```

### 2. Track Key Metrics

Track key metrics for your use case:

```python
# Track success rate
metrics = agent.get_metrics()
if metrics.success_rate < 90:
    logger.warning(f"Low success rate: {metrics.success_rate}%")

# Track performance
performance = agent.get_performance_metrics()
if performance['p95_response_time'] > 3.0:
    logger.warning(f"Slow P95: {performance['p95_response_time']}s")
```

### 3. Set Appropriate Thresholds

Set thresholds based on your requirements:

```python
# Production thresholds
THRESHOLDS = {
    "success_rate": 95.0,
    "error_rate": 5.0,
    "p95_response_time": 2.0,
    "health_score": 80.0
}
```

### 4. Alert on Critical Issues

Alert on critical health issues:

```python
health = agent.get_health_status()
if health['status'] == 'unhealthy':
    await send_critical_alert(health)
```

### 5. Aggregate Metrics

Aggregate metrics across agents for system-wide monitoring:

```python
# Aggregate across all agents
all_metrics = [agent.get_metrics() for agent in all_agents]
overall_success_rate = sum(m.success_rate for m in all_metrics) / len(all_metrics)
```

## Summary

Performance monitoring and health status provide:
- ✅ Comprehensive metrics tracking
- ✅ Health score calculation (0-100)
- ✅ Operation-level performance tracking
- ✅ Percentile calculations
- ✅ Alerting capabilities
- ✅ Dashboard integration

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Session Management](./SESSION_MANAGEMENT.md)


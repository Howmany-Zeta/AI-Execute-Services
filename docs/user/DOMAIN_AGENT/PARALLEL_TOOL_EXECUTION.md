# Parallel Tool Execution Patterns

This guide covers how to use parallel tool execution to improve agent performance by executing multiple independent tools concurrently.

## Table of Contents

1. [Overview](#overview)
2. [Basic Parallel Execution](#basic-parallel-execution)
3. [Concurrency Control](#concurrency-control)
4. [Dependency Handling](#dependency-handling)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)
7. [Best Practices](#best-practices)

## Overview

Parallel tool execution allows agents to execute multiple independent tools concurrently, providing:

- **3-5x Performance Improvement**: Execute tools in parallel instead of sequentially
- **Automatic Dependency Detection**: Automatically detects tool dependencies
- **Concurrency Control**: Configurable maximum concurrency limits
- **Error Isolation**: Errors in one tool don't block others

### When to Use Parallel Execution

- ✅ Multiple independent tools need to be executed
- ✅ Tools don't depend on each other's results
- ✅ Performance is critical
- ✅ Tools have I/O-bound operations (API calls, database queries)

### When NOT to Use Parallel Execution

- ❌ Tools depend on each other's results
- ❌ Sequential execution is required
- ❌ Resource constraints limit concurrency
- ❌ Tools have strict ordering requirements

## Basic Parallel Execution

### Pattern 1: Simple Parallel Execution

Execute multiple independent tools in parallel.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator", "translator"],
    config=AgentConfiguration()
)

await agent.initialize()

# Execute multiple tools in parallel
tool_calls = [
    {"tool_name": "search", "parameters": {"query": "AI"}},
    {"tool_name": "calculator", "parameters": {"operation": "add", "a": 1, "b": 2}},
    {"tool_name": "translator", "parameters": {"text": "Hello", "target": "es"}}
]

results = await agent.execute_tools_parallel(tool_calls)

# Results are in same order as tool_calls
for i, result in enumerate(results):
    if result["success"]:
        print(f"Tool {tool_calls[i]['tool_name']}: {result['result']}")
    else:
        print(f"Tool {tool_calls[i]['tool_name']} failed: {result['error']}")
```

### Pattern 2: With Concurrency Limit

Control maximum concurrent executions.

```python
# Execute with max 3 concurrent tools
results = await agent.execute_tools_parallel(
    tool_calls,
    max_concurrency=3  # Maximum 3 tools at once
)
```

### Pattern 3: Automatic Detection

Agent automatically detects independent tools.

```python
# Agent automatically detects independent tools and executes in parallel
result = await agent.execute_task(
    {
        "description": "Search for Python, calculate 2+2, and translate 'Hello' to Spanish"
    },
    {}
)
# All three tools execute concurrently automatically!
```

## Concurrency Control

### Pattern 1: Default Concurrency

Use default concurrency (5 tools).

```python
# Default max_concurrency is 5
results = await agent.execute_tools_parallel(tool_calls)
```

### Pattern 2: Custom Concurrency

Set custom concurrency limit.

```python
# Limit to 2 concurrent tools
results = await agent.execute_tools_parallel(
    tool_calls,
    max_concurrency=2
)
```

### Pattern 3: High Concurrency

Increase concurrency for many tools.

```python
# Execute up to 10 tools concurrently
results = await agent.execute_tools_parallel(
    tool_calls,
    max_concurrency=10
)
```

### Pattern 4: Resource-Based Concurrency

Adjust concurrency based on available resources.

```python
import os

# Adjust concurrency based on CPU count
cpu_count = os.cpu_count() or 4
max_concurrency = min(cpu_count * 2, 10)  # Max 10

results = await agent.execute_tools_parallel(
    tool_calls,
    max_concurrency=max_concurrency
)
```

## Dependency Handling

### Pattern 1: Independent Tools

Execute independent tools in parallel.

```python
# These tools are independent - execute in parallel
independent_tools = [
    {"tool_name": "search", "parameters": {"query": "Python"}},
    {"tool_name": "weather", "parameters": {"location": "NYC"}},
    {"tool_name": "calculator", "parameters": {"operation": "multiply", "a": 5, "b": 3}}
]

results = await agent.execute_tools_parallel(independent_tools)
# All execute concurrently
```

### Pattern 2: Dependent Tools

Execute dependent tools sequentially.

```python
# Tool 2 depends on Tool 1 result - execute sequentially
result1 = await agent.execute_tool("search", {"query": "Python"})
result2 = await agent.execute_tool("analyze", {"data": result1})

# Or use agent's automatic dependency detection
result = await agent.execute_task(
    {
        "description": "Search for Python and then analyze the results"
    },
    {}
)
# Agent detects dependency and executes sequentially
```

### Pattern 3: Mixed Dependencies

Mix parallel and sequential execution.

```python
# Step 1: Execute independent tools in parallel
parallel_results = await agent.execute_tools_parallel([
    {"tool_name": "search", "parameters": {"query": "Python"}},
    {"tool_name": "weather", "parameters": {"location": "NYC"}}
])

# Step 2: Use results for dependent tools
search_result = parallel_results[0]["result"]
weather_result = parallel_results[1]["result"]

# Step 3: Execute dependent tool
analysis_result = await agent.execute_tool(
    "analyze",
    {"search": search_result, "weather": weather_result}
)
```

## Error Handling

### Pattern 1: Individual Error Handling

Handle errors for each tool individually.

```python
results = await agent.execute_tools_parallel(tool_calls)

for i, result in enumerate(results):
    if result["success"]:
        print(f"Tool {i} succeeded: {result['result']}")
    else:
        print(f"Tool {i} failed: {result['error']}")
        # Handle error for this specific tool
```

### Pattern 2: Partial Success

Continue with successful results even if some tools fail.

```python
results = await agent.execute_tools_parallel(tool_calls)

# Filter successful results
successful_results = [r for r in results if r["success"]]
failed_results = [r for r in results if not r["success"]]

# Continue with successful results
if successful_results:
    # Process successful results
    process_results(successful_results)

# Handle failures
if failed_results:
    logger.warning(f"{len(failed_results)} tools failed")
    retry_failed_tools(failed_results)
```

### Pattern 3: Retry Failed Tools

Retry failed tools automatically.

```python
results = await agent.execute_tools_parallel(tool_calls)

# Identify failed tools
failed_tools = [
    tool_calls[i] for i, r in enumerate(results) if not r["success"]
]

# Retry failed tools
if failed_tools:
    retry_results = await agent.execute_tools_parallel(failed_tools)
    # Merge results
    for i, result in enumerate(retry_results):
        if result["success"]:
            # Update original results
            original_index = tool_calls.index(failed_tools[i])
            results[original_index] = result
```

## Performance Optimization

### Pattern 1: Batch Execution

Batch multiple tool calls for better performance.

```python
# Batch 10 tool calls
batches = [tool_calls[i:i+10] for i in range(0, len(tool_calls), 10)]

all_results = []
for batch in batches:
    batch_results = await agent.execute_tools_parallel(batch, max_concurrency=5)
    all_results.extend(batch_results)
```

### Pattern 2: Priority-Based Execution

Execute high-priority tools first.

```python
# Sort tools by priority
priority_tools = sorted(tool_calls, key=lambda x: x.get("priority", 0), reverse=True)

# Execute high-priority tools first
high_priority = [t for t in priority_tools if t.get("priority", 0) > 5]
low_priority = [t for t in priority_tools if t.get("priority", 0) <= 5]

# Execute high-priority tools first
high_results = await agent.execute_tools_parallel(high_priority)
low_results = await agent.execute_tools_parallel(low_priority)
```

### Pattern 3: Timeout Handling

Set timeouts for tool execution.

```python
import asyncio

async def execute_with_timeout(tool_calls, timeout=30):
    """Execute tools with timeout"""
    try:
        results = await asyncio.wait_for(
            agent.execute_tools_parallel(tool_calls),
            timeout=timeout
        )
        return results
    except asyncio.TimeoutError:
        logger.error(f"Tool execution timed out after {timeout}s")
        return None

results = await execute_with_timeout(tool_calls, timeout=30)
```

## Best Practices

### 1. Use Parallel Execution for Independent Tools

Only use parallel execution for tools that don't depend on each other:

```python
# Good: Independent tools
independent_tools = [
    {"tool_name": "search", "parameters": {"query": "Python"}},
    {"tool_name": "weather", "parameters": {"location": "NYC"}}
]
results = await agent.execute_tools_parallel(independent_tools)

# Bad: Dependent tools (execute sequentially)
result1 = await agent.execute_tool("search", {"query": "Python"})
result2 = await agent.execute_tool("analyze", {"data": result1})  # Depends on result1
```

### 2. Set Appropriate Concurrency Limits

Set concurrency limits based on your resources:

```python
# For API-limited tools
results = await agent.execute_tools_parallel(tool_calls, max_concurrency=3)

# For CPU-bound tools
results = await agent.execute_tools_parallel(tool_calls, max_concurrency=os.cpu_count())
```

### 3. Handle Errors Gracefully

Always handle errors for individual tools:

```python
results = await agent.execute_tools_parallel(tool_calls)

for result in results:
    if not result["success"]:
        logger.error(f"Tool failed: {result['error']}")
        # Handle error appropriately
```

### 4. Monitor Performance

Monitor parallel execution performance:

```python
import time

start = time.time()
results = await agent.execute_tools_parallel(tool_calls)
duration = time.time() - start

print(f"Executed {len(tool_calls)} tools in {duration:.2f}s")
print(f"Average time per tool: {duration / len(tool_calls):.2f}s")
```

### 5. Use for I/O-Bound Operations

Parallel execution is most effective for I/O-bound operations:

```python
# Good: API calls, database queries
io_bound_tools = [
    {"tool_name": "api_call", "parameters": {...}},
    {"tool_name": "db_query", "parameters": {...}}
]
results = await agent.execute_tools_parallel(io_bound_tools)

# Less effective: CPU-bound operations
cpu_bound_tools = [
    {"tool_name": "calculate", "parameters": {"complex": True}}
]
# May not benefit much from parallel execution
```

## Summary

Parallel tool execution provides:
- ✅ 3-5x performance improvement
- ✅ Automatic dependency detection
- ✅ Configurable concurrency limits
- ✅ Error isolation
- ✅ Better resource utilization

**Key Takeaways**:
- Use for independent tools
- Set appropriate concurrency limits
- Handle errors gracefully
- Monitor performance
- Best for I/O-bound operations

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Tool Caching](./TOOL_CACHING.md)


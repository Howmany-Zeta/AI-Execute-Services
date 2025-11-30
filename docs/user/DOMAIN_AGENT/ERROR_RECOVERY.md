# Error Recovery Strategies

This guide covers how to configure and use error recovery strategies to improve agent reliability and success rates through automatic retry, task simplification, fallback approaches, and delegation.

## Table of Contents

1. [Overview](#overview)
2. [Recovery Strategies](#recovery-strategies)
3. [Basic Recovery Configuration](#basic-recovery-configuration)
4. [Strategy Chains](#strategy-chains)
5. [Custom Recovery Logic](#custom-recovery-logic)
6. [Error Classification](#error-classification)
7. [Best Practices](#best-practices)

## Overview

Error recovery strategies provide:

- **Automatic Retry**: Retry failed tasks with exponential backoff
- **Task Simplification**: Break down complex tasks into simpler ones
- **Fallback Approaches**: Use alternative methods when primary fails
- **Delegation**: Delegate tasks to other capable agents
- **Error Classification**: Classify errors for appropriate recovery

### Recovery Strategies

1. **RETRY**: Retry with exponential backoff (for transient errors)
2. **SIMPLIFY**: Simplify task and retry (break down complex tasks)
3. **FALLBACK**: Use fallback approach or alternative method
4. **DELEGATE**: Delegate to another capable agent
5. **ABORT**: Abort execution and return error (terminal strategy)

## Recovery Strategies

### Strategy 1: RETRY

Retry failed tasks with exponential backoff.

**Use When**:
- Transient errors (network, timeout, rate limits)
- Temporary failures
- Errors likely to succeed on retry

**Example**:
```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.domain.agent.models import RecoveryStrategy
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search"],
    config=AgentConfiguration(),
    recovery_strategies=[RecoveryStrategy.RETRY]
)

await agent.initialize()

# Execute with retry recovery
result = await agent.execute_with_recovery(
    task={"description": "Search for Python"},
    context={},
    strategies=[RecoveryStrategy.RETRY]
)
```

### Strategy 2: SIMPLIFY

Simplify complex tasks and retry.

**Use When**:
- Task is too complex
- Breaking down helps
- Simpler version likely to succeed

**Example**:
```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    recovery_strategies=[RecoveryStrategy.SIMPLIFY]
)

# Execute with simplification recovery
result = await agent.execute_with_recovery(
    task={"description": "Complex multi-step task"},
    context={},
    strategies=[RecoveryStrategy.SIMPLIFY]
)
# Task simplified and retried automatically
```

### Strategy 3: FALLBACK

Use fallback approach when primary fails.

**Use When**:
- Alternative approach available
- Primary method failed
- Fallback method acceptable

**Example**:
```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search", "fallback_search"],
    config=config,
    recovery_strategies=[RecoveryStrategy.FALLBACK]
)

# Execute with fallback recovery
result = await agent.execute_with_recovery(
    task={"description": "Search task"},
    context={},
    strategies=[RecoveryStrategy.FALLBACK]
)
# Falls back to alternative tool if primary fails
```

### Strategy 4: DELEGATE

Delegate task to another capable agent.

**Use When**:
- Other agents available
- Current agent lacks capability
- Delegation appropriate

**Example**:
```python
# Create agent registry
agent_registry = {
    "specialist-agent": specialist_agent
}

agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    collaboration_enabled=True,
    agent_registry=agent_registry,
    recovery_strategies=[RecoveryStrategy.DELEGATE]
)

# Execute with delegation recovery
result = await agent.execute_with_recovery(
    task={"description": "Specialized task"},
    context={},
    strategies=[RecoveryStrategy.DELEGATE]
)
# Delegated to specialist agent if current agent fails
```

### Strategy 5: ABORT

Abort execution and return error.

**Use When**:
- All recovery attempts exhausted
- Error is terminal
- No further recovery possible

**Example**:
```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    recovery_strategies=[RecoveryStrategy.ABORT]
)

# Execute with abort recovery
try:
    result = await agent.execute_with_recovery(
        task={"description": "Task"},
        context={},
        strategies=[RecoveryStrategy.ABORT]
    )
except Exception as e:
    # Abort strategy returns error immediately
    print(f"Task aborted: {e}")
```

## Basic Recovery Configuration

### Pattern 1: Single Strategy

Use single recovery strategy.

```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    recovery_strategies=[RecoveryStrategy.RETRY]
)

# Execute with retry
result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=[RecoveryStrategy.RETRY]
)
```

### Pattern 2: Multiple Strategies

Use multiple recovery strategies.

```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    recovery_strategies=[
        RecoveryStrategy.RETRY,
        RecoveryStrategy.SIMPLIFY,
        RecoveryStrategy.FALLBACK
    ]
)

# Execute with multiple strategies (tried in order)
result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=[
        RecoveryStrategy.RETRY,
        RecoveryStrategy.SIMPLIFY,
        RecoveryStrategy.FALLBACK
    ]
)
```

### Pattern 3: Default Strategies

Use default recovery strategies from agent configuration.

```python
agent = HybridAgent(
    agent_id="agent-1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    recovery_strategies=[
        RecoveryStrategy.RETRY,
        RecoveryStrategy.SIMPLIFY,
        RecoveryStrategy.FALLBACK
    ]
)

# Uses default strategies from agent configuration
result = await agent.execute_with_recovery(task, context)
```

## Strategy Chains

### Pattern 1: Full Recovery Chain

Use complete recovery chain.

```python
strategies = [
    RecoveryStrategy.RETRY,      # Try retry first
    RecoveryStrategy.SIMPLIFY,    # Then simplify
    RecoveryStrategy.FALLBACK,    # Then fallback
    RecoveryStrategy.DELEGATE,    # Then delegate
    RecoveryStrategy.ABORT        # Finally abort
]

result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=strategies
)
```

### Pattern 2: Conservative Chain

Use conservative recovery chain (no delegation).

```python
strategies = [
    RecoveryStrategy.RETRY,
    RecoveryStrategy.SIMPLIFY,
    RecoveryStrategy.FALLBACK
    # No delegation - keep within current agent
]

result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=strategies
)
```

### Pattern 3: Quick Fail Chain

Use quick fail chain (abort early).

```python
strategies = [
    RecoveryStrategy.RETRY,
    RecoveryStrategy.ABORT  # Abort after retry
]

result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=strategies
)
```

## Custom Recovery Logic

### Pattern 1: Custom Retry Logic

Implement custom retry logic.

```python
class CustomAgent(HybridAgent):
    async def _execute_with_retry(self, func, *args, **kwargs):
        """Custom retry logic"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                # Custom delay logic
                await asyncio.sleep(2 ** attempt)
```

### Pattern 2: Custom Simplification

Implement custom task simplification.

```python
class CustomAgent(HybridAgent):
    async def _simplify_task(self, task):
        """Custom task simplification"""
        description = task.get("description", "")
        
        # Break down complex task
        if "and" in description.lower():
            # Split into multiple tasks
            parts = description.split(" and ")
            return {
                "description": parts[0],  # First part only
                "simplified": True
            }
        
        return task
```

### Pattern 3: Custom Fallback

Implement custom fallback logic.

```python
class CustomAgent(HybridAgent):
    async def _execute_with_fallback(self, task, context):
        """Custom fallback logic"""
        try:
            # Try primary approach
            return await self.execute_task(task, context)
        except Exception:
            # Use fallback tool
            fallback_task = {
                **task,
                "tool": "fallback_search"  # Use fallback tool
            }
            return await self.execute_task(fallback_task, context)
```

## Error Classification

### Pattern 1: Error-Based Strategy Selection

Select strategy based on error type.

```python
try:
    result = await agent.execute_task(task, context)
except TimeoutError:
    # Use retry for timeout
    result = await agent.execute_with_recovery(
        task, context,
        strategies=[RecoveryStrategy.RETRY]
    )
except ValueError:
    # Use simplify for validation errors
    result = await agent.execute_with_recovery(
        task, context,
        strategies=[RecoveryStrategy.SIMPLIFY]
    )
except Exception as e:
    # Use full chain for unknown errors
    result = await agent.execute_with_recovery(
        task, context,
        strategies=[
            RecoveryStrategy.RETRY,
            RecoveryStrategy.SIMPLIFY,
            RecoveryStrategy.FALLBACK
        ]
    )
```

### Pattern 2: Automatic Error Classification

Agent automatically classifies errors.

```python
# Agent automatically classifies errors and selects appropriate strategy
result = await agent.execute_with_recovery(
    task=task,
    context=context,
    strategies=[
        RecoveryStrategy.RETRY,      # For transient errors
        RecoveryStrategy.SIMPLIFY,    # For complex tasks
        RecoveryStrategy.FALLBACK     # For other errors
    ]
)
```

## Best Practices

### 1. Use Appropriate Strategy Order

Order strategies from least to most expensive:

```python
strategies = [
    RecoveryStrategy.RETRY,      # Cheapest - just retry
    RecoveryStrategy.SIMPLIFY,   # Moderate - simplify task
    RecoveryStrategy.FALLBACK,   # Moderate - use alternative
    RecoveryStrategy.DELEGATE,   # Expensive - delegate to another agent
    RecoveryStrategy.ABORT       # Terminal - give up
]
```

### 2. Configure Based on Error Types

Configure strategies based on expected error types:

```python
# For network-heavy tasks
strategies = [
    RecoveryStrategy.RETRY,  # Retry network errors
    RecoveryStrategy.FALLBACK  # Use alternative endpoint
]

# For complex tasks
strategies = [
    RecoveryStrategy.SIMPLIFY,  # Break down complex tasks
    RecoveryStrategy.DELEGATE   # Delegate to specialist
]
```

### 3. Limit Recovery Attempts

Limit total recovery attempts:

```python
# Limit to 3 total attempts
strategies = [
    RecoveryStrategy.RETRY,      # 1 attempt
    RecoveryStrategy.SIMPLIFY,   # 1 attempt
    RecoveryStrategy.FALLBACK,   # 1 attempt
    RecoveryStrategy.ABORT      # Give up
]
```

### 4. Monitor Recovery Success

Monitor recovery success rates:

```python
recovery_attempts = 0
recovery_successes = 0

try:
    result = await agent.execute_task(task, context)
except Exception:
    recovery_attempts += 1
    result = await agent.execute_with_recovery(
        task, context,
        strategies=[RecoveryStrategy.RETRY]
    )
    recovery_successes += 1

success_rate = recovery_successes / recovery_attempts if recovery_attempts > 0 else 0
print(f"Recovery success rate: {success_rate:.1%}")
```

### 5. Handle Recovery Failures

Handle cases where all recovery strategies fail:

```python
try:
    result = await agent.execute_with_recovery(
        task=task,
        context=context,
        strategies=[
            RecoveryStrategy.RETRY,
            RecoveryStrategy.SIMPLIFY,
            RecoveryStrategy.FALLBACK,
            RecoveryStrategy.ABORT
        ]
    )
except Exception as e:
    # All recovery strategies failed
    logger.error(f"All recovery strategies failed: {e}")
    # Handle final failure
    handle_final_failure(e)
```

## Summary

Error recovery strategies provide:
- ✅ Automatic retry with backoff
- ✅ Task simplification
- ✅ Fallback approaches
- ✅ Task delegation
- ✅ Error classification

**Key Takeaways**:
- Order strategies from least to most expensive
- Configure based on error types
- Limit recovery attempts
- Monitor recovery success
- Handle recovery failures

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Collaboration](./COLLABORATION.md)


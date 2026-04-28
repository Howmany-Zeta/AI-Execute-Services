# Streaming Response Usage

This guide covers how to use agent-level streaming to receive tokens, tool calls, and results as they're generated, providing better user experience for long-running operations.

## Table of Contents

1. [Overview](#overview)
2. [Basic Streaming](#basic-streaming)
3. [Streaming Task Execution](#streaming-task-execution)
4. [Streaming Message Processing](#streaming-message-processing)
5. [Event Types](#event-types)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)

## Overview

Agent-level streaming provides:

- **Real-Time Feedback**: See tokens and tool calls as they happen
- **Better UX**: Users see progress instead of waiting for complete response
- **Tool Call Visibility**: See which tools are being called in real-time
- **Result Streaming**: Receive tool results as they're generated
- **Status Updates**: Get status updates throughout execution

### When to Use Streaming

- ✅ Long-running tasks
- ✅ Interactive applications
- ✅ Real-time user feedback needed
- ✅ Tool call visibility important
- ✅ Progressive result display

### When NOT to Use Streaming

- ❌ Simple, fast operations
- ❌ Batch processing
- ❌ Complete result needed before processing
- ❌ Non-interactive applications

## Basic Streaming

### Pattern 1: Stream Task Execution

Stream task execution with tokens and tool calls.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator"],
    config=AgentConfiguration()
)

await agent.initialize()

# Stream task execution
async for event in agent.execute_task_streaming(
    {"description": "Research Python and calculate 2+2"},
    {}
):
    if event['type'] == 'token':
        # Stream tokens as they're generated
        print(event['content'], end='', flush=True)
    elif event['type'] == 'tool_call':
        # Tool call started
        print(f"\nCalling {event['tool_name']}...")
    elif event['type'] == 'tool_result':
        # Tool result received
        print(f"\nResult: {event['result']}")
    elif event['type'] == 'started':
        # Lifecycle: task execution started
        print("\n[Started]")
    elif event['type'] == 'completed':
        # Lifecycle: task execution completed (HybridAgent only)
        print(f"\n[Completed in {event['execution_time']:.2f}s]")
```

### Pattern 2: Stream Message Processing

Stream message processing for conversational agents.

```python
# Stream message processing
async for token in agent.process_message_streaming("Hello, how are you?"):
    print(token, end='', flush=True)
```

### Pattern 3: Collect Streamed Results

Collect streamed results for processing.

```python
tokens = []
tool_calls = []
results = []

async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        tokens.append(event['content'])
    elif event['type'] == 'tool_call':
        tool_calls.append(event)
    elif event['type'] == 'tool_result':
        results.append(event)

# Process collected results
full_response = ''.join(tokens)
print(f"Full response: {full_response}")
print(f"Tool calls: {len(tool_calls)}")
print(f"Results: {len(results)}")
```

## Streaming Task Execution

### Pattern 1: Basic Task Streaming

Stream basic task execution.

```python
async for event in agent.execute_task_streaming(
    {"description": "Answer a question"},
    {}
):
    if event['type'] == 'token':
        print(event['content'], end='', flush=True)
    elif event['type'] == 'result':
        print(f"\nFinal result: {event['output']}")
```

### Pattern 2: ReAct Loop Streaming

Stream ReAct loop execution (HybridAgent). `HybridAgent` emits dedicated
`thought` / `action` / `observation` events for each ReAct phase, plus
`iteration_start` events that mark the boundary between iterations.

```python
async for event in agent.execute_task_streaming(
    {"description": "Research and analyze"},
    {}
):
    if event['type'] == 'token':
        # Stream reasoning tokens
        print(event['content'], end='', flush=True)
    elif event['type'] == 'iteration_start':
        # New ReAct iteration begins
        print(f"\n[Iteration {event['iteration']}]")
    elif event['type'] == 'thought':
        # Reasoning text accumulated for this iteration
        print(f"\n[Thought] {event['content']}")
    elif event['type'] == 'action':
        # Tool action selected by the model
        print(f"\n[Action] {event['tool_name']}")
    elif event['type'] == 'tool_result':
        # Raw tool result
        print(f"\n[Result] {event['result']}")
    elif event['type'] == 'observation':
        # Observation derived from the tool result
        print(f"\n[Observation] {event['content']}")
```

### Pattern 3: Lifecycle Tracking

Track execution lifecycle through streaming. `ToolAgent` and `HybridAgent`
emit `started` at the beginning and (in `HybridAgent`) `completed` at the
end; `HybridAgent` additionally emits `iteration_start` per ReAct loop.

```python
async for event in agent.execute_task_streaming(task, context):
    etype = event['type']

    if etype == 'started':
        print("Agent started")
    elif etype == 'iteration_start':
        # HybridAgent only — ReAct iteration boundary
        print(f"Iteration {event['iteration']} starting")
    elif etype == 'completed':
        # HybridAgent only — symmetric to 'started'
        print(f"Agent completed (success={event['success']})")
    elif etype == 'result':
        # Final result payload (all agents)
        print(f"Final output: {event['output']}")
```

## Streaming Message Processing

### Pattern 1: Conversational Streaming

Stream conversational responses.

```python
async for token in agent.process_message_streaming("Tell me about Python"):
    print(token, end='', flush=True)
```

### Pattern 2: Multi-Turn Streaming

Stream multi-turn conversations.

```python
# First message
async for token in agent.process_message_streaming("Hello"):
    print(token, end='', flush=True)

# Second message
async for token in agent.process_message_streaming("What can you do?"):
    print(token, end='', flush=True)
```

### Pattern 3: Streaming with Context

Stream with session context.

```python
async for token in agent.process_message_streaming(
    "Continue our conversation",
    sender_id="user-123"
):
    print(token, end='', flush=True)
```

## Event Types

### Token Events

Token events contain generated text tokens.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        content = event['content']  # Token text
        timestamp = event.get('timestamp')  # Optional timestamp
        print(content, end='', flush=True)
```

### Tool Call Events

Tool call events indicate when tools are being called.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'tool_call':
        tool_name = event['tool_name']
        parameters = event.get('parameters', {})
        timestamp = event.get('timestamp')
        
        print(f"Calling {tool_name} with {parameters}")
```

### Tool Result Events

Tool result events contain tool execution results.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'tool_result':
        tool_name = event['tool_name']
        result = event['result']
        success = event.get('success', True)
        timestamp = event.get('timestamp')
        
        if success:
            print(f"{tool_name} returned: {result}")
        else:
            print(f"{tool_name} failed: {result}")
```

### Status Events

Status events indicate execution status. Emitted by `BaseAgent` (default
implementation) and `LLMAgent`; `status` is always `"started"` in the
current implementation.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'status':
        status = event['status']  # currently always "started"
        timestamp = event.get('timestamp')

        print(f"Status: {status}")
```

### Lifecycle Events

`ToolAgent` and `HybridAgent` emit dedicated lifecycle events instead of
`status`. `started` is emitted at the beginning of streaming execution;
`completed` is emitted by `HybridAgent` only, as the symmetric counterpart
to `started`.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'started':
        timestamp = event.get('timestamp')
        print("Execution started")
    elif event['type'] == 'completed':
        success = event['success']
        execution_time = event['execution_time']
        print(f"Execution completed (success={success}, {execution_time:.2f}s)")
```

### ReAct Events (HybridAgent)

`HybridAgent` exposes the ReAct loop as discrete events. `iteration_start`
marks the boundary between iterations; `thought`, `action`, and
`observation` correspond to the three phases of each iteration.

```python
async for event in agent.execute_task_streaming(task, context):
    etype = event['type']
    if etype == 'iteration_start':
        print(f"Iteration {event['iteration']} starting")
    elif etype == 'thought':
        print(f"Thought: {event['content']}")
    elif etype == 'action':
        print(f"Action: {event['tool_name']}({event.get('parameters', {})})")
    elif etype == 'observation':
        print(f"Observation: {event['content']}")
```

### Tool Streaming Events (ToolAgent / HybridAgent)

In addition to `tool_call` and `tool_result`, the Function Calling
streaming path emits two finer-grained events:

- `tool_call_delta`: incremental tool-call fragment received from the
  provider stream (arguments may still be partial).
- `tool_calls_ready`: complete batch of tool calls assembled from the
  stream, ready to be dispatched.

`ToolAgent` also emits `tool_error` when a tool invocation fails.

### Result Events

Result events contain final task results.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'result':
        output = event['output']
        execution_time = event.get('execution_time')
        success = event.get('success', True)
        
        print(f"Final result: {output}")
        print(f"Execution time: {execution_time}s")
```

### Error Events

Error events indicate errors during execution.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'error':
        error = event['error']
        timestamp = event.get('timestamp')
        
        print(f"Error: {error}")
```

## Error Handling

### Pattern 1: Handle Streaming Errors

Handle errors during streaming.

```python
try:
    async for event in agent.execute_task_streaming(task, context):
        if event['type'] == 'error':
            print(f"Error: {event['error']}")
            break
        # Process other events
except Exception as e:
    print(f"Streaming failed: {e}")
```

### Pattern 2: Continue on Errors

Continue processing despite errors.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'error':
        logger.error(f"Error: {event['error']}")
        # Continue processing other events
        continue
    # Process event
```

### Pattern 3: Retry on Errors

Retry streaming on errors.

```python
max_retries = 3
retry_count = 0

while retry_count < max_retries:
    try:
        async for event in agent.execute_task_streaming(task, context):
            # Process events
            pass
        break  # Success
    except Exception as e:
        retry_count += 1
        if retry_count >= max_retries:
            raise
        await asyncio.sleep(1)
```

## Best Practices

### 1. Use Streaming for Long Operations

Use streaming for operations that take time:

```python
# Good: Long-running task
async for event in agent.execute_task_streaming(
    {"description": "Research and analyze complex topic"},
    {}
):
    # Stream progress
    pass

# Less useful: Fast operation
result = await agent.execute_task(
    {"description": "Simple calculation"},
    {}
)
```

### 2. Provide User Feedback

Provide feedback to users during streaming. Use the lifecycle and ReAct
events emitted by `ToolAgent` / `HybridAgent` (or `status="started"` for
`LLMAgent`) to drive UI affordances:

```python
async for event in agent.execute_task_streaming(task, context):
    etype = event['type']
    if etype in ('started', 'status'):
        show_spinner("Working...")
    elif etype == 'thought':
        show_spinner("Thinking...")
    elif etype in ('action', 'tool_call'):
        show_spinner(f"Executing {event.get('tool_name', 'tool')}...")
    elif etype in ('completed', 'result', 'error'):
        hide_spinner()
```

### 3. Handle Partial Results

Handle partial results gracefully:

```python
tokens = []
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        tokens.append(event['content'])
        # Display partial result
        display_partial(''.join(tokens))
    elif event['type'] == 'result':
        # Final result
        display_final(event['output'])
```

### 4. Monitor Streaming Performance

Monitor streaming performance:

```python
import time

start = time.time()
token_count = 0

async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        token_count += 1
    elif event['type'] == 'result':
        duration = time.time() - start
        tokens_per_second = token_count / duration
        print(f"Streaming rate: {tokens_per_second:.1f} tokens/s")
```

### 5. Buffer for Smooth Display

Buffer tokens for smooth display:

```python
buffer = []
buffer_size = 10

async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'token':
        buffer.append(event['content'])
        if len(buffer) >= buffer_size:
            # Display buffered tokens
            print(''.join(buffer), end='', flush=True)
            buffer.clear()
    
# Display remaining tokens
if buffer:
    print(''.join(buffer), end='', flush=True)
```

## Summary

Streaming provides:
- ✅ Real-time feedback
- ✅ Better user experience
- ✅ Tool call visibility
- ✅ Progressive result display
- ✅ Status updates

**Key Takeaways**:
- Use for long-running operations
- Provide user feedback
- Handle partial results
- Monitor performance
- Buffer for smooth display

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)


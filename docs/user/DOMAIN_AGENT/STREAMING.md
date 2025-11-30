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
    elif event['type'] == 'status':
        # Status update
        print(f"\nStatus: {event['status']}")
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

Stream ReAct loop execution (HybridAgent).

```python
async for event in agent.execute_task_streaming(
    {"description": "Research and analyze"},
    {}
):
    if event['type'] == 'token':
        # Stream reasoning tokens
        print(event['content'], end='', flush=True)
    elif event['type'] == 'tool_call':
        # Tool call in ReAct loop
        print(f"\n[Tool Call] {event['tool_name']}")
    elif event['type'] == 'tool_result':
        # Tool result
        print(f"\n[Result] {event['result']}")
    elif event['type'] == 'status':
        # Status update (thinking, acting, observing)
        print(f"\n[Status] {event['status']}")
```

### Pattern 3: Status Tracking

Track execution status through streaming.

```python
current_status = None

async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'status':
        current_status = event['status']
        print(f"Status: {current_status}")
        
        if current_status == 'thinking':
            print("Agent is thinking...")
        elif current_status == 'acting':
            print("Agent is executing tools...")
        elif current_status == 'observing':
            print("Agent is observing results...")
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

Status events indicate execution status.

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'status':
        status = event['status']  # started, thinking, acting, observing, completed
        iteration = event.get('iteration')  # ReAct iteration number
        timestamp = event.get('timestamp')
        
        print(f"Status: {status} (iteration {iteration})")
```

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

Provide feedback to users during streaming:

```python
async for event in agent.execute_task_streaming(task, context):
    if event['type'] == 'status':
        status = event['status']
        if status == 'thinking':
            show_spinner("Thinking...")
        elif status == 'acting':
            show_spinner("Executing tools...")
        elif status == 'completed':
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


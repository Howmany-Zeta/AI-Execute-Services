# Observation-Based Reasoning Loops

This guide provides comprehensive examples of observation-based reasoning loops using ToolObservation pattern for ReAct-style reasoning, debugging, and analysis.

## Table of Contents

1. [Overview](#overview)
2. [Basic ReAct Loop](#basic-react-loop)
3. [Advanced Reasoning Loops](#advanced-reasoning-loops)
4. [Multi-Tool Reasoning](#multi-tool-reasoning)
5. [Error Recovery in Loops](#error-recovery-in-loops)
6. [Observation Analysis](#observation-analysis)
7. [Best Practices](#best-practices)

## Overview

Observation-based reasoning loops enable:

- **Structured Reasoning**: Use ToolObservation for structured reasoning
- **Error Tracking**: Track errors in reasoning loops
- **Performance Analysis**: Analyze execution time
- **LLM Integration**: Format observations for LLM context
- **Debugging**: Debug reasoning loops with structured observations

### When to Use Observation-Based Reasoning

- ✅ ReAct-style reasoning loops
- ✅ Multi-step tool execution
- ✅ Error recovery and debugging
- ✅ Performance analysis
- ✅ LLM context building

## Basic ReAct Loop

### Pattern 1: Simple ReAct Loop

Basic ReAct loop with observations.

```python
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.llm import OpenAIClient, LLMMessage
from aiecs.domain.agent.models import ToolObservation

agent = HybridAgent(
    agent_id="agent-1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator"],
    config=AgentConfiguration()
)

await agent.initialize()

async def react_loop(task: str, max_iterations: int = 5):
    """Basic ReAct loop with observations"""
    observations = []
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content=task)
    ]
    
    for iteration in range(max_iterations):
        # Think: LLM reasoning
        thought_response = await agent.llm_client.generate_text(
            messages=messages,
            model=agent._config.llm_model
        )
        thought = thought_response.content
        
        # Check if final answer
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act: Execute tool if needed
        if "TOOL:" in thought:
            # Parse tool call
            tool_call = parse_tool_call(thought)
            
            # Execute tool with observation
            obs = await agent._execute_tool_with_observation(
                tool_name=tool_call["tool"],
                operation=tool_call.get("operation"),
                parameters=tool_call.get("parameters", {})
            )
            observations.append(obs)
            
            # Observe: Add observation to context
            observation_text = obs.to_text()
            messages.append(LLMMessage(role="assistant", content=thought))
            messages.append(LLMMessage(role="user", content=f"Observation:\n{observation_text}"))
        else:
            # No tool call - add thought to context
            messages.append(LLMMessage(role="assistant", content=thought))
    
    return "Max iterations reached"

# Use ReAct loop
result = await react_loop("Search for Python and calculate 2+2")
```

### Pattern 2: ReAct Loop with History

ReAct loop with observation history.

```python
class ObservationHistory:
    """Maintain observation history"""
    
    def __init__(self):
        self.observations = []
    
    def add(self, obs: ToolObservation):
        """Add observation to history"""
        self.observations.append(obs)
    
    def get_text(self) -> str:
        """Get formatted history"""
        return "\n\n".join([obs.to_text() for obs in self.observations])
    
    def get_successful(self) -> list:
        """Get successful observations"""
        return [obs for obs in self.observations if obs.success]
    
    def get_failed(self) -> list:
        """Get failed observations"""
        return [obs for obs in self.observations if not obs.success]

async def react_loop_with_history(task: str, max_iterations: int = 5):
    """ReAct loop with observation history"""
    history = ObservationHistory()
    messages = [
        LLMMessage(role="system", content="You are a helpful assistant."),
        LLMMessage(role="user", content=task)
    ]
    
    for iteration in range(max_iterations):
        # Add history to context
        if history.observations:
            history_text = history.get_text()
            messages.append(LLMMessage(
                role="system",
                content=f"Previous observations:\n{history_text}"
            ))
        
        # Think
        thought_response = await agent.llm_client.generate_text(messages=messages)
        thought = thought_response.content
        
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act
        if "TOOL:" in thought:
            tool_call = parse_tool_call(thought)
            obs = await agent._execute_tool_with_observation(
                tool_name=tool_call["tool"],
                parameters=tool_call.get("parameters", {})
            )
            history.add(obs)
            
            # Add observation to messages
            messages.append(LLMMessage(role="assistant", content=thought))
            messages.append(LLMMessage(role="user", content=f"Observation:\n{obs.to_text()}"))
    
    return "Max iterations reached"
```

## Advanced Reasoning Loops

### Pattern 1: Parallel Tool Execution

Execute multiple tools in parallel with observations.

```python
async def react_loop_parallel(task: str, max_iterations: int = 5):
    """ReAct loop with parallel tool execution"""
    observations = []
    messages = [LLMMessage(role="user", content=task)]
    
    for iteration in range(max_iterations):
        # Think
        thought_response = await agent.llm_client.generate_text(messages=messages)
        thought = thought_response.content
        
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act: Execute multiple tools in parallel
        if "TOOLS:" in thought:
            tool_calls = parse_multiple_tool_calls(thought)
            
            # Execute tools in parallel
            obs_tasks = [
                agent._execute_tool_with_observation(
                    tool_name=tc["tool"],
                    parameters=tc.get("parameters", {})
                )
                for tc in tool_calls
            ]
            
            parallel_obs = await asyncio.gather(*obs_tasks)
            observations.extend(parallel_obs)
            
            # Format observations
            observation_text = "\n\n".join([obs.to_text() for obs in parallel_obs])
            messages.append(LLMMessage(role="assistant", content=thought))
            messages.append(LLMMessage(role="user", content=f"Observations:\n{observation_text}"))
    
    return "Max iterations reached"
```

### Pattern 2: Conditional Tool Execution

Execute tools conditionally based on observations.

```python
async def react_loop_conditional(task: str, max_iterations: int = 5):
    """ReAct loop with conditional tool execution"""
    observations = []
    messages = [LLMMessage(role="user", content=task)]
    
    for iteration in range(max_iterations):
        # Think
        thought_response = await agent.llm_client.generate_text(messages=messages)
        thought = thought_response.content
        
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act: Conditional execution
        if "TOOL:" in thought:
            tool_call = parse_tool_call(thought)
            
            # Check if we should execute based on previous observations
            if should_execute_tool(tool_call, observations):
                obs = await agent._execute_tool_with_observation(
                    tool_name=tool_call["tool"],
                    parameters=tool_call.get("parameters", {})
                )
                observations.append(obs)
                
                messages.append(LLMMessage(role="assistant", content=thought))
                messages.append(LLMMessage(role="user", content=f"Observation:\n{obs.to_text()}"))
            else:
                # Skip tool execution
                messages.append(LLMMessage(
                    role="assistant",
                    content=thought + "\n(Skipped tool execution based on previous observations)"
                ))
    
    return "Max iterations reached"

def should_execute_tool(tool_call, observations):
    """Determine if tool should be executed"""
    # Example: Skip if same tool failed recently
    recent_failures = [
        obs for obs in observations[-3:]
        if not obs.success and obs.tool_name == tool_call["tool"]
    ]
    return len(recent_failures) < 2
```

## Multi-Tool Reasoning

### Pattern 1: Sequential Tool Chain

Execute tools sequentially with observations.

```python
async def sequential_tool_chain(tool_calls: list):
    """Execute tools sequentially with observations"""
    observations = []
    
    for tool_call in tool_calls:
        obs = await agent._execute_tool_with_observation(
            tool_name=tool_call["tool"],
            parameters=tool_call.get("parameters", {})
        )
        observations.append(obs)
        
        # Stop if tool failed
        if not obs.success:
            break
    
    return observations

# Use sequential chain
tool_calls = [
    {"tool": "search", "parameters": {"q": "Python"}},
    {"tool": "analyze", "parameters": {"data": "..."}}
]

observations = await sequential_tool_chain(tool_calls)
```

### Pattern 2: Dependent Tool Chain

Execute tools with dependencies.

```python
async def dependent_tool_chain(tool_calls: list):
    """Execute tools with dependencies"""
    observations = []
    
    for tool_call in tool_calls:
        # Use previous observation results
        if observations:
            last_result = observations[-1].result
            tool_call["parameters"]["previous_result"] = last_result
        
        obs = await agent._execute_tool_with_observation(
            tool_name=tool_call["tool"],
            parameters=tool_call.get("parameters", {})
        )
        observations.append(obs)
        
        if not obs.success:
            break
    
    return observations
```

## Error Recovery in Loops

### Pattern 1: Retry on Failure

Retry failed tools in reasoning loop.

```python
async def react_loop_with_retry(task: str, max_iterations: int = 5, max_retries: int = 3):
    """ReAct loop with retry on failure"""
    observations = []
    messages = [LLMMessage(role="user", content=task)]
    
    for iteration in range(max_iterations):
        # Think
        thought_response = await agent.llm_client.generate_text(messages=messages)
        thought = thought_response.content
        
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act: Retry on failure
        if "TOOL:" in thought:
            tool_call = parse_tool_call(thought)
            
            # Retry logic
            obs = None
            for retry in range(max_retries):
                obs = await agent._execute_tool_with_observation(
                    tool_name=tool_call["tool"],
                    parameters=tool_call.get("parameters", {})
                )
                
                if obs.success:
                    break
                
                # Wait before retry
                await asyncio.sleep(2 ** retry)
            
            observations.append(obs)
            
            # Add observation to context
            messages.append(LLMMessage(role="assistant", content=thought))
            messages.append(LLMMessage(role="user", content=f"Observation:\n{obs.to_text()}"))
    
    return "Max iterations reached"
```

### Pattern 2: Fallback Tools

Use fallback tools on failure.

```python
async def react_loop_with_fallback(task: str, max_iterations: int = 5):
    """ReAct loop with fallback tools"""
    observations = []
    messages = [LLMMessage(role="user", content=task)]
    
    tool_fallbacks = {
        "search": "fallback_search",
        "calculator": "basic_calculator"
    }
    
    for iteration in range(max_iterations):
        # Think
        thought_response = await agent.llm_client.generate_text(messages=messages)
        thought = thought_response.content
        
        if "FINAL_ANSWER:" in thought:
            return thought.split("FINAL_ANSWER:")[-1].strip()
        
        # Act: Use fallback on failure
        if "TOOL:" in thought:
            tool_call = parse_tool_call(thought)
            tool_name = tool_call["tool"]
            
            # Try primary tool
            obs = await agent._execute_tool_with_observation(
                tool_name=tool_name,
                parameters=tool_call.get("parameters", {})
            )
            
            # Use fallback if failed
            if not obs.success and tool_name in tool_fallbacks:
                fallback_tool = tool_fallbacks[tool_name]
                obs = await agent._execute_tool_with_observation(
                    tool_name=fallback_tool,
                    parameters=tool_call.get("parameters", {})
                )
            
            observations.append(obs)
            messages.append(LLMMessage(role="assistant", content=thought))
            messages.append(LLMMessage(role="user", content=f"Observation:\n{obs.to_text()}"))
    
    return "Max iterations reached"
```

## Observation Analysis

### Pattern 1: Performance Analysis

Analyze observation performance.

```python
def analyze_observations(observations: list):
    """Analyze observation performance"""
    successful = [obs for obs in observations if obs.success]
    failed = [obs for obs in observations if not obs.success]
    
    total_time = sum(
        obs.execution_time_ms for obs in observations
        if obs.execution_time_ms
    )
    
    avg_time = total_time / len(observations) if observations else 0
    
    return {
        "total": len(observations),
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / len(observations) if observations else 0,
        "avg_execution_time_ms": avg_time,
        "total_execution_time_ms": total_time
    }

# Analyze observations
analysis = analyze_observations(observations)
print(f"Success rate: {analysis['success_rate']:.1%}")
print(f"Average execution time: {analysis['avg_execution_time_ms']:.2f}ms")
```

### Pattern 2: Error Analysis

Analyze errors in observations.

```python
def analyze_errors(observations: list):
    """Analyze errors in observations"""
    failed = [obs for obs in observations if not obs.success]
    
    error_types = {}
    for obs in failed:
        error_type = obs.error.split(":")[0] if obs.error else "Unknown"
        error_types[error_type] = error_types.get(error_type, 0) + 1
    
    return {
        "total_errors": len(failed),
        "error_types": error_types,
        "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
    }

# Analyze errors
error_analysis = analyze_errors(observations)
print(f"Total errors: {error_analysis['total_errors']}")
print(f"Most common error: {error_analysis['most_common_error']}")
```

## Best Practices

### 1. Always Use Observations

Always use observations in reasoning loops:

```python
# Good: Use observations
obs = await agent._execute_tool_with_observation("search", None, {"q": "Python"})
reasoning_context = obs.to_text()

# Bad: Use raw results
result = await agent.execute_tool("search", {"q": "Python"})
reasoning_context = str(result)  # Missing error info
```

### 2. Check Success Before Using

Check success before using observation results:

```python
obs = await agent._execute_tool_with_observation("search", None, {"q": "Python"})

if obs.success:
    # Use result
    process_result(obs.result)
else:
    # Handle error
    handle_error(obs.error)
```

### 3. Format for LLM Context

Format observations properly for LLM:

```python
# Format observations
observation_text = "\n\n".join([obs.to_text() for obs in observations])

# Include in prompt
prompt = f"""
Task: {task}
Tool execution history:
{observation_text}
"""
```

### 4. Track Performance

Track performance metrics:

```python
# Track execution time
if obs.execution_time_ms and obs.execution_time_ms > 1000:
    logger.warning(f"Slow tool execution: {obs.execution_time_ms}ms")
```

### 5. Analyze Patterns

Analyze observation patterns:

```python
# Analyze patterns
slow_tools = [
    obs for obs in observations
    if obs.execution_time_ms and obs.execution_time_ms > 1000
]

frequently_failed = [
    tool for tool in set(obs.tool_name for obs in observations)
    if sum(1 for obs in observations if obs.tool_name == tool and not obs.success) > 3
]
```

## Summary

Observation-based reasoning loops provide:
- ✅ Structured reasoning with ToolObservation
- ✅ Error tracking and recovery
- ✅ Performance analysis
- ✅ LLM context building
- ✅ Debugging capabilities

**Key Patterns**:
- Use observations in ReAct loops
- Check success before using results
- Format properly for LLM context
- Track performance metrics
- Analyze observation patterns

For more details, see:
- [ToolObservation Pattern](./TOOL_OBSERVATION.md)
- [Agent Integration Guide](./AGENT_INTEGRATION.md)


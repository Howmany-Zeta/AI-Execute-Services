# ToolObservation Pattern Usage

This guide covers how to use the ToolObservation pattern for structured tracking of tool execution results, enabling observation-based reasoning loops and MasterController compatibility.

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Observation Formatting](#observation-formatting)
4. [Observation-Based Reasoning](#observation-based-reasoning)
5. [Error Handling](#error-handling)
6. [Serialization](#serialization)
7. [Best Practices](#best-practices)

## Overview

ToolObservation provides:

- **Structured Tracking**: Standardized format for tool execution results
- **Success/Error Status**: Automatic success/error tracking
- **Execution Metrics**: Execution time and timestamps
- **LLM Integration**: Text formatting for LLM context
- **Serialization**: Dictionary format for storage
- **MasterController Compatibility**: Essential for MasterController integration

### When to Use ToolObservation

- ✅ Observation-based reasoning loops
- ✅ MasterController compatibility
- ✅ Debugging and analysis
- ✅ LLM context building
- ✅ Tool execution logging

## Basic Usage

### Pattern 1: Execute Tool with Observation

Execute tool and get structured observation.

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

# Execute tool with observation
obs = await agent._execute_tool_with_observation(
    tool_name="search",
    operation="query",
    parameters={"q": "Python"}
)

# Check success
if obs.success:
    print(f"Found results: {obs.result}")
else:
    print(f"Error: {obs.error}")
```

### Pattern 2: Create Observation Manually

Create observation manually for custom tracking.

```python
from aiecs.domain.agent.models import ToolObservation
from datetime import datetime

# Successful observation
obs = ToolObservation(
    tool_name="search",
    parameters={"query": "AI", "limit": 10},
    result=["result1", "result2", "result3"],
    success=True,
    execution_time_ms=250.5
)

# Failed observation
obs = ToolObservation(
    tool_name="calculator",
    parameters={"operation": "divide", "a": 10, "b": 0},
    result=None,
    success=False,
    error="Division by zero",
    execution_time_ms=5.2
)
```

### Pattern 3: Multiple Observations

Collect multiple observations.

```python
observations = []

# Execute multiple tools
tool_calls = [
    {"tool": "search", "parameters": {"q": "Python"}},
    {"tool": "calculator", "parameters": {"operation": "add", "a": 1, "b": 2}}
]

for tool_call in tool_calls:
    obs = await agent._execute_tool_with_observation(
        tool_name=tool_call["tool"],
        parameters=tool_call["parameters"]
    )
    observations.append(obs)

# Process observations
for obs in observations:
    if obs.success:
        print(f"{obs.tool_name}: {obs.result}")
    else:
        print(f"{obs.tool_name} failed: {obs.error}")
```

## Observation Formatting

### Pattern 1: Text Formatting

Format observation as text for LLM context.

```python
obs = await agent._execute_tool_with_observation(
    tool_name="search",
    parameters={"q": "Python"},
    operation="query"
)

# Convert to text
text = obs.to_text()
# "Tool: search
# Parameters: {'q': 'Python'}
# Status: SUCCESS
# Result: ['result1', 'result2']
# Execution time: 250.5ms
# Timestamp: 2024-01-01T12:00:00"

# Include in LLM prompt
prompt = f"Tool execution results:\n{text}"
```

### Pattern 2: Multiple Observations Text

Format multiple observations for LLM context.

```python
observations = [
    await agent._execute_tool_with_observation("search", None, {"q": "Python"}),
    await agent._execute_tool_with_observation("calculator", "add", {"a": 1, "b": 2})
]

# Format all observations
observation_text = "\n\n".join([obs.to_text() for obs in observations])

# Include in LLM prompt
prompt = f"Tool execution history:\n{observation_text}"
```

### Pattern 3: Filtered Observations

Format only successful observations.

```python
observations = [
    await agent._execute_tool_with_observation("search", None, {"q": "Python"}),
    await agent._execute_tool_with_observation("calculator", "divide", {"a": 10, "b": 0})
]

# Format only successful observations
successful_obs = [obs for obs in observations if obs.success]
observation_text = "\n\n".join([obs.to_text() for obs in successful_obs])
```

## Observation-Based Reasoning

### Pattern 1: ReAct Loop with Observations

Use observations in ReAct reasoning loop.

```python
# ReAct loop with observations
task = "Search for Python and analyze results"
observations = []

for iteration in range(max_iterations):
    # Think: LLM reasoning
    thought = await llm.generate(f"Task: {task}\nObservations: {observation_text}")
    
    # Act: Execute tool
    if "TOOL:" in thought:
        tool_call = parse_tool_call(thought)
        obs = await agent._execute_tool_with_observation(
            tool_name=tool_call["tool"],
            parameters=tool_call["parameters"]
        )
        observations.append(obs)
        
        # Observe: Add observation to context
        observation_text = "\n\n".join([obs.to_text() for obs in observations])
    
    # Check if done
    if "FINAL_ANSWER:" in thought:
        break
```

### Pattern 2: Observation History

Maintain observation history for context.

```python
class ObservationHistory:
    def __init__(self):
        self.observations = []
    
    async def execute_and_record(self, agent, tool_name, parameters):
        """Execute tool and record observation"""
        obs = await agent._execute_tool_with_observation(
            tool_name=tool_name,
            parameters=parameters
        )
        self.observations.append(obs)
        return obs
    
    def get_history_text(self):
        """Get formatted history for LLM"""
        return "\n\n".join([obs.to_text() for obs in self.observations])

# Use observation history
history = ObservationHistory()

obs1 = await history.execute_and_record(agent, "search", {"q": "Python"})
obs2 = await history.execute_and_record(agent, "analyze", {"data": obs1.result})

# Get history for LLM
history_text = history.get_history_text()
```

## Error Handling

### Pattern 1: Handle Failed Observations

Handle failed observations gracefully.

```python
obs = await agent._execute_tool_with_observation(
    tool_name="search",
    parameters={"q": "Python"}
)

if not obs.success:
    # Handle error
    logger.error(f"Tool {obs.tool_name} failed: {obs.error}")
    
    # Retry with different parameters
    obs = await agent._execute_tool_with_observation(
        tool_name="search",
        parameters={"q": "Python programming"}
    )
```

### Pattern 2: Error Observation Formatting

Format error observations for debugging.

```python
obs = await agent._execute_tool_with_observation(
    tool_name="calculator",
    parameters={"operation": "divide", "a": 10, "b": 0}
)

if not obs.success:
    error_text = obs.to_text()
    # "Tool: calculator
    # Parameters: {'operation': 'divide', 'a': 10, 'b': 0}
    # Status: FAILURE
    # Error: Division by zero
    # Execution time: 5.2ms
    # Timestamp: 2024-01-01T12:00:00"
    
    logger.error(f"Tool execution failed:\n{error_text}")
```

## Serialization

### Pattern 1: Dictionary Serialization

Convert observation to dictionary.

```python
obs = await agent._execute_tool_with_observation(
    tool_name="search",
    parameters={"q": "Python"}
)

# Convert to dictionary
data = obs.to_dict()
# {
#     'tool_name': 'search',
#     'parameters': {'q': 'Python'},
#     'result': ['result1', 'result2'],
#     'success': True,
#     'error': None,
#     'execution_time_ms': 250.5,
#     'timestamp': '2024-01-01T12:00:00'
# }

# Serialize to JSON
import json
json_data = json.dumps(data)
```

### Pattern 2: Store Observations

Store observations for later analysis.

```python
observations = []

# Execute tools and collect observations
for tool_call in tool_calls:
    obs = await agent._execute_tool_with_observation(
        tool_name=tool_call["tool"],
        parameters=tool_call["parameters"]
    )
    observations.append(obs)

# Store observations
observation_data = [obs.to_dict() for obs in observations]

# Save to database or file
import json
with open("observations.json", "w") as f:
    json.dump(observation_data, f)
```

### Pattern 3: Load Observations

Load observations from storage.

```python
# Load from storage
import json
with open("observations.json", "r") as f:
    observation_data = json.load(f)

# Reconstruct observations
from aiecs.domain.agent.models import ToolObservation

observations = [
    ToolObservation(**data) for data in observation_data
]

# Use observations
for obs in observations:
    print(obs.to_text())
```

## Best Practices

### 1. Always Use Observations for Reasoning

Use observations in reasoning loops:

```python
# Good: Use observations
obs = await agent._execute_tool_with_observation("search", None, {"q": "Python"})
reasoning_context = f"Tool result: {obs.to_text()}"

# Bad: Use raw results
result = await agent.execute_tool("search", {"q": "Python"})
reasoning_context = f"Tool result: {result}"  # Missing error info
```

### 2. Check Success Before Using Results

Always check success before using results:

```python
obs = await agent._execute_tool_with_observation("search", None, {"q": "Python"})

if obs.success:
    # Use result
    process_results(obs.result)
else:
    # Handle error
    handle_error(obs.error)
```

### 3. Format Observations for LLM

Format observations properly for LLM context:

```python
# Format observations for LLM
observations = [obs1, obs2, obs3]
observation_text = "\n\n".join([obs.to_text() for obs in observations])

# Include in prompt
prompt = f"""
Task: {task}
Tool execution history:
{observation_text}
"""
```

### 4. Track Execution Time

Use execution time for performance analysis:

```python
obs = await agent._execute_tool_with_observation("search", None, {"q": "Python"})

if obs.execution_time_ms:
    if obs.execution_time_ms > 1000:
        logger.warning(f"Slow tool execution: {obs.execution_time_ms}ms")
```

### 5. Store Observations for Analysis

Store observations for later analysis:

```python
# Store observations
observation_data = [obs.to_dict() for obs in observations]

# Analyze later
slow_observations = [
    obs for obs in observations
    if obs.execution_time_ms and obs.execution_time_ms > 1000
]

failed_observations = [
    obs for obs in observations
    if not obs.success
]
```

## Summary

ToolObservation pattern provides:
- ✅ Structured tool execution tracking
- ✅ Success/error status
- ✅ Execution metrics
- ✅ LLM integration
- ✅ Serialization support
- ✅ MasterController compatibility

**Key Takeaways**:
- Use observations for reasoning loops
- Check success before using results
- Format properly for LLM context
- Track execution time
- Store for analysis

For more details, see:
- [Observation-Based Reasoning Loops](./OBSERVATION_REASONING.md)
- [MasterController Migration](./MASTERCONTROLLER_MIGRATION.md)


# MasterController Migration Path

This guide covers how to migrate from MasterController to the new agent system, including integration patterns, compatibility considerations, and migration strategies.

## Table of Contents

1. [Overview](#overview)
2. [Integration Patterns](#integration-patterns)
3. [Direct Integration](#direct-integration)
4. [Gradual Migration](#gradual-migration)
5. [Compatibility Considerations](#compatibility-considerations)
6. [Migration Strategies](#migration-strategies)
7. [Best Practices](#best-practices)

## Overview

The new agent system provides:

- **Direct MasterController Integration**: Use MasterController's LLM manager directly
- **ContextEngine Compatibility**: Shared context engine for persistent memory
- **Tool Integration**: Stateful tools with MasterController dependencies
- **Backward Compatibility**: Gradual migration path
- **Enhanced Features**: Additional capabilities beyond MasterController

### Migration Benefits

- ✅ Enhanced agent capabilities (learning, collaboration, caching)
- ✅ Better tool management (stateful tools, parallel execution)
- ✅ Improved performance (caching, streaming, parallel execution)
- ✅ Better observability (metrics, health monitoring)
- ✅ Flexible LLM client integration

## Integration Patterns

### Pattern 1: Direct LLM Manager Integration

Use MasterController's LLM manager directly as agent's LLM client.

```python
from aiecs.domain.execution.master_controller import MasterController
from aiecs.domain.agent import HybridAgent, AgentConfiguration

# Initialize MasterController
master_controller = MasterController(...)
await master_controller.initialize()

# Create agent with MasterController's LLM manager
agent = HybridAgent(
    agent_id="master_controller_agent",
    name="Master Controller Agent",
    llm_client=master_controller.llm_manager,  # Direct integration!
    tools=["search", "calculator"],
    config=AgentConfiguration(
        goal="Assist with MasterController tasks"
    )
)

await agent.initialize()

# Use agent
result = await agent.execute_task(
    {"description": "Search for Python"},
    {}
)
```

### Pattern 2: Shared ContextEngine

Share MasterController's ContextEngine for persistent memory.

```python
from aiecs.domain.execution.master_controller import MasterController
from aiecs.domain.agent import HybridAgent, AgentConfiguration

# Initialize MasterController
master_controller = MasterController(...)
await master_controller.initialize()

# Create agent with shared ContextEngine
agent = HybridAgent(
    agent_id="master_controller_agent",
    name="Master Controller Agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=AgentConfiguration(),
    context_engine=master_controller.context_engine  # Shared context engine
)

await agent.initialize()

# Conversation history persists across restarts
result = await agent.execute_task(
    {"description": "Hello"},
    {"session_id": "user-123"}
)
```

### Pattern 3: Stateful Tools Integration

Create stateful tools with MasterController dependencies.

```python
from aiecs.domain.execution.master_controller import MasterController
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.tools import BaseTool, ReadContextTool

# Initialize MasterController
master_controller = MasterController(...)
await master_controller.initialize()

# Create tools with MasterController dependencies
read_context_tool = ReadContextTool(
    context_engine=master_controller.context_engine
)

# Create agent with stateful tools
agent = HybridAgent(
    agent_id="master_controller_agent",
    name="Master Controller Agent",
    llm_client=master_controller.llm_manager,
    tools={
        "read_context": read_context_tool  # Stateful tool
    },
    config=AgentConfiguration(),
    context_engine=master_controller.context_engine
)

await agent.initialize()
```

## Direct Integration

### Pattern 1: Full Integration

Full integration with all MasterController components.

```python
from aiecs.domain.execution.master_controller import MasterController
from aiecs.domain.agent import HybridAgent, AgentConfiguration
from aiecs.tools import ReadContextTool, WriteContextTool

async def create_integrated_agent():
    """Create fully integrated agent"""
    
    # Initialize MasterController
    master_controller = MasterController(...)
    await master_controller.initialize()
    
    # Create tools with MasterController dependencies
    tools = {
        "read_context": ReadContextTool(
            context_engine=master_controller.context_engine
        ),
        "write_context": WriteContextTool(
            context_engine=master_controller.context_engine
        )
    }
    
    # Create agent
    agent = HybridAgent(
        agent_id="integrated_agent",
        name="Integrated Agent",
        llm_client=master_controller.llm_manager,
        tools=tools,
        config=AgentConfiguration(
            goal="Assist with MasterController tasks"
        ),
        context_engine=master_controller.context_engine
    )
    
    await agent.initialize()
    return agent

# Use agent
agent = await create_integrated_agent()
result = await agent.execute_task(
    {"description": "Read context and answer question"},
    {"session_id": "user-123"}
)
```

### Pattern 2: Wrapper Pattern

Wrap MasterController functionality in agent.

```python
class MasterControllerAgentWrapper:
    """Wrapper that integrates MasterController with agent"""
    
    def __init__(self, master_controller):
        self.master_controller = master_controller
        self.agent = None
    
    async def initialize(self):
        """Initialize agent with MasterController"""
        await self.master_controller.initialize()
        
        self.agent = HybridAgent(
            agent_id="master_controller_wrapper",
            name="Master Controller Wrapper",
            llm_client=self.master_controller.llm_manager,
            tools=self._create_tools(),
            config=AgentConfiguration(),
            context_engine=self.master_controller.context_engine
        )
        
        await self.agent.initialize()
    
    def _create_tools(self):
        """Create tools from MasterController"""
        return {
            "read_context": ReadContextTool(
                context_engine=self.master_controller.context_engine
            )
        }
    
    async def execute(self, task, context):
        """Execute task through agent"""
        return await self.agent.execute_task(task, context)

# Use wrapper
wrapper = MasterControllerAgentWrapper(master_controller)
await wrapper.initialize()
result = await wrapper.execute(task, context)
```

## Gradual Migration

### Pattern 1: Side-by-Side

Run MasterController and agent system side-by-side.

```python
# Keep MasterController running
master_controller = MasterController(...)
await master_controller.initialize()

# Create new agent system
agent = HybridAgent(
    agent_id="new_agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config,
    context_engine=master_controller.context_engine
)

# Gradually migrate tasks from MasterController to agent
# Old code
# result = await master_controller.execute(task)

# New code
result = await agent.execute_task(task, context)
```

### Pattern 2: Feature-by-Feature

Migrate features one at a time.

```python
# Phase 1: Migrate LLM calls
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=[],
    config=config
)

# Phase 2: Add tools
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search", "calculator"],
    config=config
)

# Phase 3: Add ContextEngine
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config,
    context_engine=master_controller.context_engine
)
```

### Pattern 3: Hybrid Approach

Use both systems for different tasks.

```python
# Use MasterController for existing tasks
master_result = await master_controller.execute(existing_task)

# Use agent system for new features
agent_result = await agent.execute_task(
    {"description": "New feature task"},
    {}
)

# Gradually migrate more tasks to agent system
```

## Compatibility Considerations

### Pattern 1: API Compatibility

Maintain API compatibility during migration.

```python
class CompatibleAgent:
    """Agent with MasterController-compatible API"""
    
    def __init__(self, master_controller):
        self.master_controller = master_controller
        self.agent = None
    
    async def initialize(self):
        await self.master_controller.initialize()
        self.agent = HybridAgent(
            agent_id="compatible_agent",
            llm_client=self.master_controller.llm_manager,
            tools=[],
            config=AgentConfiguration(),
            context_engine=self.master_controller.context_engine
        )
        await self.agent.initialize()
    
    async def execute(self, task, context=None):
        """MasterController-compatible execute method"""
        if context is None:
            context = {}
        return await self.agent.execute_task(task, context)

# Use compatible API
agent = CompatibleAgent(master_controller)
await agent.initialize()
result = await agent.execute(task, context)  # Same API as MasterController
```

### Pattern 2: Tool Compatibility

Ensure tool compatibility.

```python
# MasterController tools work with agent system
master_controller = MasterController(...)
await master_controller.initialize()

# Use MasterController tools directly
tools = {
    "read_context": ReadContextTool(
        context_engine=master_controller.context_engine
    )
}

agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=tools,
    config=config,
    context_engine=master_controller.context_engine
)
```

## Migration Strategies

### Strategy 1: Big Bang Migration

Migrate everything at once.

```python
# Stop MasterController
# Replace with agent system
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=all_tools,
    config=config,
    context_engine=master_controller.context_engine
)

# All functionality now through agent system
```

### Strategy 2: Gradual Migration

Migrate gradually over time.

```python
# Week 1: Migrate LLM calls
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=[],
    config=config
)

# Week 2: Add tools
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config
)

# Week 3: Add ContextEngine
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config,
    context_engine=master_controller.context_engine
)
```

### Strategy 3: Feature-Based Migration

Migrate by feature.

```python
# Migrate search feature
search_agent = HybridAgent(
    agent_id="search_agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config
)

# Migrate analysis feature
analysis_agent = HybridAgent(
    agent_id="analysis_agent",
    llm_client=master_controller.llm_manager,
    tools=["analysis"],
    config=config
)
```

## Best Practices

### 1. Start with Direct Integration

Start with direct integration for simplicity:

```python
# Simple direct integration
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config,
    context_engine=master_controller.context_engine
)
```

### 2. Share ContextEngine

Share ContextEngine for consistent memory:

```python
# Share ContextEngine
agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=["search"],
    config=config,
    context_engine=master_controller.context_engine  # Shared
)
```

### 3. Use Stateful Tools

Use stateful tools with MasterController dependencies:

```python
# Stateful tools
tools = {
    "read_context": ReadContextTool(
        context_engine=master_controller.context_engine
    )
}

agent = HybridAgent(
    agent_id="agent",
    llm_client=master_controller.llm_manager,
    tools=tools,
    config=config
)
```

### 4. Test Compatibility

Test compatibility before full migration:

```python
# Test compatibility
test_task = {"description": "Test task"}
master_result = await master_controller.execute(test_task)
agent_result = await agent.execute_task(test_task, {})

# Compare results
assert master_result == agent_result
```

### 5. Monitor Performance

Monitor performance during migration:

```python
# Monitor performance
metrics = agent.get_performance_metrics()
print(f"Average response time: {metrics['avg_response_time']}s")

health = agent.get_health_status()
print(f"Health status: {health['status']}")
```

## Summary

MasterController migration provides:
- ✅ Direct LLM manager integration
- ✅ Shared ContextEngine
- ✅ Stateful tool support
- ✅ Gradual migration path
- ✅ Enhanced features

**Key Migration Patterns**:
- Direct integration for simplicity
- Share ContextEngine for consistency
- Use stateful tools
- Test compatibility
- Monitor performance

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md)
- [ToolObservation Pattern](./TOOL_OBSERVATION.md)


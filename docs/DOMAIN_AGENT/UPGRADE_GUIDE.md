# Upgrade Guide: Enhanced Hybrid Agent Flexibility

## Quick Start

**✅ No upgrade required!** All changes are backward compatible. This guide helps you adopt new features with practical examples.

---

## Step-by-Step Upgrade Examples

### Example 1: Upgrading to Tool Instances

**Scenario**: You have a `ReadContextTool` that needs a `ContextEngine` instance.

#### Step 1: Identify the Need

```python
# Current code - doesn't work for stateful tools
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["read_context"],  # Can't pass context_engine!
    llm_client=llm_client,
    config=config
)
```

#### Step 2: Create Tool Instance

```python
from aiecs.domain.context import ContextEngine
from aiecs.tools import ReadContextTool

# Initialize ContextEngine
context_engine = ContextEngine()
await context_engine.initialize()

# Create tool instance with dependency
read_context_tool = ReadContextTool(context_engine=context_engine)
```

#### Step 3: Update Agent Creation

```python
# Updated code - works with stateful tools
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools={
        "read_context": read_context_tool  # Tool instance with state
    },
    llm_client=llm_client,
    config=config
)
```

#### Step 4: Verify

```python
# Test that tool state is preserved
result1 = await agent.execute_tool("read_context", operation="read", parameters={"key": "test"})
result2 = await agent.execute_tool("read_context", operation="read", parameters={"key": "test"})
# Tool's internal state (e.g., cache) is preserved between calls
```

---

### Example 2: Upgrading to Custom LLM Client

**Scenario**: You have a `LLMIntegrationManager` wrapper that doesn't inherit from `BaseLLMClient`.

#### Step 1: Review Your Custom LLM Client

```python
# Your existing custom LLM wrapper
class LLMIntegrationManager:
    def __init__(self):
        self.provider = "custom"
        # ... initialization ...
    
    async def generate(self, messages, **kwargs):
        # Custom generation logic
        return response
    
    async def stream(self, messages, **kwargs):
        # Custom streaming logic
        async for token in self._internal_stream():
            yield token
```

#### Step 2: Ensure Protocol Compliance

```python
from aiecs.llm import LLMResponse

class LLMIntegrationManager:
    provider_name = "custom"  # Required attribute
    
    async def generate_text(self, messages, **kwargs):
        # Rename from 'generate' to 'generate_text'
        response = await self._internal_generate(messages, **kwargs)
        return LLMResponse(
            content=response.content,
            provider=self.provider_name,
            model=response.model
        )
    
    async def stream_text(self, messages, **kwargs):
        # Rename from 'stream' to 'stream_text'
        async for token in self._internal_stream(messages, **kwargs):
            yield token
    
    async def close(self):
        # Add cleanup if needed
        await self._cleanup()
```

#### Step 3: Use Directly

```python
# No adapter needed!
llm_manager = LLMIntegrationManager()

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_manager,  # Works directly!
    tools=["search"],
    config=config
)
```

#### Step 4: Test

```python
# Verify it works
result = await agent.execute_task({"description": "Test task"}, {})
assert result is not None
```

---

### Example 3: Upgrading to Persistent Memory

**Scenario**: You need conversation history to persist across agent restarts.

#### Step 1: Set Up ContextEngine

```python
from aiecs.domain.context import ContextEngine

# Initialize ContextEngine (do this once at startup)
context_engine = ContextEngine()
await context_engine.initialize()
```

#### Step 2: Update Agent Creation

```python
# Add context_engine parameter
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search"],
    llm_client=llm_client,
    config=config,
    context_engine=context_engine  # Enable persistence
)
```

#### Step 3: Use Conversation Methods

```python
# Create a session
session_id = await agent.create_session(user_id="user123")

# Add conversation messages
await agent.add_conversation_message("user", "Hello", session_id)
await agent.add_conversation_message("assistant", "Hi there!", session_id)

# Get conversation history
history = await agent.get_conversation_history(session_id)
print(f"History: {len(history)} messages")

# History persists even after agent restart!
```

#### Step 4: Verify Persistence

```python
# Restart agent (simulate)
await agent.shutdown()

# Create new agent instance
new_agent = HybridAgent(
    agent_id="agent1",  # Same agent_id
    name="My Agent",
    tools=["search"],
    llm_client=llm_client,
    config=config,
    context_engine=context_engine  # Same ContextEngine
)
await new_agent.initialize()

# History is still there!
history = await new_agent.get_conversation_history(session_id)
assert len(history) == 2  # Still has 2 messages
```

---

### Example 4: Upgrading to Performance Features

**Scenario**: You want to reduce API costs and improve speed.

#### Step 1: Enable Tool Caching

```python
from aiecs.domain.agent.base_agent import CacheConfig

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search", "calculator"],
    llm_client=llm_client,
    config=config,
    cache_config=CacheConfig(
        enabled=True,
        default_ttl=300,  # 5 minutes
        tool_specific_ttl={
            "search": 600,  # 10 minutes for search
            "calculator": 60  # 1 minute for calculator
        }
    )
)
```

#### Step 2: Use Cached Execution

```python
# First call - hits API
result1 = await agent.execute_tool_with_cache(
    tool_name="search",
    operation="query",
    parameters={"q": "AI"},
    cache_ttl=300
)

# Second call - uses cache (no API call!)
result2 = await agent.execute_tool_with_cache(
    tool_name="search",
    operation="query",
    parameters={"q": "AI"},  # Same parameters
    cache_ttl=300
)

# Check cache stats
stats = agent.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.1%}")
```

#### Step 3: Enable Parallel Execution

```python
# Execute multiple independent tools in parallel
results = await agent.execute_tools_parallel([
    {"tool": "search", "operation": "query", "parameters": {"q": "AI"}},
    {"tool": "calculator", "operation": "add", "parameters": {"a": 1, "b": 2}},
    {"tool": "translator", "operation": "translate", "parameters": {"text": "Hello"}}
], max_concurrency=3)

# Results are 3-5x faster than sequential execution!
```

#### Step 4: Monitor Performance

```python
# Track operation performance
with agent.track_operation_time("data_processing"):
    result = await agent.execute_task(task, context)

# Get metrics
metrics = agent.get_performance_metrics()
print(f"Average: {metrics['avg_response_time']}s")
print(f"P95: {metrics['p95_response_time']}s")
```

---

### Example 5: Upgrading to Production Features

**Scenario**: You need production-ready features (resource limits, error recovery, health monitoring).

#### Step 1: Configure Resource Limits

```python
from aiecs.domain.agent.models import ResourceLimits

resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    max_tokens_per_minute=10000,
    max_tool_calls_per_minute=100,
    max_memory_mb=512
)

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search"],
    llm_client=llm_client,
    config=config,
    resource_limits=resource_limits
)
```

#### Step 2: Use Resource Management

```python
# Check resource availability before executing
if await agent.check_resource_availability():
    result = await agent.execute_task(task, context)
else:
    # Wait for resources to become available
    await agent.wait_for_resources(timeout=30.0)
    result = await agent.execute_task(task, context)
```

#### Step 3: Enable Learning

```python
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search"],
    llm_client=llm_client,
    config=config,
    learning_enabled=True  # Enable learning
)

# Record experiences
await agent.record_experience(
    task_type="data_analysis",
    approach="parallel_tools",
    success=True,
    execution_time=2.5
)

# Get recommendations
approach = await agent.get_recommended_approach("data_analysis")
print(f"Recommended: {approach}")
```

#### Step 4: Monitor Health

```python
# Get health status
health = agent.get_health_status()
print(f"Status: {health['status']}")  # healthy, degraded, unhealthy
print(f"Score: {health['score']}")  # 0-100

# Get comprehensive status
status = agent.get_comprehensive_status()
print(f"Capabilities: {status['capabilities']}")
print(f"Metrics: {status['metrics']}")
```

---

## Complete Upgrade Example

Here's a complete example upgrading from basic agent to full-featured agent:

### Before (Basic Agent)

```python
from aiecs.domain.agent import HybridAgent
from aiecs.llm import OpenAIClient

# Basic agent
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search", "calculator"],
    llm_client=OpenAIClient(),
    config=config
)
await agent.initialize()

# Execute task
result = await agent.execute_task({"description": "Search for AI"}, {})
```

### After (Full-Featured Agent)

```python
from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import ResourceLimits
from aiecs.domain.agent.base_agent import CacheConfig
from aiecs.domain.context import ContextEngine
from aiecs.tools import SearchTool, CalculatorTool

# Initialize ContextEngine
context_engine = ContextEngine()
await context_engine.initialize()

# Create tool instances
search_tool = SearchTool(api_key="...")
calculator_tool = CalculatorTool()

# Full-featured agent
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools={
        "search": search_tool,
        "calculator": calculator_tool
    },
    llm_client=OpenAIClient(),
    config=config,
    context_engine=context_engine,  # Persistent memory
    cache_config=CacheConfig(enabled=True, default_ttl=300),  # Caching
    resource_limits=ResourceLimits(max_concurrent_tasks=5),  # Resource limits
    learning_enabled=True,  # Learning
    collaboration_enabled=True  # Collaboration
)
await agent.initialize()

# Create session
session_id = await agent.create_session(user_id="user123")

# Execute task with all features
with agent.track_operation_time("search_task"):
    result = await agent.execute_task_with_recovery(
        {"description": "Search for AI"},
        {},
        session_id=session_id
    )

# Get metrics
health = agent.get_health_status()
metrics = agent.get_performance_metrics()
print(f"Health: {health['status']}, Avg time: {metrics['avg_response_time']}s")
```

---

## Upgrade Checklist

Use this checklist to track your upgrade:

- [ ] **Review current usage**
  - [ ] Identify agent types used
  - [ ] List tools and their dependencies
  - [ ] Document LLM client usage

- [ ] **Adopt tool instances** (if needed)
  - [ ] Create tool instances with dependencies
  - [ ] Update agent creation
  - [ ] Test tool state preservation

- [ ] **Adopt custom LLM clients** (if needed)
  - [ ] Ensure protocol compliance
  - [ ] Update agent creation
  - [ ] Test LLM integration

- [ ] **Adopt persistent memory** (if needed)
  - [ ] Set up ContextEngine
  - [ ] Update agent creation
  - [ ] Test persistence

- [ ] **Adopt performance features** (if needed)
  - [ ] Enable caching
  - [ ] Use parallel execution
  - [ ] Track performance metrics

- [ ] **Adopt production features** (if needed)
  - [ ] Configure resource limits
  - [ ] Enable learning
  - [ ] Set up health monitoring

- [ ] **Testing**
  - [ ] Test backward compatibility
  - [ ] Test new features
  - [ ] Monitor performance
  - [ ] Verify health status

---

## Common Upgrade Patterns

### Pattern 1: Minimal Upgrade (Just Tool Instances)

```python
# Only upgrade what you need
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools={"search": SearchTool()},  # Only change: tool instances
    llm_client=OpenAIClient(),  # Keep as-is
    config=config  # Keep as-is
)
```

### Pattern 2: Moderate Upgrade (Memory + Performance)

```python
# Add persistence and performance
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools=["search"],  # Keep tool names
    llm_client=OpenAIClient(),  # Keep as-is
    config=config,
    context_engine=context_engine,  # Add persistence
    cache_config=CacheConfig(enabled=True)  # Add caching
)
```

### Pattern 3: Full Upgrade (All Features)

```python
# Use all new features
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    tools={"search": SearchTool()},  # Tool instances
    llm_client=CustomLLMClient(),  # Custom client
    config=config,
    config_manager=ConfigManager(),  # Config manager
    checkpointer=Checkpointer(),  # Checkpointer
    context_engine=context_engine,  # Persistence
    cache_config=CacheConfig(enabled=True),  # Caching
    resource_limits=ResourceLimits(),  # Resource limits
    learning_enabled=True,  # Learning
    collaboration_enabled=True  # Collaboration
)
```

---

## Troubleshooting Upgrades

### Issue: Tool instances not preserving state

**Solution**: Ensure tools are created before agent initialization:

```python
# ✅ Correct: Create tools first
tool = MyTool(state="preserved")
agent = HybridAgent(tools={"tool": tool})

# ❌ Wrong: Create tools after agent
agent = HybridAgent(tools={})
tool = MyTool()  # Too late!
```

### Issue: Custom LLM client not working

**Solution**: Verify protocol compliance:

```python
# Check required methods
assert hasattr(llm_client, 'generate_text')
assert hasattr(llm_client, 'stream_text')
assert hasattr(llm_client, 'close')
assert hasattr(llm_client, 'provider_name')
```

### Issue: ContextEngine not persisting

**Solution**: Ensure ContextEngine is initialized and same instance used:

```python
# ✅ Correct: Initialize and reuse
context_engine = ContextEngine()
await context_engine.initialize()
agent1 = HybridAgent(context_engine=context_engine)
agent2 = HybridAgent(context_engine=context_engine)  # Same instance

# ❌ Wrong: Different instances
agent1 = HybridAgent(context_engine=ContextEngine())
agent2 = HybridAgent(context_engine=ContextEngine())  # Different!
```

---

## Next Steps

After upgrading:

1. **Monitor performance** - Check metrics and health status
2. **Review documentation** - See this directory for more examples
3. **Test thoroughly** - Verify all features work as expected
4. **Gradual adoption** - Add features incrementally based on needs

For more help:
- **Migration Guide**: `./MIGRATION_GUIDE.md`
- **Integration Guide**: `./AGENT_INTEGRATION.md`
- **Examples**: `./EXAMPLES.md`



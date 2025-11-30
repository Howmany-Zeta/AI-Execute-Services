# Migration Guide: Enhanced Hybrid Agent Flexibility

## Overview

This guide covers migrating to the enhanced agent flexibility features introduced in the `enhance-hybrid-agent-flexibility` change. **Good news: No migration is required!** All changes are backward compatible.

## Backward Compatibility

All existing code continues to work without any changes. The enhancements add **optional** parameters and features that you can adopt gradually.

### What Stays the Same

- ✅ Existing agent creation code works unchanged
- ✅ Tool names (`List[str]`) still work
- ✅ `BaseLLMClient` instances still work
- ✅ All existing methods and APIs unchanged
- ✅ No breaking changes to any interfaces

### What's New (Optional)

- 🆕 Tool instances (`Dict[str, BaseTool]`) for stateful tools
- 🆕 Custom LLM clients (any `LLMClientProtocol` implementation)
- 🆕 ContextEngine integration for persistent memory
- 🆕 Custom config managers for dynamic configuration
- 🆕 Custom checkpointers for LangGraph integration
- 🆕 Performance tracking and health monitoring
- 🆕 Tool caching and parallel execution
- 🆕 Agent collaboration features
- 🆕 Learning and adaptation capabilities
- 🆕 Resource management and rate limiting
- 🆕 Error recovery strategies

## Migration Scenarios

### Scenario 1: No Migration Needed

If your code works fine as-is, you don't need to do anything:

```python
# This still works exactly as before
from aiecs.domain.agent import HybridAgent
from aiecs.llm import OpenAIClient

agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=OpenAIClient(),
    tools=["search", "calculator"],  # Still works!
    config=config
)
```

### Scenario 2: Adopting Tool Instances

**When to migrate**: You have tools that need state or dependencies (e.g., `ReadContextTool` with `context_engine`, `SmartAnalysisTool` with `llm_manager`).

**Before** (doesn't work for stateful tools):
```python
# Tools loaded by name - no way to inject dependencies
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools=["read_context", "smart_analysis"],  # Can't pass context_engine!
    config=config
)
```

**After** (works with stateful tools):
```python
from aiecs.tools import BaseTool
from aiecs.domain.context import ContextEngine

# Create tool instances with dependencies
context_engine = ContextEngine()
await context_engine.initialize()

read_context_tool = ReadContextTool(context_engine=context_engine)
smart_analysis_tool = SmartAnalysisTool(llm_manager=llm_manager)

# Pass tool instances directly
agent = HybridAgent(
    agent_id="agent1",
    name="My Agent",
    llm_client=llm_client,
    tools={
        "read_context": read_context_tool,  # Stateful tool instance
        "smart_analysis": smart_analysis_tool
    },
    config=config
)
```

### Scenario 3: Adopting Custom LLM Clients

**When to migrate**: You have custom LLM wrappers (e.g., `LLMIntegrationManager` in MasterController) that don't inherit from `BaseLLMClient`.

**Before** (requires adapter):
```python
# Custom wrapper doesn't work directly
class LLMIntegrationManager:
    # Custom implementation
    pass

# Had to create adapter
class LLMAdapter(BaseLLMClient):
    def __init__(self, manager):
        self.manager = manager
    # ... adapter code ...

agent = HybridAgent(
    llm_client=LLMAdapter(LLMIntegrationManager())  # Required adapter
)
```

**After** (works directly):
```python
# Custom wrapper works directly - no adapter needed!
class LLMIntegrationManager:
    provider_name = "custom"
    
    async def generate_text(self, messages, **kwargs):
        # Your custom implementation
        return LLMResponse(...)
    
    async def stream_text(self, messages, **kwargs):
        # Your custom streaming
        async for token in self._custom_stream():
            yield token
    
    async def close(self):
        # Cleanup
        pass

# Use directly - no adapter needed!
agent = HybridAgent(
    llm_client=LLMIntegrationManager(),  # Works directly!
    tools=["search"],
    config=config
)
```

### Scenario 4: Adopting ContextEngine for Persistent Memory

**When to migrate**: You need conversation history to persist across agent restarts.

**Before** (in-memory only):
```python
# Conversation history lost on restart
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config
)
# History lost when agent restarts
```

**After** (persistent memory):
```python
from aiecs.domain.context import ContextEngine

# Initialize ContextEngine
context_engine = ContextEngine()
await context_engine.initialize()

# Agent with persistent memory
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    context_engine=context_engine  # Enables persistence
)
# Conversation history persists across restarts!
```

### Scenario 5: Adopting Custom Config Manager

**When to migrate**: You need dynamic configuration from external sources (database, config server, etc.).

**Before** (static config only):
```python
# Config is static
config = AgentConfiguration(
    goal="Help users",
    llm_model="gpt-4"
)
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    config=config,  # Static config
    tools=["search"]
)
```

**After** (dynamic config):
```python
from aiecs.domain.agent.integration import ConfigManagerProtocol

class DatabaseConfigManager:
    async def get_config(self, key: str, default: Any = None) -> Any:
        return await db.get_config(key, default)
    
    async def set_config(self, key: str, value: Any) -> None:
        await db.set_config(key, value)
    
    async def reload_config(self) -> None:
        await db.refresh_cache()

# Agent with dynamic config
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    config=config,
    tools=["search"],
    config_manager=DatabaseConfigManager()  # Dynamic config
)

# Config can be updated at runtime
await agent.get_config_manager().set_config("goal", "New goal")
```

### Scenario 6: Adopting Custom Checkpointer

**When to migrate**: You need LangGraph integration or custom state persistence.

**Before** (no checkpointing):
```python
# No checkpointing support
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config
)
# Can't save/load state
```

**After** (with checkpointing):
```python
from aiecs.domain.agent.integration import CheckpointerProtocol

class RedisCheckpointer:
    async def save_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
    ) -> str:
        checkpoint_id = str(uuid.uuid4())
        await redis.set(f"checkpoint:{checkpoint_id}", json.dumps(checkpoint_data))
        return checkpoint_id
    
    async def load_checkpoint(
        self, agent_id: str, session_id: str, checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        if checkpoint_id:
            data = await redis.get(f"checkpoint:{checkpoint_id}")
            return json.loads(data) if data else None
        return await self._load_latest(agent_id, session_id)
    
    async def list_checkpoints(self, agent_id: str, session_id: str) -> list[str]:
        return await redis.keys(f"checkpoint:{agent_id}:{session_id}:*")

# Agent with checkpointing
agent = HybridAgent(
    agent_id="agent1",
    llm_client=llm_client,
    tools=["search"],
    config=config,
    checkpointer=RedisCheckpointer()  # LangGraph-compatible
)

# Save/load state
checkpoint_id = await agent.save_checkpoint("session-123")
await agent.load_checkpoint("session-123", checkpoint_id)
```

## Gradual Adoption Strategy

You can adopt new features incrementally:

### Phase 1: Core Flexibility (Optional)
- Start using tool instances if you have stateful tools
- Start using custom LLM clients if you have wrappers

### Phase 2: Memory & Persistence (Optional)
- Add ContextEngine for persistent conversation history
- Add checkpointers for state persistence

### Phase 3: Advanced Features (Optional)
- Enable performance tracking
- Add tool caching for cost reduction
- Enable parallel tool execution for speed

### Phase 4: Production Features (Optional)
- Add resource limits for stability
- Enable learning for adaptation
- Add collaboration for multi-agent workflows

## Common Patterns

### Pattern 1: MasterController Integration

**Before**: Required adapter layers
```python
# Had to create adapter
class LLMAdapter(BaseLLMClient):
    def __init__(self, manager):
        self.manager = manager
    # ... adapter code ...

agent = HybridAgent(
    llm_client=LLMAdapter(master_controller.llm_manager)
)
```

**After**: Direct integration
```python
# Use LLMIntegrationManager directly
agent = HybridAgent(
    llm_client=master_controller.llm_manager,  # Works directly!
    tools={
        "read_context": ReadContextTool(context_engine=master_controller.context_engine),
        "smart_analysis": SmartAnalysisTool(llm_manager=master_controller.llm_manager)
    }
)
```

### Pattern 2: Service Tool Integration

**Before**: Tools couldn't access service instances
```python
# Tools loaded by name - no service access
agent = HybridAgent(
    tools=["service_tool"]  # Can't pass service instance
)
```

**After**: Tools can access service instances
```python
# Create tool with service instance
service_tool = ServiceTool(service=my_service_instance)

agent = HybridAgent(
    tools={
        "service_tool": service_tool  # Service instance accessible
    }
)
```

## Testing Your Migration

1. **Test backward compatibility**: Ensure existing code still works
2. **Test new features**: Verify new features work as expected
3. **Test gradually**: Adopt one feature at a time
4. **Monitor performance**: Check for any performance regressions

## Troubleshooting

### Issue: Tool instances not working

**Solution**: Ensure tools are `BaseTool` instances and have required methods:
```python
from aiecs.tools import BaseTool

class MyTool(BaseTool):
    async def run_async(self, **kwargs):
        return "result"
```

### Issue: Custom LLM client not working

**Solution**: Ensure it implements `LLMClientProtocol`:
```python
class MyLLMClient:
    provider_name = "custom"
    
    async def generate_text(self, messages, **kwargs):
        # Must implement this
        pass
    
    async def stream_text(self, messages, **kwargs):
        # Must implement this
        async for token in self._stream():
            yield token
    
    async def close(self):
        # Must implement this
        pass
```

### Issue: ContextEngine not persisting

**Solution**: Ensure ContextEngine is initialized:
```python
context_engine = ContextEngine()
await context_engine.initialize()  # Don't forget this!

agent = HybridAgent(
    context_engine=context_engine
)
```

## Summary

- ✅ **No migration required** - all changes are backward compatible
- ✅ **Adopt gradually** - use new features as needed
- ✅ **No breaking changes** - existing code continues to work
- ✅ **Enhanced flexibility** - new features available when needed

For more details, see:
- [Agent Integration Guide](./AGENT_INTEGRATION.md) - Comprehensive integration documentation
- [Example Implementations](./EXAMPLES.md) - Common pattern examples


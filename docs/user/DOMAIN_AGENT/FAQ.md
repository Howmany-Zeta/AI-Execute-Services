# FAQ: Enhanced Hybrid Agent Flexibility

## General Questions

### Q: Do I need to migrate my existing code?

**A: No!** All changes are 100% backward compatible. Your existing code will continue to work without any modifications. New features are optional and can be adopted gradually.

### Q: Will my existing agents break?

**A: No.** All existing agent code continues to work exactly as before. The enhancements add optional parameters and features that don't affect existing functionality.

### Q: What's the performance impact?

**A: Minimal.** For backward-compatible code paths, overhead is less than 25%. New features only add overhead when enabled. See `PERFORMANCE_BENCHMARK_SUMMARY.md` for details.

### Q: Are there any breaking changes?

**A: No.** We've verified that there are no breaking changes. See `BREAKING_CHANGES_ANALYSIS.md` for detailed analysis.

---

## Tool Instances

### Q: When should I use tool instances instead of tool names?

**A:** Use tool instances when:
- Tools need dependencies (e.g., ContextEngine, LLM clients)
- Tools need to preserve state across operations
- Tools need custom configuration
- You're integrating with custom services

**Example:**
```python
# Use tool instances for stateful tools
context_engine = ContextEngine()
await context_engine.initialize()

read_context_tool = ReadContextTool(context_engine=context_engine)
agent = HybridAgent(tools={"read_context": read_context_tool})
```

### Q: Can I mix tool names and tool instances?

**A: No.** You must use either `List[str]` (tool names) or `Dict[str, BaseTool]` (tool instances), not both. However, you can convert tool names to instances:

```python
# Convert tool names to instances
tools_dict = {name: get_tool(name) for name in tool_names}
agent = HybridAgent(tools=tools_dict)
```

### Q: Do tool instances preserve state?

**A: Yes!** Tool instances preserve their internal state across agent operations. This is useful for caching, counters, or maintaining connections.

**Example:**
```python
class StatefulTool(BaseTool):
    def __init__(self):
        self.call_count = 0  # State preserved
    
    async def run_async(self, **kwargs):
        self.call_count += 1
        return f"Called {self.call_count} times"

tool = StatefulTool()
agent = HybridAgent(tools={"tool": tool})

# First call
await agent.execute_tool("tool", operation="test")
# tool.call_count == 1

# Second call
await agent.execute_tool("tool", operation="test")
# tool.call_count == 2 (state preserved!)
```

---

## Custom LLM Clients

### Q: What's the difference between BaseLLMClient and LLMClientProtocol?

**A:** 
- **BaseLLMClient**: Abstract base class requiring inheritance
- **LLMClientProtocol**: Protocol (duck typing) - any object with required methods works

**Protocol is more flexible** - you don't need to inherit from BaseLLMClient.

### Q: How do I make my custom LLM client work with agents?

**A:** Ensure it implements `LLMClientProtocol`:

```python
class MyLLMClient:
    provider_name = "custom"  # Required attribute
    
    async def generate_text(self, messages, **kwargs):
        # Must return LLMResponse
        return LLMResponse(content="...", provider="custom", model="custom-model")
    
    async def stream_text(self, messages, **kwargs):
        # Must be async generator
        async for token in self._stream():
            yield token
    
    async def close(self):
        # Cleanup if needed
        pass

# Use directly
agent = HybridAgent(llm_client=MyLLMClient())
```

### Q: Can I use MasterController's LLMIntegrationManager?

**A: Yes!** As long as it implements the required methods (`generate_text`, `stream_text`, `close`) and has `provider_name` attribute:

```python
# Works directly - no adapter needed!
agent = HybridAgent(
    llm_client=master_controller.llm_manager,  # Works!
    tools=["search"],
    config=config
)
```

---

## ContextEngine Integration

### Q: Do I need ContextEngine for agents to work?

**A: No.** ContextEngine is optional. Agents work fine without it, using in-memory storage. ContextEngine is only needed for persistent conversation history.

### Q: How do I set up ContextEngine?

**A:**

```python
from aiecs.domain.context import ContextEngine

# Initialize once at startup
context_engine = ContextEngine()
await context_engine.initialize()

# Use with agents
agent = HybridAgent(
    agent_id="agent1",
    context_engine=context_engine
)
```

### Q: Does conversation history persist across agent restarts?

**A: Yes**, if you use ContextEngine:

```python
# First session
agent1 = HybridAgent(context_engine=context_engine)
await agent1.add_conversation_message("user", "Hello", session_id="session1")

# After restart
agent2 = HybridAgent(context_engine=context_engine)  # Same ContextEngine
history = await agent2.get_conversation_history("session1")
# History is still there!
```

### Q: Can multiple agents share the same ContextEngine?

**A: Yes!** Multiple agents can share the same ContextEngine instance. Sessions are isolated by `session_id`.

---

## Session Management

### Q: What's the difference between agent_id and session_id?

**A:**
- **agent_id**: Identifies the agent instance (e.g., "agent1")
- **session_id**: Identifies a conversation session (e.g., "session-user123")

Multiple sessions can belong to the same agent.

### Q: How do I create a session?

**A:**

```python
session_id = await agent.create_session(user_id="user123")
```

### Q: How do I track session metrics?

**A:**

```python
# Track requests
await agent.track_session_request(session_id)

# Get metrics
metrics = await agent.get_session_metrics(session_id)
print(f"Requests: {metrics['request_count']}")
print(f"Errors: {metrics['error_count']}")
```

### Q: How do I clean up old sessions?

**A:**

```python
# Cleanup inactive sessions older than 24 hours
await agent.cleanup_inactive_sessions(max_age_hours=24)
```

---

## Performance Features

### Q: How much faster is parallel tool execution?

**A:** Typically 3-5x faster for independent tools. Speedup depends on:
- Number of tools
- Tool execution time
- Network latency

**Example:**
```python
# Sequential: ~3 seconds
# Parallel: ~1 second (3x faster)
results = await agent.execute_tools_parallel([
    {"tool": "search", ...},
    {"tool": "calculator", ...},
    {"tool": "translator", ...}
])
```

### Q: How much can tool caching reduce costs?

**A:** Typically 30-50% reduction in API calls for repeated queries. Effectiveness depends on:
- Cache TTL settings
- Query repetition patterns
- Tool-specific caching needs

**Example:**
```python
# First call: API call
result1 = await agent.execute_tool_with_cache("search", ...)

# Second call (within TTL): Cache hit (no API call!)
result2 = await agent.execute_tool_with_cache("search", ...)
```

### Q: How do I configure caching?

**A:**

```python
from aiecs.domain.agent.base_agent import CacheConfig

agent = HybridAgent(
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

---

## Resource Management

### Q: What are resource limits?

**A:** Resource limits prevent agents from exceeding quotas:
- `max_concurrent_tasks`: Maximum parallel tasks
- `max_tokens_per_minute`: Token rate limit
- `max_tool_calls_per_minute`: Tool call rate limit
- `max_memory_mb`: Memory limit

### Q: How do I set resource limits?

**A:**

```python
from aiecs.domain.agent.models import ResourceLimits

resource_limits = ResourceLimits(
    max_concurrent_tasks=5,
    max_tokens_per_minute=10000,
    max_tool_calls_per_minute=100
)

agent = HybridAgent(resource_limits=resource_limits)
```

### Q: What happens when limits are exceeded?

**A:** The agent will wait for resources to become available (up to timeout) or raise an error:

```python
if await agent.check_resource_availability():
    result = await agent.execute_task(task, context)
else:
    await agent.wait_for_resources(timeout=30.0)
    result = await agent.execute_task(task, context)
```

---

## Learning and Adaptation

### Q: What is agent learning?

**A:** Agents can learn from past experiences and recommend best approaches for similar tasks.

### Q: How do I enable learning?

**A:**

```python
agent = HybridAgent(learning_enabled=True)
```

### Q: How do I record experiences?

**A:**

```python
await agent.record_experience(
    task_type="data_analysis",
    approach="parallel_tools",
    success=True,
    execution_time=2.5
)
```

### Q: How do I get recommendations?

**A:**

```python
approach = await agent.get_recommended_approach("data_analysis")
print(f"Recommended: {approach}")
```

---

## Collaboration

### Q: What is agent collaboration?

**A:** Agents can delegate tasks to other agents, perform peer review, and reach consensus.

### Q: How do I enable collaboration?

**A:**

```python
agent = HybridAgent(
    collaboration_enabled=True,
    agent_registry={
        "agent2": other_agent_instance,
        "agent3": another_agent_instance
    }
)
```

### Q: How do I delegate tasks?

**A:**

```python
result = await agent.delegate_task(
    task_description="Analyze this data",
    target_agent_id="agent2"
)
```

---

## Health Monitoring

### Q: How do I check agent health?

**A:**

```python
health = agent.get_health_status()
print(f"Status: {health['status']}")  # healthy, degraded, unhealthy
print(f"Score: {health['score']}")  # 0-100
```

### Q: What affects health score?

**A:** Health score is based on:
- Error rate
- Response time
- Resource usage
- Recent failures

### Q: How do I get comprehensive status?

**A:**

```python
status = agent.get_comprehensive_status()
print(f"Capabilities: {status['capabilities']}")
print(f"Metrics: {status['metrics']}")
print(f"Health: {status['health']}")
```

---

## Troubleshooting

### Q: My tool instances aren't preserving state

**A:** Ensure tools are created before agent initialization:

```python
# ✅ Correct
tool = MyTool()
agent = HybridAgent(tools={"tool": tool})

# ❌ Wrong
agent = HybridAgent(tools={})
tool = MyTool()  # Too late!
```

### Q: My custom LLM client isn't working

**A:** Verify it implements `LLMClientProtocol`:

```python
# Check required methods
assert hasattr(llm_client, 'generate_text')
assert hasattr(llm_client, 'stream_text')
assert hasattr(llm_client, 'close')
assert hasattr(llm_client, 'provider_name')
```

### Q: ContextEngine isn't persisting data

**A:** Ensure ContextEngine is initialized and same instance used:

```python
# ✅ Correct
context_engine = ContextEngine()
await context_engine.initialize()
agent1 = HybridAgent(context_engine=context_engine)
agent2 = HybridAgent(context_engine=context_engine)  # Same instance

# ❌ Wrong
agent1 = HybridAgent(context_engine=ContextEngine())
agent2 = HybridAgent(context_engine=ContextEngine())  # Different!
```

### Q: Performance is slower than expected

**A:** Check:
1. Are you using caching? Enable it for repeated queries
2. Are tools independent? Use parallel execution
3. Are resource limits too restrictive? Adjust limits
4. Check performance metrics: `agent.get_performance_metrics()`

---

## Migration Questions

### Q: How do I migrate from tool names to tool instances?

**A:** See `UPGRADE_GUIDE.md` Example 1 for step-by-step instructions.

### Q: How do I migrate from BaseLLMClient to custom client?

**A:** See `UPGRADE_GUIDE.md` Example 2 for step-by-step instructions.

### Q: Can I migrate gradually?

**A: Yes!** Adopt features incrementally:
1. Start with tool instances (if needed)
2. Add ContextEngine (if needed)
3. Add performance features (if needed)
4. Add production features (if needed)

---

## Additional Resources

- **Migration Guide**: `./MIGRATION_GUIDE.md`
- **Upgrade Guide**: `./UPGRADE_GUIDE.md`
- **Integration Guide**: `./AGENT_INTEGRATION.md`
- **Examples**: `./EXAMPLES.md`
- **API Reference**: `./API_REFERENCE.md`
- **Release Notes**: `../../openspec/changes/enhance-hybrid-agent-flexibility/RELEASE_NOTES.md`

---

## Still Have Questions?

If you have questions not covered here:
1. Check the documentation in this directory
2. Review the examples in `./EXAMPLES.md`
3. Check the API reference in `./API_REFERENCE.md`
4. File an issue or ask in the team chat



# Migration Checklist: Enhanced Hybrid Agent Flexibility

## Quick Start

**✅ No migration required!** All changes are backward compatible. This checklist helps you adopt new features gradually.

---

## Pre-Migration Assessment

### Step 1: Assess Your Current Usage

- [ ] **Review your agent creation code**
  - Identify where agents are created
  - Note which agent types you use (HybridAgent, ToolAgent, LLMAgent)
  - Document current tool and LLM client usage

- [ ] **Identify pain points**
  - Do you need stateful tools with dependencies?
  - Do you have custom LLM wrappers that don't inherit from BaseLLMClient?
  - Do you need persistent conversation history?
  - Do you need session management?
  - Do you need checkpointing for LangGraph?

- [ ] **Review dependencies**
  - Check if you're using ContextEngine
  - Check if you have custom config managers
  - Check if you need checkpointing functionality

---

## Migration Checklist by Feature

### ✅ No Action Required (Backward Compatible)

- [x] **Existing agent code continues to work**
  - No changes needed to existing agent creation
  - Tool names (`List[str]`) still work
  - `BaseLLMClient` instances still work
  - All existing methods unchanged

### 🆕 Optional: Adopt Tool Instances

**When to adopt**: You have tools that need state or dependencies

- [ ] **Identify stateful tools**
  - List tools that need dependencies (ContextEngine, LLM clients, etc.)
  - Document tool initialization requirements

- [ ] **Create tool instances**
  ```python
  # Example: Create tool instances with dependencies
  context_engine = ContextEngine()
  await context_engine.initialize()
  
  read_context_tool = ReadContextTool(context_engine=context_engine)
  smart_analysis_tool = SmartAnalysisTool(llm_manager=llm_manager)
  ```

- [ ] **Update agent creation**
  ```python
  # Change from tool names to tool instances
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools={
          "read_context": read_context_tool,  # Changed from ["read_context"]
          "smart_analysis": smart_analysis_tool
      },
      config=config
  )
  ```

- [ ] **Test tool state preservation**
  - Verify tool state persists across operations
  - Test tool dependencies work correctly

### 🆕 Optional: Adopt Custom LLM Clients

**When to adopt**: You have custom LLM wrappers that don't inherit from BaseLLMClient

- [ ] **Identify custom LLM clients**
  - List custom LLM wrappers (e.g., LLMIntegrationManager)
  - Document their interface requirements

- [ ] **Verify protocol compliance**
  - Ensure custom client implements `LLMClientProtocol`
  - Required methods: `generate_text()`, `stream_text()`, `close()`
  - Required attribute: `provider_name`

- [ ] **Update agent creation**
  ```python
  # Use custom LLM client directly (no adapter needed)
  agent = LLMAgent(
      agent_id="agent1",
      name="My Agent",
      llm_client=CustomLLMClient(),  # Works without BaseLLMClient inheritance
      config=config
  )
  ```

- [ ] **Test LLM client integration**
  - Verify text generation works
  - Test streaming functionality
  - Verify error handling

### 🆕 Optional: Adopt ContextEngine Integration

**When to adopt**: You need persistent conversation history

- [ ] **Set up ContextEngine**
  ```python
  from aiecs.domain.context import ContextEngine
  
  context_engine = ContextEngine()
  await context_engine.initialize()
  ```

- [ ] **Update agent creation**
  ```python
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      context_engine=context_engine  # Add ContextEngine
  )
  ```

- [ ] **Update conversation management**
  ```python
  # Use agent's conversation methods
  await agent.add_conversation_message("user", "Hello", session_id)
  history = await agent.get_conversation_history(session_id)
  ```

- [ ] **Test persistence**
  - Verify conversation history persists across restarts
  - Test session isolation

### 🆕 Optional: Adopt Session Management

**When to adopt**: You need session lifecycle management and metrics

- [ ] **Create sessions**
  ```python
  session_id = await agent.create_session(user_id="user123")
  ```

- [ ] **Track session requests**
  ```python
  await agent.track_session_request(session_id)
  ```

- [ ] **Get session metrics**
  ```python
  metrics = await agent.get_session_metrics(session_id)
  ```

- [ ] **End sessions**
  ```python
  await agent.end_session(session_id)
  ```

- [ ] **Set up cleanup**
  ```python
  # Cleanup inactive sessions periodically
  await agent.cleanup_inactive_sessions(max_age_hours=24)
  ```

### 🆕 Optional: Adopt Custom Config Manager

**When to adopt**: You need dynamic configuration from external sources

- [ ] **Create config manager**
  ```python
  class DatabaseConfigManager:
      async def get_config(self, key: str, default: Any = None) -> Any:
          return await db.get_config(key) or default
      
      async def set_config(self, key: str, value: Any) -> None:
          await db.update_config(key, value)
      
      async def reload_config(self) -> None:
          await db.reload_config()
  ```

- [ ] **Update agent creation**
  ```python
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      config_manager=DatabaseConfigManager()
  )
  ```

- [ ] **Test config updates**
  - Verify runtime config updates work
  - Test config reload functionality

### 🆕 Optional: Adopt Custom Checkpointer

**When to adopt**: You need LangGraph integration or custom state persistence

- [ ] **Create checkpointer**
  ```python
  class RedisCheckpointer:
      async def save_checkpoint(
          self, agent_id: str, session_id: str, checkpoint_data: Dict[str, Any]
      ) -> str:
          checkpoint_id = f"checkpoint-{uuid.uuid4()}"
          await redis.set(f"checkpoint:{agent_id}:{session_id}:{checkpoint_id}", 
                         json.dumps(checkpoint_data))
          return checkpoint_id
      
      async def load_checkpoint(
          self, agent_id: str, session_id: str, checkpoint_id: str = None
      ) -> Dict[str, Any]:
          # Implementation
          ...
  ```

- [ ] **Update agent creation**
  ```python
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      checkpointer=RedisCheckpointer()
  )
  ```

- [ ] **Test checkpointing**
  - Verify checkpoint save/load works
  - Test checkpoint listing

### 🆕 Optional: Adopt Performance Features

**When to adopt**: You need better performance (caching, parallel execution, streaming)

- [ ] **Enable tool caching**
  ```python
  from aiecs.domain.agent.base_agent import CacheConfig
  
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      cache_config=CacheConfig(enabled=True, default_ttl=300)
  )
  ```

- [ ] **Use parallel tool execution**
  ```python
  results = await agent.execute_tools_parallel([
      {"tool": "search", "operation": "query", "parameters": {"q": "AI"}},
      {"tool": "calculator", "operation": "add", "parameters": {"a": 1, "b": 2}}
  ])
  ```

- [ ] **Use streaming responses**
  ```python
  async for event in agent.execute_task_streaming(task, context):
      if event['type'] == 'token':
          print(event['content'], end='', flush=True)
  ```

### 🆕 Optional: Adopt Reliability Features

**When to adopt**: You need better error handling and resource management

- [ ] **Enable resource limits**
  ```python
  from aiecs.domain.agent.models import ResourceLimits
  
  resource_limits = ResourceLimits(
      max_concurrent_tasks=5,
      max_tokens_per_minute=10000
  )
  
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      resource_limits=resource_limits
  )
  ```

- [ ] **Enable learning**
  ```python
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      learning_enabled=True
  )
  ```

- [ ] **Enable collaboration**
  ```python
  agent = HybridAgent(
      agent_id="agent1",
      name="My Agent",
      tools=["search"],
      llm_client=OpenAIClient(),
      collaboration_enabled=True,
      agent_registry={"agent2": other_agent}
  )
  ```

### 🆕 Optional: Adopt Observability Features

**When to adopt**: You need better monitoring and health tracking

- [ ] **Track operation performance**
  ```python
  with agent.track_operation_time("data_processing"):
      result = await agent.execute_task(task, context)
  ```

- [ ] **Get health status**
  ```python
  health = agent.get_health_status()
  print(f"Health: {health['status']}, Score: {health['score']}")
  ```

- [ ] **Get comprehensive status**
  ```python
  status = agent.get_comprehensive_status()
  ```

---

## Testing Checklist

After adopting any new features:

- [ ] **Unit tests pass**
  - Run existing tests to ensure no regressions
  - Add tests for new features

- [ ] **Integration tests pass**
  - Test end-to-end workflows
  - Verify feature interactions

- [ ] **Performance tests**
  - Verify performance overhead is acceptable
  - Test caching effectiveness
  - Test parallel execution speedup

- [ ] **Production readiness**
  - Monitor error rates
  - Check resource usage
  - Verify health status reporting

---

## Rollback Plan

If you encounter issues:

1. **Remove new optional parameters**
   - Revert to tool names if tool instances cause issues
   - Revert to BaseLLMClient if custom client has issues
   - Remove ContextEngine if persistence causes issues

2. **Disable new features**
   - Set `learning_enabled=False`
   - Set `collaboration_enabled=False`
   - Remove `resource_limits`

3. **Verify backward compatibility**
   - All existing code should still work
   - No breaking changes introduced

---

## Support Resources

- **Migration Guide**: `./MIGRATION_GUIDE.md`
- **Integration Guide**: `./AGENT_INTEGRATION.md`
- **Examples**: `./EXAMPLES.md`
- **API Reference**: `./API_REFERENCE.md`
- **Release Notes**: `../../openspec/changes/enhance-hybrid-agent-flexibility/RELEASE_NOTES.md`

---

## Summary

✅ **No migration required** - existing code works as-is
🆕 **New features are optional** - adopt gradually based on needs
📚 **Comprehensive documentation** - guides and examples available
🔄 **Backward compatible** - safe to upgrade



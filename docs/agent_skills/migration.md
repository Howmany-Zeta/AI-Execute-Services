# Migration Guide

This guide explains how to add skills support to existing AIECS agents.

## Overview

The Agent Skills Extension is designed as an opt-in enhancement. **No breaking changes are required** to adopt skills - existing agents continue to work without modification.

## Backward Compatibility

The skills system maintains full backward compatibility:

- ✅ Existing agents work unchanged
- ✅ No required API changes
- ✅ Skills are opt-in per agent
- ✅ No configuration changes required unless using skills

## Adding Skills to Existing Agents

### Step 1: Add the SkillCapableMixin

Modify your agent class to include the mixin:

**Before:**
```python
from aiecs.domain.agent.base import BaseAIAgent

class MyAgent(BaseAIAgent):
    def __init__(self, name: str, llm_client: LLMClient, **kwargs):
        super().__init__(name=name, llm_client=llm_client, **kwargs)
```

**After:**
```python
from aiecs.domain.agent.base import BaseAIAgent
from aiecs.domain.agent.skills import SkillCapableMixin, SkillRegistry

class MyAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        skill_registry: SkillRegistry = None,
        **kwargs
    ):
        super().__init__(name=name, llm_client=llm_client, **kwargs)
        # Initialize skill support
        self.__init_skills__(skill_registry=skill_registry)
```

### Step 2: Configure Skill Registry (Optional)

If you want to load skills from directories:

```python
from aiecs.domain.agent.skills import SkillRegistry, SkillDiscovery

# Create and populate registry
registry = SkillRegistry.get_instance()
discovery = SkillDiscovery(registry=registry)
await discovery.discover()

# Pass to agent
agent = MyAgent(
    name="assistant",
    llm_client=client,
    skill_registry=registry
)
```

### Step 3: Attach Skills

```python
# Attach skills by name
agent.attach_skills(["python-coding", "data-analysis"])

# Or attach skill instances directly
from aiecs.domain.agent.skills import SkillLoader

loader = SkillLoader()
skill = await loader.load_skill(Path("/path/to/skill"))
agent.attach_skill_instances([skill])
```

### Step 4: Use Skill Context

Integrate skill context into your agent's prompt handling:

```python
# In your agent's process method
def process(self, request: str) -> str:
    # Get skill context
    skill_context = self.get_skill_context()
    
    # Build system prompt with skill knowledge
    system_prompt = f"""You are a helpful assistant.

{skill_context}
"""
    
    # Continue with normal processing...
```

## Configuration Changes

### Environment Variables

The following optional environment variables can configure skills:

| Variable | Description | Default |
|----------|-------------|---------|
| `AIECS_SKILL_DIRECTORIES` | Comma-separated skill directories | Built-in skills only |
| `AIECS_SKILL_AUTO_DISCOVER` | Enable auto-discovery at startup | `false` |
| `AIECS_SKILL_MAX_CONCURRENT_DISCOVERY` | Max concurrent skill loading | `10` |

### Example Configuration

```bash
# .env file
AIECS_SKILL_DIRECTORIES=/app/skills,/shared/skills
AIECS_SKILL_AUTO_DISCOVER=true
```

## Migration Examples

### Example 1: Simple Agent

**Before:**
```python
class SimpleAgent(BaseAIAgent):
    async def run(self, task: str) -> str:
        return await self.llm_client.complete(task)
```

**After:**
```python
class SimpleAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_skills__()
    
    async def run(self, task: str) -> str:
        # Enrich prompt with skill context
        context = self.get_skill_context()
        enhanced_prompt = f"{context}\n\nTask: {task}" if context else task
        return await self.llm_client.complete(enhanced_prompt)
```

### Example 2: Agent with Custom Tools

**Before:**
```python
class ToolAgent(BaseAIAgent):
    def __init__(self, name, llm_client, tools):
        super().__init__(name=name, llm_client=llm_client)
        self.tools = tools
```

**After:**
```python
class ToolAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, name, llm_client, tools, skill_registry=None):
        super().__init__(name=name, llm_client=llm_client)
        self.tools = tools
        self.__init_skills__(skill_registry=skill_registry)
    
    # Override to integrate with agent's tool system
    def _has_tool(self, tool_name: str) -> bool:
        return tool_name in self.tools or tool_name in self._skill_tools
    
    def _add_tool(self, tool):
        self.tools[tool.name] = tool
    
    def _remove_tool(self, tool_name: str):
        if tool_name in self.tools:
            del self.tools[tool_name]
```

### Example 3: Agent with Existing Context Management

**Before:**
```python
class ContextAgent(BaseAIAgent):
    def __init__(self, *args, context_engine=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_engine = context_engine
    
    def get_context(self) -> str:
        return self.context_engine.get_context()
```

**After:**
```python
class ContextAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, context_engine=None, skill_registry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_engine = context_engine
        self.__init_skills__(skill_registry=skill_registry)
    
    def get_context(self) -> str:
        # Combine existing context with skill context
        base_context = self.context_engine.get_context()
        skill_context = self.get_skill_context()
        
        if skill_context:
            return f"{base_context}\n\n{skill_context}"
        return base_context
```

## Gradual Adoption

You can adopt skills gradually:

### Phase 1: Add Mixin (No Behavior Change)

```python
class MyAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_skills__()  # Skills available but not used
```

### Phase 2: Attach Skills on Demand

```python
# Only attach when needed
if task_requires_coding_help:
    agent.attach_skills(["python-coding"])
```

### Phase 3: Integrate Context

```python
# Add skill context to prompts
context = agent.get_skill_context()
```

### Phase 4: Use Script Execution

```python
# Execute skill scripts
result = await agent.execute_skill_script("python-coding", "validate-python", {...})
```

## Troubleshooting

### Skill Not Found

```python
# Check available skills
registry = SkillRegistry.get_instance()
print(registry.list_skills())

# Ensure discovery ran
discovery = SkillDiscovery()
result = await discovery.discover()
print(f"Discovered: {result.success_count}, Failed: {result.failure_count}")
```

### Script Execution Fails

```python
result = await agent.execute_skill_script("skill", "script", {...})

if not result.success:
    print(f"Error: {result.error}")
    print(f"Exit code: {result.exit_code}")
    print(f"Stderr: {result.stderr}")
```

### Skill Registry Not Configured

```python
# Error: "Skill registry not configured"
# Solution: Pass registry to __init_skills__

self.__init_skills__(skill_registry=SkillRegistry.get_instance())

# Or use attach_skill_instances() instead of attach_skills()
```

## Rollback

If you need to remove skill support:

1. Remove `SkillCapableMixin` from class inheritance
2. Remove `__init_skills__()` call from `__init__`
3. Remove skill-related parameters
4. Remove any `get_skill_context()` or `execute_skill_script()` calls

The agent will return to its original behavior.

---

**Back to:** [Overview](./README.md) | [Using Skills](./using_skills.md)


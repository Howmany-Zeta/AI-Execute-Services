# Using Skills

This guide explains how to integrate skills with your AIECS agents.

## Overview

There are three strategies for integrating skills:

1. **Context Injection** (default) - Skills provide knowledge for prompts
2. **Direct Script Execution** - Programmatically call skill scripts
3. **Tool Registration** - Register skill scripts as LLM-callable tools

## Setting Up Skills

### Initialize Skill Infrastructure

```python
from aiecs.domain.agent.skills import (
    SkillRegistry,
    SkillDiscovery,
    SkillCapableMixin,
)

# Get or create registry
registry = SkillRegistry.get_instance()

# Discover skills from directories
discovery = SkillDiscovery(registry=registry)
result = await discovery.discover()
print(f"Discovered {result.success_count} skills")
```

### Create a Skill-Capable Agent

Use the `SkillCapableMixin` to add skill capabilities:

```python
from aiecs.domain.agent.base import BaseAIAgent
from aiecs.domain.agent.skills import SkillCapableMixin, SkillRegistry

class MyAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, skill_registry=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_skills__(skill_registry=skill_registry)

# Create agent with skill support
agent = MyAgent(
    name="assistant",
    llm_client=my_llm_client,
    skill_registry=SkillRegistry.get_instance()
)
```

## Attaching Skills

### Attach by Name

```python
# Attach skills from the registry
attached = agent.attach_skills(["python-coding", "data-analysis"])
print(f"Attached: {attached}")
```

### Attach Instances Directly

```python
from aiecs.domain.agent.skills import SkillLoader

loader = SkillLoader()
skill = await loader.load_skill(Path("/path/to/my-skill"))

# Attach the skill instance
agent.attach_skill_instances([skill])
```

### Attachment Options

```python
# With options
agent.attach_skills(
    skill_names=["python-coding"],
    auto_register_tools=True,      # Register scripts as LLM tools
    inject_script_paths=True,       # Include script paths in context
)
```

## Strategy 1: Context Injection (Default)

Skills automatically provide context for agent prompts.

### Get Skill Context

```python
# Get formatted context from all attached skills
context = agent.get_skill_context()

# Include in system prompt
system_prompt = f"""You are a helpful assistant.

{context}
"""
```

### Context Options

```python
from aiecs.domain.agent.skills import ContextOptions

# Customize context generation
options = ContextOptions(
    include_body=True,         # Include skill body content
    include_scripts=True,      # Include script information
    include_resources=True,    # Include resource listings
    max_body_length=2000,      # Truncate long body content
)

context = agent._skill_context.build_context(
    skills=agent.attached_skills,
    options=options
)
```

## Strategy 2: Direct Script Execution

Execute skill scripts programmatically:

### Basic Execution

```python
result = await agent.execute_skill_script(
    skill_name="python-coding",
    script_name="validate-python",
    input_data={"file_path": "mycode.py"}
)

if result.success:
    print(f"Result: {result.result}")
else:
    print(f"Error: {result.error}")
```

### Execution Options

```python
from aiecs.domain.agent.skills import ExecutionMode

result = await agent.execute_skill_script(
    skill_name="python-coding",
    script_name="run-tests",
    input_data={"test_path": "tests/", "verbose": True},
    mode=ExecutionMode.SUBPROCESS,  # Force subprocess mode
    timeout=60,                      # Custom timeout
)

# Check execution details
print(f"Mode used: {result.mode_used.value}")
print(f"Execution time: {result.execution_time:.2f}s")
```

### List Available Scripts

```python
# List scripts for a skill
scripts = agent.list_skill_scripts("python-coding")
for name, script in scripts.items():
    print(f"{name}: {script.description}")

# Get info about specific script
info = agent.get_script_info("python-coding", "validate-python")
print(f"Path: {info.path}")
print(f"Parameters: {info.parameters}")
```

## Strategy 3: Tool Registration

Register skill scripts as LLM-callable tools:

### Enable Auto-Registration

```python
# Scripts become tools when attached with auto_register_tools=True
agent.attach_skills(
    ["python-coding"],
    auto_register_tools=True
)

# Now LLM can call these tools:
# - python-coding_validate-python
# - python-coding_run-tests
```

### List Skill Tools

```python
# See registered skill tools
tools = agent.list_skill_tools()
for name, tool in tools.items():
    print(f"{name}: {tool.description}")
```

## Tool Recommendations

Skills can recommend tools for specific tasks:

### Get Recommendations

```python
# Get all recommended tools from attached skills
recommendations = agent.get_recommended_tools()
print(f"Recommended: {recommendations}")

# Filter by available tools
available = ["python", "pytest", "docker", "git"]
filtered = agent.get_recommended_tools(available_tools=available)
```

## Skill Management

### Check Attached Skills

```python
# List attached skill names
print(agent.skill_names)

# Check if specific skill is attached
if agent.has_skill("python-coding"):
    print("Python coding skill is active")

# Get skill definition
skill = agent.get_attached_skill("python-coding")
print(f"Version: {skill.metadata.version}")
```

### Detach Skills

```python
# Detach specific skills
detached = agent.detach_skills(["data-analysis"])

# Detach all skills
detached = agent.detach_all_skills()
```

### Load Skill Resources

```python
# Load content from a skill resource
content = await agent.load_skill_resource(
    skill_name="python-coding",
    resource_path="references/best-practices.md"
)
print(content)
```

## Skill Matching

Find skills that match a request:

```python
from aiecs.domain.agent.skills import SkillMatcher

matcher = SkillMatcher(registry=SkillRegistry.get_instance())

# Find matching skills
matches = matcher.match("I need help writing Python unit tests")

for match in matches:
    print(f"{match.skill_name}: {match.score:.2f} - {match.reason}")
```

## Error Handling

### Script Execution Errors

```python
try:
    result = await agent.execute_skill_script(
        "python-coding", "validate-python",
        {"file_path": "nonexistent.py"}
    )

    if not result.success:
        if result.timed_out:
            print("Script timed out")
        elif result.blocking_error:
            print(f"Blocking error (exit code 2): {result.error}")
        else:
            print(f"Error: {result.error}")
except ValueError as e:
    print(f"Invalid skill/script: {e}")
```

### Skill Not Found

```python
try:
    agent.attach_skills(["nonexistent-skill"])
except ValueError as e:
    print(f"Skill not found: {e}")
```

## Configuration

### Environment Variables

```bash
# Skill directories (comma-separated)
export AIECS_SKILL_DIRECTORIES="/path/to/skills,/another/path"

# Auto-discovery at startup
export AIECS_SKILL_AUTO_DISCOVER=true

# Max concurrent discovery
export AIECS_SKILL_MAX_CONCURRENT_DISCOVERY=10
```

### Programmatic Configuration

```python
from aiecs.domain.agent.skills import SkillDiscovery

discovery = SkillDiscovery(
    directories=[Path("/custom/skills")],
    auto_register=True,
    skip_registered=True,
    max_concurrent=20
)
```

## Best Practices

1. **Attach skills before processing** - Ensure skills are attached before the agent starts processing requests

2. **Use context injection for knowledge** - Best for providing reference information and guidelines

3. **Use direct execution for actions** - Best for validation, testing, and transformation tasks

4. **Use tool registration sparingly** - Only when LLM needs autonomous script access

5. **Handle script errors** - Always check `result.success` after script execution

6. **Monitor execution time** - Use `result.execution_time` to identify slow scripts

---

**Previous:** [Creating Skills](./creating_skills.md) | **Next:** [SKILL.md Reference](./skill_reference.md)


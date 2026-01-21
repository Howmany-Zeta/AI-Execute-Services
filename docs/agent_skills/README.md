# Agent Skills Extension

The Agent Skills Extension provides a modular, reusable knowledge system for AIECS agents. Inspired by the Claude Code agent skills pattern, this extension enables agents to dynamically acquire specialized knowledge and capabilities through declarative skill definitions.

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Creating Skills](./creating_skills.md) | Guide to creating custom skills |
| [Using Skills](./using_skills.md) | Guide to integrating skills with agents |
| [SKILL.md Reference](./skill_reference.md) | Complete SKILL.md format specification |
| [Examples](./examples.md) | Example skills and usage patterns |

## 🌟 Key Features

- **Progressive Disclosure**: Metadata loads instantly, body content loads when needed, resources load on demand
- **Auto-Discovery**: Automatically find and load skills from configured directories
- **Flexible Integration**: Multiple strategies for integrating skills with agents
- **Script Execution**: Run skill scripts in native Python or subprocess modes
- **Tool Recommendations**: Skills can recommend tools to use for specific tasks
- **Validation**: Comprehensive validation of skill definitions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SkillCapableMixin                           │
│  (Provides skill attachment, context injection, script execution)│
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ SkillRegistry │   │  SkillContext   │   │SkillScriptExecutor│
│ (Stores skills)│   │ (Builds prompts)│   │ (Runs scripts)  │
└───────────────┘   └─────────────────┘   └─────────────────┘
        ▲                                          │
        │                                          │
┌───────────────┐                         ┌─────────────────┐
│ SkillDiscovery│                         │ SkillDefinition │
│  (Auto-finds) │                         │    (Model)      │
└───────────────┘                         └─────────────────┘
        ▲                                          ▲
        │                                          │
┌───────────────┐                         ┌─────────────────┐
│  Skill Dirs   │─────────────────────────│   SKILL.md     │
│   (Files)     │                         │    (Files)      │
└───────────────┘                         └─────────────────┘
```

## 🚀 Quick Start

### 1. Attach Skills to an Agent

```python
from aiecs.domain.agent.skills import SkillCapableMixin, SkillRegistry

class MyAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_skills__(skill_registry=SkillRegistry.get_instance())

# Attach skills by name
agent = MyAgent(name="assistant", llm_client=client)
agent.attach_skills(["python-coding", "data-analysis"])
```

### 2. Get Skill Context for Prompts

```python
# Get context from attached skills
context = agent.get_skill_context()
# Include in system prompt or user message
```

### 3. Execute Skill Scripts

```python
# Execute a skill script directly
result = await agent.execute_skill_script(
    skill_name="python-coding",
    script_name="validate-python",
    input_data={"file_path": "mycode.py"}
)
```

## 📁 Skill Directory Structure

A skill is a directory containing a `SKILL.md` file:

```
my-skill/
├── SKILL.md           # Skill definition (required)
├── scripts/           # Executable scripts
│   └── helper.py
├── references/        # Reference documentation
│   └── guide.md
├── examples/          # Example code/configs
│   └── sample.py
└── assets/            # Static assets
    └── template.json
```

## ⚙️ Configuration

Set skill directories via environment variable or configuration:

```bash
export AIECS_SKILL_DIRECTORIES="/path/to/skills,/another/path"
```

Or configure programmatically:

```python
from aiecs.domain.agent.skills import SkillDiscovery

discovery = SkillDiscovery()
discovery.add_directory(Path("/path/to/skills"))
result = await discovery.discover()
```

## 🔗 Related Documentation

- [Agent Integration Guide](../user/DOMAIN_AGENT/AGENT_INTEGRATION.md)
- [API Reference](../api/domain.rst)

---

**Last Updated:** Phase 7 (Documentation)  
**Related OpenSpec:** `add-agent-skills-extension`


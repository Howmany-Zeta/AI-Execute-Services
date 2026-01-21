# Creating Skills

This guide explains how to create custom skills for the Agent Skills Extension.

## Overview

A skill is a modular knowledge package that agents can dynamically load. Each skill consists of:

1. **SKILL.md file**: Defines metadata and knowledge content
2. **Optional scripts**: Executable Python or shell scripts
3. **Optional resources**: References, examples, and assets

## Creating a Basic Skill

### Step 1: Create the Skill Directory

```bash
mkdir -p skills/my-custom-skill
cd skills/my-custom-skill
```

### Step 2: Create SKILL.md

Create a `SKILL.md` file with YAML frontmatter and Markdown body:

```markdown
---
name: my-custom-skill
description: A brief description of what this skill provides
version: 1.0.0
author: Your Name
tags:
  - category
  - topic
dependencies: []
recommended_tools:
  - tool-name
---

# My Custom Skill

Detailed information about this skill goes here.

## When to Use This Skill

Describe when an agent should activate this skill...

## Key Concepts

Explain the main concepts...

## Quick Reference

Provide quick reference information...
```

## Skill Metadata Fields

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique skill identifier (kebab-case) |
| `description` | string | Brief description for skill matching |
| `version` | string | Semantic version (X.Y.Z) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `author` | string | Skill author name |
| `tags` | list[string] | Tags for categorization and matching |
| `dependencies` | list[string] | Other skills this depends on |
| `recommended_tools` | list[string] | Tools to recommend when skill is active |
| `scripts` | dict | Script definitions (see below) |

## Adding Scripts

Scripts allow skills to provide executable functionality:

### Script Definition Format

```yaml
scripts:
  script-name:
    path: scripts/my-script.py
    mode: native  # or "subprocess" or "auto"
    description: What this script does
    parameters:
      param1:
        type: string
        required: true
        description: Description of param1
      param2:
        type: integer
        required: false
        description: Description of param2
```

### Execution Modes

| Mode | Description |
|------|-------------|
| `native` | Direct Python import (faster, default for .py) |
| `subprocess` | Run as subprocess (isolated, default for non-Python) |
| `auto` | Determine mode based on file extension |

### Writing Python Scripts

Python scripts must have an entry point function:

```python
# scripts/my-script.py

def execute(input_data: dict) -> dict:
    """Main entry point - receives input as dict, returns dict."""
    param1 = input_data.get("param1")

    # Do work...

    return {"result": "success", "data": processed_data}
```

Alternative entry points (checked in order): `execute`, `main`, `run`

### Async Script Support

```python
async def execute(input_data: dict) -> dict:
    """Async entry point is also supported."""
    result = await some_async_operation()
    return {"result": result}
```

### Shell Scripts

```bash
#!/bin/bash
# scripts/my-script.sh

# Input is provided via stdin as JSON
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.file_path')

# Do work...

# Output result as JSON to stdout
echo '{"success": true}'
```

## Adding Resources

### References

Documentation and guides the agent can consult:

```
my-skill/
└── references/
    ├── quick-start.md
    └── best-practices.md
```

Reference these in your SKILL.md body:
```markdown
See `references/best-practices.md` for detailed guidelines.
```

### Examples

Example code and configurations:

```
my-skill/
└── examples/
    ├── basic-usage.py
    └── advanced-config.json
```

### Assets

Static files like templates or data:

```
my-skill/
└── assets/
    ├── template.json
    └── config.yaml
```

## Validation

Validate your skill before deployment:

```python
from aiecs.domain.agent.skills import SkillLoader, SkillValidator

# Load the skill
loader = SkillLoader()
skill = await loader.load_skill(Path("skills/my-custom-skill"))

# Validate
validator = SkillValidator()
result = validator.validate(skill)

if result.valid:
    print("✅ Skill is valid!")
else:
    for issue in result.issues:
        print(f"❌ {issue}")
```

## Best Practices

### Naming Conventions

- Use **kebab-case** for skill names: `python-testing`, `api-integration`
- Use **semantic versioning**: `1.0.0`, `2.1.3`
- Use **lowercase tags**: `python`, `testing`, `web-api`

### Content Guidelines

1. **Be specific in descriptions** - helps with skill matching
2. **Include trigger phrases** - "When to Use This Skill" section
3. **Provide quick references** - tables and code snippets for fast lookup
4. **Link to resources** - reference your examples and documentation

### Script Guidelines

1. **Handle errors gracefully** - return error information in result dict
2. **Validate inputs** - check required parameters
3. **Use appropriate mode** - native for pure Python, subprocess for isolation
4. **Document parameters** - clear descriptions for each parameter

## Example: Complete Skill

```
api-testing/
├── SKILL.md
├── scripts/
│   ├── validate-openapi.py
│   └── generate-tests.py
├── references/
│   ├── http-methods.md
│   └── status-codes.md
├── examples/
│   ├── basic-api-test.py
│   └── mock-server.py
└── assets/
    └── test-template.json
```

See [Examples](./examples.md) for complete working examples.

---

**Next:** [Using Skills](./using_skills.md) | [SKILL.md Reference](./skill_reference.md)
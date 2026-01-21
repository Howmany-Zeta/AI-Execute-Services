# SKILL.md Format Reference

This document provides the complete specification for the SKILL.md file format.

## Overview

SKILL.md files define agent skills using YAML frontmatter for metadata and Markdown for content. The format follows the pattern:

```markdown
---
# YAML frontmatter (metadata)
name: skill-name
description: Brief description
version: 1.0.0
---

# Markdown Body (knowledge content)
```

## YAML Frontmatter Schema

### Required Fields

```yaml
name: string           # Unique identifier (kebab-case)
description: string    # Brief description (for matching)
version: string        # Semantic version (X.Y.Z)
```

### Optional Fields

```yaml
author: string                    # Author name
tags: list[string]               # Categorization tags
dependencies: list[string]       # Required skills
recommended_tools: list[string]  # Tools to recommend
scripts: dict                    # Script definitions
```

## Field Specifications

### name (required)

Unique skill identifier in kebab-case format.

**Format:** `^[a-z0-9]+(-[a-z0-9]+)*$`

**Examples:**
```yaml
name: python-testing        # ✅ Valid
name: api-integration       # ✅ Valid
name: data-analysis         # ✅ Valid
name: Python_Testing        # ❌ Invalid (uppercase, underscore)
name: my skill              # ❌ Invalid (space)
```

### description (required)

Brief description used for skill matching and display.

**Guidelines:**
- Keep under 200 characters
- Include key terms for matching
- Describe what the skill provides

**Example:**
```yaml
description: Comprehensive Python development guidance covering best practices, coding patterns, testing strategies, and code quality standards.
```

### version (required)

Semantic version following SemVer format.

**Format:** `^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$`

**Examples:**
```yaml
version: 1.0.0              # ✅ Valid
version: 2.1.3              # ✅ Valid
version: 1.0.0-beta.1       # ✅ Valid (prerelease)
version: 1.0.0+build.123    # ✅ Valid (build metadata)
version: 1.0                # ❌ Invalid (missing patch)
version: v1.0.0             # ❌ Invalid (leading 'v')
```

### author (optional)

Skill author name for attribution.

**Example:**
```yaml
author: AIECS Team
```

### tags (optional)

List of lowercase tags for categorization.

**Format:** Each tag should be `^[a-z0-9-]+$`

**Example:**
```yaml
tags:
  - python
  - testing
  - development
  - best-practices
```

### dependencies (optional)

List of required skills (by name).

**Example:**
```yaml
dependencies:
  - python-basics
  - testing-fundamentals
```

### recommended_tools (optional)

Tools to recommend when this skill is active.

**Example:**
```yaml
recommended_tools:
  - python
  - pytest
  - ruff
  - mypy
```

### scripts (optional)

Dictionary of executable script definitions.

**Schema:**
```yaml
scripts:
  script-name:                    # Unique script identifier
    path: string                  # Path relative to skill directory (required)
    mode: string                  # Execution mode: native|subprocess|auto
    description: string           # What the script does
    parameters:                   # Input parameters
      param-name:
        type: string             # Parameter type
        required: boolean        # Is required?
        description: string      # Parameter description
```

**Complete Example:**
```yaml
scripts:
  validate-syntax:
    path: scripts/validate.py
    mode: native
    description: Validates Python syntax and style
    parameters:
      file_path:
        type: string
        required: true
        description: Path to the Python file
      strict:
        type: boolean
        required: false
        description: Enable strict mode
  
  run-tests:
    path: scripts/test-runner.sh
    mode: subprocess
    description: Runs test suite
    parameters:
      test_path:
        type: string
        required: false
        description: Test file or directory
```

**Execution Modes:**

| Mode | Description | Default For |
|------|-------------|-------------|
| `native` | Direct Python import | `.py` files |
| `subprocess` | Run as subprocess | Non-Python files |
| `auto` | Determine by extension | - |

**Parameter Types:**

| Type | JSON Schema Equivalent |
|------|----------------------|
| `string` | string |
| `integer` | integer |
| `number` | number |
| `boolean` | boolean |
| `object` | object |
| `array` | array |

## Markdown Body

The body follows the YAML frontmatter and contains the skill's knowledge content.

### Structure Recommendations

```markdown
---
# frontmatter...
---

# Skill Title

Brief introduction.

## When to Use This Skill

Trigger conditions and use cases.

## Key Concepts

Main knowledge content.

## Quick Reference

Tables, code snippets, and cheat sheets.

## Resources

Links to references and examples.
```

### Content Guidelines

1. **Include trigger phrases** - Help skill matching
2. **Use headers** - Enable section extraction
3. **Add code examples** - Practical guidance
4. **Reference resources** - Link to files in skill directory

## Complete Example

```markdown
---
name: python-testing
description: Python testing best practices using pytest, including fixtures, mocking, and test organization.
version: 1.0.0
author: AIECS Team
tags:
  - python
  - testing
  - pytest
  - quality
dependencies:
  - python-coding
recommended_tools:
  - pytest
  - coverage
  - pytest-mock
scripts:
  run-tests:
    path: scripts/run-tests.py
    mode: native
    description: Runs pytest with specified options
    parameters:
      test_path:
        type: string
        required: false
        description: Path to test file or directory
      coverage:
        type: boolean
        required: false
        description: Enable coverage reporting
  generate-fixtures:
    path: scripts/gen-fixtures.py
    mode: native
    description: Generates test fixtures from sample data
    parameters:
      input_file:
        type: string
        required: true
        description: Path to sample data file
---

# Python Testing

This skill provides guidance for testing Python applications using pytest.

## When to Use This Skill

Activate this skill when:
- Writing unit tests or integration tests
- Setting up test infrastructure
- Debugging failing tests
- Improving test coverage

## Key Concepts

### Test Structure

```python
def test_function_name():
    # Arrange
    data = prepare_test_data()

    # Act
    result = function_under_test(data)

    # Assert
    assert result == expected_value
```

### Fixtures

```python
@pytest.fixture
def sample_data():
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -v` | Verbose output |
| `pytest -k "name"` | Filter by name |
| `pytest --cov` | With coverage |

## Resources

See `references/pytest-guide.md` for detailed pytest documentation.
```

## Validation

Use the SkillValidator to validate SKILL.md files:

```python
from aiecs.domain.agent.skills import SkillLoader, SkillValidator

loader = SkillLoader()
skill = await loader.load_skill(Path("path/to/skill"))

validator = SkillValidator(strict_mode=True)
result = validator.validate(skill)

print(result)  # Shows validation issues
```

### Validation Checks

- ✅ Required fields present (name, description, version)
- ✅ Name is kebab-case
- ✅ Version is semantic versioning
- ✅ Tags are lowercase
- ✅ Script paths exist
- ✅ Script modes are valid
- ✅ Parameter types are valid

---

**Previous:** [Using Skills](./using_skills.md) | **Next:** [Examples](./examples.md)


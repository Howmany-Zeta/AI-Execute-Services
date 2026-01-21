# Examples

This document provides complete examples of skills and their usage patterns.

## Built-in Skills

AIECS includes several built-in skills in `aiecs/domain/agent/skills/builtin/`:

### python-coding

```yaml
name: python-coding
description: Comprehensive Python development guidance
version: 1.0.0
scripts:
  validate-python:
    path: scripts/validate-python.sh
    mode: subprocess
  run-tests:
    path: scripts/run-tests.sh
    mode: subprocess
```

### data-analysis

```yaml
name: data-analysis
description: Data analysis and visualization guidance
version: 1.0.0
recommended_tools:
  - pandas
  - matplotlib
  - seaborn
```

### api-integration

```yaml
name: api-integration
description: REST API integration patterns and best practices
version: 1.0.0
recommended_tools:
  - requests
  - httpx
```

## Complete Skill Example

### Directory Structure

```
code-review/
├── SKILL.md
├── scripts/
│   ├── analyze-complexity.py
│   └── check-style.sh
├── references/
│   ├── review-checklist.md
│   └── common-issues.md
└── examples/
    └── sample-review.md
```

### SKILL.md

````markdown
---
name: code-review
description: Code review guidance with automated analysis for Python projects
version: 1.0.0
author: AIECS Team
tags:
  - code-review
  - quality
  - python
dependencies:
  - python-coding
recommended_tools:
  - ruff
  - mypy
  - bandit
scripts:
  analyze-complexity:
    path: scripts/analyze-complexity.py
    mode: native
    description: Analyzes cyclomatic complexity of Python modules
    parameters:
      file_path:
        type: string
        required: true
        description: Path to Python file
      threshold:
        type: integer
        required: false
        description: Complexity threshold (default 10)
  check-style:
    path: scripts/check-style.sh
    mode: subprocess
    description: Runs style checks using ruff
    parameters:
      directory:
        type: string
        required: true
        description: Directory to check
---

# Code Review

This skill provides guidance for conducting effective code reviews.

## When to Use This Skill

Activate this skill when:
- Reviewing pull requests
- Analyzing code quality
- Identifying potential issues
- Suggesting improvements

## Review Checklist

### Correctness
- [ ] Logic is correct
- [ ] Edge cases handled
- [ ] Error handling present

### Style
- [ ] Follows PEP 8
- [ ] Meaningful names
- [ ] Appropriate comments

### Security
- [ ] Input validation
- [ ] No hardcoded secrets
- [ ] Safe dependencies

## Common Issues

See `references/common-issues.md` for detailed issue descriptions.
````

### scripts/analyze-complexity.py

```python
"""Complexity analysis script."""
import ast
import sys
from pathlib import Path


def calculate_complexity(node):
    """Calculate cyclomatic complexity."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


def execute(input_data: dict) -> dict:
    """Analyze complexity of a Python file."""
    file_path = input_data.get("file_path")
    threshold = input_data.get("threshold", 10)

    if not file_path:
        return {"success": False, "error": "file_path is required"}

    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        source = path.read_text()
        tree = ast.parse(source)

        results = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = calculate_complexity(node)
                results.append({
                    "function": node.name,
                    "complexity": complexity,
                    "exceeds_threshold": complexity > threshold
                })

        return {
            "success": True,
            "file": str(file_path),
            "threshold": threshold,
            "functions": results,
            "total_issues": sum(1 for r in results if r["exceeds_threshold"])
        }
    except SyntaxError as e:
        return {"success": False, "error": f"Syntax error: {e}"}
```

## Usage Examples

### Example 1: Basic Skill Attachment

```python
from aiecs.domain.agent.skills import SkillCapableMixin, SkillRegistry

class ReviewAgent(SkillCapableMixin, BaseAIAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__init_skills__(skill_registry=SkillRegistry.get_instance())

agent = ReviewAgent(name="reviewer", llm_client=client)
agent.attach_skills(["code-review", "python-coding"])

# Get context for prompts
context = agent.get_skill_context()
```

### Example 2: Direct Script Execution

```python
# Run complexity analysis
result = await agent.execute_skill_script(
    skill_name="code-review",
    script_name="analyze-complexity",
    input_data={
        "file_path": "src/module.py",
        "threshold": 8
    }
)

if result.success:
    data = result.result
    print(f"Analyzed {data['file']}")
    print(f"Issues found: {data['total_issues']}")

    for func in data["functions"]:
        status = "⚠️" if func["exceeds_threshold"] else "✅"
        print(f"  {status} {func['function']}: {func['complexity']}")
else:
    print(f"Error: {result.error}")
```

### Example 3: Tool Registration

```python
# Attach with tool registration
agent.attach_skills(
    ["code-review"],
    auto_register_tools=True
)

# Now LLM can call:
# - code-review_analyze-complexity
# - code-review_check-style

tools = agent.list_skill_tools()
for name in tools:
    print(f"Tool available: {name}")
```

### Example 4: Skill Discovery

```python
from aiecs.domain.agent.skills import SkillDiscovery
from pathlib import Path

discovery = SkillDiscovery()
discovery.add_directory(Path("/custom/skills"))

result = await discovery.discover()

print(f"Discovered: {result.success_count}")
print(f"Failed: {result.failure_count}")
print(f"Skipped: {result.skip_count}")

for skill in result.discovered:
    print(f"  - {skill.metadata.name} v{skill.metadata.version}")
```

### Example 5: Skill Matching

```python
from aiecs.domain.agent.skills import SkillMatcher

matcher = SkillMatcher(registry=SkillRegistry.get_instance())

# Find skills matching a request
matches = matcher.match("I need to review this Python code for quality issues")

for match in matches[:3]:
    print(f"{match.skill_name}: {match.score:.2f}")
    print(f"  Reason: {match.reason}")
```

### Example 6: Skill Validation

```python
from aiecs.domain.agent.skills import SkillLoader, SkillValidator

loader = SkillLoader()
validator = SkillValidator(strict_mode=True)

skill = await loader.load_skill(Path("skills/my-skill"))
result = validator.validate(skill)

if result.valid:
    print("✅ Skill is valid")
else:
    print("❌ Validation failed:")
    for issue in result.errors:
        print(f"  ERROR: {issue}")
    for issue in result.warnings:
        print(f"  WARNING: {issue}")
```

## Integration Patterns

### Pattern 1: Dynamic Skill Loading

```python
async def handle_request(request: str, agent: SkillCapableMixin):
    # Match skills to request
    matcher = SkillMatcher(registry=SkillRegistry.get_instance())
    matches = matcher.match(request)

    # Attach top matching skills
    skill_names = [m.skill_name for m in matches[:3]]
    agent.attach_skills(skill_names)

    # Get enriched context
    context = agent.get_skill_context()

    # Process with skill knowledge
    result = await agent.process(request, context=context)

    return result
```

### Pattern 2: Skill-Enhanced Workflow

```python
async def code_review_workflow(file_path: str, agent: SkillCapableMixin):
    # Attach review skills
    agent.attach_skills(["code-review", "python-coding"])

    # Run automated analysis
    complexity_result = await agent.execute_skill_script(
        "code-review", "analyze-complexity",
        {"file_path": file_path}
    )

    style_result = await agent.execute_skill_script(
        "code-review", "check-style",
        {"directory": str(Path(file_path).parent)}
    )

    # Get context for LLM review
    context = agent.get_skill_context()

    # Have LLM provide review
    review_prompt = f"""
    Review the file: {file_path}

    Automated Analysis:
    - Complexity: {complexity_result.result}
    - Style: {style_result.result}

    {context}

    Provide a comprehensive review.
    """

    return await agent.process(review_prompt)
```

---

**Previous:** [SKILL.md Reference](./skill_reference.md) | [Back to Overview](./README.md)
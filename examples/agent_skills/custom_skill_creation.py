"""
Custom Skill Creation Guide

Demonstrates:
- SKILL.md file format and structure
- Directory structure for skills
- Using SkillLoader to load custom skills
- Validating skills with SkillValidator
- Creating skills programmatically

This guide shows how to create and validate custom skills for AIECS agents.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from aiecs.domain.agent.skills import (
    SkillDefinition,
    SkillLoader,
    SkillMetadata,
    SkillResource,
    SkillValidator,
    ValidationResult,
)


# =============================================================================
# SKILL.md File Format Reference
# =============================================================================

SKILL_MD_TEMPLATE = '''---
name: my-custom-skill
description: "Use this skill when asked to 'do something specific', 'perform this task', or mentions 'keyword'."
version: 1.0.0
author: Your Name
tags:
  - category
  - subcategory
dependencies: []
recommended_tools:
  - tool-name-1
  - tool-name-2
scripts:
  run_analysis:
    path: scripts/analyze.py
    mode: native
    description: Run analysis on input data
    parameters:
      input_file:
        type: string
        description: Path to input file
        required: true
      verbose:
        type: boolean
        description: Enable verbose output
---

# My Custom Skill

This is the body of the skill in Markdown format. It contains the knowledge
and instructions that will be injected into the agent's context.

## Key Concepts

- Concept 1: Explanation
- Concept 2: Explanation

## Best Practices

1. First practice
2. Second practice
3. Third practice

## Example Usage

```python
# Example code that demonstrates this skill
result = perform_task(input_data)
```
'''


def print_skill_structure() -> None:
    """Print the recommended skill directory structure."""
    print("""
Skill Directory Structure:
==========================

my-skill/
├── SKILL.md           # Required: Skill definition with YAML frontmatter
├── scripts/           # Optional: Executable scripts
│   ├── analyze.py
│   └── process.sh
├── references/        # Optional: Reference documentation
│   ├── api-docs.md
│   └── guidelines.md
├── examples/          # Optional: Example files
│   ├── basic-usage.py
│   └── advanced.py
└── assets/            # Optional: Additional assets
    ├── template.json
    └── config.yaml
""")


def create_skill_programmatically() -> SkillDefinition:
    """Create a skill definition programmatically."""
    metadata = SkillMetadata(
        name="code-review",
        description="Use when asked to 'review code', 'check code quality', or 'find bugs'.",
        version="1.0.0",
        author="AIECS Team",
        tags=["code-review", "quality", "best-practices"],
        recommended_tools=["linter", "static_analyzer"],
    )
    
    skill = SkillDefinition(
        metadata=metadata,
        skill_path=Path("/tmp/skills/code-review"),
        body="""
# Code Review Guidelines

When reviewing code, focus on:
1. **Correctness**: Does the code do what it's supposed to?
2. **Readability**: Is the code easy to understand?
3. **Maintainability**: Will this code be easy to modify?
4. **Performance**: Are there any obvious performance issues?
5. **Security**: Are there any security vulnerabilities?

## Code Smells to Watch For
- Long methods (>50 lines)
- Deep nesting (>3 levels)
- Magic numbers
- Duplicated code
- Poor naming
""",
        scripts={
            "lint": SkillResource(
                path="scripts/lint.py",
                type="script",
                mode="native",
                description="Run linter on code",
                parameters={
                    "file_path": {"type": "string", "required": True},
                    "fix": {"type": "boolean", "required": False},
                },
            ),
        },
        references={
            "style-guide": SkillResource(
                path="references/style-guide.md",
                type="reference",
            ),
        },
        examples={
            "review-example": SkillResource(
                path="examples/sample-review.md",
                type="example",
            ),
        },
    )
    
    return skill


def validate_skill(skill: SkillDefinition) -> ValidationResult:
    """Validate a skill definition."""
    validator = SkillValidator(
        strict_mode=False,
        validate_resources=False,  # Skip file existence check for demo
        validate_scripts=False,
    )

    return validator.validate(skill)


async def load_skill_from_directory(skill_path: Path) -> Optional[SkillDefinition]:
    """Load a skill from a directory using SkillLoader."""
    loader = SkillLoader()

    try:
        skill = await loader.load_skill(skill_path, load_body=True)
        return skill
    except Exception as e:
        print(f"Failed to load skill from {skill_path}: {e}")
        return None


async def demo_create_and_load_skill() -> None:
    """Demo creating a skill directory and loading it."""
    print("\n" + "=" * 60)
    print("Creating and Loading a Custom Skill")
    print("=" * 60)

    # Create temporary skill directory
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "demo-skill"
        skill_dir.mkdir()

        # Write SKILL.md
        skill_md_content = """---
name: demo-skill
description: "A demo skill for testing 'custom creation' and 'skill loading'."
version: 1.0.0
tags:
  - demo
  - example
recommended_tools:
  - demo_tool
---

# Demo Skill

This is a demonstration skill created for testing purposes.

## Features

- Feature 1
- Feature 2
"""
        (skill_dir / "SKILL.md").write_text(skill_md_content)

        # Create scripts directory
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "demo.py").write_text("print('Hello from demo script!')")

        print(f"Created skill at: {skill_dir}")

        # Load the skill
        skill = await load_skill_from_directory(skill_dir)

        if skill:
            print(f"\nLoaded skill: {skill.metadata.name}")
            print(f"  Version: {skill.metadata.version}")
            print(f"  Tags: {skill.metadata.tags}")
            print(f"  Body preview: {skill.body[:100] if skill.body else 'None'}...")

            # Validate the skill
            result = validate_skill(skill)
            print(f"\nValidation: {'PASSED' if result.valid else 'FAILED'}")
            for issue in result.issues:
                print(f"  - {issue}")


async def main() -> None:
    """Run the custom skill creation demo."""
    print("=" * 60)
    print("Custom Skill Creation Guide")
    print("=" * 60)

    # Show SKILL.md format
    print("\n1. SKILL.md File Format:")
    print("-" * 40)
    print(SKILL_MD_TEMPLATE[:500] + "...")

    # Show directory structure
    print("\n2. Recommended Directory Structure:")
    print_skill_structure()

    # Create skill programmatically
    print("\n3. Creating a Skill Programmatically:")
    print("-" * 40)
    skill = create_skill_programmatically()
    print(f"Created skill: {skill.metadata.name}")
    print(f"  Description: {skill.metadata.description}")
    print(f"  Tags: {skill.metadata.tags}")
    print(f"  Scripts: {list(skill.scripts.keys())}")

    # Validate skill
    print("\n4. Validating the Skill:")
    print("-" * 40)
    result = validate_skill(skill)
    print(f"Validation result: {result}")

    # Demo loading from directory
    await demo_create_and_load_skill()

    print("\n" + "=" * 60)
    print("Custom skill creation guide completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


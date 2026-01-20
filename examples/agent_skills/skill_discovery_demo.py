"""
Skill Discovery Demo

Demonstrates:
- Using SkillDiscovery to find skills from directories
- Using SkillRegistry to manage and look up skills
- Using SkillMatcher to match skills to user tasks

This example shows how to discover, register, and match skills dynamically.
"""

import asyncio
from pathlib import Path
from typing import List

from aiecs.domain.agent.skills import (
    MatchResult,
    SkillDefinition,
    SkillDiscovery,
    SkillMatcher,
    SkillMetadata,
    SkillRegistry,
    SkillResource,
)


def create_demo_skills() -> List[SkillDefinition]:
    """Create demo skills for the example."""
    python_skill = SkillDefinition(
        metadata=SkillMetadata(
            name="python-coding",
            description="Use when asked to 'write Python code', 'create a Python script', or 'implement in Python'.",
            version="1.0.0",
            tags=["python", "coding", "development"],
            recommended_tools=["code_executor", "linter"],
        ),
        skill_path=Path("/tmp/skills/python-coding"),
        body="Expert Python programming guidelines and patterns.",
    )
    
    testing_skill = SkillDefinition(
        metadata=SkillMetadata(
            name="python-testing",
            description="Use when asked to 'write tests', 'create unit tests', or 'test my code'.",
            version="1.0.0",
            tags=["python", "testing", "pytest"],
            recommended_tools=["pytest_runner", "coverage"],
        ),
        skill_path=Path("/tmp/skills/python-testing"),
        body="Python testing best practices with pytest.",
    )
    
    api_skill = SkillDefinition(
        metadata=SkillMetadata(
            name="api-integration",
            description="Use when asked to 'call an API', 'integrate with REST', or 'make HTTP requests'.",
            version="1.0.0",
            tags=["api", "rest", "http"],
            recommended_tools=["http_client", "json_parser"],
        ),
        skill_path=Path("/tmp/skills/api-integration"),
        body="RESTful API integration patterns and best practices.",
    )
    
    return [python_skill, testing_skill, api_skill]


def demo_skill_registry() -> SkillRegistry:
    """Demonstrate SkillRegistry usage."""
    print("\n" + "=" * 60)
    print("SkillRegistry Demo")
    print("=" * 60)
    
    # Reset registry for clean demo (normally not needed)
    SkillRegistry.reset_instance()
    registry = SkillRegistry.get_instance()
    
    # Register skills
    skills = create_demo_skills()
    for skill in skills:
        registry.register_skill(skill)
        print(f"Registered: {skill.metadata.name}")
    
    # List all skills
    print(f"\nTotal registered skills: {registry.skill_count()}")
    print(f"Skill names: {registry.list_skill_names()}")
    
    # Get skill by name
    skill = registry.get_skill("python-testing")
    if skill:
        print(f"\nLooked up skill: {skill.metadata.name} v{skill.metadata.version}")
    
    # Filter by tag
    python_skills = registry.get_skills_by_tag("python")
    print(f"\nSkills with 'python' tag: {[s.metadata.name for s in python_skills]}")
    
    # Find skills that recommend a specific tool
    skills_with_pytest = registry.find_skills_with_tool("pytest_runner")
    print(f"Skills recommending 'pytest_runner': {[s.metadata.name for s in skills_with_pytest]}")
    
    return registry


def demo_skill_matcher(registry: SkillRegistry) -> None:
    """Demonstrate SkillMatcher usage."""
    print("\n" + "=" * 60)
    print("SkillMatcher Demo")
    print("=" * 60)
    
    # Create matcher (can use registry or explicit skill list)
    matcher = SkillMatcher(registry=registry, default_threshold=0.1)
    
    # Match skills to user requests
    test_requests = [
        "write unit tests for my Python function",
        "create a REST API client",
        "help me write Python code",
    ]
    
    for request in test_requests:
        print(f"\nRequest: \"{request}\"")
        matches = matcher.match(request, max_results=3)
        
        if matches:
            for skill, score in matches:
                print(f"  - {skill.metadata.name}: score={score:.2f}")
        else:
            print("  No matching skills found")
    
    # Get detailed match results
    print("\nDetailed match for 'write tests':")
    detailed_results: List[MatchResult] = matcher.match_detailed("write tests")
    for result in detailed_results[:2]:
        print(f"  Skill: {result.skill.metadata.name}")
        print(f"    Score: {result.score:.2f}")
        print(f"    Matched phrases: {result.matched_phrases}")
        print(f"    Matched keywords: {result.matched_keywords}")


async def demo_skill_discovery() -> None:
    """Demonstrate SkillDiscovery usage."""
    print("\n" + "=" * 60)
    print("SkillDiscovery Demo")
    print("=" * 60)
    
    # Reset registry for clean demo
    SkillRegistry.reset_instance()
    registry = SkillRegistry.get_instance()
    
    # Create discovery instance
    discovery = SkillDiscovery(
        registry=registry,
        auto_register=True,  # Automatically register discovered skills
    )
    
    # Check configured directories
    directories = discovery.get_directories()
    print(f"Configured skill directories: {directories}")
    
    # Discover skills from builtin directory
    builtin_path = Path(__file__).parent.parent.parent / "aiecs" / "domain" / "agent" / "skills" / "builtin"
    
    if builtin_path.exists():
        print(f"\nDiscovering skills from: {builtin_path}")
        result = await discovery.discover(directories=[builtin_path])
        
        print(f"Discovery result: {result}")
        print(f"  Discovered: {result.success_count}")
        print(f"  Failed: {result.failure_count}")
        print(f"  Skipped: {result.skip_count}")
        
        if result.discovered:
            print("\nDiscovered skills:")
            for skill in result.discovered:
                print(f"  - {skill.metadata.name}: {skill.metadata.description[:50]}...")
    else:
        print(f"\nBuiltin skills directory not found at: {builtin_path}")
        print("Skipping discovery demo.")


async def main() -> None:
    """Run all skill demos."""
    print("=" * 60)
    print("Skill Discovery, Registry, and Matcher Demo")
    print("=" * 60)
    
    # Demo registry
    registry = demo_skill_registry()
    
    # Demo matcher
    demo_skill_matcher(registry)
    
    # Demo discovery (async)
    await demo_skill_discovery()
    
    print("\n" + "=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


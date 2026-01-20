"""
Basic Skill Usage Example

Demonstrates:
- Creating a skill-capable agent using SkillCapableMixin
- Attaching skills to an agent
- Loading skill context
- Accessing skill resources

This example shows the fundamental patterns for working with agent skills.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from aiecs.domain.agent.skills import (
    SkillCapableMixin,
    SkillDefinition,
    SkillLoader,
    SkillMetadata,
    SkillRegistry,
    SkillResource,
)


class SkillCapableAgent(SkillCapableMixin):
    """
    Example agent class that uses the SkillCapableMixin.
    
    This demonstrates how to integrate skill support into any agent class
    by mixing in SkillCapableMixin.
    """
    
    def __init__(
        self,
        name: str,
        skill_registry: Optional[SkillRegistry] = None,
    ) -> None:
        """
        Initialize the skill-capable agent.
        
        Args:
            name: Agent name
            skill_registry: Optional registry for loading skills by name
        """
        self.name = name
        # Initialize skill support from the mixin
        self.__init_skills__(skill_registry=skill_registry)
    
    def process_task(self, task_description: str) -> str:
        """
        Process a task with skill-enhanced context.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Response including skill context
        """
        # Get skill context to inject into prompt
        skill_context = self.get_skill_context(request=task_description)
        
        # In a real implementation, this would be sent to an LLM
        return f"Processing with context:\n{skill_context}\n\nTask: {task_description}"


def create_sample_skill() -> SkillDefinition:
    """Create a sample skill programmatically for demonstration."""
    metadata = SkillMetadata(
        name="python-testing",
        description="Use this skill when asked to 'write tests', 'create unit tests', or 'test code'.",
        version="1.0.0",
        author="AIECS Team",
        tags=["python", "testing", "pytest"],
        recommended_tools=["pytest_runner", "coverage_reporter"],
    )
    
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/tmp/skills/python-testing"),
        body="""
## Python Testing Best Practices

When writing Python tests:
1. Use pytest as the testing framework
2. Organize tests in a tests/ directory
3. Use descriptive test names with test_ prefix
4. Use fixtures for setup and teardown
5. Aim for high code coverage
""",
        scripts={
            "run_tests": SkillResource(
                path="scripts/run_tests.py",
                type="script",
                mode="native",
                description="Run pytest with coverage",
            ),
        },
    )


def main() -> None:
    """Run the basic skill usage example."""
    print("=" * 60)
    print("Basic Skill Usage Example")
    print("=" * 60)
    
    # Create a skill-capable agent
    agent = SkillCapableAgent(name="TestAgent")
    print(f"\n1. Created agent: {agent.name}")
    
    # Create and attach a skill directly (without registry)
    skill = create_sample_skill()
    attached = agent.attach_skill_instances(
        skills=[skill],
        auto_register_tools=False,
        inject_script_paths=True,
    )
    print(f"2. Attached skills: {attached}")
    
    # Check attached skills
    print(f"3. Agent has skill 'python-testing': {agent.has_skill('python-testing')}")
    print(f"4. All attached skill names: {agent.skill_names}")
    
    # Get skill context for a task
    context = agent.get_skill_context(request="write unit tests for my code")
    print(f"\n5. Skill context for 'write unit tests':\n{'-' * 40}")
    print(context[:500] + "..." if len(context) > 500 else context)
    
    # Get recommended tools
    tools = agent.get_recommended_tools()
    print(f"\n6. Recommended tools from attached skills: {tools}")
    
    # List available scripts
    scripts = agent.list_skill_scripts("python-testing")
    print(f"\n7. Available scripts: {list(scripts.keys())}")
    
    # Detach skills
    detached = agent.detach_skills(["python-testing"])
    print(f"\n8. Detached skills: {detached}")
    print(f"9. Remaining skills: {agent.skill_names}")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
Hybrid Agent with Skills Integration

Demonstrates:
- Using HybridAgent's built-in skill support (via BaseAIAgent)
- Skill-enhanced message processing
- Using skills in ReAct loop

This example shows how to use a HybridAgent with modular skill knowledge.
Note: HybridAgent already inherits SkillCapableMixin through BaseAIAgent,
so no additional mixin is needed.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiecs.domain.agent import AgentConfiguration, HybridAgent
from aiecs.domain.agent.skills import (
    SkillContext,
    SkillDefinition,
    SkillMatcher,
    SkillMetadata,
    SkillRegistry,
    SkillResource,
)


class SkillEnhancedHybridAgent(HybridAgent):
    """
    HybridAgent with enhanced skill integration patterns.

    HybridAgent already has skill support through SkillCapableMixin
    (inherited via BaseAIAgent). This class demonstrates how to add
    additional skill-related convenience methods.

    This agent combines:
    - LLM reasoning (from HybridAgent)
    - Tool execution (from HybridAgent)
    - Modular skill knowledge (from SkillCapableMixin via BaseAIAgent)

    Skills are automatically matched to user requests and their context
    is injected into the LLM prompt for enhanced responses.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Any,
        tools: Any,
        config: AgentConfiguration,
        skill_registry: Optional[SkillRegistry] = None,
        auto_match_skills: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the skill-enhanced hybrid agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client for reasoning
            tools: Available tools (list of names or dict of instances)
            config: Agent configuration
            skill_registry: Optional registry for loading skills by name
            auto_match_skills: If True, automatically match skills to requests
            **kwargs: Additional arguments for HybridAgent
        """
        # Initialize HybridAgent (which already has SkillCapableMixin)
        super().__init__(
            agent_id=agent_id,
            name=name,
            llm_client=llm_client,
            tools=tools,
            config=config,
            **kwargs,
        )

        # Set custom skill registry if provided
        if skill_registry is not None:
            self._skill_registry = skill_registry

        self.auto_match_skills = auto_match_skills
        self._custom_skill_matcher: Optional[SkillMatcher] = None

    def set_skill_matcher(self, matcher: SkillMatcher) -> None:
        """Set a custom skill matcher for request matching."""
        self._custom_skill_matcher = matcher

    def get_enhanced_system_prompt(self, request: str) -> str:
        """
        Build a system prompt enhanced with skill context.

        Args:
            request: User request to match skills against

        Returns:
            System prompt with injected skill knowledge
        """
        base_prompt = self._config.goal or "You are a helpful AI assistant."

        # Get skill context (automatically matches if matcher is set)
        skill_context = self.get_skill_context(request=request)

        if skill_context:
            return f"""{base_prompt}

## Specialized Knowledge

The following specialized knowledge is available for this task:

{skill_context}

Use this knowledge to provide accurate and helpful responses.
"""
        return base_prompt

    async def process_message_with_skills(
        self,
        message: str,
        sender_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a message with skill-enhanced context.

        This method:
        1. Matches relevant skills to the message
        2. Injects skill context into the reasoning
        3. Uses the ReAct loop for task execution

        Args:
            message: User message
            sender_id: Optional sender identifier

        Returns:
            Response with skill-enhanced reasoning
        """
        # Get enhanced system prompt with skill context
        enhanced_prompt = self.get_enhanced_system_prompt(message)

        # Get recommended tools from skills
        recommended = self.get_recommended_tools(request=message)

        # Process with HybridAgent (ReAct loop)
        result = await self.process_message(message, sender_id)

        # Add skill metadata to response
        result["skill_context"] = {
            "active_skills": self.skill_names,
            "recommended_tools": recommended,
            "enhanced_prompt_used": bool(enhanced_prompt != self._config.goal),
        }

        return result


def create_demo_skills() -> List[SkillDefinition]:
    """Create demo skills for the example."""
    research_skill = SkillDefinition(
        metadata=SkillMetadata(
            name="research-methodology",
            description="Use when asked to 'research', 'investigate', or 'find information'.",
            version="1.0.0",
            tags=["research", "methodology"],
            recommended_tools=["web_search", "document_reader"],
        ),
        skill_path=Path("/tmp/skills/research"),
        body="""
## Research Methodology

When conducting research:
1. Define the research question clearly
2. Identify reliable sources
3. Cross-reference information from multiple sources
4. Synthesize findings into coherent insights
5. Cite sources appropriately
""",
    )
    
    return [research_skill]


class MockLLMClient:
    """Mock LLM client for demonstration purposes."""

    provider_name = "mock"

    async def generate_text(self, messages: List[Dict[str, str]], **kwargs: Any) -> Any:
        """Generate a mock response."""
        from aiecs.llm import LLMResponse
        return LLMResponse(
            content=f"[Mock LLM Response] Processed {len(messages)} messages.",
            provider="mock",
            model="mock-model"
        )

    async def stream_text(self, messages: List[Dict[str, str]], **kwargs: Any) -> Any:
        """Stream mock response."""
        yield "[Mock LLM Response]"

    async def close(self) -> None:
        """Close the mock client."""
        pass


async def demo_skill_enhanced_agent() -> None:
    """Demonstrate the skill-enhanced hybrid agent."""
    print("\n" + "=" * 60)
    print("Skill-Enhanced Hybrid Agent Demo")
    print("=" * 60)

    # Create configuration
    config = AgentConfiguration(
        goal="Help users with research and analysis tasks",
        llm_model="gpt-4",
        temperature=0.7,
    )

    # Create mock LLM client (replace with real client in production)
    llm_client = MockLLMClient()

    # Create the skill-enhanced agent
    agent = SkillEnhancedHybridAgent(
        agent_id="research-agent-1",
        name="Research Assistant",
        llm_client=llm_client,
        tools=[],  # Add real tools in production
        config=config,
    )

    print(f"\n1. Created agent: {agent.name}")

    # Attach skills
    skills = create_demo_skills()
    attached = agent.attach_skill_instances(skills)
    print(f"2. Attached skills: {attached}")

    # Initialize agent
    await agent.initialize()
    await agent.activate()
    print("3. Agent initialized and activated")

    # Demonstrate enhanced prompt
    test_request = "Research the latest trends in AI agents"
    enhanced_prompt = agent.get_enhanced_system_prompt(test_request)
    print(f"\n4. Enhanced prompt for '{test_request}':")
    print("-" * 40)
    print(enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt)

    # Get recommended tools
    recommended_tools = agent.get_recommended_tools(request=test_request)
    print(f"\n5. Recommended tools: {recommended_tools}")

    # Show skill context
    skill_context = agent.get_skill_context(request=test_request)
    print(f"\n6. Skill context preview:")
    print("-" * 40)
    print(skill_context[:300] + "..." if len(skill_context) > 300 else skill_context)

    # Cleanup
    await agent.deactivate()
    await agent.shutdown()
    print("\n7. Agent shut down")


async def main() -> None:
    """Run the hybrid agent with skills demo."""
    print("=" * 60)
    print("Hybrid Agent with Skills Integration Example")
    print("=" * 60)

    print("""
This example demonstrates how to create an agent that combines:
- LLM reasoning capabilities (HybridAgent)
- Tool execution for actions (HybridAgent)
- Modular skill knowledge (SkillCapableMixin)

The SkillEnhancedHybridAgent class shows the pattern for integrating
skills into any agent type using Python's mixin pattern.
""")

    await demo_skill_enhanced_agent()

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)

    print("""
Key Takeaways:
--------------
1. HybridAgent already has skill support via BaseAIAgent (inherits SkillCapableMixin)
2. Use attach_skill_instances() to add skills to any agent
3. Use get_skill_context() to inject skill knowledge into prompts
4. Use get_recommended_tools() to get skill-based tool suggestions
5. Skills can be attached/detached dynamically at runtime
""")


if __name__ == "__main__":
    asyncio.run(main())


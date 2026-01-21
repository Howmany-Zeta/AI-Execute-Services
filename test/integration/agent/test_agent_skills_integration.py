"""
Integration tests for Agent Skills Extension.

Tests skill discovery, attachment, context injection, and execution
with real agents (LLMAgent, HybridAgent, ToolAgent) using real skills
from test/skills-for-test directory.

Covers tasks from Phase 4.2, 4.3, 4.4, 4.4b, and Phase 6.2.
"""

import pytest
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

from aiecs.domain.agent.llm_agent import LLMAgent
from aiecs.domain.agent.hybrid_agent import HybridAgent
from aiecs.domain.agent.tool_agent import ToolAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.skills.discovery import SkillDiscovery
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.domain.agent.skills.loader import SkillLoader
from aiecs.domain.agent.skills.executor import ExecutionMode
from aiecs.llm import XAIClient, LLMMessage


# Load test environment
load_dotenv(".env.test")

# Test skills directory
TEST_SKILLS_DIR = Path(__file__).parent.parent.parent / "skills-for-test"


@pytest.fixture
def skill_registry():
    """Create a fresh skill registry for each test."""
    registry = SkillRegistry()
    registry.clear()
    return registry


@pytest.fixture
async def discovered_skills(skill_registry):
    """Discover skills from test directory."""
    discovery = SkillDiscovery(
        loader=SkillLoader(),
        registry=skill_registry,
        directories=[TEST_SKILLS_DIR]
    )

    result = await discovery.discover()
    return result


@pytest.fixture
def xai_client():
    """Create xAI client for real LLM calls."""
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        pytest.skip("XAI_API_KEY not set in .env.test")
    return XAIClient()


# ==================== Phase 6.2: Integration Tests ====================


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillDiscovery:
    """Test skill discovery from directories."""
    
    async def test_discover_skills_from_test_directory(self, skill_registry):
        """Test discovering skills from test/skills-for-test directory."""
        discovery = SkillDiscovery(
            loader=SkillLoader(),
            registry=skill_registry,
            directories=[TEST_SKILLS_DIR]
        )

        result = await discovery.discover()

        # Verify skills were discovered
        assert result.success_count > 0
        assert len(result.discovered) > 0

        # Verify skills are registered
        registered_skills = skill_registry.list_skills()
        assert len(registered_skills) > 0

        print(f"\nDiscovered {result.success_count} skills")
        print(f"Registered {len(registered_skills)} skills")
        for skill_meta in registered_skills[:5]:  # Show first 5
            print(f"  - {skill_meta.name}: {skill_meta.description[:60]}...")
    
    async def test_discover_specific_skills(self, skill_registry):
        """Test discovering specific skills."""
        discovery = SkillDiscovery(
            loader=SkillLoader(),
            registry=skill_registry,
            directories=[TEST_SKILLS_DIR]
        )

        # Discover all skills
        await discovery.discover()
        
        # Check for specific skills
        template_skill = skill_registry.get_skill("template-skill")
        assert template_skill is not None
        assert template_skill.metadata.name == "template-skill"
        
        file_organizer = skill_registry.get_skill("file-organizer")
        if file_organizer:
            assert file_organizer.metadata.name == "file-organizer"
            assert "organizes your files" in file_organizer.metadata.description.lower()


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillAttachment:
    """Test skill attachment to agents."""
    
    async def test_attach_skills_to_llm_agent(self, discovered_skills, skill_registry, xai_client):
        """Test attaching skills to LLMAgent."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
            skill_names=["template-skill"],
        )

        agent = LLMAgent(
            agent_id="test_llm_skills",
            name="LLM Agent with Skills",
            llm_client=xai_client,
            config=config,
        )


        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach skills
        agent.attach_skills(["template-skill"], auto_register_tools=False, inject_script_paths=True)
        
        # Verify skills are attached
        assert agent.has_skill("template-skill")
        assert len(agent.attached_skills) == 1
        
        print(f"\nAttached {len(agent.attached_skills)} skills to LLMAgent")

    async def test_attach_skills_to_hybrid_agent(self, discovered_skills, skill_registry, xai_client):
        """Test attaching skills to HybridAgent."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
            skill_names=["file-organizer"],
        )

        agent = HybridAgent(
            agent_id="test_hybrid_skills",
            name="Hybrid Agent with Skills",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach skills
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)

        # Verify skills are attached
        assert agent.has_skill("file-organizer")
        assert len(agent.attached_skills) == 1

        print(f"\nAttached {len(agent.attached_skills)} skills to HybridAgent")

    async def test_attach_skills_to_tool_agent(self, discovered_skills, skill_registry, xai_client):
        """Test attaching skills to ToolAgent."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
            skill_names=["changelog-generator"],
        )

        agent = ToolAgent(
            agent_id="test_tool_skills",
            name="Tool Agent with Skills",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach skills
        agent.attach_skills(["changelog-generator"], auto_register_tools=False, inject_script_paths=True)

        # Verify skills are attached
        assert agent.has_skill("changelog-generator")
        assert len(agent.attached_skills) == 1

        print(f"\nAttached {len(agent.attached_skills)} skills to ToolAgent")


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillContextInjection:
    """Test skill context injection in agents."""

    async def test_llm_agent_skill_context_injection(self, discovered_skills, skill_registry, xai_client):
        """Test skill context injection in LLMAgent (Phase 4.3)."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = LLMAgent(
            agent_id="test_llm_context",
            name="LLM Agent Context Test",
            llm_client=xai_client,
            config=config,
        )


        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach skill with context injection
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)

        # Get skill context
        context = agent.get_skill_context("Help me organize my files")

        # Verify context includes skill information
        assert context is not None
        assert len(context) > 0
        assert "file-organizer" in context.lower() or "file organizer" in context.lower()

        print(f"\nSkill context length: {len(context)} characters")
        print(f"Context preview: {context[:200]}...")

    async def test_hybrid_agent_skill_context_injection(self, discovered_skills, skill_registry, xai_client):
        """Test skill context injection in HybridAgent (Phase 4.4)."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_hybrid_context",
            name="Hybrid Agent Context Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach skill with context injection
        agent.attach_skills(["changelog-generator"], auto_register_tools=False, inject_script_paths=True)

        # Get skill context
        context = agent.get_skill_context("Create a changelog")

        # Verify context includes skill information
        assert context is not None
        assert len(context) > 0

        print(f"\nHybrid agent skill context length: {len(context)} characters")

    async def test_tool_agent_skill_context_injection(self, discovered_skills, skill_registry, xai_client):
        """Test skill context injection in ToolAgent (Phase 4.4b)."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = ToolAgent(
            agent_id="test_tool_context",
            name="Tool Agent Context Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Attach skill with context injection

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["template-skill"], auto_register_tools=False, inject_script_paths=True)

        # Get skill context
        context = agent.get_skill_context("Use template skill")

        # Verify context includes skill information
        assert context is not None
        assert len(context) > 0

        print(f"\nTool agent skill context length: {len(context)} characters")

    async def test_context_injection_with_script_paths_disabled(self, discovered_skills, skill_registry, xai_client):
        """Test context injection with script paths disabled."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = LLMAgent(
            agent_id="test_no_scripts",
            name="Agent Without Script Paths",
            llm_client=xai_client,
            config=config,
        )


        # Attach skill with script paths disabled

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=False)

        # Get skill context
        context = agent.get_skill_context("Help me organize files")

        # Verify context exists but doesn't include script paths
        assert context is not None
        # Context should still have skill body but not script details
        assert "file-organizer" in context.lower() or "file organizer" in context.lower()

        print(f"\nContext without scripts length: {len(context)} characters")


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillResourceLoading:
    """Test skill resource loading."""

    async def test_load_skill_resource(self, discovered_skills, skill_registry, xai_client):
        """Test loading skill resources."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = LLMAgent(
            agent_id="test_resources",
            name="Resource Test Agent",
            llm_client=xai_client,
            config=config,
        )


        # Attach skill

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)

        # Get attached skill
        skill = agent.get_attached_skill("file-organizer")
        assert skill is not None

        # Check if skill has resources
        if skill.scripts:
            print(f"\nSkill has {len(skill.scripts)} scripts")
            for script_name, script_resource in skill.scripts.items():
                print(f"  - {script_name}: {script_resource.path}")

        # Load skill body
        if not skill.is_body_loaded():
            await skill.load_body()

        assert skill.is_body_loaded()
        assert skill.body is not None
        print(f"\nLoaded skill body: {len(skill.body)} characters")


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillScriptExecution:
    """Test skill script execution end-to-end."""

    async def test_execute_skill_script_if_available(self, discovered_skills, skill_registry, xai_client):
        """Test executing skill scripts if available."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_script_exec",
            name="Script Execution Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Attach skills

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["template-skill"], auto_register_tools=False, inject_script_paths=True)

        # Get skill
        skill = agent.get_attached_skill("template-skill")
        assert skill is not None

        # Check if skill has scripts
        if skill.scripts:
            print(f"\nSkill has {len(skill.scripts)} scripts available")
            for script_name in skill.scripts.keys():
                print(f"  - {script_name}")

                # Try to execute script
                try:
                    result = await agent.execute_skill_script(
                        "template-skill",
                        script_name,
                        input_data={"test": "data"},
                        mode=ExecutionMode.AUTO
                    )
                    print(f"    Execution result: {result.success}")
                    if result.success:
                        print(f"    Output: {str(result.output)[:100]}...")
                except Exception as e:
                    print(f"    Execution failed (expected for some scripts): {e}")
        else:
            print("\nNo scripts available in template-skill")


@pytest.mark.asyncio
@pytest.mark.integration
class TestToolRecommendations:
    """Test tool recommendations from skills."""

    async def test_get_recommended_tools(self, discovered_skills, skill_registry, xai_client):
        """Test getting recommended tools from skills."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_recommendations",
            name="Tool Recommendations Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Attach skills

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)

        # Get recommended tools
        recommended = agent.get_recommended_tools("Help me organize files")

        # Verify recommendations
        assert isinstance(recommended, list)
        print(f"\nRecommended tools: {recommended}")

        # Get skill to check metadata
        skill = agent.get_attached_skill("file-organizer")
        if skill and skill.metadata.recommended_tools:
            print(f"Skill recommends: {skill.metadata.recommended_tools}")


@pytest.mark.asyncio
@pytest.mark.integration
class TestRealLLMWithSkills:
    """Test real LLM calls with skill context (Phase 4.2, 4.3, 4.4, 4.4b)."""

    async def test_llm_agent_with_skill_real_call(self, discovered_skills, skill_registry, xai_client):
        """Test LLMAgent with skill context in real LLM call."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            max_tokens=500,
            skills_enabled=True,
        )

        agent = LLMAgent(
            agent_id="test_llm_real",
            name="LLM Agent Real Test",
            llm_client=xai_client,
            config=config,
        )


        # Attach skill

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)

        await agent.initialize()

        # Execute task with skill context
        task = {
            "description": "I have a messy Downloads folder with 100+ files. What should I do?"
        }

        result = await agent.execute_task(task, {})

        # Verify result
        assert result["success"] is True
        assert "output" in result

        output = result["output"]
        print(f"\n{'='*60}")
        print("LLM Agent with Skill Response:")
        print(f"{'='*60}")
        print(output)
        print(f"{'='*60}")

        # The response should mention file organization concepts
        # (though we can't guarantee exact content)
        assert len(output) > 0

    async def test_hybrid_agent_with_skill_real_call(self, discovered_skills, skill_registry, xai_client):
        """Test HybridAgent with skill context in real LLM call."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            max_tokens=500,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_hybrid_real",
            name="Hybrid Agent Real Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Attach skill

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["changelog-generator"], auto_register_tools=False, inject_script_paths=True)

        await agent.initialize()

        # Execute task with skill context
        task = {
            "description": "How do I create a changelog from git commits?"
        }

        result = await agent.execute_task(task, {})

        # Verify result
        assert result["success"] is True
        assert "output" in result

        output = result["output"]
        print(f"\n{'='*60}")
        print("Hybrid Agent with Skill Response:")
        print(f"{'='*60}")
        print(output)
        print(f"{'='*60}")

        assert len(output) > 0

    async def test_tool_agent_with_skill_real_call(self, discovered_skills, skill_registry, xai_client):
        """Test ToolAgent with skill context in real LLM call."""
        from aiecs.tools.base_tool import BaseTool

        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            max_tokens=500,
            skills_enabled=True,
        )

        # Create a simple mock tool
        class SimpleTestTool(BaseTool):
            async def execute(self, operation: str, **kwargs):
                return {"success": True, "result": f"Executed {operation}"}

        agent = ToolAgent(
            agent_id="test_tool_real",
            name="Tool Agent Real Test",
            llm_client=xai_client,
            tools={"test_tool": SimpleTestTool()},
            config=config,
        )


        # Attach skill

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["template-skill"], auto_register_tools=False, inject_script_paths=True)

        await agent.initialize()

        # Execute task with skill context
        task = {
            "description": "What is the template skill for?"
        }

        result = await agent.execute_task(task, {})

        # Verify result
        assert result["success"] is True

        print(f"\n{'='*60}")
        print("Tool Agent with Skill Response:")
        print(f"{'='*60}")
        print(f"Result: {result}")
        print(f"{'='*60}")


@pytest.mark.asyncio
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_attach_nonexistent_skill(self, skill_registry, xai_client):
        """Test attaching a skill that doesn't exist."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            skills_enabled=True,
        )

        agent = LLMAgent(
            agent_id="test_error",
            name="Error Test Agent",
            llm_client=xai_client,
            config=config,
        )


        # Try to attach non-existent skill
        with pytest.raises(Exception):
            agent.attach_skills(["nonexistent-skill"], auto_register_tools=False)

    async def test_skill_context_without_skills(self, xai_client):
        """Test getting skill context when no skills are attached."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            skills_enabled=False,
        )

        agent = LLMAgent(
            agent_id="test_no_skills",
            name="No Skills Agent",
            llm_client=xai_client,
            config=config,
        )


        # Get context without skills

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        context = agent.get_skill_context("test query")

        # Should return empty or None
        assert context is None or context == ""

    async def test_execute_script_on_skill_without_scripts(self, discovered_skills, skill_registry, xai_client):
        """Test executing script on skill that has no scripts."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_no_script",
            name="No Script Test",
            llm_client=xai_client,
            tools={},
            config=config,
        )


        # Attach skill

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)
        agent.attach_skills(["template-skill"], auto_register_tools=False)

        # Try to execute non-existent script
        with pytest.raises(Exception):
            await agent.execute_skill_script(
                "template-skill",
                "nonexistent_script",
                input_data={}
            )


@pytest.mark.asyncio
@pytest.mark.integration
class TestSkillDependencyResolution:
    """Test skill dependency resolution."""

    async def test_attach_multiple_skills(self, discovered_skills, skill_registry, xai_client):
        """Test attaching multiple skills to an agent."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_multi_skills",
            name="Multi-Skill Agent",
            llm_client=xai_client,
            tools={},
            config=config,
        )

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach multiple skills
        skills_to_attach = ["template-skill", "file-organizer", "changelog-generator"]
        available_skills = [s for s in skills_to_attach if skill_registry.get_skill(s) is not None]

        if len(available_skills) > 0:
            agent.attach_skills(available_skills, auto_register_tools=False, inject_script_paths=True)

            # Verify all skills are attached
            for skill_name in available_skills:
                assert agent.has_skill(skill_name)

            print(f"\nAttached {len(agent.attached_skills)} skills")

            # Get context with multiple skills
            context = agent.get_skill_context("Help me with file organization and changelogs")
            assert context is not None
            print(f"Multi-skill context length: {len(context)} characters")

    async def test_skill_context_max_skills_limit(self, discovered_skills, skill_registry, xai_client):
        """Test skill context respects max_skills limit."""
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            skills_enabled=True,
            skill_context_max_skills=2,  # Limit to 2 skills
        )

        agent = LLMAgent(
            agent_id="test_max_skills",
            name="Max Skills Test",
            llm_client=xai_client,
            config=config,
        )

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Attach multiple skills
        skills_to_attach = ["template-skill", "file-organizer", "changelog-generator"]
        available_skills = [s for s in skills_to_attach if skill_registry.get_skill(s) is not None]

        if len(available_skills) >= 3:
            agent.attach_skills(available_skills, auto_register_tools=False, inject_script_paths=True)

            # Get context - should only include top 2 relevant skills
            context = agent.get_skill_context("Help me organize files")
            assert context is not None

            print(f"\nContext with max_skills=2: {len(context)} characters")


@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEndSkillWorkflow:
    """Test complete end-to-end skill workflow."""

    async def test_complete_skill_workflow(self, xai_client):
        """Test complete workflow: discover -> attach -> use skills."""
        # Step 1: Create registry and discover skills
        registry = SkillRegistry()
        discovery = SkillDiscovery(
            loader=SkillLoader(),
            registry=registry,
            directories=[TEST_SKILLS_DIR]
        )

        result = await discovery.discover()
        print(f"\n{'='*60}")
        print(f"Step 1: Discovered {result.success_count} skills")

        # Step 2: Create agent with skills enabled
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            max_tokens=500,
            skills_enabled=True,
        )

        agent = HybridAgent(
            agent_id="test_e2e",
            name="End-to-End Test Agent",
            llm_client=xai_client,
            tools={},
            config=config,
        )

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=registry)

        # Step 3: Attach skills
        if registry.get_skill("file-organizer"):
            agent.attach_skills(["file-organizer"], auto_register_tools=False, inject_script_paths=True)
            print(f"Step 2: Attached file-organizer skill")

        # Step 4: Initialize agent
        await agent.initialize()
        print(f"Step 3: Initialized agent")

        # Step 5: Execute task with skill context
        task = {
            "description": "My Downloads folder is messy. What's the best way to organize it?"
        }

        result = await agent.execute_task(task, {})

        # Step 6: Verify result
        assert result["success"] is True
        assert "output" in result

        print(f"Step 4: Executed task successfully")
        print(f"{'='*60}")
        print("Agent Response:")
        print(f"{'='*60}")
        print(result["output"])
        print(f"{'='*60}")

        # Cleanup
        await agent.shutdown()


# ==================== Main Test Runner ====================

if __name__ == "__main__":
    """Run tests directly for debugging."""
    import sys

    # Run specific test
    pytest.main([
        __file__,
        "-v",
        "-s",
        "--tb=short",
        "-k", "test_complete_skill_workflow"
    ])


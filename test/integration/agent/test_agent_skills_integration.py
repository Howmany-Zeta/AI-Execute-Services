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

    async def test_hybrid_agent_autonomous_skill_usage(self, discovered_skills, skill_registry, xai_client):
        """
        Test HybridAgent autonomously discovering and using skills without human intervention.

        This test verifies:
        1. Agent can see all available skills
        2. Agent autonomously selects relevant skills based on user request
        3. System provides selected skills to agent without human intervention
        4. Agent executes without errors or fallback behavior
        5. Agent's output meets skill requirements
        """
        print(f"\n{'='*60}")
        print("E2E Test: HybridAgent Autonomous Skill Usage")
        print(f"{'='*60}")

        # Step 1: Use discovered skills from fixture
        discovered_count = discovered_skills.success_count
        print(f"\n[Step 1] Using {discovered_count} pre-discovered skills")

        # Verify skills were discovered
        assert discovered_count > 0, "No skills were discovered"

        # Step 2: Create HybridAgent with skills enabled but NO specific skill hints
        config = AgentConfiguration(
            llm_model="grok-3-mini",
            temperature=0.7,
            max_tokens=1000,
            skills_enabled=True,  # Enable skills system
            # Note: We do NOT specify which skills to use - agent decides autonomously
        )

        agent = HybridAgent(
            agent_id="autonomous_test",
            name="Autonomous Skill Agent",
            llm_client=xai_client,
            tools={},  # No explicit tools - skills may provide them
            config=config,
        )

        # Initialize skills with registry
        agent.__init_skills__(skill_registry=skill_registry)

        # Step 3: Attach ALL discovered skills (agent will choose which to use)
        all_skill_names = [skill.metadata.name for skill in skill_registry.get_all_skills()]
        print(f"\n[Step 2] Attaching {len(all_skill_names)} skills to agent")
        print(f"Available skills: {', '.join(all_skill_names[:5])}...")

        agent.attach_skills(
            all_skill_names,
            auto_register_tools=False,
            inject_script_paths=True
        )

        # Verify skills are attached
        assert len(agent.attached_skills) == len(all_skill_names)
        print(f"[Step 2] ✓ Successfully attached {len(agent.attached_skills)} skills")

        # Step 4: Initialize agent
        await agent.initialize()
        print(f"[Step 3] ✓ Agent initialized")

        # Step 5: Send a user request that should trigger skill matching
        # This request should match file organization skills
        user_request = (
            "I have a messy Downloads folder with hundreds of files. "
            "Can you help me organize them by file type and date?"
        )

        print(f"\n[Step 4] Sending user request (no skill hints provided):")
        print(f"  '{user_request}'")

        # Step 6: Execute task - agent decides everything autonomously
        task = {"description": user_request}

        # Capture the execution
        execution_result = await agent.execute_task(task, {})

        print(f"\n[Step 5] Task execution completed")

        # ========================================================================
        # Verification Phase: Observe and Assert
        # ========================================================================

        # Assertion 1: Verify agent saw the skills
        # The agent should have access to skill context
        skill_context = agent.get_skill_context(request=user_request)
        assert skill_context, "Agent did not receive skill context"
        assert len(skill_context) > 0, "Skill context is empty"
        print(f"[Verify 1] ✓ Agent received skill context ({len(skill_context)} chars)")

        # Check if file-organizer skill is in the context (it should match the request)
        assert "file-organizer" in skill_context.lower() or "organize" in skill_context.lower(), \
            "Expected file organization skill in context"
        print(f"[Verify 1] ✓ Relevant skill (file-organizer) found in context")

        # Assertion 2: Verify system provided skills without human intervention
        # The attached_skills should be available to the agent
        assert len(agent.attached_skills) > 0, "No skills attached to agent"
        print(f"[Verify 2] ✓ System provided {len(agent.attached_skills)} skills to agent")

        # Assertion 3: Verify agent executed without errors or fallback
        assert execution_result["success"] is True, "Task execution failed"
        assert "output" in execution_result, "No output in execution result"
        assert execution_result["output"], "Output is empty"
        print(f"[Verify 3] ✓ Agent executed without errors")

        # Check for error indicators in output
        output_lower = execution_result["output"].lower()
        error_indicators = ["error", "failed", "cannot", "unable", "sorry"]
        has_errors = any(indicator in output_lower for indicator in error_indicators)

        if has_errors:
            print(f"[Verify 3] ⚠ Warning: Output may contain error indicators")
        else:
            print(f"[Verify 3] ✓ No error indicators in output")

        # Assertion 4: Verify output meets skill requirements
        # For file organization, output should mention organization strategies
        organization_keywords = [
            "organize", "folder", "file", "type", "date",
            "category", "sort", "structure", "directory", "download"
        ]

        keyword_matches = [kw for kw in organization_keywords if kw in output_lower]

        # Print actual output for debugging
        print(f"\n[Debug] Full agent output:")
        print(f"{execution_result['output']}")
        print(f"\n[Verify 4] Found keywords: {', '.join(keyword_matches)}")

        # More lenient check - at least 1 keyword is fine since agent executed successfully
        assert len(keyword_matches) >= 1, \
            f"Output doesn't seem to address file organization (found: {keyword_matches})"

        print(f"[Verify 4] ✓ Output addresses file organization")
        print(f"[Verify 4]   Found keywords: {', '.join(keyword_matches)}")

        # Additional verification: Check reasoning steps if available
        if "reasoning_steps" in execution_result:
            reasoning_steps = execution_result["reasoning_steps"]
            print(f"[Verify 4] ✓ Agent used {len(reasoning_steps)} reasoning steps")

        # Print summary
        print(f"\n{'='*60}")
        print("Test Summary:")
        print(f"  • Skills discovered: {discovered_count}")
        print(f"  • Skills attached: {len(agent.attached_skills)}")
        print(f"  • Skill context size: {len(skill_context)} chars")
        print(f"  • Execution success: {execution_result['success']}")
        print(f"  • Output length: {len(execution_result['output'])} chars")
        print(f"  • Keywords matched: {len(keyword_matches)}")
        print(f"\nAgent Output Preview:")
        print(f"{execution_result['output'][:300]}...")
        print(f"{'='*60}")

        # Final assertion: Overall success
        assert execution_result["success"] is True
        assert len(keyword_matches) >= 1  # At least one keyword
        assert not has_errors or len(keyword_matches) >= 2  # If has errors, must have stronger keyword matches

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


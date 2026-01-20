"""
Unit tests for SkillCapableMixin.

Tests cover:
- Skill attachment and detachment
- Direct call strategy (native + subprocess)
- Tool registration strategy (opt-in)
- Context injection strategy (default)
- Mode selection (AUTO, NATIVE, SUBPROCESS)
- Async script execution
- Tool naming conflicts
- Detach cleanup
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional

from aiecs.domain.agent.skills.mixin import SkillCapableMixin
from aiecs.domain.agent.skills.models import SkillDefinition, SkillMetadata, SkillResource
from aiecs.domain.agent.skills.executor import ExecutionMode, ScriptExecutionResult, SkillScriptExecutor
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.domain.agent.skills.context import SkillContext
from aiecs.domain.agent.tools.models import Tool
from aiecs.domain.agent.tools.registry import SkillScriptRegistry


class MockSkillCapableAgent(SkillCapableMixin):
    """Mock agent class for testing the mixin."""

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional[SkillScriptRegistry] = None,
        script_executor: Optional[SkillScriptExecutor] = None,
    ):
        # Initialize mixin state
        self.__init_skills__(
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            script_executor=script_executor,
        )
        # Track tools added via _add_tool for testing
        self._agent_tools: Dict[str, Tool] = {}

    def _has_tool(self, tool_name: str) -> bool:
        """Check if tool exists in agent or skill tools."""
        return tool_name in self._skill_tools or tool_name in self._agent_tools

    def _add_tool(self, tool: Tool) -> None:
        """Add tool to agent's tool registry."""
        self._agent_tools[tool.name] = tool

    def _remove_tool(self, tool_name: str) -> None:
        """Remove tool from agent's tool registry."""
        if tool_name in self._agent_tools:
            del self._agent_tools[tool_name]


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill for unit testing",
        version="1.0.0",
        tags=["test", "sample"],
        recommended_tools=["tool1", "tool2"]
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/test-skill"),
        scripts={
            "validate": SkillResource(
                path="scripts/validate.py",
                type="script",
                executable=True,
                mode="native",
                description="Validate input data",
                parameters={
                    "code": {"type": "string", "required": True, "description": "Code to validate"},
                    "strict": {"type": "boolean", "required": False}
                }
            ),
            "run-tests": SkillResource(
                path="scripts/run_tests.py",
                type="script",
                executable=True,
                mode="subprocess",
                description="Run test suite"
            )
        }
    )


@pytest.fixture
def skill_without_metadata():
    """Create a skill with scripts but no metadata on scripts."""
    metadata = SkillMetadata(
        name="simple-skill",
        description="A simple skill",
        version="1.0.0"
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/path/to/simple-skill"),
        scripts={
            "process": SkillResource(
                path="scripts/process.py",
                type="script",
                executable=True
            )
        }
    )


@pytest.fixture
def mock_registry():
    """Create a mock skill registry."""
    registry = MagicMock(spec=SkillRegistry)
    return registry


@pytest.fixture
def mock_tool_registry():
    """Create a mock tool registry."""
    registry = MagicMock(spec=SkillScriptRegistry)
    registry.has_tool = MagicMock(return_value=False)
    registry.get_tool = MagicMock(return_value=None)
    return registry


@pytest.fixture
def mock_executor():
    """Create a mock script executor."""
    executor = MagicMock(spec=SkillScriptExecutor)
    executor.execute = AsyncMock(return_value=ScriptExecutionResult(
        success=True,
        result={"test": "result"},
        execution_time=0.1,
        mode_used=ExecutionMode.NATIVE
    ))
    return executor


@pytest.fixture
def agent(mock_executor):
    """Create a mock agent with the mixin."""
    return MockSkillCapableAgent(script_executor=mock_executor)


@pytest.fixture
def agent_with_registry(mock_registry, mock_executor):
    """Create an agent with a skill registry."""
    return MockSkillCapableAgent(
        skill_registry=mock_registry,
        script_executor=mock_executor
    )


# ==============================================================================
# Basic Skill Attachment Tests
# ==============================================================================

class TestSkillAttachment:
    """Tests for skill attachment and detachment."""

    def test_attach_skill_instances(self, agent, sample_skill):
        """Test attaching skill instances directly."""
        result = agent.attach_skill_instances([sample_skill])

        assert result == ["test-skill"]
        assert agent.has_skill("test-skill")
        assert len(agent.attached_skills) == 1
        assert agent.skill_names == ["test-skill"]

    def test_attach_multiple_skills(self, agent, sample_skill, skill_without_metadata):
        """Test attaching multiple skills."""
        result = agent.attach_skill_instances([sample_skill, skill_without_metadata])

        assert len(result) == 2
        assert "test-skill" in result
        assert "simple-skill" in result
        assert len(agent.attached_skills) == 2

    def test_attach_duplicate_skill_skipped(self, agent, sample_skill):
        """Test that duplicate skills are skipped."""
        agent.attach_skill_instances([sample_skill])
        result = agent.attach_skill_instances([sample_skill])

        assert result == []  # No new skills attached
        assert len(agent.attached_skills) == 1

    def test_attach_skills_by_name_requires_registry(self, agent):
        """Test that attach_skills requires a registry."""
        with pytest.raises(ValueError, match="Skill registry not configured"):
            agent.attach_skills(["test-skill"])

    def test_attach_skills_by_name(self, agent_with_registry, sample_skill, mock_registry):
        """Test attaching skills by name from registry."""
        mock_registry.get_skills.return_value = [sample_skill]

        result = agent_with_registry.attach_skills(["test-skill"])

        assert result == ["test-skill"]
        mock_registry.get_skills.assert_called_once_with(["test-skill"])

    def test_attach_skills_empty_result(self, agent_with_registry, mock_registry):
        """Test attaching skills when none found in registry."""
        mock_registry.get_skills.return_value = []

        result = agent_with_registry.attach_skills(["nonexistent"])

        assert result == []

    def test_detach_skills(self, agent, sample_skill):
        """Test detaching skills."""
        agent.attach_skill_instances([sample_skill])
        assert agent.has_skill("test-skill")

        agent.detach_skills(["test-skill"])

        assert not agent.has_skill("test-skill")
        assert len(agent.attached_skills) == 0

    def test_detach_nonexistent_skill(self, agent):
        """Test detaching a skill that doesn't exist."""
        # Should not raise an error
        agent.detach_skills(["nonexistent"])

    def test_get_attached_skill(self, agent, sample_skill):
        """Test getting a skill by name."""
        agent.attach_skill_instances([sample_skill])

        skill = agent.get_attached_skill("test-skill")

        assert skill is not None
        assert skill.metadata.name == "test-skill"

    def test_get_attached_skill_not_found(self, agent):
        """Test getting a skill that doesn't exist."""
        skill = agent.get_attached_skill("nonexistent")
        assert skill is None


# ==============================================================================
# Tool Registration Tests (Phase 4.1.3)
# ==============================================================================

class TestToolRegistration:
    """Tests for tool registration strategy."""

    def test_auto_register_tools_false_by_default(self, agent, sample_skill):
        """Test that tools are not registered by default."""
        agent.attach_skill_instances([sample_skill])

        # No tools should be registered
        assert len(agent._skill_tools) == 0
        assert len(agent._agent_tools) == 0

    def test_auto_register_tools_true(self, agent, sample_skill):
        """Test that tools are registered when auto_register_tools=True."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        # Tools should be registered
        assert len(agent._skill_tools) == 2
        assert "test-skill_validate" in agent._skill_tools
        assert "test-skill_run-tests" in agent._skill_tools

        # Tools should also be in agent tools
        assert "test-skill_validate" in agent._agent_tools
        assert "test-skill_run-tests" in agent._agent_tools

    def test_tool_naming_convention(self, agent, sample_skill):
        """Test that tool names follow skill_script convention."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        for tool_name in agent._skill_tools:
            assert tool_name.startswith("test-skill_")

    def test_tool_description_from_metadata(self, agent, sample_skill):
        """Test that tool description comes from script metadata."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        assert validate_tool.description == "Validate input data"

    def test_tool_description_fallback(self, agent, skill_without_metadata):
        """Test fallback description when metadata is missing."""
        agent.attach_skill_instances([skill_without_metadata], auto_register_tools=True)

        process_tool = agent._skill_tools["simple-skill_process"]
        assert "process" in process_tool.description
        assert "simple-skill" in process_tool.description

    def test_tool_parameters_from_metadata(self, agent, sample_skill):
        """Test that tool parameters come from script metadata."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        params = validate_tool.parameters

        assert params["type"] == "object"
        assert "code" in params["properties"]
        assert params["properties"]["code"]["type"] == "string"
        assert "code" in params["required"]

    def test_tool_parameters_fallback(self, agent, skill_without_metadata):
        """Test fallback parameters when metadata is missing."""
        agent.attach_skill_instances([skill_without_metadata], auto_register_tools=True)

        process_tool = agent._skill_tools["simple-skill_process"]
        params = process_tool.parameters

        assert params["type"] == "object"
        assert "input_data" in params["properties"]

    def test_tool_source_tracking(self, agent, sample_skill):
        """Test that tools track their source skill."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        assert validate_tool.source == "test-skill"

    def test_tool_naming_conflict_raises_error(self, agent, sample_skill):
        """Test that tool naming conflicts raise an error."""
        # First attachment should succeed
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        # Create a duplicate skill with same name
        duplicate_skill = SkillDefinition(
            metadata=SkillMetadata(
                name="test-skill",  # Same name
                description="Duplicate",
                version="2.0.0"
            ),
            skill_path=Path("/path/to/duplicate"),
            scripts={
                "validate": SkillResource(
                    path="scripts/validate.py",
                    type="script",
                    executable=True
                )
            }
        )

        # Detach first, then try to attach duplicate
        agent.detach_skills(["test-skill"])

        # Now attach a skill that would conflict with existing agent tool
        agent._agent_tools["conflict_script"] = MagicMock()

        conflict_skill = SkillDefinition(
            metadata=SkillMetadata(
                name="conflict",
                description="Conflict skill",
                version="1.0.0"
            ),
            skill_path=Path("/path/to/conflict"),
            scripts={
                "script": SkillResource(
                    path="scripts/script.py",
                    type="script",
                    executable=True
                )
            }
        )

        with pytest.raises(ValueError, match="already exists"):
            agent.attach_skill_instances([conflict_skill], auto_register_tools=True)

    def test_cleanup_skill_tools_on_detach(self, agent, sample_skill):
        """Test that tools are cleaned up when skill is detached."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        assert len(agent._skill_tools) == 2
        assert len(agent._agent_tools) == 2

        agent.detach_skills(["test-skill"])

        assert len(agent._skill_tools) == 0
        assert len(agent._agent_tools) == 0



# ==============================================================================
# Script Execution Tests
# ==============================================================================

class TestScriptExecution:
    """Tests for direct script execution API."""

    @pytest.mark.asyncio
    async def test_execute_skill_script_success(self, agent, sample_skill, mock_executor):
        """Test successful script execution."""
        agent.attach_skill_instances([sample_skill])

        result = await agent.execute_skill_script(
            skill_name="test-skill",
            script_name="validate",
            input_data={"code": "print('hello')"}
        )

        assert result.success is True
        assert result.result == {"test": "result"}
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_skill_script_not_attached(self, agent):
        """Test execution fails for non-attached skill."""
        with pytest.raises(ValueError, match="not attached"):
            await agent.execute_skill_script(
                skill_name="nonexistent",
                script_name="validate",
                input_data={}
            )

    @pytest.mark.asyncio
    async def test_execute_skill_script_not_found(self, agent, sample_skill):
        """Test execution fails for non-existent script."""
        agent.attach_skill_instances([sample_skill])

        with pytest.raises(ValueError, match="not found"):
            await agent.execute_skill_script(
                skill_name="test-skill",
                script_name="nonexistent",
                input_data={}
            )

    @pytest.mark.asyncio
    async def test_execute_skill_script_with_mode(self, agent, sample_skill, mock_executor):
        """Test script execution with explicit mode."""
        agent.attach_skill_instances([sample_skill])

        await agent.execute_skill_script(
            skill_name="test-skill",
            script_name="validate",
            input_data={},
            mode=ExecutionMode.SUBPROCESS
        )

        # Verify mode was passed to executor
        call_args = mock_executor.execute.call_args
        assert call_args.kwargs.get("mode") == ExecutionMode.SUBPROCESS

    @pytest.mark.asyncio
    async def test_execute_skill_script_with_timeout(self, agent, sample_skill, mock_executor):
        """Test script execution with custom timeout."""
        agent.attach_skill_instances([sample_skill])

        await agent.execute_skill_script(
            skill_name="test-skill",
            script_name="validate",
            input_data={},
            timeout=60.0
        )

        # Verify timeout was passed to executor
        call_args = mock_executor.execute.call_args
        assert call_args.kwargs.get("timeout") == 60.0


# ==============================================================================
# Mode Resolution Tests
# ==============================================================================

class TestModeResolution:
    """Tests for execution mode resolution."""

    def test_resolve_mode_auto_uses_script_metadata(self, agent, sample_skill):
        """Test AUTO mode uses script metadata when available."""
        agent.attach_skill_instances([sample_skill])

        # validate script has mode="native" in metadata
        validate_script = sample_skill.scripts["validate"]
        mode = agent._resolve_execution_mode(ExecutionMode.AUTO, validate_script)

        assert mode == ExecutionMode.NATIVE

    def test_resolve_mode_explicit_overrides_metadata(self, agent, sample_skill):
        """Test explicit mode overrides script metadata."""
        agent.attach_skill_instances([sample_skill])

        validate_script = sample_skill.scripts["validate"]
        mode = agent._resolve_execution_mode(ExecutionMode.SUBPROCESS, validate_script)

        assert mode == ExecutionMode.SUBPROCESS

    def test_resolve_mode_auto_defaults_to_auto(self, agent, skill_without_metadata):
        """Test AUTO mode stays AUTO when no metadata."""
        agent.attach_skill_instances([skill_without_metadata])

        process_script = skill_without_metadata.scripts["process"]
        mode = agent._resolve_execution_mode(ExecutionMode.AUTO, process_script)

        # Should remain AUTO for executor to decide
        assert mode == ExecutionMode.AUTO


# ==============================================================================
# Tool Executor Tests
# ==============================================================================

class TestToolExecutor:
    """Tests for tool executor creation."""

    @pytest.mark.asyncio
    async def test_tool_executor_calls_script_executor(self, agent, sample_skill, mock_executor):
        """Test that tool executor properly calls script executor."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        executor_fn = validate_tool.execute

        # Call the executor
        result = await executor_fn({"code": "test"})

        assert result["success"] is True
        assert result["result"] == {"test": "result"}
        mock_executor.execute.assert_called()

    @pytest.mark.asyncio
    async def test_tool_executor_returns_structured_result(self, agent, sample_skill, mock_executor):
        """Test that tool executor returns structured result."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        result = await validate_tool.execute({})

        assert "success" in result
        assert "result" in result
        assert "error" in result
        assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_tool_executor_handles_error(self, agent, sample_skill, mock_executor):
        """Test that tool executor handles execution errors."""
        mock_executor.execute.return_value = ScriptExecutionResult(
            success=False,
            result=None,
            error="Script failed",
            execution_time=0.1,
            mode_used=ExecutionMode.NATIVE
        )

        agent.attach_skill_instances([sample_skill], auto_register_tools=True)

        validate_tool = agent._skill_tools["test-skill_validate"]
        result = await validate_tool.execute({})

        assert result["success"] is False
        assert result["error"] == "Script failed"


# ==============================================================================
# Context Injection Tests
# ==============================================================================

class TestContextInjection:
    """Tests for context injection configuration."""

    def test_inject_script_paths_default_true(self, agent, sample_skill):
        """Test that inject_script_paths defaults to True."""
        agent.attach_skill_instances([sample_skill])

        config = agent._skill_injection_config.get("test-skill")
        assert config is not None
        assert config["inject_script_paths"] is True

    def test_inject_script_paths_false(self, agent, sample_skill):
        """Test setting inject_script_paths to False."""
        agent.attach_skill_instances([sample_skill], inject_script_paths=False)

        config = agent._skill_injection_config.get("test-skill")
        assert config["inject_script_paths"] is False

    def test_skill_context_updated_on_attach(self, agent, sample_skill):
        """Test that skill context is updated when skill is attached."""
        agent.attach_skill_instances([sample_skill])

        # Skill should be in context
        skills = agent._skill_context.get_skills()
        assert len(skills) == 1
        assert skills[0].metadata.name == "test-skill"

    def test_skill_context_cleared_on_detach(self, agent, sample_skill):
        """Test that skill context is cleared when skill is detached."""
        agent.attach_skill_instances([sample_skill])
        agent.detach_skills(["test-skill"])

        # Skill should be removed from context
        skills = agent._skill_context.get_skills()
        assert len(skills) == 0


# ==============================================================================
# get_skill_context() Tests (Phase 4.1.4)
# ==============================================================================

class TestGetSkillContext:
    """Tests for get_skill_context() method."""

    def test_get_skill_context_empty_when_no_skills(self, agent):
        """Test that context is empty when no skills attached."""
        context = agent.get_skill_context()
        assert context == ""

    def test_get_skill_context_includes_skill_header(self, agent, sample_skill):
        """Test that context includes skill header."""
        agent.attach_skill_instances([sample_skill])
        context = agent.get_skill_context()

        assert "## Skill: test-skill" in context
        assert "A test skill for unit testing" in context

    def test_get_skill_context_includes_body(self, agent):
        """Test that context includes skill body."""
        skill = SkillDefinition(
            metadata=SkillMetadata(
                name="body-skill",
                description="Skill with body",
                version="1.0.0"
            ),
            skill_path=Path("/path/to/skill"),
            body="This is the skill body content."
        )
        agent.attach_skill_instances([skill])
        context = agent.get_skill_context()

        assert "This is the skill body content." in context

    def test_get_skill_context_includes_scripts_by_default(self, agent, sample_skill):
        """Test that context includes scripts section by default."""
        agent.attach_skill_instances([sample_skill])
        context = agent.get_skill_context()

        assert "### Available Scripts" in context
        assert "validate" in context
        assert "run-tests" in context

    def test_get_skill_context_excludes_scripts_when_disabled(self, agent, sample_skill):
        """Test that scripts are excluded when inject_script_paths=False."""
        agent.attach_skill_instances([sample_skill], inject_script_paths=False)
        context = agent.get_skill_context()

        assert "### Available Scripts" not in context
        # But skill header should still be present
        assert "## Skill: test-skill" in context

    def test_get_skill_context_includes_recommended_tools(self, agent, sample_skill):
        """Test that context includes recommended tools."""
        agent.attach_skill_instances([sample_skill])
        context = agent.get_skill_context()

        assert "### Recommended Tools" in context
        assert "tool1" in context
        assert "tool2" in context

    def test_get_skill_context_includes_tools_even_when_scripts_disabled(self, agent, sample_skill):
        """Test that tools are included even when scripts are disabled."""
        agent.attach_skill_instances([sample_skill], inject_script_paths=False)
        context = agent.get_skill_context()

        # Scripts should be excluded
        assert "### Available Scripts" not in context
        # But tools should still be included
        assert "### Recommended Tools" in context
        assert "tool1" in context

    def test_get_skill_context_multiple_skills(self, agent, sample_skill, skill_without_metadata):
        """Test context with multiple skills."""
        agent.attach_skill_instances([sample_skill, skill_without_metadata])
        context = agent.get_skill_context()

        assert "## Skill: test-skill" in context
        assert "## Skill: simple-skill" in context
        assert "---" in context  # Separator between skills


# ==============================================================================
# get_recommended_tools() Tests (Phase 4.1.4)
# ==============================================================================

class TestGetRecommendedTools:
    """Tests for get_recommended_tools() method."""

    def test_get_recommended_tools_empty_when_no_skills(self, agent):
        """Test that no tools recommended when no skills attached."""
        tools = agent.get_recommended_tools()
        assert tools == []

    def test_get_recommended_tools_from_skill(self, agent, sample_skill):
        """Test that tools are recommended from attached skill."""
        agent.attach_skill_instances([sample_skill])
        tools = agent.get_recommended_tools()

        assert "tool1" in tools
        assert "tool2" in tools

    def test_get_recommended_tools_unique(self, agent):
        """Test that recommended tools are unique."""
        # Create two skills with overlapping tools
        skill1 = SkillDefinition(
            metadata=SkillMetadata(
                name="skill1",
                description="First skill",
                version="1.0.0",
                recommended_tools=["tool1", "tool2"]
            ),
            skill_path=Path("/path/to/skill1")
        )
        skill2 = SkillDefinition(
            metadata=SkillMetadata(
                name="skill2",
                description="Second skill",
                version="1.0.0",
                recommended_tools=["tool2", "tool3"]
            ),
            skill_path=Path("/path/to/skill2")
        )
        agent.attach_skill_instances([skill1, skill2])
        tools = agent.get_recommended_tools()

        # tool2 should only appear once
        assert tools.count("tool2") == 1
        assert len(tools) == 3
        assert "tool1" in tools
        assert "tool2" in tools
        assert "tool3" in tools

    def test_get_recommended_tools_preserves_order(self, agent, sample_skill):
        """Test that tool order is preserved."""
        agent.attach_skill_instances([sample_skill])
        tools = agent.get_recommended_tools()

        # tool1 should come before tool2
        assert tools.index("tool1") < tools.index("tool2")

    def test_get_recommended_tools_filters_by_availability(self, agent, sample_skill):
        """Test that tools can be filtered by availability."""
        agent.attach_skill_instances([sample_skill])

        # Only tool1 is available
        tools = agent.get_recommended_tools(available_tools=["tool1", "other_tool"])

        assert tools == ["tool1"]
        assert "tool2" not in tools


# ==============================================================================
# list_skill_tools() Tests (Phase 4.1.4)
# ==============================================================================

class TestListSkillTools:
    """Tests for list_skill_tools() method."""

    def test_list_skill_tools_empty_when_no_registration(self, agent, sample_skill):
        """Test that no tools listed when auto_register_tools=False."""
        agent.attach_skill_instances([sample_skill])  # Default: no registration
        tools = agent.list_skill_tools()

        assert tools == {}

    def test_list_skill_tools_with_registration(self, agent, sample_skill):
        """Test that tools are listed when auto_register_tools=True."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)
        tools = agent.list_skill_tools()

        assert "test-skill_validate" in tools
        assert "test-skill_run-tests" in tools

    def test_list_skill_tools_returns_copy(self, agent, sample_skill):
        """Test that list_skill_tools returns a copy."""
        agent.attach_skill_instances([sample_skill], auto_register_tools=True)
        tools = agent.list_skill_tools()

        # Modify returned dict
        tools["fake_tool"] = None

        # Original should be unchanged
        assert "fake_tool" not in agent._skill_tools


# ==============================================================================
# load_skill_resource() Tests (Phase 4.1.4)
# ==============================================================================

class TestLoadSkillResource:
    """Tests for load_skill_resource() method."""

    @pytest.mark.asyncio
    async def test_load_skill_resource_not_attached(self, agent):
        """Test loading resource from non-attached skill raises error."""
        with pytest.raises(ValueError, match="not attached"):
            await agent.load_skill_resource("nonexistent", "file.txt")

    @pytest.mark.asyncio
    async def test_load_skill_resource_not_found(self, agent, sample_skill):
        """Test loading non-existent resource raises error."""
        agent.attach_skill_instances([sample_skill])

        with pytest.raises(ValueError, match="not found"):
            await agent.load_skill_resource("test-skill", "nonexistent.txt")

    @pytest.mark.asyncio
    async def test_load_skill_resource_from_scripts(self, agent, tmp_path):
        """Test loading a script resource."""
        # Create a real skill with a real file
        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        script_file = scripts_dir / "validate.py"
        script_file.write_text("# Test script content")

        skill = SkillDefinition(
            metadata=SkillMetadata(
                name="test-skill",
                description="Test",
                version="1.0.0"
            ),
            skill_path=skill_path,
            scripts={
                "validate": SkillResource(
                    path="scripts/validate.py",
                    type="script",
                    executable=True
                )
            }
        )
        agent.attach_skill_instances([skill])

        content = await agent.load_skill_resource("test-skill", "scripts/validate.py")
        assert content == "# Test script content"

    @pytest.mark.asyncio
    async def test_load_skill_resource_caches_content(self, agent, tmp_path):
        """Test that loaded content is cached in the resource."""
        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()
        refs_dir = skill_path / "references"
        refs_dir.mkdir()
        ref_file = refs_dir / "guide.md"
        ref_file.write_text("# Guide content")

        resource = SkillResource(
            path="references/guide.md",
            type="reference"
        )
        skill = SkillDefinition(
            metadata=SkillMetadata(
                name="test-skill",
                description="Test",
                version="1.0.0"
            ),
            skill_path=skill_path,
            references={"guide": resource}
        )
        agent.attach_skill_instances([skill])

        # First load
        await agent.load_skill_resource("test-skill", "references/guide.md")

        # Content should be cached
        assert resource.content == "# Guide content"



# ==============================================================================
# _load_recommended_tools() Tests (Phase 4.1.4)
# ==============================================================================

class TestLoadRecommendedTools:
    """Tests for _load_recommended_tools() method."""

    def test_load_recommended_tools_skips_without_registry(self, agent, sample_skill):
        """Test that loading is skipped when no tool registry."""
        # Agent has no tool registry
        assert agent._tool_registry is None

        # This should not raise
        agent._load_recommended_tools(sample_skill)

        # No tools should be added
        assert len(agent._agent_tools) == 0

    def test_load_recommended_tools_with_registry(self, mock_tool_registry, mock_executor, sample_skill):
        """Test loading tools from registry."""
        agent = MockSkillCapableAgent(
            tool_registry=mock_tool_registry,
            script_executor=mock_executor
        )

        # Set up mock to return a tool
        mock_tool = MagicMock()
        mock_tool.name = "tool1"
        mock_tool_registry.has_tool.return_value = True
        mock_tool_registry.get_tool.return_value = mock_tool

        agent._load_recommended_tools(sample_skill)

        # Tool should be added
        mock_tool_registry.get_tool.assert_called()

    def test_load_recommended_tools_skips_existing(self, mock_tool_registry, mock_executor, sample_skill):
        """Test that existing tools are not re-loaded."""
        agent = MockSkillCapableAgent(
            tool_registry=mock_tool_registry,
            script_executor=mock_executor
        )

        # Pre-add a tool
        agent._skill_tools["tool1"] = MagicMock()

        mock_tool_registry.has_tool.return_value = True
        mock_tool_registry.get_tool.return_value = MagicMock()

        agent._load_recommended_tools(sample_skill)

        # Should not try to get tool1 since it's already present
        # (The implementation checks _has_tool which checks _skill_tools)


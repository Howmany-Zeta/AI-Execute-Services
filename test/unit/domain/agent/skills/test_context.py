"""
Unit tests for SkillContext.

Tests context building, resource listing, script availability,
tool recommendations, and progressive disclosure.
"""

from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from aiecs.domain.agent.skills.context import (
    ContextOptions,
    SkillContext,
    SkillContextError,
    SkillContextResult,
)
from aiecs.domain.agent.skills.models import (
    SkillDefinition,
    SkillMetadata,
    SkillResource,
)


# Fixtures for test skills
@pytest.fixture
def python_testing_skill() -> SkillDefinition:
    """Create a Python testing skill for tests."""
    metadata = SkillMetadata(
        name="python-testing",
        description='Use this skill when the user asks to "write tests" or "create unit tests".',
        version="1.0.0",
        author="Test Author",
        tags=["python", "testing", "pytest"],
        recommended_tools=["pytest_runner", "coverage_reporter"],
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/skills/python-testing"),
        body="# Python Testing\n\nThis skill provides guidance for writing Python tests.",
        scripts={
            "run_tests": SkillResource(
                path="scripts/run_tests.py",
                type="script",
                mode="subprocess",
                description="Run pytest on specified files",
                parameters={"files": {"type": "list", "required": True}},
            ),
            "validate_syntax": SkillResource(
                path="scripts/validate_syntax.py",
                type="script",
                mode="native",
                description="Validate Python syntax",
            ),
        },
        references={
            "pytest_guide": SkillResource(
                path="references/pytest_guide.md",
                type="reference",
            ),
        },
        examples={
            "test_example": SkillResource(
                path="examples/test_example.py",
                type="example",
            ),
        },
    )


@pytest.fixture
def code_review_skill() -> SkillDefinition:
    """Create a code review skill for tests."""
    metadata = SkillMetadata(
        name="code-review",
        description='Use this skill when the user asks to "review code" or "check quality".',
        version="1.0.0",
        tags=["review", "quality"],
        recommended_tools=["code_analyzer", "linter"],
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/skills/code-review"),
        body="# Code Review\n\nThis skill provides guidance for code reviews.",
    )


@pytest.fixture
def minimal_skill() -> SkillDefinition:
    """Create a minimal skill without optional fields."""
    metadata = SkillMetadata(
        name="minimal-skill",
        description="A minimal skill for testing.",
        version="0.1.0",
    )
    return SkillDefinition(
        metadata=metadata,
        skill_path=Path("/skills/minimal"),
    )


class TestSkillContextInit:
    """Tests for SkillContext initialization."""

    def test_init_empty(self):
        """Test initialization with no skills."""
        context = SkillContext()
        assert context.get_skills() == []

    def test_init_with_skills(self, python_testing_skill):
        """Test initialization with skills."""
        context = SkillContext(skills=[python_testing_skill])
        assert len(context.get_skills()) == 1
        assert context.get_skills()[0].metadata.name == "python-testing"

    def test_set_skills(self, python_testing_skill, code_review_skill):
        """Test setting skills."""
        context = SkillContext()
        context.set_skills([python_testing_skill, code_review_skill])
        assert len(context.get_skills()) == 2

    def test_add_skill(self, python_testing_skill):
        """Test adding a skill."""
        context = SkillContext()
        context.add_skill(python_testing_skill)
        assert len(context.get_skills()) == 1

    def test_clear_skills(self, python_testing_skill):
        """Test clearing skills."""
        context = SkillContext(skills=[python_testing_skill])
        context.clear_skills()
        assert context.get_skills() == []


class TestBuildContext:
    """Tests for context building."""

    def test_build_context_empty(self):
        """Test building context with no skills."""
        context = SkillContext()
        result = context.build_context()
        assert result == ""

    def test_build_context_single_skill(self, python_testing_skill):
        """Test building context with a single skill."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "## Skill: python-testing" in result
        assert "write tests" in result

    def test_build_context_includes_resources(self, python_testing_skill):
        """Test that context includes resource information."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "### Available Resources" in result
        assert "references/pytest_guide.md" in result
        assert "examples/test_example.py" in result

    def test_build_context_includes_tool_recommendations(self, python_testing_skill):
        """Test that context includes tool recommendations."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "### Recommended Tools" in result
        assert "pytest_runner" in result
        assert "coverage_reporter" in result

    def test_build_context_without_body(self, python_testing_skill):
        """Test building context without body content."""
        context = SkillContext(skills=[python_testing_skill])
        options = ContextOptions(include_body=False)
        result = context.build_context(options=options)

        assert "## Skill: python-testing" in result
        assert "# Python Testing" not in result

    def test_build_context_without_scripts(self, python_testing_skill):
        """Test building context without scripts."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context(include_scripts=False)

        assert "### Available Scripts" not in result

    def test_build_context_max_body_length(self, python_testing_skill):
        """Test truncating body content."""
        context = SkillContext(skills=[python_testing_skill])
        options = ContextOptions(max_body_length=20)
        result = context.build_context(options=options)

        assert "...(truncated)" in result

    def test_build_context_minimal_skill(self, minimal_skill):
        """Test building context for minimal skill."""
        context = SkillContext(skills=[minimal_skill])
        result = context.build_context()

        assert "## Skill: minimal-skill" in result
        assert "### Available Scripts" not in result
        assert "### Available Resources" not in result
        assert "### Recommended Tools" not in result


class TestScriptFormatting:
    """Tests for script information formatting."""

    def test_script_metadata_included(self, python_testing_skill):
        """Test that script metadata is included."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        # Check script name and path
        assert "run_tests" in result
        assert "scripts/run_tests.py" in result

        # Check mode
        assert "subprocess" in result

        # Check description
        assert "Run pytest on specified files" in result

    def test_script_parameters_included(self, python_testing_skill):
        """Test that script parameters are included."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "Parameters:" in result
        assert "files" in result
        assert "required" in result.lower()


class TestResourcePaths:
    """Tests for resource path listing."""

    def test_get_resource_paths_empty(self):
        """Test getting resource paths with no skills."""
        context = SkillContext()
        result = context.get_resource_paths()
        assert result == {}

    def test_get_resource_paths(self, python_testing_skill):
        """Test getting resource paths."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.get_resource_paths()

        assert "python-testing" in result
        paths = result["python-testing"]
        assert "references/pytest_guide.md" in paths["references"]
        assert "examples/test_example.py" in paths["examples"]
        assert "scripts/run_tests.py" in paths["scripts"]
        assert "scripts/validate_syntax.py" in paths["scripts"]


class TestScriptInfo:
    """Tests for script information retrieval."""

    def test_get_script_info_empty(self):
        """Test getting script info with no skills."""
        context = SkillContext()
        result = context.get_script_info()
        assert result == {}

    def test_get_script_info(self, python_testing_skill):
        """Test getting script info."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.get_script_info()

        assert "python-testing" in result
        scripts = result["python-testing"]
        assert "run_tests" in scripts
        assert scripts["run_tests"]["path"] == "scripts/run_tests.py"
        assert scripts["run_tests"]["mode"] == "subprocess"
        assert scripts["run_tests"]["description"] == "Run pytest on specified files"
        assert scripts["run_tests"]["parameters"] == {"files": {"type": "list", "required": True}}

    def test_get_script_info_minimal_skill(self, minimal_skill):
        """Test getting script info for skill without scripts."""
        context = SkillContext(skills=[minimal_skill])
        result = context.get_script_info()
        assert result == {}


class TestToolRecommendations:
    """Tests for tool recommendation logic."""

    def test_get_recommended_tools_empty(self):
        """Test getting recommendations with no skills."""
        context = SkillContext()
        result = context.get_recommended_tools("write tests")
        assert result == []

    def test_get_recommended_tools_basic(self, python_testing_skill):
        """Test getting recommendations from a skill."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.get_recommended_tools("write tests")

        assert "pytest_runner" in result
        assert "coverage_reporter" in result

    def test_get_recommended_tools_filter_available(self, python_testing_skill):
        """Test filtering recommendations by available tools."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.get_recommended_tools(
            "write tests",
            available_tools=["pytest_runner", "other_tool"]
        )

        assert "pytest_runner" in result
        assert "coverage_reporter" not in result

    def test_get_recommended_tools_uniqueness(self, python_testing_skill, code_review_skill):
        """Test that recommendations are unique."""
        # Add same tool to both skills
        code_review_skill.metadata.recommended_tools.append("pytest_runner")

        context = SkillContext(skills=[python_testing_skill, code_review_skill])
        result = context.get_recommended_tools("write tests")

        # Should only appear once
        assert result.count("pytest_runner") == 1

    def test_get_recommended_tools_order_preserved(self, python_testing_skill, code_review_skill):
        """Test that order is preserved."""
        context = SkillContext(skills=[python_testing_skill, code_review_skill])
        result = context.get_recommended_tools("write tests")

        # First skill's tools should come first
        pytest_idx = result.index("pytest_runner")
        code_analyzer_idx = result.index("code_analyzer")
        assert pytest_idx < code_analyzer_idx

    def test_get_recommended_tools_minimal_skill(self, minimal_skill):
        """Test getting recommendations from skill without tools."""
        context = SkillContext(skills=[minimal_skill])
        result = context.get_recommended_tools("do something")
        assert result == []


class TestFormatToolRecommendations:
    """Tests for tool recommendation formatting."""

    def test_format_empty(self):
        """Test formatting with no recommendations."""
        context = SkillContext()
        result = context.format_tool_recommendations("write tests")
        assert result == ""

    def test_format_basic(self, python_testing_skill):
        """Test basic formatting."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.format_tool_recommendations("write tests")

        assert "## Tool Recommendations" in result
        assert "pytest_runner" in result
        assert "coverage_reporter" in result

    def test_format_with_descriptions(self, python_testing_skill):
        """Test formatting with tool descriptions."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.format_tool_recommendations(
            "write tests",
            tool_descriptions={
                "pytest_runner": "Run pytest test suites",
                "coverage_reporter": "Generate coverage reports",
            }
        )

        assert "**pytest_runner**: Run pytest test suites" in result
        assert "**coverage_reporter**: Generate coverage reports" in result


class TestProgressiveDisclosure:
    """Tests for progressive disclosure logic."""

    def test_level1_metadata_only(self, python_testing_skill):
        """Test Level 1: metadata only."""
        # Remove body to simulate metadata-only loading
        python_testing_skill.body = None
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "## Skill: python-testing" in result
        assert "write tests" in result  # Description is included
        # Body content should not be present
        assert "# Python Testing" not in result

    def test_level2_with_body(self, python_testing_skill):
        """Test Level 2: metadata + body."""
        context = SkillContext(skills=[python_testing_skill])
        options = ContextOptions(include_resources=False)
        result = context.build_context(options=options)

        assert "## Skill: python-testing" in result
        assert "# Python Testing" in result

    def test_level3_with_resources(self, python_testing_skill):
        """Test Level 3: metadata + body + resources."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "## Skill: python-testing" in result
        assert "# Python Testing" in result
        assert "### Available Resources" in result


class TestMultipleSkills:
    """Tests for handling multiple skills."""

    def test_build_context_multiple_skills(self, python_testing_skill, code_review_skill):
        """Test building context with multiple skills."""
        context = SkillContext(skills=[python_testing_skill, code_review_skill])
        result = context.build_context()

        assert "## Skill: python-testing" in result
        assert "## Skill: code-review" in result
        assert "---" in result  # Separator between skills

    def test_build_context_includes_scripts(self, python_testing_skill):
        """Test that context includes script information."""
        context = SkillContext(skills=[python_testing_skill])
        result = context.build_context()

        assert "### Available Scripts" in result
        assert "run_tests" in result
        assert "scripts/run_tests.py" in result
        assert "subprocess" in result


class TestSkillMatching:
    """Tests for skill matching with SkillMatcher integration."""

    def test_get_recommended_tools_with_matcher(self, python_testing_skill, code_review_skill):
        """Test getting recommendations with SkillMatcher."""
        from aiecs.domain.agent.skills.matcher import SkillMatcher

        matcher = SkillMatcher()
        context = SkillContext(skills=[python_testing_skill, code_review_skill], matcher=matcher)

        # Request matches python-testing skill
        result = context.get_recommended_tools("write tests")

        # Should include tools from matching skill
        assert "pytest_runner" in result
        assert "coverage_reporter" in result

    def test_build_context_with_matcher_filters_skills(self, python_testing_skill, code_review_skill):
        """Test that build_context filters skills based on matcher."""
        from aiecs.domain.agent.skills.matcher import SkillMatcher

        matcher = SkillMatcher()
        context = SkillContext(skills=[python_testing_skill, code_review_skill], matcher=matcher)

        # Request should match python-testing skill better
        result = context.build_context(request="write unit tests")

        # Should include python-testing skill
        assert "python-testing" in result

    def test_get_recommended_tools_no_matcher_uses_all_skills(self, python_testing_skill, code_review_skill):
        """Test that without matcher, all skills are used."""
        context = SkillContext(skills=[python_testing_skill, code_review_skill])

        # Without matcher, should get tools from all skills
        result = context.get_recommended_tools("any request")

        assert "pytest_runner" in result
        assert "coverage_reporter" in result
        assert "code_analyzer" in result
        assert "linter" in result


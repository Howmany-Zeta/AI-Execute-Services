"""
Unit tests for SkillDiscovery.
"""

import pytest
import tempfile
import os
from pathlib import Path

from aiecs.domain.agent.skills.discovery import (
    SkillDiscovery,
    SkillDiscoveryError,
    SkillDiscoveryResult,
    SKILL_DIRECTORIES_ENV,
)
from aiecs.domain.agent.skills.registry import SkillRegistry
from aiecs.domain.agent.skills.loader import SkillLoader


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry before and after each test."""
    SkillRegistry.reset_instance()
    yield
    SkillRegistry.reset_instance()


@pytest.fixture
def skill_content():
    """Basic SKILL.md content for testing."""
    return """---
name: test-skill
description: A test skill for discovery
version: 1.0.0
tags:
  - test
---

# Test Skill

This is a test skill.
"""


@pytest.fixture
def temp_skills_dir(skill_content):
    """Create a temporary directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create skill-one
        skill_one = base / "skill-one"
        skill_one.mkdir()
        (skill_one / "SKILL.md").write_text(skill_content.replace("test-skill", "skill-one"))
        
        # Create skill-two
        skill_two = base / "skill-two"
        skill_two.mkdir()
        (skill_two / "SKILL.md").write_text(skill_content.replace("test-skill", "skill-two"))
        
        yield base


@pytest.fixture
def temp_skill_with_resources(skill_content):
    """Create a skill with resources."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "resource-skill"
        skill_path.mkdir()
        
        content = """---
name: resource-skill
description: A skill with resources
version: 1.0.0
scripts:
  validate:
    path: scripts/validate.py
    mode: native
---

# Resource Skill

This skill has resources.
"""
        (skill_path / "SKILL.md").write_text(content)
        
        # Create scripts directory
        scripts = skill_path / "scripts"
        scripts.mkdir()
        (scripts / "validate.py").write_text("""
def execute(input_data):
    return {"valid": True}
""")
        
        yield skill_path.parent


class TestSkillDiscoveryResult:
    """Tests for SkillDiscoveryResult."""
    
    def test_empty_result(self):
        """Test empty discovery result."""
        result = SkillDiscoveryResult()
        assert result.success_count == 0
        assert result.failure_count == 0
        assert result.skip_count == 0
    
    def test_result_repr(self):
        """Test result string representation."""
        result = SkillDiscoveryResult()
        assert "discovered=0" in repr(result)


class TestSkillDiscoveryInit:
    """Tests for SkillDiscovery initialization."""
    
    def test_default_init(self):
        """Test default initialization."""
        discovery = SkillDiscovery()
        assert discovery._loader is not None
        assert discovery._registry is not None
    
    def test_custom_loader(self):
        """Test initialization with custom loader."""
        loader = SkillLoader()
        discovery = SkillDiscovery(loader=loader)
        assert discovery._loader is loader
    
    def test_custom_directories(self, temp_skills_dir):
        """Test initialization with custom directories."""
        discovery = SkillDiscovery(directories=[temp_skills_dir])
        assert temp_skills_dir in discovery.get_directories()
    
    def test_set_directories(self, temp_skills_dir):
        """Test setting directories."""
        discovery = SkillDiscovery(directories=[])
        discovery.set_directories([temp_skills_dir])
        assert temp_skills_dir in discovery.get_directories()
    
    def test_add_directory(self, temp_skills_dir):
        """Test adding a directory."""
        discovery = SkillDiscovery(directories=[])
        discovery.add_directory(temp_skills_dir)
        assert temp_skills_dir in discovery.get_directories()


class TestSkillDiscovery:
    """Tests for skill discovery operations."""

    @pytest.mark.asyncio
    async def test_discover_skills(self, temp_skills_dir):
        """Test discovering skills from directory."""
        discovery = SkillDiscovery(directories=[temp_skills_dir])
        result = await discovery.discover()

        assert result.success_count == 2
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_discover_with_resources(self, temp_skill_with_resources):
        """Test discovering skills with resources."""
        discovery = SkillDiscovery(directories=[temp_skill_with_resources])
        result = await discovery.discover()

        assert result.success_count == 1
        skill = result.discovered[0]
        assert "validate" in skill.scripts

    @pytest.mark.asyncio
    async def test_auto_register_skills(self, temp_skills_dir):
        """Test that discovered skills are auto-registered."""
        registry = SkillRegistry.get_instance()
        discovery = SkillDiscovery(
            directories=[temp_skills_dir],
            auto_register=True
        )

        await discovery.discover()

        assert registry.has_skill("skill-one")
        assert registry.has_skill("skill-two")

    @pytest.mark.asyncio
    async def test_skip_registered_skills(self, temp_skills_dir):
        """Test skipping already registered skills."""
        # First discovery
        discovery = SkillDiscovery(
            directories=[temp_skills_dir],
            skip_registered=True
        )
        result1 = await discovery.discover()
        assert result1.success_count == 2

        # Second discovery should skip
        result2 = await discovery.discover()
        assert result2.success_count == 0
        assert result2.skip_count == 2

    @pytest.mark.asyncio
    async def test_no_auto_register(self, temp_skills_dir):
        """Test discovery without auto-registration."""
        registry = SkillRegistry.get_instance()
        discovery = SkillDiscovery(
            directories=[temp_skills_dir],
            auto_register=False
        )

        result = await discovery.discover()

        assert result.success_count == 2
        assert not registry.has_skill("skill-one")
        assert not registry.has_skill("skill-two")

    @pytest.mark.asyncio
    async def test_discover_empty_directory(self):
        """Test discovery with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            discovery = SkillDiscovery(directories=[Path(tmpdir)])
            result = await discovery.discover()

            assert result.success_count == 0
            assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_discover_nonexistent_directory(self):
        """Test discovery with nonexistent directory."""
        discovery = SkillDiscovery(directories=[Path("/nonexistent/path")])
        result = await discovery.discover()

        assert result.success_count == 0


class TestSkillDiscoveryError:
    """Tests for discovery error handling."""

    @pytest.mark.asyncio
    async def test_malformed_skill(self):
        """Test handling of malformed SKILL.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "bad-skill"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text("not valid yaml frontmatter")

            discovery = SkillDiscovery(directories=[Path(tmpdir)])
            result = await discovery.discover()

            assert result.success_count == 0
            assert result.failure_count == 1

    @pytest.mark.asyncio
    async def test_callback_on_failure(self):
        """Test failure callback is called."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "bad-skill"
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text("invalid")

            failures = []
            discovery = SkillDiscovery(directories=[Path(tmpdir)])
            discovery.on_failed(lambda path, err: failures.append((path, err)))

            await discovery.discover()

            assert len(failures) == 1

    @pytest.mark.asyncio
    async def test_callback_on_discovered(self, temp_skills_dir):
        """Test discovered callback is called."""
        discovered = []
        discovery = SkillDiscovery(directories=[temp_skills_dir])
        discovery.on_discovered(lambda skill: discovered.append(skill))

        await discovery.discover()

        assert len(discovered) == 2


class TestSingleSkillDiscovery:
    """Tests for single skill discovery."""

    @pytest.mark.asyncio
    async def test_discover_single(self, temp_skills_dir):
        """Test discovering a single skill."""
        discovery = SkillDiscovery(auto_register=True)
        skill_path = temp_skills_dir / "skill-one"

        skill = await discovery.discover_single(skill_path)

        assert skill.metadata.name == "skill-one"
        assert SkillRegistry.get_instance().has_skill("skill-one")

    @pytest.mark.asyncio
    async def test_discover_single_nonexistent(self):
        """Test discovering nonexistent skill raises error."""
        discovery = SkillDiscovery()

        with pytest.raises(SkillDiscoveryError):
            await discovery.discover_single(Path("/nonexistent"))


class TestRefresh:
    """Tests for refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_updates_skills(self, temp_skills_dir):
        """Test that refresh updates already-registered skills."""
        discovery = SkillDiscovery(
            directories=[temp_skills_dir],
            skip_registered=True
        )

        # Initial discovery
        result1 = await discovery.discover()
        assert result1.success_count == 2

        # Refresh should not skip
        result2 = await discovery.refresh()
        # Note: refresh will fail to re-register since they're already registered
        # but it won't skip them
        assert result2.skip_count == 0


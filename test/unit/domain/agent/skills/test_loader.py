"""
Unit tests for SkillLoader.
"""

import pytest
from pathlib import Path
import tempfile
import os

from aiecs.domain.agent.skills.loader import SkillLoader, SkillLoadError
from aiecs.domain.agent.skills.models import SkillDefinition, SkillResource


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_path = Path(tmpdir) / "test-skill"
        skill_path.mkdir()
        
        # Create SKILL.md
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
version: 1.0.0
author: Test Author
tags:
  - test
  - unit-testing
recommended_tools:
  - test-runner
  - linter
scripts:
  validate:
    path: scripts/validate.py
    mode: native
    description: Validate code syntax
    parameters:
      code:
        type: string
        required: true
  format:
    path: scripts/format.sh
    mode: subprocess
    description: Format code files
---

# Test Skill

This is a test skill for validating the SkillLoader implementation.

## Usage

Use this skill when testing the skill loading functionality.
""")
        
        # Create directories
        (skill_path / "scripts").mkdir()
        (skill_path / "references").mkdir()
        (skill_path / "examples").mkdir()
        (skill_path / "assets").mkdir()
        
        # Create script files
        validate_py = skill_path / "scripts" / "validate.py"
        validate_py.write_text("""
def execute(input_data):
    code = input_data.get('code', '')
    try:
        compile(code, '<string>', 'exec')
        return {"valid": True}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}
""")
        
        format_sh = skill_path / "scripts" / "format.sh"
        format_sh.write_text("#!/bin/bash\necho 'Formatting...'\n")
        os.chmod(format_sh, 0o755)
        
        # Create an auto-discovered script
        auto_script = skill_path / "scripts" / "auto_discovered.py"
        auto_script.write_text("def execute(data): return data\n")
        
        # Create reference files
        ref_file = skill_path / "references" / "guide.md"
        ref_file.write_text("# Reference Guide\n\nThis is a reference document.")
        
        # Create example files
        example_file = skill_path / "examples" / "sample.py"
        example_file.write_text("# Example code\nprint('Hello')\n")
        
        # Create asset files
        asset_file = skill_path / "assets" / "template.txt"
        asset_file.write_text("Template content here")
        
        yield skill_path


@pytest.fixture
def loader():
    """Create a SkillLoader instance."""
    return SkillLoader(cache_ttl=60)


class TestSkillLoader:
    """Tests for SkillLoader class."""

    @pytest.mark.asyncio
    async def test_load_skill_basic(self, loader, temp_skill_dir):
        """Test basic skill loading from SKILL.md."""
        skill = await loader.load_skill(temp_skill_dir)
        
        assert skill.metadata.name == "test-skill"
        assert skill.metadata.description == "A test skill for unit testing"
        assert skill.metadata.version == "1.0.0"
        assert skill.metadata.author == "Test Author"
        assert "test" in skill.metadata.tags
        assert "test-runner" in skill.metadata.recommended_tools

    @pytest.mark.asyncio
    async def test_load_skill_body(self, loader, temp_skill_dir):
        """Test skill body content loading."""
        skill = await loader.load_skill(temp_skill_dir, load_body=True)
        
        assert skill.body is not None
        assert "# Test Skill" in skill.body
        assert "validating the SkillLoader" in skill.body

    @pytest.mark.asyncio
    async def test_load_skill_without_body(self, loader, temp_skill_dir):
        """Test loading skill without body (metadata only)."""
        skill = await loader.load_skill(temp_skill_dir, load_body=False)

        assert skill.body is None
        assert skill.metadata.name == "test-skill"

    @pytest.mark.asyncio
    async def test_yaml_script_configuration(self, loader, temp_skill_dir):
        """Test parsing of script configuration from YAML frontmatter."""
        skill = await loader.load_skill(temp_skill_dir)

        # Check YAML-declared scripts
        assert "validate" in skill.scripts
        validate_script = skill.scripts["validate"]
        assert validate_script.path == "scripts/validate.py"
        assert validate_script.mode == "native"
        assert validate_script.description == "Validate code syntax"
        assert validate_script.parameters is not None
        assert validate_script.parameters["code"]["type"] == "string"
        assert validate_script.parameters["code"]["required"] is True

        assert "format" in skill.scripts
        format_script = skill.scripts["format"]
        assert format_script.path == "scripts/format.sh"
        assert format_script.mode == "subprocess"
        assert format_script.description == "Format code files"

    @pytest.mark.asyncio
    async def test_auto_discovered_scripts(self, loader, temp_skill_dir):
        """Test auto-discovery of scripts from scripts/ directory."""
        skill = await loader.load_skill(temp_skill_dir)

        # auto_discovered.py should be found
        assert "auto_discovered" in skill.scripts
        auto_script = skill.scripts["auto_discovered"]
        assert auto_script.path == "scripts/auto_discovered.py"
        assert auto_script.mode == "native"  # Default for .py
        assert auto_script.executable is True

    @pytest.mark.asyncio
    async def test_yaml_scripts_override_discovered(self, loader, temp_skill_dir):
        """Test that YAML-declared scripts take precedence over auto-discovered."""
        skill = await loader.load_skill(temp_skill_dir)

        # validate script should have YAML config, not auto-discovered defaults
        validate = skill.scripts["validate"]
        assert validate.description == "Validate code syntax"
        assert validate.parameters is not None

    @pytest.mark.asyncio
    async def test_resource_discovery(self, loader, temp_skill_dir):
        """Test discovery of references, examples, and assets."""
        skill = await loader.load_skill(temp_skill_dir)

        # References
        assert "guide" in skill.references
        ref = skill.references["guide"]
        assert ref.path == "references/guide.md"
        assert ref.type == "reference"
        assert ref.content is None  # Not loaded yet

        # Examples
        assert "sample" in skill.examples
        ex = skill.examples["sample"]
        assert ex.path == "examples/sample.py"
        assert ex.type == "example"

        # Assets
        assert "template" in skill.assets
        asset = skill.assets["template"]
        assert asset.path == "assets/template.txt"
        assert asset.type == "asset"

    @pytest.mark.asyncio
    async def test_load_resource_content(self, loader, temp_skill_dir):
        """Test lazy loading of resource content."""
        skill = await loader.load_skill(temp_skill_dir)

        # Load reference content
        content = await loader.load_resource(skill, "reference", "guide")

        assert content is not None
        assert "# Reference Guide" in content
        assert skill.references["guide"].content == content

    @pytest.mark.asyncio
    async def test_resource_caching(self, loader, temp_skill_dir):
        """Test that resource content is cached."""
        skill = await loader.load_skill(temp_skill_dir)

        # Load twice
        content1 = await loader.load_resource(skill, "reference", "guide")
        content2 = await loader.load_resource(skill, "reference", "guide")

        assert content1 == content2
        # Should be same object due to caching
        assert skill.references["guide"].content is content1

    @pytest.mark.asyncio
    async def test_load_body_on_demand(self, loader, temp_skill_dir):
        """Test loading body content on demand."""
        skill = await loader.load_skill(temp_skill_dir, load_body=False)

        assert skill.body is None

        # Load body
        body = await loader.load_body(skill)

        assert body is not None
        assert "# Test Skill" in body
        assert skill.body == body

    @pytest.mark.asyncio
    async def test_default_mode_for_python_scripts(self, loader, temp_skill_dir):
        """Test default mode is 'native' for Python scripts."""
        skill = await loader.load_skill(temp_skill_dir)

        # auto_discovered.py has no YAML config
        auto = skill.scripts["auto_discovered"]
        assert auto.mode == "native"

    @pytest.mark.asyncio
    async def test_default_mode_for_shell_scripts(self, temp_skill_dir):
        """Test default mode is 'subprocess' for non-Python scripts."""
        # Create skill with only auto-discovered shell script
        skill_md = temp_skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Test skill
version: 1.0.0
---
# Test
""")

        # Create shell script
        shell_script = temp_skill_dir / "scripts" / "helper.sh"
        shell_script.write_text("#!/bin/bash\necho test\n")

        loader = SkillLoader()
        skill = await loader.load_skill(temp_skill_dir)

        assert "helper" in skill.scripts
        assert skill.scripts["helper"].mode == "subprocess"


class TestSkillLoaderErrors:
    """Tests for error handling in SkillLoader."""

    @pytest.mark.asyncio
    async def test_missing_skill_md(self, loader):
        """Test error when SKILL.md is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "no-skill"
            skill_path.mkdir()

            with pytest.raises(SkillLoadError, match="SKILL.md not found"):
                await loader.load_skill(skill_path)

    @pytest.mark.asyncio
    async def test_missing_frontmatter(self, loader):
        """Test error when YAML frontmatter is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "bad-skill"
            skill_path.mkdir()

            skill_md = skill_path / "SKILL.md"
            skill_md.write_text("# Just markdown, no frontmatter")

            with pytest.raises(SkillLoadError, match="frontmatter"):
                await loader.load_skill(skill_path)

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, loader):
        """Test error when required fields are missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "incomplete-skill"
            skill_path.mkdir()

            skill_md = skill_path / "SKILL.md"
            skill_md.write_text("""---
name: incomplete
# Missing description and version
---
# Test
""")

            with pytest.raises(SkillLoadError, match="Missing required fields"):
                await loader.load_skill(skill_path)

    @pytest.mark.asyncio
    async def test_invalid_resource_type(self, loader, temp_skill_dir):
        """Test error when loading invalid resource type."""
        skill = await loader.load_skill(temp_skill_dir)

        with pytest.raises(SkillLoadError, match="Invalid resource type"):
            await loader.load_resource(skill, "invalid_type", "any")

    @pytest.mark.asyncio
    async def test_resource_not_found(self, loader, temp_skill_dir):
        """Test error when resource is not found."""
        skill = await loader.load_skill(temp_skill_dir)

        with pytest.raises(SkillLoadError, match="Resource not found"):
            await loader.load_resource(skill, "reference", "nonexistent")


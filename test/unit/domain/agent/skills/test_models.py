"""
Unit tests for skill data models.
"""

import pytest
from pathlib import Path

from aiecs.domain.agent.skills.models import (
    SkillMetadata,
    SkillResource,
    SkillDefinition,
)


class TestSkillMetadata:
    """Tests for SkillMetadata dataclass."""
    
    def test_valid_metadata(self):
        """Test creating valid skill metadata."""
        metadata = SkillMetadata(
            name="python-coding",
            description="Python development guidance",
            version="1.0.0",
            author="AIECS Team",
            tags=["python", "coding"],
            dependencies=["code-analysis"],
            recommended_tools=["python-linter", "test-runner"]
        )
        
        assert metadata.name == "python-coding"
        assert metadata.description == "Python development guidance"
        assert metadata.version == "1.0.0"
        assert metadata.author == "AIECS Team"
        assert metadata.tags == ["python", "coding"]
        assert metadata.dependencies == ["code-analysis"]
        assert metadata.recommended_tools == ["python-linter", "test-runner"]
    
    def test_metadata_with_defaults(self):
        """Test metadata with optional fields as None."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test description",
            version="1.0.0"
        )
        
        assert metadata.author is None
        assert metadata.tags == []
        assert metadata.dependencies == []
        assert metadata.recommended_tools == []
    
    def test_invalid_name_format(self):
        """Test that invalid name format raises ValueError."""
        with pytest.raises(ValueError, match="must be kebab-case"):
            SkillMetadata(
                name="InvalidName",  # Should be kebab-case
                description="Test",
                version="1.0.0"
            )
        
        with pytest.raises(ValueError, match="must be kebab-case"):
            SkillMetadata(
                name="invalid_name",  # Underscores not allowed
                description="Test",
                version="1.0.0"
            )
    
    def test_invalid_version_format(self):
        """Test that invalid version format raises ValueError."""
        with pytest.raises(ValueError, match="must be semantic version"):
            SkillMetadata(
                name="test-skill",
                description="Test",
                version="1.0"  # Should be semver
            )
        
        with pytest.raises(ValueError, match="must be semantic version"):
            SkillMetadata(
                name="test-skill",
                description="Test",
                version="v1.0.0"  # Should not have 'v' prefix
            )


class TestSkillResource:
    """Tests for SkillResource dataclass."""
    
    def test_valid_resource(self):
        """Test creating valid skill resource."""
        resource = SkillResource(
            path="references/best-practices.md",
            type="reference"
        )
        
        assert resource.path == "references/best-practices.md"
        assert resource.type == "reference"
        assert resource.content is None
        assert resource.executable is False
        assert resource.mode is None
    
    def test_script_resource_with_metadata(self):
        """Test script resource with mode, description, and parameters."""
        resource = SkillResource(
            path="scripts/validate.py",
            type="script",
            mode="native",
            description="Validate Python code syntax",
            parameters={
                "code": {"type": "string", "required": True},
                "strict": {"type": "boolean", "required": False}
            }
        )
        
        assert resource.path == "scripts/validate.py"
        assert resource.type == "script"
        assert resource.executable is True  # Auto-set for scripts
        assert resource.mode == "native"
        assert resource.description == "Validate Python code syntax"
        assert resource.parameters == {
            "code": {"type": "string", "required": True},
            "strict": {"type": "boolean", "required": False}
        }
    
    def test_script_auto_executable(self):
        """Test that scripts are automatically marked as executable."""
        resource = SkillResource(
            path="scripts/test.sh",
            type="script"
        )
        
        assert resource.executable is True
    
    def test_invalid_resource_type(self):
        """Test that invalid resource type raises ValueError."""
        with pytest.raises(ValueError, match="Resource type must be one of"):
            SkillResource(
                path="test.txt",
                type="invalid"
            )
    
    def test_invalid_script_mode(self):
        """Test that invalid script mode raises ValueError."""
        with pytest.raises(ValueError, match="Script mode must be one of"):
            SkillResource(
                path="scripts/test.py",
                type="script",
                mode="invalid"
            )
    
    def test_valid_script_modes(self):
        """Test all valid script modes."""
        for mode in ['native', 'subprocess', 'auto']:
            resource = SkillResource(
                path="scripts/test.py",
                type="script",
                mode=mode
            )
            assert resource.mode == mode


class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""
    
    def test_valid_skill_definition(self):
        """Test creating valid skill definition."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0",
            recommended_tools=["tool1", "tool2"]
        )
        
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill")
        )
        
        assert skill.metadata == metadata
        assert skill.skill_path == Path("/path/to/skill")
        assert skill.body is None
        assert skill.references == {}
        assert skill.examples == {}
        assert skill.scripts == {}
        assert skill.assets == {}

    def test_skill_with_resources(self):
        """Test skill definition with resources."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0"
        )

        ref_resource = SkillResource(
            path="references/guide.md",
            type="reference"
        )

        script_resource = SkillResource(
            path="scripts/validate.py",
            type="script",
            mode="native",
            description="Validate code",
            parameters={"code": {"type": "string"}}
        )

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill"),
            references={"guide": ref_resource},
            scripts={"validate": script_resource}
        )

        assert "guide" in skill.references
        assert "validate" in skill.scripts
        assert skill.scripts["validate"].mode == "native"
        assert skill.scripts["validate"].description == "Validate code"

    def test_recommended_tools_property(self):
        """Test recommended_tools property."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0",
            recommended_tools=["tool1", "tool2"]
        )

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill")
        )

        assert skill.recommended_tools == ["tool1", "tool2"]

    def test_recommended_tools_empty(self):
        """Test recommended_tools when not specified."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0"
        )

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill")
        )

        assert skill.recommended_tools == []

    def test_is_body_loaded(self):
        """Test is_body_loaded method."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0"
        )

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill")
        )

        assert not skill.is_body_loaded()

        skill.body = "# Test Skill\n\nThis is the body content."
        assert skill.is_body_loaded()

    def test_is_resource_loaded(self):
        """Test is_resource_loaded method."""
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            version="1.0.0"
        )

        ref_resource = SkillResource(
            path="references/guide.md",
            type="reference"
        )

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=Path("/path/to/skill"),
            references={"guide": ref_resource}
        )

        # Resource exists but content not loaded
        assert not skill.is_resource_loaded("reference", "guide")

        # Load content
        ref_resource.content = "# Guide\n\nContent here."
        assert skill.is_resource_loaded("reference", "guide")

        # Non-existent resource
        assert not skill.is_resource_loaded("reference", "nonexistent")

        # Invalid resource type
        assert not skill.is_resource_loaded("invalid", "guide")


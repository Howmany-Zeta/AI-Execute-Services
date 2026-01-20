"""
Unit tests for skill validator.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from aiecs.domain.agent.skills.validator import (
    SkillValidator,
    SkillValidationError,
    ValidationResult,
    ValidationIssue,
    VALID_SCRIPT_MODES,
)
from aiecs.domain.agent.skills.models import (
    SkillMetadata,
    SkillResource,
    SkillDefinition,
)


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_create_error_issue(self):
        """Test creating an error issue."""
        issue = ValidationIssue(
            field="name",
            message="Invalid name format",
            severity="error"
        )
        assert issue.field == "name"
        assert issue.message == "Invalid name format"
        assert issue.severity == "error"
        assert "[ERROR]" in str(issue)

    def test_create_warning_issue(self):
        """Test creating a warning issue."""
        issue = ValidationIssue(
            field="description",
            message="Description is short",
            severity="warning"
        )
        assert issue.severity == "warning"
        assert "[WARNING]" in str(issue)

    def test_default_severity(self):
        """Test default severity is error."""
        issue = ValidationIssue(field="test", message="test")
        assert issue.severity == "error"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True, skill_name="test-skill")
        assert result.valid is True
        assert result.skill_name == "test-skill"
        assert result.issues == []
        assert result.errors == []
        assert result.warnings == []

    def test_add_error(self):
        """Test adding an error to result."""
        result = ValidationResult(valid=True)
        result.add_error("field", "error message")
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field"
        assert result.errors[0].message == "error message"

    def test_add_warning(self):
        """Test adding a warning to result."""
        result = ValidationResult(valid=True)
        result.add_warning("field", "warning message")
        assert result.valid is True  # Warnings don't invalidate
        assert len(result.warnings) == 1

    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult(valid=True)
        result1.add_warning("field1", "warning")

        result2 = ValidationResult(valid=True)
        result2.add_error("field2", "error")

        result1.merge(result2)

        assert result1.valid is False  # Merged in an error
        assert len(result1.issues) == 2

    def test_str_representation(self):
        """Test string representation."""
        result = ValidationResult(valid=True, skill_name="my-skill")
        assert "passed" in str(result)
        assert "my-skill" in str(result)

        result.add_error("name", "bad name")
        assert "failed" in str(result)


class TestSkillValidator:
    """Tests for SkillValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return SkillValidator()

    @pytest.fixture
    def valid_metadata(self):
        """Create valid metadata."""
        return SkillMetadata(
            name="test-skill",
            description="A valid test skill for testing purposes",
            version="1.0.0",
            author="Test Author",
            tags=["test", "validation"],
            dependencies=["other-skill"],
            recommended_tools=["tool1", "tool2"]
        )

    @pytest.fixture
    def valid_skill(self, valid_metadata, tmp_path):
        """Create a valid skill definition."""
        skill_path = tmp_path / "test-skill"
        skill_path.mkdir()

        # Create SKILL.md
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\nversion: 1.0.0\n---\nBody")

        return SkillDefinition(
            metadata=valid_metadata,
            skill_path=skill_path,
            body="Test skill body"
        )

    def test_validate_valid_skill(self, validator, valid_skill):
        """Test validating a valid skill."""
        result = validator.validate(valid_skill)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_name_format(self, validator, tmp_path):
        """Test validation fails for invalid name format."""
        # SkillMetadata validates on creation, so we need to test yaml_dict validation
        yaml_dict = {
            "name": "InvalidName",
            "description": "Test",
            "version": "1.0.0"
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("kebab-case" in e.message for e in result.errors)

    def test_validate_invalid_version_format(self, validator):
        """Test validation fails for invalid version format."""
        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "invalid"
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("semantic versioning" in e.message for e in result.errors)

    def test_validate_missing_required_fields(self, validator):
        """Test validation fails for missing required fields."""
        yaml_dict = {"name": "test-skill"}  # Missing description and version
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("description" in e.field for e in result.errors)
        assert any("version" in e.field for e in result.errors)

    def test_validate_null_required_fields(self, validator):
        """Test validation fails for null required fields."""
        yaml_dict = {
            "name": "test-skill",
            "description": None,
            "version": "1.0.0"
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("cannot be null" in e.message for e in result.errors)

    def test_validate_list_fields_type(self, validator):
        """Test validation for list field types."""
        yaml_dict = {
            "name": "test-skill",
            "description": "Test",
            "version": "1.0.0",
            "tags": "not-a-list"
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("must be a list" in e.message for e in result.errors)

    def test_validate_list_items_type(self, validator):
        """Test validation for list item types."""
        yaml_dict = {
            "name": "test-skill",
            "description": "Test",
            "version": "1.0.0",
            "tags": ["valid", 123, "another"]
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("must be strings" in e.message for e in result.errors)

    def test_validate_empty_description_warning(self, validator, valid_metadata, tmp_path):
        """Test warning for very short description."""
        skill_path = tmp_path / "test"
        skill_path.mkdir()

        # Create metadata with short description
        metadata = SkillMetadata(
            name="test-skill",
            description="Short",  # Very short
            version="1.0.0"
        )
        skill = SkillDefinition(metadata=metadata, skill_path=skill_path)

        result = validator.validate(skill)
        assert any("very short" in w.message for w in result.warnings)

    def test_strict_mode(self, validator, valid_metadata, tmp_path):
        """Test strict mode converts warnings to errors."""
        strict_validator = SkillValidator(strict_mode=True)
        skill_path = tmp_path / "test"
        skill_path.mkdir()

        metadata = SkillMetadata(
            name="test-skill",
            description="Short",
            version="1.0.0"
        )
        skill = SkillDefinition(metadata=metadata, skill_path=skill_path)

        result = strict_validator.validate(skill)
        # Warnings become errors in strict mode
        assert result.valid is False or len(result.warnings) == 0


class TestScriptConfigValidation:
    """Tests for script configuration validation."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return SkillValidator()

    def test_validate_scripts_valid_config(self, validator, tmp_path):
        """Test validation of valid script configuration."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "mode": "native",
                    "description": "Run tests",
                    "parameters": {
                        "input": {"type": "string", "required": True}
                    }
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is True

    def test_validate_scripts_invalid_mode(self, validator, tmp_path):
        """Test validation fails for invalid script mode."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "mode": "invalid_mode"
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is False
        assert any("Invalid mode" in e.message for e in result.errors)

    def test_validate_scripts_missing_path(self, validator):
        """Test validation fails for missing script path."""
        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "mode": "native"
                    # Missing 'path' field
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict)
        assert result.valid is False
        assert any("must include 'path'" in e.message for e in result.errors)

    def test_validate_scripts_nonexistent_file(self, validator, tmp_path):
        """Test validation fails when script file doesn't exist."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/nonexistent.py"
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is False
        assert any("does not exist" in e.message for e in result.errors)

    def test_validate_scripts_simple_path_format(self, validator, tmp_path):
        """Test validation of simple path-only script format."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": "scripts/test.py"  # Simple path format
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is True

    def test_validate_scripts_invalid_parameters_type(self, validator, tmp_path):
        """Test validation fails for invalid parameters type."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "parameters": "not-a-dict"
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is False
        assert any("must be a dictionary" in e.message for e in result.errors)

    def test_validate_scripts_invalid_param_definition(self, validator, tmp_path):
        """Test validation fails for invalid parameter definition."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "parameters": {
                        "param1": "not-a-dict"  # Should be a dict
                    }
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is False
        assert any("must be a dictionary" in e.message for e in result.errors)

    def test_validate_scripts_invalid_param_required(self, validator, tmp_path):
        """Test validation fails for non-boolean required field."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "parameters": {
                        "param1": {"type": "string", "required": "yes"}
                    }
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        assert result.valid is False
        assert any("must be a boolean" in e.message for e in result.errors)

    def test_validate_scripts_unknown_type_warning(self, validator, tmp_path):
        """Test warning for unknown parameter type."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test.py").write_text("print('test')")

        yaml_dict = {
            "name": "test-skill",
            "description": "Test description",
            "version": "1.0.0",
            "scripts": {
                "test_script": {
                    "path": "scripts/test.py",
                    "parameters": {
                        "param1": {"type": "custom_type"}
                    }
                }
            }
        }
        result = validator.validate_yaml_dict(yaml_dict, skill_path)
        # Should be a warning, not error
        assert any("Unknown type" in w.message for w in result.warnings)


class TestResourceValidation:
    """Tests for resource validation."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return SkillValidator()

    def test_validate_resources_exist(self, validator, tmp_path):
        """Test validation passes when resources exist."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        refs_dir = skill_path / "references"
        refs_dir.mkdir()
        (refs_dir / "doc.md").write_text("# Documentation")

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            references={
                "doc": SkillResource(
                    path="references/doc.md",
                    type="reference"
                )
            }
        )

        result = validator.validate(skill)
        assert result.valid is True

    def test_validate_resources_missing(self, validator, tmp_path):
        """Test validation fails when resources don't exist."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            references={
                "missing": SkillResource(
                    path="references/missing.md",
                    type="reference"
                )
            }
        )

        result = validator.validate(skill)
        assert result.valid is False
        assert any("does not exist" in e.message for e in result.errors)

    def test_validate_scripts_in_skill(self, validator, tmp_path):
        """Test validation of scripts in SkillDefinition."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('run')")

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            scripts={
                "run": SkillResource(
                    path="scripts/run.py",
                    type="script",
                    mode="native",
                    description="Run the script"
                )
            }
        )

        result = validator.validate(skill)
        assert result.valid is True

    def test_validate_script_invalid_mode_in_skill(self, validator, tmp_path):
        """Test validation fails for invalid mode in SkillDefinition."""
        skill_path = tmp_path / "skill"
        skill_path.mkdir()
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "run.py").write_text("print('run')")

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )

        # Create script resource with invalid mode manually
        # Note: SkillResource validates mode, so we test via mocking
        script = SkillResource(
            path="scripts/run.py",
            type="script",
            mode="native"  # Valid mode
        )
        # Override mode to test validation
        object.__setattr__(script, 'mode', 'invalid_mode')

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            scripts={"run": script}
        )

        result = validator.validate(skill)
        assert result.valid is False
        assert any("Invalid mode" in e.message for e in result.errors)


class TestValidatorOptions:
    """Tests for validator configuration options."""

    def test_disable_resource_validation(self, tmp_path):
        """Test disabling resource validation."""
        validator = SkillValidator(validate_resources=False)
        skill_path = tmp_path / "skill"
        skill_path.mkdir()

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )
        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            references={
                "missing": SkillResource(
                    path="references/missing.md",
                    type="reference"
                )
            }
        )

        result = validator.validate(skill)
        # Should pass because resource validation is disabled
        assert result.valid is True

    def test_disable_script_validation(self, tmp_path):
        """Test disabling script validation."""
        validator = SkillValidator(validate_scripts=False)
        skill_path = tmp_path / "skill"
        skill_path.mkdir()

        metadata = SkillMetadata(
            name="test-skill",
            description="Test description for validation",
            version="1.0.0"
        )

        # Create script resource and override mode
        script = SkillResource(
            path="scripts/missing.py",
            type="script",
            mode="native"
        )
        object.__setattr__(script, 'mode', 'invalid_mode')

        skill = SkillDefinition(
            metadata=metadata,
            skill_path=skill_path,
            scripts={"missing": script}
        )

        result = validator.validate(skill)
        # Should pass because script validation is disabled
        assert result.valid is True


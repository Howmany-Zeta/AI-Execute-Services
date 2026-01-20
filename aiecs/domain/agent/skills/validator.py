"""
Skill Validator

Validates SKILL.md files and skill definitions for correctness.
Provides comprehensive validation for YAML frontmatter, skill metadata,
resources, and script configurations.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SkillDefinition, SkillMetadata, SkillResource

logger = logging.getLogger(__name__)

# Valid script execution modes
VALID_SCRIPT_MODES = {'native', 'subprocess', 'auto'}

# Valid resource types
VALID_RESOURCE_TYPES = {'reference', 'example', 'script', 'asset'}

# Kebab-case pattern
KEBAB_CASE_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

# Semantic version pattern (basic semver: X.Y.Z with optional prerelease)
SEMVER_PATTERN = re.compile(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$')


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    field: str
    message: str
    severity: str = "error"  # "error" or "warning"

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.field}: {self.message}"


@dataclass
class ValidationResult:
    """Result of skill validation."""

    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    skill_name: Optional[str] = None
    skill_path: Optional[Path] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        """Get all error-level issues."""
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get all warning-level issues."""
        return [i for i in self.issues if i.severity == "warning"]

    def add_error(self, field: str, message: str) -> None:
        """Add an error issue."""
        self.issues.append(ValidationIssue(field, message, "error"))
        self.valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning issue."""
        self.issues.append(ValidationIssue(field, message, "warning"))

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.issues.extend(other.issues)
        if not other.valid:
            self.valid = False

    def __str__(self) -> str:
        if self.valid and not self.warnings:
            return f"Validation passed for skill: {self.skill_name or 'unknown'}"

        lines = [f"Validation {'passed with warnings' if self.valid else 'failed'} "
                 f"for skill: {self.skill_name or 'unknown'}"]
        for issue in self.issues:
            lines.append(f"  - {issue}")
        return "\n".join(lines)


class SkillValidationError(Exception):
    """Raised when skill validation fails."""

    def __init__(self, message: str, result: Optional[ValidationResult] = None):
        super().__init__(message)
        self.result = result


class SkillValidator:
    """
    Validates skill definitions and SKILL.md files.

    Provides validation for:
    - YAML frontmatter schema (required fields, types)
    - Metadata format (kebab-case names, semver versions)
    - Resource existence (referenced files must exist)
    - Script configuration (paths, modes, parameters)
    - Dependency references (if dependencies are declared)
    """

    def __init__(
        self,
        strict_mode: bool = False,
        validate_resources: bool = True,
        validate_scripts: bool = True
    ):
        """
        Initialize the skill validator.

        Args:
            strict_mode: If True, warnings are treated as errors
            validate_resources: If True, check resource files exist
            validate_scripts: If True, validate script configurations
        """
        self.strict_mode = strict_mode
        self.validate_resources = validate_resources
        self.validate_scripts = validate_scripts

    def validate(self, skill: SkillDefinition) -> ValidationResult:
        """
        Validate a skill definition.

        Args:
            skill: SkillDefinition to validate

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(
            valid=True,
            skill_name=skill.metadata.name,
            skill_path=skill.skill_path
        )

        # Validate metadata
        self._validate_metadata(skill.metadata, result)

        # Validate resources if enabled
        if self.validate_resources:
            self._validate_resources(skill, result)

        # Validate scripts if enabled
        if self.validate_scripts:
            self._validate_scripts(skill, result)

        # In strict mode, convert warnings to errors
        if self.strict_mode:
            for issue in result.issues:
                if issue.severity == "warning":
                    issue.severity = "error"
                    result.valid = False

        return result

    def validate_yaml_dict(
        self,
        yaml_dict: Dict[str, Any],
        skill_path: Optional[Path] = None
    ) -> ValidationResult:
        """
        Validate a YAML frontmatter dictionary before creating a skill.

        Args:
            yaml_dict: Parsed YAML frontmatter dictionary
            skill_path: Optional path to skill directory for resource validation

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult(
            valid=True,
            skill_name=yaml_dict.get('name', 'unknown'),
            skill_path=skill_path
        )

        # Check required fields
        required_fields = ['name', 'description', 'version']
        for field_name in required_fields:
            if field_name not in yaml_dict:
                result.add_error(field_name, f"Required field '{field_name}' is missing")
            elif yaml_dict[field_name] is None:
                result.add_error(field_name, f"Required field '{field_name}' cannot be null")
            elif not isinstance(yaml_dict[field_name], str):
                result.add_error(
                    field_name,
                    f"Field '{field_name}' must be a string, got {type(yaml_dict[field_name]).__name__}"
                )

        # Validate name format (if present)
        if 'name' in yaml_dict and isinstance(yaml_dict['name'], str):
            self._validate_name_format(yaml_dict['name'], result)

        # Validate version format (if present)
        if 'version' in yaml_dict and isinstance(yaml_dict['version'], str):
            self._validate_version_format(yaml_dict['version'], result)

        # Validate optional list fields
        list_fields = ['tags', 'dependencies', 'recommended_tools']
        for field_name in list_fields:
            if field_name in yaml_dict and yaml_dict[field_name] is not None:
                if not isinstance(yaml_dict[field_name], list):
                    result.add_error(
                        field_name,
                        f"Field '{field_name}' must be a list, got {type(yaml_dict[field_name]).__name__}"
                    )
                else:
                    for i, item in enumerate(yaml_dict[field_name]):
                        if not isinstance(item, str):
                            result.add_error(
                                f"{field_name}[{i}]",
                                f"List items must be strings, got {type(item).__name__}"
                            )

        # Validate scripts configuration if present
        if 'scripts' in yaml_dict and yaml_dict['scripts'] is not None:
            self._validate_scripts_yaml(yaml_dict['scripts'], skill_path, result)

        return result

    def _validate_metadata(
        self,
        metadata: SkillMetadata,
        result: ValidationResult
    ) -> None:
        """Validate skill metadata fields."""
        # Name format
        self._validate_name_format(metadata.name, result)

        # Version format
        self._validate_version_format(metadata.version, result)

        # Description should not be empty
        if not metadata.description or not metadata.description.strip():
            result.add_error("description", "Description cannot be empty")

        # Warn if description is too short
        if metadata.description and len(metadata.description.strip()) < 10:
            result.add_warning(
                "description",
                "Description is very short; consider adding more detail for better skill matching"
            )

        # Validate tags format (should be lowercase, no spaces)
        if metadata.tags:
            for i, tag in enumerate(metadata.tags):
                if not isinstance(tag, str):
                    result.add_error(f"tags[{i}]", f"Tag must be a string, got {type(tag).__name__}")
                elif not re.match(r'^[a-z0-9-]+$', tag):
                    result.add_warning(
                        f"tags[{i}]",
                        f"Tag '{tag}' should be lowercase alphanumeric with hyphens"
                    )

        # Validate dependencies format (should be kebab-case skill names)
        if metadata.dependencies:
            for i, dep in enumerate(metadata.dependencies):
                if not isinstance(dep, str):
                    result.add_error(
                        f"dependencies[{i}]",
                        f"Dependency must be a string, got {type(dep).__name__}"
                    )
                elif not KEBAB_CASE_PATTERN.match(dep):
                    result.add_warning(
                        f"dependencies[{i}]",
                        f"Dependency '{dep}' should be kebab-case"
                    )

    def _validate_name_format(self, name: str, result: ValidationResult) -> None:
        """Validate skill name is kebab-case."""
        if not KEBAB_CASE_PATTERN.match(name):
            result.add_error(
                "name",
                f"Skill name must be kebab-case (lowercase with hyphens): '{name}'"
            )

    def _validate_version_format(self, version: str, result: ValidationResult) -> None:
        """Validate version is semantic versioning format."""
        if not SEMVER_PATTERN.match(version):
            result.add_error(
                "version",
                f"Version must be semantic versioning (X.Y.Z): '{version}'"
            )

    def _validate_resources(
        self,
        skill: SkillDefinition,
        result: ValidationResult
    ) -> None:
        """Validate that all resource files exist."""
        resource_collections = [
            ('references', skill.references),
            ('examples', skill.examples),
            ('assets', skill.assets),
        ]

        for collection_name, resources in resource_collections:
            for name, resource in resources.items():
                resource_path = skill.skill_path / resource.path
                if not resource_path.exists():
                    result.add_error(
                        f"{collection_name}.{name}",
                        f"Resource file does not exist: {resource.path}"
                    )
                elif not resource_path.is_file():
                    result.add_error(
                        f"{collection_name}.{name}",
                        f"Resource path is not a file: {resource.path}"
                    )

    def _validate_scripts(
        self,
        skill: SkillDefinition,
        result: ValidationResult
    ) -> None:
        """Validate script configurations."""
        for name, script in skill.scripts.items():
            # Validate script path exists
            script_path = skill.skill_path / script.path
            if not script_path.exists():
                result.add_error(
                    f"scripts.{name}.path",
                    f"Script file does not exist: {script.path}"
                )
            elif not script_path.is_file():
                result.add_error(
                    f"scripts.{name}.path",
                    f"Script path is not a file: {script.path}"
                )

            # Validate mode value
            if script.mode is not None:
                if script.mode not in VALID_SCRIPT_MODES:
                    result.add_error(
                        f"scripts.{name}.mode",
                        f"Invalid mode '{script.mode}'. Must be one of: {', '.join(sorted(VALID_SCRIPT_MODES))}"
                    )

            # Validate parameters if provided
            if script.parameters is not None:
                self._validate_script_parameters(name, script.parameters, result)

            # Validate description if provided
            if script.description is not None:
                if not isinstance(script.description, str):
                    result.add_error(
                        f"scripts.{name}.description",
                        f"Description must be a string, got {type(script.description).__name__}"
                    )
                elif not script.description.strip():
                    result.add_warning(
                        f"scripts.{name}.description",
                        "Script description is empty"
                    )

    def _validate_scripts_yaml(
        self,
        scripts_config: Any,
        skill_path: Optional[Path],
        result: ValidationResult
    ) -> None:
        """Validate scripts configuration from YAML frontmatter."""
        if not isinstance(scripts_config, dict):
            result.add_error(
                "scripts",
                f"Scripts must be a dictionary, got {type(scripts_config).__name__}"
            )
            return

        for script_name, config in scripts_config.items():
            # Validate script name format
            if not isinstance(script_name, str):
                result.add_error(
                    f"scripts.{script_name}",
                    f"Script name must be a string"
                )
                continue

            # Handle simple string path format
            if isinstance(config, str):
                # Simple path-only format
                if skill_path:
                    full_path = skill_path / config
                    if not full_path.exists():
                        result.add_error(
                            f"scripts.{script_name}",
                            f"Script file does not exist: {config}"
                        )
                continue

            if not isinstance(config, dict):
                result.add_error(
                    f"scripts.{script_name}",
                    f"Script configuration must be a string (path) or dictionary, got {type(config).__name__}"
                )
                continue

            # Validate required 'path' field
            if 'path' not in config:
                result.add_error(
                    f"scripts.{script_name}.path",
                    "Script configuration must include 'path' field"
                )
            elif not isinstance(config['path'], str):
                result.add_error(
                    f"scripts.{script_name}.path",
                    f"Script path must be a string, got {type(config['path']).__name__}"
                )
            elif skill_path:
                # Validate path exists
                full_path = skill_path / config['path']
                if not full_path.exists():
                    result.add_error(
                        f"scripts.{script_name}.path",
                        f"Script file does not exist: {config['path']}"
                    )

            # Validate mode if provided
            if 'mode' in config and config['mode'] is not None:
                if not isinstance(config['mode'], str):
                    result.add_error(
                        f"scripts.{script_name}.mode",
                        f"Mode must be a string, got {type(config['mode']).__name__}"
                    )
                elif config['mode'] not in VALID_SCRIPT_MODES:
                    result.add_error(
                        f"scripts.{script_name}.mode",
                        f"Invalid mode '{config['mode']}'. Must be one of: {', '.join(sorted(VALID_SCRIPT_MODES))}"
                    )

            # Validate description if provided
            if 'description' in config and config['description'] is not None:
                if not isinstance(config['description'], str):
                    result.add_error(
                        f"scripts.{script_name}.description",
                        f"Description must be a string, got {type(config['description']).__name__}"
                    )

            # Validate parameters if provided
            if 'parameters' in config and config['parameters'] is not None:
                self._validate_script_parameters(
                    script_name,
                    config['parameters'],
                    result
                )

    def _validate_script_parameters(
        self,
        script_name: str,
        parameters: Any,
        result: ValidationResult
    ) -> None:
        """Validate script parameter definitions."""
        if not isinstance(parameters, dict):
            result.add_error(
                f"scripts.{script_name}.parameters",
                f"Parameters must be a dictionary, got {type(parameters).__name__}"
            )
            return

        valid_types = {'string', 'integer', 'number', 'boolean', 'object', 'array'}

        for param_name, param_def in parameters.items():
            if not isinstance(param_name, str):
                result.add_error(
                    f"scripts.{script_name}.parameters",
                    f"Parameter name must be a string"
                )
                continue

            if not isinstance(param_def, dict):
                result.add_error(
                    f"scripts.{script_name}.parameters.{param_name}",
                    f"Parameter definition must be a dictionary, got {type(param_def).__name__}"
                )
                continue

            # Validate type field
            if 'type' in param_def:
                if not isinstance(param_def['type'], str):
                    result.add_error(
                        f"scripts.{script_name}.parameters.{param_name}.type",
                        f"Type must be a string, got {type(param_def['type']).__name__}"
                    )
                elif param_def['type'] not in valid_types:
                    result.add_warning(
                        f"scripts.{script_name}.parameters.{param_name}.type",
                        f"Unknown type '{param_def['type']}'. Common types: {', '.join(sorted(valid_types))}"
                    )

            # Validate required field
            if 'required' in param_def:
                if not isinstance(param_def['required'], bool):
                    result.add_error(
                        f"scripts.{script_name}.parameters.{param_name}.required",
                        f"Required must be a boolean, got {type(param_def['required']).__name__}"
                    )

            # Validate description field
            if 'description' in param_def:
                if not isinstance(param_def['description'], str):
                    result.add_error(
                        f"scripts.{script_name}.parameters.{param_name}.description",
                        f"Description must be a string, got {type(param_def['description']).__name__}"
                    )


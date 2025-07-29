"""
Framework Validator

Validates framework.yaml configuration against the defined schema.
Provides comprehensive validation with detailed error reporting.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from pydantic import ValidationError

from ..schemas.framework_schema import FrameworkConfigModel, FrameworkModel, MetaFrameworkModel

logger = logging.getLogger(__name__)


class FrameworkValidationError(Exception):
    """Custom exception for framework validation errors."""

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        super().__init__(message)
        self.errors = errors or []


class FrameworkValidator:
    """
    Validator for framework configuration files.

    Provides comprehensive validation of framework.yaml files including:
    - Schema validation
    - Business rule validation
    - Cross-reference validation
    - Data consistency checks
    """

    def __init__(self):
        """Initialize the framework validator."""
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

    def validate_file(self, file_path: str) -> Tuple[bool, FrameworkConfigModel, List[str], List[str]]:
        """
        Validate a framework configuration file.

        Args:
            file_path: Path to the framework.yaml file

        Returns:
            Tuple of (is_valid, config_model, errors, warnings)

        Raises:
            FrameworkValidationError: If validation fails critically
        """
        try:
            logger.info(f"Validating framework configuration file: {file_path}")

            # Reset validation state
            self.validation_errors.clear()
            self.validation_warnings.clear()

            # Check if file exists
            if not Path(file_path).exists():
                raise FrameworkValidationError(f"Framework configuration file not found: {file_path}")

            # Load and parse YAML
            config_data = self._load_yaml_file(file_path)

            # Validate schema
            config_model = self._validate_schema(config_data)

            # Perform business rule validation
            self._validate_business_rules(config_model)

            # Perform consistency checks
            self._validate_consistency(config_model)

            is_valid = len(self.validation_errors) == 0

            if is_valid:
                logger.info("Framework configuration validation passed")
            else:
                logger.warning(f"Framework configuration validation failed with {len(self.validation_errors)} errors")

            return is_valid, config_model, self.validation_errors.copy(), self.validation_warnings.copy()

        except Exception as e:
            logger.error(f"Framework validation failed: {e}")
            if isinstance(e, FrameworkValidationError):
                raise
            else:
                raise FrameworkValidationError(f"Validation failed: {e}")

    def validate_config_data(self, config_data: Dict[str, Any]) -> Tuple[bool, FrameworkConfigModel, List[str], List[str]]:
        """
        Validate framework configuration data directly.

        Args:
            config_data: Configuration data dictionary

        Returns:
            Tuple of (is_valid, config_model, errors, warnings)
        """
        try:
            # Reset validation state
            self.validation_errors.clear()
            self.validation_warnings.clear()

            # Validate schema
            config_model = self._validate_schema(config_data)

            # Perform business rule validation
            self._validate_business_rules(config_model)

            # Perform consistency checks
            self._validate_consistency(config_model)

            is_valid = len(self.validation_errors) == 0

            return is_valid, config_model, self.validation_errors.copy(), self.validation_warnings.copy()

        except Exception as e:
            logger.error(f"Framework validation failed: {e}")
            raise FrameworkValidationError(f"Validation failed: {e}")

    def _load_yaml_file(self, file_path: str) -> Dict[str, Any]:
        """Load and parse YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

            if not isinstance(data, dict):
                raise FrameworkValidationError("Framework configuration must be a YAML object/dictionary")

            return data

        except yaml.YAMLError as e:
            raise FrameworkValidationError(f"Invalid YAML syntax: {e}")
        except Exception as e:
            raise FrameworkValidationError(f"Failed to load YAML file: {e}")

    def _validate_schema(self, config_data: Dict[str, Any]) -> FrameworkConfigModel:
        """Validate configuration data against Pydantic schema."""
        try:
            return FrameworkConfigModel(**config_data)
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error['loc'])
                error_messages.append(f"Field '{field_path}': {error['msg']}")

            raise FrameworkValidationError(
                "Schema validation failed",
                errors=error_messages
            )

    def _validate_business_rules(self, config: FrameworkConfigModel) -> None:
        """Validate business rules and constraints."""

        # Validate framework business rules
        for framework in config.frameworks:
            self._validate_framework_business_rules(framework)

        # Validate meta-framework business rules
        for meta_framework in config.meta_frameworks:
            self._validate_meta_framework_business_rules(meta_framework, config)

    def _validate_framework_business_rules(self, framework: FrameworkModel) -> None:
        """Validate business rules for individual frameworks."""

        # Check component count
        components = framework.get_components_list()
        if len(components) < 2:
            self.validation_warnings.append(
                f"Framework '{framework.name}' has only {len(components)} component(s). "
                "Consider if this is sufficient for meaningful analysis."
            )

        if len(components) > 10:
            self.validation_warnings.append(
                f"Framework '{framework.name}' has {len(components)} components. "
                "Consider if this might be too complex for practical use."
            )

        # Check tag count
        tags = framework.get_tags_list()
        if len(tags) < 2:
            self.validation_warnings.append(
                f"Framework '{framework.name}' has only {len(tags)} tag(s). "
                "More tags improve searchability."
            )

        # Validate duration format
        if not self._is_valid_duration_format(framework.estimated_duration):
            self.validation_errors.append(
                f"Framework '{framework.name}' has invalid duration format: '{framework.estimated_duration}'. "
                "Expected format: 'X-Y hours' or 'X hours'"
            )

        # Check required data types
        if len(framework.required_data_types) == 0:
            self.validation_warnings.append(
                f"Framework '{framework.name}' has no required data types specified."
            )

    def _validate_meta_framework_business_rules(self, meta_framework: MetaFrameworkModel, config: FrameworkConfigModel) -> None:
        """Validate business rules for meta-frameworks."""

        # Check component framework count
        if len(meta_framework.component_frameworks) > 6:
            self.validation_warnings.append(
                f"Meta-framework '{meta_framework.name}' has {len(meta_framework.component_frameworks)} "
                "component frameworks. This might be too complex for practical execution."
            )

        # Validate duration format
        if not self._is_valid_duration_format(meta_framework.estimated_duration):
            self.validation_errors.append(
                f"Meta-framework '{meta_framework.name}' has invalid duration format: '{meta_framework.estimated_duration}'"
            )

        # Check complexity consistency
        component_complexities = []
        for component_name in meta_framework.component_frameworks:
            framework = config.get_framework_by_name(component_name)
            if framework:
                component_complexities.append(framework.complexity_level)

        if component_complexities:
            max_component_complexity = max(component_complexities, key=lambda x: self._complexity_to_int(x))
            meta_complexity_int = self._complexity_to_int(meta_framework.complexity_level)
            max_component_int = self._complexity_to_int(max_component_complexity)

            if meta_complexity_int < max_component_int:
                self.validation_warnings.append(
                    f"Meta-framework '{meta_framework.name}' complexity ({meta_framework.complexity_level}) "
                    f"is lower than its most complex component ({max_component_complexity})"
                )

    def _validate_consistency(self, config: FrameworkConfigModel) -> None:
        """Validate data consistency across the configuration."""

        # Check for problem type coverage
        problem_types = set()
        for framework in config.frameworks:
            problem_types.add(framework.solves_problem_type)

        for meta_framework in config.meta_frameworks:
            problem_types.add(meta_framework.solves_problem_type)

        # Check for duplicate problem types
        framework_problem_types = [f.solves_problem_type for f in config.frameworks]
        meta_problem_types = [m.solves_problem_type for m in config.meta_frameworks]

        all_problem_types = framework_problem_types + meta_problem_types
        duplicate_types = set([pt for pt in all_problem_types if all_problem_types.count(pt) > 1])

        if duplicate_types:
            self.validation_warnings.append(
                f"Duplicate problem types found: {', '.join(duplicate_types)}. "
                "Consider if multiple frameworks for the same problem type are necessary."
            )

        # Validate tag consistency
        self._validate_tag_consistency(config)

    def _validate_tag_consistency(self, config: FrameworkConfigModel) -> None:
        """Validate tag consistency across frameworks."""

        # Collect all tags
        all_tags = set()
        for framework in config.frameworks:
            all_tags.update(framework.get_tags_list())

        # Check for similar tags that might be typos
        tag_list = list(all_tags)
        for i, tag1 in enumerate(tag_list):
            for tag2 in tag_list[i+1:]:
                if self._are_similar_tags(tag1, tag2):
                    self.validation_warnings.append(
                        f"Similar tags found: '{tag1}' and '{tag2}'. "
                        "Consider if these should be the same tag."
                    )

    def _is_valid_duration_format(self, duration: str) -> bool:
        """Check if duration format is valid."""
        import re
        # Patterns: "X hours", "X-Y hours", "X-Y minutes"
        patterns = [
            r'^\d+-\d+\s+(hours?|minutes?)$',
            r'^\d+\s+(hours?|minutes?)$'
        ]

        return any(re.match(pattern, duration.strip(), re.IGNORECASE) for pattern in patterns)

    def _complexity_to_int(self, complexity: str) -> int:
        """Convert complexity level to integer for comparison."""
        mapping = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "very_high": 4
        }
        return mapping.get(complexity.lower(), 0)

    def _are_similar_tags(self, tag1: str, tag2: str) -> bool:
        """Check if two tags are similar (potential typos)."""
        # Simple similarity check based on edit distance
        if abs(len(tag1) - len(tag2)) > 2:
            return False

        # Calculate simple edit distance
        def edit_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return edit_distance(s2, s1)

            if len(s2) == 0:
                return len(s1)

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        distance = edit_distance(tag1.lower(), tag2.lower())
        max_length = max(len(tag1), len(tag2))

        # Consider similar if edit distance is less than 30% of the longer string
        return distance <= max_length * 0.3

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of the validation results."""
        return {
            "total_errors": len(self.validation_errors),
            "total_warnings": len(self.validation_warnings),
            "errors": self.validation_errors.copy(),
            "warnings": self.validation_warnings.copy(),
            "is_valid": len(self.validation_errors) == 0
        }


def validate_framework_config(file_path: str) -> Tuple[bool, Optional[FrameworkConfigModel], Dict[str, Any]]:
    """
    Convenience function to validate a framework configuration file.

    Args:
        file_path: Path to the framework.yaml file

    Returns:
        Tuple of (is_valid, config_model, validation_summary)
    """
    validator = FrameworkValidator()

    try:
        is_valid, config_model, errors, warnings = validator.validate_file(file_path)

        summary = {
            "total_errors": len(errors),
            "total_warnings": len(warnings),
            "errors": errors,
            "warnings": warnings,
            "is_valid": is_valid
        }

        return is_valid, config_model, summary

    except FrameworkValidationError as e:
        summary = {
            "total_errors": 1,
            "total_warnings": 0,
            "errors": [str(e)] + (e.errors if e.errors else []),
            "warnings": [],
            "is_valid": False
        }

        return False, None, summary

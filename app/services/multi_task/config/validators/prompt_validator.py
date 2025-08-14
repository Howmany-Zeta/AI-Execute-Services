"""
Prompt Configuration Validator

Validates prompt configuration files (prompts.yaml) to ensure they contain
valid role definitions, system prompts, and tool instructions.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: Dict[str, Any]
    warnings: List[str]

    def add_error(self, key: str, message: str) -> None:
        """Add an error to the validation result."""
        if key not in self.errors:
            self.errors[key] = []
        self.errors[key].append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(message)


class PromptValidator:
    """
    Validator for prompt configuration files.

    Validates the structure and content of prompts.yaml files to ensure
    they contain valid role definitions and system prompts.
    """

    def __init__(self):
        """Initialize the prompt validator."""
        self.required_fields = {
            'system_prompt': str,
            'roles': dict
        }

        self.required_role_fields = {
            'goal': str,
            'backstory': str
        }

        self.optional_role_fields = {
            'tools': list,
            'tools_instruction': str,
            'domain_specialization': str,
            'reasoning_guidance': str
        }

        # Valid tool names (should match available tools)
        self.valid_tools = {
            'chart', 'classifier', 'image', 'office', 'pandas',
            'report', 'research', 'scraper', 'stats', 'search_api'
        }

        # Valid task categories
        self.valid_categories = {
            'answer', 'collect', 'process', 'analyze', 'generate'
        }

    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a prompt configuration.

        Args:
            config_data: The prompt configuration data to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Validate top-level structure
            self._validate_structure(config_data, result)

            if result.is_valid:
                # Validate system prompt
                self._validate_system_prompt(config_data.get('system_prompt', ''), result)

                # Validate roles
                self._validate_roles(config_data.get('roles', {}), result)

        except Exception as e:
            result.add_error('validation_error', f"Unexpected error during validation: {e}")
            logger.error(f"Error validating prompt configuration: {e}")

        return result

    def _validate_structure(self, config_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate the top-level structure of the configuration."""
        if not isinstance(config_data, dict):
            result.add_error('structure', 'Configuration must be a dictionary')
            return

        # Check required fields
        for field, expected_type in self.required_fields.items():
            if field not in config_data:
                result.add_error('required_fields', f"Missing required field: {field}")
            elif not isinstance(config_data[field], expected_type):
                result.add_error(
                    'field_types',
                    f"Field '{field}' must be of type {expected_type.__name__}"
                )

    def _validate_system_prompt(self, system_prompt: str, result: ValidationResult) -> None:
        """Validate the system prompt content."""
        if not system_prompt or not system_prompt.strip():
            result.add_error('system_prompt', 'System prompt cannot be empty')
            return

        # Check minimum length
        if len(system_prompt.strip()) < 50:
            result.add_warning('System prompt is very short (less than 50 characters)')

        # Check for required sections
        required_sections = ['CAPABILITIES', 'TOOL USE GUIDELINES', 'RULES', 'OBJECTIVE']
        missing_sections = []

        for section in required_sections:
            if section not in system_prompt:
                missing_sections.append(section)

        if missing_sections:
            result.add_warning(f"System prompt missing recommended sections: {missing_sections}")

        # Check for placeholder patterns
        placeholder_pattern = r'\{[^}]+\}'
        placeholders = re.findall(placeholder_pattern, system_prompt)
        if placeholders:
            result.add_warning(f"System prompt contains placeholders that may need values: {placeholders}")

    def _validate_roles(self, roles: Dict[str, Any], result: ValidationResult) -> None:
        """Validate all role definitions."""
        if not roles:
            result.add_error('roles', 'No roles defined')
            return

        # Validate each role
        for role_name, role_config in roles.items():
            self._validate_single_role(role_name, role_config, result)

        # Check for recommended system roles
        recommended_system_roles = [
            'intent_parser', 'task_decomposer', 'planner', 'supervisor', 'director'
        ]

        missing_system_roles = []
        for role in recommended_system_roles:
            if role not in roles:
                missing_system_roles.append(role)

        if missing_system_roles:
            result.add_warning(f"Missing recommended system roles: {missing_system_roles}")

    def _validate_single_role(self, role_name: str, role_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate a single role definition."""
        if not isinstance(role_config, dict):
            result.add_error(f'role_{role_name}', 'Role configuration must be a dictionary')
            return

        # Check required fields
        for field, expected_type in self.required_role_fields.items():
            if field not in role_config:
                result.add_error(f'role_{role_name}', f"Missing required field: {field}")
            elif not isinstance(role_config[field], expected_type):
                result.add_error(
                    f'role_{role_name}',
                    f"Field '{field}' must be of type {expected_type.__name__}"
                )

        # Validate optional fields
        for field, expected_type in self.optional_role_fields.items():
            if field in role_config and not isinstance(role_config[field], expected_type):
                result.add_error(
                    f'role_{role_name}',
                    f"Field '{field}' must be of type {expected_type.__name__}"
                )

        # Validate specific field content
        self._validate_role_goal(role_name, role_config.get('goal', ''), result)
        self._validate_role_backstory(role_name, role_config.get('backstory', ''), result)
        self._validate_role_tools(role_name, role_config.get('tools', []), result)
        self._validate_role_tools_instruction(role_name, role_config.get('tools_instruction', ''), result)
        self._validate_role_domain_specialization(role_name, role_config.get('domain_specialization', ''), result)
        self._validate_role_reasoning_guidance(role_name, role_config.get('reasoning_guidance', ''), result)

    def _validate_role_goal(self, role_name: str, goal: str, result: ValidationResult) -> None:
        """Validate a role's goal."""
        if not goal or not goal.strip():
            result.add_error(f'role_{role_name}_goal', 'Goal cannot be empty')
            return

        # Check minimum length
        if len(goal.strip()) < 20:
            result.add_warning(f"Role '{role_name}' goal is very short (less than 20 characters)")

        # Check for action words
        action_words = ['analyze', 'create', 'generate', 'process', 'manage', 'execute', 'validate', 'review']
        has_action = any(word in goal.lower() for word in action_words)

        if not has_action:
            result.add_warning(f"Role '{role_name}' goal should contain action words describing what the role does")

    def _validate_role_backstory(self, role_name: str, backstory: str, result: ValidationResult) -> None:
        """Validate a role's backstory."""
        if not backstory or not backstory.strip():
            result.add_error(f'role_{role_name}_backstory', 'Backstory cannot be empty')
            return

        # Check minimum length
        if len(backstory.strip()) < 30:
            result.add_warning(f"Role '{role_name}' backstory is very short (less than 30 characters)")

    def _validate_role_tools(self, role_name: str, tools: List[str], result: ValidationResult) -> None:
        """Validate a role's tools list."""
        if not isinstance(tools, list):
            return  # Type validation handled elsewhere

        # Check for valid tool names
        invalid_tools = []
        for tool in tools:
            if not isinstance(tool, str):
                result.add_error(f'role_{role_name}_tools', f"Tool name must be a string: {tool}")
            elif tool not in self.valid_tools:
                invalid_tools.append(tool)

        if invalid_tools:
            result.add_warning(f"Role '{role_name}' uses unknown tools: {invalid_tools}")

    def _validate_role_tools_instruction(self, role_name: str, tools_instruction: str, result: ValidationResult) -> None:
        """Validate a role's tools instruction."""
        if not tools_instruction:
            return  # Optional field

        # Check for tool operation patterns
        tool_operation_pattern = r'(\w+)\.(\w+)'
        operations = re.findall(tool_operation_pattern, tools_instruction)

        if operations:
            # Validate tool names in operations
            for tool_name, operation in operations:
                if tool_name not in self.valid_tools:
                    result.add_warning(f"Role '{role_name}' tools instruction references unknown tool: {tool_name}")

        # Check for thinking tags
        if '<thinking>' in tools_instruction and '</thinking>' not in tools_instruction:
            result.add_error(f'role_{role_name}_tools_instruction', 'Unclosed <thinking> tag in tools instruction')

    def _validate_role_domain_specialization(self, role_name: str, domain_specialization: str, result: ValidationResult) -> None:
        """Validate a role's domain specialization."""
        if not domain_specialization:
            return  # Optional field

        # Check for domain references
        if 'DOMAINS' in domain_specialization or 'base.py' in domain_specialization:
            # This is good - role references the domain list
            pass
        else:
            result.add_warning(f"Role '{role_name}' domain specialization should reference the DOMAINS list")

        # Check for specific domain examples
        domain_examples = ['Economics', 'Medicine', 'AI', 'Finance', 'Psychology']
        has_examples = any(domain in domain_specialization for domain in domain_examples)

        if not has_examples:
            result.add_warning(f"Role '{role_name}' domain specialization should include specific domain examples")

    def _validate_role_reasoning_guidance(self, role_name: str, reasoning_guidance: str, result: ValidationResult) -> None:
        """Validate a role's reasoning guidance."""
        if not reasoning_guidance:
            return  # Optional field

        # Check for ReAct framework components
        react_components = ['Thought', 'Action', 'Observation', 'Reflection']
        missing_components = []

        for component in react_components:
            if component not in reasoning_guidance:
                missing_components.append(component)

        if missing_components:
            result.add_warning(f"Role '{role_name}' reasoning guidance missing ReAct components: {missing_components}")

        # Check for ReAct pattern keywords
        react_keywords = ['ReAct', 'framework', 'reasoning', 'systematic']
        has_react_keywords = any(keyword.lower() in reasoning_guidance.lower() for keyword in react_keywords)

        if not has_react_keywords:
            result.add_warning(f"Role '{role_name}' reasoning guidance should reference ReAct framework or systematic reasoning")

        # Check minimum length for meaningful guidance
        if len(reasoning_guidance.strip()) < 50:
            result.add_warning(f"Role '{role_name}' reasoning guidance is very short (less than 50 characters)")

    def validate_role_consistency(self, roles: Dict[str, Any]) -> ValidationResult:
        """
        Validate consistency across all roles.

        Args:
            roles: Dictionary of role configurations

        Returns:
            ValidationResult for cross-role consistency
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Check for duplicate goals
            goals = {}
            for role_name, role_config in roles.items():
                goal = role_config.get('goal', '')
                if goal in goals:
                    result.add_warning(f"Roles '{role_name}' and '{goals[goal]}' have similar goals")
                else:
                    goals[goal] = role_name

            # Check tool distribution
            tool_usage = {}
            for role_name, role_config in roles.items():
                tools = role_config.get('tools', [])
                for tool in tools:
                    if tool not in tool_usage:
                        tool_usage[tool] = []
                    tool_usage[tool].append(role_name)

            # Warn about unused tools
            unused_tools = self.valid_tools - set(tool_usage.keys())
            if unused_tools:
                result.add_warning(f"Tools not used by any role: {unused_tools}")

            # Check category coverage
            category_agents = {category: [] for category in self.valid_categories}

            for role_name, role_config in roles.items():
                # Infer category from role name
                for category in self.valid_categories:
                    if category in role_name.lower() or category in role_config.get('goal', '').lower():
                        category_agents[category].append(role_name)

            # Warn about categories without dedicated agents
            for category, agents in category_agents.items():
                if not agents:
                    result.add_warning(f"No dedicated agents found for category: {category}")

        except Exception as e:
            result.add_error('consistency_check', f"Error during consistency validation: {e}")
            logger.error(f"Error validating role consistency: {e}")

        return result

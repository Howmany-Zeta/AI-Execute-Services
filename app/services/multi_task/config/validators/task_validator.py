"""
Task Configuration Validator

Validates task configuration files (tasks.yaml) to ensure they contain
valid task definitions, tool configurations, and conditional logic.
"""

from typing import Dict, Any, List, Optional, Set
import re
import logging
from .prompt_validator import ValidationResult

logger = logging.getLogger(__name__)


class TaskValidator:
    """
    Validator for task configuration files.

    Validates the structure and content of tasks.yaml files to ensure
    they contain valid task definitions and tool configurations.
    """

    def __init__(self):
        """Initialize the task validator."""
        self.required_sections = {
            'system_tasks': dict,
            'sub_tasks': dict
        }

        self.required_task_fields = {
            'description': str,
            'agent': str,
            'expected_output': str
        }

        self.optional_task_fields = {
            'task_type': str,
            'tools': dict,
            'conditions': list
        }

        # Valid task types
        self.valid_task_types = {'fast', 'heavy'}

        # Valid tool names
        self.valid_tools = {
            'chart', 'classifier', 'image', 'office', 'pandas',
            'report', 'research', 'scraper', 'stats', 'search_api'
        }

        # Valid tool operations by tool
        self.valid_operations = {
            'scraper': {
                'get_requests', 'get_aiohttp', 'get_urllib', 'render', 'parse_html'
            },
            'pandas': {
                'dropna', 'fill_na', 'strip_strings', 'replace_values', 'filter',
                'select_columns', 'to_datetime', 'apply', 'sort_values', 'describe',
                'mean', 'min', 'max', 'merge', 'concat', 'drop_columns', 'astype',
                'pivot', 'melt', 'stack', 'unstack', 'to_numeric'
            },
            'stats': {
                'ttest', 'ttest_ind', 'anova', 'correlation', 'chi_square',
                'non_parametric', 'regression', 'time_series', 'describe', 'preprocess'
            },
            'research': {
                'mill_agreement', 'mill_difference', 'mill_concomitant', 'mill_joint',
                'mill_residues', 'summarize', 'deduction', 'induction'
            },
            'classifier': {
                'summarize', 'keyword_extract', 'tokenize', 'pos_tag', 'ner', 'dependency_parse',
                'classify', 'batch_process'
            },
            'office': {
                'read_docx', 'read_pptx', 'read_xlsx', 'extract_text',
                'write_docx', 'write_pptx', 'write_xlsx'
            },
            'image': {
                'load', 'ocr', 'resize', 'filter', 'detect_edges', 'metadata'
            },
            'chart': set(),  # Chart operations to be defined
            'report': {
                'generate_pdf', 'generate_image', 'generate_html', 'generate_excel',
                'generate_pptx', 'generate_markdown', 'generate_word'
            },
            'search_api': set()  # Search API operations to be defined
        }

        # Valid task categories
        self.valid_categories = {
            'answer', 'collect', 'process', 'analyze', 'generate'
        }

        # System task names that should exist
        self.required_system_tasks = {
            'parse_intent', 'breakdown_subTask', 'plan_sequence', 'examination', 'acceptance'
        }

    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a task configuration.

        Args:
            config_data: The task configuration data to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Validate top-level structure
            self._validate_structure(config_data, result)

            if result.is_valid:
                # Validate system tasks
                system_tasks = config_data.get('system_tasks', {})
                self._validate_system_tasks(system_tasks, result)

                # Validate sub-tasks
                sub_tasks = config_data.get('sub_tasks', {})
                self._validate_sub_tasks(sub_tasks, result)

                # Validate cross-task consistency
                self._validate_task_consistency(system_tasks, sub_tasks, result)

        except Exception as e:
            result.add_error('validation_error', f"Unexpected error during validation: {e}")
            logger.error(f"Error validating task configuration: {e}")

        return result

    def _validate_structure(self, config_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate the top-level structure of the configuration."""
        if not isinstance(config_data, dict):
            result.add_error('structure', 'Configuration must be a dictionary')
            return

        # Check required sections
        for section, expected_type in self.required_sections.items():
            if section not in config_data:
                result.add_error('required_sections', f"Missing required section: {section}")
            elif not isinstance(config_data[section], expected_type):
                result.add_error(
                    'section_types',
                    f"Section '{section}' must be of type {expected_type.__name__}"
                )

    def _validate_system_tasks(self, system_tasks: Dict[str, Any], result: ValidationResult) -> None:
        """Validate system task definitions."""
        if not system_tasks:
            result.add_error('system_tasks', 'No system tasks defined')
            return

        # Check for required system tasks
        missing_tasks = self.required_system_tasks - set(system_tasks.keys())
        if missing_tasks:
            result.add_error('system_tasks', f"Missing required system tasks: {missing_tasks}")

        # Validate each system task
        for task_name, task_config in system_tasks.items():
            self._validate_single_task(f"system_task_{task_name}", task_config, result, is_system_task=True)

    def _validate_sub_tasks(self, sub_tasks: Dict[str, Any], result: ValidationResult) -> None:
        """Validate sub-task definitions."""
        if not sub_tasks:
            result.add_warning('No sub-tasks defined')
            return

        # Validate each sub-task
        for task_name, task_config in sub_tasks.items():
            self._validate_single_task(f"sub_task_{task_name}", task_config, result, is_system_task=False)

        # Check category coverage
        self._validate_category_coverage(sub_tasks, result)

    def _validate_single_task(self, task_key: str, task_config: Dict[str, Any],
                            result: ValidationResult, is_system_task: bool = False) -> None:
        """Validate a single task definition."""
        if not isinstance(task_config, dict):
            result.add_error(task_key, 'Task configuration must be a dictionary')
            return

        # Check required fields
        for field, expected_type in self.required_task_fields.items():
            if field not in task_config:
                result.add_error(task_key, f"Missing required field: {field}")
            elif not isinstance(task_config[field], expected_type):
                result.add_error(
                    task_key,
                    f"Field '{field}' must be of type {expected_type.__name__}"
                )

        # Validate optional fields
        for field, expected_type in self.optional_task_fields.items():
            if field in task_config and not isinstance(task_config[field], expected_type):
                result.add_error(
                    task_key,
                    f"Field '{field}' must be of type {expected_type.__name__}"
                )

        # Validate specific field content
        self._validate_task_description(task_key, task_config.get('description', ''), result)
        self._validate_task_agent(task_key, task_config.get('agent', ''), result)
        self._validate_task_expected_output(task_key, task_config.get('expected_output', ''), result)
        self._validate_task_type(task_key, task_config.get('task_type', 'fast'), result)

        # Validate tools configuration
        if 'tools' in task_config:
            self._validate_task_tools(task_key, task_config['tools'], result)

        # Validate conditions
        if 'conditions' in task_config:
            self._validate_task_conditions(task_key, task_config['conditions'], result)

        # System task specific validations
        if is_system_task:
            self._validate_system_task_specific(task_key, task_config, result)

    def _validate_task_description(self, task_key: str, description: str, result: ValidationResult) -> None:
        """Validate a task's description."""
        if not description or not description.strip():
            result.add_error(task_key, 'Description cannot be empty')
            return

        # Check minimum length - now only as warning, not error
        if len(description.strip()) < 20:
            result.add_warning(f"Task '{task_key}' description is very short (less than 20 characters)")

        # Removed action words/verb requirement validation
        # Description can now be without verbs as per requirements

    def _validate_task_agent(self, task_key: str, agent: str, result: ValidationResult) -> None:
        """Validate a task's agent assignment."""
        if not agent or not agent.strip():
            result.add_error(task_key, 'Agent cannot be empty')
            return

        # Check agent naming convention
        if not re.match(r'^[a-z_]+$', agent):
            result.add_warning(f"Task '{task_key}' agent name should use lowercase with underscores: {agent}")

    def _validate_task_expected_output(self, task_key: str, expected_output: str, result: ValidationResult) -> None:
        """Validate a task's expected output."""
        if not expected_output or not expected_output.strip():
            result.add_error(task_key, 'Expected output cannot be empty')
            return

        # Check for format specifications
        format_keywords = ['json', 'text', 'list', 'dictionary', 'format']
        has_format = any(keyword in expected_output.lower() for keyword in format_keywords)

        if not has_format:
            result.add_warning(f"Task '{task_key}' expected output should specify the output format")

    def _validate_task_type(self, task_key: str, task_type: str, result: ValidationResult) -> None:
        """Validate a task's type."""
        if task_type not in self.valid_task_types:
            result.add_error(task_key, f"Invalid task type: {task_type}. Must be one of {self.valid_task_types}")

    def _validate_task_tools(self, task_key: str, tools: Dict[str, Any], result: ValidationResult) -> None:
        """Validate a task's tools configuration."""
        if not isinstance(tools, dict):
            result.add_error(task_key, 'Tools must be a dictionary')
            return

        for tool_name, tool_config in tools.items():
            # Validate tool name
            if tool_name not in self.valid_tools:
                result.add_warning(f"Task '{task_key}' uses unknown tool: {tool_name}")
                continue

            # Validate tool configuration
            self._validate_tool_config(task_key, tool_name, tool_config, result)

    def _validate_tool_config(self, task_key: str, tool_name: str, tool_config: Dict[str, Any],
                            result: ValidationResult) -> None:
        """Validate a specific tool's configuration."""
        if not isinstance(tool_config, dict):
            result.add_error(task_key, f"Tool '{tool_name}' configuration must be a dictionary")
            return

        # Check for operations
        if 'operations' not in tool_config:
            result.add_error(task_key, f"Tool '{tool_name}' must have 'operations' field")
            return

        operations = tool_config['operations']
        if not isinstance(operations, list):
            result.add_error(task_key, f"Tool '{tool_name}' operations must be a list")
            return

        # Validate each operation
        valid_ops = self.valid_operations.get(tool_name, set())
        for operation in operations:
            if isinstance(operation, str):
                # Simple operation name
                if valid_ops and operation not in valid_ops:
                    result.add_warning(f"Task '{task_key}' tool '{tool_name}' uses unknown operation: {operation}")
            elif isinstance(operation, dict):
                # Operation with conditions
                for op_name, op_config in operation.items():
                    if valid_ops and op_name not in valid_ops:
                        result.add_warning(f"Task '{task_key}' tool '{tool_name}' uses unknown operation: {op_name}")

                    # Validate operation conditions
                    if isinstance(op_config, dict) and 'conditions' in op_config:
                        self._validate_operation_conditions(task_key, tool_name, op_name, op_config['conditions'], result)

    def _validate_operation_conditions(self, task_key: str, tool_name: str, operation: str,
                                     conditions: List[Dict], result: ValidationResult) -> None:
        """Validate operation conditions."""
        if not isinstance(conditions, list):
            result.add_error(task_key, f"Tool '{tool_name}' operation '{operation}' conditions must be a list")
            return

        for condition in conditions:
            if not isinstance(condition, dict):
                result.add_error(task_key, f"Tool '{tool_name}' operation '{operation}' condition must be a dictionary")
                continue

            # Check condition structure
            if 'if' not in condition:
                result.add_error(task_key, f"Tool '{tool_name}' operation '{operation}' condition missing 'if' clause")

            if 'then' not in condition:
                result.add_error(task_key, f"Tool '{tool_name}' operation '{operation}' condition missing 'then' clause")

            # Validate condition expression
            if 'if' in condition:
                self._validate_condition_expression(task_key, condition['if'], result)

    def _validate_condition_expression(self, task_key: str, expression: str, result: ValidationResult) -> None:
        """Validate a condition expression."""
        if not isinstance(expression, str):
            result.add_error(task_key, 'Condition expression must be a string')
            return

        # Check for common condition patterns
        valid_patterns = [
            r'data\.\w+',  # data.property
            r'input\.\w+',  # input.property
            r'resource\.\w+',  # resource.property
            r'model\.\w+',  # model.property
            r'query\.\w+',  # query.property
            r'task\.\w+',  # task.property
            r'\w+\s*(==|!=|>|<|>=|<=)\s*',  # comparison operators
            r'\w+\s+in\s+',  # in operator
            r'\w+\.contains\(',  # contains method
            r'\w+\.includes\(',  # includes method
        ]

        has_valid_pattern = any(re.search(pattern, expression) for pattern in valid_patterns)

        if not has_valid_pattern:
            result.add_warning(f"Task '{task_key}' condition expression may be invalid: {expression}")

    def _validate_task_conditions(self, task_key: str, conditions: List[Dict], result: ValidationResult) -> None:
        """Validate task-level conditions."""
        if not isinstance(conditions, list):
            result.add_error(task_key, 'Conditions must be a list')
            return

        for condition in conditions:
            if not isinstance(condition, dict):
                result.add_error(task_key, 'Each condition must be a dictionary')
                continue

            # Check condition structure
            if 'if' not in condition:
                result.add_error(task_key, 'Condition missing "if" clause')

            if 'then' not in condition:
                result.add_error(task_key, 'Condition missing "then" clause')

            # Validate condition expression
            if 'if' in condition:
                self._validate_condition_expression(task_key, condition['if'], result)

    def _validate_system_task_specific(self, task_key: str, task_config: Dict[str, Any],
                                     result: ValidationResult) -> None:
        """Validate system task specific requirements."""
        task_name = task_key.replace('system_task_', '')

        # Specific validations for different system tasks
        if task_name == 'parse_intent':
            # Should not have tools (relies on NLP)
            if task_config.get('tools'):
                result.add_warning(f"System task '{task_name}' should not use tools (relies on NLP)")

        elif task_name == 'breakdown_subTask':
            # Should not have tools (relies on logic)
            if task_config.get('tools'):
                result.add_warning(f"System task '{task_name}' should not use tools (relies on logic)")

        elif task_name == 'plan_sequence':
            # Should not use tools directly
            if task_config.get('tools'):
                result.add_warning(f"System task '{task_name}' should not use tools directly")

        elif task_name in ['examination', 'acceptance']:
            # Should have research tools
            tools = task_config.get('tools', {})
            if 'research' not in tools:
                result.add_error(task_key, f"System task '{task_name}' should use research tools")

            # Should have conditions
            if 'conditions' not in task_config:
                result.add_error(task_key, f"System task '{task_name}' should have conditions")

    def _validate_category_coverage(self, sub_tasks: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that all task categories are covered by sub-tasks."""
        category_tasks = {category: [] for category in self.valid_categories}

        for task_name, task_config in sub_tasks.items():
            # Infer category from task name
            for category in self.valid_categories:
                if task_name.startswith(f"{category}_"):
                    category_tasks[category].append(task_name)
                    break

        # Check for categories without tasks
        for category, tasks in category_tasks.items():
            if not tasks:
                result.add_warning(f"No sub-tasks found for category: {category}")
            elif len(tasks) < 2:
                result.add_warning(f"Only one sub-task found for category '{category}': {tasks}")

    def _validate_task_consistency(self, system_tasks: Dict[str, Any], sub_tasks: Dict[str, Any],
                                 result: ValidationResult) -> None:
        """Validate consistency between system tasks and sub-tasks."""
        try:
            # Check agent references
            all_agents = set()

            # Collect agents from all tasks
            for task_config in system_tasks.values():
                all_agents.add(task_config.get('agent', ''))

            for task_config in sub_tasks.values():
                all_agents.add(task_config.get('agent', ''))

            # Remove empty agents
            all_agents.discard('')

            # Check for agent naming consistency
            system_agents = {task_config.get('agent', '') for task_config in system_tasks.values()}
            sub_task_agents = {task_config.get('agent', '') for task_config in sub_tasks.values()}

            # System agents should be different from sub-task agents
            overlap = system_agents & sub_task_agents
            if overlap:
                result.add_warning(f"Agents used in both system and sub-tasks: {overlap}")

            # Check tool usage consistency
            all_tools_used = set()

            for task_config in list(system_tasks.values()) + list(sub_tasks.values()):
                tools = task_config.get('tools', {})
                all_tools_used.update(tools.keys())

            # Check for unused valid tools
            unused_tools = self.valid_tools - all_tools_used
            if unused_tools:
                result.add_warning(f"Valid tools not used by any task: {unused_tools}")

        except Exception as e:
            result.add_error('consistency_check', f"Error during consistency validation: {e}")
            logger.error(f"Error validating task consistency: {e}")

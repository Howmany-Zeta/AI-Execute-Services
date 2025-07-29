"""
Configuration Validator

Main validator that coordinates validation of all configuration types
and provides unified validation results.
"""

from typing import Dict, Any, List
import logging
from .prompt_validator import PromptValidator, ValidationResult
from .task_validator import TaskValidator
from .domain_validator import DomainValidator
from .llm_binding_validator import LLMBindingValidator
from .agent_list_validator import AgentListValidator

logger = logging.getLogger(__name__)


class ConfigValidator:
    """
    Main configuration validator that coordinates validation of all configuration types.

    Provides unified validation for prompts, tasks, domains, and cross-configuration
    consistency checks.
    """

    def __init__(self):
        """Initialize the configuration validator."""
        self.prompt_validator = PromptValidator()
        self.task_validator = TaskValidator()
        self.domain_validator = DomainValidator()
        self.llm_binding_validator = LLMBindingValidator()
        self.agent_list_validator = AgentListValidator()

        # Configuration file mappings
        self.config_validators = {
            'prompts.yaml': self._validate_prompts,
            'tasks.yaml': self._validate_tasks,
            'domains.json': self._validate_domains_config,
            'llm_binding.yaml': self._validate_llm_binding,
            'agent_list.yaml': self._validate_agent_list
        }

    def validate_config(self, config_name: str, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a specific configuration file.

        Args:
            config_name: Name of the configuration file
            config_data: Configuration data to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        try:
            if config_name in self.config_validators:
                return self.config_validators[config_name](config_data)
            else:
                result = ValidationResult(is_valid=False, errors={}, warnings=[])
                result.add_error('unknown_config', f"Unknown configuration type: {config_name}")
                return result

        except Exception as e:
            logger.error(f"Error validating configuration {config_name}: {e}")
            result = ValidationResult(is_valid=False, errors={}, warnings=[])
            result.add_error('validation_error', f"Unexpected error during validation: {e}")
            return result

    def _validate_prompts(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate prompts configuration."""
        return self.prompt_validator.validate(config_data)

    def _validate_tasks(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate tasks configuration."""
        return self.task_validator.validate(config_data)

    def _validate_domains_config(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate domains configuration."""
        if 'domains' not in config_data:
            result = ValidationResult(is_valid=False, errors={}, warnings=[])
            result.add_error('structure', 'Domains configuration must contain "domains" field')
            return result

        return self.domain_validator.validate_domains(config_data['domains'])

    def _validate_llm_binding(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate LLM binding configuration."""
        return self.llm_binding_validator.validate(config_data)

    def _validate_agent_list(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate agent list configuration."""
        return self.agent_list_validator.validate(config_data)

    def validate_domains(self, domains: List[str]) -> ValidationResult:
        """
        Validate a list of domains.

        Args:
            domains: List of domain names to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        return self.domain_validator.validate_domains(domains)

    def validate_all_configs(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, ValidationResult]:
        """
        Validate all configurations and check cross-configuration consistency.

        Args:
            configs: Dictionary mapping config names to config data

        Returns:
            Dictionary mapping config names to their validation results
        """
        results = {}

        try:
            # Validate each configuration individually
            for config_name, config_data in configs.items():
                results[config_name] = self.validate_config(config_name, config_data)

            # Perform cross-configuration validation
            cross_validation = self._validate_cross_config_consistency(configs)
            results['cross_validation'] = cross_validation

        except Exception as e:
            logger.error(f"Error during comprehensive validation: {e}")
            error_result = ValidationResult(is_valid=False, errors={}, warnings=[])
            error_result.add_error('validation_error', f"Error during comprehensive validation: {e}")
            results['validation_error'] = error_result

        return results

    def _validate_cross_config_consistency(self, configs: Dict[str, Dict[str, Any]]) -> ValidationResult:
        """
        Validate consistency across different configuration files.

        Args:
            configs: Dictionary mapping config names to config data

        Returns:
            ValidationResult for cross-configuration consistency
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            prompts_config = configs.get('prompts.yaml', {})
            tasks_config = configs.get('tasks.yaml', {})
            domains_config = configs.get('domains.json', {})
            llm_binding_config = configs.get('llm_binding.yaml', {})
            agent_list_config = configs.get('agent_list.yaml', {})

            # Validate agent consistency between prompts and tasks
            self._validate_agent_consistency(prompts_config, tasks_config, result)

            # Validate domain usage consistency
            self._validate_domain_usage_consistency(prompts_config, domains_config, result)

            # Validate tool consistency
            self._validate_tool_consistency(prompts_config, tasks_config, result)

            # Validate role-task alignment
            self._validate_role_task_alignment(prompts_config, tasks_config, result)

            # Validate LLM binding consistency with prompts
            if llm_binding_config and prompts_config:
                self._validate_llm_binding_consistency(llm_binding_config, prompts_config, result)

            # Validate agent list consistency with prompts
            if agent_list_config and prompts_config:
                self._validate_agent_list_consistency(agent_list_config, prompts_config, result)

            # Validate consistency between LLM bindings and agent list
            if llm_binding_config and agent_list_config:
                self._validate_llm_binding_agent_list_consistency(llm_binding_config, agent_list_config, result)

        except Exception as e:
            result.add_error('cross_validation_error', f"Error during cross-validation: {e}")
            logger.error(f"Error during cross-configuration validation: {e}")

        return result

    def _validate_agent_consistency(self, prompts_config: Dict[str, Any],
                                  tasks_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that agents referenced in tasks exist in prompts."""
        if not prompts_config or not tasks_config:
            return

        # Get all defined roles from prompts
        defined_roles = set(prompts_config.get('roles', {}).keys())

        # Get all referenced agents from tasks
        referenced_agents = set()

        for task_section in ['system_tasks', 'sub_tasks']:
            tasks = tasks_config.get(task_section, {})
            for task_config in tasks.values():
                agent = task_config.get('agent')
                if agent:
                    referenced_agents.add(agent)

        # Check for missing role definitions
        missing_roles = referenced_agents - defined_roles
        if missing_roles:
            result.add_error('agent_consistency', f"Tasks reference undefined agents: {missing_roles}")

        # Check for unused role definitions
        unused_roles = defined_roles - referenced_agents
        if unused_roles:
            result.add_warning(f"Defined roles not used by any task: {unused_roles}")

    def _validate_domain_usage_consistency(self, prompts_config: Dict[str, Any],
                                         domains_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that domain references in prompts match available domains."""
        if not prompts_config or not domains_config:
            return

        available_domains = domains_config.get('domains', [])
        if not available_domains:
            return

        # Check domain references in role configurations
        roles = prompts_config.get('roles', {})
        for role_name, role_config in roles.items():
            domain_spec = role_config.get('domain_specialization', '')
            if domain_spec:
                # Validate domain specialization
                domain_validation = self.domain_validator.validate_domain_specialization(
                    domain_spec, available_domains
                )

                if not domain_validation.is_valid:
                    for error_key, error_messages in domain_validation.errors.items():
                        result.add_error(
                            f'role_{role_name}_domain',
                            f"Domain specialization error: {error_messages}"
                        )

                # Add warnings
                for warning in domain_validation.warnings:
                    result.add_warning(f"Role '{role_name}' domain specialization: {warning}")

    def _validate_tool_consistency(self, prompts_config: Dict[str, Any],
                                 tasks_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate tool usage consistency between prompts and tasks."""
        if not prompts_config or not tasks_config:
            return

        # Get tools mentioned in role configurations
        role_tools = set()
        roles = prompts_config.get('roles', {})
        for role_config in roles.values():
            tools = role_config.get('tools', [])
            role_tools.update(tools)

        # Get tools used in task configurations
        task_tools = set()
        for task_section in ['system_tasks', 'sub_tasks']:
            tasks = tasks_config.get(task_section, {})
            for task_config in tasks.values():
                tools = task_config.get('tools', {})
                task_tools.update(tools.keys())

        # Check for tools mentioned in roles but not used in tasks
        unused_role_tools = role_tools - task_tools
        if unused_role_tools:
            result.add_warning(f"Tools mentioned in roles but not used in tasks: {unused_role_tools}")

        # Check for tools used in tasks but not mentioned in roles
        unmentioned_task_tools = task_tools - role_tools
        if unmentioned_task_tools:
            result.add_warning(f"Tools used in tasks but not mentioned in roles: {unmentioned_task_tools}")

    def _validate_role_task_alignment(self, prompts_config: Dict[str, Any],
                                    tasks_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that role capabilities align with task requirements."""
        if not prompts_config or not tasks_config:
            return

        roles = prompts_config.get('roles', {})

        # Check each task's agent assignment
        for task_section in ['system_tasks', 'sub_tasks']:
            tasks = tasks_config.get(task_section, {})
            for task_name, task_config in tasks.items():
                agent = task_config.get('agent')
                if not agent or agent not in roles:
                    continue

                role_config = roles[agent]

                # Check if role tools match task tool requirements
                role_tools = set(role_config.get('tools', []))
                task_tools = set(task_config.get('tools', {}).keys())

                if task_tools and not role_tools:
                    result.add_warning(
                        f"Task '{task_name}' requires tools {task_tools} but agent '{agent}' has no tools defined"
                    )
                elif task_tools and not (task_tools <= role_tools):
                    missing_tools = task_tools - role_tools
                    result.add_warning(
                        f"Task '{task_name}' requires tools {missing_tools} not available to agent '{agent}'"
                    )

                # Check if role goal aligns with task description
                role_goal = role_config.get('goal', '').lower()
                task_desc = task_config.get('description', '').lower()

                # Simple keyword matching for alignment check
                goal_keywords = set(role_goal.split())
                desc_keywords = set(task_desc.split())

                # Remove common words
                common_words = {'the', 'and', 'or', 'to', 'for', 'in', 'on', 'at', 'by', 'with'}
                goal_keywords -= common_words
                desc_keywords -= common_words

                if goal_keywords and desc_keywords:
                    overlap = goal_keywords & desc_keywords
                    if len(overlap) / len(goal_keywords | desc_keywords) < 0.1:
                        result.add_warning(
                            f"Task '{task_name}' description may not align well with agent '{agent}' goal"
                        )

    def get_validation_summary(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary of validation results.

        Args:
            validation_results: Dictionary of validation results

        Returns:
            Summary dictionary with overall status and statistics
        """
        summary = {
            'overall_valid': True,
            'total_errors': 0,
            'total_warnings': 0,
            'config_status': {},
            'error_categories': {},
            'warning_categories': {}
        }

        try:
            for config_name, result in validation_results.items():
                # Update overall status
                if not result.is_valid:
                    summary['overall_valid'] = False

                # Count errors and warnings
                error_count = sum(len(errors) if isinstance(errors, list) else 1
                                for errors in result.errors.values())
                warning_count = len(result.warnings)

                summary['total_errors'] += error_count
                summary['total_warnings'] += warning_count

                # Store config-specific status
                summary['config_status'][config_name] = {
                    'valid': result.is_valid,
                    'errors': error_count,
                    'warnings': warning_count
                }

                # Categorize errors
                for error_key, error_messages in result.errors.items():
                    if error_key not in summary['error_categories']:
                        summary['error_categories'][error_key] = 0
                    summary['error_categories'][error_key] += (
                        len(error_messages) if isinstance(error_messages, list) else 1
                    )

                # Categorize warnings (simple categorization by keywords)
                for warning in result.warnings:
                    category = self._categorize_warning(warning)
                    if category not in summary['warning_categories']:
                        summary['warning_categories'][category] = 0
                    summary['warning_categories'][category] += 1

        except Exception as e:
            logger.error(f"Error generating validation summary: {e}")
            summary['summary_error'] = str(e)

        return summary

    def _categorize_warning(self, warning: str) -> str:
        """Categorize a warning message."""
        warning_lower = warning.lower()

        if 'tool' in warning_lower:
            return 'tools'
        elif 'domain' in warning_lower:
            return 'domains'
        elif 'agent' in warning_lower or 'role' in warning_lower:
            return 'agents'
        elif 'task' in warning_lower:
            return 'tasks'
        elif 'config' in warning_lower:
            return 'configuration'
        else:
            return 'general'


    def _validate_llm_binding_consistency(self, llm_binding_config: Dict[str, Any],
                                        prompts_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate consistency between LLM bindings and prompts configuration."""
        if not llm_binding_config or not prompts_config:
            return

        llm_bindings = llm_binding_config.get('llm_bindings', {})
        prompts_roles = prompts_config.get('roles', {})

        # Use the LLM binding validator for consistency check
        consistency_result = self.llm_binding_validator.validate_consistency_with_prompts(
            llm_bindings, prompts_roles
        )

        # Merge results
        for error_key, error_messages in consistency_result.errors.items():
            for message in error_messages:
                result.add_error(f'llm_binding_{error_key}', message)

        for warning in consistency_result.warnings:
            result.add_warning(f'LLM Binding: {warning}')

    def _validate_agent_list_consistency(self, agent_list_config: Dict[str, Any],
                                       prompts_config: Dict[str, Any], result: ValidationResult) -> None:
        """Validate consistency between agent list and prompts configuration."""
        if not agent_list_config or not prompts_config:
            return

        agent_categories = agent_list_config.get('agent_categories', {})
        prompts_roles = prompts_config.get('roles', {})

        # Use the agent list validator for consistency check
        consistency_result = self.agent_list_validator.validate_consistency_with_prompts(
            agent_categories, prompts_roles
        )

        # Merge results
        for error_key, error_messages in consistency_result.errors.items():
            for message in error_messages:
                result.add_error(f'agent_list_{error_key}', message)

        for warning in consistency_result.warnings:
            result.add_warning(f'Agent List: {warning}')

    def _validate_llm_binding_agent_list_consistency(self, llm_binding_config: Dict[str, Any],
                                                   agent_list_config: Dict[str, Any],
                                                   result: ValidationResult) -> None:
        """Validate consistency between LLM bindings and agent list."""
        if not llm_binding_config or not agent_list_config:
            return

        # Get agents from both configurations
        llm_binding_agents = set(llm_binding_config.get('llm_bindings', {}).keys())

        # Get all agents from agent list categories
        agent_list_agents = set()
        agent_categories = agent_list_config.get('agent_categories', {})
        for category_config in agent_categories.values():
            agents = category_config.get('agents', [])
            agent_list_agents.update(agents)

        # Check for mismatches
        missing_in_bindings = agent_list_agents - llm_binding_agents
        if missing_in_bindings:
            result.add_error(
                'llm_binding_agent_list_consistency',
                f"Agents in agent list missing LLM bindings: {sorted(missing_in_bindings)}"
            )

        missing_in_list = llm_binding_agents - agent_list_agents
        if missing_in_list:
            result.add_error(
                'llm_binding_agent_list_consistency',
                f"Agents with LLM bindings missing from agent list: {sorted(missing_in_list)}"
            )

        # Check total count consistency
        if len(llm_binding_agents) != len(agent_list_agents):
            result.add_warning(
                f"Agent count mismatch: LLM bindings has {len(llm_binding_agents)} agents, "
                f"agent list has {len(agent_list_agents)} agents"
            )

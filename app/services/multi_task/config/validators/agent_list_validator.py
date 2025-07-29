"""
Agent List Configuration Validator

Validates agent_list.yaml configuration files to ensure they contain
valid agent categorization and are consistent with prompts configuration.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from .prompt_validator import ValidationResult
from ..schemas.agent_list_schema import AgentListSchema, AgentCategorySchema

logger = logging.getLogger(__name__)


class AgentListValidator:
    """
    Validator for agent list configuration files.

    Validates the structure and content of agent_list.yaml files to ensure
    they contain valid agent categorization and consistency with prompts.
    """

    def __init__(self):
        """Initialize the agent list validator."""
        # Expected categories based on the system design
        self.expected_categories = {
            'system': {
                'description': 'Core system agents for orchestration and management',
                'min_agents': 5,
                'expected_agents': ['intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director']
            },
            'answer': {
                'description': 'Agents specialized in research and answering questions',
                'min_agents': 2,
                'prefixes': ['researcher_', 'writer_conclusion']
            },
            'collect': {
                'description': 'Agents for data collection and gathering',
                'min_agents': 2,
                'prefixes': ['fieldwork_'],
                'keywords': ['scraper', 'searcher', 'collector']
            },
            'process': {
                'description': 'Agents for data processing and transformation',
                'min_agents': 3,
                'prefixes': ['fieldwork_'],
                'exclude_keywords': ['scraper', 'searcher', 'collector']
            },
            'analyze': {
                'description': 'Agents for data analysis and insights',
                'min_agents': 3,
                'prefixes': ['analyst_']
            },
            'generate': {
                'description': 'Agents for content generation and reporting',
                'min_agents': 3,
                'prefixes': ['writer_'],
                'exclude_keywords': ['conclusion']
            },
            'specialized': {
                'description': 'Specialized agents for specific tasks',
                'min_agents': 0,
                'optional': True
            }
        }

    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate an agent list configuration.

        Args:
            config_data: The agent list configuration data to validate

        Returns:
            ValidationResult containing validation status and any errors
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Validate top-level structure
            self._validate_structure(config_data, result)

            if result.is_valid:
                # Validate metadata
                self._validate_metadata(config_data.get('metadata', {}), result)

                # Validate agent categories
                self._validate_agent_categories(config_data.get('agent_categories', {}), result)

                # Validate cross-category consistency
                self._validate_cross_category_consistency(config_data.get('agent_categories', {}), result)

        except Exception as e:
            result.add_error('validation_error', f"Unexpected error during validation: {e}")
            logger.error(f"Error validating agent list configuration: {e}")

        return result

    def _validate_structure(self, config_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate the top-level structure of the configuration."""
        if not isinstance(config_data, dict):
            result.add_error('structure', 'Configuration must be a dictionary')
            return

        # Check required fields
        required_fields = ['metadata', 'agent_categories']
        for field in required_fields:
            if field not in config_data:
                result.add_error('required_fields', f"Missing required field: {field}")
            elif not isinstance(config_data[field], dict):
                result.add_error('field_types', f"Field '{field}' must be a dictionary")

    def _validate_metadata(self, metadata: Dict[str, Any], result: ValidationResult) -> None:
        """Validate the metadata section."""
        if not metadata:
            result.add_error('metadata', 'Metadata section cannot be empty')
            return

        # Check required metadata fields
        required_fields = ['version', 'description', 'total_agents']
        for field in required_fields:
            if field not in metadata:
                result.add_error('metadata', f"Missing required metadata field: {field}")

        # Validate version format
        version = metadata.get('version', '')
        if version:
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                result.add_error('metadata', 'Version must be in format X.Y.Z')

        # Validate total_agents
        total_agents = metadata.get('total_agents')
        if total_agents is not None:
            if not isinstance(total_agents, int) or total_agents <= 0:
                result.add_error('metadata', 'total_agents must be a positive integer')

        # Validate description
        description = metadata.get('description', '')
        if description and len(description.strip()) < 10:
            result.add_warning('Metadata description is very short (less than 10 characters)')

    def _validate_agent_categories(self, agent_categories: Dict[str, Any], result: ValidationResult) -> None:
        """Validate all agent categories."""
        if not agent_categories:
            result.add_error('agent_categories', 'No agent categories defined')
            return

        # Check for required categories
        missing_categories = set(self.expected_categories.keys()) - set(agent_categories.keys())
        # Remove optional categories from missing check
        missing_categories = {cat for cat in missing_categories
                            if not self.expected_categories[cat].get('optional', False)}

        if missing_categories:
            result.add_error('agent_categories', f"Missing required categories: {sorted(missing_categories)}")

        # Validate each category
        for category_name, category_config in agent_categories.items():
            self._validate_single_category(category_name, category_config, result)

    def _validate_single_category(self, category_name: str, category_config: Dict[str, Any],
                                 result: ValidationResult) -> None:
        """Validate a single agent category."""
        if not isinstance(category_config, dict):
            result.add_error(f'category_{category_name}', 'Category configuration must be a dictionary')
            return

        # Check required fields
        required_fields = ['description', 'agents']
        for field in required_fields:
            if field not in category_config:
                result.add_error(f'category_{category_name}', f"Missing required field: {field}")

        # Validate description
        description = category_config.get('description', '')
        if description and len(description.strip()) < 10:
            result.add_warning(f"Category '{category_name}' description is very short")

        # Validate agents list
        agents = category_config.get('agents', [])
        if not isinstance(agents, list):
            result.add_error(f'category_{category_name}', 'Agents must be a list')
            return

        if not agents:
            result.add_error(f'category_{category_name}', 'Category must contain at least one agent')
            return

        # Check for duplicates within category
        if len(agents) != len(set(agents)):
            duplicates = [agent for agent in agents if agents.count(agent) > 1]
            result.add_error(f'category_{category_name}', f"Duplicate agents: {duplicates}")

        # Validate agent names
        for agent in agents:
            if not isinstance(agent, str):
                result.add_error(f'category_{category_name}', f"Agent name must be a string: {agent}")
            elif not agent.strip():
                result.add_error(f'category_{category_name}', 'Agent name cannot be empty')

        # Validate category-specific requirements
        self._validate_category_requirements(category_name, agents, result)

    def _validate_category_requirements(self, category_name: str, agents: List[str],
                                      result: ValidationResult) -> None:
        """Validate category-specific requirements."""
        if category_name not in self.expected_categories:
            result.add_warning(f"Unknown category: {category_name}")
            return

        category_spec = self.expected_categories[category_name]

        # Check minimum agent count
        min_agents = category_spec.get('min_agents', 0)
        if len(agents) < min_agents:
            result.add_error(
                f'category_{category_name}',
                f"Category requires at least {min_agents} agents, found {len(agents)}"
            )

        # Check expected agents (for system category)
        expected_agents = category_spec.get('expected_agents', [])
        if expected_agents:
            missing_expected = set(expected_agents) - set(agents)
            if missing_expected:
                result.add_error(
                    f'category_{category_name}',
                    f"Missing expected agents: {sorted(missing_expected)}"
                )

        # Check agent name patterns
        prefixes = category_spec.get('prefixes', [])
        keywords = category_spec.get('keywords', [])
        exclude_keywords = category_spec.get('exclude_keywords', [])

        if prefixes or keywords or exclude_keywords:
            for agent in agents:
                # Skip system agents from pattern checking
                if agent in expected_agents:
                    continue

                valid_pattern = False

                # Check prefixes
                if prefixes:
                    if any(agent.startswith(prefix) for prefix in prefixes):
                        valid_pattern = True

                # Check keywords
                if keywords:
                    if any(keyword in agent for keyword in keywords):
                        valid_pattern = True

                # Check exclude keywords
                if exclude_keywords:
                    if any(keyword in agent for keyword in exclude_keywords):
                        valid_pattern = False

                # For categories with specific patterns, warn about non-matching agents
                if (prefixes or keywords) and not valid_pattern:
                    result.add_warning(
                        f"Agent '{agent}' in category '{category_name}' doesn't match expected pattern"
                    )

    def _validate_cross_category_consistency(self, agent_categories: Dict[str, Any],
                                           result: ValidationResult) -> None:
        """Validate consistency across all categories."""
        all_agents = []
        category_mapping = {}

        # Collect all agents and check for cross-category duplicates
        for category_name, category_config in agent_categories.items():
            agents = category_config.get('agents', [])
            for agent in agents:
                if agent in all_agents:
                    existing_category = category_mapping[agent]
                    result.add_error(
                        'cross_category',
                        f"Agent '{agent}' appears in both '{existing_category}' and '{category_name}' categories"
                    )
                else:
                    all_agents.append(agent)
                    category_mapping[agent] = category_name

        # Validate total count consistency
        total_agents_calculated = len(all_agents)

        # Check if metadata total matches calculated total
        # This will be checked when we have access to metadata in the full validation

    def validate_consistency_with_prompts(self, agent_categories: Dict[str, Any],
                                        prompts_roles: Dict[str, Any]) -> ValidationResult:
        """
        Validate consistency between agent list and prompts configuration.

        Args:
            agent_categories: Agent categories configuration
            prompts_roles: Roles from prompts configuration

        Returns:
            ValidationResult for consistency validation
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Get all agents from categories
            list_agents = set()
            for category_config in agent_categories.values():
                agents = category_config.get('agents', [])
                list_agents.update(agents)

            # Get all agents from prompts
            prompt_agents = set(prompts_roles.keys())

            # Check for missing agents in list
            missing_in_list = prompt_agents - list_agents
            if missing_in_list:
                result.add_error(
                    'consistency',
                    f"Agents in prompts.yaml missing from agent list: {sorted(missing_in_list)}"
                )

            # Check for extra agents in list
            extra_in_list = list_agents - prompt_agents
            if extra_in_list:
                result.add_warning(f"Agents in list not found in prompts.yaml: {sorted(extra_in_list)}")

            # Validate categorization accuracy
            self._validate_categorization_accuracy(agent_categories, prompts_roles, result)

        except Exception as e:
            result.add_error('consistency_check', f"Error during consistency validation: {e}")
            logger.error(f"Error validating agent list consistency: {e}")

        return result

    def _validate_categorization_accuracy(self, agent_categories: Dict[str, Any],
                                        prompts_roles: Dict[str, Any], result: ValidationResult) -> None:
        """Validate that agents are categorized correctly based on their roles."""
        # Create reverse mapping from agent to category
        agent_to_category = {}
        for category_name, category_config in agent_categories.items():
            agents = category_config.get('agents', [])
            for agent in agents:
                agent_to_category[agent] = category_name

        # Check categorization based on role goals and names
        miscategorized = []

        for agent_name, role_config in prompts_roles.items():
            if agent_name not in agent_to_category:
                continue  # Already reported as missing

            assigned_category = agent_to_category[agent_name]
            goal = role_config.get('goal', '').lower()

            # Determine expected category based on agent name and goal
            expected_category = self._infer_category_from_role(agent_name, goal)

            if expected_category and expected_category != assigned_category:
                miscategorized.append(f"'{agent_name}' in '{assigned_category}' but seems like '{expected_category}'")

        if miscategorized:
            result.add_warning(f"Potentially miscategorized agents: {miscategorized}")

    def _infer_category_from_role(self, agent_name: str, goal: str) -> Optional[str]:
        """Infer the expected category based on agent name and goal."""
        # System agents
        if agent_name in ['intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director']:
            return 'system'

        # Answer agents
        if agent_name.startswith('researcher_') or 'writer_conclusion' in agent_name:
            return 'answer'

        # Collect agents
        if agent_name.startswith('fieldwork_') and any(keyword in agent_name for keyword in ['scraper', 'searcher', 'collector']):
            return 'collect'

        # Process agents
        if agent_name.startswith('fieldwork_') and not any(keyword in agent_name for keyword in ['scraper', 'searcher', 'collector']):
            return 'process'

        # Analyze agents
        if agent_name.startswith('analyst_'):
            return 'analyze'

        # Generate agents
        if agent_name.startswith('writer_') and 'conclusion' not in agent_name:
            return 'generate'

        # Check goal for additional clues
        if 'analyze' in goal or 'analysis' in goal:
            return 'analyze'
        elif 'generate' in goal or 'create' in goal or 'write' in goal:
            return 'generate'
        elif 'collect' in goal or 'gather' in goal or 'scrape' in goal:
            return 'collect'
        elif 'process' in goal or 'transform' in goal or 'clean' in goal:
            return 'process'
        elif 'research' in goal or 'answer' in goal:
            return 'answer'

        return None

    def get_agent_list_summary(self, agent_categories: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of agent list configuration.

        Args:
            agent_categories: Agent categories configuration

        Returns:
            Summary dictionary with statistics and analysis
        """
        summary = {
            'total_categories': len(agent_categories),
            'total_agents': 0,
            'category_distribution': {},
            'agents_by_category': {},
            'category_percentages': {}
        }

        try:
            all_agents = []

            for category_name, category_config in agent_categories.items():
                agents = category_config.get('agents', [])
                agent_count = len(agents)

                summary['category_distribution'][category_name] = agent_count
                summary['agents_by_category'][category_name] = agents
                summary['total_agents'] += agent_count
                all_agents.extend(agents)

            # Calculate percentages
            if summary['total_agents'] > 0:
                for category_name, count in summary['category_distribution'].items():
                    percentage = round((count / summary['total_agents']) * 100, 1)
                    summary['category_percentages'][category_name] = percentage

            # Check for duplicates across categories
            if len(all_agents) != len(set(all_agents)):
                duplicates = [agent for agent in all_agents if all_agents.count(agent) > 1]
                summary['duplicate_agents'] = list(set(duplicates))

        except Exception as e:
            logger.error(f"Error generating agent list summary: {e}")
            summary['error'] = str(e)

        return summary

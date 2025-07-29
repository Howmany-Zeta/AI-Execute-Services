"""
LLM Binding Configuration Validator

Validates llm_binding.yaml configuration files to ensure they contain
valid LLM provider bindings and are consistent with prompts configuration.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging
from .prompt_validator import ValidationResult
from ..schemas.llm_binding_schema import LLMBindingSchema, LLMBindingEntrySchema

logger = logging.getLogger(__name__)


class LLMBindingValidator:
    """
    Validator for LLM binding configuration files.

    Validates the structure and content of llm_binding.yaml files to ensure
    they contain valid LLM provider bindings and consistency with prompts.
    """

    def __init__(self):
        """Initialize the LLM binding validator."""
        self.valid_providers = {
            "OpenAI", "Vertex", "xAI"
        }

        self.valid_models = {
            "OpenAI": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
            "Vertex": ["gemini-2.5-pro", "gemini-2.5-flash"],
            "xAI": [
                "grok-beta", "grok", "grok-2", "grok-2-vision",
                "grok-3", "grok-3-fast", "grok-3-mini", "grok-3-mini-fast",
                "grok-3-reasoning", "grok-3-reasoning-fast",
                "grok-3-mini-reasoning", "grok-3-mini-reasoning-fast",
                "grok-4-fast", "grok-4-0709" # Add the model that's actually used in the config
            ]
        }

        # Expected agent name patterns
        self.valid_agent_prefixes = [
            'intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director',
            'researcher_', 'writer_', 'fieldwork_', 'analyst_', 'meta_architect',
            'general_'
        ]

    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate an LLM binding configuration.

        Args:
            config_data: The LLM binding configuration data to validate

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

                # Validate LLM bindings
                self._validate_llm_bindings(config_data.get('llm_bindings', {}), result)

        except Exception as e:
            result.add_error('validation_error', f"Unexpected error during validation: {e}")
            logger.error(f"Error validating LLM binding configuration: {e}")

        return result

    def _validate_structure(self, config_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate the top-level structure of the configuration."""
        if not isinstance(config_data, dict):
            result.add_error('structure', 'Configuration must be a dictionary')
            return

        # Check required fields
        required_fields = ['metadata', 'llm_bindings']
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
        required_fields = ['version', 'description']
        for field in required_fields:
            if field not in metadata:
                result.add_error('metadata', f"Missing required metadata field: {field}")

        # Validate version format
        version = metadata.get('version', '')
        if version:
            import re
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                result.add_error('metadata', 'Version must be in format X.Y.Z')

        # Validate description
        description = metadata.get('description', '')
        if description and len(description.strip()) < 10:
            result.add_warning('Metadata description is very short (less than 10 characters)')

    def _validate_llm_bindings(self, llm_bindings: Dict[str, Any], result: ValidationResult) -> None:
        """Validate all LLM bindings."""
        if not llm_bindings:
            result.add_error('llm_bindings', 'No LLM bindings defined')
            return

        # Validate each binding
        for agent_name, binding_config in llm_bindings.items():
            self._validate_single_binding(agent_name, binding_config, result)

        # Analyze provider distribution
        self._analyze_provider_distribution(llm_bindings, result)

    def _validate_single_binding(self, agent_name: str, binding_config: Dict[str, Any],
                                result: ValidationResult) -> None:
        """Validate a single LLM binding."""
        if not isinstance(binding_config, dict):
            result.add_error(f'binding_{agent_name}', 'Binding configuration must be a dictionary')
            return

        # Validate agent name pattern
        if not any(agent_name.startswith(prefix) for prefix in self.valid_agent_prefixes):
            result.add_warning(f"Agent name '{agent_name}' doesn't follow expected naming pattern")

        # Get provider and model
        provider = binding_config.get('llm_provider')
        model = binding_config.get('llm_model')

        # Validate provider-model consistency
        if (provider is None) != (model is None):
            result.add_error(
                f'binding_{agent_name}',
                'llm_provider and llm_model must both be set or both be None for context-aware selection'
            )
            return

        # If provider is set, validate it
        if provider is not None:
            if provider not in self.valid_providers:
                result.add_error(
                    f'binding_{agent_name}',
                    f"Invalid provider '{provider}'. Valid providers: {self.valid_providers}"
                )

            # Validate model for the provider
            if model is not None and provider in self.valid_models:
                valid_models_for_provider = self.valid_models[provider]
                if valid_models_for_provider and model not in valid_models_for_provider:
                    result.add_error(
                        f'binding_{agent_name}',
                        f"Invalid model '{model}' for provider '{provider}'. Valid models: {valid_models_for_provider}"
                    )

        # Check for unexpected fields
        expected_fields = {'llm_provider', 'llm_model'}
        unexpected_fields = set(binding_config.keys()) - expected_fields
        if unexpected_fields:
            result.add_warning(f"Agent '{agent_name}' has unexpected fields: {unexpected_fields}")

    def _analyze_provider_distribution(self, llm_bindings: Dict[str, Any], result: ValidationResult) -> None:
        """Analyze and validate provider distribution."""
        provider_stats = {}
        context_aware_count = 0
        total_agents = len(llm_bindings)

        for agent_name, binding_config in llm_bindings.items():
            provider = binding_config.get('llm_provider')

            if provider is None:
                context_aware_count += 1
            else:
                if provider not in provider_stats:
                    provider_stats[provider] = []
                provider_stats[provider].append(agent_name)

        # Check for balanced distribution
        if provider_stats:
            max_count = max(len(agents) for agents in provider_stats.values())
            min_count = min(len(agents) for agents in provider_stats.values())

            if max_count > min_count * 3:  # If one provider has 3x more agents than another
                result.add_warning('LLM provider distribution is heavily skewed')

        # Check for reasonable context-aware usage
        context_aware_percentage = (context_aware_count / total_agents) * 100 if total_agents > 0 else 0
        if context_aware_percentage > 50:
            result.add_warning(f'High percentage of context-aware agents ({context_aware_percentage:.1f}%)')

        # Log distribution for information
        if provider_stats:
            distribution_info = {provider: len(agents) for provider, agents in provider_stats.items()}
            result.add_warning(f'Provider distribution: {distribution_info}, Context-aware: {context_aware_count}')

    def validate_consistency_with_prompts(self, llm_bindings: Dict[str, Any],
                                        prompts_roles: Dict[str, Any]) -> ValidationResult:
        """
        Validate consistency between LLM bindings and prompts configuration.

        Args:
            llm_bindings: LLM bindings configuration
            prompts_roles: Roles from prompts configuration

        Returns:
            ValidationResult for consistency validation
        """
        result = ValidationResult(is_valid=True, errors={}, warnings=[])

        try:
            # Get agent lists
            binding_agents = set(llm_bindings.keys())
            prompt_agents = set(prompts_roles.keys())

            # Check for missing bindings
            missing_bindings = prompt_agents - binding_agents
            if missing_bindings:
                result.add_error(
                    'consistency',
                    f"Agents in prompts.yaml missing LLM bindings: {sorted(missing_bindings)}"
                )

            # Check for extra bindings
            extra_bindings = binding_agents - prompt_agents
            if extra_bindings:
                result.add_warning(f"LLM bindings for agents not in prompts.yaml: {sorted(extra_bindings)}")

            # Validate strategic provider assignment
            self._validate_strategic_assignment(llm_bindings, prompts_roles, result)

        except Exception as e:
            result.add_error('consistency_check', f"Error during consistency validation: {e}")
            logger.error(f"Error validating LLM binding consistency: {e}")

        return result

    def _validate_strategic_assignment(self, llm_bindings: Dict[str, Any],
                                     prompts_roles: Dict[str, Any], result: ValidationResult) -> None:
        """Validate strategic LLM provider assignments based on agent roles."""
        # Categorize agents by their roles
        system_agents = []
        analysis_agents = []
        generation_agents = []

        for agent_name, role_config in prompts_roles.items():
            if agent_name in ['intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director']:
                system_agents.append(agent_name)
            elif agent_name.startswith('analyst_') or 'analyze' in role_config.get('goal', '').lower():
                analysis_agents.append(agent_name)
            elif agent_name.startswith('writer_') or 'generate' in role_config.get('goal', '').lower():
                generation_agents.append(agent_name)

        # Check strategic assignments
        openai_agents = []
        vertex_agents = []

        for agent_name, binding_config in llm_bindings.items():
            provider = binding_config.get('llm_provider')
            if provider == 'OpenAI':
                openai_agents.append(agent_name)
            elif provider == 'Vertex':
                vertex_agents.append(agent_name)

        # Validate system agents use reliable providers
        system_without_provider = [agent for agent in system_agents
                                 if agent in llm_bindings and llm_bindings[agent].get('llm_provider') is None]
        if system_without_provider:
            result.add_warning(f"System agents using context-aware selection: {system_without_provider}")

        # Check for reasonable distribution
        if len(openai_agents) == 0 and len(vertex_agents) == 0:
            result.add_warning("No agents assigned to major providers (OpenAI/Vertex)")

    def get_binding_summary(self, llm_bindings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of LLM bindings.

        Args:
            llm_bindings: LLM bindings configuration

        Returns:
            Summary dictionary with statistics and analysis
        """
        summary = {
            'total_agents': len(llm_bindings),
            'provider_distribution': {},
            'context_aware_count': 0,
            'agents_by_provider': {},
            'models_used': set()
        }

        try:
            for agent_name, binding_config in llm_bindings.items():
                provider = binding_config.get('llm_provider')
                model = binding_config.get('llm_model')

                if provider is None:
                    summary['context_aware_count'] += 1
                else:
                    # Update provider distribution
                    if provider not in summary['provider_distribution']:
                        summary['provider_distribution'][provider] = 0
                        summary['agents_by_provider'][provider] = []

                    summary['provider_distribution'][provider] += 1
                    summary['agents_by_provider'][provider].append(agent_name)

                    # Track models
                    if model:
                        summary['models_used'].add(f"{provider}:{model}")

            # Convert set to list for JSON serialization
            summary['models_used'] = list(summary['models_used'])

        except Exception as e:
            logger.error(f"Error generating binding summary: {e}")
            summary['error'] = str(e)

        return summary

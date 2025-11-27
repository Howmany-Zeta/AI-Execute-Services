"""
Configuration validation utilities for LLM models.

This module provides validation functions to ensure configuration integrity
and provide helpful error messages.
"""

import logging
from typing import List, Tuple

from aiecs.llm.config.model_config import (
    LLMModelsConfig,
    ProviderConfig,
    ModelConfig,
    ModelCostConfig,
)

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""


def validate_cost_config(cost_config: ModelCostConfig, model_name: str) -> List[str]:
    """
    Validate cost configuration.

    Args:
        cost_config: Cost configuration to validate
        model_name: Name of the model (for error messages)

    Returns:
        List of warning messages (empty if valid)
    """
    warnings = []

    if cost_config.input < 0:
        raise ConfigValidationError(f"Model '{model_name}': Input cost must be non-negative, got {cost_config.input}")

    if cost_config.output < 0:
        raise ConfigValidationError(f"Model '{model_name}': Output cost must be non-negative, got {cost_config.output}")

    # Warn if costs are zero (might be intentional for free tiers or unknown
    # pricing)
    if cost_config.input == 0 and cost_config.output == 0:
        warnings.append(f"Model '{model_name}': Both input and output costs are 0")

    return warnings


def validate_model_config(model_config: ModelConfig) -> List[str]:
    """
    Validate a single model configuration.

    Args:
        model_config: Model configuration to validate

    Returns:
        List of warning messages (empty if valid)

    Raises:
        ConfigValidationError: If validation fails
    """
    warnings = []

    # Validate name
    if not model_config.name or not model_config.name.strip():
        raise ConfigValidationError("Model name cannot be empty")

    # Validate costs
    cost_warnings = validate_cost_config(model_config.costs, model_config.name)
    warnings.extend(cost_warnings)

    # Validate capabilities
    if model_config.capabilities.max_tokens <= 0:
        raise ConfigValidationError(f"Model '{model_config.name}': max_tokens must be positive, " f"got {model_config.capabilities.max_tokens}")

    if model_config.capabilities.context_window <= 0:
        raise ConfigValidationError(f"Model '{model_config.name}': context_window must be positive, " f"got {model_config.capabilities.context_window}")

    # Validate default params
    if not (0.0 <= model_config.default_params.temperature <= 2.0):
        raise ConfigValidationError(f"Model '{model_config.name}': temperature must be between 0.0 and 2.0, " f"got {model_config.default_params.temperature}")

    if model_config.default_params.max_tokens <= 0:
        raise ConfigValidationError(f"Model '{model_config.name}': default max_tokens must be positive, " f"got {model_config.default_params.max_tokens}")

    # Warn if default max_tokens exceeds capability max_tokens
    if model_config.default_params.max_tokens > model_config.capabilities.max_tokens:
        warnings.append(f"Model '{model_config.name}': default max_tokens ({model_config.default_params.max_tokens}) " f"exceeds capability max_tokens ({model_config.capabilities.max_tokens})")

    return warnings


def validate_provider_config(provider_config: ProviderConfig) -> List[str]:
    """
    Validate a provider configuration.

    Args:
        provider_config: Provider configuration to validate

    Returns:
        List of warning messages (empty if valid)

    Raises:
        ConfigValidationError: If validation fails
    """
    warnings = []

    # Validate provider name
    if not provider_config.provider_name or not provider_config.provider_name.strip():
        raise ConfigValidationError("Provider name cannot be empty")

    # Validate models list
    if not provider_config.models:
        raise ConfigValidationError(f"Provider '{provider_config.provider_name}': Must have at least one model")

    # Validate default model exists
    model_names = provider_config.get_model_names()
    if provider_config.default_model not in model_names:
        raise ConfigValidationError(f"Provider '{provider_config.provider_name}': Default model '{provider_config.default_model}' " f"not found in models list: {model_names}")

    # Validate each model
    for model in provider_config.models:
        model_warnings = validate_model_config(model)
        warnings.extend(model_warnings)

    # Check for duplicate model names
    if len(model_names) != len(set(model_names)):
        duplicates = [name for name in model_names if model_names.count(name) > 1]
        raise ConfigValidationError(f"Provider '{provider_config.provider_name}': Duplicate model names found: {set(duplicates)}")

    # Validate model mappings if present
    if provider_config.model_mappings:
        for alias, target in provider_config.model_mappings.items():
            if target not in model_names:
                raise ConfigValidationError(f"Provider '{provider_config.provider_name}': Model mapping alias '{alias}' " f"points to non-existent model '{target}'. Available models: {model_names}")

            # Warn if alias is the same as target
            if alias == target:
                warnings.append(f"Provider '{provider_config.provider_name}': Model mapping has redundant entry " f"'{alias}' -> '{target}'")

    return warnings


def validate_llm_config(config: LLMModelsConfig) -> Tuple[bool, List[str]]:
    """
    Validate the entire LLM configuration.

    Args:
        config: Complete LLM configuration to validate

    Returns:
        Tuple of (is_valid, warnings_list)

    Raises:
        ConfigValidationError: If validation fails critically
    """
    warnings = []

    # Validate providers exist
    if not config.providers:
        raise ConfigValidationError("Configuration must have at least one provider")

    # Validate each provider
    for provider_name, provider_config in config.providers.items():
        try:
            provider_warnings = validate_provider_config(provider_config)
            warnings.extend(provider_warnings)
        except ConfigValidationError as e:
            raise ConfigValidationError(f"Provider '{provider_name}': {e}")

    # Log warnings
    if warnings:
        logger.warning(f"Configuration validation completed with {len(warnings)} warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    else:
        logger.info("Configuration validation completed successfully with no warnings")

    return True, warnings


def validate_config_file(config_path: str) -> Tuple[bool, List[str]]:
    """
    Validate a configuration file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Tuple of (is_valid, warnings_list)

    Raises:
        ConfigValidationError: If validation fails
        FileNotFoundError: If file doesn't exist
    """
    from aiecs.llm.config.config_loader import LLMConfigLoader
    from pathlib import Path

    loader = LLMConfigLoader()
    config_path_obj: Path | None = Path(config_path) if config_path else None
    config = loader.load_config(config_path_obj)

    return validate_llm_config(config)

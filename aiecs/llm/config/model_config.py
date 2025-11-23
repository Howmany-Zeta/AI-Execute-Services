"""
Pydantic models for LLM configuration management.

This module defines the configuration schema for all LLM providers and models,
enabling centralized, type-safe configuration management.
"""

from typing import Dict, Optional, List
from pydantic import BaseModel, Field, field_validator


class ModelCostConfig(BaseModel):
    """Token cost configuration for a model"""

    input: float = Field(ge=0, description="Cost per 1K input tokens in USD")
    output: float = Field(ge=0, description="Cost per 1K output tokens in USD")

    @field_validator("input", "output")
    @classmethod
    def validate_positive(cls, v: float) -> float:
        """Ensure costs are non-negative"""
        if v < 0:
            raise ValueError("Cost must be non-negative")
        return v


class ModelCapabilities(BaseModel):
    """Capabilities and limits for a model"""

    streaming: bool = Field(default=True, description="Whether the model supports streaming")
    vision: bool = Field(
        default=False,
        description="Whether the model supports vision/image input",
    )
    function_calling: bool = Field(
        default=False,
        description="Whether the model supports function calling",
    )
    max_tokens: int = Field(default=8192, ge=1, description="Maximum output tokens")
    context_window: int = Field(default=128000, ge=1, description="Maximum context window size")


class ModelDefaultParams(BaseModel):
    """Default parameters for model inference"""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    max_tokens: int = Field(default=8192, ge=1, description="Default max output tokens")
    top_p: float = Field(default=0.95, ge=0.0, le=1.0, description="Default top_p")
    top_k: int = Field(default=40, ge=0, description="Default top_k")


class ModelConfig(BaseModel):
    """Complete configuration for a single model"""

    name: str = Field(description="Model identifier")
    display_name: Optional[str] = Field(default=None, description="Human-readable model name")
    costs: ModelCostConfig = Field(description="Token cost configuration")
    capabilities: ModelCapabilities = Field(default_factory=ModelCapabilities, description="Model capabilities")
    default_params: ModelDefaultParams = Field(default_factory=ModelDefaultParams, description="Default parameters")
    description: Optional[str] = Field(default=None, description="Model description")

    def __init__(self, **data):
        super().__init__(**data)
        # Set display_name to name if not provided
        if self.display_name is None:
            self.display_name = self.name


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider"""

    provider_name: str = Field(description="Provider identifier")
    default_model: str = Field(description="Default model for this provider")
    models: List[ModelConfig] = Field(description="List of available models")
    model_mappings: Optional[Dict[str, str]] = Field(
        default=None,
        description="Model name aliases (e.g., 'Grok 4' -> 'grok-4')",
    )

    @field_validator("models")
    @classmethod
    def validate_models_not_empty(cls, v: List[ModelConfig]) -> List[ModelConfig]:
        """Ensure at least one model is configured"""
        if not v:
            raise ValueError("Provider must have at least one model configured")
        return v

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model"""
        # First, check if this is an alias
        if self.model_mappings and model_name in self.model_mappings:
            model_name = self.model_mappings[model_name]

        # Find the model configuration
        for model in self.models:
            if model.name == model_name:
                return model
        return None

    def get_model_names(self) -> List[str]:
        """Get list of all model names"""
        return [model.name for model in self.models]

    def get_all_model_names_with_aliases(self) -> List[str]:
        """Get list of all model names including aliases"""
        names = self.get_model_names()
        if self.model_mappings:
            names.extend(list(self.model_mappings.keys()))
        return names


class LLMModelsConfig(BaseModel):
    """Root configuration containing all providers"""

    providers: Dict[str, ProviderConfig] = Field(description="Provider configurations keyed by provider name")

    @field_validator("providers")
    @classmethod
    def validate_providers_not_empty(cls, v: Dict[str, ProviderConfig]) -> Dict[str, ProviderConfig]:
        """Ensure at least one provider is configured"""
        if not v:
            raise ValueError("At least one provider must be configured")
        return v

    def get_provider_config(self, provider_name: str) -> Optional[ProviderConfig]:
        """Get configuration for a specific provider"""
        # Normalize provider name (case-insensitive lookup)
        provider_name_lower = provider_name.lower()
        for key, config in self.providers.items():
            if key.lower() == provider_name_lower:
                return config
        return None

    def get_model_config(self, provider_name: str, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a specific model from a provider"""
        provider_config = self.get_provider_config(provider_name)
        if provider_config:
            return provider_config.get_model_config(model_name)
        return None

    def get_provider_names(self) -> List[str]:
        """Get list of all provider names"""
        return list(self.providers.keys())

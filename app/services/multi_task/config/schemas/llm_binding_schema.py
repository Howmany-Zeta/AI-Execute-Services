"""
LLM Binding Schema

Pydantic schema definitions for llm_binding.yaml configuration validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class LLMBindingEntrySchema(BaseModel):
    """Schema for individual LLM binding configuration."""

    llm_provider: Optional[str] = Field(None, description="LLM provider name (OpenAI, Vertex, etc.)")
    llm_model: Optional[str] = Field(None, description="Specific model name")

    @validator('llm_provider')
    def validate_provider(cls, v):
        """Validate LLM provider."""
        if v is None:
            return v

        valid_providers = ["OpenAI", "Vertex", "xAI"]
        if v not in valid_providers:
            raise ValueError(f"Invalid provider: {v}. Valid providers: {valid_providers}")
        return v

    @validator('llm_model')
    def validate_model(cls, v, values):
        """Validate LLM model based on provider."""
        if v is None:
            return v

        provider = values.get('llm_provider')
        if provider is None:
            raise ValueError("llm_model cannot be set without llm_provider")

        valid_models = {
            "OpenAI": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini"],
            "Vertex": ["gemini-2.5-pro", "gemini-2.5-flash"],
            "xAI": [
                "grok-beta", "grok", "grok-2", "grok-2-vision",
                "grok-3", "grok-3-fast", "grok-3-mini", "grok-3-mini-fast",
                "grok-3-reasoning", "grok-3-reasoning-fast",
                "grok-3-mini-reasoning", "grok-3-mini-reasoning-fast"
            ]
        }

        if provider in valid_models and valid_models[provider]:
            if v not in valid_models[provider]:
                raise ValueError(f"Invalid model '{v}' for provider '{provider}'. Valid models: {valid_models[provider]}")

        return v

    @validator('llm_model', always=True)
    def validate_provider_model_consistency(cls, v, values):
        """Ensure provider and model are both set or both None."""
        provider = values.get('llm_provider')

        # Both should be set or both should be None for context-aware selection
        if (provider is None) != (v is None):
            raise ValueError("llm_provider and llm_model must both be set or both be None")

        return v

    class Config:
        """Pydantic configuration."""
        extra = "forbid"


class LLMBindingSchema(BaseModel):
    """Schema for the complete llm_binding.yaml configuration."""

    metadata: Dict[str, Any] = Field(..., description="Configuration metadata")
    llm_bindings: Dict[str, LLMBindingEntrySchema] = Field(..., description="Agent to LLM bindings")

    @validator('metadata')
    def validate_metadata(cls, v):
        """Validate metadata structure."""
        required_fields = ['version', 'description']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required metadata field: {field}")

        # Validate version format
        version = v.get('version', '')
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            raise ValueError("Version must be in format X.Y.Z")

        return v

    @validator('llm_bindings')
    def validate_bindings(cls, v):
        """Validate LLM bindings structure."""
        if not v:
            raise ValueError("At least one LLM binding must be defined")

        # Check for valid agent name patterns
        valid_prefixes = [
            'intent_parser', 'task_decomposer', 'supervisor', 'planner', 'director',
            'researcher_', 'writer_', 'fieldwork_', 'analyst_', 'meta_architect',
            'general_'
        ]

        for agent_name in v.keys():
            if not any(agent_name.startswith(prefix) or agent_name == prefix for prefix in valid_prefixes):
                raise ValueError(f"Agent name '{agent_name}' doesn't follow expected naming pattern")

        return v

    @classmethod
    def validate_agent_coverage(cls, bindings: Dict[str, LLMBindingEntrySchema],
                               expected_agents: List[str]) -> List[str]:
        """Validate that all expected agents have LLM bindings."""
        warnings = []

        # Check for missing agents
        missing_agents = set(expected_agents) - set(bindings.keys())
        if missing_agents:
            warnings.append(f"Missing LLM bindings for agents: {sorted(missing_agents)}")

        # Check for extra agents
        extra_agents = set(bindings.keys()) - set(expected_agents)
        if extra_agents:
            warnings.append(f"LLM bindings for unknown agents: {sorted(extra_agents)}")

        return warnings

    @classmethod
    def analyze_provider_distribution(cls, bindings: Dict[str, LLMBindingEntrySchema]) -> Dict[str, Any]:
        """Analyze the distribution of LLM providers across agents."""
        provider_stats = {}
        context_aware_count = 0

        for agent_name, binding in bindings.items():
            if binding.llm_provider is None:
                context_aware_count += 1
            else:
                if binding.llm_provider not in provider_stats:
                    provider_stats[binding.llm_provider] = []
                provider_stats[binding.llm_provider].append(agent_name)

        return {
            'provider_distribution': {k: len(v) for k, v in provider_stats.items()},
            'provider_agents': provider_stats,
            'context_aware_agents': context_aware_count,
            'total_agents': len(bindings)
        }

    class Config:
        """Pydantic configuration."""
        extra = "forbid"
        validate_assignment = True


class LLMBindingValidationSchema(BaseModel):
    """Schema for LLM binding validation results."""

    is_valid: bool = Field(..., description="Whether the configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    agent_count: int = Field(..., description="Number of agents with LLM bindings")
    provider_distribution: Dict[str, int] = Field(default_factory=dict, description="Distribution of agents by provider")
    context_aware_count: int = Field(default=0, description="Number of agents using context-aware selection")
    missing_agents: List[str] = Field(default_factory=list, description="Agents missing from bindings")
    extra_agents: List[str] = Field(default_factory=list, description="Unknown agents in bindings")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")

    class Config:
        """Pydantic configuration."""
        extra = "allow"


class LLMProviderStatsSchema(BaseModel):
    """Schema for LLM provider usage statistics."""

    provider_name: str = Field(..., description="Name of the LLM provider")
    agent_count: int = Field(..., description="Number of agents using this provider")
    agents: List[str] = Field(..., description="List of agents using this provider")
    models_used: List[str] = Field(default_factory=list, description="Models used by this provider")

    class Config:
        """Pydantic configuration."""
        extra = "allow"

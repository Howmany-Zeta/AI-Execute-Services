"""
Agent List Schema

Pydantic schema definitions for agent_list.yaml configuration validation.
"""

from pydantic import field_validator, model_validator, ConfigDict, BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class AgentCategorySchema(BaseModel):
    """Schema for agent category configuration."""

    description: str = Field(..., description="Description of the agent category")
    agents: List[str] = Field(..., description="List of agent names in this category")

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Validate category description."""
        if not v.strip():
            raise ValueError("Category description cannot be empty")
        return v.strip()

    @field_validator('agents')
    @classmethod
    def validate_agents(cls, v):
        """Validate agents list."""
        if not v:
            raise ValueError("Category must contain at least one agent")

        # Check for duplicates
        if len(v) != len(set(v)):
            duplicates = [agent for agent in v if v.count(agent) > 1]
            raise ValueError(f"Duplicate agents found: {duplicates}")

        # Validate agent name format
        for agent in v:
            if not isinstance(agent, str):
                raise ValueError(f"Agent name must be a string: {agent}")
            if not agent.strip():
                raise ValueError("Agent name cannot be empty")

        return [agent.strip() for agent in v]
    model_config = ConfigDict(extra="forbid")


class AgentListSchema(BaseModel):
    """Schema for the complete agent_list.yaml configuration."""

    metadata: Dict[str, Any] = Field(..., description="Configuration metadata")
    agent_categories: Dict[str, AgentCategorySchema] = Field(..., description="Agent categories and their agents")

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v):
        """Validate metadata structure."""
        required_fields = ['version', 'description', 'total_agents']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required metadata field: {field}")

        # Validate version format
        version = v.get('version', '')
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            raise ValueError("Version must be in format X.Y.Z")

        # Validate total_agents is a positive integer
        total_agents = v.get('total_agents')
        if not isinstance(total_agents, int) or total_agents <= 0:
            raise ValueError("total_agents must be a positive integer")

        return v

    @field_validator('agent_categories')
    @classmethod
    def validate_categories(cls, v):
        """Validate agent categories structure."""
        if not v:
            raise ValueError("At least one agent category must be defined")

        # Expected categories based on the YAML structure
        expected_categories = ['system', 'answer', 'collect', 'process', 'analyze', 'generate', 'specialized']

        # Check for required categories
        missing_categories = set(expected_categories) - set(v.keys())
        if missing_categories:
            raise ValueError(f"Missing required categories: {sorted(missing_categories)}")

        return v

    @field_validator('agent_categories')
    @classmethod
    def validate_agent_uniqueness(cls, v):
        """Ensure no agent appears in multiple categories."""
        all_agents = []
        category_mapping = {}

        for category_name, category in v.items():
            for agent in category.agents:
                if agent in all_agents:
                    existing_category = category_mapping[agent]
                    raise ValueError(f"Agent '{agent}' appears in both '{existing_category}' and '{category_name}' categories")
                all_agents.append(agent)
                category_mapping[agent] = category_name

        return v

    @model_validator(mode='after')
    def validate_total_count(self) -> 'AgentListSchema':
        """Validate that total agent count matches metadata."""
        metadata = self.metadata or {}
        agent_categories = self.agent_categories or {}

        expected_total = metadata.get('total_agents', 0)
        actual_total = sum(len(category.agents) for category in agent_categories.values())

        if actual_total != expected_total:
            raise ValueError(f"Total agent count mismatch: metadata says {expected_total}, but found {actual_total}")

        return self

    def get_all_agents(self) -> List[str]:
        """Get a flat list of all agents across all categories."""
        all_agents = []
        for category in self.agent_categories.values():
            all_agents.extend(category.agents)
        return all_agents

    def get_agent_category(self, agent_name: str) -> Optional[str]:
        """Get the category for a specific agent."""
        for category_name, category in self.agent_categories.items():
            if agent_name in category.agents:
                return category_name
        return None

    @classmethod
    def validate_agent_consistency(cls, agent_list: List[str],
                                 expected_agents: List[str]) -> List[str]:
        """Validate consistency with expected agents from other configurations."""
        warnings = []

        # Check for missing agents
        missing_agents = set(expected_agents) - set(agent_list)
        if missing_agents:
            warnings.append(f"Missing agents from list: {sorted(missing_agents)}")

        # Check for extra agents
        extra_agents = set(agent_list) - set(expected_agents)
        if extra_agents:
            warnings.append(f"Extra agents in list: {sorted(extra_agents)}")

        return warnings

    @classmethod
    def analyze_category_distribution(cls, categories: Dict[str, AgentCategorySchema]) -> Dict[str, Any]:
        """Analyze the distribution of agents across categories."""
        distribution = {}
        total_agents = 0

        for category_name, category in categories.items():
            agent_count = len(category.agents)
            distribution[category_name] = {
                'count': agent_count,
                'agents': category.agents,
                'description': category.description
            }
            total_agents += agent_count

        # Calculate percentages
        for category_name in distribution:
            distribution[category_name]['percentage'] = round(
                (distribution[category_name]['count'] / total_agents) * 100, 1
            ) if total_agents > 0 else 0

        return {
            'category_distribution': distribution,
            'total_agents': total_agents,
            'category_count': len(categories)
        }
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class AgentListValidationSchema(BaseModel):
    """Schema for agent list validation results."""

    is_valid: bool = Field(..., description="Whether the configuration is valid")
    errors: Dict[str, List[str]] = Field(default_factory=dict, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    total_agents: int = Field(..., description="Total number of agents")
    category_count: int = Field(..., description="Number of categories")
    category_distribution: Dict[str, int] = Field(default_factory=dict, description="Agent count by category")
    missing_agents: List[str] = Field(default_factory=list, description="Agents missing from list")
    extra_agents: List[str] = Field(default_factory=list, description="Extra agents in list")
    duplicate_agents: List[str] = Field(default_factory=list, description="Agents appearing in multiple categories")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")
    model_config = ConfigDict(extra="allow")


class AgentCategoryStatsSchema(BaseModel):
    """Schema for agent category statistics."""

    category_name: str = Field(..., description="Name of the category")
    agent_count: int = Field(..., description="Number of agents in this category")
    agents: List[str] = Field(..., description="List of agents in this category")
    description: str = Field(..., description="Category description")
    percentage: float = Field(..., description="Percentage of total agents")
    model_config = ConfigDict(extra="allow")

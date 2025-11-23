"""
Role-Based Configuration

Load agent configuration from role templates.
"""

import logging
import yaml  # type: ignore[import-untyped]
from typing import Dict, Any, Optional
from pathlib import Path

from ..models import AgentConfiguration

logger = logging.getLogger(__name__)


class RoleConfiguration:
    """
    Manages role-based agent configurations.

    Example:
        role_config = RoleConfiguration.load_from_file("roles/developer.yaml")
        agent_config = role_config.to_agent_config()
    """

    def __init__(
        self,
        role_name: str,
        goal: Optional[str] = None,
        backstory: Optional[str] = None,
        domain_knowledge: Optional[str] = None,
        llm_model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None,
        **kwargs,
    ):
        """
        Initialize role configuration.

        Args:
            role_name: Role name
            goal: Agent goal
            backstory: Agent backstory
            domain_knowledge: Domain knowledge
            llm_model: LLM model to use
            temperature: LLM temperature
            max_tokens: Max tokens
            tools: List of tool names
            **kwargs: Additional configuration
        """
        self.role_name = role_name
        self.goal = goal
        self.backstory = backstory
        self.domain_knowledge = domain_knowledge
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tools = tools or []
        self.additional_config = kwargs

    def to_agent_config(self) -> AgentConfiguration:
        """
        Convert to AgentConfiguration.

        Returns:
            AgentConfiguration instance
        """
        return AgentConfiguration(  # type: ignore[call-arg]
            goal=self.goal,
            backstory=self.backstory,
            domain_knowledge=self.domain_knowledge,
            llm_model=self.llm_model,
            temperature=self.temperature,
            max_tokens=self.max_tokens if self.max_tokens is not None else 4096,  # type: ignore[arg-type]
            **self.additional_config,
        )

    @classmethod
    def load_from_file(cls, file_path: str) -> "RoleConfiguration":
        """
        Load role configuration from YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            RoleConfiguration instance
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Role configuration file not found: {file_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded role configuration from {file_path}")
        return cls(**data)

    @classmethod
    def load_from_dict(cls, data: Dict[str, Any]) -> "RoleConfiguration":
        """
        Load role configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            RoleConfiguration instance
        """
        return cls(**data)

    def merge_with(self, other: "RoleConfiguration") -> "RoleConfiguration":
        """
        Merge with another configuration (other takes precedence).

        Args:
            other: Other configuration

        Returns:
            New merged RoleConfiguration
        """
        merged_data = {
            "role_name": other.role_name or self.role_name,
            "goal": other.goal or self.goal,
            "backstory": other.backstory or self.backstory,
            "domain_knowledge": other.domain_knowledge or self.domain_knowledge,
            "llm_model": other.llm_model or self.llm_model,
            "temperature": (other.temperature if other.temperature != 0.7 else self.temperature),
            "max_tokens": other.max_tokens or self.max_tokens,
            "tools": other.tools if other.tools else self.tools,
            **{**self.additional_config, **other.additional_config},
        }
        return RoleConfiguration(**merged_data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role_name": self.role_name,
            "goal": self.goal,
            "backstory": self.backstory,
            "domain_knowledge": self.domain_knowledge,
            "llm_model": self.llm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": self.tools,
            **self.additional_config,
        }


def load_role_config(role_name: str, base_path: str = "./agent_roles") -> RoleConfiguration:
    """
    Load role configuration by name.

    Args:
        role_name: Role name
        base_path: Base directory for role configurations

    Returns:
        RoleConfiguration instance
    """
    file_path = Path(base_path) / f"{role_name}.yaml"
    return RoleConfiguration.load_from_file(str(file_path))


# Predefined role templates
ROLE_TEMPLATES = {
    "developer": {
        "role_name": "developer",
        "goal": "Write clean, efficient, and maintainable code",
        "backstory": ("You are an experienced software developer with expertise in " "multiple programming languages and best practices"),
        "domain_knowledge": "Software development, design patterns, testing, debugging",
        "temperature": 0.3,
    },
    "researcher": {
        "role_name": "researcher",
        "goal": "Gather, analyze, and synthesize information from various sources",
        "backstory": "You are a meticulous researcher skilled at finding and evaluating information",
        "domain_knowledge": "Research methodologies, critical analysis, information synthesis",
        "temperature": 0.5,
    },
    "analyst": {
        "role_name": "analyst",
        "goal": "Analyze data and provide actionable insights",
        "backstory": "You are a data analyst with strong analytical and problem-solving skills",
        "domain_knowledge": "Data analysis, statistics, visualization, interpretation",
        "temperature": 0.4,
    },
    "creative": {
        "role_name": "creative",
        "goal": "Generate creative and innovative ideas",
        "backstory": "You are a creative thinker with a knack for innovative solutions",
        "domain_knowledge": "Creative thinking, brainstorming, innovation",
        "temperature": 0.9,
    },
}


def get_role_template(role_name: str) -> RoleConfiguration:
    """
    Get predefined role template.

    Args:
        role_name: Role name

    Returns:
        RoleConfiguration instance
    """
    if role_name not in ROLE_TEMPLATES:
        raise ValueError(f"Unknown role template: {role_name}")

    return RoleConfiguration.load_from_dict(ROLE_TEMPLATES[role_name])

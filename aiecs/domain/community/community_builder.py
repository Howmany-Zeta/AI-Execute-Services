"""
Community Builder

Provides a fluent interface for building communities with preset templates
and customizable configuration.
"""

import logging
from typing import Dict, List, Any, Optional

from .models.community_models import GovernanceType
from .community_integration import CommunityIntegration

logger = logging.getLogger(__name__)


class CommunityBuilder:
    """
    Fluent interface builder for creating communities.

    Provides an intuitive way to configure and create communities
    with method chaining.
    """

    def __init__(self, integration: CommunityIntegration):
        """
        Initialize the community builder.

        Args:
            integration: Community integration instance
        """
        self.integration = integration
        self._reset()

    def _reset(self) -> None:
        """Reset builder state."""
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._governance_type: GovernanceType = GovernanceType.DEMOCRATIC
        self._agent_roles: List[str] = []
        self._creator_agent_id: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
        self._is_temporary: bool = False
        self._duration_minutes: int = 60
        self._auto_cleanup: bool = True
        self._template: Optional[str] = None
        self._template_config: Dict[str, Any] = {}

    def with_name(self, name: str) -> "CommunityBuilder":
        """
        Set the community name.

        Args:
            name: Name of the community

        Returns:
            Self for chaining
        """
        self._name = name
        return self

    def with_description(self, description: str) -> "CommunityBuilder":
        """
        Set the community description.

        Args:
            description: Description of the community

        Returns:
            Self for chaining
        """
        self._description = description
        return self

    def with_governance(self, governance_type: GovernanceType) -> "CommunityBuilder":
        """
        Set the governance type.

        Args:
            governance_type: Type of governance

        Returns:
            Self for chaining
        """
        self._governance_type = governance_type
        return self

    def add_agent_role(self, role: str) -> "CommunityBuilder":
        """
        Add an agent role to the community.

        Args:
            role: Agent role to add

        Returns:
            Self for chaining
        """
        if role not in self._agent_roles:
            self._agent_roles.append(role)
        return self

    def add_agent_roles(self, roles: List[str]) -> "CommunityBuilder":
        """
        Add multiple agent roles.

        Args:
            roles: List of agent roles

        Returns:
            Self for chaining
        """
        for role in roles:
            self.add_agent_role(role)
        return self

    def with_creator(self, agent_id: str) -> "CommunityBuilder":
        """
        Set the creator agent.

        Args:
            agent_id: ID of the creating agent

        Returns:
            Self for chaining
        """
        self._creator_agent_id = agent_id
        return self

    def with_duration(self, minutes: int, auto_cleanup: bool = True) -> "CommunityBuilder":
        """
        Make the community temporary with a duration.

        Args:
            minutes: Duration in minutes
            auto_cleanup: Whether to automatically cleanup after duration

        Returns:
            Self for chaining
        """
        self._is_temporary = True
        self._duration_minutes = minutes
        self._auto_cleanup = auto_cleanup
        return self

    def with_metadata(self, key: str, value: Any) -> "CommunityBuilder":
        """
        Add metadata to the community.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for chaining
        """
        self._metadata[key] = value
        return self

    def use_template(self, template: str, **config) -> "CommunityBuilder":
        """
        Use a preset template.

        Args:
            template: Template name (research, development, support, creative)
            **config: Template configuration

        Returns:
            Self for chaining
        """
        self._template = template
        self._template_config = config
        return self

    async def build(self) -> str:
        """
        Build and create the community.

        Returns:
            Community ID
        """
        # Apply template if specified
        if self._template:
            await self._apply_template(self._template, self._template_config)

        # Validate required fields
        if not self._name:
            raise ValueError("Community name is required")

        # Create community based on configuration
        if self._is_temporary:
            community_id = await self.integration.create_temporary_community(
                name=self._name,
                description=self._description or f"Community: {self._name}",
                agent_roles=self._agent_roles,
                duration_minutes=self._duration_minutes,
                auto_cleanup=self._auto_cleanup,
                governance_type=self._governance_type,
                creator_agent_id=self._creator_agent_id,
            )
        else:
            community_id = await self.integration.create_agent_community(
                name=self._name,
                description=self._description or f"Community: {self._name}",
                agent_roles=self._agent_roles,
                governance_type=self._governance_type,
                creator_agent_id=self._creator_agent_id,
            )

        # Apply metadata
        if self._metadata:
            community = self.integration.community_manager.communities[community_id]
            community.metadata.update(self._metadata)

        logger.info(f"Built community: {self._name} ({community_id})")

        # Reset builder for reuse
        self._reset()

        return community_id

    async def _apply_template(self, template: str, config: Dict[str, Any]) -> None:
        """Apply a preset template configuration."""
        if template == "research":
            await self._apply_research_template(config)
        elif template == "development":
            await self._apply_development_template(config)
        elif template == "support":
            await self._apply_support_template(config)
        elif template == "creative":
            await self._apply_creative_template(config)
        else:
            logger.warning(f"Unknown template: {template}")

    async def _apply_research_template(self, config: Dict[str, Any]) -> None:
        """Apply research community template."""
        self.with_governance(GovernanceType.CONSENSUS)

        # Default research roles
        default_roles = ["researcher", "analyst", "writer", "reviewer"]
        self.add_agent_roles(config.get("roles", default_roles))

        # Research-specific metadata
        if "topic" in config:
            self.with_metadata("research_topic", config["topic"])
        if "questions" in config:
            self.with_metadata("research_questions", config["questions"])
        if "methodologies" in config:
            self.with_metadata("methodologies", config["methodologies"])

        self.with_metadata("type", "research")
        logger.debug("Applied research template")

    async def _apply_development_template(self, config: Dict[str, Any]) -> None:
        """Apply development/project community template."""
        self.with_governance(GovernanceType.HIERARCHICAL)

        # Default development roles
        default_roles = ["architect", "developer", "tester", "reviewer"]
        self.add_agent_roles(config.get("roles", default_roles))

        # Development-specific metadata
        if "project_name" in config:
            self.with_metadata("project_name", config["project_name"])
        if "goal" in config:
            self.with_metadata("project_goal", config["goal"])
        if "deadline" in config:
            self.with_metadata("project_deadline", config["deadline"])
        if "tech_stack" in config:
            self.with_metadata("tech_stack", config["tech_stack"])

        self.with_metadata("type", "development")
        logger.debug("Applied development template")

    async def _apply_support_template(self, config: Dict[str, Any]) -> None:
        """Apply support community template."""
        self.with_governance(GovernanceType.DEMOCRATIC)

        # Default support roles
        default_roles = ["support_agent", "specialist", "escalation_handler"]
        self.add_agent_roles(config.get("roles", default_roles))

        # Support-specific metadata
        if "support_level" in config:
            self.with_metadata("support_level", config["support_level"])
        if "coverage_hours" in config:
            self.with_metadata("coverage_hours", config["coverage_hours"])

        self.with_metadata("type", "support")
        logger.debug("Applied support template")

    async def _apply_creative_template(self, config: Dict[str, Any]) -> None:
        """Apply creative collaboration template."""
        self.with_governance(GovernanceType.HYBRID)

        # Default creative roles
        default_roles = ["ideator", "creator", "critic", "synthesizer"]
        self.add_agent_roles(config.get("roles", default_roles))

        # Creative-specific metadata
        if "project_type" in config:
            self.with_metadata("project_type", config["project_type"])
        if "style_guidelines" in config:
            self.with_metadata("style_guidelines", config["style_guidelines"])

        self.with_metadata("type", "creative")
        logger.debug("Applied creative template")


# Convenience function for quick builder creation
def builder(integration: CommunityIntegration) -> CommunityBuilder:
    """
    Create a new community builder.

    Args:
        integration: Community integration instance

    Returns:
        CommunityBuilder instance
    """
    return CommunityBuilder(integration)

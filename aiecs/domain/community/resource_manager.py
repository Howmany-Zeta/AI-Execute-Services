"""
Community Resource Manager

Manages shared resources, knowledge bases, and collaborative tools
within agent communities.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .community_manager import CommunityManager
    from aiecs.domain.context.context_engine import ContextEngine
import json

from .models.community_models import (
    CommunityResource,
    CommunityMember,
    ResourceType,
)
from .exceptions import CommunityValidationError as TaskValidationError

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manager for community resources, knowledge sharing, and collaborative tools.
    """

    def __init__(
        self,
        community_manager: Optional["CommunityManager"] = None,
        context_engine: Optional["ContextEngine"] = None,
    ) -> None:
        """
        Initialize the resource manager.

        Args:
            community_manager: Reference to the community manager
            context_engine: Optional context engine for persistent storage
        """
        self.community_manager = community_manager
        self.context_engine = context_engine

        # Resource indexing and search
        # tag -> set of resource_ids
        self.resource_index: Dict[str, Set[str]] = {}
        # type -> set of resource_ids
        self.type_index: Dict[ResourceType, Set[str]] = {}
        # owner_id -> set of resource_ids
        self.owner_index: Dict[str, Set[str]] = {}

        # Knowledge graph for resource relationships
        self.resource_relationships: Dict[str, Dict[str, List[str]]] = {}

        # Usage analytics
        self.usage_analytics: Dict[str, Dict[str, Any]] = {}

        logger.info("Resource manager initialized")

    async def create_knowledge_resource(
        self,
        community_id: str,
        owner_member_id: str,
        title: str,
        content: str,
        knowledge_type: str = "general",
        tags: Optional[List[str]] = None,
        related_resources: Optional[List[str]] = None,
    ) -> str:
        """
        Create a knowledge resource for the community.

        Args:
            community_id: ID of the community
            owner_member_id: ID of the member creating the resource
            title: Title of the knowledge resource
            content: Knowledge content
            knowledge_type: Type of knowledge (general, expertise, experience, etc.)
            tags: Tags for categorization
            related_resources: IDs of related resources

        Returns:
            Resource ID
        """
        resource_content: Dict[str, Any] = {
            "title": title,
            "content": content,
            "knowledge_type": knowledge_type,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        if related_resources:
            resource_content["related_resources"] = related_resources

        if self.community_manager is None:
            raise ValueError("CommunityManager not initialized")
        resource_id = await self.community_manager.create_community_resource(
            community_id=community_id,
            owner_member_id=owner_member_id,
            name=title,
            resource_type=ResourceType.KNOWLEDGE,
            content=resource_content,
            description=f"Knowledge resource: {knowledge_type}",
            tags=tags or [],
        )

        # Update indexes
        await self._update_resource_indexes(resource_id, tags or [], ResourceType.KNOWLEDGE, owner_member_id)

        # Create relationships
        if related_resources:
            await self._create_resource_relationships(resource_id, related_resources)

        logger.info(f"Created knowledge resource: {title} ({resource_id})")
        return resource_id

    async def create_tool_resource(
        self,
        community_id: str,
        owner_member_id: str,
        tool_name: str,
        tool_config: Dict[str, Any],
        description: str,
        usage_instructions: str,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Create a tool resource for community sharing.

        Args:
            community_id: ID of the community
            owner_member_id: ID of the member creating the resource
            tool_name: Name of the tool
            tool_config: Tool configuration
            description: Tool description
            usage_instructions: Instructions for using the tool
            tags: Tags for categorization

        Returns:
            Resource ID
        """
        resource_content = {
            "tool_name": tool_name,
            "tool_config": tool_config,
            "description": description,
            "usage_instructions": usage_instructions,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        if self.community_manager is None:
            raise ValueError("CommunityManager not initialized")
        resource_id = await self.community_manager.create_community_resource(
            community_id=community_id,
            owner_member_id=owner_member_id,
            name=tool_name,
            resource_type=ResourceType.TOOL,
            content=resource_content,
            description=description,
            tags=tags or [],
        )

        # Update indexes
        await self._update_resource_indexes(resource_id, tags or [], ResourceType.TOOL, owner_member_id)

        logger.info(f"Created tool resource: {tool_name} ({resource_id})")
        return resource_id

    async def create_experience_resource(
        self,
        community_id: str,
        owner_member_id: str,
        experience_title: str,
        situation: str,
        actions_taken: List[str],
        outcomes: Dict[str, Any],
        lessons_learned: List[str],
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Create an experience resource for knowledge sharing.

        Args:
            community_id: ID of the community
            owner_member_id: ID of the member sharing the experience
            experience_title: Title of the experience
            situation: Description of the situation
            actions_taken: List of actions taken
            outcomes: Outcomes and results
            lessons_learned: Key lessons learned
            tags: Tags for categorization

        Returns:
            Resource ID
        """
        resource_content = {
            "experience_title": experience_title,
            "situation": situation,
            "actions_taken": actions_taken,
            "outcomes": outcomes,
            "lessons_learned": lessons_learned,
            "created_at": datetime.utcnow().isoformat(),
            "experience_type": "case_study",
        }

        if self.community_manager is None:
            raise ValueError("CommunityManager not initialized")
        resource_id = await self.community_manager.create_community_resource(
            community_id=community_id,
            owner_member_id=owner_member_id,
            name=experience_title,
            resource_type=ResourceType.EXPERIENCE,
            content=resource_content,
            description=f"Experience sharing: {situation[:100]}...",
            tags=tags or [],
        )

        # Update indexes
        await self._update_resource_indexes(resource_id, tags or [], ResourceType.EXPERIENCE, owner_member_id)

        logger.info(f"Created experience resource: {experience_title} ({resource_id})")
        return resource_id

    async def search_resources(
        self,
        community_id: str,
        query: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        tags: Optional[List[str]] = None,
        owner_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for community resources.

        Args:
            community_id: ID of the community
            query: Text query for searching
            resource_type: Filter by resource type
            tags: Filter by tags
            owner_id: Filter by owner
            limit: Maximum number of results

        Returns:
            List of matching resources
        """
        if not self.community_manager:
            raise TaskValidationError("Community manager not available")

        community = self.community_manager.communities.get(community_id)
        if not community:
            raise TaskValidationError(f"Community not found: {community_id}")

        # Get candidate resource IDs
        candidate_ids = set(community.shared_resources)

        # Apply filters
        if resource_type and resource_type in self.type_index:
            candidate_ids &= self.type_index[resource_type]

        if tags:
            for tag in tags:
                if tag in self.resource_index:
                    candidate_ids &= self.resource_index[tag]

        if owner_id and owner_id in self.owner_index:
            candidate_ids &= self.owner_index[owner_id]

        # Get resource details and apply text search
        results = []
        for resource_id in candidate_ids:
            resource = self.community_manager.resources.get(resource_id)
            if not resource:
                continue

            # Text search in resource content
            if query:
                searchable_text = f"{resource.name} {resource.description or ''} {json.dumps(resource.content)}"
                if query.lower() not in searchable_text.lower():
                    continue

            # Add to results
            results.append(
                {
                    "resource_id": resource.resource_id,
                    "name": resource.name,
                    "resource_type": resource.resource_type,
                    "description": resource.description,
                    "owner_id": resource.owner_id,
                    "tags": resource.tags,
                    "usage_count": resource.usage_count,
                    "rating": resource.rating,
                    "created_at": resource.created_at,
                    "content_preview": self._get_content_preview(resource.content),
                }
            )

            if len(results) >= limit:
                break

        # Sort by relevance (usage count and rating)
        results.sort(key=lambda x: (x["usage_count"], x["rating"]), reverse=True)

        logger.info(f"Found {len(results)} resources for query: {query}")
        return results

    async def get_resource_recommendations(
        self,
        community_id: str,
        member_id: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get personalized resource recommendations for a member.

        Args:
            community_id: ID of the community
            member_id: ID of the member
            context: Optional context for recommendations
            limit: Maximum number of recommendations

        Returns:
            List of recommended resources
        """
        if not self.community_manager:
            raise TaskValidationError("Community manager not available")

        member = self.community_manager.members.get(member_id)
        if not member:
            raise TaskValidationError(f"Member not found: {member_id}")

        # Get member's specializations and interests
        member_tags = set(member.specializations)

        # Find resources matching member's interests
        candidate_resources = []
        for tag in member_tags:
            if tag in self.resource_index:
                for resource_id in self.resource_index[tag]:
                    resource = self.community_manager.resources.get(resource_id)
                    if resource and resource.owner_id != member_id:  # Don't recommend own resources
                        candidate_resources.append(resource)

        # Score and rank resources
        scored_resources = []
        for resource in candidate_resources:
            score = self._calculate_recommendation_score(resource, member, context)
            scored_resources.append((score, resource))

        # Sort by score and return top recommendations
        scored_resources.sort(key=lambda x: x[0], reverse=True)

        recommendations = []
        for score, resource in scored_resources[:limit]:
            recommendations.append(
                {
                    "resource_id": resource.resource_id,
                    "name": resource.name,
                    "resource_type": resource.resource_type,
                    "description": resource.description,
                    "recommendation_score": score,
                    "tags": resource.tags,
                    "usage_count": resource.usage_count,
                    "rating": resource.rating,
                }
            )

        logger.info(f"Generated {len(recommendations)} recommendations for member {member_id}")
        return recommendations

    def _calculate_recommendation_score(
        self,
        resource: CommunityResource,
        member: CommunityMember,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Calculate recommendation score for a resource."""
        score = 0.0

        # Tag matching score
        member_tags = set(member.specializations)
        resource_tags = set(resource.tags)
        tag_overlap = len(member_tags & resource_tags)
        score += tag_overlap * 2.0

        # Usage popularity score
        score += resource.usage_count * 0.1

        # Quality score
        score += resource.rating * 1.0

        # Recency score (newer resources get slight boost)
        days_old = (datetime.utcnow() - resource.created_at).days
        recency_score = max(0, 1.0 - (days_old / 365))  # Decay over a year
        score += recency_score * 0.5

        return score

    async def _update_resource_indexes(
        self,
        resource_id: str,
        tags: List[str],
        resource_type: ResourceType,
        owner_id: str,
    ) -> None:
        """Update resource indexes for efficient searching."""
        # Tag index
        for tag in tags:
            if tag not in self.resource_index:
                self.resource_index[tag] = set()
            self.resource_index[tag].add(resource_id)

        # Type index
        if resource_type not in self.type_index:
            self.type_index[resource_type] = set()
        self.type_index[resource_type].add(resource_id)

        # Owner index
        if owner_id not in self.owner_index:
            self.owner_index[owner_id] = set()
        self.owner_index[owner_id].add(resource_id)

    async def _create_resource_relationships(self, resource_id: str, related_resource_ids: List[str]) -> None:
        """Create relationships between resources."""
        if resource_id not in self.resource_relationships:
            self.resource_relationships[resource_id] = {
                "related_to": [],
                "referenced_by": [],
            }

        for related_id in related_resource_ids:
            # Add forward relationship
            if related_id not in self.resource_relationships[resource_id]["related_to"]:
                self.resource_relationships[resource_id]["related_to"].append(related_id)

            # Add backward relationship
            if related_id not in self.resource_relationships:
                self.resource_relationships[related_id] = {
                    "related_to": [],
                    "referenced_by": [],
                }
            if resource_id not in self.resource_relationships[related_id]["referenced_by"]:
                self.resource_relationships[related_id]["referenced_by"].append(resource_id)

    def _get_content_preview(self, content: Dict[str, Any], max_length: int = 200) -> str:
        """Get a preview of resource content."""
        if "content" in content:
            text = str(content["content"])
        elif "description" in content:
            text = str(content["description"])
        else:
            text = str(content)

        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

"""
Community Manager

Core component for managing agent communities, including governance,
resource sharing, and collaborative decision-making.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
import uuid

from .models.community_models import (
    AgentCommunity, CommunityMember, CommunityResource, CommunityDecision,
    CollaborationSession, CommunityRole, GovernanceType, DecisionStatus, ResourceType
)
from ..core.exceptions.task_exceptions import TaskValidationError

logger = logging.getLogger(__name__)


class CommunityManager:
    """
    Manager for agent communities, handling governance, collaboration, and resource sharing.
    """

    def __init__(self, context_engine=None):
        """
        Initialize the community manager.
        
        Args:
            context_engine: Optional context engine for persistent storage
        """
        self.context_engine = context_engine
        
        # In-memory storage (should be replaced with persistent storage)
        self.communities: Dict[str, AgentCommunity] = {}
        self.members: Dict[str, CommunityMember] = {}
        self.resources: Dict[str, CommunityResource] = {}
        self.decisions: Dict[str, CommunityDecision] = {}
        self.sessions: Dict[str, CollaborationSession] = {}
        
        # Community relationships
        self.member_communities: Dict[str, Set[str]] = {}  # member_id -> set of community_ids
        self.community_members: Dict[str, Set[str]] = {}   # community_id -> set of member_ids
        
        self._initialized = False
        logger.info("Community manager initialized")

    async def initialize(self) -> None:
        """Initialize the community manager."""
        if self._initialized:
            return
        
        # Load existing communities and members from persistent storage if available
        if self.context_engine:
            await self._load_from_storage()
        
        self._initialized = True
        logger.info("Community manager initialization completed")

    async def create_community(
        self,
        name: str,
        description: Optional[str] = None,
        governance_type: GovernanceType = GovernanceType.DEMOCRATIC,
        governance_rules: Optional[Dict[str, Any]] = None,
        creator_agent_id: Optional[str] = None
    ) -> str:
        """
        Create a new agent community.
        
        Args:
            name: Name of the community
            description: Optional description
            governance_type: Type of governance
            governance_rules: Governance rules and policies
            creator_agent_id: ID of the agent creating the community
            
        Returns:
            Community ID
        """
        community = AgentCommunity(
            name=name,
            description=description,
            governance_type=governance_type,
            governance_rules=governance_rules or {}
        )
        
        self.communities[community.community_id] = community
        self.community_members[community.community_id] = set()
        
        # Add creator as the first leader if provided
        if creator_agent_id:
            await self.add_member_to_community(
                community.community_id,
                creator_agent_id,
                community_role=CommunityRole.LEADER
            )
        
        logger.info(f"Created community: {name} ({community.community_id})")
        return community.community_id

    async def add_member_to_community(
        self,
        community_id: str,
        agent_id: str,
        agent_role: str = "general",
        community_role: CommunityRole = CommunityRole.CONTRIBUTOR,
        specializations: Optional[List[str]] = None
    ) -> str:
        """
        Add a member to a community.
        
        Args:
            community_id: ID of the community
            agent_id: ID of the agent to add
            agent_role: Functional role of the agent
            community_role: Role within the community
            specializations: Areas of specialization
            
        Returns:
            Member ID
        """
        if community_id not in self.communities:
            raise TaskValidationError(f"Community not found: {community_id}")
        
        # Check if agent is already a member
        existing_member = self._find_member_by_agent_id(community_id, agent_id)
        if existing_member:
            logger.warning(f"Agent {agent_id} is already a member of community {community_id}")
            return existing_member.member_id
        
        member = CommunityMember(
            member_id=str(uuid.uuid4()),
            agent_id=agent_id,
            agent_role=agent_role,
            community_role=community_role,
            specializations=specializations or []
        )
        
        self.members[member.member_id] = member
        
        # Update relationships
        if agent_id not in self.member_communities:
            self.member_communities[agent_id] = set()
        self.member_communities[agent_id].add(community_id)
        self.community_members[community_id].add(member.member_id)
        
        # Update community
        community = self.communities[community_id]
        community.members.append(member.member_id)
        
        if community_role == CommunityRole.LEADER:
            community.leaders.append(member.member_id)
        elif community_role == CommunityRole.COORDINATOR:
            community.coordinators.append(member.member_id)
        
        logger.info(f"Added member {agent_id} to community {community_id} as {community_role}")
        return member.member_id

    async def create_community_resource(
        self,
        community_id: str,
        owner_member_id: str,
        name: str,
        resource_type: ResourceType,
        content: Dict[str, Any],
        description: Optional[str] = None,
        access_level: str = "public",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Create a shared community resource.
        
        Args:
            community_id: ID of the community
            owner_member_id: ID of the member creating the resource
            name: Name of the resource
            resource_type: Type of resource
            content: Resource content/data
            description: Optional description
            access_level: Access level (public, restricted, private)
            tags: Tags for categorization
            
        Returns:
            Resource ID
        """
        if community_id not in self.communities:
            raise TaskValidationError(f"Community not found: {community_id}")
        
        if owner_member_id not in self.members:
            raise TaskValidationError(f"Member not found: {owner_member_id}")
        
        resource = CommunityResource(
            name=name,
            resource_type=resource_type,
            description=description,
            owner_id=owner_member_id,
            access_level=access_level,
            content=content,
            tags=tags or []
        )
        
        self.resources[resource.resource_id] = resource
        
        # Update community
        community = self.communities[community_id]
        community.shared_resources.append(resource.resource_id)
        community.resource_count += 1
        
        logger.info(f"Created resource {name} in community {community_id}")
        return resource.resource_id

    async def propose_decision(
        self,
        community_id: str,
        proposer_member_id: str,
        title: str,
        description: str,
        decision_type: str,
        implementation_plan: Optional[str] = None,
        deadline: Optional[datetime] = None
    ) -> str:
        """
        Propose a decision for community consideration.
        
        Args:
            community_id: ID of the community
            proposer_member_id: ID of the member proposing
            title: Title of the proposal
            description: Detailed description
            decision_type: Type of decision
            implementation_plan: Plan for implementation
            deadline: Implementation deadline
            
        Returns:
            Decision ID
        """
        if community_id not in self.communities:
            raise TaskValidationError(f"Community not found: {community_id}")
        
        if proposer_member_id not in self.members:
            raise TaskValidationError(f"Member not found: {proposer_member_id}")
        
        decision = CommunityDecision(
            title=title,
            description=description,
            proposer_id=proposer_member_id,
            decision_type=decision_type,
            implementation_plan=implementation_plan,
            deadline=deadline,
            voting_ends_at=datetime.utcnow() + timedelta(days=3)  # Default 3-day voting period
        )
        
        self.decisions[decision.decision_id] = decision
        
        # Update community
        community = self.communities[community_id]
        community.decision_count += 1
        
        logger.info(f"Proposed decision '{title}' in community {community_id}")
        return decision.decision_id

    async def vote_on_decision(
        self,
        decision_id: str,
        member_id: str,
        vote: str  # "for", "against", "abstain"
    ) -> bool:
        """
        Cast a vote on a community decision.
        
        Args:
            decision_id: ID of the decision
            member_id: ID of the voting member
            vote: Vote choice ("for", "against", "abstain")
            
        Returns:
            True if vote was cast successfully
        """
        if decision_id not in self.decisions:
            raise TaskValidationError(f"Decision not found: {decision_id}")
        
        if member_id not in self.members:
            raise TaskValidationError(f"Member not found: {member_id}")
        
        decision = self.decisions[decision_id]
        
        # Check if voting is still open
        if decision.status != DecisionStatus.VOTING and decision.status != DecisionStatus.PROPOSED:
            raise TaskValidationError(f"Voting is closed for decision {decision_id}")
        
        if decision.voting_ends_at and datetime.utcnow() > decision.voting_ends_at:
            raise TaskValidationError(f"Voting period has ended for decision {decision_id}")
        
        # Remove previous vote if exists
        if member_id in decision.votes_for:
            decision.votes_for.remove(member_id)
        if member_id in decision.votes_against:
            decision.votes_against.remove(member_id)
        if member_id in decision.abstentions:
            decision.abstentions.remove(member_id)
        
        # Cast new vote
        if vote.lower() == "for":
            decision.votes_for.append(member_id)
        elif vote.lower() == "against":
            decision.votes_against.append(member_id)
        elif vote.lower() == "abstain":
            decision.abstentions.append(member_id)
        else:
            raise TaskValidationError(f"Invalid vote choice: {vote}")
        
        # Update decision status
        if decision.status == DecisionStatus.PROPOSED:
            decision.status = DecisionStatus.VOTING
        
        logger.info(f"Member {member_id} voted '{vote}' on decision {decision_id}")
        return True

    def _find_member_by_agent_id(self, community_id: str, agent_id: str) -> Optional[CommunityMember]:
        """Find a community member by agent ID."""
        if community_id not in self.community_members:
            return None
        
        for member_id in self.community_members[community_id]:
            member = self.members.get(member_id)
            if member and member.agent_id == agent_id:
                return member
        
        return None

    async def _load_from_storage(self) -> None:
        """Load communities and members from persistent storage."""
        # TODO: Implement loading from context_engine or database
        pass

"""
Community Manager

Core component for managing agent communities, including governance,
resource sharing, and collaborative decision-making.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine
import uuid

from .models.community_models import (
    AgentCommunity,
    CommunityMember,
    CommunityResource,
    CommunityDecision,
    CollaborationSession,
    CommunityRole,
    GovernanceType,
    DecisionStatus,
    ResourceType,
)
from .exceptions import CommunityValidationError as TaskValidationError

logger = logging.getLogger(__name__)


class MemberLifecycleHooks(Protocol):
    """
    Protocol defining lifecycle hooks for community member events.
    Implement this protocol to receive notifications about member lifecycle events.
    """

    async def on_member_join(self, community_id: str, member_id: str, member: CommunityMember) -> None:
        """Called when a member joins a community."""
        ...

    async def on_member_exit(
        self,
        community_id: str,
        member_id: str,
        member: CommunityMember,
        reason: Optional[str] = None,
    ) -> None:
        """Called when a member exits/is removed from a community."""
        ...

    async def on_member_update(
        self,
        community_id: str,
        member_id: str,
        member: CommunityMember,
        changes: Dict[str, Any],
    ) -> None:
        """Called when a member's properties are updated."""
        ...

    async def on_member_inactive(
        self,
        community_id: str,
        member_id: str,
        member: CommunityMember,
        reason: Optional[str] = None,
    ) -> None:
        """Called when a member becomes inactive."""
        ...


class CommunityManager:
    """
    Manager for agent communities, handling governance, collaboration, and resource sharing.
    """

    def __init__(self, context_engine: Optional["ContextEngine"] = None) -> None:
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
        # member_id -> set of community_ids
        self.member_communities: Dict[str, Set[str]] = {}
        # community_id -> set of member_ids
        self.community_members: Dict[str, Set[str]] = {}

        # Lifecycle hooks
        self.lifecycle_hooks: List[MemberLifecycleHooks] = []

        self._initialized = False
        logger.info("Community manager initialized")

    async def initialize(self) -> None:
        """Initialize the community manager."""
        if self._initialized:
            return

        # Load existing communities and members from persistent storage if
        # available
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
        creator_agent_id: Optional[str] = None,
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
            governance_rules=governance_rules or {},
            max_members=None,
            updated_at=None,
        )

        self.communities[community.community_id] = community
        self.community_members[community.community_id] = set()

        # Add creator as the first leader if provided
        if creator_agent_id:
            await self.add_member_to_community(
                community.community_id,
                creator_agent_id,
                community_role=CommunityRole.LEADER,
            )

        # Auto-save to storage
        await self._save_to_storage()

        logger.info(f"Created community: {name} ({community.community_id})")
        return community.community_id

    async def add_member_to_community(
        self,
        community_id: str,
        agent_id: str,
        agent_role: str = "general",
        community_role: CommunityRole = CommunityRole.CONTRIBUTOR,
        specializations: Optional[List[str]] = None,
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
            specializations=specializations or [],
            last_active_at=None,
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

        # Auto-save to storage
        await self._save_to_storage()

        # Execute lifecycle hooks
        await self._execute_hook("on_member_join", community_id, member.member_id, member)

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
        tags: Optional[List[str]] = None,
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
            updated_at=None,
            access_level=access_level,
            content=content,
            tags=tags or [],
        )

        self.resources[resource.resource_id] = resource

        # Update community
        community = self.communities[community_id]
        community.shared_resources.append(resource.resource_id)
        community.resource_count += 1

        # Auto-save to storage
        await self._save_to_storage()

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
        deadline: Optional[datetime] = None,
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
            voting_ends_at=datetime.utcnow() + timedelta(days=3),  # Default 3-day voting period
            implemented_at=None,
        )

        self.decisions[decision.decision_id] = decision

        # Update community
        community = self.communities[community_id]
        community.decision_count += 1

        # Auto-save to storage
        await self._save_to_storage()

        logger.info(f"Proposed decision '{title}' in community {community_id}")
        return decision.decision_id

    async def vote_on_decision(
        self,
        decision_id: str,
        member_id: str,
        vote: str,  # "for", "against", "abstain"
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

        # Auto-save to storage
        await self._save_to_storage()

        logger.info(f"Member {member_id} voted '{vote}' on decision {decision_id}")
        return True

    async def remove_member_from_community(
        self,
        community_id: str,
        member_id: str,
        transfer_resources: bool = True,
        new_owner_id: Optional[str] = None,
    ) -> bool:
        """
        Remove a member from a community with graceful cleanup.

        Args:
            community_id: ID of the community
            member_id: ID of the member to remove
            transfer_resources: Whether to transfer member's resources
            new_owner_id: Optional new owner for transferred resources

        Returns:
            True if member was removed successfully
        """
        if community_id not in self.communities:
            raise TaskValidationError(f"Community not found: {community_id}")

        if member_id not in self.members:
            raise TaskValidationError(f"Member not found: {member_id}")

        member = self.members[member_id]
        community = self.communities[community_id]

        # Transfer or orphan resources
        if transfer_resources:
            await self.transfer_member_resources(
                member_id=member_id,
                new_owner_id=(new_owner_id or community.leaders[0] if community.leaders else None),
                community_id=community_id,
            )

        # Remove from community member list
        if member_id in community.members:
            community.members.remove(member_id)

        # Remove from leadership positions
        if member_id in community.leaders:
            community.leaders.remove(member_id)

        if member_id in community.coordinators:
            community.coordinators.remove(member_id)

        # Update relationships
        if community_id in self.community_members:
            self.community_members[community_id].discard(member_id)

        if member.agent_id in self.member_communities:
            self.member_communities[member.agent_id].discard(community_id)

        # Mark member as inactive
        member.is_active = False
        member.last_active_at = datetime.utcnow()

        # Auto-save to storage
        await self._save_to_storage()

        # Execute lifecycle hooks
        await self._execute_hook("on_member_exit", community_id, member_id, member, reason="removed")

        logger.info(f"Removed member {member_id} from community {community_id}")
        return True

    async def transfer_member_resources(self, member_id: str, new_owner_id: Optional[str], community_id: str) -> List[str]:
        """
        Transfer ownership of member's resources to another member.

        Args:
            member_id: ID of the member whose resources to transfer
            new_owner_id: ID of the new owner (None = make resources orphaned/community-owned)
            community_id: ID of the community

        Returns:
            List of transferred resource IDs
        """
        if member_id not in self.members:
            raise TaskValidationError(f"Member not found: {member_id}")

        transferred_resources = []

        # Find all resources owned by this member
        for resource_id, resource in self.resources.items():
            if resource.owner_id == member_id:
                if new_owner_id:
                    # Transfer to new owner
                    resource.owner_id = new_owner_id
                    resource.metadata["transferred_from"] = member_id
                    resource.metadata["transferred_at"] = datetime.utcnow().isoformat()
                    resource.updated_at = datetime.utcnow()
                else:
                    # Make community-owned (orphaned)
                    resource.owner_id = "community"
                    resource.metadata["orphaned_from"] = member_id
                    resource.metadata["orphaned_at"] = datetime.utcnow().isoformat()
                    resource.access_level = "public"  # Make public for community access

                transferred_resources.append(resource_id)

        # Auto-save to storage
        if transferred_resources:
            await self._save_to_storage()

        logger.info(f"Transferred {len(transferred_resources)} resources from member {member_id}")
        return transferred_resources

    async def deactivate_member(self, member_id: str, reason: Optional[str] = None) -> bool:
        """
        Soft deactivation of a member (doesn't remove, just marks inactive).

        Args:
            member_id: ID of the member to deactivate
            reason: Optional reason for deactivation

        Returns:
            True if member was deactivated successfully
        """
        if member_id not in self.members:
            raise TaskValidationError(f"Member not found: {member_id}")

        member = self.members[member_id]
        member.is_active = False
        member.last_active_at = datetime.utcnow()
        member.participation_level = "inactive"

        if reason:
            member.metadata["deactivation_reason"] = reason
            member.metadata["deactivated_at"] = datetime.utcnow().isoformat()

        # Auto-save to storage
        await self._save_to_storage()

        # Execute lifecycle hooks
        await self._execute_hook("on_member_inactive", None, member_id, member, reason=reason)

        logger.info(f"Deactivated member {member_id}")
        return True

    async def reactivate_member(self, member_id: str, restore_roles: bool = True) -> bool:
        """
        Reactivate a previously deactivated member.

        Args:
            member_id: ID of the member to reactivate
            restore_roles: Whether to restore previous roles

        Returns:
            True if member was reactivated successfully
        """
        if member_id not in self.members:
            raise TaskValidationError(f"Member not found: {member_id}")

        member = self.members[member_id]
        member.is_active = True
        member.last_active_at = datetime.utcnow()
        member.participation_level = "active"

        # Clear deactivation metadata
        if "deactivation_reason" in member.metadata:
            del member.metadata["deactivation_reason"]
        if "deactivated_at" in member.metadata:
            member.metadata["previous_deactivation"] = member.metadata["deactivated_at"]
            del member.metadata["deactivated_at"]

        member.metadata["reactivated_at"] = datetime.utcnow().isoformat()

        # Auto-save to storage
        await self._save_to_storage()

        logger.info(f"Reactivated member {member_id}")
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

    def register_lifecycle_hook(self, hook: MemberLifecycleHooks) -> None:
        """
        Register a lifecycle hook handler.

        Args:
            hook: Hook handler implementing MemberLifecycleHooks protocol
        """
        self.lifecycle_hooks.append(hook)
        logger.info(f"Registered lifecycle hook: {hook.__class__.__name__}")

    def unregister_lifecycle_hook(self, hook: MemberLifecycleHooks) -> bool:
        """
        Unregister a lifecycle hook handler.

        Args:
            hook: Hook handler to remove

        Returns:
            True if hook was removed
        """
        if hook in self.lifecycle_hooks:
            self.lifecycle_hooks.remove(hook)
            logger.info(f"Unregistered lifecycle hook: {hook.__class__.__name__}")
            return True
        return False

    async def _execute_hook(
        self,
        hook_name: str,
        community_id: Optional[str],
        member_id: str,
        member: CommunityMember,
        **kwargs,
    ) -> None:
        """
        Execute all registered hooks for a specific event.

        Args:
            hook_name: Name of the hook method to call
            community_id: ID of the community (optional for some hooks)
            member_id: ID of the member
            member: Member object
            **kwargs: Additional arguments to pass to the hook
        """
        for hook in self.lifecycle_hooks:
            try:
                hook_method = getattr(hook, hook_name, None)
                if hook_method:
                    if community_id:
                        await hook_method(community_id, member_id, member, **kwargs)
                    else:
                        await hook_method(member_id, member, **kwargs)
            except Exception as e:
                logger.error(f"Error executing lifecycle hook {hook_name}: {e}")

    async def _load_from_storage(self) -> None:
        """
        Load communities and members from persistent storage.

        Loads:
        - Communities
        - Members
        - Resources
        - Decisions
        - Sessions
        - Relationships
        """
        if not self.context_engine:
            logger.warning("No context engine available for loading")
            return

        try:
            # Load communities
            communities_data = await self._load_data_by_key("communities")
            if communities_data:
                for community_id, community_dict in communities_data.items():
                    try:
                        community = AgentCommunity(**community_dict)
                        self.communities[community_id] = community
                        self.community_members[community_id] = set(community.members)
                    except Exception as e:
                        logger.error(f"Failed to load community {community_id}: {e}")

            # Load members
            members_data = await self._load_data_by_key("community_members")
            if members_data:
                for member_id, member_dict in members_data.items():
                    try:
                        member = CommunityMember(**member_dict)
                        self.members[member_id] = member
                    except Exception as e:
                        logger.error(f"Failed to load member {member_id}: {e}")

            # Load resources
            resources_data = await self._load_data_by_key("community_resources")
            if resources_data:
                for resource_id, resource_dict in resources_data.items():
                    try:
                        resource = CommunityResource(**resource_dict)
                        self.resources[resource_id] = resource
                    except Exception as e:
                        logger.error(f"Failed to load resource {resource_id}: {e}")

            # Load decisions
            decisions_data = await self._load_data_by_key("community_decisions")
            if decisions_data:
                for decision_id, decision_dict in decisions_data.items():
                    try:
                        decision = CommunityDecision(**decision_dict)
                        self.decisions[decision_id] = decision
                    except Exception as e:
                        logger.error(f"Failed to load decision {decision_id}: {e}")

            # Load sessions
            sessions_data = await self._load_data_by_key("community_sessions")
            if sessions_data:
                for session_id, session_dict in sessions_data.items():
                    try:
                        session = CollaborationSession(**session_dict)
                        self.sessions[session_id] = session
                    except Exception as e:
                        logger.error(f"Failed to load session {session_id}: {e}")

            # Rebuild member_communities relationships
            for member_id, member in self.members.items():
                for community_id, community in self.communities.items():
                    if member_id in community.members:
                        if member.agent_id not in self.member_communities:
                            self.member_communities[member.agent_id] = set()
                        self.member_communities[member.agent_id].add(community_id)

            logger.info(f"Loaded {len(self.communities)} communities, {len(self.members)} members from storage")

        except Exception as e:
            logger.error(f"Error loading from storage: {e}")

    async def _load_data_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Load data from context engine by key."""
        if not self.context_engine:
            return None

        try:
            # Try to get data from context engine
            # The exact method depends on the context engine implementation
            if hasattr(self.context_engine, "get_context"):
                data = await self.context_engine.get_context(key)
                return data
            elif hasattr(self.context_engine, "get"):
                data = await self.context_engine.get(key)
                return data
            else:
                logger.warning("Context engine does not support get operations")
                return None
        except Exception as e:
            logger.debug(f"No data found for key {key}: {e}")
            return None

    async def _save_to_storage(self) -> None:
        """
        Save all communities and members to persistent storage.

        Saves:
        - Communities
        - Members
        - Resources
        - Decisions
        - Sessions
        """
        if not self.context_engine:
            logger.debug("No context engine available for saving")
            return

        try:
            # Save communities
            communities_data = {cid: community.model_dump() for cid, community in self.communities.items()}
            await self._save_data_by_key("communities", communities_data)

            # Save members
            members_data = {mid: member.model_dump() for mid, member in self.members.items()}
            await self._save_data_by_key("community_members", members_data)

            # Save resources
            resources_data = {rid: resource.model_dump() for rid, resource in self.resources.items()}
            await self._save_data_by_key("community_resources", resources_data)

            # Save decisions
            decisions_data = {did: decision.model_dump() for did, decision in self.decisions.items()}
            await self._save_data_by_key("community_decisions", decisions_data)

            # Save sessions
            sessions_data = {sid: session.model_dump() for sid, session in self.sessions.items()}
            await self._save_data_by_key("community_sessions", sessions_data)

            logger.debug(f"Saved {len(self.communities)} communities, {len(self.members)} members to storage")

        except Exception as e:
            logger.error(f"Error saving to storage: {e}")

    async def _save_data_by_key(self, key: str, data: Dict[str, Any]) -> None:
        """Save data to context engine by key."""
        if not self.context_engine:
            return

        try:
            # The exact method depends on the context engine implementation
            if hasattr(self.context_engine, "set_context"):
                await self.context_engine.set_context(key, data)
            elif hasattr(self.context_engine, "set"):
                await self.context_engine.set(key, data)
            elif hasattr(self.context_engine, "save"):
                await self.context_engine.save(key, data)
            else:
                logger.warning("Context engine does not support set/save operations")
        except Exception as e:
            logger.error(f"Failed to save data for key {key}: {e}")

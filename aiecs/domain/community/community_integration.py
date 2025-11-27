"""
Community Integration Module

Integrates community collaboration features with the existing agent system,
providing seamless community-aware agent management and collaboration.
"""

import logging
from typing import Dict, List, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from aiecs.domain.context.context_engine import ContextEngine
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import asyncio

from .community_manager import CommunityManager
from .decision_engine import DecisionEngine, ConsensusAlgorithm
from .resource_manager import ResourceManager
from .collaborative_workflow import CollaborativeWorkflowEngine
from .models.community_models import CommunityRole, GovernanceType
from .exceptions import CommunityValidationError as TaskValidationError

logger = logging.getLogger(__name__)


class CommunityIntegration:
    """
    Integration layer for community collaboration features.
    """

    def __init__(
        self,
        agent_manager: Optional[Any] = None,
        context_engine: Optional["ContextEngine"] = None,
    ) -> None:
        """
        Initialize community integration.

        Args:
            agent_manager: Reference to the agent manager
            context_engine: Context engine for persistent storage
        """
        self.agent_manager = agent_manager
        self.context_engine = context_engine

        # Initialize community components
        self.community_manager = CommunityManager(context_engine)
        self.decision_engine = DecisionEngine(self.community_manager)
        self.resource_manager = ResourceManager(self.community_manager, context_engine)
        self.workflow_engine = CollaborativeWorkflowEngine(self.community_manager, self.resource_manager, self.decision_engine)

        # Community-aware agent tracking
        # agent_id -> community_ids
        self.agent_community_mapping: Dict[str, List[str]] = {}
        # community_id -> agent_ids
        self.community_agent_mapping: Dict[str, List[str]] = {}

        self._initialized = False
        logger.info("Community integration initialized")

    async def initialize(self) -> None:
        """Initialize all community components."""
        if self._initialized:
            return

        await self.community_manager.initialize()
        self._initialized = True
        logger.info("Community integration initialization completed")

    async def create_agent_community(
        self,
        name: str,
        description: str,
        agent_roles: List[str],
        governance_type: GovernanceType = GovernanceType.DEMOCRATIC,
        creator_agent_id: Optional[str] = None,
    ) -> str:
        """
        Create a new agent community with specified agent roles.

        Args:
            name: Name of the community
            description: Description of the community
            agent_roles: List of agent roles to include
            governance_type: Type of governance
            creator_agent_id: ID of the creating agent

        Returns:
            Community ID
        """
        # Create the community
        community_id = await self.community_manager.create_community(
            name=name,
            description=description,
            governance_type=governance_type,
            creator_agent_id=creator_agent_id,
        )

        # Add agents to the community if agent_manager is available
        if self.agent_manager:
            for role in agent_roles:
                # Get agents with this role from agent manager
                agents = self.agent_manager.agent_registry.get_agents_by_role(role)

                for agent in agents:
                    await self._add_agent_to_community(community_id, agent.agent_id, role)
        else:
            # For testing or when agent_manager is not available, just log the
            # roles
            logger.debug(f"Agent manager not available, community created without auto-adding agents for roles: {agent_roles}")

        logger.info(f"Created agent community '{name}' with {len(agent_roles)} role types")
        return community_id

    async def _add_agent_to_community(
        self,
        community_id: str,
        agent_id: str,
        agent_role: str,
        community_role: CommunityRole = CommunityRole.CONTRIBUTOR,
    ) -> str:
        """Add an agent to a community."""
        # Add to community manager
        member_id = await self.community_manager.add_member_to_community(
            community_id=community_id,
            agent_id=agent_id,
            agent_role=agent_role,
            community_role=community_role,
        )

        # Update mappings
        if agent_id not in self.agent_community_mapping:
            self.agent_community_mapping[agent_id] = []
        self.agent_community_mapping[agent_id].append(community_id)

        if community_id not in self.community_agent_mapping:
            self.community_agent_mapping[community_id] = []
        self.community_agent_mapping[community_id].append(agent_id)

        return member_id

    async def initiate_community_collaboration(
        self,
        community_id: str,
        collaboration_type: str,
        purpose: str,
        leader_agent_id: Optional[str] = None,
        specific_participants: Optional[List[str]] = None,
        session_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Initiate a collaborative session within a community.

        Args:
            community_id: ID of the community
            collaboration_type: Type of collaboration (brainstorming, problem_solving, etc.)
            purpose: Purpose of the collaboration
            leader_agent_id: Optional leader agent ID
            specific_participants: Optional specific participants
            session_config: Optional session configuration

        Returns:
            Session ID
        """
        community = self.community_manager.communities.get(community_id)
        if not community:
            raise TaskValidationError(f"Community not found: {community_id}")

        # Determine participants
        if specific_participants:
            participants = specific_participants
        else:
            # Use all community members
            participants = community.members

        # Determine leader
        if not leader_agent_id:
            # Use first leader or coordinator
            if community.leaders:
                leader_member = self.community_manager.members.get(community.leaders[0])
                leader_agent_id = leader_member.agent_id if leader_member else None
            elif community.coordinators:
                coordinator_member = self.community_manager.members.get(community.coordinators[0])
                leader_agent_id = coordinator_member.agent_id if coordinator_member else None

        # Ensure we have a leader agent ID
        if not leader_agent_id:
            raise ValueError("Cannot start collaborative session: no leader agent ID available")

        # Start collaborative session
        session_id = await self.workflow_engine.start_collaborative_session(
            community_id=community_id,
            session_leader_id=leader_agent_id,
            session_type=collaboration_type,
            purpose=purpose,
            participants=participants,
            session_config=session_config,
        )

        logger.info(f"Initiated {collaboration_type} collaboration in community {community_id}")
        return session_id

    async def propose_community_decision(
        self,
        community_id: str,
        proposer_agent_id: str,
        title: str,
        description: str,
        decision_type: str,
        implementation_plan: Optional[str] = None,
    ) -> str:
        """
        Propose a decision for community consideration.

        Args:
            community_id: ID of the community
            proposer_agent_id: ID of the proposing agent
            title: Title of the proposal
            description: Detailed description
            decision_type: Type of decision
            implementation_plan: Optional implementation plan

        Returns:
            Decision ID
        """
        # Find the member ID for the proposing agent
        proposer_member_id = None
        for member_id, member in self.community_manager.members.items():
            if member.agent_id == proposer_agent_id:
                proposer_member_id = member_id
                break

        if not proposer_member_id:
            raise TaskValidationError(f"Agent {proposer_agent_id} is not a community member")

        decision_id = await self.community_manager.propose_decision(
            community_id=community_id,
            proposer_member_id=proposer_member_id,
            title=title,
            description=description,
            decision_type=decision_type,
            implementation_plan=implementation_plan,
        )

        logger.info(f"Agent {proposer_agent_id} proposed decision '{title}' in community {community_id}")
        return decision_id

    async def agent_vote_on_decision(self, decision_id: str, agent_id: str, vote: str) -> bool:
        """
        Cast a vote on behalf of an agent.

        Args:
            decision_id: ID of the decision
            agent_id: ID of the voting agent
            vote: Vote choice ("for", "against", "abstain")

        Returns:
            True if vote was cast successfully
        """
        # Find the member ID for the voting agent
        member_id = None
        for mid, member in self.community_manager.members.items():
            if member.agent_id == agent_id:
                member_id = mid
                break

        if not member_id:
            raise TaskValidationError(f"Agent {agent_id} is not a community member")

        success = await self.community_manager.vote_on_decision(decision_id=decision_id, member_id=member_id, vote=vote)

        logger.info(f"Agent {agent_id} voted '{vote}' on decision {decision_id}")
        return success

    async def evaluate_community_decision(
        self,
        decision_id: str,
        community_id: str,
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY,
    ) -> Dict[str, Any]:
        """
        Evaluate a community decision using consensus algorithm.

        Args:
            decision_id: ID of the decision
            community_id: ID of the community
            algorithm: Consensus algorithm to use

        Returns:
            Evaluation result
        """
        passed, details = await self.decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=community_id,
            algorithm=algorithm,
        )

        result = {
            "decision_id": decision_id,
            "passed": passed,
            "algorithm": algorithm,
            "details": details,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Decision {decision_id} evaluation: {'PASSED' if passed else 'REJECTED'}")
        return result

    async def create_community_knowledge_resource(
        self,
        community_id: str,
        creator_agent_id: str,
        title: str,
        content: str,
        knowledge_type: str = "general",
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Create a knowledge resource on behalf of an agent.

        Args:
            community_id: ID of the community
            creator_agent_id: ID of the creating agent
            title: Title of the knowledge resource
            content: Knowledge content
            knowledge_type: Type of knowledge
            tags: Tags for categorization

        Returns:
            Resource ID
        """
        # Find the member ID for the creating agent
        creator_member_id = None
        for member_id, member in self.community_manager.members.items():
            if member.agent_id == creator_agent_id:
                creator_member_id = member_id
                break

        if not creator_member_id:
            raise TaskValidationError(f"Agent {creator_agent_id} is not a community member")

        resource_id = await self.resource_manager.create_knowledge_resource(
            community_id=community_id,
            owner_member_id=creator_member_id,
            title=title,
            content=content,
            knowledge_type=knowledge_type,
            tags=tags,
        )

        logger.info(f"Agent {creator_agent_id} created knowledge resource '{title}'")
        return resource_id

    async def get_agent_communities(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get all communities that an agent belongs to.

        Args:
            agent_id: ID of the agent

        Returns:
            List of community information
        """
        communities = []

        if agent_id in self.agent_community_mapping:
            for community_id in self.agent_community_mapping[agent_id]:
                community = self.community_manager.communities.get(community_id)
                if community:
                    # Find agent's role in this community
                    agent_role = None
                    community_role = None
                    for member_id in community.members:
                        member = self.community_manager.members.get(member_id)
                        if member and member.agent_id == agent_id:
                            agent_role = member.agent_role
                            community_role = member.community_role
                            break

                    communities.append(
                        {
                            "community_id": community_id,
                            "name": community.name,
                            "description": community.description,
                            "governance_type": community.governance_type,
                            "agent_role": agent_role,
                            "community_role": community_role,
                            "member_count": len(community.members),
                            "is_leader": (member_id in community.leaders if member_id else False),
                            "is_coordinator": (member_id in community.coordinators if member_id else False),
                        }
                    )

        return communities

    async def get_community_status(self, community_id: str) -> Dict[str, Any]:
        """
        Get comprehensive status of a community.

        Args:
            community_id: ID of the community

        Returns:
            Community status information
        """
        community = self.community_manager.communities.get(community_id)
        if not community:
            raise TaskValidationError(f"Community not found: {community_id}")

        # Get active sessions
        active_sessions = [session_id for session_id, session in self.workflow_engine.active_sessions.items() if session.community_id == community_id]

        # Get recent decisions
        recent_decisions = [
            decision
            for decision in self.community_manager.decisions.values()
            if any(
                member.agent_id in self.community_agent_mapping.get(community_id, []) for member_id in [decision.proposer_id] for member in [self.community_manager.members.get(member_id)] if member
            )
        ]

        status = {
            "community_id": community_id,
            "name": community.name,
            "description": community.description,
            "governance_type": community.governance_type,
            "member_count": len(community.members),
            "leader_count": len(community.leaders),
            "coordinator_count": len(community.coordinators),
            "resource_count": community.resource_count,
            "decision_count": community.decision_count,
            "activity_level": community.activity_level,
            "collaboration_score": community.collaboration_score,
            "active_sessions": len(active_sessions),
            "recent_decisions": len(recent_decisions),
            "is_active": community.is_active,
            "created_at": community.created_at.isoformat(),
            "updated_at": (community.updated_at.isoformat() if community.updated_at else None),
        }

        return status

    # ========== Quick-Create Factory Methods ==========

    async def create_temporary_community(
        self,
        name: str,
        description: str,
        agent_roles: List[str],
        duration_minutes: int = 60,
        auto_cleanup: bool = True,
        governance_type: GovernanceType = GovernanceType.DEMOCRATIC,
        creator_agent_id: Optional[str] = None,
    ) -> str:
        """
        Create a temporary community with automatic cleanup.

        Args:
            name: Name of the community
            description: Description
            agent_roles: List of agent roles to include
            duration_minutes: Duration before auto-cleanup
            auto_cleanup: Whether to automatically cleanup after duration
            governance_type: Type of governance
            creator_agent_id: ID of the creating agent

        Returns:
            Community ID
        """
        community_id = await self.create_agent_community(
            name=name,
            description=description,
            agent_roles=agent_roles,
            governance_type=governance_type,
            creator_agent_id=creator_agent_id,
        )

        # Mark as temporary
        community = self.community_manager.communities[community_id]
        community.metadata["temporary"] = True
        community.metadata["created_for_duration"] = duration_minutes
        community.metadata["cleanup_at"] = (datetime.utcnow() + timedelta(minutes=duration_minutes)).isoformat()

        # Schedule cleanup if enabled
        if auto_cleanup:
            asyncio.create_task(self._cleanup_temporary_community(community_id, duration_minutes))

        logger.info(f"Created temporary community {name} for {duration_minutes} minutes")
        return community_id

    async def _cleanup_temporary_community(self, community_id: str, duration_minutes: int) -> None:
        """Cleanup temporary community after duration."""
        await asyncio.sleep(duration_minutes * 60)

        try:
            community = self.community_manager.communities.get(community_id)
            if community and community.metadata.get("temporary"):
                # Mark as inactive
                community.is_active = False
                community.metadata["cleanup_completed"] = datetime.utcnow().isoformat()
                logger.info(f"Cleaned up temporary community {community_id}")
        except Exception as e:
            logger.error(f"Error cleaning up temporary community {community_id}: {e}")

    async def create_project_community(
        self,
        project_name: str,
        project_description: str,
        agent_roles: List[str],
        project_goal: str,
        project_deadline: Optional[datetime] = None,
        creator_agent_id: Optional[str] = None,
    ) -> str:
        """
        Create a community pre-configured for project collaboration.

        Args:
            project_name: Name of the project
            project_description: Project description
            agent_roles: List of agent roles for the project
            project_goal: Goal of the project
            project_deadline: Optional project deadline
            creator_agent_id: ID of the creating agent

        Returns:
            Community ID
        """
        community_id = await self.create_agent_community(
            name=f"Project: {project_name}",
            description=project_description,
            agent_roles=agent_roles,
            governance_type=GovernanceType.HIERARCHICAL,  # Project-based governance
            creator_agent_id=creator_agent_id,
        )

        # Configure for project collaboration
        community = self.community_manager.communities[community_id]
        community.metadata["type"] = "project"
        community.metadata["project_goal"] = project_goal
        if project_deadline:
            community.metadata["project_deadline"] = project_deadline.isoformat()

        # Create initial project resources
        if creator_agent_id:
            # Find creator member
            creator_member_id = None
            for mid, member in self.community_manager.members.items():
                if member.agent_id == creator_agent_id and mid in community.members:
                    creator_member_id = mid
                    break

            if creator_member_id:
                # Create project charter resource
                await self.resource_manager.create_knowledge_resource(
                    community_id=community_id,
                    owner_member_id=creator_member_id,
                    title=f"{project_name} Charter",
                    content=f"Goal: {project_goal}\n\nDescription: {project_description}",
                    knowledge_type="project_charter",
                    tags=["project", "charter", project_name],
                )

        logger.info(f"Created project community: {project_name}")
        return community_id

    async def create_research_community(
        self,
        research_topic: str,
        research_questions: List[str],
        agent_roles: List[str],
        methodologies: Optional[List[str]] = None,
        creator_agent_id: Optional[str] = None,
    ) -> str:
        """
        Create a community pre-configured for research collaboration.

        Args:
            research_topic: Topic of research
            research_questions: Research questions to explore
            agent_roles: List of agent roles for research
            methodologies: Optional research methodologies
            creator_agent_id: ID of the creating agent

        Returns:
            Community ID
        """
        community_id = await self.create_agent_community(
            name=f"Research: {research_topic}",
            description=f"Collaborative research on {research_topic}",
            agent_roles=agent_roles,
            governance_type=GovernanceType.CONSENSUS,  # Consensus-based for research
            creator_agent_id=creator_agent_id,
        )

        # Configure for research
        community = self.community_manager.communities[community_id]
        community.metadata["type"] = "research"
        community.metadata["research_topic"] = research_topic
        community.metadata["research_questions"] = research_questions
        if methodologies:
            community.metadata["methodologies"] = methodologies

        # Create research resources
        if creator_agent_id:
            # Find creator member
            creator_member_id = None
            for mid, member in self.community_manager.members.items():
                if member.agent_id == creator_agent_id and mid in community.members:
                    creator_member_id = mid
                    break

            if creator_member_id:
                # Create research plan resource
                research_plan = {
                    "topic": research_topic,
                    "questions": research_questions,
                    "methodologies": methodologies or [],
                    "status": "planning",
                }

                await self.resource_manager.create_knowledge_resource(
                    community_id=community_id,
                    owner_member_id=creator_member_id,
                    title=f"{research_topic} Research Plan",
                    content=str(research_plan),
                    knowledge_type="research_plan",
                    tags=["research", "plan", research_topic],
                )

        logger.info(f"Created research community: {research_topic}")
        return community_id

    async def quick_brainstorm(
        self,
        topic: str,
        agent_ids: List[str],
        duration_minutes: int = 30,
        auto_cleanup: bool = True,
    ) -> Dict[str, Any]:
        """
        Quick one-line brainstorming session with temporary community.

        Args:
            topic: Topic to brainstorm
            agent_ids: List of agent IDs to participate
            duration_minutes: Duration of the session
            auto_cleanup: Whether to cleanup community after

        Returns:
            Session results and summary
        """
        # Create temporary community
        community_id = await self.create_temporary_community(
            name=f"Brainstorm: {topic}",
            description=f"Quick brainstorming session on {topic}",
            agent_roles=[],  # Will add specific agents
            duration_minutes=duration_minutes,
            auto_cleanup=auto_cleanup,
            governance_type=GovernanceType.DEMOCRATIC,
        )

        # Add specific agents to community
        for agent_id in agent_ids:
            await self._add_agent_to_community(
                community_id=community_id,
                agent_id=agent_id,
                agent_role="brainstormer",
                community_role=CommunityRole.CONTRIBUTOR,
            )

        # Ensure we have at least one agent
        if not agent_ids:
            raise ValueError("Cannot start brainstorming session: no agents provided")

        # Start brainstorming session
        session_id = await self.workflow_engine.start_collaborative_session(
            community_id=community_id,
            session_leader_id=agent_ids[0],
            session_type="brainstorming",
            purpose=f"Brainstorm ideas for {topic}",
            participants=[mid for mid in self.community_manager.communities[community_id].members],
            duration_minutes=duration_minutes,
        )

        # Wait for session to complete (simplified - in reality would be async)
        await asyncio.sleep(2)  # Simulate session time

        # End session and get results
        summary = await self.workflow_engine.end_session(session_id)

        results = {
            "topic": topic,
            "community_id": community_id,
            "session_id": session_id,
            "participants": agent_ids,
            "duration_minutes": duration_minutes,
            "summary": summary,
        }

        logger.info(f"Completed quick brainstorm on {topic}")
        return results

    # ========== Context Managers ==========

    @asynccontextmanager
    async def temporary_community(
        self,
        name: str,
        agent_roles: List[str],
        governance_type: GovernanceType = GovernanceType.DEMOCRATIC,
        creator_agent_id: Optional[str] = None,
    ):
        """
        Context manager for temporary communities with automatic cleanup.

        Args:
            name: Name of the community
            agent_roles: List of agent roles
            governance_type: Type of governance
            creator_agent_id: ID of the creating agent

        Yields:
            Community ID

        Example:
            async with integration.temporary_community("Quick Collab", ["analyst", "writer"]) as community_id:
                # Use community
                await integration.initiate_community_collaboration(...)
            # Community automatically cleaned up
        """
        community_id = await self.create_agent_community(
            name=name,
            description=f"Temporary community: {name}",
            agent_roles=agent_roles,
            governance_type=governance_type,
            creator_agent_id=creator_agent_id,
        )

        try:
            yield community_id
        finally:
            # Cleanup
            community = self.community_manager.communities.get(community_id)
            if community:
                community.is_active = False
                community.metadata["context_manager_cleanup"] = datetime.utcnow().isoformat()
                logger.info(f"Context manager cleaned up community {community_id}")

    @asynccontextmanager
    async def collaborative_session(
        self,
        community_id: str,
        session_type: str,
        purpose: str,
        leader_agent_id: Optional[str] = None,
        participants: Optional[List[str]] = None,
    ):
        """
        Context manager for collaborative sessions with automatic cleanup.

        Args:
            community_id: ID of the community
            session_type: Type of session
            purpose: Purpose of the session
            leader_agent_id: Optional leader agent ID
            participants: Optional specific participants

        Yields:
            Session ID

        Example:
            async with integration.collaborative_session(
                community_id, "brainstorming", "Generate ideas"
            ) as session_id:
                # Session is active
                pass
            # Session automatically ended
        """
        session_id = await self.initiate_community_collaboration(
            community_id=community_id,
            collaboration_type=session_type,
            purpose=purpose,
            leader_agent_id=leader_agent_id,
            specific_participants=participants,
        )

        try:
            yield session_id
        finally:
            # End session
            try:
                await self.workflow_engine.end_session(session_id)
                logger.info(f"Context manager ended session {session_id}")
            except Exception as e:
                logger.error(f"Error ending session in context manager: {e}")

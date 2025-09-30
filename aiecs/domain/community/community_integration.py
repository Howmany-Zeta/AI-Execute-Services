"""
Community Integration Module

Integrates community collaboration features with the existing agent system,
providing seamless community-aware agent management and collaboration.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .community_manager import CommunityManager
from .decision_engine import DecisionEngine, ConsensusAlgorithm
from .resource_manager import ResourceManager
from .collaborative_workflow import CollaborativeWorkflowEngine
from .models.community_models import CommunityRole, GovernanceType
from ..core.exceptions.task_exceptions import TaskValidationError

logger = logging.getLogger(__name__)


class CommunityIntegration:
    """
    Integration layer for community collaboration features.
    """

    def __init__(self, agent_manager=None, context_engine=None):
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
        self.workflow_engine = CollaborativeWorkflowEngine(
            self.community_manager, 
            self.resource_manager, 
            self.decision_engine
        )
        
        # Community-aware agent tracking
        self.agent_community_mapping: Dict[str, List[str]] = {}  # agent_id -> community_ids
        self.community_agent_mapping: Dict[str, List[str]] = {}  # community_id -> agent_ids
        
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
        creator_agent_id: Optional[str] = None
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
        if not self.agent_manager:
            raise TaskValidationError("Agent manager not available")
        
        # Create the community
        community_id = await self.community_manager.create_community(
            name=name,
            description=description,
            governance_type=governance_type,
            creator_agent_id=creator_agent_id
        )
        
        # Add agents to the community
        for role in agent_roles:
            # Get agents with this role from agent manager
            agents = self.agent_manager.agent_registry.get_agents_by_role(role)
            
            for agent in agents:
                await self._add_agent_to_community(community_id, agent.agent_id, role)
        
        logger.info(f"Created agent community '{name}' with {len(agent_roles)} role types")
        return community_id

    async def _add_agent_to_community(
        self,
        community_id: str,
        agent_id: str,
        agent_role: str,
        community_role: CommunityRole = CommunityRole.CONTRIBUTOR
    ) -> str:
        """Add an agent to a community."""
        # Add to community manager
        member_id = await self.community_manager.add_member_to_community(
            community_id=community_id,
            agent_id=agent_id,
            agent_role=agent_role,
            community_role=community_role
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
        session_config: Optional[Dict[str, Any]] = None
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
        
        # Start collaborative session
        session_id = await self.workflow_engine.start_collaborative_session(
            community_id=community_id,
            session_leader_id=leader_agent_id,
            session_type=collaboration_type,
            purpose=purpose,
            participants=participants,
            session_config=session_config
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
        implementation_plan: Optional[str] = None
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
            implementation_plan=implementation_plan
        )
        
        logger.info(f"Agent {proposer_agent_id} proposed decision '{title}' in community {community_id}")
        return decision_id

    async def agent_vote_on_decision(
        self,
        decision_id: str,
        agent_id: str,
        vote: str
    ) -> bool:
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
        
        success = await self.community_manager.vote_on_decision(
            decision_id=decision_id,
            member_id=member_id,
            vote=vote
        )
        
        logger.info(f"Agent {agent_id} voted '{vote}' on decision {decision_id}")
        return success

    async def evaluate_community_decision(
        self,
        decision_id: str,
        community_id: str,
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY
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
            algorithm=algorithm
        )
        
        result = {
            "decision_id": decision_id,
            "passed": passed,
            "algorithm": algorithm,
            "details": details,
            "evaluated_at": datetime.utcnow().isoformat()
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
        tags: Optional[List[str]] = None
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
            tags=tags
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
                    
                    communities.append({
                        "community_id": community_id,
                        "name": community.name,
                        "description": community.description,
                        "governance_type": community.governance_type,
                        "agent_role": agent_role,
                        "community_role": community_role,
                        "member_count": len(community.members),
                        "is_leader": member_id in community.leaders if member_id else False,
                        "is_coordinator": member_id in community.coordinators if member_id else False
                    })
        
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
        active_sessions = [
            session_id for session_id, session in self.workflow_engine.active_sessions.items()
            if session.community_id == community_id
        ]
        
        # Get recent decisions
        recent_decisions = [
            decision for decision in self.community_manager.decisions.values()
            if any(member.agent_id in self.community_agent_mapping.get(community_id, [])
                  for member_id in [decision.proposer_id]
                  for member in [self.community_manager.members.get(member_id)]
                  if member)
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
            "updated_at": community.updated_at.isoformat() if community.updated_at else None
        }
        
        return status

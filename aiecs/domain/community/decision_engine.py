"""
Community Decision Engine

Implements collective decision-making algorithms for agent communities,
including consensus building, voting mechanisms, and conflict resolution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import asyncio

from .models.community_models import (
    CommunityDecision, CommunityMember, AgentCommunity,
    DecisionStatus, GovernanceType
)
from ..core.exceptions.task_exceptions import TaskValidationError

logger = logging.getLogger(__name__)


class ConsensusAlgorithm(str, Enum):
    """Types of consensus algorithms."""
    SIMPLE_MAJORITY = "simple_majority"
    SUPERMAJORITY = "supermajority"
    UNANIMOUS = "unanimous"
    WEIGHTED_VOTING = "weighted_voting"
    DELEGATED_PROOF = "delegated_proof"


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    MEDIATION = "mediation"
    ARBITRATION = "arbitration"
    COMPROMISE = "compromise"
    ESCALATION = "escalation"


class DecisionEngine:
    """
    Engine for collective decision-making in agent communities.
    """

    def __init__(self, community_manager=None):
        """
        Initialize the decision engine.
        
        Args:
            community_manager: Reference to the community manager
        """
        self.community_manager = community_manager
        
        # Decision algorithms configuration
        self.consensus_algorithms = {
            ConsensusAlgorithm.SIMPLE_MAJORITY: self._simple_majority_consensus,
            ConsensusAlgorithm.SUPERMAJORITY: self._supermajority_consensus,
            ConsensusAlgorithm.UNANIMOUS: self._unanimous_consensus,
            ConsensusAlgorithm.WEIGHTED_VOTING: self._weighted_voting_consensus,
            ConsensusAlgorithm.DELEGATED_PROOF: self._delegated_proof_consensus
        }
        
        # Conflict resolution strategies
        self.conflict_resolvers = {
            ConflictResolutionStrategy.MEDIATION: self._mediation_resolution,
            ConflictResolutionStrategy.ARBITRATION: self._arbitration_resolution,
            ConflictResolutionStrategy.COMPROMISE: self._compromise_resolution,
            ConflictResolutionStrategy.ESCALATION: self._escalation_resolution
        }
        
        logger.info("Decision engine initialized")

    async def evaluate_decision(
        self,
        decision_id: str,
        community_id: str,
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate a community decision using the specified consensus algorithm.
        
        Args:
            decision_id: ID of the decision to evaluate
            community_id: ID of the community
            algorithm: Consensus algorithm to use
            
        Returns:
            Tuple of (decision_passed, evaluation_details)
        """
        if not self.community_manager:
            raise TaskValidationError("Community manager not available")
        
        decision = self.community_manager.decisions.get(decision_id)
        if not decision:
            raise TaskValidationError(f"Decision not found: {decision_id}")
        
        community = self.community_manager.communities.get(community_id)
        if not community:
            raise TaskValidationError(f"Community not found: {community_id}")
        
        # Get consensus algorithm function
        consensus_func = self.consensus_algorithms.get(algorithm)
        if not consensus_func:
            raise TaskValidationError(f"Unknown consensus algorithm: {algorithm}")
        
        # Evaluate decision
        result, details = await consensus_func(decision, community)
        
        # Update decision status based on result
        if result:
            decision.status = DecisionStatus.APPROVED
            logger.info(f"Decision {decision_id} approved by {algorithm}")
        else:
            decision.status = DecisionStatus.REJECTED
            logger.info(f"Decision {decision_id} rejected by {algorithm}")
        
        return result, details

    async def _simple_majority_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity
    ) -> Tuple[bool, Dict[str, Any]]:
        """Simple majority voting (>50%)."""
        total_votes = len(decision.votes_for) + len(decision.votes_against)
        votes_for = len(decision.votes_for)
        votes_against = len(decision.votes_against)
        
        if total_votes == 0:
            return False, {"reason": "No votes cast", "votes_for": 0, "votes_against": 0}
        
        majority_threshold = total_votes / 2
        passed = votes_for > majority_threshold
        
        details = {
            "algorithm": "simple_majority",
            "votes_for": votes_for,
            "votes_against": votes_against,
            "abstentions": len(decision.abstentions),
            "total_votes": total_votes,
            "threshold": majority_threshold,
            "passed": passed
        }
        
        return passed, details

    async def _supermajority_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity,
        threshold: float = 0.67
    ) -> Tuple[bool, Dict[str, Any]]:
        """Supermajority voting (default 67%)."""
        total_votes = len(decision.votes_for) + len(decision.votes_against)
        votes_for = len(decision.votes_for)
        
        if total_votes == 0:
            return False, {"reason": "No votes cast", "threshold": threshold}
        
        support_ratio = votes_for / total_votes
        passed = support_ratio >= threshold
        
        details = {
            "algorithm": "supermajority",
            "votes_for": votes_for,
            "votes_against": len(decision.votes_against),
            "abstentions": len(decision.abstentions),
            "total_votes": total_votes,
            "support_ratio": support_ratio,
            "threshold": threshold,
            "passed": passed
        }
        
        return passed, details

    async def _unanimous_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity
    ) -> Tuple[bool, Dict[str, Any]]:
        """Unanimous consensus (all votes must be 'for')."""
        votes_for = len(decision.votes_for)
        votes_against = len(decision.votes_against)
        total_members = len(community.members)
        
        # For unanimous consensus, we need all active members to vote 'for'
        # and no votes 'against'
        passed = votes_against == 0 and votes_for > 0
        
        details = {
            "algorithm": "unanimous",
            "votes_for": votes_for,
            "votes_against": votes_against,
            "abstentions": len(decision.abstentions),
            "total_members": total_members,
            "passed": passed
        }
        
        return passed, details

    async def _weighted_voting_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity
    ) -> Tuple[bool, Dict[str, Any]]:
        """Weighted voting based on member reputation and contribution."""
        if not self.community_manager:
            return False, {"reason": "Community manager not available"}
        
        weighted_for = 0.0
        weighted_against = 0.0
        total_weight = 0.0
        
        # Calculate weights for all votes
        for member_id in decision.votes_for:
            member = self.community_manager.members.get(member_id)
            if member:
                weight = self._calculate_member_weight(member)
                weighted_for += weight
                total_weight += weight
        
        for member_id in decision.votes_against:
            member = self.community_manager.members.get(member_id)
            if member:
                weight = self._calculate_member_weight(member)
                weighted_against += weight
                total_weight += weight
        
        if total_weight == 0:
            return False, {"reason": "No weighted votes", "total_weight": 0}
        
        support_ratio = weighted_for / total_weight
        passed = support_ratio > 0.5  # Weighted majority
        
        details = {
            "algorithm": "weighted_voting",
            "weighted_for": weighted_for,
            "weighted_against": weighted_against,
            "total_weight": total_weight,
            "support_ratio": support_ratio,
            "passed": passed
        }
        
        return passed, details

    async def _delegated_proof_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity
    ) -> Tuple[bool, Dict[str, Any]]:
        """Delegated proof consensus (leaders and coordinators have more weight)."""
        if not self.community_manager:
            return False, {"reason": "Community manager not available"}
        
        leader_votes_for = 0
        leader_votes_against = 0
        coordinator_votes_for = 0
        coordinator_votes_against = 0
        regular_votes_for = 0
        regular_votes_against = 0
        
        # Count votes by role
        for member_id in decision.votes_for:
            member = self.community_manager.members.get(member_id)
            if member:
                if member_id in community.leaders:
                    leader_votes_for += 1
                elif member_id in community.coordinators:
                    coordinator_votes_for += 1
                else:
                    regular_votes_for += 1
        
        for member_id in decision.votes_against:
            member = self.community_manager.members.get(member_id)
            if member:
                if member_id in community.leaders:
                    leader_votes_against += 1
                elif member_id in community.coordinators:
                    coordinator_votes_against += 1
                else:
                    regular_votes_against += 1
        
        # Calculate weighted score (leaders: 3x, coordinators: 2x, regular: 1x)
        score_for = (leader_votes_for * 3) + (coordinator_votes_for * 2) + regular_votes_for
        score_against = (leader_votes_against * 3) + (coordinator_votes_against * 2) + regular_votes_against
        
        total_score = score_for + score_against
        passed = total_score > 0 and score_for > score_against
        
        details = {
            "algorithm": "delegated_proof",
            "leader_votes_for": leader_votes_for,
            "leader_votes_against": leader_votes_against,
            "coordinator_votes_for": coordinator_votes_for,
            "coordinator_votes_against": coordinator_votes_against,
            "regular_votes_for": regular_votes_for,
            "regular_votes_against": regular_votes_against,
            "score_for": score_for,
            "score_against": score_against,
            "passed": passed
        }
        
        return passed, details

    def _calculate_member_weight(self, member: CommunityMember) -> float:
        """Calculate voting weight for a member based on reputation and contribution."""
        base_weight = 1.0
        reputation_bonus = member.reputation * 0.5  # Up to 50% bonus for reputation
        contribution_bonus = member.contribution_score * 0.3  # Up to 30% bonus for contribution
        
        return base_weight + reputation_bonus + contribution_bonus

    async def resolve_conflict(
        self,
        decision_id: str,
        community_id: str,
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MEDIATION
    ) -> Dict[str, Any]:
        """
        Resolve conflicts in community decisions.
        
        Args:
            decision_id: ID of the decision with conflict
            community_id: ID of the community
            strategy: Conflict resolution strategy
            
        Returns:
            Resolution details
        """
        resolver_func = self.conflict_resolvers.get(strategy)
        if not resolver_func:
            raise TaskValidationError(f"Unknown conflict resolution strategy: {strategy}")
        
        return await resolver_func(decision_id, community_id)

    async def _mediation_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """Mediation-based conflict resolution."""
        # TODO: Implement mediation logic
        return {"strategy": "mediation", "status": "pending", "mediator": None}

    async def _arbitration_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """Arbitration-based conflict resolution."""
        # TODO: Implement arbitration logic
        return {"strategy": "arbitration", "status": "pending", "arbitrator": None}

    async def _compromise_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """Compromise-based conflict resolution."""
        # TODO: Implement compromise logic
        return {"strategy": "compromise", "status": "pending", "compromise_proposal": None}

    async def _escalation_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """Escalation-based conflict resolution."""
        # TODO: Implement escalation logic
        return {"strategy": "escalation", "status": "pending", "escalation_level": 1}

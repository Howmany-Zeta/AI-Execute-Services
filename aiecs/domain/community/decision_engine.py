"""
Community Decision Engine

Implements collective decision-making algorithms for agent communities,
including consensus building, voting mechanisms, and conflict resolution.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from .models.community_models import (
    CommunityDecision,
    CommunityMember,
    AgentCommunity,
    DecisionStatus,
)
from .exceptions import CommunityValidationError as TaskValidationError

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
            ConsensusAlgorithm.DELEGATED_PROOF: self._delegated_proof_consensus,
        }

        # Conflict resolution strategies
        self.conflict_resolvers = {
            ConflictResolutionStrategy.MEDIATION: self._mediation_resolution,
            ConflictResolutionStrategy.ARBITRATION: self._arbitration_resolution,
            ConflictResolutionStrategy.COMPROMISE: self._compromise_resolution,
            ConflictResolutionStrategy.ESCALATION: self._escalation_resolution,
        }

        logger.info("Decision engine initialized")

    async def evaluate_decision(
        self,
        decision_id: str,
        community_id: str,
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.SIMPLE_MAJORITY,
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

    async def _simple_majority_consensus(self, decision: CommunityDecision, community: AgentCommunity) -> Tuple[bool, Dict[str, Any]]:
        """Simple majority voting (>50%)."""
        total_votes = len(decision.votes_for) + len(decision.votes_against)
        votes_for = len(decision.votes_for)
        votes_against = len(decision.votes_against)

        if total_votes == 0:
            return False, {
                "reason": "No votes cast",
                "votes_for": 0,
                "votes_against": 0,
            }

        majority_threshold = total_votes / 2
        passed = votes_for > majority_threshold

        details = {
            "algorithm": "simple_majority",
            "votes_for": votes_for,
            "votes_against": votes_against,
            "abstentions": len(decision.abstentions),
            "total_votes": total_votes,
            "threshold": majority_threshold,
            "passed": passed,
        }

        return passed, details

    async def _supermajority_consensus(
        self,
        decision: CommunityDecision,
        community: AgentCommunity,
        threshold: float = 0.67,
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
            "passed": passed,
        }

        return passed, details

    async def _unanimous_consensus(self, decision: CommunityDecision, community: AgentCommunity) -> Tuple[bool, Dict[str, Any]]:
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
            "passed": passed,
        }

        return passed, details

    async def _weighted_voting_consensus(self, decision: CommunityDecision, community: AgentCommunity) -> Tuple[bool, Dict[str, Any]]:
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
            "passed": passed,
        }

        return passed, details

    async def _delegated_proof_consensus(self, decision: CommunityDecision, community: AgentCommunity) -> Tuple[bool, Dict[str, Any]]:
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
            "passed": passed,
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
        strategy: ConflictResolutionStrategy = ConflictResolutionStrategy.MEDIATION,
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
        """
        Mediation-based conflict resolution.

        Process:
        1. Select neutral mediator (high reputation, not involved in voting)
        2. Facilitate structured discussion between opposing sides
        3. Identify core concerns and interests
        4. Propose compromise solutions
        5. Build consensus on mediated outcome
        """
        if not self.community_manager:
            return {
                "strategy": "mediation",
                "status": "failed",
                "reason": "Community manager not available",
            }

        decision = self.community_manager.decisions.get(decision_id)
        community = self.community_manager.communities.get(community_id)

        if not decision or not community:
            return {
                "strategy": "mediation",
                "status": "failed",
                "reason": "Decision or community not found",
            }

        # Step 1: Select mediator
        mediator_id = await self._select_mediator(decision, community)
        if not mediator_id:
            return {
                "strategy": "mediation",
                "status": "failed",
                "reason": "No suitable mediator found",
            }

        # Step 2: Identify opposing sides
        for_side = decision.votes_for
        against_side = decision.votes_against

        # Step 3: Analyze core concerns (simulate by examining vote
        # distribution)
        concerns = {
            "support_concerns": self._extract_concerns(for_side, community),
            "opposition_concerns": self._extract_concerns(against_side, community),
        }

        # Step 4: Propose compromise
        compromise_proposal = {
            "original_proposal": decision.title,
            "modifications": [
                "Address key concerns from opposition",
                "Maintain core value from supporters",
                "Add safeguards or conditions",
                "Phased implementation approach",
            ],
            "mediator_recommendation": "Modified proposal with balanced approach",
        }

        # Step 5: Set up for re-vote
        result = {
            "strategy": "mediation",
            "status": "mediation_completed",
            "mediator_id": mediator_id,
            "mediator": (self.community_manager.members.get(mediator_id).agent_id if mediator_id else None),
            "concerns_identified": concerns,
            "compromise_proposal": compromise_proposal,
            "next_steps": "Re-vote on mediated proposal",
            "recommended_threshold": "simple_majority",
        }

        logger.info(f"Mediation completed for decision {decision_id} by mediator {mediator_id}")
        return result

    async def _select_mediator(self, decision: CommunityDecision, community: AgentCommunity) -> Optional[str]:
        """Select a neutral mediator for conflict resolution."""
        # Find members who didn't vote or abstained, with high reputation
        candidates = []

        all_voters = set(decision.votes_for + decision.votes_against)

        for member_id in community.members:
            if member_id not in all_voters:
                member = self.community_manager.members.get(member_id)
                if member and member.reputation > 0.5:  # High reputation threshold
                    candidates.append((member_id, member.reputation))

        # Also consider abstentions with very high reputation
        for member_id in decision.abstentions:
            member = self.community_manager.members.get(member_id)
            if member and member.reputation > 0.7:
                candidates.append((member_id, member.reputation))

        if not candidates:
            return None

        # Select highest reputation member
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _extract_concerns(self, voter_ids: List[str], community: AgentCommunity) -> List[str]:
        """Extract concerns from voter groups based on their roles and specializations."""
        concerns = []
        role_distribution: Dict[str, int] = {}

        for voter_id in voter_ids:
            member = self.community_manager.members.get(voter_id) if self.community_manager else None
            if member:
                role = member.community_role.value
                role_distribution[role] = role_distribution.get(role, 0) + 1

        # Generate concerns based on roles
        if "leader" in role_distribution:
            concerns.append("Strategic alignment and governance impact")
        if "specialist" in role_distribution:
            concerns.append("Technical feasibility and implementation details")
        if "contributor" in role_distribution:
            concerns.append("Practical implications and workload impact")

        return concerns if concerns else ["General concerns about proposal"]

    async def _arbitration_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """
        Arbitration-based conflict resolution.

        Process:
        1. Select authoritative arbitrator (leader or senior coordinator)
        2. Review all arguments and evidence
        3. Make binding decision
        4. Provide detailed rationale
        """
        if not self.community_manager:
            return {
                "strategy": "arbitration",
                "status": "failed",
                "reason": "Community manager not available",
            }

        decision = self.community_manager.decisions.get(decision_id)
        community = self.community_manager.communities.get(community_id)

        if not decision or not community:
            return {
                "strategy": "arbitration",
                "status": "failed",
                "reason": "Decision or community not found",
            }

        # Step 1: Select arbitrator (prefer leader, then coordinator with
        # highest reputation)
        arbitrator_id = await self._select_arbitrator(community)
        if not arbitrator_id:
            return {
                "strategy": "arbitration",
                "status": "failed",
                "reason": "No suitable arbitrator found",
            }

        # Step 2: Analyze decision context
        votes_for = len(decision.votes_for)
        votes_against = len(decision.votes_against)
        total_votes = votes_for + votes_against

        # Step 3: Make arbitration decision (simulate based on vote distribution and priority)
        # In practice, this would involve the actual arbitrator's judgment
        support_ratio = votes_for / total_votes if total_votes > 0 else 0

        # Arbitrator considers: vote distribution, decision priority, community
        # impact
        # Lower threshold with rationale
        arbitration_decision = "approved" if support_ratio >= 0.4 else "rejected"

        # Step 4: Provide rationale
        rationale = self._generate_arbitration_rationale(arbitration_decision, support_ratio, decision, community)

        result = {
            "strategy": "arbitration",
            "status": "arbitration_completed",
            "arbitrator_id": arbitrator_id,
            "arbitrator": (self.community_manager.members.get(arbitrator_id).agent_id if arbitrator_id else None),
            "binding_decision": arbitration_decision,
            "rationale": rationale,
            "votes_for": votes_for,
            "votes_against": votes_against,
            "support_ratio": support_ratio,
            "is_binding": True,
            "appeal_allowed": False,
        }

        # Update decision status based on arbitration
        if arbitration_decision == "approved":
            decision.status = DecisionStatus.APPROVED
        else:
            decision.status = DecisionStatus.REJECTED

        logger.info(f"Arbitration completed for decision {decision_id}: {arbitration_decision}")
        return result

    async def _select_arbitrator(self, community: AgentCommunity) -> Optional[str]:
        """Select an authoritative arbitrator."""
        # Prefer leaders first
        if community.leaders:
            # Select leader with highest reputation
            best_leader = None
            best_reputation = -1

            for leader_id in community.leaders:
                member = self.community_manager.members.get(leader_id)
                if member and member.reputation > best_reputation:
                    best_reputation = member.reputation
                    best_leader = leader_id

            if best_leader:
                return best_leader

        # Fall back to coordinators
        if community.coordinators:
            best_coordinator = None
            best_reputation = -1

            for coordinator_id in community.coordinators:
                member = self.community_manager.members.get(coordinator_id)
                if member and member.reputation > best_reputation:
                    best_reputation = member.reputation
                    best_coordinator = coordinator_id

            if best_coordinator:
                return best_coordinator

        return None

    def _generate_arbitration_rationale(
        self,
        decision: str,
        support_ratio: float,
        proposal: CommunityDecision,
        community: AgentCommunity,
    ) -> str:
        """Generate detailed rationale for arbitration decision."""
        rationale_parts = []

        rationale_parts.append(f"After careful review of the proposal '{proposal.title}', ")
        rationale_parts.append(f"with {support_ratio:.1%} support from voting members, ")

        if decision == "approved":
            rationale_parts.append("this arbitration approves the proposal. ")
            rationale_parts.append("The decision aligns with community interests and demonstrates sufficient support. ")
            if support_ratio < 0.5:
                rationale_parts.append("While not achieving majority, the strategic importance warrants approval. ")
        else:
            rationale_parts.append("this arbitration rejects the proposal. ")
            rationale_parts.append("The concerns raised outweigh the benefits, and insufficient consensus exists. ")

        rationale_parts.append(f"Priority level: {proposal.priority}. ")
        rationale_parts.append("This decision is binding and final.")

        return "".join(rationale_parts)

    async def _compromise_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """
        Compromise-based conflict resolution.

        Process:
        1. Analyze opposing positions
        2. Identify negotiable vs non-negotiable elements
        3. Generate compromise alternatives
        4. Create hybrid solution
        5. Test acceptance with stakeholders
        """
        if not self.community_manager:
            return {
                "strategy": "compromise",
                "status": "failed",
                "reason": "Community manager not available",
            }

        decision = self.community_manager.decisions.get(decision_id)
        community = self.community_manager.communities.get(community_id)

        if not decision or not community:
            return {
                "strategy": "compromise",
                "status": "failed",
                "reason": "Decision or community not found",
            }

        votes_for = len(decision.votes_for)
        votes_against = len(decision.votes_against)
        total_votes = votes_for + votes_against

        if total_votes == 0:
            return {
                "strategy": "compromise",
                "status": "failed",
                "reason": "No votes to analyze",
            }

        # Step 1: Analyze positions
        support_ratio = votes_for / total_votes
        opposition_ratio = votes_against / total_votes

        position_analysis = {
            "support_strength": support_ratio,
            "opposition_strength": opposition_ratio,
            "balance": ("balanced" if 0.4 <= support_ratio <= 0.6 else "polarized"),
        }

        # Step 2: Identify elements
        elements = {
            "core_proposal": decision.title,
            "negotiable_elements": [
                "Implementation timeline",
                "Resource allocation",
                "Scope limitations",
                "Review checkpoints",
            ],
            "non_negotiable_elements": [
                "Core objectives",
                "Safety requirements",
                "Community values alignment",
            ],
        }

        # Step 3 & 4: Generate compromise alternatives
        compromise_options = []

        # Option 1: Phased approach
        compromise_options.append(
            {
                "option": "phased_implementation",
                "description": "Implement in phases with review points",
                "modifications": [
                    "Start with pilot/trial phase",
                    "Review after initial phase",
                    "Full rollout conditional on pilot success",
                ],
                "acceptance_probability": 0.75,
            }
        )

        # Option 2: Conditional approval
        compromise_options.append(
            {
                "option": "conditional_approval",
                "description": "Approve with conditions addressing concerns",
                "modifications": [
                    "Add oversight committee",
                    "Include opposition representatives",
                    "Establish success metrics and review schedule",
                ],
                "acceptance_probability": 0.70,
            }
        )

        # Option 3: Scaled-down version
        compromise_options.append(
            {
                "option": "scaled_down",
                "description": "Reduced scope addressing primary concerns",
                "modifications": [
                    "Limit scope to less contentious areas",
                    "Reduce resource commitment",
                    "Extend timeline for gradual adoption",
                ],
                "acceptance_probability": 0.65,
            }
        )

        # Select best compromise based on vote distribution
        recommended_option = compromise_options[0] if support_ratio > 0.45 else compromise_options[2]

        result = {
            "strategy": "compromise",
            "status": "compromise_proposed",
            "position_analysis": position_analysis,
            "elements": elements,
            "compromise_options": compromise_options,
            "recommended_option": recommended_option,
            "next_steps": "Review compromise options and vote on preferred alternative",
            "requires_revote": True,
            "expected_consensus": recommended_option["acceptance_probability"],
        }

        logger.info(f"Compromise resolution generated for decision {decision_id}")
        return result

    async def _escalation_resolution(self, decision_id: str, community_id: str) -> Dict[str, Any]:
        """
        Escalation-based conflict resolution.

        Process:
        1. Determine current escalation level
        2. Escalate to higher authority/broader group
        3. Apply progressively stronger resolution mechanisms
        4. Track escalation path and outcomes

        Escalation Levels:
        - Level 1: Community-wide discussion and re-vote
        - Level 2: Coordinator council review
        - Level 3: Leader decision
        - Level 4: External arbitration or parent community
        """
        if not self.community_manager:
            return {
                "strategy": "escalation",
                "status": "failed",
                "reason": "Community manager not available",
            }

        decision = self.community_manager.decisions.get(decision_id)
        community = self.community_manager.communities.get(community_id)

        if not decision or not community:
            return {
                "strategy": "escalation",
                "status": "failed",
                "reason": "Decision or community not found",
            }

        # Determine current escalation level from metadata
        current_level = decision.metadata.get("escalation_level", 0)
        next_level = current_level + 1

        # Define escalation path
        escalation_path = {
            1: {
                "level": 1,
                "name": "Community Discussion",
                "authority": "All active members",
                "process": "Open discussion with extended voting period",
                "threshold": "supermajority (67%)",
                "timeline": "7 days",
            },
            2: {
                "level": 2,
                "name": "Coordinator Council",
                "authority": "Community coordinators",
                "process": "Coordinator review and recommendation",
                "threshold": "coordinator consensus",
                "timeline": "3 days",
            },
            3: {
                "level": 3,
                "name": "Leadership Decision",
                "authority": "Community leaders",
                "process": "Leadership panel makes binding decision",
                "threshold": "leader majority or single leader decision",
                "timeline": "1 day",
            },
            4: {
                "level": 4,
                "name": "External Review",
                "authority": "External arbitrator or parent community",
                "process": "Independent third-party review",
                "threshold": "external arbitrator decision",
                "timeline": "As needed",
            },
        }

        if next_level > 4:
            return {
                "strategy": "escalation",
                "status": "max_escalation_reached",
                "message": "Maximum escalation level reached. Decision must be resolved or abandoned.",
                "recommendation": "Consider abandoning or significantly revising the proposal",
            }

        current_escalation = escalation_path[next_level]

        # Determine escalation authority
        authority_members = []
        if next_level == 1:
            authority_members = community.members
        elif next_level == 2:
            authority_members = community.coordinators
        elif next_level == 3:
            authority_members = community.leaders
        elif next_level == 4:
            authority_members = []  # External

        # Update decision metadata
        decision.metadata["escalation_level"] = next_level
        decision.metadata["escalation_timestamp"] = datetime.utcnow().isoformat()
        decision.metadata["escalation_history"] = decision.metadata.get("escalation_history", [])
        decision.metadata["escalation_history"].append(
            {
                "from_level": current_level,
                "to_level": next_level,
                "timestamp": datetime.utcnow().isoformat(),
                "reason": "Unresolved conflict",
            }
        )

        result = {
            "strategy": "escalation",
            "status": "escalated",
            "previous_level": current_level,
            "current_level": next_level,
            "escalation_details": current_escalation,
            "authority_members": authority_members,
            "authority_count": len(authority_members),
            "escalation_history": decision.metadata["escalation_history"],
            "next_steps": f"Proceed with {current_escalation['name']} process",
            "required_action": current_escalation["process"],
            "decision_threshold": current_escalation["threshold"],
            "timeline": current_escalation["timeline"],
        }

        # Reset voting for re-evaluation at new level
        if next_level < 4:
            decision.votes_for = []
            decision.votes_against = []
            decision.abstentions = []
            decision.status = DecisionStatus.PROPOSED
            timeline_str = current_escalation.get("timeline", "0 days")
            if isinstance(timeline_str, str):
                decision.voting_ends_at = datetime.utcnow() + timedelta(days=int(timeline_str.split()[0]))
            else:
                decision.voting_ends_at = datetime.utcnow() + timedelta(days=7)  # Default to 7 days

        logger.info(f"Decision {decision_id} escalated to level {next_level}: {current_escalation['name']}")
        return result

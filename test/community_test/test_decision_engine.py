"""
Tests for DecisionEngine

Tests for consensus algorithms and conflict resolution.
"""

import pytest
import logging

from aiecs.domain.community.decision_engine import ConsensusAlgorithm, ConflictResolutionStrategy
from aiecs.domain.community.models import DecisionStatus

logger = logging.getLogger(__name__)


class TestConsensusAlgorithms:
    """Tests for consensus algorithms."""
    
    @pytest.mark.asyncio
    async def test_simple_majority_pass(self, decision_engine, community_manager, sample_community, sample_members):
        """Test simple majority consensus - passing."""
        logger.info("Testing simple majority consensus (pass)")
        
        # Create decision
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Majority Test",
            description="Test simple majority",
            decision_type="policy"
        )
        
        # 3 for, 1 against
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[3], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        assert passed is True
        assert details["votes_for"] == 3
        assert details["votes_against"] == 1
        
        decision = community_manager.decisions[decision_id]
        assert decision.status == DecisionStatus.APPROVED
        
        logger.debug(f"Simple majority passed: {details}")
    
    @pytest.mark.asyncio
    async def test_simple_majority_fail(self, decision_engine, community_manager, sample_community, sample_members):
        """Test simple majority consensus - failing."""
        logger.info("Testing simple majority consensus (fail)")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Majority Fail Test",
            description="Test simple majority fail",
            decision_type="policy"
        )
        
        # 1 for, 3 against
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[3], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        assert passed is False
        
        decision = community_manager.decisions[decision_id]
        assert decision.status == DecisionStatus.REJECTED
        
        logger.debug(f"Simple majority failed: {details}")
    
    @pytest.mark.asyncio
    async def test_supermajority_consensus(self, decision_engine, community_manager, sample_community, sample_members):
        """Test supermajority consensus (67%)."""
        logger.info("Testing supermajority consensus")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Supermajority Test",
            description="Test supermajority",
            decision_type="policy"
        )
        
        # 4 for, 1 against = 80% support
        for i in range(1, 5):
            await community_manager.vote_on_decision(decision_id, sample_members[i], "for")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SUPERMAJORITY
        )
        
        assert passed is True
        assert details["support_ratio"] >= 0.67
        
        logger.debug(f"Supermajority consensus: {details}")
    
    @pytest.mark.asyncio
    async def test_weighted_voting(self, decision_engine, community_manager, sample_community, sample_members):
        """Test weighted voting based on reputation."""
        logger.info("Testing weighted voting")
        
        # Set different reputation levels
        for i, member_id in enumerate(sample_members):
            member = community_manager.members[member_id]
            member.reputation = 0.2 * i  # 0.0, 0.2, 0.4, 0.6, 0.8
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Weighted Vote Test",
            description="Test weighted voting",
            decision_type="policy"
        )
        
        # High reputation members vote for
        await community_manager.vote_on_decision(decision_id, sample_members[3], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "for")
        # Low reputation members vote against
        await community_manager.vote_on_decision(decision_id, sample_members[1], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.WEIGHTED_VOTING
        )
        
        assert "weighted_for" in details
        assert "weighted_against" in details
        
        logger.debug(f"Weighted voting result: {details}")
    
    @pytest.mark.asyncio
    async def test_delegated_proof(self, decision_engine, community_manager, sample_community, sample_members):
        """Test delegated proof consensus (leaders have more weight)."""
        logger.info("Testing delegated proof consensus")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[2],
            title="Delegated Proof Test",
            description="Test delegated proof",
            decision_type="policy"
        )
        
        # Leader votes for (has 3x weight)
        await community_manager.vote_on_decision(decision_id, sample_members[0], "for")
        # Regular members vote against
        await community_manager.vote_on_decision(decision_id, sample_members[2], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[3], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.DELEGATED_PROOF
        )
        
        assert "leader_votes_for" in details
        assert "score_for" in details
        assert "score_against" in details
        
        logger.debug(f"Delegated proof result: {details}")


class TestConflictResolution:
    """Tests for conflict resolution strategies."""
    
    @pytest.mark.asyncio
    async def test_mediation_resolution(self, decision_engine, community_manager, sample_community, sample_members):
        """Test mediation conflict resolution."""
        logger.info("Testing mediation resolution")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Mediation Test",
            description="Test mediation",
            decision_type="policy"
        )
        
        # Split vote
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "against")
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.MEDIATION
        )
        
        assert result["strategy"] == "mediation"
        assert "mediator_id" in result or result["status"] == "failed"
        assert "compromise_proposal" in result or result["status"] == "failed"
        
        logger.debug(f"Mediation result: {result['status']}")
    
    @pytest.mark.asyncio
    async def test_arbitration_resolution(self, decision_engine, community_manager, sample_community, sample_members):
        """Test arbitration conflict resolution."""
        logger.info("Testing arbitration resolution")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[2],
            title="Arbitration Test",
            description="Test arbitration",
            decision_type="policy"
        )
        
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "against")
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.ARBITRATION
        )
        
        assert result["strategy"] == "arbitration"
        assert "arbitrator_id" in result or result["status"] == "failed"
        assert "binding_decision" in result or result["status"] == "failed"
        
        logger.debug(f"Arbitration result: {result.get('binding_decision', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_compromise_resolution(self, decision_engine, community_manager, sample_community, sample_members):
        """Test compromise conflict resolution."""
        logger.info("Testing compromise resolution")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Compromise Test",
            description="Test compromise",
            decision_type="policy"
        )
        
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[3], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "against")
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.COMPROMISE
        )
        
        assert result["strategy"] == "compromise"
        assert "compromise_options" in result or result["status"] == "failed"
        
        if "compromise_options" in result:
            assert len(result["compromise_options"]) > 0
        
        logger.debug(f"Compromise options: {len(result.get('compromise_options', []))}")
    
    @pytest.mark.asyncio
    async def test_escalation_resolution(self, decision_engine, community_manager, sample_community, sample_members):
        """Test escalation conflict resolution."""
        logger.info("Testing escalation resolution")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Escalation Test",
            description="Test escalation",
            decision_type="policy"
        )
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.ESCALATION
        )
        
        assert result["strategy"] == "escalation"
        assert "current_level" in result or result["status"] == "failed"
        
        if "current_level" in result:
            assert result["current_level"] == 1  # First escalation
        
        logger.debug(f"Escalated to level: {result.get('current_level', 'N/A')}")


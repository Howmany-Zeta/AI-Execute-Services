"""
Extended Tests for Decision Engine

Additional tests to improve coverage and test edge cases.
"""

import pytest
import logging

from aiecs.domain.community.decision_engine import ConsensusAlgorithm, ConflictResolutionStrategy
from aiecs.domain.community.models import DecisionStatus, CommunityRole, CommunityMember

logger = logging.getLogger(__name__)


class TestUnanimousConsensus:
    """Tests for unanimous consensus algorithm."""
    
    @pytest.mark.asyncio
    async def test_unanimous_all_for(self, decision_engine, community_manager, sample_community, sample_members):
        """Test unanimous consensus when all vote for."""
        logger.info("Testing unanimous consensus - all for")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Unanimous Test",
            description="Test unanimous voting",
            decision_type="policy"
        )
        
        # All members vote for
        for member_id in sample_members:
            await community_manager.vote_on_decision(decision_id, member_id, "for")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.UNANIMOUS
        )
        
        assert passed is True
        assert details["votes_against"] == 0
        assert details["votes_for"] == len(sample_members)
        
        decision = community_manager.decisions[decision_id]
        assert decision.status == DecisionStatus.APPROVED
        
        logger.debug(f"Unanimous consensus passed: {details}")
    
    @pytest.mark.asyncio
    async def test_unanimous_one_against(self, decision_engine, community_manager, sample_community, sample_members):
        """Test unanimous consensus fails with one opposition."""
        logger.info("Testing unanimous consensus - one against")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Unanimous Fail Test",
            description="Test unanimous with opposition",
            decision_type="policy"
        )
        
        # Most vote for, one against
        for member_id in sample_members[:-1]:
            await community_manager.vote_on_decision(decision_id, member_id, "for")
        await community_manager.vote_on_decision(decision_id, sample_members[-1], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.UNANIMOUS
        )
        
        assert passed is False
        assert details["votes_against"] > 0
        
        decision = community_manager.decisions[decision_id]
        assert decision.status == DecisionStatus.REJECTED
        
        logger.debug(f"Unanimous consensus failed: {details}")


class TestEdgeCases:
    """Tests for edge cases in decision making."""
    
    @pytest.mark.asyncio
    async def test_no_votes_cast(self, decision_engine, community_manager, sample_community, sample_members):
        """Test decision evaluation with no votes."""
        logger.info("Testing no votes cast")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="No Votes Test",
            description="Test with no votes",
            decision_type="policy"
        )
        
        # Don't cast any votes
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        assert passed is False
        assert "No votes cast" in details["reason"]
        
        logger.debug("No votes case handled correctly")
    
    @pytest.mark.asyncio
    async def test_all_abstentions(self, decision_engine, community_manager, sample_community, sample_members):
        """Test when all members abstain."""
        logger.info("Testing all abstentions")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="All Abstain Test",
            description="Test all abstaining",
            decision_type="policy"
        )
        
        for member_id in sample_members:
            await community_manager.vote_on_decision(decision_id, member_id, "abstain")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        assert passed is False
        # When everyone abstains, there are no actual votes
        if "total_votes" in details:
            assert details["total_votes"] == 0
        if "abstentions" in details:
            assert details["abstentions"] == len(sample_members)
        
        logger.debug("All abstentions handled correctly")
    
    @pytest.mark.asyncio
    async def test_tie_vote(self, decision_engine, community_manager, sample_community, sample_members):
        """Test tie vote scenario."""
        logger.info("Testing tie vote")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Tie Test",
            description="Test tie vote",
            decision_type="policy"
        )
        
        # 2 for, 2 against (exactly 50%)
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[2], "for")
        await community_manager.vote_on_decision(decision_id, sample_members[3], "against")
        await community_manager.vote_on_decision(decision_id, sample_members[4], "against")
        
        passed, details = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        # Simple majority requires >50%, so tie should fail
        assert passed is False
        assert details["votes_for"] == details["votes_against"]
        
        logger.debug("Tie vote handled correctly - requires majority")


class TestWeightCalculation:
    """Tests for member weight calculation."""
    
    @pytest.mark.asyncio
    async def test_high_reputation_weight(self, decision_engine):
        """Test weight for high reputation member."""
        logger.info("Testing high reputation weight calculation")
        
        from aiecs.domain.community.models import CommunityRole
        from datetime import datetime
        
        member = CommunityMember(
            member_id="test_high_rep",
            agent_id="test_agent",
            agent_role="expert",
            community_role=CommunityRole.SPECIALIST,
            reputation=1.0,  # Maximum reputation
            contribution_score=1.0,  # Maximum contribution
            joined_at=datetime.utcnow()
        )
        
        weight = decision_engine._calculate_member_weight(member)
        
        # Base (1.0) + reputation (1.0 * 0.5) + contribution (1.0 * 0.3)
        expected = 1.0 + 0.5 + 0.3
        assert abs(weight - expected) < 0.01
        assert weight == 1.8
        
        logger.debug(f"High reputation weight: {weight}")
    
    @pytest.mark.asyncio
    async def test_low_reputation_weight(self, decision_engine):
        """Test weight for low reputation member."""
        logger.info("Testing low reputation weight calculation")
        
        from aiecs.domain.community.models import CommunityRole
        from datetime import datetime
        
        member = CommunityMember(
            member_id="test_low_rep",
            agent_id="test_agent",
            agent_role="newcomer",
            community_role=CommunityRole.OBSERVER,
            reputation=0.0,
            contribution_score=0.0,
            joined_at=datetime.utcnow()
        )
        
        weight = decision_engine._calculate_member_weight(member)
        
        # Only base weight
        assert weight == 1.0
        
        logger.debug(f"Low reputation weight: {weight}")


class TestConflictResolutionEdgeCases:
    """Tests for edge cases in conflict resolution."""
    
    @pytest.mark.asyncio
    async def test_mediation_all_voted(self, decision_engine, community_manager, sample_community, sample_members):
        """Test mediation when all members voted - may have no suitable mediator."""
        logger.info("Testing mediation with all members voted")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="All Voted Test",
            description="Test mediation when all voted",
            decision_type="policy"
        )
        
        # All members vote
        for i, member_id in enumerate(sample_members):
            vote = "for" if i % 2 == 0 else "against"
            await community_manager.vote_on_decision(decision_id, member_id, vote)
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.MEDIATION
        )
        
        # Should complete or fail gracefully
        assert result["strategy"] == "mediation"
        assert "status" in result
        
        logger.debug(f"Mediation result: {result['status']}")
    
    @pytest.mark.asyncio
    async def test_escalation_level_progression(self, decision_engine, community_manager, sample_community, sample_members):
        """Test escalation progresses through levels."""
        logger.info("Testing escalation level progression")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Escalation Levels Test",
            description="Test escalation progression",
            decision_type="policy"
        )
        
        # First escalation - should go to level 1
        result1 = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.ESCALATION
        )
        
        assert result1["current_level"] == 1
        assert result1["previous_level"] == 0
        
        # Second escalation - should go to level 2
        result2 = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.ESCALATION
        )
        
        assert result2["current_level"] == 2
        assert result2["previous_level"] == 1
        
        logger.debug(f"Escalated from level {result1['current_level']} to {result2['current_level']}")
    
    @pytest.mark.asyncio
    async def test_escalation_max_level(self, decision_engine, community_manager, sample_community, sample_members):
        """Test escalation at maximum level."""
        logger.info("Testing max escalation level")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Max Escalation Test",
            description="Test max escalation",
            decision_type="policy"
        )
        
        decision = community_manager.decisions[decision_id]
        # Set to level 4 already
        decision.metadata["escalation_level"] = 4
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=sample_community,
            strategy=ConflictResolutionStrategy.ESCALATION
        )
        
        assert result["status"] == "max_escalation_reached"
        assert "Maximum escalation level reached" in result["message"]
        
        logger.debug("Max escalation handled correctly")
    
    @pytest.mark.asyncio
    async def test_arbitration_no_leaders(self, decision_engine, community_manager, sample_community, sample_members):
        """Test arbitration when no leaders exist."""
        logger.info("Testing arbitration without leaders")
        
        # Create a community without leaders
        community_id = await community_manager.create_community(
            name="No Leader Community",
            description="Community without leaders"
        )
        
        # Add only contributors (no leaders)
        member_ids = []
        for i in range(3):
            mid = await community_manager.add_member_to_community(
                community_id=community_id,
                agent_id=f"contributor_{i}",
                agent_role="contributor",
                community_role=CommunityRole.CONTRIBUTOR
            )
            member_ids.append(mid)
        
        decision_id = await community_manager.propose_decision(
            community_id=community_id,
            proposer_member_id=member_ids[0],
            title="No Leader Arbitration",
            description="Test",
            decision_type="policy"
        )
        
        result = await decision_engine.resolve_conflict(
            decision_id=decision_id,
            community_id=community_id,
            strategy=ConflictResolutionStrategy.ARBITRATION
        )
        
        # Should fail or handle gracefully
        assert result["strategy"] == "arbitration"
        
        logger.debug(f"Arbitration without leaders: {result['status']}")


class TestAlgorithmCombinations:
    """Tests for using different algorithms in sequence."""
    
    @pytest.mark.asyncio
    async def test_algorithm_progression(self, decision_engine, community_manager, sample_community, sample_members):
        """Test using different algorithms in sequence on same decision."""
        logger.info("Testing algorithm progression")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Algorithm Progression Test",
            description="Test multiple algorithms",
            decision_type="policy"
        )
        
        # Cast votes: 3 for, 2 against (60% support)
        for i, member_id in enumerate(sample_members):
            vote = "for" if i < 3 else "against"
            await community_manager.vote_on_decision(decision_id, member_id, vote)
        
        # Test simple majority (>50%)
        passed1, details1 = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        assert passed1 is True
        logger.debug(f"Simple majority: {passed1}")
        
        # Reset status for next test
        decision = community_manager.decisions[decision_id]
        decision.status = DecisionStatus.VOTING
        
        # Test supermajority (67%)
        passed2, details2 = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.SUPERMAJORITY
        )
        assert passed2 is False  # 60% < 67%
        logger.debug(f"Supermajority: {passed2}")
        
        # Reset status
        decision.status = DecisionStatus.VOTING
        
        # Test unanimous
        passed3, details3 = await decision_engine.evaluate_decision(
            decision_id=decision_id,
            community_id=sample_community,
            algorithm=ConsensusAlgorithm.UNANIMOUS
        )
        assert passed3 is False  # Has opposition
        logger.debug(f"Unanimous: {passed3}")
        
        logger.info("Algorithm progression completed")


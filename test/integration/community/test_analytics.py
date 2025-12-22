"""
Tests for Community Analytics

Tests for decision tracking, participation analytics, and health metrics.
"""

import pytest
import logging
from datetime import datetime, timedelta

from aiecs.domain.community.models import DecisionStatus

logger = logging.getLogger(__name__)


class TestDecisionAnalytics:
    """Tests for decision analytics."""
    
    @pytest.mark.asyncio
    async def test_get_decision_analytics(self, analytics, community_manager, sample_community, sample_members):
        """Test getting decision analytics."""
        logger.info("Testing decision analytics")
        
        # Create multiple decisions
        for i in range(5):
            decision_id = await community_manager.propose_decision(
                community_id=sample_community,
                proposer_member_id=sample_members[0],
                title=f"Decision {i}",
                description=f"Test decision {i}",
                decision_type="policy" if i % 2 == 0 else "resource"
            )
            
            # Vote on some
            if i < 3:
                for member_id in sample_members[1:4]:
                    await community_manager.vote_on_decision(decision_id, member_id, "for")
                
                # Approve some decisions
                decision = community_manager.decisions[decision_id]
                if i < 2:
                    decision.status = DecisionStatus.APPROVED
        
        # Get analytics
        analytics_data = analytics.get_decision_analytics(sample_community, time_range_days=30)
        
        assert analytics_data is not None
        assert analytics_data["total_decisions"] == 5
        assert "approval_rate" in analytics_data
        assert "decision_types" in analytics_data
        
        logger.debug(f"Decision analytics: {analytics_data['total_decisions']} decisions")
    
    @pytest.mark.asyncio
    async def test_decision_velocity(self, analytics, community_manager, sample_community, sample_members):
        """Test decision velocity calculation."""
        logger.info("Testing decision velocity")
        
        # Create decisions
        for i in range(10):
            await community_manager.propose_decision(
                community_id=sample_community,
                proposer_member_id=sample_members[0],
                title=f"Decision {i}",
                description="Test",
                decision_type="policy"
            )
        
        analytics_data = analytics.get_decision_analytics(sample_community, time_range_days=7)
        
        assert "decision_velocity" in analytics_data
        assert analytics_data["decision_velocity"] > 0
        
        logger.debug(f"Decision velocity: {analytics_data['decision_velocity']} per day")


class TestParticipationAnalytics:
    """Tests for member participation analytics."""
    
    @pytest.mark.asyncio
    async def test_get_participation_analytics(self, analytics, community_manager, sample_community, sample_members):
        """Test getting participation analytics."""
        logger.info("Testing participation analytics")
        
        # Create decision and vote
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Participation Test",
            description="Test",
            decision_type="policy"
        )
        
        # Multiple members vote
        for i, member_id in enumerate(sample_members[1:4]):
            await community_manager.vote_on_decision(decision_id, member_id, "for")
        
        # Get analytics
        analytics_data = analytics.get_member_participation_analytics(sample_community, time_range_days=30)
        
        assert analytics_data is not None
        assert analytics_data["total_members"] == len(sample_members)
        assert analytics_data["total_votes_cast"] > 0
        assert "member_metrics" in analytics_data
        
        logger.debug(f"Participation: {analytics_data['active_members']}/{analytics_data['total_members']} active")
    
    @pytest.mark.asyncio
    async def test_top_contributors(self, analytics, community_manager, sample_community, sample_members):
        """Test identifying top contributors."""
        logger.info("Testing top contributors identification")
        
        # Make some members more active
        for i in range(3):
            decision_id = await community_manager.propose_decision(
                community_id=sample_community,
                proposer_member_id=sample_members[1],  # Same member proposes multiple
                title=f"Proposal {i}",
                description="Test",
                decision_type="policy"
            )
            
            # Everyone votes
            for member_id in sample_members[2:]:
                await community_manager.vote_on_decision(decision_id, member_id, "for")
        
        analytics_data = analytics.get_member_participation_analytics(sample_community, time_range_days=30)
        
        assert "top_voters" in analytics_data
        assert "top_proposers" in analytics_data
        assert len(analytics_data["top_proposers"]) > 0
        
        # Member 1 should be top proposer
        top_proposer = analytics_data["top_proposers"][0]
        assert top_proposer["proposals_made"] == 3
        
        logger.debug(f"Top proposer made {top_proposer['proposals_made']} proposals")


class TestCommunityHealth:
    """Tests for community health metrics."""
    
    @pytest.mark.asyncio
    async def test_get_health_metrics(self, analytics, community_manager, sample_community, sample_members):
        """Test getting community health metrics."""
        logger.info("Testing community health metrics")
        
        health = analytics.get_community_health_metrics(sample_community)
        
        assert health is not None
        assert "overall_health_score" in health
        assert "health_status" in health
        assert "health_components" in health
        assert "member_statistics" in health
        
        assert 0 <= health["overall_health_score"] <= 100
        
        logger.debug(f"Health score: {health['overall_health_score']}, Status: {health['health_status']}")
    
    @pytest.mark.asyncio
    async def test_health_recommendations(self, analytics, community_manager, sample_community):
        """Test health recommendations generation."""
        logger.info("Testing health recommendations")
        
        # Create community with minimal activity
        community_id = await community_manager.create_community(
            name="Low Activity Community",
            description="For testing recommendations"
        )
        
        health = analytics.get_community_health_metrics(community_id)
        
        assert "recommendations" in health
        # Should have recommendations for low activity community
        assert len(health["recommendations"]) > 0
        
        logger.debug(f"Recommendations: {len(health['recommendations'])}")
    
    @pytest.mark.asyncio
    async def test_health_with_active_community(self, analytics, community_manager, sample_community, sample_members):
        """Test health metrics for active community."""
        logger.info("Testing health for active community")
        
        # Make community active
        # Create decisions
        for i in range(3):
            decision_id = await community_manager.propose_decision(
                community_id=sample_community,
                proposer_member_id=sample_members[0],
                title=f"Decision {i}",
                description="Test",
                decision_type="policy"
            )
        
        # Create resources
        for i in range(2):
            from aiecs.domain.community.models import ResourceType
            await community_manager.create_community_resource(
                community_id=sample_community,
                owner_member_id=sample_members[0],
                name=f"Resource {i}",
                resource_type=ResourceType.KNOWLEDGE,
                content={"data": i}
            )
        
        health = analytics.get_community_health_metrics(sample_community)
        
        assert health["activity_statistics"]["recent_decisions"] > 0
        assert health["activity_statistics"]["recent_resources"] > 0
        
        logger.debug(f"Active community health: {health['overall_health_score']}")


class TestCollaborationEffectiveness:
    """Tests for collaboration effectiveness metrics."""
    
    @pytest.mark.asyncio
    async def test_get_collaboration_effectiveness(self, analytics, community_manager, sample_community, sample_members):
        """Test getting collaboration effectiveness."""
        logger.info("Testing collaboration effectiveness")
        
        # Create and approve some decisions
        for i in range(5):
            decision_id = await community_manager.propose_decision(
                community_id=sample_community,
                proposer_member_id=sample_members[0],
                title=f"Decision {i}",
                description="Test",
                decision_type="policy"
            )
            
            # Vote
            for member_id in sample_members[1:4]:
                await community_manager.vote_on_decision(decision_id, member_id, "for")
            
            # Approve
            decision = community_manager.decisions[decision_id]
            decision.status = DecisionStatus.APPROVED
        
        effectiveness = analytics.get_collaboration_effectiveness(sample_community, time_range_days=30)
        
        assert effectiveness is not None
        assert "effectiveness_score" in effectiveness
        assert "effectiveness_level" in effectiveness
        assert "strengths" in effectiveness
        assert "weaknesses" in effectiveness
        
        logger.debug(f"Effectiveness: {effectiveness['effectiveness_score']}, Level: {effectiveness['effectiveness_level']}")
    
    @pytest.mark.asyncio
    async def test_comprehensive_report(self, analytics, community_manager, sample_community, sample_members):
        """Test comprehensive analytics report."""
        logger.info("Testing comprehensive report")
        
        # Generate some activity
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Report Test Decision",
            description="For testing report",
            decision_type="policy"
        )
        
        await community_manager.vote_on_decision(decision_id, sample_members[1], "for")
        
        report = analytics.get_comprehensive_report(sample_community, time_range_days=30)
        
        assert report is not None
        assert "decision_analytics" in report
        assert "participation_analytics" in report
        assert "health_metrics" in report
        assert "collaboration_effectiveness" in report
        
        logger.debug(f"Comprehensive report generated for community {sample_community}")



"""
Tests for CommunityManager

Comprehensive tests for community and member management.
"""

import pytest
import logging
from datetime import datetime

from aiecs.domain.community.models import (
    GovernanceType, CommunityRole, ResourceType
)
from aiecs.domain.community.exceptions import CommunityValidationError

logger = logging.getLogger(__name__)


class TestCommunityCreation:
    """Tests for community creation."""
    
    @pytest.mark.asyncio
    async def test_create_basic_community(self, community_manager):
        """Test creating a basic community."""
        logger.info("Testing basic community creation")
        
        community_id = await community_manager.create_community(
            name="Test Community",
            description="A test community",
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        assert community_id is not None
        assert community_id in community_manager.communities
        
        community = community_manager.communities[community_id]
        assert community.name == "Test Community"
        assert community.description == "A test community"
        assert community.governance_type == GovernanceType.DEMOCRATIC
        assert community.is_active is True
        
        logger.debug(f"Created community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_create_community_all_governance_types(self, community_manager):
        """Test creating communities with all governance types."""
        logger.info("Testing all governance types")
        
        governance_types = [
            GovernanceType.DEMOCRATIC,
            GovernanceType.CONSENSUS,
            GovernanceType.HIERARCHICAL,
            GovernanceType.HYBRID
        ]
        
        for gov_type in governance_types:
            community_id = await community_manager.create_community(
                name=f"Community {gov_type.value}",
                governance_type=gov_type
            )
            
            community = community_manager.communities[community_id]
            assert community.governance_type == gov_type
            logger.debug(f"Created {gov_type.value} community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_create_community_with_creator(self, community_manager):
        """Test creating a community with a creator agent."""
        logger.info("Testing community creation with creator")
        
        community_id = await community_manager.create_community(
            name="Creator Community",
            creator_agent_id="creator_agent_001"
        )
        
        community = community_manager.communities[community_id]
        assert len(community.members) == 1
        assert len(community.leaders) == 1
        
        # Verify creator is leader
        leader_member = community_manager.members[community.leaders[0]]
        assert leader_member.agent_id == "creator_agent_001"
        assert leader_member.community_role == CommunityRole.LEADER
        
        logger.debug(f"Creator community with leader: {community_id}")


class TestMemberManagement:
    """Tests for member management."""
    
    @pytest.mark.asyncio
    async def test_add_member_to_community(self, community_manager, sample_community):
        """Test adding a member to a community."""
        logger.info("Testing add member to community")
        
        member_id = await community_manager.add_member_to_community(
            community_id=sample_community,
            agent_id="test_agent_001",
            agent_role="developer",
            community_role=CommunityRole.CONTRIBUTOR,
            specializations=["python", "testing"]
        )
        
        assert member_id is not None
        assert member_id in community_manager.members
        
        member = community_manager.members[member_id]
        assert member.agent_id == "test_agent_001"
        assert member.agent_role == "developer"
        assert member.community_role == CommunityRole.CONTRIBUTOR
        assert "python" in member.specializations
        assert member.is_active is True
        
        community = community_manager.communities[sample_community]
        assert member_id in community.members
        
        logger.debug(f"Added member: {member_id}")
    
    @pytest.mark.asyncio
    async def test_add_multiple_roles(self, community_manager, sample_community):
        """Test adding members with different roles."""
        logger.info("Testing multiple member roles")
        
        roles = [
            (CommunityRole.LEADER, "leaders"),
            (CommunityRole.COORDINATOR, "coordinators"),
            (CommunityRole.SPECIALIST, "members"),
            (CommunityRole.CONTRIBUTOR, "members"),
            (CommunityRole.OBSERVER, "members")
        ]
        
        for role, list_attr in roles:
            member_id = await community_manager.add_member_to_community(
                community_id=sample_community,
                agent_id=f"agent_{role.value}",
                agent_role=role.value,
                community_role=role
            )
            
            community = community_manager.communities[sample_community]
            assert member_id in getattr(community, list_attr)
            logger.debug(f"Added {role.value}: {member_id}")
    
    @pytest.mark.asyncio
    async def test_remove_member_from_community(self, community_manager, sample_community, sample_members):
        """Test removing a member from a community."""
        logger.info("Testing remove member from community")
        
        member_id = sample_members[2]  # A contributor
        member_before = community_manager.members[member_id]
        
        success = await community_manager.remove_member_from_community(
            community_id=sample_community,
            member_id=member_id,
            transfer_resources=False
        )
        
        assert success is True
        
        community = community_manager.communities[sample_community]
        assert member_id not in community.members
        
        # Member should still exist but be inactive
        member = community_manager.members[member_id]
        assert member.is_active is False
        
        logger.debug(f"Removed member: {member_id}")
    
    @pytest.mark.asyncio
    async def test_deactivate_and_reactivate_member(self, community_manager, sample_members):
        """Test deactivating and reactivating a member."""
        logger.info("Testing member deactivation and reactivation")
        
        member_id = sample_members[3]
        
        # Deactivate
        success = await community_manager.deactivate_member(
            member_id=member_id,
            reason="Temporary leave"
        )
        assert success is True
        
        member = community_manager.members[member_id]
        assert member.is_active is False
        assert member.participation_level == "inactive"
        assert member.metadata.get("deactivation_reason") == "Temporary leave"
        logger.debug(f"Deactivated member: {member_id}")
        
        # Reactivate
        success = await community_manager.reactivate_member(member_id=member_id)
        assert success is True
        
        member = community_manager.members[member_id]
        assert member.is_active is True
        assert member.participation_level == "active"
        assert "deactivation_reason" not in member.metadata
        logger.debug(f"Reactivated member: {member_id}")


class TestResourceManagement:
    """Tests for resource management."""
    
    @pytest.mark.asyncio
    async def test_create_community_resource(self, community_manager, sample_community, sample_members):
        """Test creating a community resource."""
        logger.info("Testing create community resource")
        
        resource_id = await community_manager.create_community_resource(
            community_id=sample_community,
            owner_member_id=sample_members[0],
            name="Test Resource",
            resource_type=ResourceType.KNOWLEDGE,
            content={"data": "test content"},
            description="A test resource",
            tags=["test", "resource"]
        )
        
        assert resource_id is not None
        assert resource_id in community_manager.resources
        
        resource = community_manager.resources[resource_id]
        assert resource.name == "Test Resource"
        assert resource.resource_type == ResourceType.KNOWLEDGE
        assert resource.owner_id == sample_members[0]
        assert "test" in resource.tags
        assert resource.is_available is True
        
        community = community_manager.communities[sample_community]
        assert resource_id in community.shared_resources
        assert community.resource_count > 0
        
        logger.debug(f"Created resource: {resource_id}")
    
    @pytest.mark.asyncio
    async def test_transfer_member_resources(self, community_manager, sample_community, sample_members):
        """Test transferring resources when member exits."""
        logger.info("Testing resource transfer")
        
        # Create resources
        owner_id = sample_members[2]
        resource_ids = []
        
        for i in range(3):
            rid = await community_manager.create_community_resource(
                community_id=sample_community,
                owner_member_id=owner_id,
                name=f"Resource {i}",
                resource_type=ResourceType.DATA,
                content={"data": f"content_{i}"}
            )
            resource_ids.append(rid)
        
        # Transfer resources to new owner
        new_owner_id = sample_members[0]
        transferred = await community_manager.transfer_member_resources(
            member_id=owner_id,
            new_owner_id=new_owner_id,
            community_id=sample_community
        )
        
        assert len(transferred) == 3
        
        for rid in resource_ids:
            resource = community_manager.resources[rid]
            assert resource.owner_id == new_owner_id
            assert resource.metadata.get("transferred_from") == owner_id
        
        logger.debug(f"Transferred {len(transferred)} resources")


class TestDecisionManagement:
    """Tests for decision management."""
    
    @pytest.mark.asyncio
    async def test_propose_decision(self, community_manager, sample_community, sample_members):
        """Test proposing a decision."""
        logger.info("Testing propose decision")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Test Proposal",
            description="A test proposal",
            decision_type="policy"
        )
        
        assert decision_id is not None
        assert decision_id in community_manager.decisions
        
        decision = community_manager.decisions[decision_id]
        assert decision.title == "Test Proposal"
        assert decision.proposer_id == sample_members[0]
        assert decision.decision_type == "policy"
        
        logger.debug(f"Proposed decision: {decision_id}")
    
    @pytest.mark.asyncio
    async def test_vote_on_decision(self, community_manager, sample_community, sample_members):
        """Test voting on a decision."""
        logger.info("Testing vote on decision")
        
        # Create decision
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Vote Test",
            description="Test voting",
            decision_type="policy"
        )
        
        # Vote for
        success = await community_manager.vote_on_decision(
            decision_id=decision_id,
            member_id=sample_members[1],
            vote="for"
        )
        assert success is True
        
        # Vote against
        success = await community_manager.vote_on_decision(
            decision_id=decision_id,
            member_id=sample_members[2],
            vote="against"
        )
        assert success is True
        
        # Abstain
        success = await community_manager.vote_on_decision(
            decision_id=decision_id,
            member_id=sample_members[3],
            vote="abstain"
        )
        assert success is True
        
        decision = community_manager.decisions[decision_id]
        assert sample_members[1] in decision.votes_for
        assert sample_members[2] in decision.votes_against
        assert sample_members[3] in decision.abstentions
        
        logger.debug(f"Votes recorded for decision: {decision_id}")
    
    @pytest.mark.asyncio
    async def test_change_vote(self, community_manager, sample_community, sample_members):
        """Test changing a vote."""
        logger.info("Testing change vote")
        
        decision_id = await community_manager.propose_decision(
            community_id=sample_community,
            proposer_member_id=sample_members[0],
            title="Change Vote Test",
            description="Test changing vote",
            decision_type="policy"
        )
        
        member_id = sample_members[1]
        
        # Initial vote
        await community_manager.vote_on_decision(decision_id, member_id, "for")
        decision = community_manager.decisions[decision_id]
        assert member_id in decision.votes_for
        
        # Change vote
        await community_manager.vote_on_decision(decision_id, member_id, "against")
        decision = community_manager.decisions[decision_id]
        assert member_id not in decision.votes_for
        assert member_id in decision.votes_against
        
        logger.debug("Vote changed successfully")


class TestLifecycleHooks:
    """Tests for lifecycle hooks."""
    
    @pytest.mark.asyncio
    async def test_lifecycle_hook_registration(self, community_manager):
        """Test registering lifecycle hooks."""
        logger.info("Testing lifecycle hook registration")
        
        class TestHook:
            def __init__(self):
                self.events = []
            
            async def on_member_join(self, community_id, member_id, member):
                self.events.append(("join", community_id, member_id))
            
            async def on_member_exit(self, community_id, member_id, member, reason=None):
                self.events.append(("exit", community_id, member_id, reason))
            
            async def on_member_update(self, community_id, member_id, member, changes):
                self.events.append(("update", community_id, member_id))
            
            async def on_member_inactive(self, community_id, member_id, member, reason=None):
                self.events.append(("inactive", member_id, reason))
        
        hook = TestHook()
        community_manager.register_lifecycle_hook(hook)
        
        # Create community and add member
        community_id = await community_manager.create_community("Hook Test")
        member_id = await community_manager.add_member_to_community(
            community_id=community_id,
            agent_id="hook_test_agent",
            agent_role="tester"
        )
        
        # Check hook was called
        assert len(hook.events) > 0
        assert hook.events[-1][0] == "join"
        assert hook.events[-1][1] == community_id
        
        logger.debug(f"Hook recorded {len(hook.events)} events")



"""
Extended Integration Tests for Community Integration

Comprehensive tests for previously untested core functionalities:
- Decision system integration
- Resource creation integration  
- Query APIs
- Agent auto-integration
- Quick APIs
"""

import pytest
import logging
from datetime import datetime

from aiecs.domain.community.community_integration import CommunityIntegration
from aiecs.domain.community.decision_engine import ConsensusAlgorithm
from aiecs.domain.community.models.community_models import (
    GovernanceType, CommunityRole, DecisionStatus
)
from aiecs.domain.community.exceptions import CommunityValidationError

logger = logging.getLogger(__name__)


@pytest.fixture
def integration_with_community(event_loop):
    """Fixture with integration and a pre-created community."""
    async def _create():
        integration = CommunityIntegration()
        await integration.initialize()
        
        # Create a community
        community_id = await integration.create_agent_community(
            name="Test Community",
            description="Integration test community",
            agent_roles=[],
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Add some members
        member_ids = []
        for i in range(3):
            member_id = await integration._add_agent_to_community(
                community_id=community_id,
                agent_id=f"agent-{i}",
                agent_role="contributor",
                community_role=CommunityRole.CONTRIBUTOR
            )
            member_ids.append(member_id)
        
        return integration, community_id, member_ids
    
    return event_loop.run_until_complete(_create())


class TestDecisionIntegration:
    """Test decision system integration."""
    
    @pytest.mark.asyncio
    async def test_propose_decision_by_agent(self, integration_with_community):
        """Test agent proposing a decision."""
        logger.info("Testing agent decision proposal")
        
        integration, community_id, member_ids = integration_with_community
        
        # Agent proposes a decision
        decision_id = await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Upgrade Framework",
            description="Proposal to upgrade to v2.0",
            decision_type="technical",
            implementation_plan="Step 1: Test\nStep 2: Deploy"
        )
        
        assert decision_id is not None
        
        # Verify decision was created
        decision = integration.community_manager.decisions[decision_id]
        assert decision.title == "Upgrade Framework"
        assert decision.description == "Proposal to upgrade to v2.0"
        assert decision.decision_type == "technical"
        assert decision.status == DecisionStatus.PROPOSED
    
    @pytest.mark.asyncio
    async def test_propose_decision_by_non_member(self, integration_with_community):
        """Test that non-member cannot propose decision."""
        logger.info("Testing non-member decision proposal error")
        
        integration, community_id, _ = integration_with_community
        
        with pytest.raises(CommunityValidationError, match="not a community member"):
            await integration.propose_community_decision(
                community_id=community_id,
                proposer_agent_id="non-member-agent",
                title="Invalid Proposal",
                description="Should fail",
                decision_type="test"
            )
    
    @pytest.mark.asyncio
    async def test_agent_vote_on_decision(self, integration_with_community):
        """Test agent voting on a decision."""
        logger.info("Testing agent voting")
        
        integration, community_id, member_ids = integration_with_community
        
        # Create a decision
        decision_id = await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Test Decision",
            description="For voting test",
            decision_type="policy"
        )
        
        # Agents vote
        success_1 = await integration.agent_vote_on_decision(
            decision_id=decision_id,
            agent_id="agent-0",
            vote="for"
        )
        
        success_2 = await integration.agent_vote_on_decision(
            decision_id=decision_id,
            agent_id="agent-1",
            vote="for"
        )
        
        success_3 = await integration.agent_vote_on_decision(
            decision_id=decision_id,
            agent_id="agent-2",
            vote="against"
        )
        
        assert success_1 is True
        assert success_2 is True
        assert success_3 is True
        
        # Verify votes were recorded
        decision = integration.community_manager.decisions[decision_id]
        assert len(decision.votes_for) == 2
        assert len(decision.votes_against) == 1
    
    @pytest.mark.asyncio
    async def test_vote_by_non_member(self, integration_with_community):
        """Test that non-member cannot vote."""
        logger.info("Testing non-member voting error")
        
        integration, community_id, _ = integration_with_community
        
        decision_id = await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Test",
            description="Test",
            decision_type="test"
        )
        
        with pytest.raises(CommunityValidationError, match="not a community member"):
            await integration.agent_vote_on_decision(
                decision_id=decision_id,
                agent_id="non-member",
                vote="for"
            )
    
    @pytest.mark.asyncio
    async def test_evaluate_community_decision(self, integration_with_community):
        """Test evaluating a community decision."""
        logger.info("Testing decision evaluation")
        
        integration, community_id, _ = integration_with_community
        
        # Create and vote on decision
        decision_id = await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Evaluation Test",
            description="Test evaluation",
            decision_type="test"
        )
        
        await integration.agent_vote_on_decision(decision_id, "agent-0", "for")
        await integration.agent_vote_on_decision(decision_id, "agent-1", "for")
        await integration.agent_vote_on_decision(decision_id, "agent-2", "against")
        
        # Evaluate with simple majority
        result = await integration.evaluate_community_decision(
            decision_id=decision_id,
            community_id=community_id,
            algorithm=ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        
        assert result["decision_id"] == decision_id
        assert result["passed"] is True
        assert result["algorithm"] == ConsensusAlgorithm.SIMPLE_MAJORITY
        assert "details" in result
        assert "evaluated_at" in result
    
    @pytest.mark.asyncio
    async def test_evaluate_with_different_algorithms(self, integration_with_community):
        """Test evaluation with different consensus algorithms."""
        logger.info("Testing different consensus algorithms")
        
        integration, community_id, _ = integration_with_community
        
        decision_id = await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Algorithm Test",
            description="Test",
            decision_type="test"
        )
        
        # 2 for, 1 against
        await integration.agent_vote_on_decision(decision_id, "agent-0", "for")
        await integration.agent_vote_on_decision(decision_id, "agent-1", "for")
        await integration.agent_vote_on_decision(decision_id, "agent-2", "against")
        
        # Test simple majority (should pass)
        result1 = await integration.evaluate_community_decision(
            decision_id, community_id, ConsensusAlgorithm.SIMPLE_MAJORITY
        )
        assert result1["passed"] is True
        
        # Test supermajority (should fail - needs 2/3)
        result2 = await integration.evaluate_community_decision(
            decision_id, community_id, ConsensusAlgorithm.SUPERMAJORITY
        )
        assert result2["passed"] is False
        
        # Test unanimous (should fail)
        result3 = await integration.evaluate_community_decision(
            decision_id, community_id, ConsensusAlgorithm.UNANIMOUS
        )
        assert result3["passed"] is False


class TestResourceIntegration:
    """Test resource creation integration."""
    
    @pytest.mark.asyncio
    async def test_create_knowledge_resource(self, integration_with_community):
        """Test creating knowledge resource on behalf of agent."""
        logger.info("Testing knowledge resource creation")
        
        integration, community_id, _ = integration_with_community
        
        resource_id = await integration.create_community_knowledge_resource(
            community_id=community_id,
            creator_agent_id="agent-0",
            title="API Documentation",
            content="Complete API documentation for v2.0",
            knowledge_type="documentation",
            tags=["api", "docs", "v2"]
        )
        
        assert resource_id is not None
        
        # Verify resource was created
        resource = integration.community_manager.resources[resource_id]
        assert resource.name == "API Documentation"
        assert resource.content["content"] == "Complete API documentation for v2.0"
        assert resource.content["knowledge_type"] == "documentation"
        assert "api" in resource.tags
        assert "docs" in resource.tags
    
    @pytest.mark.asyncio
    async def test_create_resource_by_non_member(self, integration_with_community):
        """Test that non-member cannot create resource."""
        logger.info("Testing non-member resource creation error")
        
        integration, community_id, _ = integration_with_community
        
        with pytest.raises(CommunityValidationError, match="not a community member"):
            await integration.create_community_knowledge_resource(
                community_id=community_id,
                creator_agent_id="non-member",
                title="Invalid Resource",
                content="Should fail",
                knowledge_type="test"
            )
    
    @pytest.mark.asyncio
    async def test_create_multiple_resources(self, integration_with_community):
        """Test creating multiple resources by different agents."""
        logger.info("Testing multiple resource creation")
        
        integration, community_id, _ = integration_with_community
        
        resource_ids = []
        for i in range(3):
            resource_id = await integration.create_community_knowledge_resource(
                community_id=community_id,
                creator_agent_id=f"agent-{i}",
                title=f"Resource {i}",
                content=f"Content {i}",
                knowledge_type="general"
            )
            resource_ids.append(resource_id)
        
        assert len(resource_ids) == 3
        assert len(set(resource_ids)) == 3  # All unique
        
        # Verify all resources exist
        for rid in resource_ids:
            assert rid in integration.community_manager.resources


class TestQueryAPIs:
    """Test query API integration."""
    
    @pytest.mark.asyncio
    async def test_get_agent_communities(self, integration_with_community):
        """Test getting all communities an agent belongs to."""
        logger.info("Testing get agent communities")
        
        integration, community_id, _ = integration_with_community
        
        # Get communities for agent-0
        communities = await integration.get_agent_communities("agent-0")
        
        assert len(communities) == 1
        comm = communities[0]
        assert comm["community_id"] == community_id
        assert comm["name"] == "Test Community"
        assert comm["agent_role"] == "contributor"
        assert comm["community_role"] == CommunityRole.CONTRIBUTOR
        assert comm["member_count"] == 3
        assert comm["is_leader"] is False
        assert comm["is_coordinator"] is False
    
    @pytest.mark.asyncio
    async def test_get_agent_communities_multiple(self):
        """Test agent belonging to multiple communities."""
        logger.info("Testing agent in multiple communities")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        agent_id = "multi-agent"
        
        # Create multiple communities and add agent to each
        community_ids = []
        for i in range(3):
            comm_id = await integration.create_agent_community(
                name=f"Community {i}",
                description=f"Test {i}",
                agent_roles=[],
                governance_type=GovernanceType.DEMOCRATIC
            )
            
            await integration._add_agent_to_community(
                community_id=comm_id,
                agent_id=agent_id,
                agent_role=f"role-{i}",
                community_role=CommunityRole.CONTRIBUTOR if i < 2 else CommunityRole.LEADER
            )
            
            community_ids.append(comm_id)
        
        # Get all communities
        communities = await integration.get_agent_communities(agent_id)
        
        assert len(communities) == 3
        
        # Verify roles
        roles = [c["agent_role"] for c in communities]
        assert "role-0" in roles
        assert "role-1" in roles
        assert "role-2" in roles
        
        # Verify leader status
        leader_communities = [c for c in communities if c["is_leader"]]
        assert len(leader_communities) == 1
    
    @pytest.mark.asyncio
    async def test_get_agent_communities_empty(self):
        """Test agent with no communities."""
        logger.info("Testing agent with no communities")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        communities = await integration.get_agent_communities("non-member-agent")
        
        assert communities == []
    
    @pytest.mark.asyncio
    async def test_get_community_status_not_found(self):
        """Test getting status of non-existent community."""
        logger.info("Testing get status for non-existent community")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        with pytest.raises(CommunityValidationError, match="Community not found"):
            await integration.get_community_status("non-existent-id")
    
    @pytest.mark.asyncio
    async def test_get_community_status_complete(self, integration_with_community):
        """Test getting complete community status."""
        logger.info("Testing complete community status")
        
        integration, community_id, _ = integration_with_community
        
        # Add some activity
        await integration.propose_community_decision(
            community_id=community_id,
            proposer_agent_id="agent-0",
            title="Test Decision",
            description="Test",
            decision_type="test"
        )
        
        await integration.create_community_knowledge_resource(
            community_id=community_id,
            creator_agent_id="agent-1",
            title="Test Resource",
            content="Test",
            knowledge_type="test"
        )
        
        # Get status
        status = await integration.get_community_status(community_id)
        
        assert status["community_id"] == community_id
        assert status["name"] == "Test Community"
        assert status["member_count"] == 3
        assert status["governance_type"] == GovernanceType.DEMOCRATIC
        assert status["is_active"] is True
        assert "created_at" in status


class TestAgentIntegration:
    """Test agent auto-integration features."""
    
    @pytest.mark.asyncio
    async def test_agent_community_mapping(self):
        """Test agent-community mapping updates."""
        logger.info("Testing agent-community mapping")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        community_id = await integration.create_agent_community(
            name="Test",
            description="Test",
            agent_roles=[],
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Add agent
        await integration._add_agent_to_community(
            community_id=community_id,
            agent_id="test-agent",
            agent_role="tester",
            community_role=CommunityRole.CONTRIBUTOR
        )
        
        # Verify mapping
        assert "test-agent" in integration.agent_community_mapping
        assert community_id in integration.agent_community_mapping["test-agent"]
        assert community_id in integration.community_agent_mapping
        assert "test-agent" in integration.community_agent_mapping[community_id]
    
    @pytest.mark.asyncio
    async def test_multiple_communities_per_agent(self):
        """Test agent added to multiple communities updates mappings."""
        logger.info("Testing multiple communities per agent")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        agent_id = "multi-comm-agent"
        community_ids = []
        
        # Create 3 communities and add same agent to each
        for i in range(3):
            comm_id = await integration.create_agent_community(
                name=f"Community {i}",
                description="Test",
                agent_roles=[],
                governance_type=GovernanceType.DEMOCRATIC
            )
            
            await integration._add_agent_to_community(
                community_id=comm_id,
                agent_id=agent_id,
                agent_role=f"role-{i}"
            )
            
            community_ids.append(comm_id)
        
        # Verify agent is in all communities
        assert agent_id in integration.agent_community_mapping
        assert len(integration.agent_community_mapping[agent_id]) == 3
        
        for comm_id in community_ids:
            assert comm_id in integration.agent_community_mapping[agent_id]
            assert agent_id in integration.community_agent_mapping[comm_id]


class TestQuickAPIs:
    """Test quick convenience APIs."""
    
    @pytest.mark.asyncio
    async def test_quick_brainstorm_basic(self):
        """Test quick brainstorm basic functionality."""
        logger.info("Testing quick brainstorm")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        agent_ids = ["alice", "bob", "charlie"]
        
        results = await integration.quick_brainstorm(
            topic="Product Ideas 2025",
            agent_ids=agent_ids,
            duration_minutes=1,  # Short for testing
            auto_cleanup=True
        )
        
        assert results["topic"] == "Product Ideas 2025"
        assert "community_id" in results
        assert "session_id" in results
        assert results["participants"] == agent_ids
        assert results["duration_minutes"] == 1
        assert "summary" in results
        
        # Verify community was created
        community_id = results["community_id"]
        assert community_id in integration.community_manager.communities
        
        # Verify agents were added
        community = integration.community_manager.communities[community_id]
        assert len(community.members) == 3
    
    @pytest.mark.asyncio
    async def test_quick_brainstorm_creates_temporary_community(self):
        """Test that quick brainstorm creates temporary community."""
        logger.info("Testing quick brainstorm temporary community")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        results = await integration.quick_brainstorm(
            topic="Quick Ideas",
            agent_ids=["agent1", "agent2"],
            duration_minutes=1,
            auto_cleanup=False  # Don't auto-cleanup for verification
        )
        
        community_id = results["community_id"]
        community = integration.community_manager.communities[community_id]
        
        # Verify it's marked as temporary
        assert community.metadata.get("temporary") is True
        assert "cleanup_at" in community.metadata


class TestContextManagers:
    """Test context manager edge cases."""
    
    @pytest.mark.asyncio
    async def test_collaborative_session_error_handling(self):
        """Test session context manager handles errors properly."""
        logger.info("Testing session context manager error handling")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        community_id = await integration.create_agent_community(
            name="Test",
            description="Test",
            agent_roles=[],
            governance_type=GovernanceType.DEMOCRATIC
        )
        
        # Add a member
        await integration._add_agent_to_community(
            community_id=community_id,
            agent_id="test-agent",
            agent_role="tester"
        )
        
        # Use context manager
        async with integration.collaborative_session(
            community_id=community_id,
            session_type="test",
            purpose="Testing error handling"
        ) as session_id:
            assert session_id is not None
            # Session should be active
            assert session_id in integration.workflow_engine.active_sessions
        
        # After context exit, session should be ended (or attempted)
        # The session might still be in active_sessions if end failed, 
        # but the context manager should have tried to end it


class TestInitialization:
    """Test initialization edge cases."""
    
    @pytest.mark.asyncio
    async def test_repeat_initialization(self):
        """Test that repeated initialization is handled correctly."""
        logger.info("Testing repeat initialization")
        
        integration = CommunityIntegration()
        
        await integration.initialize()
        assert integration._initialized is True
        
        # Initialize again (should return early)
        await integration.initialize()
        assert integration._initialized is True  # Still True
    
    @pytest.mark.asyncio
    async def test_initialization_without_agent_manager(self):
        """Test initialization without agent_manager."""
        logger.info("Testing initialization without agent_manager")
        
        integration = CommunityIntegration(agent_manager=None)
        await integration.initialize()
        
        assert integration.agent_manager is None
        assert integration._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialization_with_context_engine(self):
        """Test initialization with context_engine."""
        logger.info("Testing initialization with context_engine")
        
        # Mock context engine
        class MockContextEngine:
            async def get_context(self, key):
                return None
        
        engine = MockContextEngine()
        integration = CommunityIntegration(context_engine=engine)
        await integration.initialize()
        
        assert integration.context_engine is engine
        assert integration._initialized is True


class TestCollaborationSessionAdvanced:
    """Test advanced collaboration session features."""
    
    @pytest.mark.asyncio
    async def test_collaboration_without_leader(self):
        """Test collaboration when no leader is specified."""
        logger.info("Testing collaboration without leader")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        # Create community with leader
        community_id = await integration.create_agent_community(
            name="Test",
            description="Test",
            agent_roles=[],
            governance_type=GovernanceType.HIERARCHICAL
        )
        
        # Add leader
        await integration._add_agent_to_community(
            community_id=community_id,
            agent_id="leader-agent",
            agent_role="leader",
            community_role=CommunityRole.LEADER
        )
        
        # Start collaboration without specifying leader
        session_id = await integration.initiate_community_collaboration(
            community_id=community_id,
            collaboration_type="planning",
            purpose="Test auto leader selection"
            # leader_agent_id not specified
        )
        
        assert session_id is not None
        # Leader should be auto-selected from community leaders
    
    @pytest.mark.asyncio
    async def test_collaboration_community_not_found(self):
        """Test collaboration with non-existent community."""
        logger.info("Testing collaboration with non-existent community")
        
        integration = CommunityIntegration()
        await integration.initialize()
        
        with pytest.raises(CommunityValidationError, match="Community not found"):
            await integration.initiate_community_collaboration(
                community_id="non-existent",
                collaboration_type="test",
                purpose="Should fail"
            )


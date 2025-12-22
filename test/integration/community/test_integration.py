"""
Tests for Community Integration

Tests for high-level integration features and workflows.
"""

import pytest
import logging
import asyncio

from aiecs.domain.community.models import GovernanceType, CommunityRole

logger = logging.getLogger(__name__)


class TestQuickCreateMethods:
    """Tests for quick-create factory methods."""
    
    @pytest.mark.asyncio
    async def test_create_temporary_community(self, community_integration):
        """Test creating a temporary community."""
        logger.info("Testing temporary community creation")
        
        community_id = await community_integration.create_temporary_community(
            name="Temp Community",
            description="A temporary community",
            agent_roles=["analyst", "developer"],
            duration_minutes=60,
            auto_cleanup=False  # Don't actually wait for cleanup in test
        )
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata.get("temporary") is True
        assert community.metadata.get("created_for_duration") == 60
        
        logger.debug(f"Created temporary community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_create_project_community(self, community_integration):
        """Test creating a project community."""
        logger.info("Testing project community creation")
        
        community_id = await community_integration.create_project_community(
            project_name="Test Project",
            project_description="A test project",
            agent_roles=["architect", "developer"],
            project_goal="Build test software",
            creator_agent_id="project_creator"
        )
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata.get("type") == "project"
        assert community.metadata.get("project_goal") == "Build test software"
        assert community.governance_type == GovernanceType.HIERARCHICAL
        
        logger.debug(f"Created project community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_create_research_community(self, community_integration):
        """Test creating a research community."""
        logger.info("Testing research community creation")
        
        community_id = await community_integration.create_research_community(
            research_topic="AI Safety",
            research_questions=["How to ensure AI alignment?", "What are the risks?"],
            agent_roles=["researcher", "analyst"],
            methodologies=["qualitative", "quantitative"],
            creator_agent_id="researcher_lead"
        )
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata.get("type") == "research"
        assert community.metadata.get("research_topic") == "AI Safety"
        assert len(community.metadata.get("research_questions", [])) == 2
        assert community.governance_type == GovernanceType.CONSENSUS
        
        logger.debug(f"Created research community: {community_id}")


class TestContextManagers:
    """Tests for context managers."""
    
    @pytest.mark.asyncio
    async def test_temporary_community_context_manager(self, community_integration):
        """Test temporary community context manager."""
        logger.info("Testing temporary community context manager")
        
        community_id_captured = None
        
        async with community_integration.temporary_community(
            name="Context Manager Community",
            agent_roles=["tester"]
        ) as community_id:
            community_id_captured = community_id
            
            # Community should exist
            assert community_id in community_integration.community_manager.communities
            community = community_integration.community_manager.communities[community_id]
            assert community.is_active is True
            
            logger.debug(f"Community active in context: {community_id}")
        
        # After context, community should be marked inactive
        community = community_integration.community_manager.communities[community_id_captured]
        assert community.is_active is False
        
        logger.debug("Community cleaned up after context")
    
    @pytest.mark.asyncio
    async def test_collaborative_session_context_manager(self, community_integration):
        """Test collaborative session context manager."""
        logger.info("Testing collaborative session context manager")
        
        # Create community first
        community_id = await community_integration.create_agent_community(
            name="Session Test Community",
            description="For testing sessions",
            agent_roles=["tester"],
            creator_agent_id="session_creator"
        )
        
        session_id_captured = None
        
        async with community_integration.collaborative_session(
            community_id=community_id,
            session_type="brainstorming",
            purpose="Test session"
        ) as session_id:
            session_id_captured = session_id
            
            # Session should be active
            assert session_id in community_integration.workflow_engine.active_sessions
            
            logger.debug(f"Session active: {session_id}")
        
        # After context, session should be ended
        assert session_id_captured not in community_integration.workflow_engine.active_sessions
        
        logger.debug("Session ended after context")


class TestWorkflowIntegration:
    """Tests for workflow integration."""
    
    @pytest.mark.asyncio
    async def test_initiate_brainstorming_session(self, community_integration):
        """Test initiating a brainstorming session."""
        logger.info("Testing brainstorming session")
        
        # Create community
        community_id = await community_integration.create_agent_community(
            name="Brainstorm Community",
            description="For brainstorming",
            agent_roles=[],
            creator_agent_id="brainstorm_leader"
        )
        
        # Initiate session
        session_id = await community_integration.initiate_community_collaboration(
            community_id=community_id,
            collaboration_type="brainstorming",
            purpose="Generate ideas"
        )
        
        assert session_id is not None
        assert session_id in community_integration.workflow_engine.active_sessions
        
        logger.debug(f"Brainstorming session started: {session_id}")
        
        # End session
        summary = await community_integration.workflow_engine.end_session(session_id)
        assert summary is not None
        
        logger.debug(f"Session ended with summary")
    
    @pytest.mark.asyncio
    async def test_problem_solving_workflow(self, community_integration):
        """Test problem solving workflow."""
        logger.info("Testing problem solving workflow")
        
        community_id = await community_integration.create_agent_community(
            name="Problem Solving Community",
            description="For solving problems",
            agent_roles=[],
            creator_agent_id="problem_solver"
        )
        
        session_id = await community_integration.initiate_community_collaboration(
            community_id=community_id,
            collaboration_type="problem_solving",
            purpose="Solve technical issues"
        )
        
        assert session_id is not None
        
        # Let workflow process a bit
        await asyncio.sleep(1)
        
        summary = await community_integration.workflow_engine.end_session(session_id)
        assert "session_type" in summary
        
        logger.debug("Problem solving workflow completed")


class TestCommunityBuilder:
    """Tests for community builder pattern."""
    
    @pytest.mark.asyncio
    async def test_builder_basic_usage(self, community_integration):
        """Test basic builder usage."""
        logger.info("Testing community builder basic usage")
        
        from aiecs.domain.community.community_builder import CommunityBuilder
        
        builder = CommunityBuilder(community_integration)
        
        community_id = await (builder
            .with_name("Built Community")
            .with_description("Built with builder pattern")
            .with_governance(GovernanceType.DEMOCRATIC)
            .add_agent_role("developer")
            .add_agent_role("tester")
            .build())
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.name == "Built Community"
        assert community.governance_type == GovernanceType.DEMOCRATIC
        
        logger.debug(f"Built community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_builder_with_template(self, community_integration):
        """Test builder with preset templates."""
        logger.info("Testing builder with templates")
        
        from aiecs.domain.community.community_builder import CommunityBuilder
        
        builder = CommunityBuilder(community_integration)
        
        # Research template
        community_id = await (builder
            .with_name("Research Community")
            .use_template("research", topic="AI Research")
            .build())
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata.get("type") == "research"
        assert community.governance_type == GovernanceType.CONSENSUS
        
        logger.debug(f"Built research community: {community_id}")
    
    @pytest.mark.asyncio
    async def test_builder_temporary_community(self, community_integration):
        """Test builder for temporary community."""
        logger.info("Testing builder for temporary community")
        
        from aiecs.domain.community.community_builder import CommunityBuilder
        
        builder = CommunityBuilder(community_integration)
        
        community_id = await (builder
            .with_name("Temporary Built Community")
            .with_duration(minutes=30, auto_cleanup=False)
            .add_agent_role("participant")
            .build())
        
        assert community_id is not None
        
        community = community_integration.community_manager.communities[community_id]
        assert community.metadata.get("temporary") is True
        
        logger.debug(f"Built temporary community: {community_id}")


class TestAnalytics:
    """Tests for analytics integration."""
    
    @pytest.mark.asyncio
    async def test_get_community_status(self, community_integration):
        """Test getting community status."""
        logger.info("Testing get community status")
        
        community_id = await community_integration.create_agent_community(
            name="Status Test Community",
            description="For status testing",
            agent_roles=[],
            creator_agent_id="status_tester"
        )
        
        status = await community_integration.get_community_status(community_id)
        
        assert status is not None
        assert status["community_id"] == community_id
        assert "member_count" in status
        assert "health_status" in status or "activity_level" in status
        
        logger.debug(f"Community status: {status}")



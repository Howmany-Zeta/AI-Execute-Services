"""
Comprehensive Tests for Collaborative Workflows

Tests for all 7 workflow types to achieve 100% workflow coverage.
"""

import pytest
import logging

logger = logging.getLogger(__name__)


class TestKnowledgeSynthesisWorkflow:
    """Tests for knowledge synthesis workflow."""
    
    @pytest.mark.asyncio
    async def test_knowledge_synthesis_workflow(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test knowledge synthesis workflow execution."""
        logger.info("Testing knowledge synthesis workflow")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="knowledge_synthesis",
            purpose="Synthesize project learnings and best practices",
            participants=sample_members[:4],
            duration_minutes=95
        )
        
        assert session_id is not None
        assert session_id in workflow_engine.active_sessions
        
        # Verify session created
        session = workflow_engine.active_sessions[session_id]
        assert session.session_type == "knowledge_synthesis"
        assert session.purpose == "Synthesize project learnings and best practices"
        
        # Verify 5 phases executed
        phases = session.metadata.get("phases", [])
        assert len(phases) == 5
        
        # Verify phase names and order
        phase_names = [p["phase_name"] for p in phases]
        assert phase_names[0] == "knowledge_gathering"
        assert phase_names[1] == "information_analysis"
        assert phase_names[2] == "pattern_identification"
        assert phase_names[3] == "synthesis"
        assert phase_names[4] == "artifact_creation"
        
        # Verify phase configurations
        assert phases[0]["config"]["resource_search"] is True
        assert phases[1]["config"]["quality_assessment"] is True
        assert phases[2]["config"]["pattern_analysis"] is True
        assert phases[3]["config"]["collaborative_editing"] is True
        assert phases[4]["config"]["create_resources"] is True
        
        logger.debug(f"Knowledge synthesis workflow completed with {len(phases)} phases")


class TestDecisionMakingWorkflow:
    """Tests for decision making workflow."""
    
    @pytest.mark.asyncio
    async def test_decision_making_workflow(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test decision making workflow execution."""
        logger.info("Testing decision making workflow")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="decision_making",
            purpose="Select database technology for new service",
            participants=sample_members[:5],
            agenda=["Frame decision", "Generate options", "Evaluate", "Decide"],
            duration_minutes=80
        )
        
        assert session_id is not None
        assert session_id in workflow_engine.active_sessions
        
        # Verify 5 phases executed
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        assert len(phases) == 5
        
        # Verify phase names
        phase_names = [p["phase_name"] for p in phases]
        assert "decision_framing" in phase_names
        assert "option_generation" in phase_names
        assert "criteria_definition" in phase_names
        assert "option_evaluation" in phase_names
        assert "decision_making" in phase_names
        
        # Verify phase configurations
        assert phases[0]["config"]["structured_framing"] is True
        assert phases[1]["config"]["creative_options"] is True
        assert phases[2]["config"]["criteria_weighting"] is True
        assert phases[3]["config"]["systematic_evaluation"] is True
        assert phases[4]["config"]["consensus_building"] is True
        assert phases[4]["config"]["create_decision"] is True
        
        logger.debug(f"Decision making workflow completed")


class TestResourceCreationWorkflow:
    """Tests for resource creation workflow."""
    
    @pytest.mark.asyncio
    async def test_resource_creation_workflow(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test resource creation workflow execution."""
        logger.info("Testing resource creation workflow")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="resource_creation",
            purpose="Create API documentation for payment service",
            participants=sample_members[:3],
            duration_minutes=60
        )
        
        assert session_id is not None
        
        # Verify 3 phases executed
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        assert len(phases) == 3
        
        # Verify phase names
        phase_names = [p["phase_name"] for p in phases]
        assert "resource_planning" in phase_names
        assert "collaborative_creation" in phase_names
        assert "review_refinement" in phase_names
        
        # Verify phase configurations
        assert phases[1]["config"]["collaborative_editing"] is True
        assert phases[2]["config"]["peer_review"] is True
        
        logger.debug(f"Resource creation workflow completed with {len(phases)} phases")


class TestPeerReviewWorkflow:
    """Tests for peer review workflow (previously thought to be placeholder)."""
    
    @pytest.mark.asyncio
    async def test_peer_review_workflow_basic(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test basic peer review workflow execution."""
        logger.info("Testing peer review workflow (fully implemented!)")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="peer_review",
            purpose="Review pull request #456 - Authentication refactor",
            participants=sample_members[1:5],  # 4 reviewers
            session_config={
                "approval_threshold": 0.75,
                "review_criteria": ["security", "performance", "maintainability"]
            }
        )
        
        assert session_id is not None
        assert session_id in workflow_engine.active_sessions
        
        # Verify 5 phases executed
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        assert len(phases) == 5
        
        # Verify phase names and order
        phase_names = [p["phase_name"] for p in phases]
        assert phase_names[0] == "reviewer_assignment"
        assert phase_names[1] == "individual_review"
        assert phase_names[2] == "review_collection"
        assert phase_names[3] == "feedback_integration"
        assert phase_names[4] == "final_approval"
        
        logger.debug(f"Peer review workflow completed with {len(phases)} phases")
    
    @pytest.mark.asyncio
    async def test_peer_review_workflow_configuration(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test peer review workflow with detailed configuration."""
        logger.info("Testing peer review workflow configuration")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="peer_review",
            purpose="Review architecture design document",
            participants=sample_members,
            session_config={
                "min_reviewers": 3,
                "approval_threshold": 0.8
            }
        )
        
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        
        # Verify reviewer assignment configuration
        reviewer_assignment = phases[0]
        assert reviewer_assignment["phase_name"] == "reviewer_assignment"
        assert reviewer_assignment["config"]["min_reviewers"] == 2  # Default from workflow
        assert reviewer_assignment["config"]["max_reviewers"] == 5
        
        # Verify individual review configuration
        individual_review = phases[1]
        assert individual_review["phase_name"] == "individual_review"
        assert individual_review["config"]["review_criteria"] == ["accuracy", "completeness", "clarity", "quality"]
        assert individual_review["config"]["parallel_reviews"] is True
        assert individual_review["config"]["time_limit_minutes"] == 30
        
        # Verify review collection configuration
        review_collection = phases[2]
        assert review_collection["phase_name"] == "review_collection"
        assert review_collection["config"]["identify_conflicts"] is True
        assert review_collection["config"]["aggregate_scores"] is True
        
        # Verify feedback integration configuration
        feedback_integration = phases[3]
        assert feedback_integration["phase_name"] == "feedback_integration"
        assert feedback_integration["config"]["collaborative_editing"] is True
        assert feedback_integration["config"]["track_changes"] is True
        
        # Verify final approval configuration
        final_approval = phases[4]
        assert final_approval["phase_name"] == "final_approval"
        assert final_approval["config"]["require_consensus"] is True
        assert final_approval["config"]["approval_threshold"] == 0.8
        
        logger.debug("Peer review configuration verified")


class TestConsensusBuildingWorkflow:
    """Tests for consensus building workflow (previously thought to be placeholder)."""
    
    @pytest.mark.asyncio
    async def test_consensus_building_workflow_basic(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test basic consensus building workflow execution."""
        logger.info("Testing consensus building workflow (fully implemented!)")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="consensus_building",
            purpose="Align on Q4 team priorities and objectives",
            participants=sample_members,
            session_config={
                "consensus_threshold": 0.85
            }
        )
        
        assert session_id is not None
        assert session_id in workflow_engine.active_sessions
        
        # Verify 5 phases executed
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        assert len(phases) == 5
        
        # Verify phase names and order
        phase_names = [p["phase_name"] for p in phases]
        assert phase_names[0] == "issue_presentation"
        assert phase_names[1] == "position_sharing"
        assert phase_names[2] == "common_ground_identification"
        assert phase_names[3] == "proposal_refinement"
        assert phase_names[4] == "convergence_check"
        
        logger.debug(f"Consensus building workflow completed with {len(phases)} phases")
    
    @pytest.mark.asyncio
    async def test_consensus_building_workflow_configuration(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test consensus building workflow with detailed configuration."""
        logger.info("Testing consensus building workflow configuration")
        
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="consensus_building",
            purpose="Establish team working agreements",
            participants=sample_members,
            duration_minutes=90
        )
        
        session = workflow_engine.active_sessions[session_id]
        phases = session.metadata.get("phases", [])
        
        # Verify issue presentation configuration
        issue_presentation = phases[0]
        assert issue_presentation["phase_name"] == "issue_presentation"
        assert issue_presentation["config"]["clarification_enabled"] is True
        assert issue_presentation["config"]["time_limit_minutes"] == 15
        
        # Verify position sharing configuration
        position_sharing = phases[1]
        assert position_sharing["phase_name"] == "position_sharing"
        assert position_sharing["config"]["equal_participation"] is True
        assert position_sharing["config"]["capture_positions"] is True
        assert position_sharing["config"]["time_limit_minutes"] == 20
        
        # Verify common ground identification configuration
        common_ground = phases[2]
        assert common_ground["phase_name"] == "common_ground_identification"
        assert common_ground["config"]["find_overlaps"] is True
        assert common_ground["config"]["identify_blockers"] is True
        assert common_ground["config"]["time_limit_minutes"] == 15
        
        # Verify proposal refinement configuration
        proposal_refinement = phases[3]
        assert proposal_refinement["phase_name"] == "proposal_refinement"
        assert proposal_refinement["config"]["iterative_refinement"] is True
        assert proposal_refinement["config"]["test_proposals"] is True
        assert proposal_refinement["config"]["time_limit_minutes"] == 25
        
        # Verify convergence check configuration
        convergence_check = phases[4]
        assert convergence_check["phase_name"] == "convergence_check"
        assert convergence_check["config"]["consensus_threshold"] == 0.9
        assert convergence_check["config"]["allow_dissent"] is True
        assert convergence_check["config"]["document_agreement"] is True
        assert convergence_check["config"]["time_limit_minutes"] == 15
        
        logger.debug("Consensus building configuration verified")


class TestWorkflowSessionManagement:
    """Tests for workflow session lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_session_end_and_summary(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test ending a session and getting summary."""
        logger.info("Testing session end and summary")
        
        # Start a session
        session_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="brainstorming",
            purpose="Generate ideas",
            participants=sample_members[:3]
        )
        
        # End the session
        summary = await workflow_engine.end_session(session_id)
        
        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["session_type"] == "brainstorming"
        assert summary["purpose"] == "Generate ideas"
        assert len(summary["participants"]) == 3
        assert "duration_minutes" in summary
        assert summary["phases_completed"] == 4  # Brainstorming has 4 phases
        assert summary["status"] == "completed"
        
        # Verify session removed from active sessions
        assert session_id not in workflow_engine.active_sessions
        
        logger.debug(f"Session ended successfully: {summary}")
    
    @pytest.mark.asyncio
    async def test_session_not_found_error(self, workflow_engine):
        """Test error when trying to end non-existent session."""
        logger.info("Testing session not found error")
        
        with pytest.raises(Exception) as exc_info:
            await workflow_engine.end_session("non_existent_session_id")
        
        assert "Session not found" in str(exc_info.value)
        
        logger.debug("Session not found error handled correctly")
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_parallel(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test running multiple sessions in parallel."""
        logger.info("Testing multiple parallel sessions")
        
        # Start multiple sessions
        session1_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[0],
            session_type="brainstorming",
            purpose="Feature ideas",
            participants=sample_members[:2]
        )
        
        session2_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[1],
            session_type="problem_solving",
            purpose="Bug analysis",
            participants=sample_members[2:4]
        )
        
        session3_id = await workflow_engine.start_collaborative_session(
            community_id=sample_community,
            session_leader_id=sample_members[2],
            session_type="peer_review",
            purpose="Code review",
            participants=sample_members[3:5]
        )
        
        # Verify all sessions active
        assert session1_id in workflow_engine.active_sessions
        assert session2_id in workflow_engine.active_sessions
        assert session3_id in workflow_engine.active_sessions
        
        # Verify different session types
        assert workflow_engine.active_sessions[session1_id].session_type == "brainstorming"
        assert workflow_engine.active_sessions[session2_id].session_type == "problem_solving"
        assert workflow_engine.active_sessions[session3_id].session_type == "peer_review"
        
        # End all sessions
        await workflow_engine.end_session(session1_id)
        await workflow_engine.end_session(session2_id)
        await workflow_engine.end_session(session3_id)
        
        assert len(workflow_engine.active_sessions) == 0
        
        logger.debug("Multiple parallel sessions managed successfully")


class TestWorkflowCoverage:
    """Test all 7 workflow types for complete coverage."""
    
    @pytest.mark.asyncio
    async def test_all_workflow_types(self, workflow_engine, community_manager, sample_community, sample_members):
        """Test that all 7 workflow types are available and executable."""
        logger.info("Testing all 7 workflow types")
        
        workflow_types = [
            ("brainstorming", 4),
            ("problem_solving", 5),
            ("knowledge_synthesis", 5),
            ("decision_making", 5),
            ("resource_creation", 3),
            ("peer_review", 5),
            ("consensus_building", 5)
        ]
        
        for workflow_type, expected_phases in workflow_types:
            session_id = await workflow_engine.start_collaborative_session(
                community_id=sample_community,
                session_leader_id=sample_members[0],
                session_type=workflow_type,
                purpose=f"Test {workflow_type}",
                participants=sample_members[:3]
            )
            
            session = workflow_engine.active_sessions[session_id]
            phases = session.metadata.get("phases", [])
            
            assert len(phases) == expected_phases, \
                f"{workflow_type} should have {expected_phases} phases, got {len(phases)}"
            
            logger.debug(f"{workflow_type}: {expected_phases} phases executed ✓")
            
            # Clean up
            await workflow_engine.end_session(session_id)
        
        logger.info("All 7 workflow types tested successfully!")





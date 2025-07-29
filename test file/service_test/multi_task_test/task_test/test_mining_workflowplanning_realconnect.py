"""
Comprehensive Test Suite for Refactored Mining Service

This test suite provides comprehensive coverage for the refactored MiningService
that uses LangGraph workflow with enhanced demand analysis and blueprint generation.

The refactored service includes:
1. LangGraph-based workflow orchestration
2. Enhanced intent analysis with complexity assessment
3. Meta architect flow for complex requests
4. Simple strategy flow for simpler requests
5. Summarizer flow for user feedback and workflow planning
6. Improved error handling and fallback mechanisms

Requirements:
- Uses real instances, not mocks
- Initializes corresponding agents with real LLM integration
- Receives meaningful content from real LLM calls
- Achieves >85% coverage
- Uses pytest with coverage support
"""

import pytest
import pytest_asyncio
import asyncio
import json
import time
import os
from typing import Dict, Any, List
from datetime import datetime

# Import the services under test
from app.services.multi_task.services.demand.mining import (
    MiningService, MiningContext, MiningState, MiningResult, DemandState
)
from app.services.multi_task.services.planner.workflow_planning import (
    WorkflowPlanningService, WorkflowPlanningState
)

# Import real dependencies
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole

# Import LLM architecture components
from app.llm import get_llm_manager, LLMMessage, LLMResponse, AIProvider
from app.llm.client_factory import LLMClientFactory, LLMClientManager

@pytest.fixture
def real_config_manager():
    """Fixture for real configuration manager"""
    return ConfigManager()


@pytest.fixture
def real_llm_manager():
    """Fixture for real LLM integration manager"""
    return LLMIntegrationManager()


@pytest_asyncio.fixture
async def mining_service(real_llm_manager, real_config_manager):
    """Fixture for mining service with real agents and real LLM"""
    service = MiningService(real_llm_manager, real_config_manager)
    await service.initialize()
    return service


@pytest_asyncio.fixture
async def workflow_planning_service(real_llm_manager, real_config_manager):
    """Fixture for workflow planning service with real agents and real LLM"""
    service = WorkflowPlanningService(real_config_manager, real_llm_manager)
    await service.initialize()
    return service


@pytest.fixture
def mining_context():
    """Fixture for mining context"""
    return MiningContext(
        user_id="test_user",
        session_id="test_session",
        domain="data_analysis",
        timestamp=datetime.now().isoformat(),
        task_id="test_task_001",
        max_clarification_rounds=3,
        current_round=0
    )


@pytest.fixture
def sample_mining_state(mining_context):
    """Fixture for sample mining state"""
    return MiningState(
        user_input="Analyze Q3 2024 financial performance for Apple Inc.",
        context=mining_context,
        messages=[]
    )


class TestMiningServiceInitialization:
    """Test suite for MiningService initialization and setup"""

    @pytest.mark.asyncio
    async def test_mining_service_initialization(self, mining_service):
        """Test mining service initialization with real agents"""
        assert mining_service is not None
        assert mining_service.intent_parser is not None
        assert mining_service.meta_architect is not None
        assert mining_service.workflow is not None
        assert mining_service._total_mining_operations == 0
        assert mining_service._successful_operations == 0

        # Test that agents are properly initialized
        assert hasattr(mining_service.intent_parser, 'agent_id')
        assert hasattr(mining_service.meta_architect, 'agent_id')

    @pytest.mark.asyncio
    async def test_agents_initialization(self, mining_service):
        """Test that agents are properly configured"""
        # Test intent parser configuration
        assert mining_service.intent_parser.config.name == "Mining Intent Parser"
        assert mining_service.intent_parser.config.role == AgentRole.INTENT_PARSER
        assert mining_service.intent_parser.config.max_iter == 3
        assert mining_service.intent_parser.config.allow_delegation is False

        # Test meta architect configuration
        assert mining_service.meta_architect.config.name == "Mining Meta Architect"
        assert mining_service.meta_architect.config.role == AgentRole.META_ARCHITECT
        assert mining_service.meta_architect.config.max_iter == 5
        assert mining_service.meta_architect.config.allow_delegation is False

    @pytest.mark.asyncio
    async def test_workflow_initialization(self, mining_service):
        """Test that LangGraph workflow is properly initialized"""
        assert mining_service.workflow is not None

        # Test that workflow has the expected nodes (we can't directly access nodes, but we can test execution)
        # This will be tested through actual workflow execution


class TestMiningServiceCoreWorkflow:
    """Test suite for core mining workflow functionality"""

    @pytest.mark.asyncio
    async def test_mine_requirements_smart_compliant(self, mining_service, mining_context):
        """Test mining requirements for SMART compliant input with real LLM"""
        user_input = "Analyze Apple's Q3 2024 financial performance compared to Q2 2024, focusing on revenue growth and profit margins"

        result = await mining_service.mine_requirements(user_input, mining_context)

        assert isinstance(result, MiningResult)
        assert result.original_input == user_input
        assert result.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]
        assert result.smart_analysis is not None
        assert result.processing_time_ms > 0
        assert len(result.final_requirements) >= 1

        # Verify real LLM response structure
        assert isinstance(result.smart_analysis, dict)

    @pytest.mark.asyncio
    async def test_mine_requirements_vague_unclear(self, mining_service, mining_context):
        """Test mining requirements for vague input with real LLM"""
        user_input = "Help me with business stuff"

        result = await mining_service.mine_requirements(user_input, mining_context)

        assert isinstance(result, MiningResult)
        assert result.demand_state in ["VAGUE_UNCLEAR", "SMART_COMPLIANT", "SMART_LARGE_SCOPE"]
        assert result.smart_analysis is not None

    @pytest.mark.asyncio
    async def test_mine_requirements_complex_domain(self, mining_service, mining_context):
        """Test mining requirements for complex domain-specific input"""
        mining_context.domain = "technology"
        user_input = "Develop a comprehensive AI strategy for enterprise digital transformation including implementation roadmap, risk assessment, and ROI projections for the next 18 months"

        result = await mining_service.mine_requirements(user_input, mining_context)

        assert isinstance(result, MiningResult)
        assert result.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]

    @pytest.mark.asyncio
    async def test_mine_requirements_empty_input(self, mining_service, mining_context):
        """Test mining requirements with empty input"""
        with pytest.raises(ValueError, match="Empty user input provided for mining"):
            await mining_service.mine_requirements("", mining_context)

    @pytest.mark.asyncio
    async def test_mine_requirements_whitespace_input(self, mining_service, mining_context):
        """Test mining requirements with whitespace-only input"""
        with pytest.raises(ValueError, match="Empty user input provided for mining"):
            await mining_service.mine_requirements("   \n\t   ", mining_context)


class TestMiningServiceWorkflowNodes:
    """Test suite for individual workflow nodes"""

    @pytest.mark.asyncio
    async def test_analyze_demand_node(self, mining_service, sample_mining_state):
        """Test analyze demand node functionality with real LLM"""
        result_state = await mining_service._analyze_demand_node(sample_mining_state)

        assert result_state.demand_state is not None
        assert result_state.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE", "VAGUE_UNCLEAR"]
        assert result_state.smart_analysis is not None
        assert result_state.error is None

        # Verify real LLM analysis structure
        assert isinstance(result_state.smart_analysis, dict)

    @pytest.mark.asyncio
    async def test_intent_analysis_node(self, mining_service, sample_mining_state):
        """Test intent analysis node functionality with real LLM"""
        # Set up state with demand analysis completed
        sample_mining_state.demand_state = "SMART_COMPLIANT"
        sample_mining_state.smart_analysis = {"complexity": "medium"}

        result_state = await mining_service._intent_analysis_node(sample_mining_state)

        assert result_state.intent_analysis is not None
        assert result_state.error is None
        assert "intent_categories" in result_state.intent_analysis
        assert "complexity_assessment" in result_state.intent_analysis
        assert "intent_parsing_result" in result_state.intent_analysis

        # Verify real LLM intent analysis
        assert isinstance(result_state.intent_analysis["intent_categories"], list)
        assert isinstance(result_state.intent_analysis["complexity_assessment"], dict)

    @pytest.mark.asyncio
    async def test_meta_architect_flow_node(self, mining_service, sample_mining_state):
        """Test meta architect flow node for complex requests"""
        # Set up state with intent analysis completed
        sample_mining_state.demand_state = "SMART_LARGE_SCOPE"
        sample_mining_state.smart_analysis = {"complexity": "high"}
        sample_mining_state.intent_analysis = {
            "intent_categories": ["collect", "process", "analyze", "generate"],
            "complexity_assessment": {"complexity_level": "high"},
            "intent_parsing_result": {"categories": ["collect", "analyze"]}
        }

        result_state = await mining_service._meta_architect_flow_node(sample_mining_state)

        assert result_state.meta_architect_result is not None
        assert result_state.error is None
        assert "architect_output" in result_state.meta_architect_result
        assert "execution_roadmap" in result_state.meta_architect_result
        assert "entities_keywords" in result_state.meta_architect_result

    @pytest.mark.asyncio
    async def test_simple_strategy_flow_node(self, mining_service, sample_mining_state):
        """Test simple strategy flow node for simpler requests"""
        # Set up state with intent analysis completed
        sample_mining_state.demand_state = "SMART_COMPLIANT"
        sample_mining_state.smart_analysis = {"complexity": "low"}
        sample_mining_state.intent_analysis = {
            "intent_categories": ["analyze"],
            "complexity_assessment": {"complexity_level": "low"},
            "intent_parsing_result": {"categories": ["analyze"]}
        }

        result_state = await mining_service._simple_strategy_flow_node(sample_mining_state)

        assert result_state.simple_strategy_result is not None
        assert result_state.error is None
        assert "question_type" in result_state.simple_strategy_result
        assert "execution_strategy" in result_state.simple_strategy_result
        assert "intent_categories" in result_state.simple_strategy_result

    @pytest.mark.asyncio
    async def test_summarizer_flow_node_meta_architect(self, mining_service, sample_mining_state):
        """Test summarizer flow node with meta architect results"""
        # Set up state with meta architect results
        sample_mining_state.meta_architect_result = {
            "architect_output": {"problem_analysis": "complex analysis"},
            "execution_roadmap": {"steps": ["step1", "step2"]},
            "entities_keywords": {"entities": ["entity1"], "keywords": ["keyword1"]}
        }
        sample_mining_state.demand_state = "SMART_LARGE_SCOPE"
        sample_mining_state.smart_analysis = {"complexity": "high"}

        result_state = await mining_service._summarizer_flow_node(sample_mining_state)

        assert result_state.summarizer_result is not None
        assert result_state.error is None
        assert result_state.summarizer_result["summary_data"]["flow_type"] == "meta_architect"
        assert result_state.summarizer_result["ready_for_workflow_planning"] is True
        assert result_state.summarizer_result["user_feedback_required"] is True

    @pytest.mark.asyncio
    async def test_summarizer_flow_node_simple_strategy(self, mining_service, sample_mining_state):
        """Test summarizer flow node with simple strategy results"""
        # Set up state with simple strategy results
        sample_mining_state.simple_strategy_result = {
            "question_type": "analytical",
            "execution_strategy": {"execution_mode": "direct"},
            "intent_categories": ["analyze"],
            "complexity_assessment": {"complexity_level": "low"}
        }
        sample_mining_state.demand_state = "SMART_COMPLIANT"
        sample_mining_state.smart_analysis = {"complexity": "low"}

        result_state = await mining_service._summarizer_flow_node(sample_mining_state)

        assert result_state.summarizer_result is not None
        assert result_state.error is None
        assert result_state.summarizer_result["summary_data"]["flow_type"] == "simple_strategy"
        assert result_state.summarizer_result["ready_for_workflow_planning"] is True
        assert result_state.summarizer_result["user_feedback_required"] is False

    @pytest.mark.asyncio
    async def test_clarify_requirements_node(self, mining_service, sample_mining_state):
        """Test clarify requirements node functionality"""
        # Set up state for clarification
        sample_mining_state.demand_state = "VAGUE_UNCLEAR"
        sample_mining_state.smart_analysis = {"smart_analysis": {"specific": False, "measurable": False}}

        result_state = await mining_service._clarify_requirements_node(sample_mining_state)

        assert result_state.context.current_round == 1
        assert result_state.error is None
        assert len(result_state.messages) > 0
        assert "Clarification needed" in result_state.messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_generate_blueprint_node(self, mining_service, sample_mining_state):
        """Test generate blueprint node functionality with real LLM"""
        # Set up state for blueprint generation
        sample_mining_state.demand_state = "SMART_COMPLIANT"
        sample_mining_state.smart_analysis = {"scope_assessment": {"complexity": "medium"}}

        result_state = await mining_service._generate_blueprint_node(sample_mining_state)

        assert result_state.blueprint is not None
        assert result_state.error is None
        assert isinstance(result_state.blueprint, dict)

    @pytest.mark.asyncio
    async def test_confirm_blueprint_node(self, mining_service, sample_mining_state):
        """Test confirm blueprint node functionality"""
        # Set up state with blueprint
        sample_mining_state.blueprint = {
            "problem_analysis": {
                "complexity": "low"
            },
            "tree_structure": {
                "strategy": "test_strategy"
            }
        }

        result_state = await mining_service._confirm_blueprint_node(sample_mining_state)

        assert result_state.user_confirmed is True
        assert result_state.error is None
        assert len(result_state.messages) > 0

    @pytest.mark.asyncio
    async def test_finalize_result_node(self, mining_service, sample_mining_state):
        """Test finalize result node functionality"""
        # Set up state for finalization
        sample_mining_state.demand_state = "SMART_COMPLIANT"
        sample_mining_state.smart_analysis = {"analysis": "complete"}

        result_state = await mining_service._finalize_result_node(sample_mining_state)

        assert result_state.completed is True
        assert result_state.error is None
        assert len(result_state.messages) > 0
        assert "Mining process completed successfully" in result_state.messages[-1]["content"]


class TestMiningServiceRouting:
    """Test suite for workflow routing logic"""

    def test_route_after_analysis_smart_compliant(self, mining_service, sample_mining_state):
        """Test routing after analysis for SMART compliant input"""
        sample_mining_state.demand_state = DemandState.SMART_COMPLIANT.value

        route = mining_service._route_after_analysis(sample_mining_state)
        assert route == "intent_analysis"

    def test_route_after_analysis_smart_large_scope(self, mining_service, sample_mining_state):
        """Test routing after analysis for SMART large scope input"""
        sample_mining_state.demand_state = DemandState.SMART_LARGE_SCOPE.value

        route = mining_service._route_after_analysis(sample_mining_state)
        assert route == "intent_analysis"

    def test_route_after_analysis_vague_unclear(self, mining_service, sample_mining_state):
        """Test routing after analysis for vague unclear input"""
        sample_mining_state.demand_state = DemandState.VAGUE_UNCLEAR.value

        route = mining_service._route_after_analysis(sample_mining_state)
        assert route == "clarify"

    def test_route_after_analysis_error(self, mining_service, sample_mining_state):
        """Test routing after analysis with error"""
        sample_mining_state.error = "Test error"

        route = mining_service._route_after_analysis(sample_mining_state)
        assert route == "error"

    def test_route_after_intent_analysis_complex(self, mining_service, sample_mining_state):
        """Test routing after intent analysis for complex requests"""
        sample_mining_state.intent_analysis = {
            "intent_categories": ["collect", "process", "analyze", "generate"],
            "complexity_assessment": {"complexity_level": "high"}
        }

        route = mining_service._route_after_intent_analysis(sample_mining_state)
        assert route == "meta_architect"

    def test_route_after_intent_analysis_simple(self, mining_service, sample_mining_state):
        """Test routing after intent analysis for simple requests"""
        sample_mining_state.intent_analysis = {
            "intent_categories": ["analyze"],
            "complexity_assessment": {"complexity_level": "low"}
        }

        route = mining_service._route_after_intent_analysis(sample_mining_state)
        assert route == "simple_strategy"

    def test_route_after_clarification_continue(self, mining_service, sample_mining_state):
        """Test routing after clarification to continue clarifying"""
        sample_mining_state.demand_state = DemandState.VAGUE_UNCLEAR.value
        sample_mining_state.context.current_round = 1

        route = mining_service._route_after_clarification(sample_mining_state)
        assert route == "continue_clarify"

    def test_route_after_clarification_generate(self, mining_service, sample_mining_state):
        """Test routing after clarification to generate blueprint"""
        sample_mining_state.demand_state = DemandState.SMART_COMPLIANT.value
        sample_mining_state.context.current_round = 3

        route = mining_service._route_after_clarification(sample_mining_state)
        assert route == "generate"

    def test_route_after_confirmation_confirmed(self, mining_service, sample_mining_state):
        """Test routing after confirmation when user confirmed"""
        sample_mining_state.user_confirmed = True

        route = mining_service._route_after_confirmation(sample_mining_state)
        assert route == "confirmed"

    def test_route_after_confirmation_not_confirmed(self, mining_service, sample_mining_state):
        """Test routing after confirmation when user not confirmed"""
        sample_mining_state.user_confirmed = False

        route = mining_service._route_after_confirmation(sample_mining_state)
        assert route == "confirmed"  # For now, proceed anyway


class TestMiningServiceErrorHandling:
    """Test suite for error handling and fallback mechanisms"""

    @pytest.mark.asyncio
    async def test_analyze_demand_node_error_handling(self, mining_service, mining_context):
        """Test error handling in analyze demand node"""
        # Create a state that might cause errors
        state = MiningState(
            user_input="",  # Empty input might cause issues in processing
            context=mining_context,
            messages=[]
        )

        # The node should handle errors gracefully
        result_state = await mining_service._analyze_demand_node(state)

        # Should have a fallback demand_state even if there are errors
        assert result_state.demand_state is not None
        assert result_state.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE", "VAGUE_UNCLEAR"]

    @pytest.mark.asyncio
    async def test_intent_analysis_node_error_handling(self, mining_service, sample_mining_state):
        """Test error handling in intent analysis node"""
        # Set up state that might cause errors
        sample_mining_state.context = None  # This might cause issues

        result_state = await mining_service._intent_analysis_node(sample_mining_state)

        # Should handle errors gracefully
        if result_state.error:
            assert "Intent analysis failed" in result_state.error

    def test_infer_demand_state_from_analysis(self, mining_service):
        """Test demand state inference from analysis"""
        # Test with valid smart analysis
        smart_analysis = {
            "smart_analysis": {
                "specific": True,
                "measurable": True,
                "achievable": True,
                "relevant": True,
                "time_bound": False
            },
            "scope_assessment": {"complexity": "high"}
        }

        result = mining_service._infer_demand_state_from_analysis(smart_analysis, "test input")
        assert result == "SMART_LARGE_SCOPE"

    def test_get_fallback_demand_state(self, mining_service):
        """Test fallback demand state generation"""
        # Test with vague input
        result = mining_service._get_fallback_demand_state("help me")
        assert result == "VAGUE_UNCLEAR"

        # Test with specific input
        result = mining_service._get_fallback_demand_state("analyze Apple's Q3 2024 financial performance")
        assert result in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]

        # Test with short input
        result = mining_service._get_fallback_demand_state("hi")
        assert result == "VAGUE_UNCLEAR"


class TestMiningServiceUtilityMethods:
    """Test suite for utility methods"""

    @pytest.mark.asyncio
    async def test_generate_clarification_questions(self, mining_service, sample_mining_state):
        """Test clarification questions generation"""
        sample_mining_state.smart_analysis = {
            "smart_analysis": {
                "specific": False,
                "measurable": False,
                "time_bound": True,
                "relevant": True
            }
        }

        questions = await mining_service._generate_clarification_questions(sample_mining_state)

        assert isinstance(questions, list)
        assert len(questions) > 0
        assert any("specific" in q.lower() for q in questions)
        assert any("measurable" in q.lower() for q in questions)

    def test_create_blueprint_summary(self, mining_service):
        """Test blueprint summary creation"""
        blueprint = {
            "problem_analysis": {"complexity": "medium"},
            "tree_structure": {"strategy": "divide_and_conquer", "estimated_depth": 3}
        }

        summary = mining_service._create_blueprint_summary(blueprint)
        assert isinstance(summary, str)
        assert "medium" in summary
        assert "divide_and_conquer" in summary

    def test_extract_final_requirements(self, mining_service, sample_mining_state):
        """Test final requirements extraction"""
        sample_mining_state.intent_analysis = {
            "intent_categories": ["analyze", "generate"],
            "complexity_assessment": {"complexity_level": "medium"}
        }
        sample_mining_state.meta_architect_result = {
            "architect_output": {"problem_analysis": "strategic analysis"}
        }

        requirements = mining_service._extract_final_requirements(sample_mining_state)

        assert isinstance(requirements, list)
        assert len(requirements) > 0
        assert sample_mining_state.user_input in requirements

    def test_extract_clarification_history(self, mining_service, sample_mining_state):
        """Test clarification history extraction"""
        sample_mining_state.messages = [
            {"role": "assistant", "content": "Clarification needed (Round 1): What specific metrics?"},
            {"role": "user", "content": "Revenue and profit margins"}
        ]

        history = mining_service._extract_clarification_history(sample_mining_state)

        assert isinstance(history, list)
        if len(history) > 0:
            assert "round" in history[0]
            assert "question" in history[0]

    def test_get_current_time_ms(self, mining_service):
        """Test current time in milliseconds"""
        time_ms = mining_service._get_current_time_ms()
        assert isinstance(time_ms, float)
        assert time_ms > 0

    def test_get_current_timestamp(self, mining_service):
        """Test current timestamp"""
        timestamp = mining_service._get_current_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0


class TestMiningServiceMetricsAndHealth:
    """Test suite for metrics and health check functionality"""

    @pytest.mark.asyncio
    async def test_service_metrics_tracking(self, mining_service, mining_context):
        """Test service metrics tracking with real operations"""
        initial_metrics = mining_service.get_service_metrics()
        assert initial_metrics['total_mining_operations'] == 0
        assert initial_metrics['successful_operations'] == 0
        assert initial_metrics['success_rate'] == 0.0
        assert initial_metrics['framework'] == "langgraph_with_agents"

        # Perform real mining operations
        test_inputs = [
            "Analyze customer satisfaction trends for Q3 2024",
            "Create a competitive analysis report for the smartphone market"
        ]

        for user_input in test_inputs:
            await mining_service.mine_requirements(user_input, mining_context)

        updated_metrics = mining_service.get_service_metrics()
        assert updated_metrics['total_mining_operations'] == 2
        assert updated_metrics['successful_operations'] == 2
        assert updated_metrics['success_rate'] == 1.0

    @pytest.mark.asyncio
    async def test_health_check_real_agents(self, mining_service):
        """Test mining service health check with real agents"""
        health_status = await mining_service.health_check()

        assert health_status['service_status'] == 'healthy'
        assert 'intent_parser_status' in health_status
        assert 'meta_architect_status' in health_status
        assert 'workflow_initialized' in health_status
        assert health_status['workflow_initialized'] is True
        assert 'config_manager_available' in health_status
        assert 'llm_manager_available' in health_status
        assert 'metrics' in health_status

        # Verify agent capabilities if available
        if 'agent_capabilities' in health_status:
            assert 'intent_parser' in health_status['agent_capabilities']
            assert 'meta_architect' in health_status['agent_capabilities']

    def test_update_metrics(self, mining_service):
        """Test metrics update functionality"""
        initial_total = mining_service._total_mining_operations
        initial_successful = mining_service._successful_operations

        # Test successful operation
        mining_service._update_metrics(True, 2)

        assert mining_service._total_mining_operations == initial_total + 1
        assert mining_service._successful_operations == initial_successful + 1

        # Test failed operation
        mining_service._update_metrics(False, 0)

        assert mining_service._total_mining_operations == initial_total + 2
        assert mining_service._successful_operations == initial_successful + 1


class TestMiningServiceDataClasses:
    """Test suite for data classes and enums"""

    def test_demand_state_enum(self):
        """Test DemandState enum values"""
        assert DemandState.SMART_COMPLIANT.value == "SMART_COMPLIANT"
        assert DemandState.SMART_LARGE_SCOPE.value == "SMART_LARGE_SCOPE"
        assert DemandState.VAGUE_UNCLEAR.value == "VAGUE_UNCLEAR"

    def test_mining_context_dataclass(self):
        """Test MiningContext dataclass functionality"""
        context = MiningContext(
            user_id="test_user",
            session_id="test_session",
            domain="test_domain",
            task_id="test_task",
            max_clarification_rounds=5,
            current_round=1
        )

        assert context.user_id == "test_user"
        assert context.session_id == "test_session"
        assert context.domain == "test_domain"
        assert context.task_id == "test_task"
        assert context.max_clarification_rounds == 5
        assert context.current_round == 1

    def test_mining_state_dataclass(self):
        """Test MiningState dataclass functionality"""
        context = MiningContext(user_id="test", task_id="test")
        state = MiningState(
            user_input="test input",
            context=context,
            messages=[]
        )

        assert state.user_input == "test input"
        assert state.context.user_id == "test"
        assert state.demand_state is None
        assert state.completed is False
        assert state.intent_analysis is None
        assert state.meta_architect_result is None
        assert state.simple_strategy_result is None
        assert state.summarizer_result is None

    def test_mining_result_dataclass(self):
        """Test MiningResult dataclass functionality"""
        result = MiningResult(
            original_input="test input",
            final_requirements=["requirement 1"],
            demand_state="SMART_COMPLIANT",
            smart_analysis={"specific": True},
            blueprint={"strategy": "test"},
            clarification_history=[],
            processing_time_ms=100.0,
            user_confirmed=True
        )

        assert result.original_input == "test input"
        assert result.demand_state == "SMART_COMPLIANT"
        assert result.user_confirmed is True
        assert result.processing_time_ms == 100.0


class TestMiningServiceIntegration:
    """Integration tests for mining service with workflow planning"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_real_llm(self, mining_service, workflow_planning_service, mining_context):
        """Test complete end-to-end workflow from mining to planning with real LLM"""
        # Step 1: Mine requirements with real LLM
        user_input = "Create a comprehensive competitive intelligence report for the electric vehicle market, including market share analysis, technology trends, and strategic recommendations for the next 2 years"
        mining_result = await mining_service.mine_requirements(user_input, mining_context)

        assert isinstance(mining_result, MiningResult)
        assert mining_result.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]

        # Step 2: Extract intent categories from real mining result
        # Simulate intent extraction (in real implementation, this would be part of mining)
        mining_output = {
            "intent_categories": ["collect", "analyze", "generate"],
            "intent_confidence": 0.85,
            "intent_reasoning": "Comprehensive competitive intelligence requiring data collection, analysis, and strategic reporting",
            "strategic_blueprint": mining_result.blueprint
        }

        # Step 3: Create workflow plan with real LLM
        workflow_result = await workflow_planning_service.create_workflow_plan(
            mining_output, user_id=mining_context.user_id, task_id=mining_context.task_id
        )

        assert workflow_result['success'] is True
        assert len(workflow_result['intent']['categories']) == 3
        assert 'workflow_plan' in workflow_result
        assert 'validation' in workflow_result
        assert workflow_result['validation']['is_valid'] is True

        # Verify real LLM integration quality
        assert len(str(workflow_result['decomposition'])) > 200  # Substantial content
        assert len(str(workflow_result['workflow_plan'])) > 200  # Substantial content

    @pytest.mark.asyncio
    async def test_performance_with_real_llm(self, mining_service, mining_context):
        """Test performance metrics with real LLM calls"""
        # Test mining service performance
        start_time = time.time()
        user_input = "Develop a digital transformation strategy for a traditional manufacturing company, including technology adoption roadmap and change management plan"
        mining_result = await mining_service.mine_requirements(user_input, mining_context)
        mining_time = time.time() - start_time

        assert mining_result.processing_time_ms > 0
        assert mining_time < 60  # Should complete within 60 seconds for real LLM

    @pytest.mark.asyncio
    async def test_real_config_manager_integration(self, real_config_manager):
        """Test that real config manager is properly integrated"""
        assert real_config_manager is not None

        # Test that config manager can provide real configurations
        try:
            # Test prompts config access
            prompts_config = real_config_manager.get_prompts_config()
            assert isinstance(prompts_config, dict)
            # Check if there are any prompts loaded
            if prompts_config:
                assert len(prompts_config) > 0
        except Exception as e:
            # Config may not have all prompts, but should not crash
            assert "not found" in str(e).lower() or "missing" in str(e).lower()

        try:
            # Test task config access
            task_config = real_config_manager.get_task_config('collect_search')
            assert isinstance(task_config, dict)
        except Exception as e:
            # Config may not have all tasks, but should not crash
            assert "not found" in str(e).lower() or "missing" in str(e).lower()


class TestWorkflowPlanningService:
    """Comprehensive test suite for WorkflowPlanningService with real LLM integration"""

    @pytest.mark.asyncio
    async def test_workflow_planning_service_initialization(self, workflow_planning_service):
        """Test workflow planning service initialization with real agents"""
        assert workflow_planning_service is not None
        assert workflow_planning_service.task_decomposer is not None
        assert workflow_planning_service.planner is not None
        assert workflow_planning_service.plan_validator is not None
        assert workflow_planning_service.workflow_graph is not None
        assert workflow_planning_service.total_plans_created == 0

        # Test that real agents are properly initialized
        assert hasattr(workflow_planning_service.task_decomposer, 'agent_id')
        assert hasattr(workflow_planning_service.planner, 'agent_id')

    @pytest.mark.asyncio
    async def test_create_workflow_plan_success_real_llm(self, workflow_planning_service):
        """Test successful workflow plan creation with real LLM"""
        mining_input = {
            "intent_categories": ["collect", "analyze", "generate"],
            "intent_confidence": 0.85,
            "intent_reasoning": "Clear data analysis request requiring data collection, analysis, and report generation",
            "strategic_blueprint": {
                "problem_analysis": {"complexity": "medium", "domain": "market_research"},
                "tree_structure": {"strategy": "divide_and_conquer", "estimated_depth": 3}
            }
        }

        result = await workflow_planning_service.create_workflow_plan(
            mining_input, user_id="test_user", task_id="test_task_001"
        )

        assert result['success'] is True
        assert result['task_id'] == "test_task_001"
        assert result['user_id'] == "test_user"
        assert 'intent' in result
        assert 'decomposition' in result
        assert 'workflow_plan' in result
        assert 'validation' in result
        assert 'metadata' in result

        # Verify real LLM generated meaningful content
        assert len(result['decomposition']['subtask_breakdown']) > 0
        assert len(result['workflow_plan']['dsl_plan']) > 0
        assert result['validation']['is_valid'] is True

    @pytest.mark.asyncio
    async def test_create_workflow_plan_complex_scenario(self, workflow_planning_service):
        """Test workflow plan creation for complex scenario with real LLM"""
        complex_mining_input = {
            "intent_categories": ["collect", "process", "analyze", "generate"],
            "intent_confidence": 0.9,
            "intent_reasoning": "Complex multi-domain analysis requiring data collection, processing, analysis, and comprehensive reporting",
            "strategic_blueprint": {
                "problem_analysis": {
                    "complexity": "high",
                    "domain": "multi_domain",
                    "key_challenges": ["data_integration", "cross_domain_analysis", "scalability"]
                },
                "tree_structure": {
                    "strategy": "hierarchical_decomposition",
                    "estimated_depth": 4,
                    "main_branches": ["data_collection", "preprocessing", "analysis", "synthesis", "reporting"]
                }
            }
        }

        result = await workflow_planning_service.create_workflow_plan(complex_mining_input)

        assert result['success'] is True
        assert len(result['intent']['categories']) == 4

        # Verify complex workflow structure from real LLM
        assert 'workflow_plan' in result
        assert 'execution_order' in result['workflow_plan']
        assert 'dependencies' in result['workflow_plan']
        assert len(result['workflow_plan']['execution_order']) > 0

        # Real LLM should handle complexity assessment
        assert 'complexity_assessment' in result['metadata']
        complexity = result['metadata']['complexity_assessment']
        assert complexity['complexity_level'] in ['medium', 'high']


class TestMiningServiceEndToEndWorkflow:
    """End-to-end workflow tests from analyze_demand to summarizer_flow with multiple scenarios"""

    @pytest.mark.asyncio
    async def test_smart_compliant_complete_workflow(self, mining_service, mining_context):
        """Test complete workflow for SMART compliant input: analyze_demand -> intent_analysis -> simple_strategy -> summarizer"""
        user_input = "Analyze Apple's Q3 2024 revenue growth compared to Q2 2024, focusing on iPhone sales data and market share changes"

        # Create initial state
        initial_state = MiningState(
            user_input=user_input,
            context=mining_context,
            messages=[]
        )

        # Step 1: Analyze demand
        state_after_demand = await mining_service._analyze_demand_node(initial_state)
        assert state_after_demand.demand_state is not None
        assert state_after_demand.smart_analysis is not None
        assert state_after_demand.error is None

        # Step 2: Intent analysis (should be routed here for SMART_COMPLIANT)
        if state_after_demand.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]:
            state_after_intent = await mining_service._intent_analysis_node(state_after_demand)
            assert state_after_intent.intent_analysis is not None
            assert state_after_intent.error is None

            # Step 3: Route to appropriate flow based on complexity
            route = mining_service._route_after_intent_analysis(state_after_intent)

            if route == "simple_strategy":
                # Step 4a: Simple strategy flow
                state_after_strategy = await mining_service._simple_strategy_flow_node(state_after_intent)
                assert state_after_strategy.simple_strategy_result is not None
                assert state_after_strategy.error is None

                # Step 5a: Summarizer flow
                final_state = await mining_service._summarizer_flow_node(state_after_strategy)
                assert final_state.summarizer_result is not None
                assert final_state.summarizer_result["summary_data"]["flow_type"] == "simple_strategy"
                assert final_state.error is None

            elif route == "meta_architect":
                # Step 4b: Meta architect flow
                state_after_architect = await mining_service._meta_architect_flow_node(state_after_intent)
                assert state_after_architect.meta_architect_result is not None
                assert state_after_architect.error is None

                # Step 5b: Summarizer flow
                final_state = await mining_service._summarizer_flow_node(state_after_architect)
                assert final_state.summarizer_result is not None
                assert final_state.summarizer_result["summary_data"]["flow_type"] == "meta_architect"
                assert final_state.error is None

    @pytest.mark.asyncio
    async def test_smart_large_scope_complete_workflow(self, mining_service, mining_context):
        """Test complete workflow for SMART large scope input: analyze_demand -> intent_analysis -> meta_architect -> summarizer"""
        user_input = "Develop a comprehensive AI-powered enterprise solution that integrates machine learning, natural language processing, computer vision, and predictive analytics to transform business operations across multiple departments including sales, marketing, customer service, and supply chain management"

        # Create initial state
        initial_state = MiningState(
            user_input=user_input,
            context=mining_context,
            messages=[]
        )

        # Step 1: Analyze demand
        state_after_demand = await mining_service._analyze_demand_node(initial_state)
        assert state_after_demand.demand_state is not None
        assert state_after_demand.smart_analysis is not None
        assert state_after_demand.error is None

        # Step 2: Intent analysis
        if state_after_demand.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]:
            state_after_intent = await mining_service._intent_analysis_node(state_after_demand)
            assert state_after_intent.intent_analysis is not None
            assert state_after_intent.error is None

            # Step 3: Should route to meta_architect for complex requests
            route = mining_service._route_after_intent_analysis(state_after_intent)

            if route == "meta_architect":
                # Step 4: Meta architect flow
                state_after_architect = await mining_service._meta_architect_flow_node(state_after_intent)
                assert state_after_architect.meta_architect_result is not None
                assert "architect_output" in state_after_architect.meta_architect_result
                assert "execution_roadmap" in state_after_architect.meta_architect_result
                assert "entities_keywords" in state_after_architect.meta_architect_result
                assert state_after_architect.error is None

                # Step 5: Summarizer flow
                final_state = await mining_service._summarizer_flow_node(state_after_architect)
                assert final_state.summarizer_result is not None
                assert final_state.summarizer_result["summary_data"]["flow_type"] == "meta_architect"
                assert final_state.summarizer_result["ready_for_workflow_planning"] is True
                assert final_state.error is None

    @pytest.mark.asyncio
    async def test_vague_unclear_complete_workflow_with_clarification(self, mining_service, mining_context):
        """Test complete workflow for vague input: analyze_demand -> clarify -> intent_analysis -> flow -> summarizer"""
        user_input = "Help me with business stuff"

        # Create initial state
        initial_state = MiningState(
            user_input=user_input,
            context=mining_context,
            messages=[]
        )

        # Step 1: Analyze demand
        state_after_demand = await mining_service._analyze_demand_node(initial_state)
        assert state_after_demand.demand_state is not None
        assert state_after_demand.smart_analysis is not None

        # Step 2: Should route to clarification for vague input
        route_after_demand = mining_service._route_after_analysis(state_after_demand)

        if route_after_demand == "clarify":
            # Step 3: Clarification round
            state_after_clarify = await mining_service._clarify_requirements_node(state_after_demand)
            assert state_after_clarify.context.current_round > 0
            assert len(state_after_clarify.messages) > 0

            # Simulate clarification completion by updating demand_state
            state_after_clarify.demand_state = "SMART_COMPLIANT"  # Simulate clarification success

            # Step 4: Route after clarification should now go to intent_analysis
            route_after_clarify = mining_service._route_after_clarification(state_after_clarify)
            assert route_after_clarify == "intent_analysis"

            # Step 5: Intent analysis
            state_after_intent = await mining_service._intent_analysis_node(state_after_clarify)
            assert state_after_intent.intent_analysis is not None
            assert state_after_intent.error is None

            # Step 6: Route to appropriate flow
            route = mining_service._route_after_intent_analysis(state_after_intent)

            if route == "simple_strategy":
                # Step 7a: Simple strategy flow
                state_after_strategy = await mining_service._simple_strategy_flow_node(state_after_intent)
                assert state_after_strategy.simple_strategy_result is not None

                # Step 8a: Summarizer flow
                final_state = await mining_service._summarizer_flow_node(state_after_strategy)
                assert final_state.summarizer_result is not None
                assert final_state.error is None

            elif route == "meta_architect":
                # Step 7b: Meta architect flow
                state_after_architect = await mining_service._meta_architect_flow_node(state_after_intent)
                assert state_after_architect.meta_architect_result is not None

                # Step 8b: Summarizer flow
                final_state = await mining_service._summarizer_flow_node(state_after_architect)
                assert final_state.summarizer_result is not None
                assert final_state.error is None

    @pytest.mark.asyncio
    async def test_multiple_clarification_rounds_workflow(self, mining_service, mining_context):
        """Test workflow with multiple clarification rounds before proceeding to intent_analysis"""
        user_input = "I need help"

        # Create initial state
        initial_state = MiningState(
            user_input=user_input,
            context=mining_context,
            messages=[]
        )

        # Step 1: Analyze demand
        state_after_demand = await mining_service._analyze_demand_node(initial_state)

        # Step 2: Multiple clarification rounds
        current_state = state_after_demand
        max_rounds = 2

        for round_num in range(max_rounds):
            if mining_service._route_after_analysis(current_state) == "clarify":
                current_state = await mining_service._clarify_requirements_node(current_state)
                assert current_state.context.current_round == round_num + 1

                # Check routing after clarification
                route = mining_service._route_after_clarification(current_state)
                if current_state.context.current_round < current_state.context.max_clarification_rounds:
                    # Should continue clarifying if still vague
                    if current_state.demand_state == "VAGUE_UNCLEAR":
                        assert route == "continue_clarify"
                    else:
                        # If clarified, should go to intent_analysis
                        assert route == "intent_analysis"
                        break
                else:
                    # After max rounds, should proceed to intent_analysis
                    assert route == "intent_analysis"
                    break

        # Simulate successful clarification
        current_state.demand_state = "SMART_COMPLIANT"

        # Step 3: Intent analysis after clarification
        state_after_intent = await mining_service._intent_analysis_node(current_state)
        assert state_after_intent.intent_analysis is not None
        assert state_after_intent.error is None

    @pytest.mark.asyncio
    async def test_workflow_routing_validation(self, mining_service, mining_context):
        """Test all routing decisions in the workflow"""
        # Test different demand states and their routing
        test_cases = [
            {
                "demand_state": "SMART_COMPLIANT",
                "expected_route_after_analysis": "intent_analysis"
            },
            {
                "demand_state": "SMART_LARGE_SCOPE",
                "expected_route_after_analysis": "intent_analysis"
            },
            {
                "demand_state": "VAGUE_UNCLEAR",
                "expected_route_after_analysis": "clarify"
            }
        ]

        for case in test_cases:
            # Create test state
            test_state = MiningState(
                user_input="Test input",
                context=mining_context,
                messages=[],
                demand_state=case["demand_state"]
            )

            # Test routing after analysis
            route = mining_service._route_after_analysis(test_state)
            assert route == case["expected_route_after_analysis"]

        # Test routing after clarification
        clarify_state = MiningState(
            user_input="Test input",
            context=mining_context,
            messages=[],
            demand_state="SMART_COMPLIANT"
        )

        route_after_clarify = mining_service._route_after_clarification(clarify_state)
        assert route_after_clarify == "intent_analysis"  # Should now route to intent_analysis

        # Test routing after intent analysis
        intent_test_cases = [
            {
                "intent_analysis": {
                    "intent_categories": ["collect", "process", "analyze", "generate"],
                    "complexity_assessment": {"complexity_level": "high"}
                },
                "expected_route": "meta_architect"
            },
            {
                "intent_analysis": {
                    "intent_categories": ["analyze"],
                    "complexity_assessment": {"complexity_level": "low"}
                },
                "expected_route": "simple_strategy"
            }
        ]

        for case in intent_test_cases:
            intent_state = MiningState(
                user_input="Test input",
                context=mining_context,
                messages=[],
                intent_analysis=case["intent_analysis"]
            )

            route = mining_service._route_after_intent_analysis(intent_state)
            assert route == case["expected_route"]


class TestCoverageValidationRealLLM:
    """Additional tests to ensure >85% coverage with real LLM integration"""

    @pytest.mark.asyncio
    async def test_real_llm_integration_calls(self, mining_service, mining_context, real_llm_manager):
        """Test that real LLM integration calls are made and return meaningful content"""
        user_input = "Conduct a comprehensive analysis of renewable energy market opportunities in Southeast Asia"

        result = await mining_service.mine_requirements(user_input, mining_context)

        # Verify real LLM was called and returned meaningful content
        assert isinstance(result, MiningResult)
        assert result.smart_analysis is not None

        # Real LLM should provide detailed analysis
        assert len(str(result.smart_analysis)) > 100

        # Verify content quality from real LLM
        smart_analysis_str = str(result.smart_analysis).lower()
        # Should contain some analysis-related terms
        analysis_terms = ['analysis', 'assessment', 'evaluation', 'specific', 'measurable', 'achievable', 'relevant', 'time']
        assert any(term in smart_analysis_str for term in analysis_terms)

    @pytest.mark.asyncio
    async def test_workflow_nodes_error_recovery(self, mining_service, mining_context):
        """Test that workflow nodes can recover from errors"""
        # Test with potentially problematic input
        user_input = "???"  # Very short, unclear input

        result = await mining_service.mine_requirements(user_input, mining_context)

        # Should still complete successfully with fallback mechanisms
        assert isinstance(result, MiningResult)
        assert result.demand_state is not None
        assert result.smart_analysis is not None

    @pytest.mark.asyncio
    async def test_complex_workflow_execution(self, mining_service, mining_context):
        """Test complex workflow execution with multiple nodes"""
        user_input = "Develop a comprehensive AI-powered customer analytics platform that can collect data from multiple sources, process it in real-time, analyze customer behavior patterns, predict future trends, and generate automated reports with actionable insights for business stakeholders"

        result = await mining_service.mine_requirements(user_input, mining_context)

        assert isinstance(result, MiningResult)
        assert result.demand_state in ["SMART_COMPLIANT", "SMART_LARGE_SCOPE"]
        assert result.processing_time_ms > 0

        # Should have meaningful final requirements
        assert len(result.final_requirements) > 0
        assert any(len(req) > 10 for req in result.final_requirements)  # At least one substantial requirement


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=app.services.multi_task.services.demand.mining",
        "--cov=app.services.multi_task.services.planner.workflow_planning",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ])

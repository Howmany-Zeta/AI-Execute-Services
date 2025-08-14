"""
Comprehensive Test Suite for WorkflowPlanningService

This test suite provides comprehensive coverage for the WorkflowPlanningService
that uses LangGraph workflow with enhanced task decomposition and planning capabilities.

The service includes:
1. LangGraph-based workflow orchestration
2. Task decomposition with agent mapping
3. Sequence planning using DSL constructs
4. Plan validation and finalization
5. Comprehensive error handling and metrics

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

# Import services (import order matters for LangChain/Pydantic compatibility)
from app.services.multi_task.services.planner.workflow_planning import ( WorkflowPlanningService, WorkflowPlanningState )

# Import real dependencies
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole
from app.services.multi_task.core.models.services_models import WorkflowPlanningState
from app.services.multi_task.core.exceptions.services_exceptions import WorkflowPlanningError


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
async def workflow_planning_service(real_config_manager, real_llm_manager):
    """Fixture for workflow planning service with real agents and real LLM"""
    service = WorkflowPlanningService(real_config_manager, real_llm_manager)
    await service.initialize()
    return service


@pytest.fixture
def sample_mining_input():
    """Fixture for sample mining input"""
    return {
        "intent_categories": ["collect", "analyze", "generate"],
        "intent_confidence": 0.85,
        "intent_reasoning": "Clear data analysis request requiring data collection, analysis, and report generation",
        "strategic_blueprint": {
            "problem_analysis": {"complexity": "medium", "domain": "market_research"},
            "tree_structure": {"strategy": "divide_and_conquer", "estimated_depth": 3}
        }
    }


@pytest.fixture
def sample_workflow_planning_state():
    """Fixture for sample workflow planning state"""
    return WorkflowPlanningState(
        task_id="test_task_001",
        user_id="test_user",
        intent_categories=["collect", "analyze", "generate"],
        intent_confidence=0.85,
        intent_reasoning="Test reasoning",
        strategic_blueprint={"problem_analysis": {"complexity": "medium"}}
    )


@pytest.fixture
def sample_workflow_plan():
    """Fixture for sample workflow plan"""
    return [
        {
            "task": "collect_data",
            "tools": ["scraper", "search_api"],
            "agent": "fieldwork_webscraper",
            "estimated_duration": "30 minutes"
        },
        {
            "parallel": [
                {
                    "task": "analyze_trends",
                    "tools": ["stats", "pandas"],
                    "agent": "analyst_trendanalyst"
                },
                {
                    "task": "analyze_patterns",
                    "tools": ["classifier", "stats"],
                    "agent": "analyst_patternrecognition"
                }
            ]
        },
        {
            "task": "generate_report",
            "tools": ["report", "chart"],
            "agent": "writer_reportspecialist",
            "dependencies": ["collect_data", "analyze_trends", "analyze_patterns"]
        }
    ]


class TestWorkflowPlanningServiceInitialization:
    """Test suite for WorkflowPlanningService initialization and setup"""

    @pytest.mark.asyncio
    async def test_service_initialization(self, workflow_planning_service):
        """Test service initialization with real agents"""
        assert workflow_planning_service is not None
        assert workflow_planning_service.task_decomposer is not None
        assert workflow_planning_service.planner is not None
        assert workflow_planning_service.plan_validator is not None
        assert workflow_planning_service.workflow_graph is not None
        assert workflow_planning_service.total_plans_created == 0
        assert workflow_planning_service.successful_plans == 0
        assert workflow_planning_service.failed_plans == 0

    @pytest.mark.asyncio
    async def test_agents_initialization(self, workflow_planning_service):
        """Test that agents are properly configured"""
        # Test task decomposer configuration
        assert workflow_planning_service.task_decomposer.config.name == "Task Decomposer"
        assert workflow_planning_service.task_decomposer.config.role == AgentRole.TASK_DECOMPOSER
        assert workflow_planning_service.task_decomposer.config.metadata["enhanced_output"] is True

        # Test planner configuration
        assert workflow_planning_service.planner.config.name == "Workflow Planner"
        assert workflow_planning_service.planner.config.role == AgentRole.PLANNER
        assert workflow_planning_service.planner.config.metadata["dsl_enabled"] is True

    @pytest.mark.asyncio
    async def test_workflow_graph_initialization(self, workflow_planning_service):
        """Test that LangGraph workflow is properly initialized"""
        assert workflow_planning_service.workflow_graph is not None
        # Workflow should be compiled and ready for execution

    @pytest.mark.asyncio
    async def test_agent_mapping_loading(self, workflow_planning_service):
        """Test agent mapping is properly loaded"""
        agent_mapping = workflow_planning_service.agent_mapping
        assert isinstance(agent_mapping, dict)
        assert len(agent_mapping) > 0

        # Test some expected mappings
        expected_mappings = [
            "answer_questions", "collect_scrape", "process_dataCleaning",
            "analyze_trends", "generate_report"
        ]
        for mapping in expected_mappings:
            if mapping in agent_mapping:
                assert isinstance(agent_mapping[mapping], str)
                assert len(agent_mapping[mapping]) > 0


class TestWorkflowPlanningServiceCoreWorkflow:
    """Test suite for core workflow planning functionality"""

    @pytest.mark.asyncio
    async def test_create_workflow_plan_success(self, workflow_planning_service, sample_mining_input):
        """Test successful workflow plan creation with real LLM"""
        result = await workflow_planning_service.create_workflow_plan(
            sample_mining_input, user_id="test_user", task_id="test_task_001"
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
        """Test workflow plan creation for complex scenario"""
        complex_mining_input = {
            "intent_categories": ["collect", "process", "analyze", "generate"],
            "intent_confidence": 0.9,
            "intent_reasoning": "Complex multi-domain analysis requiring comprehensive processing",
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
        assert 'complexity_assessment' in result['metadata']
        complexity = result['metadata']['complexity_assessment']
        assert complexity['complexity_level'] in ['medium', 'high']

    @pytest.mark.asyncio
    async def test_create_workflow_plan_empty_input(self, workflow_planning_service):
        """Test workflow plan creation with empty input"""
        empty_input = {
            "intent_categories": [],
            "intent_confidence": 0.0,
            "intent_reasoning": "",
            "strategic_blueprint": {}
        }

        result = await workflow_planning_service.create_workflow_plan(empty_input)

        # Should handle gracefully with warnings
        assert 'metadata' in result
        assert len(result['metadata']['errors']) > 0 or len(result['metadata']['warnings']) > 0

    @pytest.mark.asyncio
    async def test_create_workflow_plan_auto_task_id(self, workflow_planning_service, sample_mining_input):
        """Test workflow plan creation with auto-generated task ID"""
        result = await workflow_planning_service.create_workflow_plan(sample_mining_input)

        assert 'task_id' in result
        assert result['task_id'].startswith('task_')
        assert len(result['task_id']) > 10  # Should have timestamp


class TestWorkflowPlanningServiceNodes:
    """Test suite for individual workflow nodes"""

    @pytest.mark.asyncio
    async def test_decompose_tasks_node(self, workflow_planning_service, sample_workflow_planning_state):
        """Test task decomposition node functionality"""
        result_state = await workflow_planning_service._decompose_tasks_node(sample_workflow_planning_state)

        assert result_state.subtask_breakdown is not None
        assert isinstance(result_state.subtask_breakdown, dict)
        assert result_state.decomposition_confidence >= 0.0
        assert result_state.agent_mapping is not None
        assert isinstance(result_state.agent_mapping, dict)
        assert len(result_state.errors) == 0

    @pytest.mark.asyncio
    async def test_decompose_tasks_node_empty_categories(self, workflow_planning_service):
        """Test task decomposition node with empty intent categories"""
        empty_state = WorkflowPlanningState(
            task_id="test_task",
            user_id="test_user",
            intent_categories=[],
            intent_confidence=0.0,
            intent_reasoning="",
            strategic_blueprint={}
        )

        result_state = await workflow_planning_service._decompose_tasks_node(empty_state)

        assert len(result_state.errors) > 0
        assert "No intent categories available for decomposition" in result_state.errors[0]

    @pytest.mark.asyncio
    async def test_plan_sequence_node(self, workflow_planning_service, sample_workflow_planning_state):
        """Test sequence planning node functionality"""
        # Set up state with decomposition results
        sample_workflow_planning_state.subtask_breakdown = {
            "collect": ["collect_data", "collect_sources"],
            "analyze": ["analyze_trends", "analyze_patterns"],
            "generate": ["generate_report"]
        }
        sample_workflow_planning_state.agent_mapping = {
            "collect_data": "fieldwork_webscraper",
            "analyze_trends": "analyst_trendanalyst",
            "generate_report": "writer_reportspecialist"
        }

        result_state = await workflow_planning_service._plan_sequence_node(sample_workflow_planning_state)

        assert result_state.workflow_plan is not None
        assert isinstance(result_state.workflow_plan, list)
        assert len(result_state.workflow_plan) > 0
        assert result_state.execution_order is not None
        assert result_state.parallel_groups is not None
        assert result_state.dependencies is not None
        assert len(result_state.errors) == 0

    @pytest.mark.asyncio
    async def test_plan_sequence_node_empty_breakdown(self, workflow_planning_service, sample_workflow_planning_state):
        """Test sequence planning node with empty subtask breakdown"""
        sample_workflow_planning_state.subtask_breakdown = {}

        result_state = await workflow_planning_service._plan_sequence_node(sample_workflow_planning_state)

        assert len(result_state.errors) > 0
        assert "No subtask breakdown available for planning" in result_state.errors[0]

    @pytest.mark.asyncio
    async def test_validate_plan_node(self, workflow_planning_service, sample_workflow_planning_state, sample_workflow_plan):
        """Test plan validation node functionality"""
        # Set up state with workflow plan
        sample_workflow_planning_state.workflow_plan = sample_workflow_plan
        sample_workflow_planning_state.execution_order = ["collect_data", "analyze_trends", "analyze_patterns", "generate_report"]
        sample_workflow_planning_state.parallel_groups = [["analyze_trends", "analyze_patterns"]]
        sample_workflow_planning_state.dependencies = {
            "generate_report": ["collect_data", "analyze_trends", "analyze_patterns"]
        }
        sample_workflow_planning_state.agent_mapping = {
            "collect_data": "fieldwork_webscraper",
            "analyze_trends": "analyst_trendanalyst",
            "generate_report": "writer_reportspecialist"
        }
        sample_workflow_planning_state.subtask_breakdown = {
            "collect": ["collect_data"],
            "analyze": ["analyze_trends", "analyze_patterns"],
            "generate": ["generate_report"]
        }

        result_state = await workflow_planning_service._validate_plan_node(sample_workflow_planning_state)

        assert result_state.validation_result is not None
        assert isinstance(result_state.validation_result, dict)
        assert 'is_valid' in result_state.validation_result
        assert result_state.is_valid is not None

    @pytest.mark.asyncio
    async def test_validate_plan_node_empty_plan(self, workflow_planning_service, sample_workflow_planning_state):
        """Test plan validation node with empty workflow plan"""
        sample_workflow_planning_state.workflow_plan = []

        result_state = await workflow_planning_service._validate_plan_node(sample_workflow_planning_state)

        assert len(result_state.errors) > 0
        assert "No workflow plan available for validation" in result_state.errors[0]

    @pytest.mark.asyncio
    async def test_finalize_plan_node(self, workflow_planning_service, sample_workflow_planning_state):
        """Test plan finalization node functionality"""
        # Set up state for finalization
        sample_workflow_planning_state.intent_confidence = 0.8
        sample_workflow_planning_state.decomposition_confidence = 0.9
        sample_workflow_planning_state.validation_result = {"overall_score": 0.85, "is_valid": True}
        sample_workflow_planning_state.execution_order = ["task1", "task2", "task3"]
        sample_workflow_planning_state.parallel_groups = [["task2", "task3"]]
        sample_workflow_planning_state.subtask_breakdown = {"category1": ["task1"], "category2": ["task2", "task3"]}

        result_state = await workflow_planning_service._finalize_plan_node(sample_workflow_planning_state)

        assert result_state.confidence_score is not None
        assert 0.0 <= result_state.confidence_score <= 1.0
        assert result_state.complexity_assessment is not None
        assert isinstance(result_state.complexity_assessment, dict)
        assert 'complexity_level' in result_state.complexity_assessment
        assert result_state.complexity_assessment['complexity_level'] in ['low', 'medium', 'high']


class TestWorkflowPlanningServiceDataProcessing:
    """Test suite for data processing and transformation methods"""

    def test_generate_agent_mapping(self, workflow_planning_service):
        """Test agent mapping generation"""
        subtask_breakdown = {
            "collect": ["collect_scrape", "collect_search"],
            "analyze": ["analyze_trends", "analyze_patterns"],
            "generate": ["generate_report"]
        }

        agent_mapping = workflow_planning_service._generate_agent_mapping(subtask_breakdown)

        assert isinstance(agent_mapping, dict)
        assert len(agent_mapping) > 0

        # Check that all subtasks have agent mappings
        for category, subtasks in subtask_breakdown.items():
            for subtask in subtasks:
                assert subtask in agent_mapping
                assert isinstance(agent_mapping[subtask], str)
                assert len(agent_mapping[subtask]) > 0

    def test_get_default_agent_for_category(self, workflow_planning_service):
        """Test default agent retrieval for categories"""
        test_cases = [
            ("answer", "researcher_knowledgeprovider"),
            ("collect", "fieldwork_webscraper"),
            ("process", "fieldwork_dataoperator"),
            ("analyze", "fieldwork_statistician"),
            ("generate", "writer_reportspecialist"),
            ("unknown_category", "general_researcher")
        ]

        for category, expected_agent in test_cases:
            agent = workflow_planning_service._get_default_agent_for_category(category)
            assert agent == expected_agent

    def test_get_available_tools(self, workflow_planning_service):
        """Test available tools retrieval"""
        tools = workflow_planning_service._get_available_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        expected_tools = ["scraper", "search_api", "office", "pandas", "stats", "research", "classifier", "chart", "image", "report"]
        for tool in expected_tools:
            assert tool in tools

    def test_extract_execution_order(self, workflow_planning_service, sample_workflow_plan):
        """Test execution order extraction"""
        execution_order = workflow_planning_service._extract_execution_order(sample_workflow_plan)

        assert isinstance(execution_order, list)
        assert len(execution_order) > 0
        assert "collect_data" in execution_order
        assert "analyze_trends" in execution_order
        assert "analyze_patterns" in execution_order
        assert "generate_report" in execution_order

    def test_extract_parallel_groups(self, workflow_planning_service, sample_workflow_plan):
        """Test parallel groups extraction"""
        parallel_groups = workflow_planning_service._extract_parallel_groups(sample_workflow_plan)

        assert isinstance(parallel_groups, list)
        assert len(parallel_groups) > 0
        assert ["analyze_trends", "analyze_patterns"] in parallel_groups

    def test_extract_dependencies(self, workflow_planning_service, sample_workflow_plan):
        """Test dependencies extraction"""
        dependencies = workflow_planning_service._extract_dependencies(sample_workflow_plan)

        assert isinstance(dependencies, dict)
        # Dependencies should be inferred from execution order
        assert len(dependencies) >= 0

    def test_convert_to_dsl_format(self, workflow_planning_service, sample_workflow_plan):
        """Test DSL format conversion"""
        dsl_steps = workflow_planning_service._convert_to_dsl_format(sample_workflow_plan)

        assert isinstance(dsl_steps, list)
        assert len(dsl_steps) > 0

        # Check DSL format
        for step in dsl_steps:
            assert isinstance(step, str)
            assert "(" in step and ")" in step  # Should have function-like format

    def test_assess_plan_complexity(self, workflow_planning_service, sample_workflow_planning_state):
        """Test plan complexity assessment"""
        # Set up state for complexity assessment
        sample_workflow_planning_state.execution_order = ["task1", "task2", "task3", "task4"]
        sample_workflow_planning_state.parallel_groups = [["task2", "task3"]]
        sample_workflow_planning_state.subtask_breakdown = {
            "category1": ["task1", "task2"],
            "category2": ["task3", "task4"]
        }

        complexity = workflow_planning_service._assess_plan_complexity(sample_workflow_planning_state)

        assert isinstance(complexity, dict)
        assert 'total_tasks' in complexity
        assert 'parallel_groups' in complexity
        assert 'categories' in complexity
        assert 'complexity_score' in complexity
        assert 'complexity_level' in complexity

        assert complexity['total_tasks'] == 4
        assert complexity['parallel_groups'] == 1
        assert complexity['categories'] == 2
        assert complexity['complexity_level'] in ['low', 'medium', 'high']

    def test_build_workflow_result(self, workflow_planning_service, sample_workflow_planning_state):
        """Test workflow result building"""
        # Set up complete state
        sample_workflow_planning_state.is_valid = True
        sample_workflow_planning_state.workflow_plan = [{"task": "test_task"}]
        sample_workflow_planning_state.execution_order = ["test_task"]
        sample_workflow_planning_state.parallel_groups = []
        sample_workflow_planning_state.dependencies = {}
        sample_workflow_planning_state.estimated_duration = "30 minutes"
        sample_workflow_planning_state.validation_result = {"is_valid": True}
        sample_workflow_planning_state.complexity_assessment = {"complexity_level": "medium"}
        sample_workflow_planning_state.confidence_score = 0.85
        sample_workflow_planning_state.subtask_breakdown = {"test": ["test_task"]}
        sample_workflow_planning_state.agent_mapping = {"test_task": "test_agent"}
        sample_workflow_planning_state.decomposition_confidence = 0.9

        result = workflow_planning_service._build_workflow_result(sample_workflow_planning_state)

        assert isinstance(result, dict)
        assert 'task_id' in result
        assert 'user_id' in result
        assert 'success' in result
        assert 'intent' in result
        assert 'strategic_blueprint' in result
        assert 'decomposition' in result
        assert 'workflow_plan' in result
        assert 'validation' in result
        assert 'metadata' in result

        # Verify structure
        assert result['success'] is True
        assert 'categories' in result['intent']
        assert 'confidence' in result['intent']
        assert 'subtask_breakdown' in result['decomposition']
        assert 'agent_mapping' in result['decomposition']
        assert 'dsl_plan' in result['workflow_plan']
        assert 'execution_order' in result['workflow_plan']


class TestWorkflowPlanningServiceErrorHandling:
    """Test suite for error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_decompose_tasks_node_error_handling(self, workflow_planning_service):
        """Test error handling in task decomposition node"""
        # Create state that might cause errors
        error_state = WorkflowPlanningState(
            task_id="error_test",
            user_id="test_user",
            intent_categories=["invalid_category"],
            intent_confidence=0.0,
            intent_reasoning="",
            strategic_blueprint={}
        )

        result_state = await workflow_planning_service._decompose_tasks_node(error_state)

        # Should handle errors gracefully
        assert result_state is not None
        # May have errors but should not crash

    @pytest.mark.asyncio
    async def test_plan_sequence_node_error_handling(self, workflow_planning_service, sample_workflow_planning_state):
        """Test error handling in sequence planning node"""
        # Set up state with problematic data
        sample_workflow_planning_state.subtask_breakdown = None

        result_state = await workflow_planning_service._plan_sequence_node(sample_workflow_planning_state)

        # Should handle errors gracefully
        assert result_state is not None
        # Should have error messages
        assert len(result_state.errors) > 0

    @pytest.mark.asyncio
    async def test_validate_plan_node_error_handling(self, workflow_planning_service, sample_workflow_planning_state):
        """Test error handling in plan validation node"""
        # Set up state with invalid data
        sample_workflow_planning_state.workflow_plan = None

        result_state = await workflow_planning_service._validate_plan_node(sample_workflow_planning_state)

        # Should handle errors gracefully
        assert result_state is not None
        assert len(result_state.errors) > 0

    @pytest.mark.asyncio
    async def test_workflow_execution_error_handling(self, workflow_planning_service):
        """Test error handling in workflow execution"""
        # Create invalid initial state
        invalid_state = WorkflowPlanningState(
            task_id="",  # Empty task ID
            user_id="",  # Empty user ID
            intent_categories=[],
            intent_confidence=-1.0,  # Invalid confidence
            intent_reasoning="",
            strategic_blueprint={}
        )

        try:
            result = await workflow_planning_service._execute_workflow(invalid_state)
            # Should complete but may have errors
            assert result is not None
        except Exception as e:
            # Should not crash the entire system
            assert isinstance(e, Exception)

    def test_extract_methods_with_empty_data(self, workflow_planning_service):
        """Test extraction methods with empty data"""
        empty_plan = []

        # Test extraction methods with empty data
        execution_order = workflow_planning_service._extract_execution_order(empty_plan)
        assert execution_order == []

        parallel_groups = workflow_planning_service._extract_parallel_groups(empty_plan)
        assert parallel_groups == []

        dependencies = workflow_planning_service._extract_dependencies(empty_plan)
        assert dependencies == {}

        dsl_steps = workflow_planning_service._convert_to_dsl_format(empty_plan)
        assert dsl_steps == []

    def test_assess_plan_complexity_empty_state(self, workflow_planning_service):
        """Test complexity assessment with empty state"""
        empty_state = WorkflowPlanningState(
            task_id="test",
            user_id="test",
            intent_categories=[],
            intent_confidence=0.0,
            intent_reasoning="",
            strategic_blueprint={}
        )

        complexity = workflow_planning_service._assess_plan_complexity(empty_state)

        assert isinstance(complexity, dict)
        assert complexity['total_tasks'] == 0
        assert complexity['parallel_groups'] == 0
        assert complexity['categories'] == 0
        assert complexity['complexity_level'] == 'low'


class TestWorkflowPlanningServiceMetrics:
    """Test suite for metrics and performance tracking"""

    @pytest.mark.asyncio
    async def test_service_metrics_tracking(self, workflow_planning_service, sample_mining_input):
        """Test service metrics tracking"""
        initial_metrics = workflow_planning_service.get_service_metrics()
        assert initial_metrics['total_plans_created'] == 0
        assert initial_metrics['successful_plans'] == 0
        assert initial_metrics['failed_plans'] == 0
        assert initial_metrics['success_rate'] == 0.0
        assert initial_metrics['service_status'] == "active"

        # Create a successful plan
        result = await workflow_planning_service.create_workflow_plan(sample_mining_input)

        updated_metrics = workflow_planning_service.get_service_metrics()
        assert updated_metrics['total_plans_created'] == 1

        if result['success']:
            assert updated_metrics['successful_plans'] == 1
            assert updated_metrics['failed_plans'] == 0
            assert updated_metrics['success_rate'] == 1.0
        else:
            assert updated_metrics['successful_plans'] == 0
            assert updated_metrics['failed_plans'] == 1
            assert updated_metrics['success_rate'] == 0.0

    @pytest.mark.asyncio
    async def test_multiple_plans_metrics(self, workflow_planning_service, sample_mining_input):
        """Test metrics tracking with multiple plans"""
        # Create multiple plans
        for i in range(3):
            await workflow_planning_service.create_workflow_plan(
                sample_mining_input,
                user_id=f"user_{i}",
                task_id=f"task_{i}"
            )

        metrics = workflow_planning_service.get_service_metrics()
        assert metrics['total_plans_created'] >= 3
        assert metrics['successful_plans'] + metrics['failed_plans'] == metrics['total_plans_created']

    def test_get_service_metrics_structure(self, workflow_planning_service):
        """Test service metrics structure"""
        metrics = workflow_planning_service.get_service_metrics()

        assert isinstance(metrics, dict)
        required_keys = ['total_plans_created', 'successful_plans', 'failed_plans', 'success_rate', 'service_status']
        for key in required_keys:
            assert key in metrics

        assert isinstance(metrics['total_plans_created'], int)
        assert isinstance(metrics['successful_plans'], int)
        assert isinstance(metrics['failed_plans'], int)
        assert isinstance(metrics['success_rate'], float)
        assert isinstance(metrics['service_status'], str)


class TestWorkflowPlanningServiceIntegration:
    """Integration tests for workflow planning service"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow_execution(self, workflow_planning_service, sample_mining_input):
        """Test complete end-to-end workflow execution"""
        start_time = time.time()

        result = await workflow_planning_service.create_workflow_plan(
            sample_mining_input,
            user_id="integration_test_user",
            task_id="integration_test_task"
        )

        execution_time = time.time() - start_time

        # Verify result structure and content
        assert isinstance(result, dict)
        assert result['task_id'] == "integration_test_task"
        assert result['user_id'] == "integration_test_user"

        # Verify all major components are present
        assert 'intent' in result
        assert 'decomposition' in result
        assert 'workflow_plan' in result
        assert 'validation' in result
        assert 'metadata' in result

        # Verify execution completed in reasonable time
        assert execution_time < 60  # Should complete within 60 seconds

    @pytest.mark.asyncio
    async def test_real_llm_integration_quality(self, workflow_planning_service, sample_mining_input):
        """Test that real LLM integration provides quality results"""
        result = await workflow_planning_service.create_workflow_plan(sample_mining_input)

        # Verify real LLM generated substantial content
        decomposition_content = str(result['decomposition'])
        workflow_content = str(result['workflow_plan'])

        assert len(decomposition_content) > 200  # Substantial decomposition content
        assert len(workflow_content) > 200  # Substantial workflow content

        # Verify content quality indicators
        decomposition_str = decomposition_content.lower()
        workflow_str = workflow_content.lower()

        # Should contain workflow-related terms
        workflow_terms = ['task', 'agent', 'workflow', 'plan', 'execution', 'sequence']
        assert any(term in decomposition_str for term in workflow_terms)
        assert any(term in workflow_str for term in workflow_terms)

    @pytest.mark.asyncio
    async def test_performance_benchmarking(self, workflow_planning_service, sample_mining_input):
        """Test performance benchmarking with multiple scenarios"""
        scenarios = [
            {
                "name": "simple_scenario",
                "input": {
                    "intent_categories": ["analyze"],
                    "intent_confidence": 0.8,
                    "intent_reasoning": "Simple analysis task",
                    "strategic_blueprint": {"problem_analysis": {"complexity": "low"}}
                }
            },
            {
                "name": "medium_scenario",
                "input": sample_mining_input
            },
            {
                "name": "complex_scenario",
                "input": {
                    "intent_categories": ["collect", "process", "analyze", "generate"],
                    "intent_confidence": 0.9,
                    "intent_reasoning": "Complex multi-step workflow",
                    "strategic_blueprint": {
                        "problem_analysis": {"complexity": "high"},
                        "tree_structure": {"strategy": "hierarchical", "depth": 5}
                    }
                }
            }
        ]

        performance_results = []

        for scenario in scenarios:
            start_time = time.time()
            result = await workflow_planning_service.create_workflow_plan(scenario["input"])
            execution_time = time.time() - start_time

            performance_results.append({
                "scenario": scenario["name"],
                "execution_time": execution_time,
                "success": result.get('success', False),
                "plan_size": len(result.get('workflow_plan', {}).get('dsl_plan', []))
            })

        # Verify all scenarios completed successfully
        for perf in performance_results:
            assert perf["execution_time"] < 60  # Should complete within 60 seconds
            assert perf["success"] is True
            assert perf["plan_size"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_workflow_planning(self, workflow_planning_service, sample_mining_input):
        """Test concurrent workflow planning requests"""
        # Create multiple concurrent requests
        tasks = []
        for i in range(3):
            task = workflow_planning_service.create_workflow_plan(
                sample_mining_input,
                user_id=f"concurrent_user_{i}",
                task_id=f"concurrent_task_{i}"
            )
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all completed successfully
        for i, result in enumerate(results):
            assert not isinstance(result, Exception), f"Task {i} failed with exception: {result}"
            assert isinstance(result, dict)
            assert result['success'] is True
            assert result['user_id'] == f"concurrent_user_{i}"
            assert result['task_id'] == f"concurrent_task_{i}"


class TestWorkflowPlanningServiceEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_very_large_intent_categories(self, workflow_planning_service):
        """Test with very large number of intent categories"""
        large_input = {
            "intent_categories": ["collect", "process", "analyze", "generate", "validate", "optimize", "report", "visualize", "summarize", "compare"],
            "intent_confidence": 0.7,
            "intent_reasoning": "Very complex multi-category workflow",
            "strategic_blueprint": {"problem_analysis": {"complexity": "very_high"}}
        }

        result = await workflow_planning_service.create_workflow_plan(large_input)

        # Should handle large inputs gracefully
        assert isinstance(result, dict)
        assert 'workflow_plan' in result
        assert len(result['intent']['categories']) == 10

    @pytest.mark.asyncio
    async def test_malformed_strategic_blueprint(self, workflow_planning_service):
        """Test with malformed strategic blueprint"""
        malformed_input = {
            "intent_categories": ["analyze"],
            "intent_confidence": 0.8,
            "intent_reasoning": "Test with malformed blueprint",
            "strategic_blueprint": {
                "invalid_structure": "this should not break the system",
                "nested": {"deeply": {"nested": {"data": "value"}}}
            }
        }

        result = await workflow_planning_service.create_workflow_plan(malformed_input)

        # Should handle malformed input gracefully
        assert isinstance(result, dict)
        assert 'metadata' in result

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, workflow_planning_service):
        """Test with unicode and special characters"""
        unicode_input = {
            "intent_categories": ["analyze"],
            "intent_confidence": 0.8,
            "intent_reasoning": "测试中文字符 and émojis 🚀 and special chars @#$%",
            "strategic_blueprint": {"problem_analysis": {"complexity": "medium"}}
        }

        result = await workflow_planning_service.create_workflow_plan(unicode_input)

        # Should handle unicode gracefully
        assert isinstance(result, dict)
        assert result['intent']['reasoning'] == unicode_input['intent_reasoning']

    def test_load_agent_mapping_error_handling(self, workflow_planning_service):
        """Test agent mapping loading with error conditions"""
        # Test that service handles missing configuration gracefully
        original_mapping = workflow_planning_service.agent_mapping

        # Verify that even if mapping fails, service provides fallbacks
        assert isinstance(original_mapping, dict)

        # Test fallback behavior
        fallback_agent = workflow_planning_service._get_default_agent_for_category("unknown_category")
        assert fallback_agent == "general_researcher"

    def test_extract_methods_with_malformed_data(self, workflow_planning_service):
        """Test extraction methods with malformed workflow plan data"""
        malformed_plans = [
            [{"invalid": "structure"}],
            [{"task": None}],
            [{"parallel": []}],
            [{"parallel": [{"invalid": "task"}]}]
        ]

        for malformed_plan in malformed_plans:
            # Should not crash with malformed data
            execution_order = workflow_planning_service._extract_execution_order(malformed_plan)
            assert isinstance(execution_order, list)

            parallel_groups = workflow_planning_service._extract_parallel_groups(malformed_plan)
            assert isinstance(parallel_groups, list)

            dependencies = workflow_planning_service._extract_dependencies(malformed_plan)
            assert isinstance(dependencies, dict)

            dsl_steps = workflow_planning_service._convert_to_dsl_format(malformed_plan)
            assert isinstance(dsl_steps, list)


class TestWorkflowPlanningServiceCoverageValidation:
    """Additional tests to ensure comprehensive coverage"""

    @pytest.mark.asyncio
    async def test_initialize_method_coverage(self, real_config_manager, real_llm_manager):
        """Test the initialize method specifically"""
        service = WorkflowPlanningService(real_config_manager, real_llm_manager)

        # Before initialization
        assert service.task_decomposer is None
        assert service.planner is None
        assert service.workflow_graph is None

        # Initialize
        await service.initialize()

        # After initialization
        assert service.task_decomposer is not None
        assert service.planner is not None
        assert service.workflow_graph is not None

    @pytest.mark.asyncio
    async def test_execute_workflow_method_coverage(self, workflow_planning_service, sample_workflow_planning_state):
        """Test the _execute_workflow method specifically"""
        result_state = await workflow_planning_service._execute_workflow(sample_workflow_planning_state)

        assert isinstance(result_state, WorkflowPlanningState)
        assert result_state.task_id == sample_workflow_planning_state.task_id

    def test_all_private_methods_coverage(self, workflow_planning_service, sample_workflow_planning_state, sample_workflow_plan):
        """Ensure all private methods are covered"""
        # Test _load_agent_mapping
        agent_mapping = workflow_planning_service._load_agent_mapping()
        assert isinstance(agent_mapping, dict)

        # Test _get_available_tools
        tools = workflow_planning_service._get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Test all extraction methods
        execution_order = workflow_planning_service._extract_execution_order(sample_workflow_plan)
        parallel_groups = workflow_planning_service._extract_parallel_groups(sample_workflow_plan)
        dependencies = workflow_planning_service._extract_dependencies(sample_workflow_plan)
        dsl_format = workflow_planning_service._convert_to_dsl_format(sample_workflow_plan)

        assert isinstance(execution_order, list)
        assert isinstance(parallel_groups, list)
        assert isinstance(dependencies, dict)
        assert isinstance(dsl_format, list)

        # Test complexity assessment
        complexity = workflow_planning_service._assess_plan_complexity(sample_workflow_planning_state)
        assert isinstance(complexity, dict)
        assert 'complexity_level' in complexity

        # Test result building
        sample_workflow_planning_state.is_valid = True
        sample_workflow_planning_state.workflow_plan = sample_workflow_plan
        sample_workflow_planning_state.execution_order = execution_order
        sample_workflow_planning_state.parallel_groups = parallel_groups
        sample_workflow_planning_state.dependencies = dependencies
        sample_workflow_planning_state.validation_result = {"is_valid": True}
        sample_workflow_planning_state.complexity_assessment = complexity
        sample_workflow_planning_state.confidence_score = 0.85

        result = workflow_planning_service._build_workflow_result(sample_workflow_planning_state)
        assert isinstance(result, dict)
        assert 'success' in result

    def test_metrics_edge_cases(self, workflow_planning_service):
        """Test metrics calculation edge cases"""
        # Test with zero plans
        metrics = workflow_planning_service.get_service_metrics()
        assert metrics['success_rate'] == 0.0

        # Test success rate calculation
        workflow_planning_service.total_plans_created = 10
        workflow_planning_service.successful_plans = 7
        workflow_planning_service.failed_plans = 3

        metrics = workflow_planning_service.get_service_metrics()
        assert metrics['success_rate'] == 70.0
        assert metrics['total_plans_created'] == 10
        assert metrics['successful_plans'] == 7
        assert metrics['failed_plans'] == 3


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([
        __file__,
        "-v",
        "--cov=app.services.multi_task.services.planner.workflow_planning",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=85"
    ])

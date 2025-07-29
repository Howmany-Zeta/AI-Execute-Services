"""
Workflow Planning Service

A self-contained service that integrates task_decomposer and planner using LangGraph
to replace workflow_planner. This service receives input from mining.py and provides
comprehensive workflow planning capabilities with enhanced task decomposition and agent mapping.

Key Features:
- LangGraph-based integration of task_decomposer and planner agents
- Accepts pre-processed input from mining.py (intent categories and strategic blueprint)
- Enhanced task decomposition with agent mapping
- DSL validation using plan_validator
- Comprehensive workflow plan generation
- Agent coordination and business logic
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import asdict

# LangGraph dependencies
from langgraph.graph import StateGraph, END

# Import system components
from ...agent.system.task_decomposer import TaskDecomposerAgent
from ...agent.system.planner import PlannerAgent
from .validation.plan_validator import PlanValidatorService
from ...core.models.agent_models import AgentConfig, AgentRole
from ...core.models.services_models import WorkflowPlanningState
from ...core.exceptions.services_exceptions import WorkflowPlanningError
from ...config.config_manager import ConfigManager
from app.services.llm_integration import LLMIntegrationManager

logger = logging.getLogger(__name__)


class WorkflowPlanningService:
    """
    Self-contained workflow planning service using LangGraph integration.

    This service replaces workflow_planner by providing enhanced capabilities:
    - Accepts pre-processed input from mining.py (intent categories and strategic blueprint)
    - Integrated task decomposition with agent mapping
    - LangGraph-based workflow orchestration
    - Comprehensive DSL validation
    - Enhanced business logic for agent coordination
    """

    def __init__(self, config_manager: ConfigManager, llm_manager: LLMIntegrationManager):
        """
        Initialize the workflow planning service.

        Args:
            config_manager: Configuration manager for accessing tasks.yaml and prompts.yaml
            llm_manager: LLM integration manager for agent communication
        """
        self.config_manager = config_manager
        self.llm_manager = llm_manager

        # Initialize agents (only task_decomposer and planner needed)
        self.task_decomposer = None
        self.planner = None

        # Initialize validator
        self.plan_validator = PlanValidatorService()

        # LangGraph workflow
        self.workflow_graph = None

        # Agent mapping from tasks.yaml
        self.agent_mapping = self._load_agent_mapping()

        # Performance metrics
        self.total_plans_created = 0
        self.successful_plans = 0
        self.failed_plans = 0

        logger.info("WorkflowPlanningService initialized")

    async def initialize(self) -> None:
        """Initialize the service and all agents."""
        try:
            logger.info("Initializing WorkflowPlanningService...")

            # Initialize agents
            await self._initialize_agents()

            # Build LangGraph workflow
            self._build_workflow_graph()

            logger.info("WorkflowPlanningService initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize WorkflowPlanningService: {e}")
            raise

    async def create_workflow_plan(
        self,
        mining_input: Dict[str, Any],
        user_id: str = "anonymous",
        task_id: str = None
    ) -> Dict[str, Any]:
        """
        Create a comprehensive workflow plan from mining.py input.

        Args:
            mining_input: Pre-processed input from mining.py containing:
                - intent_categories: List of identified intent categories
                - intent_confidence: Confidence score for intent parsing
                - intent_reasoning: Reasoning for intent identification
                - strategic_blueprint: Strategic blueprint from meta_architect (optional)
            user_id: User identifier
            task_id: Optional task identifier

        Returns:
            Complete workflow plan with DSL, agent mapping, and validation results
        """
        if task_id is None:
            task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Initialize state with mining input
        initial_state = WorkflowPlanningState(
            task_id=task_id,
            user_id=user_id,
            intent_categories=mining_input.get("intent_categories", []),
            intent_confidence=mining_input.get("intent_confidence", 0.0),
            intent_reasoning=mining_input.get("intent_reasoning", ""),
            strategic_blueprint=mining_input.get("strategic_blueprint", {})
        )

        try:
            logger.info(f"Creating workflow plan for task {task_id}")

            # Execute LangGraph workflow
            final_state = await self._execute_workflow(initial_state)

            # Build comprehensive result
            result = self._build_workflow_result(final_state)

            # Update metrics
            if final_state.is_valid:
                self.successful_plans += 1
            else:
                self.failed_plans += 1
            self.total_plans_created += 1

            logger.info(f"Workflow plan created successfully for task {task_id}")
            return result

        except Exception as e:
            self.failed_plans += 1
            self.total_plans_created += 1
            logger.error(f"Failed to create workflow plan for task {task_id}: {e}")
            raise

    async def _initialize_agents(self) -> None:
        """Initialize required agents (task_decomposer and planner only)."""
        try:
            # Create agent configurations
            decomposer_config = AgentConfig(
                name="Task Decomposer",
                role=AgentRole.TASK_DECOMPOSER,
                goal="Decompose complex tasks into manageable subtasks",
                backstory="An expert agent specialized in breaking down complex workflows into structured, executable subtasks with proper sequencing and dependencies.",
                metadata={"enhanced_output": True}
            )

            planner_config = AgentConfig(
                name="Workflow Planner",
                role=AgentRole.PLANNER,
                goal="Create detailed execution plans for multi-task workflows",
                backstory="A strategic planning agent that creates comprehensive execution plans, resource allocation, and timeline management for complex multi-task workflows.",
                metadata={"dsl_enabled": True}
            )

            # Initialize agents
            self.task_decomposer = TaskDecomposerAgent(
                decomposer_config, self.config_manager, self.llm_manager
            )

            self.planner = PlannerAgent(
                planner_config, self.config_manager, self.llm_manager
            )

            # Initialize agents
            await self.task_decomposer.initialize()
            await self.planner.initialize()

            logger.info("Required agents initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            raise

    def _build_workflow_graph(self) -> None:
        """Build the LangGraph workflow for planning (without intent parsing)."""
        try:
            # Create state graph
            workflow = StateGraph(WorkflowPlanningState)

            # Add nodes (intent parsing removed as it's handled by mining.py)
            workflow.add_node("decompose_tasks", self._decompose_tasks_node)
            workflow.add_node("plan_sequence", self._plan_sequence_node)
            workflow.add_node("validate_plan", self._validate_plan_node)
            workflow.add_node("finalize_plan", self._finalize_plan_node)

            # Add edges (start directly with task decomposition)
            workflow.set_entry_point("decompose_tasks")
            workflow.add_edge("decompose_tasks", "plan_sequence")
            workflow.add_edge("plan_sequence", "validate_plan")
            workflow.add_edge("validate_plan", "finalize_plan")
            workflow.add_edge("finalize_plan", END)

            # Compile workflow
            self.workflow_graph = workflow.compile()

            logger.info("LangGraph workflow built successfully")

        except Exception as e:
            logger.error(f"Failed to build workflow graph: {e}")
            raise

    async def _execute_workflow(self, initial_state: WorkflowPlanningState) -> WorkflowPlanningState:
        """Execute the LangGraph workflow."""
        try:
            # Execute workflow
            result = await self.workflow_graph.ainvoke(initial_state)
            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise

    async def _decompose_tasks_node(self, state: WorkflowPlanningState) -> WorkflowPlanningState:
        """Decompose intent categories into executable sub-tasks with agent mapping."""
        try:
            logger.debug("Executing task decomposition node")

            if not state.intent_categories:
                state.errors.append("No intent categories available for decomposition")
                return state

            # Prepare task data for decomposer
            task_data = {
                "categories": state.intent_categories
            }

            context = {
                "task_id": state.task_id,
                "user_id": state.user_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Execute task decomposition
            result = await self.task_decomposer.execute_task(task_data, context)

            # Update state with enhanced output
            state.subtask_breakdown = result.get("breakdown", {})
            state.decomposition_confidence = result.get("confidence", 0.0)

            # Get agent mapping from the decomposer result
            state.agent_mapping = result.get("agent_mapping", {})

            # If agent mapping is not provided, generate it
            if not state.agent_mapping:
                state.agent_mapping = self._generate_agent_mapping(state.subtask_breakdown)

            logger.debug(f"Task decomposition completed: {state.subtask_breakdown}")
            logger.debug(f"Agent mapping: {state.agent_mapping}")
            return state

        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            state.errors.append(f"Task decomposition failed: {e}")
            return state

    async def _plan_sequence_node(self, state: WorkflowPlanningState) -> WorkflowPlanningState:
        """Plan execution sequence using DSL constructs."""
        try:
            logger.debug("Executing sequence planning node")

            if not state.subtask_breakdown:
                state.errors.append("No subtask breakdown available for planning")
                return state

            # Prepare task data for planner
            task_data = {
                "subtask_breakdown": state.subtask_breakdown,
                "available_tools": self._get_available_tools(),
                "agent_mapping": state.agent_mapping
            }

            context = {
                "task_id": state.task_id,
                "user_id": state.user_id,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Execute sequence planning
            result = await self.planner.execute_task(task_data, context)

            # Update state
            state.workflow_plan = result.get("sequence", [])
            state.estimated_duration = result.get("estimated_duration", "Unknown")

            # Extract execution metadata
            state.execution_order = self._extract_execution_order(state.workflow_plan)
            state.parallel_groups = self._extract_parallel_groups(state.workflow_plan)
            state.dependencies = self._extract_dependencies(state.workflow_plan)

            logger.debug(f"Sequence planning completed: {len(state.workflow_plan)} steps")
            return state

        except Exception as e:
            logger.error(f"Sequence planning failed: {e}")
            state.errors.append(f"Sequence planning failed: {e}")
            return state

    async def _validate_plan_node(self, state: WorkflowPlanningState) -> WorkflowPlanningState:
        """Validate the generated workflow plan using plan_validator."""
        try:
            logger.debug("Executing plan validation node")

            if not state.workflow_plan:
                state.errors.append("No workflow plan available for validation")
                return state

            # Prepare plan data for validation
            plan_data = {
                "dsl_plan": self._convert_to_dsl_format(state.workflow_plan),
                "execution_order": state.execution_order,
                "parallel_groups": state.parallel_groups,
                "dependencies": state.dependencies,
                "agent_mapping": state.agent_mapping,
                "subtask_breakdown": state.subtask_breakdown
            }

            # Execute validation
            validation_result = await self.plan_validator.validate_workflow_plan(plan_data)

            # Update state
            state.validation_result = asdict(validation_result)
            state.is_valid = validation_result.is_valid

            # Add validation issues to warnings/errors
            for issue in validation_result.validation_issues:
                if issue.get("severity") == "CRITICAL":
                    state.errors.append(issue.get("message", "Critical validation error"))
                else:
                    state.warnings.append(issue.get("message", "Validation warning"))

            logger.debug(f"Plan validation completed: valid={state.is_valid}")
            return state

        except Exception as e:
            logger.error(f"Plan validation failed: {e}")
            state.errors.append(f"Plan validation failed: {e}")
            return state

    async def _finalize_plan_node(self, state: WorkflowPlanningState) -> WorkflowPlanningState:
        """Finalize the workflow plan with metadata and confidence scoring."""
        try:
            logger.debug("Executing plan finalization node")

            # Calculate overall confidence score
            confidence_scores = [
                state.intent_confidence,
                state.decomposition_confidence,
                state.validation_result.get("overall_score", 0.0) if state.validation_result else 0.0
            ]

            state.confidence_score = sum(confidence_scores) / len(confidence_scores)

            # Generate complexity assessment
            state.complexity_assessment = self._assess_plan_complexity(state)

            logger.debug("Plan finalization completed")
            return state

        except Exception as e:
            logger.error(f"Plan finalization failed: {e}")
            state.errors.append(f"Plan finalization failed: {e}")
            return state

    def _generate_agent_mapping(self, subtask_breakdown: Dict[str, List[str]]) -> Dict[str, str]:
        """Generate mapping of subtasks to their corresponding agents."""
        agent_mapping = {}

        for category, subtasks in subtask_breakdown.items():
            for subtask in subtasks:
                # Get agent from tasks.yaml configuration
                agent = self.agent_mapping.get(subtask)
                if agent:
                    agent_mapping[subtask] = agent
                else:
                    # Fallback to category-based mapping
                    agent_mapping[subtask] = self._get_default_agent_for_category(category)

        return agent_mapping

    def _get_default_agent_for_category(self, category: str) -> str:
        """Get default agent for a category."""
        default_agents = {
            "answer": "researcher_knowledgeprovider",
            "collect": "fieldwork_webscraper",
            "process": "fieldwork_dataoperator",
            "analyze": "fieldwork_statistician",
            "generate": "writer_reportspecialist"
        }
        return default_agents.get(category, "general_researcher")

    def _load_agent_mapping(self) -> Dict[str, str]:
        """Load agent mapping from tasks.yaml configuration."""
        try:
            # This would load from tasks.yaml via config_manager
            # For now, return a comprehensive mapping based on the tasks.yaml structure
            return {
                # Answer tasks
                "answer_discuss": "researcher_discussionfacilitator",
                "answer_conclusion": "writer_conclusionspecialist",
                "answer_questions": "researcher_knowledgeprovider",
                "answer_brainstorming": "researcher_ideagenerator",

                # Collect tasks
                "collect_scrape": "fieldwork_webscraper",
                "collect_search": "fieldwork_apisearcher",
                "collect_internalResources": "fieldwork_internaldatacollector",
                "collect_externalResources": "fieldwork_externaldatacollector",

                # Process tasks
                "process_dataCleaning": "fieldwork_dataoperator",
                "process_dataNormalization": "fieldwork_dataengineer",
                "process_dataStatistics": "fieldwork_statistician",
                "process_dataModeling": "fieldwork_datascientist",
                "process_dataIntegration": "fieldwork_dataengineer",
                "process_dataCompression": "fieldwork_dataengineer",
                "process_dataEnrichment": "fieldwork_dataengineer",
                "process_dataTransformation": "fieldwork_dataengineer",
                "process_dataFiltering": "fieldwork_dataoperator",
                "process_dataFormatting": "fieldwork_dataoperator",

                # Analyze tasks
                "analyze_dataoutcome": "fieldwork_statistician",
                "analyze_trends": "analyst_trendanalyst",
                "analyze_patterns": "analyst_patternrecognition",
                "analyze_correlations": "analyst_correlationspecialist",
                "analyze_predictions": "analyst_predictivemodeling",
                "analyze_comparisons": "analyst_comparativeanalyst",
                "analyze_insights": "analyst_insightgenerator",

                # Generate tasks
                "generate_report": "writer_reportspecialist",
                "generate_summary": "writer_summaryspecialist",
                "generate_visualization": "writer_visualizationspecialist",
                "generate_presentation": "writer_presentationspecialist",
                "generate_documentation": "writer_documentationspecialist",
                "generate_recommendations": "writer_recommendationspecialist"
            }

        except Exception as e:
            logger.warning(f"Failed to load agent mapping from configuration: {e}")
            return {}

    def _get_available_tools(self) -> List[str]:
        """Get list of available tools from configuration."""
        return [
            "scraper", "search_api", "office", "pandas", "stats",
            "research", "classifier", "chart", "image", "report"
        ]

    def _extract_execution_order(self, workflow_plan: List[Dict[str, Any]]) -> List[str]:
        """Extract execution order from workflow plan."""
        execution_order = []

        for step in workflow_plan:
            if "task" in step:
                execution_order.append(step["task"])
            elif "parallel" in step:
                for parallel_task in step["parallel"]:
                    if "task" in parallel_task:
                        execution_order.append(parallel_task["task"])

        return execution_order

    def _extract_parallel_groups(self, workflow_plan: List[Dict[str, Any]]) -> List[List[str]]:
        """Extract parallel execution groups from workflow plan."""
        parallel_groups = []

        for step in workflow_plan:
            if "parallel" in step:
                group = []
                for parallel_task in step["parallel"]:
                    if "task" in parallel_task:
                        group.append(parallel_task["task"])
                if group:
                    parallel_groups.append(group)

        return parallel_groups

    def _extract_dependencies(self, workflow_plan: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract task dependencies from workflow plan."""
        dependencies = {}
        previous_tasks = []

        for step in workflow_plan:
            current_tasks = []

            if "task" in step:
                task_name = step["task"]
                current_tasks.append(task_name)
                if previous_tasks:
                    dependencies[task_name] = previous_tasks.copy()

            elif "parallel" in step:
                for parallel_task in step["parallel"]:
                    if "task" in parallel_task:
                        task_name = parallel_task["task"]
                        current_tasks.append(task_name)
                        if previous_tasks:
                            dependencies[task_name] = previous_tasks.copy()

            previous_tasks = current_tasks

        return dependencies

    def _convert_to_dsl_format(self, workflow_plan: List[Dict[str, Any]]) -> List[str]:
        """Convert workflow plan to DSL format for validation."""
        dsl_steps = []

        for step in workflow_plan:
            if "task" in step:
                task_name = step["task"]
                tools = step.get("tools", [])
                dsl_step = f"{task_name}({', '.join(tools)})"
                dsl_steps.append(dsl_step)

            elif "parallel" in step:
                parallel_tasks = []
                for parallel_task in step["parallel"]:
                    if "task" in parallel_task:
                        task_name = parallel_task["task"]
                        tools = parallel_task.get("tools", [])
                        parallel_tasks.append(f"{task_name}({', '.join(tools)})")

                if parallel_tasks:
                    dsl_step = f"parallel({', '.join(parallel_tasks)})"
                    dsl_steps.append(dsl_step)

        return dsl_steps

    def _assess_plan_complexity(self, state: WorkflowPlanningState) -> Dict[str, Any]:
        """Assess the complexity of the workflow plan."""
        total_tasks = len(state.execution_order) if state.execution_order else 0
        parallel_groups = len(state.parallel_groups) if state.parallel_groups else 0
        categories = len(state.subtask_breakdown) if state.subtask_breakdown else 0

        complexity_score = (total_tasks * 0.4) + (parallel_groups * 0.3) + (categories * 0.3)

        if complexity_score <= 3:
            complexity_level = "low"
        elif complexity_score <= 7:
            complexity_level = "medium"
        else:
            complexity_level = "high"

        return {
            "total_tasks": total_tasks,
            "parallel_groups": parallel_groups,
            "categories": categories,
            "complexity_score": complexity_score,
            "complexity_level": complexity_level
        }

    def _build_workflow_result(self, state: WorkflowPlanningState) -> Dict[str, Any]:
        """Build the final workflow planning result."""
        return {
            "task_id": state.task_id,
            "user_id": state.user_id,
            "success": state.is_valid and len(state.errors) == 0,

            # Intent parsing results (from mining.py)
            "intent": {
                "categories": state.intent_categories,
                "confidence": state.intent_confidence,
                "reasoning": state.intent_reasoning
            },

            # Strategic blueprint (from mining.py)
            "strategic_blueprint": state.strategic_blueprint,

            # Task decomposition results
            "decomposition": {
                "subtask_breakdown": state.subtask_breakdown,
                "agent_mapping": state.agent_mapping,
                "confidence": state.decomposition_confidence
            },

            # Workflow plan
            "workflow_plan": {
                "dsl_plan": state.workflow_plan,
                "execution_order": state.execution_order,
                "parallel_groups": state.parallel_groups,
                "dependencies": state.dependencies,
                "estimated_duration": state.estimated_duration
            },

            # Validation results
            "validation": state.validation_result,

            # Metadata
            "metadata": {
                "complexity_assessment": state.complexity_assessment,
                "confidence_score": state.confidence_score,
                "created_at": datetime.utcnow().isoformat(),
                "errors": state.errors,
                "warnings": state.warnings
            }
        }

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        success_rate = (self.successful_plans / max(self.total_plans_created, 1)) * 100

        return {
            "total_plans_created": self.total_plans_created,
            "successful_plans": self.successful_plans,
            "failed_plans": self.failed_plans,
            "success_rate": success_rate,
            "service_status": "active"
        }

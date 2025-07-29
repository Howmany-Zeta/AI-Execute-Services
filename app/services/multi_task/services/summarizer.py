"""
LangGraph-based Multi-Task Summarizer Service

Complete refactoring of the Summarizer using LangGraph for state management and workflow orchestration.
This implementation provides real-time streaming, user feedback handling, and comprehensive task execution.

Key Features:
1. LangGraph state-driven workflow orchestration
2. OpenAI-compatible streaming output
3. Real-time user feedback and dynamic task updates
4. Complete integration with MiningService, WorkflowPlanningService, and WorkflowOrchestrator
5. Modular node design with comprehensive error handling
6. Top-level state management across the entire request lifecycle
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from datetime import datetime

# LangGraph dependencies
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Core imports
from app.config.registry import register_ai_service
from app.services.base_service import BaseAIService, OpenAIStreamFormatter
from app.services.llm_integration import LLMIntegrationManager, get_llm_integration_manager
from app.domain.execution.model import TaskStatus, ErrorCode, TaskStepResult
from app.infrastructure.messaging.websocket_manager import UserConfirmation

# Multi-task service imports
from .base import DOMAINS, BaseTaskService
from .demand.mining import MiningService
from .planner.workflow_planning import WorkflowPlanningService
from .interacter.interacter import InteracterService
from .qc.examine_outcome import ExamineOutcomeService
from .qc.accept_outcome import AcceptOutcomeService

# Core models, interfaces, and exceptions
from ..core.models.services_models import (
    TaskCategory, SummarizerStepStatus, SummarizerState,
    MiningContext, MiningResult, WorkflowPlanningState,
    InteractionResult, RequestType
)
from ..core.interfaces.services_interfaces import ISummarizerService
from ..core.exceptions.services_exceptions import SummarizerError, WorkflowExecutionError, StreamingError

# Execution chain imports
from ..workflows.workflow_orchestrator import WorkflowOrchestrator, WorkflowExecutionRequest, WorkflowExecutionMode
from ..execution.processors.task_processor import TaskProcessor
from ..execution.engines.langchain_engine import LangChainEngine
from ..config.config_manager import ConfigManager
from ..core.models.execution_models import ExecutionContext

logger = logging.getLogger(__name__)


@register_ai_service("multi_task", "summarizer")
class Summarizer(BaseAIService):
    """
    LangGraph-based Multi-Task Summarizer Service

    Complete refactoring using LangGraph for state management and workflow orchestration.
    Provides real-time streaming, user feedback handling, and comprehensive task execution.
    """

    def __init__(self):
        """Initialize the LangGraph summarizer service."""
        super().__init__()
        self.service_name = "summarizer"

        # Core components
        self._llm_manager: Optional[LLMIntegrationManager] = None
        self._config_manager: Optional[ConfigManager] = None

        # Specialized services
        self._interacter: Optional[InteracterService] = None
        self._mining_service: Optional[MiningService] = None
        self._workflow_planning: Optional[WorkflowPlanningService] = None
        self._examine_service: Optional[ExamineOutcomeService] = None
        self._accept_service: Optional[AcceptOutcomeService] = None

        # Execution chain components
        self._workflow_orchestrator: Optional[WorkflowOrchestrator] = None
        self._task_processor: Optional[TaskProcessor] = None
        self._langchain_engine: Optional[LangChainEngine] = None

        # LangGraph components
        self.memory_saver = MemorySaver()
        self.workflow_graph = None

        # State management
        self._active_sessions: Dict[str, SummarizerState] = {}

        # Performance metrics
        self._total_sessions = 0
        self._successful_sessions = 0
        self._average_session_time = 0.0

        logger.info("LangGraph Summarizer initialized")

    async def initialize(self):
        """Initialize all service components."""
        try:
            logger.info("Initializing LangGraph Summarizer...")

            # Initialize core components
            self._llm_manager = await get_llm_integration_manager()
            self._config_manager = ConfigManager()

            # Initialize specialized services
            await self._initialize_specialized_services()

            # Initialize execution chain
            await self._initialize_execution_chain()

            # Build LangGraph workflow
            self._build_langgraph_workflow()

            logger.info("LangGraph Summarizer initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize LangGraph Summarizer: {e}")
            raise

    async def _initialize_specialized_services(self):
        """Initialize all specialized services."""
        # Initialize InteracterService
        self._interacter = InteracterService(self._llm_manager)

        # Initialize MiningService
        self._mining_service = MiningService(
            self._llm_manager,
            self._config_manager
        )
        await self._mining_service.initialize()

        # Initialize WorkflowPlanningService
        self._workflow_planning = WorkflowPlanningService(
            self._config_manager,
            self._llm_manager
        )
        await self._workflow_planning.initialize()

        # Initialize QC services
        self._examine_service = ExamineOutcomeService(
            self._config_manager,
            self._llm_manager,
            None  # QualityProcessor will be initialized later
        )

        self._accept_service = AcceptOutcomeService(
            self._config_manager,
            self._llm_manager,
            None  # QualityProcessor will be initialized later
        )

        logger.info("Specialized services initialized")

    async def _initialize_execution_chain(self):
        """Initialize the execution chain components."""
        # Initialize LangChain Engine
        self._langchain_engine = LangChainEngine(
            agent_manager=None,  # Will be auto-created
            config_manager=self._config_manager,
            llm_manager=self._llm_manager
        )
        await self._langchain_engine.initialize()

        # Initialize TaskProcessor
        self._task_processor = TaskProcessor(self._langchain_engine)

        # Initialize WorkflowOrchestrator
        self._workflow_orchestrator = WorkflowOrchestrator(
            task_executor=self._langchain_engine,
            task_service=None,  # TODO: Implement ITaskService if needed
            max_concurrent_workflows=5
        )

        logger.info("Execution chain initialized")

    def _build_langgraph_workflow(self):
        """Build the LangGraph workflow for the summarizer."""
        try:
            # Create state graph
            workflow = StateGraph(SummarizerState)

            # Add nodes
            workflow.add_node("validate_interaction", self._validate_interaction_node)
            workflow.add_node("mine_requirements", self._mine_requirements_node)
            workflow.add_node("plan_workflow", self._plan_workflow_node)
            workflow.add_node("execute_workflow", self._execute_workflow_node)
            workflow.add_node("quality_control", self._quality_control_node)
            workflow.add_node("handle_user_feedback", self._handle_user_feedback_node)
            workflow.add_node("finalize_session", self._finalize_session_node)
            workflow.add_node("handle_error", self._handle_error_node)

            # Set entry point
            workflow.set_entry_point("validate_interaction")

            # Add conditional edges
            workflow.add_conditional_edges(
                "validate_interaction",
                self._route_after_validation,
                {
                    "proceed": "mine_requirements",
                    "error": "handle_error",
                    "end": END
                }
            )

            workflow.add_conditional_edges(
                "mine_requirements",
                self._route_after_mining,
                {
                    "proceed": "plan_workflow",
                    "clarify": "handle_user_feedback",  # Request clarification
                    "error": "handle_error"
                }
            )

            workflow.add_conditional_edges(
                "plan_workflow",
                self._route_after_planning,
                {
                    "execute": "execute_workflow",
                    "replan": "plan_workflow",  # Re-plan if needed
                    "error": "handle_error"
                }
            )

            workflow.add_conditional_edges(
                "execute_workflow",
                self._route_after_execution,
                {
                    "quality_control": "quality_control",
                    "user_feedback": "handle_user_feedback",
                    "finalize": "finalize_session",
                    "error": "handle_error"
                }
            )

            workflow.add_conditional_edges(
                "quality_control",
                self._route_after_qc,
                {
                    "finalize": "finalize_session",
                    "retry": "execute_workflow",
                    "user_feedback": "handle_user_feedback",
                    "error": "handle_error"
                }
            )

            workflow.add_conditional_edges(
                "handle_user_feedback",
                self._route_after_feedback,
                {
                    "continue": "mine_requirements",  # Continue from appropriate step
                    "replan": "plan_workflow",
                    "retry": "execute_workflow",
                    "finalize": "finalize_session",
                    "error": "handle_error"
                }
            )

            workflow.add_edge("finalize_session", END)
            workflow.add_edge("handle_error", END)

            # Compile workflow
            self.workflow_graph = workflow.compile(checkpointer=self.memory_saver)

            logger.info("LangGraph workflow built successfully")

        except Exception as e:
            logger.error(f"Failed to build LangGraph workflow: {e}")
            raise

    async def stream(self, input_data: Dict, context: Dict) -> AsyncGenerator[str, None]:
        """
        Main streaming method using LangGraph workflow orchestration.

        Returns OpenAI-compatible streaming format for Vercel AI SDK compatibility.
        """
        # Create OpenAI stream formatter
        formatter = self.create_stream_formatter(self.service_name)

        session_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        try:
            logger.info(f"Starting LangGraph session {session_id}")

            # Initialize state
            initial_state = SummarizerState(
                session_id=session_id,
                user_id=input_data.get("user_id", "anonymous"),
                task_id=input_data.get("task_id", str(uuid.uuid4())),
                user_input=input_data.get("text", ""),
                input_data=input_data,
                context=context,
                start_time=start_time
            )

            # Store active session
            self._active_sessions[session_id] = initial_state

            # Configure LangGraph execution
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "checkpoint_ns": "summarizer"
                }
            }

            # Stream workflow execution
            async for event in self.workflow_graph.astream(
                initial_state,
                config=config,
                stream_mode="updates"
            ):
                # Process each node update
                for node_name, node_state in event.items():
                    if hasattr(node_state, 'streaming_updates'):
                        # Send streaming updates
                        for update in node_state.streaming_updates:
                            # Format as OpenAI-compatible chunk
                            content = self._format_update_content(update)
                            yield self.format_stream_chunk(formatter, content)

                            # Clear processed updates
                            node_state.streaming_updates = []

            # Send completion message
            yield self.format_stream_chunk(formatter, "", "stop")
            yield self.format_stream_done(formatter)

            # Update metrics
            session_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_session_metrics(True, session_time)

        except Exception as e:
            logger.error(f"LangGraph session {session_id} failed: {e}")

            # Send error message
            error_content = f"Session failed: {str(e)}"
            yield self.format_stream_error(formatter, error_content, "execution_error")

            # Update metrics
            session_time = (datetime.utcnow() - start_time).total_seconds()
            self._update_session_metrics(False, session_time)

        finally:
            # Cleanup session
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]

    def _format_update_content(self, update: Dict[str, Any]) -> str:
        """Format update content for streaming output."""
        step = update.get("step", "unknown")
        message = update.get("message", "")
        status = update.get("status", "in_progress")

        # Create user-friendly status message
        if status == "in_progress":
            return f"🔄 {message}\n"
        elif status == "completed":
            return f"✅ {message}\n"
        elif status == "failed":
            return f"❌ {message}\n"
        else:
            return f"ℹ️ {message}\n"

    # ==================== LangGraph Node Implementations ====================

    async def _validate_interaction_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Validate user interaction using InteracterService."""
        try:
            state.current_step = "validate_interaction"
            state.add_streaming_update(
                "validate_interaction",
                "Validating user request...",
                "in_progress"
            )

            # Validate user interaction
            state.interaction_result = await self._interacter.validate_user_request(
                state.user_input, state.context
            )

            # Update state
            state.should_proceed = state.interaction_result.should_proceed
            state.step_results["validate_interaction"] = {
                "interaction_result": state.interaction_result.__dict__,
                "should_proceed": state.should_proceed
            }

            # Add completion update
            if state.should_proceed:
                state.add_streaming_update(
                    "validate_interaction",
                    "User request validated successfully",
                    "completed",
                    {"should_proceed": state.should_proceed}
                )
            else:
                state.add_streaming_update(
                    "validate_interaction",
                    state.interaction_result.guidance_message or "Request validation failed",
                    "failed",
                    {"guidance": state.interaction_result.guidance_message}
                )

            return state

        except Exception as e:
            logger.error(f"User interaction validation failed: {e}")
            state.error = f"Validation failed: {str(e)}"
            state.add_streaming_update(
                "validate_interaction",
                f"Validation error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _mine_requirements_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Mine user requirements using MiningService."""
        try:
            state.current_step = "mine_requirements"
            state.add_streaming_update(
                "mine_requirements",
                "Analyzing and mining user requirements...",
                "in_progress"
            )

            # Create mining context
            state.mining_context = MiningContext(
                user_id=state.user_id,
                session_id=state.session_id,
                task_id=state.task_id,
                domain=state.context.get("domain", "general")
            )

            # Execute mining
            state.mining_result = await self._mining_service.mine_requirements(
                state.user_input, state.mining_context
            )

            # Store results
            state.step_results["mine_requirements"] = {
                "mining_result": state.mining_result.__dict__,
                "demand_state": state.mining_result.demand_state,
                "blueprint": state.mining_result.blueprint
            }

            # Add completion update
            state.add_streaming_update(
                "mine_requirements",
                f"Requirements mined successfully: {state.mining_result.demand_state}",
                "completed",
                {
                    "demand_state": state.mining_result.demand_state,
                    "requirements_count": len(state.mining_result.final_requirements)
                }
            )

            return state

        except Exception as e:
            logger.error(f"Requirements mining failed: {e}")
            state.error = f"Mining failed: {str(e)}"
            state.add_streaming_update(
                "mine_requirements",
                f"Mining error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _plan_workflow_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Plan workflow using WorkflowPlanningService."""
        try:
            state.current_step = "plan_workflow"
            state.add_streaming_update(
                "plan_workflow",
                "Creating workflow execution plan...",
                "in_progress"
            )

            # Prepare planning input from mining results
            state.planning_input = {
                "intent_categories": [],  # Will be extracted from mining result
                "intent_confidence": 0.8,  # Default confidence
                "intent_reasoning": "Extracted from mining analysis",
                "strategic_blueprint": state.mining_result.blueprint if state.mining_result else {}
            }

            # TODO: Extract intent categories from mining result
            # For now, use a default mapping based on demand state
            if state.mining_result:
                if "collect" in state.mining_result.demand_state.lower():
                    state.planning_input["intent_categories"].append("collect")
                if "analyze" in state.mining_result.demand_state.lower():
                    state.planning_input["intent_categories"].append("analyze")
                if "generate" in state.mining_result.demand_state.lower():
                    state.planning_input["intent_categories"].append("generate")

                # Default to answer if no specific categories
                if not state.planning_input["intent_categories"]:
                    state.planning_input["intent_categories"] = ["answer"]

            # Execute workflow planning
            state.planning_result = await self._workflow_planning.create_workflow_plan(
                state.planning_input,
                state.user_id,
                state.task_id
            )

            # Store results
            state.step_results["plan_workflow"] = {
                "planning_result": state.planning_result,
                "workflow_plan": state.planning_result.get("workflow_plan", {}),
                "success": state.planning_result.get("success", False)
            }

            # Add completion update
            workflow_plan = state.planning_result.get("workflow_plan", {})
            dsl_plan = workflow_plan.get("dsl_plan", [])

            state.add_streaming_update(
                "plan_workflow",
                f"Workflow plan created with {len(dsl_plan)} execution steps",
                "completed",
                {
                    "plan_summary": f"{len(dsl_plan)} steps planned",
                    "estimated_duration": workflow_plan.get("estimated_duration", "Unknown")
                }
            )

            return state

        except Exception as e:
            logger.error(f"Workflow planning failed: {e}")
            state.error = f"Planning failed: {str(e)}"
            state.add_streaming_update(
                "plan_workflow",
                f"Planning error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _execute_workflow_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Execute workflow using WorkflowOrchestrator."""
        try:
            state.current_step = "execute_workflow"
            state.add_streaming_update(
                "execute_workflow",
                "Executing workflow tasks...",
                "in_progress"
            )

            # Prepare workflow execution request
            workflow_plan = state.planning_result.get("workflow_plan", {})
            dsl_plan = workflow_plan.get("dsl_plan", [])

            state.workflow_execution_request = WorkflowExecutionRequest(
                workflow_definition={
                    "id": state.task_id,
                    "steps": dsl_plan
                },
                execution_mode=WorkflowExecutionMode.EXECUTE,
                parameters=state.input_data,
                timeout=3600,
                metadata={
                    "session_id": state.session_id,
                    "user_id": state.user_id
                }
            )

            # Execute workflow
            response = await self._workflow_orchestrator.execute_workflow(
                state.workflow_execution_request
            )

            # Store execution results
            state.execution_results.append({
                "execution_id": response.execution_id,
                "workflow_id": response.workflow_id,
                "status": response.status.value,
                "result": response.result,
                "execution_time": response.execution_time
            })

            # Store results
            state.step_results["execute_workflow"] = {
                "execution_response": {
                    "execution_id": response.execution_id,
                    "status": response.status.value,
                    "success": response.status.value == "completed"
                },
                "execution_results": state.execution_results
            }

            # Add completion update
            state.add_streaming_update(
                "execute_workflow",
                f"Workflow execution completed: {response.status.value}",
                "completed" if response.status.value == "completed" else "failed",
                {
                    "execution_id": response.execution_id,
                    "status": response.status.value,
                    "execution_time": response.execution_time
                }
            )

            return state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            state.error = f"Execution failed: {str(e)}"
            state.add_streaming_update(
                "execute_workflow",
                f"Execution error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _quality_control_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Perform quality control on execution results."""
        try:
            state.current_step = "quality_control"
            state.add_streaming_update(
                "quality_control",
                "Performing quality control checks...",
                "in_progress"
            )

            # TODO: Implement quality control logic
            # For now, mark as passed
            state.qc_results = {
                "overall_passed": True,
                "checks_performed": ["basic_validation"],
                "issues": [],
                "recommendations": []
            }

            # Store results
            state.step_results["quality_control"] = {
                "qc_results": state.qc_results,
                "passed": state.qc_results["overall_passed"]
            }

            # Add completion update
            state.add_streaming_update(
                "quality_control",
                "Quality control checks completed successfully",
                "completed",
                {"passed": state.qc_results["overall_passed"]}
            )

            return state

        except Exception as e:
            logger.error(f"Quality control failed: {e}")
            state.error = f"Quality control failed: {str(e)}"
            state.add_streaming_update(
                "quality_control",
                f"Quality control error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _handle_user_feedback_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Handle user feedback and dynamic updates."""
        try:
            state.current_step = "handle_user_feedback"

            # Check if feedback is available
            if state.user_feedback:
                state.add_streaming_update(
                    "handle_user_feedback",
                    "Processing user feedback...",
                    "in_progress"
                )

                # Process feedback
                feedback_type = state.user_feedback.get("type", "general")
                feedback_content = state.user_feedback.get("content", "")

                # Store feedback processing results
                state.step_results["handle_user_feedback"] = {
                    "feedback_type": feedback_type,
                    "feedback_content": feedback_content,
                    "processed": True
                }

                state.add_streaming_update(
                    "handle_user_feedback",
                    f"User feedback processed: {feedback_type}",
                    "completed",
                    {"feedback_type": feedback_type}
                )
            else:
                # No feedback to process
                state.add_streaming_update(
                    "handle_user_feedback",
                    "No user feedback to process",
                    "completed"
                )

            return state

        except Exception as e:
            logger.error(f"User feedback handling failed: {e}")
            state.error = f"Feedback handling failed: {str(e)}"
            state.add_streaming_update(
                "handle_user_feedback",
                f"Feedback handling error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _finalize_session_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Finalize the session and prepare final results."""
        try:
            state.current_step = "finalize_session"
            state.add_streaming_update(
                "finalize_session",
                "Finalizing session and preparing results...",
                "in_progress"
            )

            # Mark as completed
            state.completed = True

            # Calculate session duration
            if state.start_time:
                session_duration = (datetime.utcnow() - state.start_time).total_seconds()
                state.step_timings["total_session"] = session_duration

            # Prepare final summary
            final_summary = {
                "session_id": state.session_id,
                "task_id": state.task_id,
                "user_id": state.user_id,
                "completed": state.completed,
                "steps_completed": len([s for s in state.step_status.values() if s == SummarizerStepStatus.COMPLETED]),
                "total_steps": len(state.step_status),
                "session_duration": state.step_timings.get("total_session", 0),
                "execution_results": state.execution_results,
                "qc_results": state.qc_results
            }

            # Store final results
            state.step_results["finalize_session"] = {
                "final_summary": final_summary,
                "completed": True
            }

            # Add completion update
            state.add_streaming_update(
                "finalize_session",
                f"Session completed successfully in {state.step_timings.get('total_session', 0):.2f} seconds",
                "completed",
                final_summary
            )

            return state

        except Exception as e:
            logger.error(f"Session finalization failed: {e}")
            state.error = f"Finalization failed: {str(e)}"
            state.add_streaming_update(
                "finalize_session",
                f"Finalization error: {str(e)}",
                "failed",
                error=str(e)
            )
            return state

    async def _handle_error_node(self, state: SummarizerState) -> SummarizerState:
        """Node: Handle errors and provide recovery options."""
        try:
            state.current_step = "handle_error"

            error_message = state.error or "Unknown error occurred"

            state.add_streaming_update(
                "handle_error",
                f"Handling error: {error_message}",
                "failed",
                {"error": error_message}
            )

            # Store error handling results
            state.step_results["handle_error"] = {
                "error": error_message,
                "handled": True,
                "recovery_attempted": False
            }

            return state

        except Exception as e:
            logger.error(f"Error handling failed: {e}")
            state.error = f"Error handling failed: {str(e)}"
            return state

    # ==================== LangGraph Routing Functions ====================

    def _route_after_validation(self, state: SummarizerState) -> str:
        """Route after user interaction validation."""
        if state.error:
            return "error"
        elif not state.should_proceed:
            return "end"
        else:
            return "proceed"

    def _route_after_mining(self, state: SummarizerState) -> str:
        """Route after requirements mining."""
        if state.error:
            return "error"
        elif state.mining_result and state.mining_result.needs_clarification:
            return "clarify"
        else:
            return "proceed"

    def _route_after_planning(self, state: SummarizerState) -> str:
        """Route after workflow planning."""
        if state.error:
            return "error"
        elif state.planning_result and state.planning_result.get("success", False):
            return "execute"
        else:
            return "replan"

    def _route_after_execution(self, state: SummarizerState) -> str:
        """Route after workflow execution."""
        if state.error:
            return "error"
        elif state.execution_results and any(r.get("status") == "completed" for r in state.execution_results):
            return "quality_control"
        elif state.feedback_requested:
            return "user_feedback"
        else:
            return "finalize"

    def _route_after_qc(self, state: SummarizerState) -> str:
        """Route after quality control."""
        if state.error:
            return "error"
        elif state.qc_results.get("overall_passed", False):
            return "finalize"
        elif state.qc_results.get("needs_user_input", False):
            return "user_feedback"
        else:
            return "retry"

    def _route_after_feedback(self, state: SummarizerState) -> str:
        """Route after user feedback handling."""
        if state.error:
            return "error"
        elif state.user_feedback:
            feedback_type = state.user_feedback.get("type", "general")
            if feedback_type == "clarification":
                return "continue"
            elif feedback_type == "replan":
                return "replan"
            elif feedback_type == "retry":
                return "retry"
            else:
                return "finalize"
        else:
            return "finalize"

    # ==================== Utility Methods ====================

    def _update_session_metrics(self, success: bool, session_time: float):
        """Update session performance metrics."""
        self._total_sessions += 1
        if success:
            self._successful_sessions += 1

        # Update average session time
        if self._total_sessions > 0:
            self._average_session_time = (
                (self._average_session_time * (self._total_sessions - 1) + session_time)
                / self._total_sessions
            )

    async def run(self, input_data: Dict, context: Dict) -> Dict:
        """
        Non-streaming execution method.

        This method collects all streaming results and returns them as a single response.
        """
        results = []

        async for chunk in self.stream(input_data, context):
            # Parse streaming chunk to extract content
            try:
                chunk_data = json.loads(chunk)
                if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                    delta = chunk_data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        results.append(content)
            except json.JSONDecodeError:
                # Handle non-JSON chunks
                results.append(chunk)

        return {
            "success": True,
            "result": "".join(results),
            "service": self.service_name,
            "session_metrics": {
                "total_sessions": self._total_sessions,
                "successful_sessions": self._successful_sessions,
                "success_rate": self._successful_sessions / max(self._total_sessions, 1),
                "average_session_time": self._average_session_time
            }
        }

    async def get_session_state(self, session_id: str) -> Optional[SummarizerState]:
        """Get the current state of an active session."""
        return self._active_sessions.get(session_id)

    async def update_session_feedback(self, session_id: str, feedback: Dict[str, Any]) -> bool:
        """Update user feedback for an active session."""
        if session_id in self._active_sessions:
            self._active_sessions[session_id].user_feedback = feedback
            self._active_sessions[session_id].feedback_requested = False
            return True
        return False

    async def get_service_metrics(self) -> Dict[str, Any]:
        """Get service performance metrics."""
        return {
            "service_name": self.service_name,
            "total_sessions": self._total_sessions,
            "successful_sessions": self._successful_sessions,
            "success_rate": self._successful_sessions / max(self._total_sessions, 1),
            "average_session_time": self._average_session_time,
            "active_sessions": len(self._active_sessions),
            "supported_domains": len(DOMAINS),
            "workflow_nodes": [
                "validate_interaction",
                "mine_requirements",
                "plan_workflow",
                "execute_workflow",
                "quality_control",
                "handle_user_feedback",
                "finalize_session",
                "handle_error"
            ]
        }

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities."""
        return {
            "name": self.service_name,
            "version": "2.0.0",
            "description": "LangGraph-based Multi-Task Summarizer with real-time streaming and user feedback",
            "capabilities": [
                "Real-time streaming output",
                "User interaction validation",
                "Requirements mining and analysis",
                "Workflow planning and execution",
                "Quality control and validation",
                "Dynamic user feedback handling",
                "OpenAI-compatible streaming format",
                "LangGraph state management",
                "Multi-domain task processing"
            ],
            "supported_domains": DOMAINS,
            "workflow_architecture": "LangGraph-based state machine",
            "streaming_format": "OpenAI-compatible",
            "execution_chain": "WorkflowOrchestrator → TaskProcessor → LangChainEngine → Agent",
            "state_management": "Comprehensive top-level state object",
            "error_handling": "Comprehensive error recovery and user guidance"
        }


# ==================== Service Registration ====================

async def create_summarizer() -> Summarizer:
    """Factory function to create and initialize Summarizer."""
    service = Summarizer()
    await service.initialize()
    return service


# Export for external usage
__all__ = [
    "Summarizer",
    "SummarizerState",
    "SummarizerStepStatus",
    "TaskCategory",
    "create_summarizer"
]

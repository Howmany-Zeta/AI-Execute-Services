"""
Mining Service - Enhanced Demand Analysis

This service replaces IntentParserService and integrates intent_parser and meta_architect
using langgraph for comprehensive demand analysis.

The service manages user demand states according to SMART criteria and orchestrates
multi-round interactions to clarify vague requirements and analyze user intents.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple

# LangGraph dependencies
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import system components
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.agent.system.intent_parser import IntentParserAgent
from app.services.multi_task.agent.domain.meta_architect import MetaArchitectAgent
from app.services.multi_task.services.interacter.interacter import InteracterService
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole
from app.services.multi_task.core.models.services_models import (
    DemandState, MiningContext, MiningState, MiningResult, ServiceStatus
)
from app.services.multi_task.core.exceptions.services_exceptions import MiningError
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.multi_task.data.storage.knowledge_database import KnowledgeDatabase

logger = logging.getLogger(__name__)


class MiningService:
    """
    Enhanced mining service that replaces IntentParserService.

    Uses langgraph to orchestrate intent_parser and meta_architect for:
    1. SMART criteria analysis of user demands
    2. Multi-round clarification for vague requirements
    3. Intent analysis and complexity assessment
    4. Strategic planning for complex requests
    """

    def __init__(self, llm_manager: LLMIntegrationManager, config_manager: ConfigManager, config: Dict[str, Any] = None):
        """
        Initialize the mining service.

        Args:
            llm_manager: LLM integration manager for AI operations
            config_manager: Configuration manager for prompts and tasks
            config: Optional service configuration
        """
        self.llm_manager = llm_manager
        self.config_manager = config_manager
        self._config = config or {}

        # Initialize knowledge database
        self.knowledge_db = KnowledgeDatabase(database_url="sqlite:///knowledge_database.db")
        self.knowledge_db.initialize()  # Initialize database

        # Initialize agents
        self._init_agents()

        # Initialize memory saver
        self._memory_saver = MemorySaver()

        # Initialize langgraph workflow
        self._init_workflow()

        # Performance tracking
        self._total_mining_operations = 0
        self._successful_operations = 0
        self._average_clarification_rounds = 0.0

        logger.info("MiningService initialized with langgraph workflow")

    def _init_agents(self) -> None:
        """Initialize intent parser, meta architect, and interacter agents"""
        # Validate LLM manager type before proceeding
        if not hasattr(self.llm_manager, 'generate_with_context'):
            logger.error(f"Invalid LLM manager type: {type(self.llm_manager)}")
            raise TypeError(f"llm_manager must have generate_with_context method. Got: {type(self.llm_manager)}")

        logger.debug(f"Initializing agents with LLM manager type: {type(self.llm_manager)}")

        # Create agent configurations
        intent_parser_config = AgentConfig(
            name="Mining Intent Parser",
            role=AgentRole.INTENT_PARSER,
            goal="Parse and analyze user intents for demand mining",
            backstory="An expert agent specialized in understanding user requirements and extracting actionable intents from natural language descriptions.",
            max_iter=3,
            allow_delegation=False
        )

        meta_architect_config = AgentConfig(
            name="Mining Meta Architect",
            role=AgentRole.META_ARCHITECT,  # Using available role
            goal="Design strategic blueprints for complex multi-task workflows",
            backstory="A strategic architect agent that creates comprehensive blueprints and frameworks for complex task execution workflows.",
            max_iter=5,
            allow_delegation=False
        )

        # Initialize agents with additional error handling
        try:
            self.intent_parser = IntentParserAgent(
                config=intent_parser_config,
                config_manager=self.config_manager,
                llm_manager=self.llm_manager
            )
            logger.debug(f"Intent parser initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize intent parser: {e}")
            raise

        try:
            self.meta_architect = MetaArchitectAgent(
                config=meta_architect_config,
                config_manager=self.config_manager,
                llm_manager=self.llm_manager,
                knowledge_database=self.knowledge_db  # Pass knowledge database instance
            )
            logger.debug(f"Meta architect initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize meta architect: {e}")
            raise

        # Initialize Interacter for demand state analysis
        try:
            self.interacter = InteracterService(
                llm_manager=self.llm_manager
            )
            logger.debug(f"Interacter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize interacter: {e}")
            raise

    def _init_workflow(self) -> None:
        """Initialize the enhanced, interactive langgraph workflow."""
        workflow = StateGraph(MiningState)

        # --- 1. Define All Nodes ---
        workflow.add_node("analyze_demand", self._analyze_demand_node)
        workflow.add_node("clarify_requirements", self._clarify_requirements_node)
        workflow.add_node("intent_analysis", self._intent_analysis_node)
        workflow.add_node("simple_strategy_flow", self._simple_strategy_flow_node)
        workflow.add_node("meta_architect_flow", self._meta_architect_flow_node)
        workflow.add_node("generate_roadmap", self._generate_roadmap_node)

        # NEW: Unified pause and feedback processing nodes
        workflow.add_node("wait_for_user_feedback", self._wait_for_user_feedback_node)

        # NEW: Dedicated feedback processing nodes
        workflow.add_node("process_clarification", self._process_clarification_node)
        workflow.add_node("process_adjustment", self._process_adjustment_node)

        # RENAMED: Unified result packaging node
        workflow.add_node("package_results", self._package_results_node)  # Renamed from summarizer_flow
        workflow.add_node("finalize_result", self._finalize_result_node)

        # --- 2. Define Workflow Edges ---
        # Set conditional entry point to handle both new workflows and resumed workflows with feedback
        workflow.add_conditional_edges(
            "__start__",
            self._route_workflow_entry,
            {
                "analyze_demand": "analyze_demand",
                "process_clarification": "process_clarification",
                "process_adjustment": "process_adjustment",
                "generate_roadmap": "generate_roadmap",
                "package_results": "package_results",
                "error": END
            }
        )

        # After initial analysis, either go to intent analysis or start clarification
        workflow.add_conditional_edges(
            "analyze_demand",
            self._route_after_analysis,
            {"intent_analysis": "intent_analysis", "clarify": "clarify_requirements", "error": END}
        )

        # After clarification, either proceed to intent analysis or pause for more feedback.
        workflow.add_conditional_edges(
            "clarify_requirements",
            self._route_after_clarification,
            {
                "intent_analysis": "intent_analysis",
                "wait_for_user_feedback": "wait_for_user_feedback"
            }
        )

        # NEW: Feedback processing nodes routing
        workflow.add_edge("process_clarification", "analyze_demand")  # Re-analyze after clarification
        workflow.add_conditional_edges(
            "process_adjustment",
            self._route_after_adjustment,
            {
                "intent_analysis": "intent_analysis",
                "meta_architect_flow": "meta_architect_flow",
                "error": END
            }
        )

        # After intent analysis, branch to simple or complex flow
        workflow.add_conditional_edges(
            "intent_analysis",
            self._route_after_intent_analysis,
            {"meta_architect": "meta_architect_flow", "simple_strategy": "simple_strategy_flow", "error": END}
        )

        # Both planning flows also go to the unified pause node to await confirmation
        workflow.add_edge("simple_strategy_flow", "wait_for_user_feedback")
        workflow.add_edge("meta_architect_flow", "wait_for_user_feedback")

        # The unified pause node always ends the current execution, waiting for resumption
        workflow.add_edge("wait_for_user_feedback", END)

        # Generate roadmap after meta architect confirmation
        workflow.add_edge("generate_roadmap", "package_results")

        # The two final nodes run in sequence
        workflow.add_edge("package_results", "finalize_result")
        workflow.add_edge("finalize_result", END)

        # Compile the workflow WITH the checkpointer
        self.workflow = workflow.compile(checkpointer=self._memory_saver)

    def _route_workflow_entry(self, state: MiningState) -> str:
        """Route workflow entry - handle new workflows vs resumed workflows with feedback"""
        try:
            # Validate state object
            if not state.get('user_input'):
                logger.error("Invalid state: missing user_input")
                return "error"

            # Check if this is a resumed workflow with feedback
            if state.get('user_feedback'):
                logger.info("Detected resumed workflow with user feedback")
                # Route through feedback processor
                return self._process_and_route_feedback(state)
            elif state.get('status') == "processing_feedback":
                logger.info("Detected feedback processing status")
                return self._process_and_route_feedback(state)
            else:
                # New workflow - start with demand analysis
                logger.info("Starting new workflow")
                return "analyze_demand"

        except Exception as e:
            logger.error(f"Error in workflow entry routing: {e}")
            return "error"

    async def initialize(self) -> None:
        """Initialize the service and underlying agents"""
        try:
            await self.intent_parser.initialize()
            await self.meta_architect.initialize()
            # InteracterService doesn't need async initialization
            logger.info("MiningService initialization completed")
        except Exception as e:
            logger.error(f"Failed to initialize MiningService: {e}")
            raise

    async def mine_requirements(self, user_input: str, context: MiningContext) -> MiningResult:
        """
        Main entry point for mining user requirements.

        Args:
            session_id: Session identifier for the mining process
            user_input: User input text to analyze
            context: Mining context with metadata

        Returns:
            Mining result with requirements and blueprint

        Raises:
            Exception: If mining process fails
        """
        # Prepare the configuration required by LangGraph and use session_id as thread_id
        config = {
            "configurable": {
                "thread_id": context.session_id
            }
        }

        if not user_input or not user_input.strip():
            raise ValueError("Empty user input provided for mining")

        try:
            start_time = self._get_current_time_ms()

            logger.debug(f"Starting mining process for input: {user_input[:100]}...")

            # Initialize state
            initial_state = MiningState(
                user_input=user_input.strip(),
                context=context,
                messages=[]
            )

            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state, config=config)

            # Check for errors
            if final_state.get('error'):
                raise Exception(f"Mining workflow failed: {final_state.get('error', 'Unknown error')}")

            # Calculate processing time
            processing_time = self._get_current_time_ms() - start_time

            # Create result
            # Map internal status to external status using constants
            internal_status = final_state.get("status", ServiceStatus.COMPLETED.value)
            external_status = ServiceStatus.WAITING_FOR_USER_FEEDBACK.value if internal_status == "waiting_for_user_feedback" else internal_status

            result = MiningResult(
                original_input=user_input,
                final_requirements=self._extract_final_requirements(final_state),
                demand_state=final_state.get("demand_state"),  # Use .get() for dictionaries
                smart_analysis=final_state.get("smart_analysis") or {}, # Use .get()
                clarification_history=self._extract_clarification_history(final_state),
                processing_time_ms=processing_time,
                intent_analysis=final_state.get("intent_analysis"),
                meta_architect_result=final_state.get("meta_architect_result"),
                simple_strategy_result=final_state.get("simple_strategy_result"),
                messages=final_state.get("messages"),
                status=external_status,  # Use mapped status
                session_id=context.session_id,
                task_id=context.task_id
            )

            # Update metrics
            self._update_metrics(True, context.current_round)

            logger.info(f"Successfully completed mining process: {final_state.get('demand_state')}")
            return result

        except Exception as e:
            self._update_metrics(False, 0)
            logger.error(f"Mining process failed: {e}")
            raise Exception(f"Mining process failed: {e}")

    async def resume_workflow_with_feedback(self, session_id: str, feedback_data: Dict[str, Any]) -> MiningResult:
        """
        Unified entry point to resume a paused workflow with any type of user feedback.

        Args:
            session_id: Session identifier for the paused workflow
            feedback_data: Dictionary containing feedback type, content, and other data

        Returns:
            Updated mining result after processing feedback

        Raises:
            Exception: If workflow resumption fails
        """
        try:
            logger.info(f"Resuming workflow for session {session_id} with feedback type: {feedback_data.get('type', 'unknown')}")

            # Configure workflow resumption with checkpoint
            config = {
                "configurable": {
                    "thread_id": session_id
                }
            }

            # --- NEW: Get the last known state from the checkpointer ---
            # This requires your workflow to be compiled with a checkpointer, which it is.
            last_state = self.workflow.get_state(config)

            # For LangGraph checkpoint resumption, we only need to provide the new feedback data
            # The complete state (including user_input) will be restored from the checkpoint
            state_update = {
                "user_input": last_state.values.get('user_input', ''),
                "user_feedback": feedback_data,
                "status": "processing_feedback",
                "user_responses": feedback_data.get("responses", [])
            }

            logger.info(f"Resuming workflow with state: {state_update}")

            # Resume workflow from checkpoint - it will restore the original state and merge feedback
            final_state = await self.workflow.ainvoke(state_update, config=config)

            # Check for errors in the resumed workflow
            if final_state.get('error'):
                raise Exception(f"Resumed workflow failed: {final_state.get('error', 'Unknown error')}")

            # Create updated mining result from the final state
            # Extract task_id from the context in the last state
            context_object = last_state.values.get('context')
            task_id = context_object.task_id if context_object else None

            # Map internal status to external status using constants
            internal_status = final_state.get('status', ServiceStatus.COMPLETED.value)
            external_status = ServiceStatus.WAITING_FOR_USER_FEEDBACK.value if internal_status == "waiting_for_user_feedback" else internal_status

            result = MiningResult(
                original_input=final_state.get('user_input', ''),
                final_requirements=self._extract_final_requirements(final_state),
                demand_state=final_state.get('demand_state'),
                smart_analysis=final_state.get('smart_analysis', {}),
                clarification_history=self._extract_clarification_history(final_state),
                processing_time_ms=0,  # Not tracking time for resumed workflows
                intent_analysis=final_state.get('intent_analysis', {}),
                simple_strategy_result=final_state.get('simple_strategy_result', {}),
                meta_architect_result=final_state.get('meta_architect_result', {}),
                messages=final_state.get("messages"),
                status=external_status,  # Use mapped status
                error=final_state.get('error'),
                session_id=session_id,
                task_id=task_id
            )

            logger.info(f"Workflow resumed successfully for session {session_id}: {result.demand_state}")
            return result

        except Exception as e:
            logger.error(f"Failed to resume workflow for session {session_id}: {e}")
            raise Exception(f"Workflow resumption failed: {e}")

    def _process_and_route_feedback(self, state: MiningState) -> str:
        """
        Simplified Router: Only makes routing decisions based on feedback type and confirmation.
        Processing logic has been moved to dedicated nodes.
        """
        try:
            # Validate state object
            if not state.get('user_feedback'):
                logger.error("Invalid state: missing user_feedback")
                return "error"

            feedback_type = state.get('feedback_type')
            user_feedback = state.get('user_feedback', {})
            user_confirmation = user_feedback.get("confirmation", False)

            logger.info(f"Routing feedback of type: {feedback_type}, confirmation: {user_confirmation}")

            if feedback_type == "clarification":
                # Route to clarification processing node, then re-analyze
                return "process_clarification"

            elif feedback_type == "simple_strategy_confirmation":
                if user_confirmation:
                    return "package_results"
                else:
                    # Route to adjustment processing node, then re-run intent analysis
                    return "process_adjustment"

            elif feedback_type == "meta_architect_confirmation":
                if user_confirmation:
                    return "generate_roadmap"
                else:
                    # Route to adjustment processing node, then re-run meta architect
                    return "process_adjustment"

            logger.warning(f"Unknown feedback type: {feedback_type}")
            return "package_results"  # Default fallback

        except Exception as e:
            logger.error(f"Error in feedback routing: {e}")
            state['error'] = f"Feedback routing failed: {e}"
            return "error"

    def _create_blueprint_summary(self, architect_output: Dict[str, Any]) -> str:
        """Helper to create a summary of the blueprint for user confirmation."""
        try:
            if not architect_output:
                return "No blueprint details available"

            summary_parts = []

            # Extract key components for summary
            if "problem_analysis" in architect_output:
                summary_parts.append(f"Problem Analysis: {architect_output['problem_analysis']}")

            if "solution_approach" in architect_output:
                summary_parts.append(f"Solution Approach: {architect_output['solution_approach']}")

            if "key_components" in architect_output:
                components = architect_output["key_components"]
                if isinstance(components, list):
                    summary_parts.append(f"Key Components: {', '.join(components)}")
                elif isinstance(components, dict):
                    summary_parts.append(f"Key Components: {', '.join(components.keys())}")

            return "; ".join(summary_parts) if summary_parts else "Detailed blueprint generated"

        except Exception as e:
            logger.error(f"Error creating blueprint summary: {e}")
            return "Blueprint summary unavailable"

    async def _analyze_demand_node(self, state: MiningState) -> MiningState:
        """Analyze user demand using intent parser with SMART criteria"""
        try:
            logger.debug("Executing demand analysis node")

            # Prepare context for intent parser
            context = state.get('context')
            analysis_context = {
                "task_id": context.task_id,
                "timestamp": context.timestamp or self._get_current_timestamp(),
                "domain": context.domain,
                "user_id": context.user_id,
                "session_id": context.session_id
            }

            # Analyze demand state using Interacter
            smart_analysis = await self.interacter.analyze_demand_state(
                state.get('user_input'), analysis_context
            )

            # Enhanced demand_state extraction logic
            demand_state = smart_analysis.get("demand_state") if smart_analysis else None
            logger.debug(f"DEBUG_MINING: Extracted demand_state = {demand_state}")

            # If demand_state is None, try to infer it from other fields
            if demand_state is None:
                logger.warning("DEBUG_MINING: demand_state is None, attempting to infer from smart_analysis")
                demand_state = self._infer_demand_state_from_analysis(smart_analysis, state.get('user_input'))
                logger.debug(f"DEBUG_MINING: Inferred demand_state = {demand_state}")

            # Final protection: If it is still None, use the default value
            if demand_state is None:
                logger.error("DEBUG_MINING: Failed to determine demand_state, using fallback")
                demand_state = self._get_fallback_demand_state(state.get('user_input'))
                logger.debug(f"DEBUG_MINING: Fallback demand_state = {demand_state}")

            # Make sure demand_state is not None
            if demand_state is None:
                logger.critical("DEBUG_MINING: CRITICAL - demand_state is still None after all fallbacks!")
                demand_state = "SMART_LARGE_SCOPE"
                logger.debug(f"DEBUG_MINING: Hard-coded demand_state = {demand_state}")

            # Update state
            state['demand_state'] = demand_state
            state['smart_analysis'] = smart_analysis or {}
            state['clarification_questions'] = smart_analysis.get("clarification_needed", []) if smart_analysis else []

            logger.info(f"Demand analysis completed: {state['demand_state']}")
            return state

        except Exception as e:
            logger.error(f"Demand analysis failed: {e}")
            # Set a valid demand_state even if an error occurs
            state['demand_state'] = self._get_fallback_demand_state(state.get('user_input'))
            state['smart_analysis'] = {"error": str(e)}
            state['error'] = f"Demand analysis failed: {e}"
            return state

    async def _clarify_requirements_node(self, state: MiningState) -> MiningState:
        """Enhanced clarification node - prepares questions and sets feedback type"""
        try:
            context = state.get('context')
            logger.debug(f"Executing enhanced clarification node (round {context.current_round + 1})")

            # Check if we've exceeded max rounds (max 3 rounds)
            if context.current_round >= 3:
                logger.warning("Maximum clarification rounds (3) reached - proceeding to intent analysis")
                # Set a flag to indicate we're proceeding due to max clarifications
                state['max_clarifications_reached'] = True
                # Set demand_state to SMART_COMPLIANT to route to intent analysis
                state['demand_state'] = DemandState.SMART_COMPLIANT.value
                # Return state to let workflow routing handle the next step
                return state

            # Get clarification questions from smart_analysis
            clarification_needed = []
            reasoning = ""

            smart_analysis = state.get('smart_analysis')
            if smart_analysis:
                clarification_needed = smart_analysis.get("clarification_needed", [])
                reasoning = smart_analysis.get("reasoning", "")

            # If no questions from LLM, generate default ones
            if not clarification_needed:
                clarification_needed = await self._generate_clarification_questions(state)

            # Remove duplicates from clarification questions
            if clarification_needed:
                # Convert to set to remove duplicates, then back to list
                unique_questions = list(dict.fromkeys(clarification_needed))  # Preserve order
                if len(unique_questions) != len(clarification_needed):
                    logger.warning(f"Removed {len(clarification_needed) - len(unique_questions)} duplicate clarification questions")
                clarification_needed = unique_questions

            # Store clarification questions and reasoning in state
            if not state.get('clarification_questions'):
                state['clarification_questions'] = []
            if not state.get('reasoning'):
                state['reasoning'] = ""

            # Clear previous questions and add new ones
            state['clarification_questions'] = clarification_needed
            state['reasoning'] = reasoning

            # Set feedback type for unified handling
            state['feedback_type'] = "clarification"

            # Add clarification message to messages list for Summarizer
            if not state.get('messages'):
                state['messages'] = []

            # Create clarification message in proper LangGraph format
            clarification_content = f"Clarification needed (Round {context.current_round + 1}): {'; '.join(clarification_needed)}"
            if reasoning:
                clarification_content += f"\n\nReasoning: {reasoning}"

            clarification_message = {
                "role": "assistant",
                "content": clarification_content
            }

            state['messages'].append(clarification_message)

            # Store clarification metadata separately for Summarizer detection
            state['clarification_metadata'] = {
                "type": "clarification",
                "questions": clarification_needed,
                "reasoning": reasoning,
                "round": context.current_round + 1
            }
            context.current_round += 1

            logger.info(f"Clarification message prepared (Round {context.current_round}): {clarification_content}")
            return state

        except Exception as e:
            logger.error(f"Clarification preparation failed: {e}")
            state['error'] = f"Clarification failed: {e}"
            return state

    async def _wait_for_user_feedback_node(self, state: MiningState) -> MiningState:
        """
        Unified pause node. Sets the status and prepares to hand off to Summarizer.
        """
        try:
            logger.info(f"Workflow pausing. Waiting for user feedback of type: {state.get('feedback_type')}")
            state['status'] = "waiting_for_user_feedback"
            return state
        except Exception as e:
            logger.error(f"Wait for user feedback node failed: {e}")
            state['error'] = f"Wait for user feedback failed: {e}"
            return state

    async def _process_clarification_node(self, state: MiningState) -> MiningState:
        """NEW NODE: Process clarification feedback by enriching user_input."""
        try:
            logger.debug("Processing clarification feedback")

            user_feedback = state.get('user_feedback', {})
            user_responses = user_feedback.get("responses", [])

            if user_responses:
                # Combine original input with user responses to create enriched context
                original_input = state.get('user_input')
                combined_context = f"{original_input}\n\nAdditional clarifications:\n"

                for i, response in enumerate(user_responses, 1):
                    combined_context += f"{i}. {response}\n"

                # Update user input to include clarifications for downstream processing
                state['user_input'] = combined_context
                logger.debug(f"Updated user input with clarifications: {combined_context}")

            return state

        except Exception as e:
            logger.error(f"Error processing clarification feedback: {e}")
            state['error'] = f"Clarification processing failed: {e}"
            return state

    async def _process_adjustment_node(self, state: MiningState) -> MiningState:
        """Process adjustment feedback by enriching user_input."""
        try:
            logger.debug("Processing adjustment feedback")

            user_feedback = state.get('user_feedback', {})
            adjustments = user_feedback.get("adjustments", "")

            if adjustments and adjustments.strip():
                # Combine the original input with user adjustments
                original_input = state.get('user_input')
                enhanced_input = f"{original_input}\n\nUser adjustments: {adjustments}"

                # Update user input to include adjustments for downstream processing
                state['user_input'] = enhanced_input
                logger.debug(f"Updated user input with adjustments: {enhanced_input}")

            return state

        except Exception as e:
            logger.error(f"Error processing adjustment feedback: {e}")
            state['error'] = f"Adjustment processing failed: {e}"
            return state


    async def _intent_analysis_node(self, state: MiningState) -> MiningState:
        """Intent analysis node - calls executeTask and assess_request_complexity"""
        try:
            logger.debug("Executing intent analysis node")

            # Additional validation and debugging
            if not hasattr(self.intent_parser, 'execute_task'):
                logger.error(f"Intent parser missing execute_task method: {type(self.intent_parser)}")
                state['error'] = f"Intent parser configuration error: missing execute_task method"
                return state

            logger.debug(f"Intent parser type: {type(self.intent_parser)}")
            logger.debug(f"Intent parser LLM manager type: {type(self.intent_parser.llm_manager) if hasattr(self.intent_parser, 'llm_manager') else 'No llm_manager'}")

            # Prepare context for intent parser
            context = state.get('context')
            analysis_context = {
                "task_id": f"{context.task_id}_intent",
                "timestamp": context.timestamp or self._get_current_timestamp(),
                "domain": context.domain,
                "user_id": context.user_id,
                "session_id": context.session_id
            }

            # Prepare task data for executeTask
            task_data = {
                "text": state.get('user_input'),
                "analysis_type": "intent_parsing"
            }

            logger.debug(f"Calling intent parser execute_task with context: {analysis_context}")

            # Call Intent_parser's executeTask for intent parsing with enhanced error handling
            try:
                intent_result = await self.intent_parser.execute_task(task_data, analysis_context)
                logger.debug(f"Intent parsing result: {intent_result}")
            except Exception as intent_error:
                logger.error(f"Intent parser execute_task failed: {intent_error}")
                logger.error(f"Intent parser state: busy={getattr(self.intent_parser, '_is_busy', 'unknown')}")
                # Re-raise with more context
                raise Exception(f"Intent parsing execution failed: {intent_error}")

            # Extract categories from intent result
            categories = intent_result.get("categories", [])

            # Extract the new intent result data
            reasoning = intent_result.get("reasoning", "")
            actual_output = intent_result.get("actual_output", "")

            # Call assess_request_complexity
            try:
                complexity_result = self.intent_parser.assess_request_complexity(state.get('user_input'), categories)
                logger.debug(f"Complexity assessment result: {complexity_result}")
            except Exception as complexity_error:
                logger.error(f"Complexity assessment failed: {complexity_error}")
                # Provide fallback complexity result
                complexity_result = {"complexity_level": "medium", "error": str(complexity_error)}

            # Store results in state with enhanced information
            if not state.get('intent_analysis'):
                state['intent_analysis'] = {}

            state['intent_analysis'] = {
                "intent_categories": categories,
                "complexity_assessment": complexity_result,
                "intent_parsing_reasoning": reasoning,
                "intent_parsing_output": actual_output,
            }

            logger.info(f"Intent analysis completed, ready to route to other nodes")
            return state

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            logger.error(f"Intent analysis error type: {type(e)}")
            import traceback
            logger.error(f"Intent analysis traceback: {traceback.format_exc()}")
            state['error'] = f"Intent analysis failed: {e}"
            return state

    async def _meta_architect_flow_node(self, state: MiningState) -> MiningState:
        """Meta architect flow for complex requests with enhanced context utilization"""
        try:
            logger.debug("Executing enhanced meta architect flow node")

            # Extract entities and keywords using intent_parser
            entities_keywords = self.intent_parser.extract_entities_and_keywords(state.get('user_input'))
            logger.debug(f"Extracted entities and keywords: {entities_keywords}")

            # Prepare comprehensive data for meta_architect with flattened requirements
            requirements = {
                "demand_state": state.get('demand_state'),
                "smart_analysis": state.get('smart_analysis'),
                "intent_categories": state.get('intent_analysis', {}).get("intent_categories", []),
                "intent_parsing_reasoning": state.get('intent_analysis', {}).get("intent_parsing_reasoning", ""),
                "intent_parsing_output": state.get('intent_analysis', {}).get("intent_parsing_output", ""),
                "complexity": state.get('intent_analysis', {}).get("complexity_assessment", {}).get("complexity_level", "medium"),
                "entities_keywords": entities_keywords,
                "clarification_history": self._extract_clarification_history(state),
                "has_enhanced_context": True
            }

            task_data = {
                "problem_description": state.get('user_input'),
                "domain": state.get('context').domain,
                "requirements": requirements,
                "task_type": "detailed_blueprint_construction"
            }

            # Prepare context for meta architect
            context = state.get('context')
            architect_context = {
                "task_id": f"{context.task_id}_meta_architect",
                "timestamp": self._get_current_timestamp(),
                "domain": context.domain,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "enhanced_context": True  # Flag for enhanced context usage
            }

            # Call meta_architect for detailed planning with enhanced context
            architect_result = await self.meta_architect.execute_task(task_data, architect_context)
            logger.debug(f"Enhanced meta architect result: {architect_result}")

            # Log context utilization for debugging
            if "validation_feedback" in architect_result:
                validation = architect_result["validation_feedback"]
                logger.info(f"Meta architect context validation score: {validation.get('score', 0.0)}")
                if validation.get("issues"):
                    logger.warning(f"Context validation issues: {validation['issues']}")

            # Set feedback type for unified handling
            state['feedback_type'] = "meta_architect_confirmation"

            # Store results in state
            if not state.get('meta_architect_result'):
                state['meta_architect_result'] = {}

            state['meta_architect_result'] = {
                "architect_output": architect_result,
                "entities_keywords": entities_keywords
            }

            # Add message for user confirmation
            if not state.get('messages'):
                state['messages'] = []

            # Create a message with the blueprint summary for user confirmation
            summary = self._create_blueprint_summary(architect_result)
            content = (f"I have generated a detailed blueprint: {summary}. "
                      f"Meta architect output includes: {architect_result}. "
                      f"Do you confirm to proceed, or would you like to provide feedback for adjustments?")

            # DEBUG_MINING: Log the content for debugging
            logger.debug(f"Meta architect confirmation content: {content}")

            state['messages'].append({
                "role": "assistant",
                "content": content
            })

            logger.info("Meta architect flow completed")
            return state

        except Exception as e:
            logger.error(f"Meta architect flow failed: {e}")
            state['error'] = f"Meta architect flow failed: {e}"
            return state

    async def _generate_roadmap_node(self, state: MiningState) -> MiningState:
        """Generate execution roadmap from confirmed meta architect blueprint"""
        try:
            logger.debug("Executing generate roadmap node")

            # Get the confirmed architect result
            architect_result = state.get('meta_architect_result', {}).get("architect_output", {})

            # Generate execution roadmap from meta_architect
            roadmap_task_data = {
                "architect_result": architect_result,
                "problem_description": state.get('user_input'),
                "task_type": "generate_execution_roadmap"
            }
            context = state.get('context')
            roadmap_context = {
                "task_id": f"{context.task_id}_roadmap",
                "timestamp": self._get_current_timestamp(),
                "domain": context.domain,
                "user_id": context.user_id,
                "session_id": context.session_id
            }
            roadmap_result = await self.meta_architect.execute_task(roadmap_task_data, roadmap_context)

            # DEBUG_MINING: Log the roadmap result for debugging
            logger.debug(f"Generated roadmap result: {roadmap_result}")

            # Update meta_architect_result with roadmap
            state.get('meta_architect_result', {})["execution_roadmap"] = roadmap_result

            logger.info("Roadmap generation completed")
            return state

        except Exception as e:
            logger.error(f"Roadmap generation failed: {e}")
            state['error'] = f"Roadmap generation failed: {e}"
            return state

    async def _simple_strategy_flow_node(self, state: MiningState) -> MiningState:
        """Simple strategy flow for simpler requests"""
        try:
            logger.debug("Executing simple strategy flow node")

            # Call classify_question_type
            question_type_result = self.intent_parser.classify_question_type(state.get('user_input'))
            logger.debug(f"Question type classification: {question_type_result}")

            # Call suggest_execution_strategy
            intent_analysis = state.get('intent_analysis') or {}
            categories = intent_analysis.get("intent_categories", [])
            complexity_assessment = intent_analysis.get("complexity_assessment", {})

            # Call suggest_execution_strategy method
            execution_strategy = self.intent_parser.suggest_execution_strategy(categories, complexity_assessment)
            logger.debug(f"Execution strategy: {execution_strategy}")

            # Set feedback type for unified handling
            state['feedback_type'] = "simple_strategy_confirmation"

            # Store results in state
            if not state.get('simple_strategy_result'):
                state['simple_strategy_result'] = {}

            state['simple_strategy_result'] = {
                "question_type": question_type_result,
                "execution_strategy": execution_strategy,
                "intent_categories": categories,
                "complexity_assessment": complexity_assessment,
                "intent_parsing_reasoning": intent_analysis.get("intent_parsing_reasoning", ""),
                "intent_parsing_output": intent_analysis.get("intent_parsing_output", ""),
            }

            # Add message for user confirmation
            if not state.get('messages'):
                state['messages'] = []

            # Create a message with the proposed strategy for user confirmation
            strategy = execution_strategy or {}
            content = (f"Proposed plan: {strategy.get('execution_mode', 'standard')}. "
                      f"This involves these agent roles: {strategy.get('agent_requirements', [])}. "
                      f"Intent parsing reasoning: {intent_analysis.get('intent_parsing_reasoning', '')}. "
                      f"Intent parsing output: {intent_analysis.get('intent_parsing_output', '')}. "
                      f"Do you want to proceed or suggest adjustments?")

            # DEBUG_MINING: Log the content for debugging
            logger.debug(f"Simple strategy confirmation content: {content}")

            state['messages'].append({
                "role": "assistant",
                "content": content
            })

            logger.info("Simple strategy flow completed")
            return state

        except Exception as e:
            logger.error(f"Simple strategy flow failed: {e}")
            state['error'] = f"Simple strategy flow failed: {e}"
            return state

    async def _package_results_node(self, state: MiningState) -> MiningState:
        """Package results for final output and workflow planning"""
        try:
            logger.debug("Executing package results node")

            # Prepare data for packaging based on which flow was executed
            meta_architect_result = state.get('meta_architect_result')
            if meta_architect_result:
                # Complex flow - prepare meta architect results for workflow planning
                summary_data = {
                    "flow_type": "meta_architect",
                    "architect_output": meta_architect_result.get("architect_output"),
                    "execution_roadmap": meta_architect_result.get("execution_roadmap"),
                    "entities_keywords": meta_architect_result.get("entities_keywords"),
                    "original_input": state.get('user_input'),
                    "demand_state": state.get('demand_state'),
                    "smart_analysis": state.get('smart_analysis'),
                    "intent_analysis": state.get('intent_analysis') or {}
                }
            else:
                # Simple flow - prepare strategy results for workflow planning
                simple_strategy_result = state.get('simple_strategy_result') or {}

                summary_data = {
                    "flow_type": "simple_strategy",
                    "question_type": simple_strategy_result.get("question_type"),
                    "execution_strategy": simple_strategy_result.get("execution_strategy"),
                    "intent_categories": simple_strategy_result.get("intent_categories"),
                    "complexity_assessment": simple_strategy_result.get("complexity_assessment"),
                    "original_input": state.get('user_input'),
                    "demand_state": state.get('demand_state'),
                    "smart_analysis": state.get('smart_analysis'),
                    "intent_analysis": state.get('intent_analysis') or {}
                }

            # DEBUG_MINING: Log the summary data for debugging
            logger.debug(f"Package results summary data: {summary_data}")

            # Store packaged data for workflow planning
            if not state.get('summarizer_result'):
                state['summarizer_result'] = {}

            state['summarizer_result'] = {
                "summary_data": summary_data,
                "ready_for_workflow_planning": True,
                "user_feedback_processed": True
            }

            # Add final message
            if not state.get('messages'):
                state['messages'] = []

            if summary_data["flow_type"] == "meta_architect":
                state['messages'].append({
                    "role": "assistant",
                    "content": f"Complex request analysis completed with user confirmation. Detailed blueprint and roadmap ready for workflow planning."
                })
            else:
                execution_mode = summary_data.get("execution_strategy", {}).get("execution_mode", "standard")
                state['messages'].append({
                    "role": "assistant",
                    "content": f"Request analysis completed with user confirmation. Ready for workflow planning with {execution_mode} execution mode."
                })

            logger.info(f"Package results completed: {summary_data['flow_type']}")
            return state

        except Exception as e:
            logger.error(f"Package results failed: {e}")
            state['error'] = f"Package results failed: {e}"
            return state

    async def _finalize_result_node(self, state: MiningState) -> MiningState:
        """Finalize the mining result"""
        try:
            logger.debug("Executing result finalization node")

            # DEBUG_MINING: Check state before finalization
            logger.debug(f"DEBUG_MINING: Final state demand_state = {state.get('demand_state')}")
            logger.debug(f"DEBUG_MINING: Final state smart_analysis = {state.get('smart_analysis')}")

            # Make sure the key field is not None
            if state.get('demand_state') is None:
                logger.error("DEBUG_MINING: CRITICAL - demand_state is None in final state!")
                # Try to recover from smart_analysis
                smart_analysis = state.get('smart_analysis')
                if smart_analysis and isinstance(smart_analysis, dict):
                    recovered_demand_state = smart_analysis.get('demand_state')
                    if recovered_demand_state:
                        logger.warning(f"DEBUG_MINING: Recovered demand_state from smart_analysis: {recovered_demand_state}")
                        state['demand_state'] = recovered_demand_state
                    else:
                        logger.error("DEBUG_MINING: Cannot recover demand_state, using fallback")
                        state['demand_state'] = "SMART_LARGE_SCOPE"
                else:
                    logger.error("DEBUG_MINING: smart_analysis is also invalid, using fallback")
                    state['demand_state'] = "SMART_LARGE_SCOPE"

            # Mark as completed only if not waiting for feedback
            if not state.get('status') or state.get('status') != "waiting_for_user_feedback":
                state['completed'] = True

            # Add final message
            if not state.get('messages'):
                state['messages'] = []

            state['messages'].append({
                "role": "assistant",
                "content": "Mining process completed successfully. Analysis is ready for workflow planning."
            })

            logger.debug(f"DEBUG_MINING: Final state after fixes - demand_state = {state['demand_state']}")
            logger.info("Mining result finalized")
            return state

        except Exception as e:
            logger.error(f"Result finalization failed: {e}")
            state['error'] = f"Result finalization failed: {e}"
            return state

    def _route_after_analysis(self, state: MiningState) -> str:
        """Route after demand analysis based on demand state"""
        if state.get('error'):
            return "error"

        # Normal routing based on demand state
        demand_state = state.get('demand_state')
        if demand_state == DemandState.SMART_COMPLIANT.value:
            logger.info("Demand is SMART_COMPLIANT - routing to intent analysis")
            return "intent_analysis"
        elif demand_state in [DemandState.VAGUE_UNCLEAR.value, DemandState.SMART_LARGE_SCOPE.value]:
            logger.info(f"Demand state is {demand_state} - routing to clarify")
            return "clarify"
        else:
            logger.warning(f"Unknown demand state: {demand_state} - routing to error")
            return "error"

    def _route_after_intent_analysis(self, state: MiningState) -> str:
        """Route after intent analysis based on complexity and categories"""
        if state.get('error'):
            return "error"

        try:
            # Get intent analysis results
            intent_analysis = state.get('intent_analysis', {})
            categories = intent_analysis.get("intent_categories", [])
            complexity_assessment = intent_analysis.get("complexity_assessment", {})

            complexity_level = complexity_assessment.get("complexity_level", "low")

            # Check if intent parsing result contains collect, process, analyze, generate (any 2 or more)
            target_categories = {"collect", "process", "analyze", "generate"}
            matching_categories = set(categories) & target_categories
            has_multiple_complex_categories = len(matching_categories) >= 2

            # Check if complexity is medium or high
            is_medium_or_high_complexity = complexity_level in ["medium", "high"]

            logger.debug(f"Intent routing: categories={categories}, matching={matching_categories}, "
                        f"complexity={complexity_level}, has_multiple={has_multiple_complex_categories}, "
                        f"is_medium_high={is_medium_or_high_complexity}")

            # Route to meta_architect if both conditions are met
            if has_multiple_complex_categories and is_medium_or_high_complexity:
                logger.info("Routing to meta_architect flow for complex request")
                return "meta_architect"
            else:
                logger.info("Routing to simple strategy flow")
                return "simple_strategy"

        except Exception as e:
            logger.error(f"Error in intent analysis routing: {e}")
            return "simple_strategy"  # Default to simple strategy on error

    def _route_after_adjustment(self, state: MiningState) -> str:
        """Route after adjustment processing based on original feedback type"""
        try:
            feedback_type = state.get('feedback_type')

            if feedback_type == "simple_strategy_confirmation":
                logger.info("Routing to intent_analysis after simple strategy adjustment")
                return "intent_analysis"
            elif feedback_type == "meta_architect_confirmation":
                logger.info("Routing to meta_architect_flow after meta architect adjustment")
                return "meta_architect_flow"
            else:
                logger.warning(f"Unknown feedback type for adjustment routing: {feedback_type}")
                return "intent_analysis"  # Default fallback

        except Exception as e:
            logger.error(f"Error in adjustment routing: {e}")
            return "error"

    def _route_after_clarification(self, state: MiningState) -> str:
        """
        Routes after the clarification node. If the state was forced to be
        compliant (due to max rounds), it goes to intent analysis.
        Otherwise, it proceeds to pause and wait for user feedback.
        """
        try:
            if state.get('error'):
                return "error"

            context = state.get('context')

            # Check if we've reached max clarifications and been forced to proceed
            if context and context.current_round >= 3 and state.get('demand_state') == DemandState.SMART_COMPLIANT.value:
                logger.info("Demand state forced to compliant due to max clarifications, routing to intent analysis.")
                return "intent_analysis"
            else:
                logger.info("Demand state still requires clarification, routing to wait for user feedback.")
                return "wait_for_user_feedback"

        except Exception as e:
            logger.error(f"Error in clarification routing: {e}")
            return "wait_for_user_feedback"  # Default fallback

    async def _generate_clarification_questions(self, state: MiningState) -> List[str]:
        """Generate clarification questions for vague requirements"""
        # Default clarification questions based on SMART criteria
        questions = []

        smart_analysis = state.get('smart_analysis') or {}
        smart_criteria = smart_analysis.get("smart_analysis", {})

        if not smart_criteria.get("specific"):
            questions.append("Could you provide more specific details about what you want to achieve?")

        if not smart_criteria.get("measurable"):
            questions.append("What specific measurable metrics or outcomes would indicate success?")

        if not smart_criteria.get("time_bound"):
            questions.append("What is your desired timeframe for this request?")

        if not smart_criteria.get("relevant"):
            questions.append("What is the context or purpose behind this request?")

        # Add domain-specific questions if needed
        context = state.get('context')
        if context and context.domain != "general":
            questions.append(f"Are there any {context.domain}-specific requirements or constraints?")

        return questions or ["Could you please provide more details about your requirements?"]


    def _extract_final_requirements(self, state: MiningState) -> List[str]:
        """Extract final requirements from the mining state"""
        requirements = [state.get('user_input', "")]

        user_responses = state.get('user_responses')
        if user_responses:
            requirements.extend(user_responses)

        # Add requirements from intent analysis
        intent_analysis = state.get('intent_analysis')
        if intent_analysis:
            categories = intent_analysis.get("intent_categories", [])
            if categories:
                requirements.append(f"Intent categories: {', '.join(categories)}")

            # Add detailed analysis information
            query_description = intent_analysis.get("query_description")
            if query_description:
                requirements.append(f"Query description: {query_description}")

            detailed_reasoning = intent_analysis.get("detailed_reasoning")
            if detailed_reasoning:
                requirements.append(f"Analysis reasoning: {detailed_reasoning}")

            primary_intent = intent_analysis.get("primary_intent")
            if primary_intent:
                requirements.append(f"Primary intent: {primary_intent}")

            # Add step-by-step breakdown
            sub_steps = intent_analysis.get("sub_steps_identified", [])
            if sub_steps:
                step_descriptions = []
                for step in sub_steps:
                    step_name = step.get("step_name", "")
                    step_desc = step.get("description", "")
                    step_purpose = step.get("purpose", "")
                    if step_name and step_desc:
                        step_descriptions.append(f"{step_name}: {step_desc} (Purpose: {step_purpose})")
                if step_descriptions:
                    requirements.append(f"Detailed steps: {'; '.join(step_descriptions)}")

            complexity = intent_analysis.get("complexity_assessment", {}).get("complexity_level")
            if complexity:
                requirements.append(f"Complexity level: {complexity}")

        # Add requirements from meta architect or simple strategy results
        meta_architect_result = state.get('meta_architect_result')
        if meta_architect_result:
            architect_output = meta_architect_result.get("architect_output", {})
            if architect_output.get("problem_analysis"):
                requirements.append(f"Strategic analysis: {architect_output['problem_analysis']}")
        else:
            simple_strategy_result = state.get('simple_strategy_result')
            if simple_strategy_result:
                strategy = simple_strategy_result.get("execution_strategy", {})
                if strategy.get("execution_mode"):
                    requirements.append(f"Execution mode: {strategy['execution_mode']}")

        return requirements

    def _extract_clarification_history(self, state: MiningState) -> List[Dict[str, str]]:
        """Extract clarification history from the mining state"""
        history = []

        messages = state.get('messages')
        if messages:
            for i, message in enumerate(messages):
                # Check if message is an AIMessage object or dictionary
                if hasattr(message, 'content'):
                    # AIMessage object - access attributes directly
                    content = getattr(message, 'content', '')
                    if "Clarification needed" in content:
                        history.append({
                            "round": str((i // 2) + 1),
                            "question": content,
                            "response": "User response simulated"  # In real implementation, would be actual user response
                        })
                elif isinstance(message, dict):
                    # Dictionary format - use .get() method
                    if message.get("role") == "assistant" and "Clarification needed" in message.get("content", ""):
                        history.append({
                            "round": str((i // 2) + 1),
                            "question": message.get("content", ""),
                            "response": "User response simulated"  # In real implementation, would be actual user response
                        })

        return history

    def _get_current_time_ms(self) -> float:
        """Get current time in milliseconds"""
        import time
        return time.time() * 1000

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        import datetime
        return datetime.datetime.now().isoformat()

    def _update_metrics(self, success: bool, clarification_rounds: int) -> None:
        """Update service metrics"""
        self._total_mining_operations += 1

        if success:
            self._successful_operations += 1

            # Update average clarification rounds
            self._average_clarification_rounds = (
                (self._average_clarification_rounds * (self._successful_operations - 1) + clarification_rounds) /
                self._successful_operations
            )

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get service-level metrics"""
        return {
            "total_mining_operations": self._total_mining_operations,
            "successful_operations": self._successful_operations,
            "success_rate": self._successful_operations / max(self._total_mining_operations, 1),
            "average_clarification_rounds": self._average_clarification_rounds,
            "intent_parser_status": "available" if self.intent_parser.is_available() else "busy",
            "meta_architect_status": "available" if self.meta_architect.is_available() else "busy",
            "framework": "langgraph_with_agents"
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service and agents.

        Returns:
            Health check result
        """
        try:
            health_status = {
                "service_status": "healthy",
                "intent_parser_status": "available" if self.intent_parser.is_available() else "busy",
                "meta_architect_status": "available" if self.meta_architect.is_available() else "busy",
                "workflow_initialized": self.workflow is not None,
                "config_manager_available": self.config_manager is not None,
                "llm_manager_available": self.llm_manager is not None,
                "metrics": self.get_service_metrics()
            }

            # Check agent capabilities
            try:
                intent_capabilities = self.intent_parser.get_capabilities()
                meta_capabilities = self.meta_architect.get_capabilities()
                health_status["agent_capabilities"] = {
                    "intent_parser": intent_capabilities,
                    "meta_architect": meta_capabilities
                }
            except Exception as e:
                health_status["agent_capabilities_error"] = str(e)

            return health_status

        except Exception as e:
            logger.error(f"Health check failed with an internal error: {e}", exc_info=True)
            return {
                "service_status": "unhealthy",
                "error": str(e),
                "timestamp": self._get_current_timestamp()
            }

    def _infer_demand_state_from_analysis(self, smart_analysis: Optional[Dict[str, Any]], user_input: str) -> Optional[str]:
        """
        从 smart_analysis 的其他字段推断 demand_state
        """
        if not smart_analysis:
            return None

        # Try to infer from the smart_analysis subfield
        smart_criteria = smart_analysis.get("smart_analysis", {})
        if isinstance(smart_criteria, dict):
            # Calculate the number of SMART criteria met
            criteria_met = sum(1 for v in smart_criteria.values() if v is True)

            if criteria_met >= 4:
                # Inspection scope assessment
                scope_assessment = smart_analysis.get("scope_assessment", {})
                if scope_assessment.get("complexity") == "high" or scope_assessment.get("domain_breadth") == "broad":
                    return "SMART_LARGE_SCOPE"
                else:
                    return "SMART_COMPLIANT"
            else:
                return "VAGUE_UNCLEAR"

        return None

    def _get_fallback_demand_state(self, user_input: str) -> str:
        """
        Get the fallback demand_state and make sure it never returns None
        """
        text_lower = user_input.lower()

        # Check time indicators
        time_indicators = ["2024", "2025", "q1", "q2", "q3", "q4", "quarter", "year", "month", "week"]
        has_time = any(indicator in text_lower for indicator in time_indicators)

        # Check specific indicator words
        specific_indicators = ["analyze", "compare", "performance", "financial", "revenue", "profit", "growth"]
        has_specific = any(indicator in text_lower for indicator in specific_indicators)

        # Checking Fuzzy Indicators - More Accurate Fuzzy Judgments
        vague_indicators = ["help me", "give me", "please help", "can you", "could you"]
        has_vague = any(indicator in text_lower for indicator in vague_indicators)

        # More precise classification logic
        word_count = len(user_input.split())

        # Determine demand_state - Priority: Explicit fuzzy indicator > Specific + time > Specific indicator > Default
        if has_vague:
            return "VAGUE_UNCLEAR"
        elif word_count < 4:
            return "VAGUE_UNCLEAR"
        elif has_specific and has_time:
            # There are specific and temporal indicators
            if word_count <= 25:
                return "SMART_COMPLIANT"
            else:
                return "SMART_LARGE_SCOPE"
        elif has_specific:
            # There are specific indicators but no time
            return "SMART_COMPLIANT"
        else:
            # Default
            return "SMART_LARGE_SCOPE"


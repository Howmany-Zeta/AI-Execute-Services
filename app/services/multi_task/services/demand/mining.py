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

# Import system components
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.agent.system.intent_parser import IntentParserAgent
from app.services.multi_task.agent.domain.meta_architect import MetaArchitectAgent
from app.services.multi_task.services.interacter.interacter import InteracterService
from app.services.multi_task.core.models.agent_models import AgentConfig, AgentRole
from app.services.multi_task.core.models.services_models import (
    DemandState, MiningContext, MiningState, MiningResult
)
from app.services.multi_task.core.exceptions.services_exceptions import MiningError
from app.services.multi_task.config.config_manager import ConfigManager

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

        # Initialize agents
        self._init_agents()

        # Initialize langgraph workflow
        self._init_workflow()

        # Performance tracking
        self._total_mining_operations = 0
        self._successful_operations = 0
        self._average_clarification_rounds = 0.0

        logger.info("MiningService initialized with langgraph workflow")

    def _init_agents(self) -> None:
        """Initialize intent parser, meta architect, and interacter agents"""
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

        # Initialize agents
        self.intent_parser = IntentParserAgent(
            config=intent_parser_config,
            config_manager=self.config_manager,
            llm_manager=self.llm_manager
        )

        self.meta_architect = MetaArchitectAgent(
            config=meta_architect_config,
            config_manager=self.config_manager,
            llm_manager=self.llm_manager
        )

        # Initialize Interacter for demand state analysis
        self.interacter = InteracterService(
            llm_manager=self.llm_manager
        )

    def _init_workflow(self) -> None:
        """Initialize langgraph workflow for mining process"""
        # Create state graph
        workflow = StateGraph(MiningState)

        # Add nodes
        workflow.add_node("analyze_demand", self._analyze_demand_node)
        workflow.add_node("intent_analysis", self._intent_analysis_node)
        workflow.add_node("meta_architect_flow", self._meta_architect_flow_node)
        workflow.add_node("simple_strategy_flow", self._simple_strategy_flow_node)
        workflow.add_node("summarizer_flow", self._summarizer_flow_node)
        workflow.add_node("clarify_requirements", self._clarify_requirements_node)
        workflow.add_node("finalize_result", self._finalize_result_node)

        # Set entry point
        workflow.set_entry_point("analyze_demand")

        # Add conditional edges
        workflow.add_conditional_edges(
            "analyze_demand",
            self._route_after_analysis,
            {
                "intent_analysis": "intent_analysis",
                "clarify": "clarify_requirements",
                "error": END
            }
        )

        workflow.add_conditional_edges(
            "intent_analysis",
            self._route_after_intent_analysis,
            {
                "meta_architect": "meta_architect_flow",
                "simple_strategy": "simple_strategy_flow",
                "error": END
            }
        )

        workflow.add_edge("meta_architect_flow", "summarizer_flow")
        workflow.add_edge("simple_strategy_flow", "summarizer_flow")
        workflow.add_edge("summarizer_flow", "finalize_result")

        workflow.add_conditional_edges(
            "clarify_requirements",
            self._route_after_clarification,
            {
                "continue_clarify": "clarify_requirements",
                "intent_analysis": "intent_analysis",
                "error": END
            }
        )

        workflow.add_edge("finalize_result", END)

        # Compile the workflow
        self.workflow = workflow.compile()

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
            user_input: User input text to analyze
            context: Mining context with metadata

        Returns:
            Mining result with requirements and blueprint

        Raises:
            Exception: If mining process fails
        """
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
            final_state = await self.workflow.ainvoke(initial_state)

            # Check for errors
            if getattr(final_state, 'error', None):
                raise Exception(f"Mining workflow failed: {getattr(final_state, 'error', 'Unknown error')}")

            # Calculate processing time
            processing_time = self._get_current_time_ms() - start_time

            # Create result
            result = MiningResult(
                original_input=user_input,
                final_requirements=self._extract_final_requirements(final_state),
                demand_state=final_state.get("demand_state"),  # Use .get() for dictionaries
                smart_analysis=final_state.get("smart_analysis") or {}, # Use .get()
                clarification_history=self._extract_clarification_history(final_state),
                processing_time_ms=processing_time
            )

            # Update metrics
            self._update_metrics(True, context.current_round)

            logger.info(f"Successfully completed mining process: {getattr(final_state, 'demand_state', None)}")
            return result

        except Exception as e:
            self._update_metrics(False, 0)
            logger.error(f"Mining process failed: {e}")
            raise Exception(f"Mining process failed: {e}")

    async def _analyze_demand_node(self, state: MiningState) -> MiningState:
        """Analyze user demand using intent parser with SMART criteria"""
        try:
            logger.debug("Executing demand analysis node")

            # Prepare context for intent parser
            analysis_context = {
                "task_id": state.context.task_id,
                "timestamp": state.context.timestamp or self._get_current_timestamp(),
                "domain": state.context.domain,
                "user_id": state.context.user_id,
                "session_id": state.context.session_id
            }

            # DEBUG_MINING: Interacter input debugging
            logger.debug(f"DEBUG_MINING: Interacter input - user_input: {state.user_input}")
            logger.debug(f"DEBUG_MINING: Interacter input - analysis_context: {analysis_context}")

            # Analyze demand state using Interacter
            smart_analysis = await self.interacter.analyze_demand_state(
                state.user_input, analysis_context
            )

            # DEBUG_MINING: Interacter output debugging
            logger.debug(f"DEBUG_MINING: Interacter raw output: {smart_analysis}")
            logger.debug(f"DEBUG_MINING: Interacter output type: {type(smart_analysis)}")
            if isinstance(smart_analysis, dict):
                logger.debug(f"DEBUG_MINING: Interacter output keys: {list(smart_analysis.keys())}")
                for key in ['demand_state', 'smart_analysis', 'confidence', 'reasoning']:
                    value = smart_analysis.get(key)
                    logger.debug(f"DEBUG_MINING: smart_analysis['{key}'] = {value} (type: {type(value)})")

            # 增强的 demand_state 提取逻辑
            demand_state = smart_analysis.get("demand_state") if smart_analysis else None
            logger.debug(f"DEBUG_MINING: Extracted demand_state = {demand_state}")

            # 如果 demand_state 为 None，尝试从其他字段推断
            if demand_state is None:
                logger.warning("DEBUG_MINING: demand_state is None, attempting to infer from smart_analysis")
                demand_state = self._infer_demand_state_from_analysis(smart_analysis, state.user_input)
                logger.debug(f"DEBUG_MINING: Inferred demand_state = {demand_state}")

            # 最后的保护：如果仍然为 None，使用默认值
            if demand_state is None:
                logger.error("DEBUG_MINING: Failed to determine demand_state, using fallback")
                demand_state = self._get_fallback_demand_state(state.user_input)
                logger.debug(f"DEBUG_MINING: Fallback demand_state = {demand_state}")

            # 确保 demand_state 不为 None
            if demand_state is None:
                logger.critical("DEBUG_MINING: CRITICAL - demand_state is still None after all fallbacks!")
                demand_state = "SMART_LARGE_SCOPE"  # 硬编码最后的保护
                logger.debug(f"DEBUG_MINING: Hard-coded demand_state = {demand_state}")

            # Update state
            state.demand_state = demand_state
            state.smart_analysis = smart_analysis or {}
            state.clarification_questions = smart_analysis.get("clarification_needed", []) if smart_analysis else []

            logger.info(f"Demand analysis completed: {state.demand_state}")
            return state

        except Exception as e:
            logger.error(f"Demand analysis failed: {e}")
            # 即使出错也要设置一个有效的 demand_state
            state.demand_state = self._get_fallback_demand_state(state.user_input)
            state.smart_analysis = {"error": str(e)}
            state.error = f"Demand analysis failed: {e}"
            return state

    async def _clarify_requirements_node(self, state: MiningState) -> MiningState:
        """Handle multi-round clarification for unclear requirements"""
        try:
            logger.debug(f"Executing clarification node (round {state.context.current_round + 1})")

            # Check if we've exceeded max rounds
            if state.context.current_round >= state.context.max_clarification_rounds:
                logger.warning("Maximum clarification rounds reached")
                state.error = "Maximum clarification rounds exceeded"
                return state

            # Generate clarification questions if not already present
            if not state.clarification_questions:
                state.clarification_questions = await self._generate_clarification_questions(state)

            # In a real implementation, this would interact with the user
            # For now, we'll simulate user responses or mark as needing user input
            state.context.current_round += 1

            # Add message for clarification
            if not state.messages:
                state.messages = []

            state.messages.append({
                "role": "assistant",
                "content": f"Clarification needed (Round {state.context.current_round}): {'; '.join(state.clarification_questions)}"
            })

            logger.info(f"Clarification round {state.context.current_round} completed")
            return state

        except Exception as e:
            logger.error(f"Clarification failed: {e}")
            state.error = f"Clarification failed: {e}"
            return state


    async def _intent_analysis_node(self, state: MiningState) -> MiningState:
        """Intent analysis node - calls executeTask and assess_request_complexity"""
        try:
            logger.debug("Executing intent analysis node")

            # Prepare context for intent parser
            analysis_context = {
                "task_id": f"{state.context.task_id}_intent",
                "timestamp": state.context.timestamp or self._get_current_timestamp(),
                "domain": state.context.domain,
                "user_id": state.context.user_id,
                "session_id": state.context.session_id
            }

            # Prepare task data for executeTask
            task_data = {
                "text": state.user_input,
                "analysis_type": "intent_parsing"
            }

            # Call Intent_parser's executeTask for intent parsing
            intent_result = await self.intent_parser.execute_task(task_data, analysis_context)
            logger.debug(f"Intent parsing result: {intent_result}")

            # Extract categories from intent result
            categories = intent_result.get("categories", [])

            # Extract the new intent result data
            reasoning = intent_result.get("reasoning", "")
            actual_output = intent_result.get("actual_output", "")

            # Call assess_request_complexity
            complexity_result = self.intent_parser.assess_request_complexity(state.user_input, categories)
            logger.debug(f"Complexity assessment result: {complexity_result}")

            # Store results in state with enhanced information
            if not hasattr(state, 'intent_analysis'):
                state.intent_analysis = {}

            state.intent_analysis = {
                "intent_categories": categories,
                "complexity_assessment": complexity_result,
                "intent_parsing_reasoning": reasoning,
                "intent_parsing_output": actual_output,
            }

            logger.info(f"Intent analysis completed: categories={categories}, intent_parsing_output={actual_output}, complexity={complexity_result.get('complexity_level')}")
            return state

        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            state.error = f"Intent analysis failed: {e}"
            return state

    async def _meta_architect_flow_node(self, state: MiningState) -> MiningState:
        """Meta architect flow for complex requests with enhanced context utilization"""
        try:
            logger.debug("Executing enhanced meta architect flow node")

            # Extract entities and keywords using intent_parser
            entities_keywords = self.intent_parser.extract_entities_and_keywords(state.user_input)
            logger.debug(f"Extracted entities and keywords: {entities_keywords}")

            # Prepare enhanced mining context for meta_architect
            mining_context = {
                "demand_state": state.demand_state,
                "smart_analysis": state.smart_analysis,
                "intent_parsing_reasoning": state.intent_analysis.get("intent_parsing_reasoning", ""),
                "intent_parsing_output": state.intent_analysis.get("intent_parsing_output", ""),
                "complexity": state.intent_analysis.get("complexity_assessment", {}).get("complexity_level", "medium"),
                "entities_keywords": entities_keywords,
                "analysis_focus": self._extract_analysis_focus(state.intent_analysis),
                "framework_hints": self._extract_framework_hints(entities_keywords, state.intent_analysis),
                "clarification_history": self._extract_clarification_history(state),
                "has_enhanced_context": True
            }

            # Prepare comprehensive data for meta_architect with enhanced context
            task_data = {
                "problem_description": state.user_input,
                "domain": state.context.domain,
                "requirements": mining_context,  # Add enhanced mining context
                "task_type": "detailed_blueprint_construction"
            }

            # Prepare context for meta architect
            architect_context = {
                "task_id": f"{state.context.task_id}_meta_architect",
                "timestamp": self._get_current_timestamp(),
                "domain": state.context.domain,
                "user_id": state.context.user_id,
                "session_id": state.context.session_id,
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

            # Generate execution roadmap directly from meta_architect
            roadmap_task_data = {
                "architect_result": architect_result,
                "problem_description": state.user_input,
                "task_type": "generate_execution_roadmap"
            }
            roadmap_context = {
                "task_id": f"{state.context.task_id}_roadmap",
                "timestamp": self._get_current_timestamp(),
                "domain": state.context.domain,
                "user_id": state.context.user_id,
                "session_id": state.context.session_id
            }
            roadmap_result = await self.meta_architect.execute_task(roadmap_task_data, roadmap_context)

            # Store results in state
            if not hasattr(state, 'meta_architect_result'):
                state.meta_architect_result = {}

            state.meta_architect_result = {
                "architect_output": architect_result,
                "execution_roadmap": roadmap_result,
                "entities_keywords": entities_keywords
            }

            logger.info("Meta architect flow completed")
            return state

        except Exception as e:
            logger.error(f"Meta architect flow failed: {e}")
            state.error = f"Meta architect flow failed: {e}"
            return state

    async def _simple_strategy_flow_node(self, state: MiningState) -> MiningState:
        """Simple strategy flow for simpler requests"""
        try:
            logger.debug("Executing simple strategy flow node")

            # Call classify_question_type
            question_type_result = self.intent_parser.classify_question_type(state.user_input)
            logger.debug(f"Question type classification: {question_type_result}")

            # Call suggest_execution_strategy
            intent_analysis = state.intent_analysis or {}
            categories = intent_analysis.get("intent_categories", [])
            complexity_assessment = intent_analysis.get("complexity_assessment", {})
            execution_strategy = self.intent_parser.suggest_execution_strategy(categories, complexity_assessment)
            logger.debug(f"Execution strategy: {execution_strategy}")

            # Store results in state
            if not hasattr(state, 'simple_strategy_result'):
                state.simple_strategy_result = {}

            state.simple_strategy_result = {
                "question_type": question_type_result,
                "execution_strategy": execution_strategy,
                "intent_categories": categories,
                "complexity_assessment": complexity_assessment,
                "original_intent_input": state.user_input,
                "intent_parsing_result": intent_analysis.get("intent_parsing_result", {})
            }

            logger.info("Simple strategy flow completed")
            return state

        except Exception as e:
            logger.error(f"Simple strategy flow failed: {e}")
            state.error = f"Simple strategy flow failed: {e}"
            return state

    async def _summarizer_flow_node(self, state: MiningState) -> MiningState:
        """Summarizer flow for user feedback and workflow planning"""
        try:
            logger.debug("Executing summarizer flow node")

            # Prepare data for summarizer based on which flow was executed
            if hasattr(state, 'meta_architect_result') and state.meta_architect_result:
                # Complex flow - prepare meta architect results for user feedback
                meta_architect_result = state.meta_architect_result or {}
                summary_data = {
                    "flow_type": "meta_architect",
                    "architect_output": meta_architect_result.get("architect_output"),
                    "execution_roadmap": meta_architect_result.get("execution_roadmap"),
                    "entities_keywords": meta_architect_result.get("entities_keywords"),
                    "original_input": state.user_input,
                    "demand_state": state.demand_state,
                    "smart_analysis": state.smart_analysis
                }
            else:
                # Simple flow - prepare strategy results for workflow planning
                # IF state.simple_strategy_result IS None, DEFAULT TO AN EMPTY DICTIONARY
                simple_strategy_result = state.simple_strategy_result or {}

                summary_data = {
                    "flow_type": "simple_strategy",
                    "question_type": simple_strategy_result.get("question_type"),
                    "execution_strategy": simple_strategy_result.get("execution_strategy"),
                    "intent_categories": simple_strategy_result.get("intent_categories"),
                    "complexity_assessment": simple_strategy_result.get("complexity_assessment"),
                    "original_input": state.user_input,
                    "demand_state": state.demand_state,
                    "smart_analysis": state.smart_analysis
                }

            # Store summarizer data for workflow planning
            if not hasattr(state, 'summarizer_result'):
                state.summarizer_result = {}

            state.summarizer_result = {
                "summary_data": summary_data,
                "ready_for_workflow_planning": True,
                "user_feedback_required": summary_data["flow_type"] == "meta_architect"
            }

            # Add message for user feedback or workflow planning
            if not state.messages:
                state.messages = []

            if summary_data["flow_type"] == "meta_architect":
                state.messages.append({
                    "role": "assistant",
                    "content": f"Complex request analysis completed. Detailed blueprint prepared for user review and confirmation."
                })
            else:
                state.messages.append({
                    "role": "assistant",
                    "content": f"Request analysis completed. Ready for workflow planning with {summary_data['execution_strategy']['execution_mode']} execution mode."
                })

            logger.info(f"Summarizer flow completed: {summary_data['flow_type']}")
            return state

        except Exception as e:
            logger.error(f"Summarizer flow failed: {e}")
            state.error = f"Summarizer flow failed: {e}"
            return state

    async def _finalize_result_node(self, state: MiningState) -> MiningState:
        """Finalize the mining result"""
        try:
            logger.debug("Executing result finalization node")

            # DEBUG_MINING: Check state before finalization
            logger.debug(f"DEBUG_MINING: Final state demand_state = {state.demand_state}")
            logger.debug(f"DEBUG_MINING: Final state smart_analysis = {state.smart_analysis}")

            # 确保关键字段不为 None
            if state.demand_state is None:
                logger.error("DEBUG_MINING: CRITICAL - demand_state is None in final state!")
                # 尝试从 smart_analysis 中恢复
                if state.smart_analysis and isinstance(state.smart_analysis, dict):
                    recovered_demand_state = state.smart_analysis.get('demand_state')
                    if recovered_demand_state:
                        logger.warning(f"DEBUG_MINING: Recovered demand_state from smart_analysis: {recovered_demand_state}")
                        state.demand_state = recovered_demand_state
                    else:
                        logger.error("DEBUG_MINING: Cannot recover demand_state, using fallback")
                        state.demand_state = "SMART_LARGE_SCOPE"
                else:
                    logger.error("DEBUG_MINING: smart_analysis is also invalid, using fallback")
                    state.demand_state = "SMART_LARGE_SCOPE"

            # Mark as completed
            state.completed = True

            # Add final message
            if not state.messages:
                state.messages = []

            state.messages.append({
                "role": "assistant",
                "content": "Mining process completed successfully. Analysis is ready for workflow planning."
            })

            logger.debug(f"DEBUG_MINING: Final state after fixes - demand_state = {state.demand_state}")
            logger.info("Mining result finalized")
            return state

        except Exception as e:
            logger.error(f"Result finalization failed: {e}")
            state.error = f"Result finalization failed: {e}"
            return state

    def _route_after_analysis(self, state: MiningState) -> str:
        """Route after demand analysis based on demand state"""
        if state.error:
            return "error"

        if state.demand_state == DemandState.VAGUE_UNCLEAR.value:
            return "clarify"
        elif state.demand_state in [DemandState.SMART_COMPLIANT.value, DemandState.SMART_LARGE_SCOPE.value]:
            # For SMART_COMPLIANT and SMART_LARGE_SCOPE, enter intent analysis flow
            return "intent_analysis"
        else:
            return "error"

    def _route_after_intent_analysis(self, state: MiningState) -> str:
        """Route after intent analysis based on complexity and categories"""
        if state.error:
            return "error"

        try:
            # Get intent analysis results
            intent_analysis = getattr(state, 'intent_analysis', {})
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

    def _route_after_clarification(self, state: MiningState) -> str:
        """Route after clarification based on current state"""
        if state.error:
            return "error"

        # Check if we need more clarification
        if (state.context.current_round < state.context.max_clarification_rounds and
            state.demand_state == DemandState.VAGUE_UNCLEAR.value):
            return "continue_clarify"
        else:
            # If demand state is still VAGUE_UNCLEAR after max clarification rounds,
            # we should NOT proceed to intent analysis as the requirements are still unclear
            if state.demand_state == DemandState.VAGUE_UNCLEAR.value:
                logger.warning(f"Requirements still unclear after {state.context.current_round} clarification rounds")
                state.error = "Requirements remain unclear after maximum clarification attempts"
                return "error"
            else:
                # Only proceed to intent analysis if demand state is clear
                return "intent_analysis"


    async def _generate_clarification_questions(self, state: MiningState) -> List[str]:
        """Generate clarification questions for vague requirements"""
        # Default clarification questions based on SMART criteria
        questions = []

        smart_analysis = state.smart_analysis or {}
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
        if state.context.domain != "general":
            questions.append(f"Are there any {state.context.domain}-specific requirements or constraints?")

        return questions or ["Could you please provide more details about your requirements?"]


    def _extract_final_requirements(self, state: MiningState) -> List[str]:
        """Extract final requirements from the mining state"""
        requirements = [getattr(state, 'user_input', "")]

        user_responses = getattr(state, 'user_responses', None)
        if user_responses:
            requirements.extend(user_responses)

        # Add requirements from intent analysis
        intent_analysis = getattr(state, 'intent_analysis', None)
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
        if hasattr(state, 'meta_architect_result') and state.meta_architect_result:
            architect_output = state.meta_architect_result.get("architect_output", {})
            if architect_output.get("problem_analysis"):
                requirements.append(f"Strategic analysis: {architect_output['problem_analysis']}")
        elif hasattr(state, 'simple_strategy_result') and state.simple_strategy_result:
            strategy = state.simple_strategy_result.get("execution_strategy", {})
            if strategy.get("execution_mode"):
                requirements.append(f"Execution mode: {strategy['execution_mode']}")

        return requirements

    def _extract_clarification_history(self, state: MiningState) -> List[Dict[str, str]]:
        """Extract clarification history from the mining state"""
        history = []

        messages = getattr(state, 'messages', None)
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

        # 尝试从 smart_analysis 子字段推断
        smart_criteria = smart_analysis.get("smart_analysis", {})
        if isinstance(smart_criteria, dict):
            # 计算满足的 SMART 标准数量
            criteria_met = sum(1 for v in smart_criteria.values() if v is True)

            if criteria_met >= 4:
                # 检查范围评估
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
        获取 fallback demand_state，确保永远不返回 None
        """
        text_lower = user_input.lower()

        # 检查时间指示词
        time_indicators = ["2024", "2025", "q1", "q2", "q3", "q4", "quarter", "year", "month", "week"]
        has_time = any(indicator in text_lower for indicator in time_indicators)

        # 检查具体指示词
        specific_indicators = ["analyze", "compare", "performance", "financial", "revenue", "profit", "growth"]
        has_specific = any(indicator in text_lower for indicator in specific_indicators)

        # 检查模糊指示词 - 更精确的模糊判断
        vague_indicators = ["help me", "give me", "please help", "can you", "could you"]
        has_vague = any(indicator in text_lower for indicator in vague_indicators)

        # 更精确的分类逻辑
        word_count = len(user_input.split())

        # 确定 demand_state - 优先级：明确的模糊指示词 > 具体+时间 > 具体指示词 > 默认
        if has_vague:
            return "VAGUE_UNCLEAR"
        elif word_count < 4:
            return "VAGUE_UNCLEAR"
        elif has_specific and has_time:
            # 有具体指示词和时间指示词
            if word_count <= 25:
                return "SMART_COMPLIANT"
            else:
                return "SMART_LARGE_SCOPE"
        elif has_specific:
            # 有具体指示词但没有时间
            return "SMART_COMPLIANT"
        else:
            # 默认情况
            return "SMART_LARGE_SCOPE"

    def _extract_analysis_focus(self, intent_analysis: Dict[str, Any]) -> List[str]:
        """
        从intent分析中提取分析焦点
        """
        analysis_focus = []

        intent_categories = intent_analysis.get("intent_categories", [])
        complexity_assessment = intent_analysis.get("complexity_assessment", {})

        # 基于intent categories确定分析焦点
        if "analyze" in intent_categories:
            analysis_focus.extend(["data_analysis", "performance_metrics", "trend_identification"])
        if "generate" in intent_categories:
            analysis_focus.extend(["content_creation", "strategy_development", "solution_design"])
        if "process" in intent_categories:
            analysis_focus.extend(["workflow_optimization", "process_improvement", "automation_opportunities"])
        if "collect" in intent_categories:
            analysis_focus.extend(["data_gathering", "information_consolidation", "source_validation"])

        # 基于复杂度添加焦点
        complexity_level = complexity_assessment.get("complexity_level", "medium")
        if complexity_level == "high":
            analysis_focus.extend(["stakeholder_analysis", "risk_assessment", "dependency_mapping"])
        elif complexity_level == "medium":
            analysis_focus.extend(["requirement_analysis", "feasibility_assessment"])

        return list(set(analysis_focus))  # 去重

    def _extract_framework_hints(self, entities_keywords: Dict[str, Any], intent_analysis: Dict[str, Any]) -> List[str]:
        """
        基于实体关键词和intent分析提取框架提示
        """
        framework_hints = []

        entities = entities_keywords.get("entities", [])
        keywords = entities_keywords.get("keywords", [])
        intent_categories = intent_analysis.get("intent_categories", [])

        # 基于实体和关键词推荐框架
        entity_text = " ".join(str(e).lower() for e in entities)
        keyword_text = " ".join(str(k).lower() for k in keywords)
        combined_text = f"{entity_text} {keyword_text}"

        # 财务相关框架
        if any(term in combined_text for term in ["financial", "revenue", "profit", "cost", "budget"]):
            framework_hints.extend(["Financial Ratio Analysis", "Cost-Benefit Analysis", "ROI Analysis"])

        # 性能相关框架
        if any(term in combined_text for term in ["performance", "kpi", "metric", "benchmark"]):
            framework_hints.extend(["Performance Gap Analysis", "Balanced Scorecard", "KPI Framework"])

        # 市场相关框架
        if any(term in combined_text for term in ["market", "customer", "competitor", "segment"]):
            framework_hints.extend(["Market Analysis", "Customer Segmentation", "Competitive Analysis"])

        # 策略相关框架
        if any(term in combined_text for term in ["strategy", "plan", "roadmap", "vision"]):
            framework_hints.extend(["Strategic Planning", "SWOT Analysis", "Scenario Planning"])

        # 流程相关框架
        if any(term in combined_text for term in ["process", "workflow", "procedure", "operation"]):
            framework_hints.extend(["Business Process Modeling", "Value Stream Mapping", "Lean Analysis"])

        # 基于intent categories添加框架
        if "analyze" in intent_categories:
            framework_hints.extend(["Root Cause Analysis", "Data Analysis Framework"])
        if "generate" in intent_categories:
            framework_hints.extend(["Content Strategy Framework", "Solution Design Framework"])
        if "process" in intent_categories:
            framework_hints.extend(["Process Optimization Framework", "Workflow Design"])

        return list(set(framework_hints))  # 去重并返回前5个最相关的

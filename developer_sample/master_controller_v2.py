"""
Master Controller v2 for Conversational AI Workflow Orchestration

This module provides the new tool-enabled MasterController that implements
an act-think-observe self-loop pattern with structured tool execution while
maintaining backward compatibility with existing interfaces.

Key Features:
- Tool-calling capabilities with OpenAI-style function calling
- Self-contained act-think-observe reasoning loop
- Unified entry point for all user inputs and agent communications
- Complete execution trace storage in ContextEngine
- Async/parallel tool execution support
- Smart context compression for 20k token limit
"""

import re
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from aiecs.llm import LLMMessage, LLMResponse
from app.services.llm_integration import LLMIntegrationManager
from app.services.multi_task.config.config_manager import ConfigManager
from app.services.multi_task.core.models.services_models import (
    SummarizerState, ControllerOutputType, ControllerAgentTask,
    ControllerAgentResponse, ControllerSystemCommand
)

# Import tools
from .tools import (
    BaseTool, ReadFilesTool, ReadContextTool,
    SmartAnalysisTool, SummaryContextTool, CommandGeneratorTool
)
from .smart_analysis import SmartAnalysisService

logger = logging.getLogger(__name__)


class ControllerResponse:
    """Response object from the Master Controller."""

    def __init__(self, conversation_response: str, command: Dict[str, Any], raw_response: str,
                 output_type: Optional[ControllerOutputType] = None,
                 agent_task: Optional[ControllerAgentTask] = None,
                 system_command: Optional[ControllerSystemCommand] = None,
                 execution_trace: Optional[Dict[str, Any]] = None):
        self.conversation_response = conversation_response
        self.command = command
        self.raw_response = raw_response
        self.timestamp = datetime.utcnow()

        # Extended response types for agent communication
        self.output_type = output_type
        self.agent_task = agent_task
        self.system_command = system_command
        
        # Execution trace from act-think-observe loop
        self.execution_trace = execution_trace


class MasterControllerV2:
    """
    Master Conversational Controller v2 with Tool-Calling Capabilities.

    This class serves as the intelligent interface between users and the multi-agent
    task execution environment, providing natural language understanding, workflow
    coordination, and tool-calling capabilities through an act-think-observe loop.
    """

    def __init__(self, llm_manager: LLMIntegrationManager, config_manager: ConfigManager,
                 context_engine=None, summarizer_service=None):
        """
        Initialize the Master Controller v2.

        Args:
            llm_manager: LLM integration manager for text generation
            config_manager: Configuration manager for loading prompts
            context_engine: ContextEngine for state management and persistence
            summarizer_service: Optional Summarizer service instance for command generator tool
        """
        self.llm_manager = llm_manager
        self.config_manager = config_manager
        self.context_engine = context_engine
        self.summarizer_service = summarizer_service
        self.logger = logger

        # Tool registry
        self._tools: Dict[str, BaseTool] = {}

        # Configuration
        self._load_controller_config()
        
        # Loop and context settings
        self.max_iterations = 10  # Safety limit for reasoning loop
        self.context_window_limit = 20000  # Token limit for context
        
        # Register tools
        self._register_tools()

        logger.info("Master Controller v2 initialized successfully with tool-calling capabilities")

    def _load_controller_config(self) -> None:
        """Load controller configuration from ConfigManager."""
        try:
            prompts_config = self.config_manager.get_prompts_config()

            # Use the main system_prompt from the YAML configuration
            # Try v2 first, fallback to original
            self.system_prompt = prompts_config.get('system_prompt_v2', 
                                                   prompts_config.get('system_prompt', ''))

            # Load user_prompt_template from root level
            self.user_prompt_template = prompts_config.get('user_prompt_template', 'User request: {user_input}')

            # Load other controller-specific configurations
            controller_prompts = prompts_config.get('controller_prompts', {})
            self.error_prompts = controller_prompts.get('error_prompts', {})

            if not self.system_prompt:
                logger.warning("No system prompt found in configuration, using fallback")
                self.system_prompt = self._get_fallback_system_prompt()

        except Exception as e:
            logger.error(f"Failed to load controller configuration: {e}")
            fallback_config = self._get_fallback_config()
            self.system_prompt = fallback_config['system_prompt']
            self.user_prompt_template = fallback_config['user_prompt_template']
            self.error_prompts = fallback_config['error_prompts']

    def _get_fallback_system_prompt(self) -> str:
        """Get fallback system prompt if YAML loading fails."""
        return """You are Startu MasterController v2 with tool-calling capabilities.

You have access to tools for file reading, context extraction, and analysis.

## RESPONSE FORMAT:
You must respond in JSON structure:
{
  "thought": "Your reasoning about what to do next",
  "action": {
    "type": "tool_call" | "final_response",
    "tool_calls": [...],  // if tool_call
    "response": {...}     // if final_response
  }
}

## WORKFLOW:
1. Think about what information you need
2. Use tools to gather information
3. When ready, provide final_response with command

Available Commands:
- call_mining_service(), plan_workflow(), execute_writer_task(task_description='...'),
- execute_researcher_task(task_description='...'), execute_fieldwork_task(task_description='...'),
- execute_analyst_task(task_description='...'), request_clarification(question='...'),
- present_results(), continue_conversation()"""

    def _get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration if loading fails."""
        return {
            "system_prompt": self._get_fallback_system_prompt(),
            "user_prompt_template": """## CURRENT CONTEXT:
- Session ID: {session_id}
- User Request: {user_input}

## YOUR TASK:
Respond to the user's request with appropriate actions.""",
            "error_prompts": {
                "general_error": "I encountered an unexpected issue. Let me try approaching this differently."
            }
        }

    def _register_tools(self) -> None:
        """Register all available tools."""
        try:
            # Read Files Tool
            # Configuration is automatically loaded from environment variables (DOC_PARSER_*)
            # See .env file and app/__init__.py for environment variable loading
            read_files_tool = ReadFilesTool()
            self._tools[read_files_tool.name] = read_files_tool
            
            # Read Context Tool
            if self.context_engine:
                read_context_tool = ReadContextTool(self.context_engine)
                self._tools[read_context_tool.name] = read_context_tool
            
            # Smart Analysis Tool
            smart_analysis_service = SmartAnalysisService(
                context_engine=self.context_engine,
                llm_manager=self.llm_manager
            )
            smart_analysis_tool = SmartAnalysisTool(smart_analysis_service)
            self._tools[smart_analysis_tool.name] = smart_analysis_tool
            
            # Summary Context Tool
            if self.context_engine:
                summary_context_tool = SummaryContextTool(
                    context_engine=self.context_engine,
                    llm_manager=self.llm_manager
                )
                self._tools[summary_context_tool.name] = summary_context_tool
            
            # Command Generator Tool
            # Works with or without summarizer_service (uses defaults if not available)
            command_generator_tool = CommandGeneratorTool(
                summarizer_service=self.summarizer_service
            )
            self._tools[command_generator_tool.name] = command_generator_tool
            
            logger.info(f"Registered {len(self._tools)} tools: {list(self._tools.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to register tools: {e}", exc_info=True)

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get JSON schemas for all available tools.
        
        Returns:
            List of tool schemas in OpenAI function calling format
        """
        return [tool.get_schema() for tool in self._tools.values()]

    # ==================== Main Entry Point ====================

    async def process_user_input(self, user_input: str, state: SummarizerState,
                               conversation_history: List[Dict[str, Any]] = None) -> ControllerResponse:
        """
        Single unified method for all user input processing.
        
        This method handles both new requests and feedback, maintaining
        backward compatibility with the v1 interface.

        Args:
            user_input: The user's input message
            state: Summarizer state
            conversation_history: Optional conversation history

        Returns:
            ControllerResponse containing conversation text and system commands
        """
        try:
            start_time = datetime.utcnow()
            
            # Build unified context from all sources
            context = await self._build_unified_context(
                user_input=user_input,
                state=state,
                conversation_history=conversation_history
            )
            
            # Execute act-think-observe loop
            execution_trace = await self._execute_reasoning_loop(
                user_input=user_input,
                context=context,
                state=state
            )
            
            # Store complete turn to ContextEngine
            await self._store_turn_to_context(
                session_id=state.session_id,
                user_input=user_input,
                execution_trace=execution_trace
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            execution_trace["total_time_ms"] = processing_time
            
            # Extract and return final response
            return self._create_response_from_trace(execution_trace, state)

        except Exception as e:
            logger.error(f"Controller processing failed: {e}", exc_info=True)
            return self._create_error_response(str(e), state)

    # ==================== Act-Think-Observe Loop ====================

    async def _execute_reasoning_loop(
        self,
        user_input: str,
        context: Dict[str, Any],
        state: SummarizerState
    ) -> Dict[str, Any]:
        """
        Self-contained reasoning loop with tool calling.
        
        Implements act-think-observe pattern:
        1. THINK: Analyze situation and decide next action
        2. ACT: Execute tool calls or provide final response
        3. OBSERVE: Collect tool results and update context
        4. Repeat until final response is ready
        
        Args:
            user_input: User's input message
            context: Unified context dictionary
            state: Summarizer state
            
        Returns:
            Complete execution trace with all iterations
        """
        execution_trace = {
            "user_input": user_input,
            "iterations": [],
            "final_response": None,
            "total_time_ms": 0
        }
        
        current_context = context.copy()
        
        for iteration in range(self.max_iterations):
            logger.info(f"Reasoning loop iteration {iteration + 1}/{self.max_iterations}")
            
            # THINK: Build prompt with available tools
            prompt = self._build_tool_calling_prompt(
                user_input=user_input,
                context=current_context,
                iteration=iteration,
                execution_history=execution_trace["iterations"]
            )
            
            # Call LLM with function calling
            llm_response = await self._invoke_llm_with_tools(
                prompt=prompt,
                available_tools=self._get_tool_schemas(),
                state=state
            )
            
            # Parse response
            thought = llm_response.get("thought", "")
            action = llm_response.get("action")
            
            iteration_data = {
                "iteration": iteration,
                "mastercontroller_thought": thought,
                "mastercontroller_action": action,
                "mastercontroller_observe": [],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # ACT: Execute tool calls or finalize
            if action and action.get("type") == "tool_call":
                # Execute tools
                tool_calls = action.get("tool_calls", [])
                observations = await self._execute_tools(
                    tool_calls=tool_calls,
                    state=state
                )
                iteration_data["mastercontroller_observe"] = observations
                
                # Update context with observations
                if "tool_results" not in current_context:
                    current_context["tool_results"] = []
                current_context["tool_results"].extend(observations)
                
            elif action and action.get("type") == "final_response":
                # Loop termination
                final_resp = action.get("response", {})
                iteration_data["final_response"] = final_resp
                execution_trace["iterations"].append(iteration_data)
                execution_trace["final_response"] = final_resp
                logger.info(f"Reasoning loop completed in {iteration + 1} iterations")
                break
            else:
                # Invalid response format
                logger.warning(f"Invalid action format in iteration {iteration}: {action}")
                iteration_data["error"] = "Invalid action format"
            
            execution_trace["iterations"].append(iteration_data)
            
            # Safety check: max iterations reached
            if iteration >= self.max_iterations - 1:
                logger.warning(f"Max iterations ({self.max_iterations}) reached")
                execution_trace["final_response"] = {
                    "mastercontroller_message": "I need more time to process this request. Let me continue with what I have.",
                    "mastercontroller_command": {
                        "action": "continue_conversation",
                        "params": {}
                    },
                    "error": "Max iterations reached"
                }
        
        return execution_trace

    async def _invoke_llm_with_tools(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]],
        state: SummarizerState
    ) -> Dict[str, Any]:
        """
        Invoke LLM with tool-calling capabilities.
        
        Args:
            prompt: Complete prompt including instructions
            available_tools: List of tool schemas
            state: Summarizer state
            
        Returns:
            Parsed LLM response with thought and action
        """
        try:
            # Build messages for LLM
            messages = [LLMMessage(role="user", content=prompt)]
            
            context = {
                "session_id": state.session_id,
                "task_id": getattr(state, 'task_id', 'unknown'),
                "tools": available_tools
            }
            
            # Invoke LLM
            llm_response = await self.llm_manager.generate_with_context(
                messages=messages,
                context=context,
                temperature=0.7,
                max_tokens=10240
            )
            
            # Parse JSON response
            response_content = llm_response.content
            parsed_response = self._parse_llm_response(response_content)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            # Return fallback response
            return {
                "thought": f"Error occurred: {str(e)}",
                "action": {
                    "type": "final_response",
                    "response": {
                        "mastercontroller_message": "I encountered an issue processing your request.",
                        "mastercontroller_command": {
                            "action": "continue_conversation",
                            "params": {}
                        }
                    }
                }
            }

    def _parse_llm_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM response to extract thought and action.
        
        Handles both JSON format and fallback parsing.
        
        Args:
            response_content: Raw LLM response
            
        Returns:
            Dict with thought and action
        """
        try:
            # Try to extract JSON from response
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # Try direct JSON parsing
                json_str = response_content.strip()
            
            parsed = json.loads(json_str)
            
            # Validate structure
            if "thought" in parsed and "action" in parsed:
                return parsed
            else:
                logger.warning("LLM response missing required fields, using fallback")
                return self._create_fallback_parse(response_content)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return self._create_fallback_parse(response_content)

    def _create_fallback_parse(self, response_content: str) -> Dict[str, Any]:
        """
        Create fallback parsed response when JSON parsing fails.

        Args:
            response_content: Raw response content

        Returns:
            Fallback structured response
        """
        # Use the raw response as conversation text
        # Default to continue_conversation command
        return {
            "thought": "Processing user request with available information",
            "action": {
                "type": "final_response",
                "response": {
                    "mastercontroller_message": response_content.strip(),
                    "mastercontroller_command": {
                        "action": "continue_conversation",
                        "params": {}
                    }
                }
            }
        }

    # ==================== Tool Execution ====================

    async def _execute_tools(
        self,
        tool_calls: List[Dict[str, Any]],
        state: SummarizerState
    ) -> List[Dict[str, Any]]:
        """
        Execute tools with async/parallel support when independent.
        
        Args:
            tool_calls: List of tool calls to execute
            state: Summarizer state
            
        Returns:
            List of observation results
        """
        observations = []
        
        # Group tools: parallel-safe vs sequential
        parallel_tools = []
        sequential_tools = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            if self._is_tool_parallel_safe(tool_name):
                parallel_tools.append(tool_call)
            else:
                sequential_tools.append(tool_call)
        
        # Execute parallel tools concurrently
        if parallel_tools:
            logger.info(f"Executing {len(parallel_tools)} tools in parallel")
            tasks = [
                self._execute_single_tool(tc, state) 
                for tc in parallel_tools
            ]
            parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions from gather
            for result in parallel_results:
                if isinstance(result, Exception):
                    observations.append({
                        "tool": "unknown",
                        "error": str(result),
                        "success": False
                    })
                else:
                    observations.append(result)
        
        # Execute sequential tools one by one
        for tool_call in sequential_tools:
            logger.info(f"Executing tool sequentially: {tool_call.get('name')}")
            result = await self._execute_single_tool(tool_call, state)
            observations.append(result)
        
        return observations

    async def _execute_single_tool(
        self,
        tool_call: Dict[str, Any],
        state: SummarizerState
    ) -> Dict[str, Any]:
        """
        Execute a single tool call.
        
        Args:
            tool_call: Tool call specification
            state: Summarizer state
            
        Returns:
            Tool execution result
        """
        tool_name = tool_call.get("name", "")
        parameters = tool_call.get("parameters", {})
        
        if tool_name not in self._tools:
            return {
                "tool": tool_name,
                "error": f"Tool {tool_name} not found",
                "result": None,
                "success": False
            }
        
        try:
            tool = self._tools[tool_name]
            logger.info(f"Executing tool: {tool_name} with params: {list(parameters.keys())}")
            
            # Use safe_execute for parameter validation
            result = await tool.safe_execute(**parameters)
            
            return {
                "tool": tool_name,
                "parameters": parameters,
                "result": result.get("result"),
                "success": result.get("success", False),
                "error": result.get("error")
            }
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
            return {
                "tool": tool_name,
                "parameters": parameters,
                "error": str(e),
                "success": False
            }

    def _is_tool_parallel_safe(self, tool_name: str) -> bool:
        """
        Determine if a tool can be executed in parallel.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool is safe for parallel execution
        """
        # Tools that read data are generally safe for parallel execution
        parallel_safe_tools = {
            "read_files",
            "read_context",
            "smart_analysis"
        }
        
        # Tools that modify state should run sequentially
        sequential_tools = {
            "summary_context"  # Modifies context
        }
        
        if tool_name in parallel_safe_tools:
            return True
        elif tool_name in sequential_tools:
            return False
        else:
            # Default to sequential for unknown tools
            return False

    # ==================== Context Management ====================

    async def _build_unified_context(
        self,
        user_input: str,
        state: SummarizerState,
        conversation_history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build unified context with smart compression if needed.
        
        Loads context from all sources and compresses if necessary
        to stay within token limits.
        
        Args:
            user_input: User's input message
            state: Summarizer state
            conversation_history: Optional conversation history
            
        Returns:
            Unified context dictionary
        """
        # Load all context sources
        conv_history = await self._load_conversation_history(state.session_id, conversation_history)
        agent_messages = await self._load_agent_messages(state.session_id)
        agent_results = await self._load_agent_results(state.session_id)
        system_state = self._build_system_state(state)
        command_state = state.controller_commands if hasattr(state, 'controller_commands') else []
        
        # Build raw context
        raw_context = {
            "user_input": user_input,
            "conversation_history": conv_history,
            "agent_messages": agent_messages,
            "agent_results": agent_results,
            "system_state": system_state,
            "command_state": command_state,
            "session_id": state.session_id
        }
        
        # Check if compression needed
        estimated_tokens = self._estimate_context_tokens(raw_context)
        
        if estimated_tokens > self.context_window_limit:
            logger.info(f"Context exceeds limit ({estimated_tokens} > {self.context_window_limit}), compressing")
            compressed_context = await self._compress_context_smart(
                raw_context,
                target_tokens=int(self.context_window_limit * 0.8)
            )
            return compressed_context
        
        return raw_context

    async def _load_conversation_history(
        self,
        session_id: str,
        fallback_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Load conversation history from ContextEngine or fallback."""
        if not self.context_engine:
            return fallback_history or []

        try:
            history = await self.context_engine.get_conversation_history(session_id)
            if not history:
                return fallback_history or []

            # Convert ConversationMessage objects to dicts
            converted_history = []
            for msg in history:
                if hasattr(msg, 'to_dict'):
                    # ConversationMessage object
                    converted_history.append(msg.to_dict())
                elif isinstance(msg, dict):
                    # Already a dict
                    converted_history.append(msg)
                else:
                    # Try to convert to dict
                    try:
                        converted_history.append({
                            'role': getattr(msg, 'role', 'unknown'),
                            'content': getattr(msg, 'content', str(msg)),
                            'timestamp': getattr(msg, 'timestamp', None)
                        })
                    except Exception as conv_error:
                        logger.warning(f"Failed to convert message to dict: {conv_error}")

            return converted_history
        except Exception as e:
            logger.warning(f"Failed to load conversation history: {e}")
            return fallback_history or []

    async def _load_agent_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Load agent communication messages from ContextEngine."""
        if not self.context_engine:
            return []
        
        try:
            task_context = await self.context_engine.get_task_context(session_id)
            if not task_context:
                return []
            
            # Extract agent messages from turns
            agent_messages = []
            turns = task_context.metadata.get("mastercontroller_turns", [])
            for turn in turns:
                if turn.get("type") == "agent_communication":
                    agent_messages.append(turn)
            
            return agent_messages
        except Exception as e:
            logger.warning(f"Failed to load agent messages: {e}")
            return []

    async def _load_agent_results(self, session_id: str) -> Dict[str, Any]:
        """Load agent execution results from ContextEngine."""
        if not self.context_engine:
            return {}
        
        try:
            task_context = await self.context_engine.get_task_context(session_id)
            if not task_context:
                return {}
            
            agent_results = task_context.metadata.get("agent_results", {})
            return agent_results
        except Exception as e:
            logger.warning(f"Failed to load agent results: {e}")
            return {}

    def _build_system_state(self, state: SummarizerState) -> Dict[str, Any]:
        """Build system state summary from Summarizer state."""
        return {
            "current_step": state.current_step,
            "workflow_status": getattr(state, 'workflow_status', 'unknown'),
            "completed": getattr(state, 'completed', False),
            "error": state.error,
            "mining_result": state.mining_result is not None,
            "planning_result": state.planning_result is not None
        }

    def _estimate_context_tokens(self, context: Dict[str, Any]) -> int:
        """
        Estimate token count for context.
        
        Uses rough estimate of ~4 characters per token.
        
        Args:
            context: Context dictionary
            
        Returns:
            Estimated token count
        """
        context_str = json.dumps(context, default=str)
        char_count = len(context_str)
        estimated_tokens = char_count // 4
        return estimated_tokens

    async def _compress_context_smart(
        self,
        context: Dict[str, Any],
        target_tokens: int
    ) -> Dict[str, Any]:
        """
        Smart context compression: keep recent, summarize old.
        
        Args:
            context: Raw context to compress
            target_tokens: Target token count
            
        Returns:
            Compressed context
        """
        compressed = context.copy()
        
        # Keep recent conversation messages, truncate older ones
        conv_history = context.get("conversation_history", [])
        if len(conv_history) > 10:
            # Keep last 5 messages, summarize older ones
            recent = conv_history[-5:]
            older = conv_history[:-5]
            
            # Simple summarization: just count and mention
            summary_msg = {
                "role": "system",
                "content": f"[{len(older)} earlier messages in conversation]"
            }
            compressed["conversation_history"] = [summary_msg] + recent
        
        # Truncate agent results if too many
        agent_results = context.get("agent_results", {})
        if len(agent_results) > 5:
            # Keep only most recent 5
            result_items = list(agent_results.items())
            compressed["agent_results"] = dict(result_items[-5:])
        
        # Keep agent messages truncated
        agent_messages = context.get("agent_messages", [])
        if len(agent_messages) > 3:
            compressed["agent_messages"] = agent_messages[-3:]
        
        logger.info(f"Context compressed: {self._estimate_context_tokens(context)} -> {self._estimate_context_tokens(compressed)} tokens")
        
        return compressed

    # ==================== Storage Methods ====================

    async def _store_turn_to_context(
        self,
        session_id: str,
        user_input: str,
        execution_trace: Dict[str, Any]
    ) -> None:
        """
        Store complete turn with nested structure to ContextEngine.
        
        Args:
            session_id: Session ID
            user_input: User's input
            execution_trace: Complete execution trace
        """
        if not self.context_engine:
            logger.debug("ContextEngine not available, skipping turn storage")
            return
        
        try:
            task_context = await self.context_engine.get_task_context(session_id)
            
            if not task_context:
                # Create new task context
                from aiecs.domain.task.task_context import TaskContext
                task_context = TaskContext({
                    "user_id": "unknown",
                    "chat_id": session_id,
                    "metadata": {}
                })
            
            # Ensure metadata exists
            if not hasattr(task_context, 'metadata') or task_context.metadata is None:
                task_context.metadata = {}

            # Initialize turns list in metadata
            if "mastercontroller_turns" not in task_context.metadata:
                task_context.metadata["mastercontroller_turns"] = []

            # Format execution trace for storage
            formatted_trace = self._format_execution_trace(execution_trace)

            # Create turn data
            turn_data = {
                "turn_id": f"turn_{len(task_context.metadata['mastercontroller_turns'])}",
                "user_input": user_input,
                "mastercontroller_execution": formatted_trace,
                "timestamp": datetime.utcnow().isoformat()
            }

            task_context.metadata["mastercontroller_turns"].append(turn_data)

            # Store updated context
            await self.context_engine.store_task_context(session_id, task_context)
            logger.debug(f"Stored turn to ContextEngine for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to store turn to ContextEngine: {e}", exc_info=True)

    def _format_execution_trace(self, execution_trace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format execution trace for storage.
        
        Args:
            execution_trace: Raw execution trace
            
        Returns:
            Formatted trace for storage
        """
        return {
            "iterations": execution_trace.get("iterations", []),
            "final_response": execution_trace.get("final_response"),
            "total_time_ms": execution_trace.get("total_time_ms", 0)
        }

    # ==================== Prompt Building ====================

    def _build_tool_calling_prompt(
        self,
        user_input: str,
        context: Dict[str, Any],
        iteration: int,
        execution_history: List[Dict[str, Any]]
    ) -> str:
        """
        Build prompt for tool-calling LLM.
        
        Args:
            user_input: User's input
            context: Unified context
            iteration: Current iteration number
            execution_history: Previous iterations
            
        Returns:
            Complete prompt string
        """
        # Format tool schemas
        tools_schema = json.dumps(self._get_tool_schemas(), indent=2)
        
        # Format conversation history
        conv_history_str = self._format_conversation_history(context.get("conversation_history", []))
        
        # Format previous iterations
        previous_iterations_str = self._format_previous_iterations(execution_history)
        
        # Build system prompt with tools
        system_section = f"""{self.system_prompt}

## AVAILABLE TOOLS:
{tools_schema}

## RESPONSE FORMAT (JSON):
{{
  "thought": "Your reasoning about the situation and what to do next",
  "action": {{
    "type": "tool_call" | "final_response",
    "tool_calls": [  // Only if type is "tool_call"
      {{
        "name": "tool_name",
        "parameters": {{"param": "value"}}
      }}
    ],
    "response": {{  // Only if type is "final_response"
      "mastercontroller_message": "Your response to the user",
      "mastercontroller_command": {{
        "action": "command_name",
        "params": {{}}
      }}
    }}
  }}
}}"""
        
        # Build user section
        user_section = f"""## CURRENT ITERATION: {iteration + 1}/{self.max_iterations}

## USER REQUEST:
{user_input}

## CONVERSATION HISTORY:
{conv_history_str}

## SYSTEM STATE:
{json.dumps(context.get("system_state", {}), indent=2)}

## PREVIOUS ITERATIONS:
{previous_iterations_str if previous_iterations_str else "None (first iteration)"}

## YOUR TASK:
Analyze the situation and decide on the next action. Use tools to gather information if needed, or provide a final response when ready."""
        
        return f"{system_section}\n\n{user_section}"

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """Format conversation history for prompt."""
        if not history:
            return "No previous conversation."
        
        formatted = []
        for msg in history[-8:]:  # Last 8 messages
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)

    def _format_previous_iterations(self, iterations: List[Dict[str, Any]]) -> str:
        """Format previous iterations for prompt."""
        if not iterations:
            return ""
        
        formatted = []
        for iter_data in iterations:
            thought = iter_data.get("mastercontroller_thought", "")
            action = iter_data.get("mastercontroller_action", {})
            observations = iter_data.get("mastercontroller_observe", [])
            
            formatted.append(f"Iteration {iter_data['iteration'] + 1}:")
            formatted.append(f"  Thought: {thought}")
            formatted.append(f"  Action: {action.get('type', 'unknown')}")
            
            if observations:
                formatted.append(f"  Observations:")
                for obs in observations:
                    tool_name = obs.get("tool", "unknown")
                    success = obs.get("success", False)
                    formatted.append(f"    - {tool_name}: {'Success' if success else 'Failed'}")
        
        return "\n".join(formatted)

    # ==================== Response Creation ====================

    def _create_response_from_trace(
        self,
        execution_trace: Dict[str, Any],
        state: SummarizerState
    ) -> ControllerResponse:
        """
        Create ControllerResponse from execution trace.

        Args:
            execution_trace: Complete execution trace
            state: Summarizer state

        Returns:
            ControllerResponse object
        """
        final_response = execution_trace.get("final_response", {})

        conversation_text = final_response.get("mastercontroller_message",
                                              "Processing your request...")
        command = final_response.get("mastercontroller_command", {
            "action": "continue_conversation",
            "params": {}
        })

        return ControllerResponse(
            conversation_response=conversation_text,
            command=command,
            raw_response=json.dumps(final_response),
            execution_trace=execution_trace
        )

    def _create_error_response(self, error_message: str, state: SummarizerState) -> ControllerResponse:
        """Create error response when processing fails."""
        error_response = self.error_prompts.get('general_error',
            "I encountered an issue. Let me try to help you differently.")
        
        return ControllerResponse(
            conversation_response=error_response,
            command={"action": "continue_conversation", "params": {}},
            raw_response=error_response
        )

    # ==================== Agent Communication Methods ====================

    async def process_agent_communication(
        self,
        session_id: str,
        agent_role: str,
        message_type: str,
        content: str,
        task_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> ControllerResponse:
        """
        Single unified method for all agent-initiated communication.
        
        Reuses the same prompt building and reasoning loop as user input.
        
        Args:
            session_id: Session ID
            agent_role: Agent role initiating communication
            message_type: Type of message (question, clarification, result, etc.)
            content: Message content
            task_id: Optional task ID this relates to
            metadata: Additional metadata
            
        Returns:
            ControllerResponse with MasterController's response to agent
        """
        try:
            # Load or create minimal state from session
            # Note: Agent communication typically doesn't have full SummarizerState context
            # Create minimal state for agent communication processing
            state = SummarizerState(
                session_id=session_id,
                user_id="agent_communication",
                task_id=task_id or f"agent_comm_{session_id}",
                user_input=content,
                input_data={},
                context={"agent_role": agent_role, "message_type": message_type}
            )

            # Create agent-aware input
            agent_input = f"[AGENT_{agent_role.upper()}_MESSAGE:{message_type}] {content}"
            
            context = await self._build_unified_context(
                user_input=agent_input,
                state=state,
                conversation_history=None
            )
            
            # Add agent-specific context
            context["agent_communication"] = {
                "agent_role": agent_role,
                "message_type": message_type,
                "task_id": task_id,
                "metadata": metadata or {}
            }
            
            # Execute same reasoning loop
            execution_trace = await self._execute_reasoning_loop(
                user_input=agent_input,
                context=context,
                state=state
            )
            
            # Store as agent communication turn
            await self._store_agent_communication_turn(
                session_id=session_id,
                agent_role=agent_role,
                agent_message=content,
                execution_trace=execution_trace
            )
            
            return self._create_response_from_trace(execution_trace, state)
            
        except Exception as e:
            logger.error(f"Agent communication processing failed: {e}", exc_info=True)
            # Create minimal state for error response
            minimal_state = SummarizerState(
                session_id=session_id,
                user_id="unknown",
                task_id="unknown",
                user_input=content,
                input_data={},
                context={}
            )
            return self._create_error_response(str(e), minimal_state)

    async def _store_agent_communication_turn(
        self,
        session_id: str,
        agent_role: str,
        agent_message: str,
        execution_trace: Dict[str, Any]
    ) -> None:
        """
        Store agent communication with specific identifiers.
        
        Args:
            session_id: Session ID
            agent_role: Agent role
            agent_message: Agent's message
            execution_trace: Execution trace
        """
        if not self.context_engine:
            logger.debug("ContextEngine not available, skipping agent communication storage")
            return
        
        try:
            task_context = await self.context_engine.get_task_context(session_id)
            
            if not task_context:
                from aiecs.domain.task.task_context import TaskContext
                task_context = TaskContext({
                    "user_id": "unknown",
                    "chat_id": session_id,
                    "metadata": {}
                })

            if not hasattr(task_context, 'metadata') or task_context.metadata is None:
                task_context.metadata = {}

            if "mastercontroller_turns" not in task_context.metadata:
                task_context.metadata["mastercontroller_turns"] = []
            
            # Format execution trace
            formatted_trace = self._format_execution_trace(execution_trace)
            
            # Create turn data with agent communication markers
            turn_data = {
                "turn_id": f"turn_{len(task_context.metadata['mastercontroller_turns'])}",
                "type": "agent_communication",
                f"{agent_role}_agent_message": agent_message,
                "mastercontroller_execution": formatted_trace,
                "mastercontroller_response": execution_trace.get("final_response"),
                "timestamp": datetime.utcnow().isoformat()
            }

            task_context.metadata["mastercontroller_turns"].append(turn_data)
            await self.context_engine.store_task_context(session_id, task_context)
            logger.debug(f"Stored agent communication turn for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to store agent communication: {e}", exc_info=True)

    # ==================== Utility Methods ====================

    def get_available_commands(self) -> List[str]:
        """Get list of available system commands."""
        return [
            "call_mining_service",
            "plan_workflow",
            "execute_writer_task",
            "execute_researcher_task",
            "execute_fieldwork_task",
            "execute_analyst_task",
            "request_clarification",
            "present_results",
            "continue_conversation"
        ]

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return list(self._tools.keys())

    def reload_configuration(self) -> bool:
        """Reload controller configuration from ConfigManager."""
        try:
            self._load_controller_config()
            logger.info("Controller configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload controller configuration: {e}")
            return False

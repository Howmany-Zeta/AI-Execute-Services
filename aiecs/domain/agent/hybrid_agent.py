"""
Hybrid Agent

Agent implementation combining LLM reasoning with tool execution capabilities.
Implements the ReAct (Reasoning + Acting) pattern.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from aiecs.llm import BaseLLMClient, LLMMessage, LLMResponse
from aiecs.tools import get_tool, BaseTool

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError, ToolAccessDeniedError

logger = logging.getLogger(__name__)


class HybridAgent(BaseAIAgent):
    """
    Hybrid agent combining LLM reasoning with tool execution.

    Implements ReAct pattern: Reason → Act → Observe loop.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: BaseLLMClient,
        tools: List[str],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        max_iterations: int = 10,
    ):
        """
        Initialize Hybrid agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client for reasoning
            tools: List of tool names
            config: Agent configuration
            description: Optional description
            version: Agent version
            max_iterations: Maximum ReAct iterations
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DEVELOPER,  # Can be adjusted based on use case
            config=config,
            description=description or "Hybrid agent with LLM reasoning and tool execution",
            version=version,
        )
        
        self.llm_client = llm_client
        self._available_tools = tools
        self._max_iterations = max_iterations
        self._tool_instances: Dict[str, BaseTool] = {}
        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []

        logger.info(
            f"HybridAgent initialized: {agent_id} with LLM ({llm_client.provider_name}) "
            f"and tools: {', '.join(tools)}"
        )

    async def _initialize(self) -> None:
        """Initialize Hybrid agent - build system prompt and load tools."""
        # Build system prompt
        self._system_prompt = self._build_system_prompt()
        
        # Load tool instances
        for tool_name in self._available_tools:
            try:
                self._tool_instances[tool_name] = get_tool(tool_name)
                logger.debug(f"HybridAgent {self.agent_id} loaded tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Failed to load tool {tool_name}: {e}")

        logger.info(
            f"HybridAgent {self.agent_id} initialized with {len(self._tool_instances)} tools"
        )

    async def _shutdown(self) -> None:
        """Shutdown Hybrid agent."""
        self._conversation_history.clear()
        self._tool_instances.clear()
        
        if hasattr(self.llm_client, 'close'):
            await self.llm_client.close()
        
        logger.info(f"HybridAgent {self.agent_id} shut down")

    def _build_system_prompt(self) -> str:
        """Build system prompt including tool descriptions."""
        parts = []

        # Add goal and backstory
        if self._config.goal:
            parts.append(f"Goal: {self._config.goal}")

        if self._config.backstory:
            parts.append(f"Background: {self._config.backstory}")

        # Add ReAct instructions
        parts.append(
            "You are a reasoning agent that can use tools to complete tasks. "
            "Follow the ReAct pattern:\n"
            "1. THOUGHT: Analyze the task and decide what to do\n"
            "2. ACTION: Use a tool if needed, or provide final answer\n"
            "3. OBSERVATION: Review the tool result and continue reasoning\n\n"
            "When you need to use a tool, respond with:\n"
            "TOOL: <tool_name>\n"
            "OPERATION: <operation_name>\n"
            "PARAMETERS: <json_parameters>\n\n"
            "When you have the final answer, respond with:\n"
            "FINAL ANSWER: <your_answer>"
        )

        # Add available tools
        if self._available_tools:
            parts.append(f"\nAvailable tools: {', '.join(self._available_tools)}")

        if self._config.domain_knowledge:
            parts.append(f"\nDomain Knowledge: {self._config.domain_knowledge}")

        return "\n\n".join(parts)

    async def execute_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a task using ReAct loop.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Returns:
            Execution result with 'output', 'reasoning_steps', 'tool_calls'

        Raises:
            TaskExecutionError: If task execution fails
        """
        start_time = datetime.utcnow()

        try:
            # Extract task description
            task_description = task.get('description') or task.get('prompt') or task.get('task')
            if not task_description:
                raise TaskExecutionError(
                    "Task must contain 'description', 'prompt', or 'task' field",
                    agent_id=self.agent_id
                )

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get('task_id')

            # Execute ReAct loop
            result = await self._react_loop(task_description, context)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(
                execution_time=execution_time,
                success=True,
                tokens_used=result.get('total_tokens'),
                tool_calls=result.get('tool_calls_count', 0),
            )

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return {
                "success": True,
                "output": result.get('final_answer'),
                "reasoning_steps": result.get('steps'),
                "tool_calls_count": result.get('tool_calls_count'),
                "iterations": result.get('iterations'),
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Task execution failed for {self.agent_id}: {e}")
            
            # Update metrics for failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            # Transition to error state
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                agent_id=self.agent_id,
                task_id=task.get('task_id')
            )

    async def process_message(
        self,
        message: str,
        sender_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message using ReAct loop.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary with 'response', 'reasoning_steps'
        """
        try:
            # Build task from message
            task = {
                "description": message,
                "task_id": f"msg_{datetime.utcnow().timestamp()}",
            }
            
            # Execute as task
            result = await self.execute_task(task, {"sender_id": sender_id})
            
            return {
                "response": result.get("output"),
                "reasoning_steps": result.get("reasoning_steps"),
                "timestamp": result.get("timestamp"),
            }

        except Exception as e:
            logger.error(f"Message processing failed for {self.agent_id}: {e}")
            raise

    async def _react_loop(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute ReAct loop: Reason → Act → Observe.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary with 'final_answer', 'steps', 'iterations'
        """
        steps = []
        tool_calls_count = 0
        total_tokens = 0

        # Build initial messages
        messages = self._build_initial_messages(task, context)

        for iteration in range(self._max_iterations):
            logger.debug(f"HybridAgent {self.agent_id} - ReAct iteration {iteration + 1}")

            # THINK: LLM reasons about next action
            response = await self.llm_client.generate_text(
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )

            thought = response.content
            total_tokens += getattr(response, 'total_tokens', 0)

            steps.append({
                "type": "thought",
                "content": thought,
                "iteration": iteration + 1,
            })

            # Check if final answer
            if "FINAL ANSWER:" in thought:
                final_answer = self._extract_final_answer(thought)
                return {
                    "final_answer": final_answer,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "total_tokens": total_tokens,
                }

            # Check if tool call
            if "TOOL:" in thought:
                # ACT: Execute tool
                try:
                    tool_info = self._parse_tool_call(thought)
                    tool_result = await self._execute_tool(
                        tool_info['tool'],
                        tool_info.get('operation'),
                        tool_info.get('parameters', {})
                    )
                    tool_calls_count += 1

                    steps.append({
                        "type": "action",
                        "tool": tool_info['tool'],
                        "operation": tool_info.get('operation'),
                        "parameters": tool_info.get('parameters'),
                        "iteration": iteration + 1,
                    })

                    # OBSERVE: Add tool result to conversation
                    observation = f"OBSERVATION: Tool '{tool_info['tool']}' returned: {tool_result}"
                    steps.append({
                        "type": "observation",
                        "content": observation,
                        "iteration": iteration + 1,
                    })

                    # Add to messages for next iteration
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=observation))

                except Exception as e:
                    error_msg = f"OBSERVATION: Tool execution failed: {str(e)}"
                    steps.append({
                        "type": "observation",
                        "content": error_msg,
                        "iteration": iteration + 1,
                        "error": True,
                    })
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=error_msg))

            else:
                # LLM didn't provide clear action - treat as final answer
                return {
                    "final_answer": thought,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "total_tokens": total_tokens,
                }

        # Max iterations reached
        logger.warning(f"HybridAgent {self.agent_id} reached max iterations")
        return {
            "final_answer": "Max iterations reached. Unable to complete task fully.",
            "steps": steps,
            "iterations": self._max_iterations,
            "tool_calls_count": tool_calls_count,
            "total_tokens": total_tokens,
            "max_iterations_reached": True,
        }

    def _build_initial_messages(
        self,
        task: str,
        context: Dict[str, Any]
    ) -> List[LLMMessage]:
        """Build initial messages for ReAct loop."""
        messages = []

        # Add system prompt
        if self._system_prompt:
            messages.append(LLMMessage(role="system", content=self._system_prompt))

        # Add context if provided
        if context:
            context_str = self._format_context(context)
            if context_str:
                messages.append(LLMMessage(
                    role="system",
                    content=f"Additional Context:\n{context_str}"
                ))

        # Add task
        messages.append(LLMMessage(role="user", content=f"Task: {task}"))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []
        for key, value in context.items():
            if not key.startswith('_') and value is not None:
                relevant_fields.append(f"{key}: {value}")
        return "\n".join(relevant_fields) if relevant_fields else ""

    def _extract_final_answer(self, thought: str) -> str:
        """Extract final answer from thought."""
        if "FINAL ANSWER:" in thought:
            return thought.split("FINAL ANSWER:", 1)[1].strip()
        return thought

    def _parse_tool_call(self, thought: str) -> Dict[str, Any]:
        """
        Parse tool call from LLM thought.

        Expected format:
        TOOL: <tool_name>
        OPERATION: <operation_name>
        PARAMETERS: <json_parameters>

        Args:
            thought: LLM thought containing tool call

        Returns:
            Dictionary with 'tool', 'operation', 'parameters'
        """
        import json
        
        result = {}
        
        # Extract tool
        if "TOOL:" in thought:
            tool_line = [line for line in thought.split('\n') if line.startswith('TOOL:')][0]
            result['tool'] = tool_line.split('TOOL:', 1)[1].strip()

        # Extract operation (optional)
        if "OPERATION:" in thought:
            op_line = [line for line in thought.split('\n') if line.startswith('OPERATION:')][0]
            result['operation'] = op_line.split('OPERATION:', 1)[1].strip()

        # Extract parameters (optional)
        if "PARAMETERS:" in thought:
            param_line = [line for line in thought.split('\n') if line.startswith('PARAMETERS:')][0]
            param_str = param_line.split('PARAMETERS:', 1)[1].strip()
            try:
                result['parameters'] = json.loads(param_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse parameters: {param_str}")
                result['parameters'] = {}

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any]
    ) -> Any:
        """Execute a tool operation."""
        # Check access
        if tool_name not in self._available_tools:
            raise ToolAccessDeniedError(self.agent_id, tool_name)

        tool = self._tool_instances.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not loaded")

        # Execute tool
        if operation:
            result = await tool.run_async(operation, **parameters)
        else:
            if hasattr(tool, 'run_async'):
                result = await tool.run_async(**parameters)
            else:
                raise ValueError(f"Tool {tool_name} requires operation to be specified")

        return result

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self._available_tools.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HybridAgent":
        """
        Deserialize HybridAgent from dictionary.

        Note: LLM client must be provided separately.

        Args:
            data: Dictionary representation

        Returns:
            HybridAgent instance
        """
        raise NotImplementedError(
            "HybridAgent.from_dict requires LLM client to be provided separately. "
            "Use constructor instead."
        )


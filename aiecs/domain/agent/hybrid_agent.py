"""
Hybrid Agent

Agent implementation combining LLM reasoning with tool execution capabilities.
Implements the ReAct (Reasoning + Acting) pattern.
"""

import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, AsyncIterator
from datetime import datetime

from aiecs.llm import BaseLLMClient, CacheControl, LLMMessage
from aiecs.tools import get_tool, BaseTool
from aiecs.domain.agent.tools.schema_generator import ToolSchemaGenerator

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration, ToolObservation
from .exceptions import TaskExecutionError, ToolAccessDeniedError

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )

logger = logging.getLogger(__name__)


class HybridAgent(BaseAIAgent):
    """
    Hybrid agent combining LLM reasoning with tool execution.

    Implements ReAct pattern: Reason → Act → Observe loop.

    This agent supports flexible tool and LLM client configurations:

    **Tool Configuration:**
    - Tool names (List[str]): Backward compatible, tools loaded by name
    - Tool instances (Dict[str, BaseTool]): Pre-configured tools with preserved state

    **LLM Client Configuration:**
    - BaseLLMClient: Standard LLM clients (OpenAI, xAI, etc.)
    - Custom clients: Any object implementing LLMClientProtocol (duck typing)

    Examples:
        # Example 1: Basic usage with tool names (backward compatible)
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            llm_client=OpenAIClient(),
            tools=["search", "calculator"],
            config=config
        )

        # Example 2: Using tool instances with preserved state
        from aiecs.tools import BaseTool

        class StatefulSearchTool(BaseTool):
            def __init__(self, api_key: str, context_engine):
                self.api_key = api_key
                self.context_engine = context_engine
                self.search_history = []  # State preserved across calls

            async def run_async(self, operation: str, query: str):
                self.search_history.append(query)
                # Use context_engine for context-aware search
                return f"Search results for: {query}"

        # Create tool instances with dependencies
        context_engine = ContextEngine()
        await context_engine.initialize()

        search_tool = StatefulSearchTool(
            api_key="...",
            context_engine=context_engine
        )

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            llm_client=OpenAIClient(),
            tools={
                "search": search_tool,  # Stateful tool instance
                "calculator": CalculatorTool()
            },
            config=config
        )
        # Tool state (search_history) is preserved across agent operations

        # Example 3: Using custom LLM client wrapper
        class CustomLLMWrapper:
            provider_name = "custom_wrapper"

            def __init__(self, base_client):
                self.base_client = base_client
                self.call_count = 0

            async def generate_text(self, messages, **kwargs):
                self.call_count += 1
                # Add custom logging, retry logic, etc.
                return await self.base_client.generate_text(messages, **kwargs)

            async def stream_text(self, messages, **kwargs):
                async for token in self.base_client.stream_text(messages, **kwargs):
                    yield token

            async def close(self):
                await self.base_client.close()

        # Wrap existing client
        base_client = OpenAIClient()
        wrapped_client = CustomLLMWrapper(base_client)

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            llm_client=wrapped_client,  # Custom wrapper, no inheritance needed
            tools=["search", "calculator"],
            config=config
        )

        # Example 4: Full-featured agent with all options
        from aiecs.domain.context import ContextEngine
        from aiecs.domain.agent.models import ResourceLimits

        context_engine = ContextEngine()
        await context_engine.initialize()

        resource_limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tokens_per_minute=10000
        )

        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            llm_client=CustomLLMWrapper(OpenAIClient()),
            tools={
                "search": StatefulSearchTool(api_key="...", context_engine=context_engine),
                "calculator": CalculatorTool()
            },
            config=config,
            config_manager=DatabaseConfigManager(),
            checkpointer=RedisCheckpointer(),
            context_engine=context_engine,
            collaboration_enabled=True,
            agent_registry={"agent2": other_agent},
            learning_enabled=True,
            resource_limits=resource_limits
        )

        # Example 5: Streaming with tool instances
        agent = HybridAgent(
            agent_id="agent1",
            name="My Agent",
            llm_client=OpenAIClient(),
            tools={
                "search": StatefulSearchTool(api_key="..."),
                "calculator": CalculatorTool()
            },
            config=config
        )

        # Stream task execution (tokens + tool calls)
        async for event in agent.execute_task_streaming(task, context):
            if event['type'] == 'token':
                print(event['content'], end='', flush=True)
            elif event['type'] == 'tool_call':
                print(f"\\nCalling {event['tool_name']}...")
            elif event['type'] == 'tool_result':
                print(f"Result: {event['result']}")
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        llm_client: Union[BaseLLMClient, "LLMClientProtocol"],
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        description: Optional[str] = None,
        version: str = "1.0.0",
        max_iterations: int = 10,
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional["CheckpointerProtocol"] = None,
        context_engine: Optional[Any] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
    ):
        """
        Initialize Hybrid agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            llm_client: LLM client for reasoning (BaseLLMClient or any LLMClientProtocol)
            tools: Tools - either list of tool names or dict of tool instances
            config: Agent configuration
            description: Optional description
            version: Agent version
            max_iterations: Maximum ReAct iterations
            config_manager: Optional configuration manager for dynamic config
            checkpointer: Optional checkpointer for state persistence
            context_engine: Optional context engine for persistent storage
            collaboration_enabled: Enable collaboration features
            agent_registry: Registry of other agents for collaboration
            learning_enabled: Enable learning features
            resource_limits: Optional resource limits configuration

        Example with tool instances:
            ```python
            agent = HybridAgent(
                agent_id="agent1",
                name="My Agent",
                llm_client=OpenAIClient(),
                tools={
                    "search": SearchTool(api_key="..."),
                    "calculator": CalculatorTool()
                },
                config=config
            )
            ```

        Example with tool names (backward compatible):
            ```python
            agent = HybridAgent(
                agent_id="agent1",
                name="My Agent",
                llm_client=OpenAIClient(),
                tools=["search", "calculator"],
                config=config
            )
            ```
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.DEVELOPER,  # Can be adjusted based on use case
            config=config,
            description=description or "Hybrid agent with LLM reasoning and tool execution",
            version=version,
            tools=tools,
            llm_client=llm_client,  # type: ignore[arg-type]
            config_manager=config_manager,
            checkpointer=checkpointer,
            context_engine=context_engine,
            collaboration_enabled=collaboration_enabled,
            agent_registry=agent_registry,
            learning_enabled=learning_enabled,
            resource_limits=resource_limits,
        )

        # Store LLM client reference (from BaseAIAgent or local)
        self.llm_client = self._llm_client if self._llm_client else llm_client
        self._max_iterations = max_iterations
        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []
        self._tool_schemas: List[Dict[str, Any]] = []
        self._use_function_calling: bool = False  # Will be determined during initialization

        logger.info(f"HybridAgent initialized: {agent_id} with LLM ({self.llm_client.provider_name}) " f"and {len(tools) if isinstance(tools, (list, dict)) else 0} tools")

    async def _initialize(self) -> None:
        """Initialize Hybrid agent - validate LLM client, load tools, and build system prompt."""
        # Validate LLM client using BaseAIAgent helper
        self._validate_llm_client()

        # Load tools using BaseAIAgent helper
        self._load_tools()

        # Get tool instances from BaseAIAgent (if provided as instances)
        base_tool_instances = self._get_tool_instances()

        if base_tool_instances:
            # Tool instances were provided - use them directly
            self._tool_instances = base_tool_instances
            logger.info(f"HybridAgent {self.agent_id} using " f"{len(self._tool_instances)} pre-configured tool instances")
        elif self._available_tools:
            # Tool names were provided - load them
            self._tool_instances = {}
            for tool_name in self._available_tools:
                try:
                    self._tool_instances[tool_name] = get_tool(tool_name)
                    logger.debug(f"HybridAgent {self.agent_id} loaded tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to load tool {tool_name}: {e}")

            logger.info(f"HybridAgent {self.agent_id} initialized with {len(self._tool_instances)} tools")

        # Generate tool schemas for Function Calling
        self._generate_tool_schemas()

        # Check if LLM client supports Function Calling
        self._use_function_calling = self._check_function_calling_support()

        # Build system prompt
        self._system_prompt = self._build_system_prompt()

    async def _shutdown(self) -> None:
        """Shutdown Hybrid agent."""
        self._conversation_history.clear()
        if self._tool_instances:
            self._tool_instances.clear()

        if hasattr(self.llm_client, "close"):
            await self.llm_client.close()

        logger.info(f"HybridAgent {self.agent_id} shut down")

    def _build_system_prompt(self) -> str:
        """Build system prompt including tool descriptions.

        Precedence order for base prompt:
        1. config.system_prompt - Direct custom prompt (highest priority)
        2. Assembled from goal/backstory/domain_knowledge
        3. Default: Empty (ReAct instructions will be added)

        Note: ReAct instructions and tool info are always appended regardless
        of whether system_prompt is used, as they're essential for agent operation.
        """
        parts = []

        # 1. Custom system_prompt takes precedence over goal/backstory
        if self._config.system_prompt:
            parts.append(self._config.system_prompt)
        else:
            # 2. Assemble from individual fields
            if self._config.goal:
                parts.append(f"Goal: {self._config.goal}")

            if self._config.backstory:
                parts.append(f"Background: {self._config.backstory}")

            if self._config.domain_knowledge:
                parts.append(f"Domain Knowledge: {self._config.domain_knowledge}")

        # Add ReAct instructions (always required for HybridAgent)
        parts.append(
            "You are a reasoning agent that can use tools to complete tasks. "
            "Follow the ReAct (Reasoning + Acting) pattern:\n"
            "1. THOUGHT: Analyze the task and decide what to do\n"
            "2. ACTION: Use a tool if needed, or provide final answer\n"
            "3. OBSERVATION: Review the tool result and continue reasoning\n\n"
            "RESPONSE FORMAT REQUIREMENTS:\n"
            "- Wrap your thinking process in <THOUGHT>...</THOUGHT> tags\n"
            "- Wrap your insight about tool result in <OBSERVATION>...</OBSERVATION> tags\n"
            "- Tool calls (TOOL:, OPERATION:, PARAMETERS:) MUST be OUTSIDE <THOUGHT> tags\n"
            "- Final answers (FINAL ANSWER:) MUST be OUTSIDE <THOUGHT> tags\n\n"
            "THINKING GUIDANCE:\n"
            "When writing <THOUGHT> sections, consider:\n"
            "- What is the core thing to do?\n"
            "- What information do I already have?\n"
            "- What information do I need to gather?\n"
            "- Which tools would be most helpful?\n"
            "- What action should I take?\n\n"
            "OBSERVATION GUIDANCE:\n"
            "When writing <OBSERVATION> sections, consider:\n"
            "- What did I learn from the tool results?\n"
            "- How does this information inform my next work?\n"
            "- Do I need additional information?\n"
            "- Am I ready to provide a final answer?\n\n"
            "CORRECT FORMAT EXAMPLE:\n"
            "<THOUGHT>\n"
            "I need to search for information about the weather. Let me use the search tool.\n"
            "</THOUGHT>\n\n"
            "TOOL: search\n"
            "OPERATION: query\n"
            "PARAMETERS: {\"q\": \"weather today\"}\n\n"
            "<OBSERVATION>\n"
            "The search tool returned: Today's weather is sunny, 72°F.\n"
            "</OBSERVATION>\n\n"
            "<THOUGHT>\n"
            "I have the weather information. Now I can provide the final answer.\n"
            "</THOUGHT>\n\n"
            "FINAL ANSWER: Today's weather is sunny, 72°F.\n\n"
            "INCORRECT FORMAT (DO NOT DO THIS):\n"
            "<THOUGHT>\n"
            "I need to search.\n"
            "TOOL: search\n"
            "OPERATION: query\n"
            "</THOUGHT>\n"
            "❌ Tool calls must be OUTSIDE the <THOUGHT> tags\n\n"
            "<THOUGHT>\n"
            "I know the answer.\n"
            "FINAL ANSWER: The answer is...\n"
            "</THOUGHT>\n"
            "❌ Final answers must be OUTSIDE the <THOUGHT> tags\n\n"
            "TOOL CALL FORMAT:\n"
            "TOOL: <tool_name>\n"
            "OPERATION: <operation_name>\n"
            "PARAMETERS: <json_parameters>\n\n"
            "FINAL ANSWER FORMAT:\n"
            "FINAL ANSWER: <your_answer>"
        )

        # Add available tools (always required for HybridAgent)
        if self._available_tools:
            parts.append(f"\nAvailable tools: {', '.join(self._available_tools)}")

        return "\n\n".join(parts)

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
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
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            if not task_description:
                raise TaskExecutionError(
                    "Task must contain 'description', 'prompt', or 'task' field",
                    agent_id=self.agent_id,
                )

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Execute ReAct loop
            result = await self._react_loop(task_description, context)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(
                execution_time=execution_time,
                success=True,
                tokens_used=result.get("total_tokens"),
                tool_calls=result.get("tool_calls_count", 0),
            )

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return {
                "success": True,
                "output": result.get("final_answer"),
                "reasoning_steps": result.get("steps"),
                "tool_calls_count": result.get("tool_calls_count"),
                "iterations": result.get("iterations"),
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
                task_id=task.get("task_id"),
            )

    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
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

    async def execute_task_streaming(self, task: Dict[str, Any], context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a task with streaming tokens and tool calls.

        Args:
            task: Task specification with 'description' or 'prompt'
            context: Execution context

        Yields:
            Dict[str, Any]: Event dictionaries with streaming tokens, tool calls, and results

        Example:
            ```python
            async for event in agent.execute_task_streaming(task, context):
                if event['type'] == 'token':
                    print(event['content'], end='', flush=True)
                elif event['type'] == 'tool_call':
                    print(f"\\nCalling {event['tool_name']}...")
                elif event['type'] == 'tool_result':
                    print(f"Result: {event['result']}")
            ```
        """
        start_time = datetime.utcnow()

        try:
            # Extract task description
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            if not task_description:
                yield {
                    "type": "error",
                    "error": "Task must contain 'description', 'prompt', or 'task' field",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Yield status
            yield {
                "type": "status",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Execute streaming ReAct loop
            async for event in self._react_loop_streaming(task_description, context):
                yield event

            # Get final result from last event
            if event.get("type") == "result":
                result = event

                # Calculate execution time
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                # Update metrics
                self.update_metrics(
                    execution_time=execution_time,
                    success=True,
                    tokens_used=result.get("total_tokens"),
                    tool_calls=result.get("tool_calls_count", 0),
                )

                # Transition back to active
                self._transition_state(self.state.__class__.ACTIVE)
                self._current_task_id = None
                self.last_active_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Streaming task execution failed for {self.agent_id}: {e}")

            # Update metrics for failure
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            # Transition to error state
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def process_message_streaming(self, message: str, sender_id: Optional[str] = None) -> AsyncIterator[str]:
        """
        Process a message with streaming response.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Yields:
            str: Response text tokens

        Example:
            ```python
            async for token in agent.process_message_streaming("Hello!"):
                print(token, end='', flush=True)
            ```
        """
        try:
            # Build task from message
            task = {
                "description": message,
                "task_id": f"msg_{datetime.utcnow().timestamp()}",
            }

            # Stream task execution
            async for event in self.execute_task_streaming(task, {"sender_id": sender_id}):
                if event["type"] == "token":
                    yield event["content"]

        except Exception as e:
            logger.error(f"Streaming message processing failed for {self.agent_id}: {e}")
            raise

    async def _react_loop_streaming(self, task: str, context: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute ReAct loop with streaming: Reason → Act → Observe.

        Args:
            task: Task description
            context: Context dictionary

        Yields:
            Dict[str, Any]: Event dictionaries with streaming tokens, tool calls, and results
        """
        steps = []
        tool_calls_count = 0
        total_tokens = 0

        # Build initial messages
        messages = self._build_initial_messages(task, context)

        for iteration in range(self._max_iterations):
            logger.debug(f"HybridAgent {self.agent_id} - ReAct iteration {iteration + 1}")

            # Yield iteration status
            yield {
                "type": "status",
                "status": "thinking",
                "iteration": iteration + 1,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # THINK: Stream LLM reasoning
            thought_tokens = []
            tool_calls_from_stream = None
            
            # Use Function Calling if supported, otherwise use ReAct mode
            if self._use_function_calling and self._tool_schemas:
                # Convert schemas to tools format
                tools = [{"type": "function", "function": schema} for schema in self._tool_schemas]
                # Use return_chunks=True to get tool_calls information
                stream_gen = self.llm_client.stream_text(  # type: ignore[attr-defined]
                    messages=messages,
                    model=self._config.llm_model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                    tools=tools,
                    tool_choice="auto",
                    return_chunks=True,  # Enable tool_calls accumulation
                )
            else:
                # Fallback to ReAct mode
                stream_gen = self.llm_client.stream_text(  # type: ignore[attr-defined]
                    messages=messages,
                    model=self._config.llm_model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )

            # Stream tokens and collect tool calls
            from aiecs.llm.clients.openai_compatible_mixin import StreamChunk
            
            async for chunk in stream_gen:
                # Handle StreamChunk objects (Function Calling mode)
                if isinstance(chunk, StreamChunk):
                    if chunk.type == "token" and chunk.content:
                        thought_tokens.append(chunk.content)
                        yield {
                            "type": "token",
                            "content": chunk.content,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    elif chunk.type == "tool_call" and chunk.tool_call:
                        # Yield tool call update event
                        yield {
                            "type": "tool_call_update",
                            "tool_call": chunk.tool_call,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    elif chunk.type == "tool_calls" and chunk.tool_calls:
                        # Complete tool_calls received
                        tool_calls_from_stream = chunk.tool_calls
                        yield {
                            "type": "tool_calls",
                            "tool_calls": chunk.tool_calls,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                else:
                    # Handle plain string tokens (ReAct mode or non-Function Calling)
                    thought_tokens.append(chunk)
                    yield {
                        "type": "token",
                        "content": chunk,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

            thought_raw = "".join(thought_tokens)
            # Extract thought content from <THOUGHT> tags for parsing (keep raw for display)
            thought = self._extract_thought_content(thought_raw)
            # Use raw thought (with tags) for frontend display
            thought_for_display = thought_raw.strip() if thought_raw.strip() else thought
            
            # Process tool_calls if received from stream
            if tool_calls_from_stream:
                # Process each tool call
                for tool_call in tool_calls_from_stream:
                    try:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]

                        # Parse function name to extract tool and operation
                        # CRITICAL: Try exact match first, then fall back to underscore parsing
                        if self._tool_instances and func_name in self._tool_instances:
                            # Exact match found - use full function name as tool name
                            tool_name = func_name
                            operation = None
                        elif self._available_tools and func_name in self._available_tools:
                            # Exact match in available tools list
                            tool_name = func_name
                            operation = None
                        else:
                            # Fallback: try underscore parsing for legacy compatibility
                            parts = func_name.split("_", 1)
                            if len(parts) == 2:
                                tool_name, operation = parts
                            else:
                                tool_name = parts[0]
                                operation = None

                        # Parse arguments JSON
                        import json
                        if isinstance(func_args, str):
                            parameters = json.loads(func_args)
                        else:
                            parameters = func_args if func_args else {}

                        # Yield tool call event
                        yield {
                            "type": "tool_call",
                            "tool_name": tool_name,
                            "operation": operation,
                            "parameters": parameters,
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Execute tool
                        tool_result = await self._execute_tool(tool_name, operation, parameters)
                        tool_calls_count += 1

                        steps.append(
                            {
                                "type": "action",
                                "tool": tool_name,
                                "operation": operation,
                                "parameters": parameters,
                                "iteration": iteration + 1,
                            }
                        )

                        # Yield tool result event
                        yield {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": tool_result,
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Add tool result to messages
                        observation_content = f"Tool '{tool_name}' returned: {tool_result}"
                        observation = f"<OBSERVATION>\n{observation_content}\n</OBSERVATION>"
                        steps.append(
                            {
                                "type": "observation",
                                "content": observation,
                                "iteration": iteration + 1,
                            }
                        )

                        # Add assistant message with tool call and tool result
                        messages.append(
                            LLMMessage(
                                role="assistant",
                                content=None,
                                tool_calls=tool_calls_from_stream,
                            )
                        )
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=str(tool_result),
                                tool_call_id=tool_call.get("id", "call_0"),
                            )
                        )

                    except Exception as e:
                        error_content = f"Tool execution failed: {str(e)}"
                        error_msg = f"<OBSERVATION>\n{error_content}\n</OBSERVATION>"
                        steps.append(
                            {
                                "type": "observation",
                                "content": error_msg,
                                "iteration": iteration + 1,
                                "error": True,
                            }
                        )
                        yield {
                            "type": "tool_error",
                            "tool_name": tool_name if "tool_name" in locals() else "unknown",
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=error_msg,
                                tool_call_id=tool_call.get("id", "call_0"),
                            )
                        )

                # Continue to next iteration
                continue

            steps.append(
                {
                    "type": "thought",
                    "content": thought_for_display,  # Keep tags for frontend rendering
                    "iteration": iteration + 1,
                }
            )

            # Check if final answer (use extracted thought for parsing)
            if "FINAL ANSWER:" in thought:
                final_answer = self._extract_final_answer(thought)
                yield {
                    "type": "result",
                    "success": True,
                    "output": final_answer,
                    "reasoning_steps": steps,
                    "tool_calls_count": tool_calls_count,
                    "iterations": iteration + 1,
                    "total_tokens": total_tokens,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            # Check if tool call
            if "TOOL:" in thought:
                # ACT: Execute tool
                try:
                    tool_info = self._parse_tool_call(thought)
                    tool_name = tool_info.get("tool", "")
                    if not tool_name:
                        raise ValueError("Tool name not found in tool call")

                    # Yield tool call event
                    yield {
                        "type": "tool_call",
                        "tool_name": tool_name,
                        "operation": tool_info.get("operation"),
                        "parameters": tool_info.get("parameters", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    tool_result = await self._execute_tool(
                        tool_name,
                        tool_info.get("operation"),
                        tool_info.get("parameters", {}),
                    )
                    tool_calls_count += 1

                    steps.append(
                        {
                            "type": "action",
                            "tool": tool_info["tool"],
                            "operation": tool_info.get("operation"),
                            "parameters": tool_info.get("parameters"),
                            "iteration": iteration + 1,
                        }
                    )

                    # OBSERVE: Add tool result to conversation
                    observation_content = f"Tool '{tool_info['tool']}' returned: {tool_result}"
                    observation = f"<OBSERVATION>\n{observation_content}\n</OBSERVATION>"
                    steps.append(
                        {
                            "type": "observation",
                            "content": observation,
                            "iteration": iteration + 1,
                        }
                    )

                    # Yield tool result event
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": tool_result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    # Add to messages for next iteration
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=observation))

                except Exception as e:
                    error_content = f"Tool execution failed: {str(e)}"
                    error_msg = f"<OBSERVATION>\n{error_content}\n</OBSERVATION>"
                    steps.append(
                        {
                            "type": "observation",
                            "content": error_msg,
                            "iteration": iteration + 1,
                            "error": True,
                        }
                    )

                    # Yield error event
                    yield {
                        "type": "tool_error",
                        "tool_name": tool_name if "tool_name" in locals() else "unknown",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=error_msg))

            else:
                # LLM didn't provide clear action - treat as final answer
                yield {
                    "type": "result",
                    "success": True,
                    "output": thought,
                    "reasoning_steps": steps,
                    "tool_calls_count": tool_calls_count,
                    "iterations": iteration + 1,
                    "total_tokens": total_tokens,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

        # Max iterations reached
        logger.warning(f"HybridAgent {self.agent_id} reached max iterations")
        yield {
            "type": "result",
            "success": True,
            "output": "Max iterations reached. Unable to complete task fully.",
            "reasoning_steps": steps,
            "tool_calls_count": tool_calls_count,
            "iterations": self._max_iterations,
            "total_tokens": total_tokens,
            "max_iterations_reached": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _react_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
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
            # Use Function Calling if supported, otherwise use ReAct mode
            if self._use_function_calling and self._tool_schemas:
                # Convert schemas to tools format
                tools = [{"type": "function", "function": schema} for schema in self._tool_schemas]
                response = await self.llm_client.generate_text(
                    messages=messages,
                    model=self._config.llm_model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                    tools=tools,
                    tool_choice="auto",
                )
            else:
                # Fallback to ReAct mode
                response = await self.llm_client.generate_text(
                    messages=messages,
                    model=self._config.llm_model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )

            thought_raw = response.content or ""
            # Extract thought content from <THOUGHT> tags for parsing (keep raw for display)
            thought = self._extract_thought_content(thought_raw)
            # Use raw thought (with tags) for frontend display
            thought_for_display = thought_raw.strip() if thought_raw.strip() else thought
            total_tokens += getattr(response, "total_tokens", 0)

            # Update prompt cache metrics from LLM response
            cache_read_tokens = getattr(response, "cache_read_tokens", None)
            cache_creation_tokens = getattr(response, "cache_creation_tokens", None)
            cache_hit = getattr(response, "cache_hit", None)
            if cache_read_tokens is not None or cache_creation_tokens is not None or cache_hit is not None:
                self.update_cache_metrics(
                    cache_read_tokens=cache_read_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_hit=cache_hit,
                )

            # Check for Function Calling response
            tool_calls = getattr(response, "tool_calls", None)
            function_call = getattr(response, "function_call", None)

            if tool_calls or function_call:
                # Handle Function Calling response
                tool_calls_to_process = tool_calls or []
                if function_call:
                    # Convert legacy function_call to tool_calls format
                    tool_calls_to_process = [
                        {
                            "id": "call_0",
                            "type": "function",
                            "function": {
                                "name": function_call["name"],
                                "arguments": function_call["arguments"],
                            },
                        }
                    ]

                # Process each tool call
                for tool_call in tool_calls_to_process:
                    try:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]

                        # Parse function name to extract tool and operation
                        # CRITICAL: Try exact match first, then fall back to underscore parsing
                        if self._tool_instances and func_name in self._tool_instances:
                            # Exact match found - use full function name as tool name
                            tool_name = func_name
                            operation = None
                        elif self._available_tools and func_name in self._available_tools:
                            # Exact match in available tools list
                            tool_name = func_name
                            operation = None
                        else:
                            # Fallback: try underscore parsing for legacy compatibility
                            parts = func_name.split("_", 1)
                            if len(parts) == 2:
                                tool_name, operation = parts
                            else:
                                tool_name = parts[0]
                                operation = None

                        # Parse arguments JSON
                        import json
                        if isinstance(func_args, str):
                            parameters = json.loads(func_args)
                        else:
                            parameters = func_args if func_args else {}

                        steps.append(
                            {
                                "type": "thought",
                                "content": f"Calling tool {func_name}",
                                "iteration": iteration + 1,
                            }
                        )

                        # Execute tool
                        tool_result = await self._execute_tool(tool_name, operation, parameters)
                        tool_calls_count += 1

                        steps.append(
                            {
                                "type": "action",
                                "tool": tool_name,
                                "operation": operation,
                                "parameters": parameters,
                                "iteration": iteration + 1,
                            }
                        )

                        # Add tool result to messages
                        observation_content = f"Tool '{tool_name}' returned: {tool_result}"
                        observation = f"<OBSERVATION>\n{observation_content}\n</OBSERVATION>"
                        steps.append(
                            {
                                "type": "observation",
                                "content": observation,
                                "iteration": iteration + 1,
                            }
                        )

                        # Add assistant message with tool call and tool result
                        messages.append(
                            LLMMessage(
                                role="assistant",
                                content=None,  # Content is None when using tool calls
                                tool_calls=tool_calls_to_process if tool_calls else None,
                            )
                        )
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=str(tool_result),
                                tool_call_id=tool_call.get("id", "call_0"),
                            )
                        )

                    except Exception as e:
                        error_content = f"Tool execution failed: {str(e)}"
                        error_msg = f"<OBSERVATION>\n{error_content}\n</OBSERVATION>"
                        steps.append(
                            {
                                "type": "observation",
                                "content": error_msg,
                                "iteration": iteration + 1,
                                "error": True,
                            }
                        )
                        # Add error to messages
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=error_msg,
                                tool_call_id=tool_call.get("id", "call_0"),
                            )
                        )

                # Continue to next iteration
                continue

            # If using Function Calling and no tool calls, check if we have a final answer
            if self._use_function_calling and thought:
                # LLM provided a text response without tool calls - treat as final answer
                # Extract final answer if FINAL ANSWER: marker is present
                final_answer = self._extract_final_answer(thought) if "FINAL ANSWER:" in thought else thought
                return {
                    "final_answer": final_answer,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "total_tokens": total_tokens,
                }

            steps.append(
                {
                    "type": "thought",
                    "content": thought_for_display,  # Keep tags for frontend rendering
                    "iteration": iteration + 1,
                }
            )

            # Check if final answer (ReAct mode, use extracted thought for parsing)
            if "FINAL ANSWER:" in thought:
                final_answer = self._extract_final_answer(thought)
                return {
                    "final_answer": final_answer,
                    "steps": steps,
                    "iterations": iteration + 1,
                    "tool_calls_count": tool_calls_count,
                    "total_tokens": total_tokens,
                }

            # Check if tool call (ReAct mode)
            if "TOOL:" in thought:
                # ACT: Execute tool
                try:
                    tool_info = self._parse_tool_call(thought)
                    tool_name = tool_info.get("tool", "")
                    if not tool_name:
                        raise ValueError("Tool name not found in tool call")
                    tool_result = await self._execute_tool(
                        tool_name,
                        tool_info.get("operation"),
                        tool_info.get("parameters", {}),
                    )
                    tool_calls_count += 1

                    steps.append(
                        {
                            "type": "action",
                            "tool": tool_info["tool"],
                            "operation": tool_info.get("operation"),
                            "parameters": tool_info.get("parameters"),
                            "iteration": iteration + 1,
                        }
                    )

                    # OBSERVE: Add tool result to conversation
                    observation_content = f"Tool '{tool_info['tool']}' returned: {tool_result}"
                    observation = f"<OBSERVATION>\n{observation_content}\n</OBSERVATION>"
                    steps.append(
                        {
                            "type": "observation",
                            "content": observation,
                            "iteration": iteration + 1,
                        }
                    )

                    # Add to messages for next iteration
                    messages.append(LLMMessage(role="assistant", content=thought))
                    messages.append(LLMMessage(role="user", content=observation))

                except Exception as e:
                    error_content = f"Tool execution failed: {str(e)}"
                    error_msg = f"<OBSERVATION>\n{error_content}\n</OBSERVATION>"
                    steps.append(
                        {
                            "type": "observation",
                            "content": error_msg,
                            "iteration": iteration + 1,
                            "error": True,
                        }
                    )
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

    def _build_initial_messages(self, task: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """Build initial messages for ReAct loop."""
        messages = []

        # Add system prompt with cache control if caching is enabled
        if self._system_prompt:
            cache_control = (
                CacheControl(type="ephemeral")
                if self._config.enable_prompt_caching
                else None
            )
            messages.append(
                LLMMessage(
                    role="system",
                    content=self._system_prompt,
                    cache_control=cache_control,
                )
            )

        # Add context if provided
        if context:
            # Special handling: if context contains 'history' as a list of messages,
            # add them as separate user/assistant messages instead of formatting
            history = context.get("history")
            if isinstance(history, list) and len(history) > 0:
                # Check if history contains message-like dictionaries
                for msg in history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        # Valid message format - add as separate message
                        messages.append(
                            LLMMessage(
                                role=msg["role"],
                                content=msg["content"],
                            )
                        )
                    elif isinstance(msg, LLMMessage):
                        # Already an LLMMessage instance
                        messages.append(msg)
            
            # Format remaining context fields (excluding history) as Additional Context
            context_without_history = {k: v for k, v in context.items() if k != "history"}
            if context_without_history:
                context_str = self._format_context(context_without_history)
                if context_str:
                    messages.append(
                        LLMMessage(
                            role="user",
                            content=f"Additional Context:\n{context_str}",
                        )
                    )

        # Add task
        messages.append(LLMMessage(role="user", content=f"Task: {task}"))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []
        for key, value in context.items():
            if not key.startswith("_") and value is not None:
                relevant_fields.append(f"{key}: {value}")
        return "\n".join(relevant_fields) if relevant_fields else ""

    def _extract_thought_content(self, text: str) -> str:
        """
        Extract content from <THOUGHT>...</THOUGHT> tags.
        
        If tags are present, extracts the content inside them.
        Otherwise, returns the original text.
        
        Args:
            text: Text that may contain THOUGHT tags
            
        Returns:
            Extracted thought content or original text
        """
        import re
        
        # Try to extract content from <THOUGHT>...</THOUGHT> tags
        thought_pattern = r'<THOUGHT>(.*?)</THOUGHT>'
        match = re.search(thought_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If no tags found, return original text
        return text.strip()
    
    def _extract_observation_content(self, text: str) -> str:
        """
        Extract content from <OBSERVATION>...</OBSERVATION> tags.
        
        If tags are present, extracts the content inside them.
        Otherwise, returns the original text.
        
        Args:
            text: Text that may contain OBSERVATION tags
            
        Returns:
            Extracted observation content or original text
        """
        import re
        
        # Try to extract content from <OBSERVATION>...</OBSERVATION> tags
        observation_pattern = r'<OBSERVATION>(.*?)</OBSERVATION>'
        match = re.search(observation_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # If no tags found, return original text
        return text.strip()

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
            tool_line = [line for line in thought.split("\n") if line.startswith("TOOL:")][0]
            result["tool"] = tool_line.split("TOOL:", 1)[1].strip()

        # Extract operation (optional)
        if "OPERATION:" in thought:
            op_line = [line for line in thought.split("\n") if line.startswith("OPERATION:")][0]
            result["operation"] = op_line.split("OPERATION:", 1)[1].strip()

        # Extract parameters (optional)
        if "PARAMETERS:" in thought:
            param_line = [line for line in thought.split("\n") if line.startswith("PARAMETERS:")][0]
            param_str = param_line.split("PARAMETERS:", 1)[1].strip()
            try:
                result["parameters"] = json.loads(param_str)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse parameters: {param_str}")
                result["parameters"] = {}  # type: ignore[assignment]

        return result

    async def _execute_tool(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any],
    ) -> Any:
        """Execute a tool operation."""
        # Check access
        if not self._available_tools or tool_name not in self._available_tools:
            raise ToolAccessDeniedError(self.agent_id, tool_name)

        if not self._tool_instances:
            raise ValueError(f"Tool instances not available for {tool_name}")
        tool = self._tool_instances.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not loaded")

        # Execute tool
        if operation:
            result = await tool.run_async(operation, **parameters)
        else:
            if hasattr(tool, "run_async"):
                result = await tool.run_async(**parameters)
            else:
                raise ValueError(f"Tool {tool_name} requires operation to be specified")

        return result

    async def _execute_tool_with_observation(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any],
    ) -> "ToolObservation":
        """
        Execute a tool and return structured observation.

        Wraps tool execution with automatic success/error tracking,
        execution time measurement, and structured result formatting.

        Args:
            tool_name: Name of the tool to execute
            operation: Optional operation name
            parameters: Tool parameters

        Returns:
            ToolObservation with execution details

        Example:
            ```python
            obs = await agent._execute_tool_with_observation(
                tool_name="search",
                operation="query",
                parameters={"q": "AI"}
            )
            print(obs.to_text())
            ```
        """

        start_time = datetime.utcnow()

        try:
            # Execute tool
            result = await self._execute_tool(tool_name, operation, parameters)

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create observation
            observation = ToolObservation(
                tool_name=tool_name,
                parameters=parameters,
                result=result,
                success=True,
                error=None,
                execution_time_ms=execution_time_ms,
            )

            logger.info(f"Tool '{tool_name}' executed successfully in {execution_time_ms:.2f}ms")

            return observation

        except Exception as e:
            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            # Create error observation
            observation = ToolObservation(
                tool_name=tool_name,
                parameters=parameters,
                result=None,
                success=False,
                error=str(e),
                execution_time_ms=execution_time_ms,
            )

            logger.error(f"Tool '{tool_name}' failed after {execution_time_ms:.2f}ms: {e}")

            return observation

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self._available_tools.copy() if self._available_tools else []

    def _generate_tool_schemas(self) -> None:
        """Generate OpenAI Function Calling schemas for available tools."""
        if not self._tool_instances:
            return

        try:
            # Use ToolSchemaGenerator to generate schemas from tool instances
            self._tool_schemas = ToolSchemaGenerator.generate_schemas_for_tool_instances(
                self._tool_instances
            )
            logger.info(f"HybridAgent {self.agent_id} generated {len(self._tool_schemas)} tool schemas")
        except Exception as e:
            logger.warning(f"Failed to generate tool schemas: {e}. Falling back to ReAct mode.")
            self._tool_schemas = []

    def _check_function_calling_support(self) -> bool:
        """
        Check if LLM client supports Function Calling.

        Returns:
            True if Function Calling is supported, False otherwise
        """
        # Check if we have tools and schemas
        if not self._tool_instances or not self._tool_schemas:
            return False

        # Check if LLM client supports Function Calling
        # OpenAI, xAI (OpenAI-compatible), Google Vertex AI, and some other providers support it
        provider_name = getattr(self.llm_client, "provider_name", "").lower()
        supported_providers = ["openai", "xai", "anthropic", "vertex"]
        
        # Note: Google Vertex AI uses FunctionDeclaration format, but it's handled via GoogleFunctionCallingMixin
        # The mixin converts OpenAI format to Google format internally

        # Also check if generate_text method accepts 'tools' or 'functions' parameter
        import inspect
        try:
            sig = inspect.signature(self.llm_client.generate_text)
            params = sig.parameters
            has_tools_param = "tools" in params or "functions" in params
        except (ValueError, TypeError):
            # If signature inspection fails, assume not supported
            has_tools_param = False

        return provider_name in supported_providers or has_tools_param

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
        raise NotImplementedError("HybridAgent.from_dict requires LLM client to be provided separately. " "Use constructor instead.")

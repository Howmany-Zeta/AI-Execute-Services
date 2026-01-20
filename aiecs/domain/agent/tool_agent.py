"""
Tool Agent

Agent implementation specialized in tool usage and execution.
Supports LLM + Function Calling mode for intelligent tool selection and execution.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, AsyncIterator
from datetime import datetime

from aiecs.llm import BaseLLMClient, CacheControl, LLMMessage
from aiecs.tools import get_tool, BaseTool
from aiecs.domain.agent.tools.schema_generator import ToolSchemaGenerator

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration
from .exceptions import TaskExecutionError, ToolAccessDeniedError

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )

logger = logging.getLogger(__name__)


class ToolAgent(BaseAIAgent):
    """
    Agent specialized in tool selection and execution with LLM-powered intelligence.

    This agent combines LLM reasoning with tool execution using Function Calling mode
    (non-ReAct pattern). Unlike HybridAgent which uses iterative ReAct loops,
    ToolAgent uses a single LLM call with function calling to select and execute tools.

    **Mode of Operation:**
    - LLM-powered mode (with llm_client): LLM selects tools via Function Calling,
      then agent executes them. Supports streaming of tool calls and results.
    - Direct mode (without llm_client): Execute tools directly with explicit task spec.

    **Tool Configuration:**
    - Tool names (List[str]): Backward compatible, tools loaded by name
    - Tool instances (Dict[str, BaseTool]): Pre-configured tools with preserved state

    **Streaming Events (for execute_task_streaming):**
    - type='status': Agent status updates
    - type='token': LLM response tokens (reasoning)
    - type='tool_call': Tool being called (name, operation, parameters)
    - type='tool_call_update': Incremental tool call data during streaming
    - type='tool_calls': Complete tool_calls list from LLM
    - type='tool_result': Tool execution result
    - type='tool_error': Tool execution error
    - type='result': Final result

    Examples:
        # Example 1: LLM-powered tool agent with function calling
        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            llm_client=OpenAIClient(),
            tools=["search", "calculator"],
            config=config
        )

        # LLM selects appropriate tool via function calling
        result = await agent.execute_task({
            "description": "Calculate 5 + 3 and search for weather"
        }, {})

        # Example 2: Direct tool execution (backward compatible, no LLM)
        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            tools=["search", "calculator"],
            config=config
        )

        result = await agent.execute_task({
            "tool": "calculator",
            "operation": "add",
            "parameters": {"a": 5, "b": 3}
        }, {})

        # Example 3: Streaming with tool calls
        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            llm_client=OpenAIClient(),
            tools={"search": SearchTool(), "calculator": CalculatorTool()},
            config=config
        )

        async for event in agent.execute_task_streaming(task, context):
            if event['type'] == 'token':
                print(event['content'], end='', flush=True)
            elif event['type'] == 'tool_call':
                print(f"\\nCalling {event['tool_name']}...")
            elif event['type'] == 'tool_result':
                print(f"Result: {event['result']}")

        # Example 4: Full-featured agent with all options
        from aiecs.domain.context import ContextEngine
        from aiecs.domain.agent.models import ResourceLimits

        context_engine = ContextEngine()
        await context_engine.initialize()

        resource_limits = ResourceLimits(
            max_concurrent_tasks=5,
            max_tool_calls_per_minute=100
        )

        agent = ToolAgent(
            agent_id="agent1",
            name="My Tool Agent",
            llm_client=OpenAIClient(),
            tools={
                "search": ContextAwareSearchTool(api_key="...", context_engine=context_engine),
                "calculator": StatefulCalculatorTool()
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
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        tools: Union[List[str], Dict[str, BaseTool]],
        config: AgentConfiguration,
        llm_client: Optional[Union[BaseLLMClient, "LLMClientProtocol"]] = None,
        description: Optional[str] = None,
        version: str = "1.0.0",
        config_manager: Optional["ConfigManagerProtocol"] = None,
        checkpointer: Optional["CheckpointerProtocol"] = None,
        context_engine: Optional[Any] = None,
        collaboration_enabled: bool = False,
        agent_registry: Optional[Dict[str, Any]] = None,
        learning_enabled: bool = False,
        resource_limits: Optional[Any] = None,
    ):
        """
        Initialize Tool agent.

        Args:
            agent_id: Unique agent identifier
            name: Agent name
            tools: Tools - either list of tool names or dict of tool instances
            config: Agent configuration
            llm_client: Optional LLM client for intelligent tool selection (Function Calling mode)
            description: Optional description
            version: Agent version
            config_manager: Optional configuration manager for dynamic config
            checkpointer: Optional checkpointer for state persistence
            context_engine: Optional context engine for persistent storage
            collaboration_enabled: Enable collaboration features
            agent_registry: Registry of other agents for collaboration
            learning_enabled: Enable learning features
            resource_limits: Optional resource limits configuration

        Example with LLM-powered tool selection:
            ```python
            agent = ToolAgent(
                agent_id="agent1",
                name="My Tool Agent",
                llm_client=OpenAIClient(),
                tools={
                    "search": SearchTool(api_key="..."),
                    "calculator": CalculatorTool()
                },
                config=config
            )
            # LLM selects tools via function calling
            result = await agent.execute_task({"description": "Calculate 5 + 3"}, {})
            ```

        Example with direct tool execution (backward compatible):
            ```python
            agent = ToolAgent(
                agent_id="agent1",
                name="My Tool Agent",
                tools=["search", "calculator"],
                config=config
            )
            result = await agent.execute_task({
                "tool": "calculator",
                "operation": "add",
                "parameters": {"a": 5, "b": 3}
            }, {})
            ```
        """
        super().__init__(
            agent_id=agent_id,
            name=name,
            agent_type=AgentType.TASK_EXECUTOR,
            config=config,
            description=description or "Tool-based task execution agent with LLM intelligence",
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

        # Store LLM client reference
        self.llm_client = self._llm_client if self._llm_client else llm_client
        self._tool_instances: Dict[str, BaseTool] = {}
        self._tool_usage_stats: Dict[str, Dict[str, int]] = {}
        self._tool_schemas: List[Dict[str, Any]] = []
        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []

        tool_count = len(tools) if isinstance(tools, (list, dict)) else 0
        llm_info = f" with LLM ({self.llm_client.provider_name})" if self.llm_client else ""
        logger.info(f"ToolAgent initialized: {agent_id}{llm_info} and {tool_count} tools")

    async def _initialize(self) -> None:
        """Initialize Tool agent - load tools, validate LLM client, generate schemas."""
        # Validate LLM client if provided
        if self.llm_client:
            self._validate_llm_client()

        # Load tools using shared method from BaseAIAgent
        self._tool_instances = self._initialize_tools_from_config()
        logger.info(
            f"ToolAgent {self.agent_id} initialized with "
            f"{len(self._tool_instances)} tools"
        )

        # Generate tool schemas for Function Calling
        if self.llm_client:
            self._generate_tool_schemas()

        # Build system prompt
        self._system_prompt = self._build_system_prompt()

        # Initialize usage stats for all tools
        for tool_name in self._tool_instances.keys():
            self._tool_usage_stats[tool_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
            }

    async def _shutdown(self) -> None:
        """Shutdown Tool agent."""
        self._tool_instances.clear()
        self._conversation_history.clear()

        # Close LLM client if present
        if self.llm_client and hasattr(self.llm_client, "close"):
            await self.llm_client.close()

        logger.info(f"ToolAgent {self.agent_id} shut down")

    def _build_system_prompt(self) -> str:
        """Build system prompt for tool selection.

        If skills are enabled and attached, skill context is included to provide
        domain knowledge and guide tool selection.
        """
        parts = []

        # Get base prompt from shared method
        base_prompt = self._build_base_system_prompt()
        if base_prompt != "You are a helpful AI assistant.":
            parts.append(base_prompt)

        # Add skill context if skills are enabled and attached
        # This provides domain knowledge and tool recommendations for tool selection
        if self._config.skills_enabled and self._attached_skills:
            skill_context = self.get_skill_context(include_all_skills=True)
            if skill_context:
                parts.append(skill_context)

        # Add tool agent instructions
        parts.append(
            "You are a tool-executing agent. Your role is to select and use the "
            "appropriate tools to complete tasks. Use the provided function calling "
            "interface to invoke tools. Execute tools as needed and provide the results."
        )

        # Add available tools description
        if self._available_tools:
            parts.append(f"\nAvailable tools: {', '.join(self._available_tools)}")

        return "\n\n".join(parts)

    def _generate_tool_schemas(self) -> None:
        """Generate OpenAI Function Calling schemas for available tools."""
        if not self._tool_instances:
            return

        try:
            self._tool_schemas = ToolSchemaGenerator.generate_schemas_for_tool_instances(
                self._tool_instances
            )
            logger.info(f"ToolAgent {self.agent_id} generated {len(self._tool_schemas)} tool schemas")
        except Exception as e:
            logger.warning(f"Failed to generate tool schemas: {e}. Function calling disabled.")
            self._tool_schemas = []

    def _check_function_calling_support(self) -> bool:
        """Check if LLM client supports Function Calling."""
        if not self.llm_client or not self._tool_schemas:
            return False

        import inspect

        provider_name = getattr(self.llm_client, "provider_name", "").lower()
        supported_providers = ["openai", "xai", "anthropic", "vertex"]

        try:
            sig = inspect.signature(self.llm_client.generate_text)
            params = sig.parameters
            has_tools_param = "tools" in params or "functions" in params
        except (ValueError, TypeError):
            has_tools_param = False

        return provider_name in supported_providers or has_tools_param

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using tools.

        Supports three modes:
        1. LLM mode (with llm_client): LLM selects tools via Function Calling
        2. Explicit format (backward compatible): {'tool': 'name', 'operation': 'op', 'parameters': {...}}
        3. Function call format: {'function_call': {'name': 'tool', 'arguments': {...}}}

        Args:
            task: Task specification with 'description' (LLM mode), or 'tool' + 'parameters' (direct mode)
            context: Execution context

        Returns:
            Execution result with 'output', 'tool_used', 'execution_time', 'tool_results'

        Raises:
            TaskExecutionError: If task execution fails
        """
        start_time = datetime.utcnow()
        tool_name: Optional[str] = None

        try:
            # Check if we should use LLM mode
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            use_llm_mode = (
                self.llm_client is not None
                and self._tool_schemas
                and task_description
                and not task.get("tool")  # Not explicit tool specification
            )

            if use_llm_mode:
                # LLM-powered Function Calling mode
                return await self._execute_with_llm(task, context, start_time)

            # Direct tool execution mode (backward compatible)
            tool_name = task.get("tool")
            operation = task.get("operation")
            parameters = task.get("parameters", {})

            # Check for function_call format
            if not tool_name and "function_call" in task:
                function_call = task["function_call"]
                tool_name = function_call.get("name")
                operation = function_call.get("operation")
                parameters = function_call.get("arguments", {})

            if not tool_name:
                raise TaskExecutionError(
                    "Task must contain 'description' (LLM mode), 'tool' field, or 'function_call'",
                    agent_id=self.agent_id,
                )

            # Check tool access
            if not self._available_tools or tool_name not in self._available_tools:
                raise ToolAccessDeniedError(self.agent_id, tool_name)

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Execute tool directly
            result = await self._execute_tool(tool_name, operation, parameters)

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            # Update metrics
            self.update_metrics(execution_time=execution_time, success=True, tool_calls=1)
            self._update_tool_stats(tool_name, success=True)

            # Transition back to active
            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return {
                "success": True,
                "output": result,
                "tool_used": tool_name,
                "operation": operation,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Task execution failed for {self.agent_id}: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

            if tool_name:
                self._update_tool_stats(tool_name, success=False)

            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            raise TaskExecutionError(
                f"Task execution failed: {str(e)}",
                agent_id=self.agent_id,
                task_id=task.get("task_id"),
            )

    async def _execute_with_llm(
        self, task: Dict[str, Any], context: Dict[str, Any], start_time: datetime
    ) -> Dict[str, Any]:
        """Execute task using LLM Function Calling mode."""
        task_description = self._extract_task_description(task)
        tool_calls_count = 0
        tool_results: List[Dict[str, Any]] = []

        # Transition to busy state
        self._transition_state(self.state.__class__.BUSY)
        self._current_task_id = task.get("task_id")

        # Build messages
        messages = self._build_messages(task_description, context)

        # Convert schemas to tools format
        tools = [{"type": "function", "function": schema} for schema in self._tool_schemas]

        # Call LLM with Function Calling
        response = await self.llm_client.generate_text(  # type: ignore[union-attr]
            messages=messages,
            model=self._config.llm_model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            context=context,
            tools=tools,
            tool_choice="auto",
        )

        # Get LLM response content
        llm_response = response.content or ""

        # Check for tool_calls in response
        response_tool_calls = getattr(response, "tool_calls", None)
        function_call = getattr(response, "function_call", None)

        if response_tool_calls or function_call:
            # Process tool calls
            calls_to_process = response_tool_calls or []
            if function_call:
                calls_to_process = [{
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": function_call["name"],
                        "arguments": function_call["arguments"],
                    },
                }]

            for tool_call in calls_to_process:
                try:
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    # Parse tool name and operation
                    tool_name, operation = self._parse_function_name(func_name)

                    # Parse arguments
                    if isinstance(func_args, str):
                        parameters = json.loads(func_args)
                    else:
                        parameters = func_args if func_args else {}

                    # Execute tool
                    tool_result = await self._execute_tool(tool_name, operation, parameters)
                    tool_calls_count += 1
                    self._update_tool_stats(tool_name, success=True)

                    tool_results.append({
                        "tool": tool_name,
                        "operation": operation,
                        "parameters": parameters,
                        "result": tool_result,
                        "success": True,
                    })

                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    tool_results.append({
                        "tool": func_name if "func_name" in locals() else "unknown",
                        "error": str(e),
                        "success": False,
                    })

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Update metrics
        self.update_metrics(
            execution_time=execution_time,
            success=True,
            tokens_used=getattr(response, "total_tokens", None),
            tool_calls=tool_calls_count,
        )

        # Transition back to active
        self._transition_state(self.state.__class__.ACTIVE)
        self._current_task_id = None
        self.last_active_at = datetime.utcnow()

        return {
            "success": True,
            "output": tool_results[-1]["result"] if tool_results else llm_response,
            "llm_response": llm_response,
            "tool_results": tool_results,
            "tool_calls_count": tool_calls_count,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _parse_function_name(self, func_name: str) -> tuple:
        """Parse function name to extract tool and operation."""
        # Try exact match first
        if self._tool_instances and func_name in self._tool_instances:
            return func_name, None
        if self._available_tools and func_name in self._available_tools:
            return func_name, None

        # Fallback: underscore parsing
        parts = func_name.split("_", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return parts[0], None

    def _build_messages(self, user_message: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """Build LLM messages for function calling.

        If skills are enabled and attached, request-specific skill context is added
        to help guide tool selection for the specific user request.
        """
        messages = []

        # Add system prompt
        if self._system_prompt:
            cache_control = (
                CacheControl(type="ephemeral")
                if self._config.enable_prompt_caching
                else None
            )
            messages.append(
                LLMMessage(role="system", content=self._system_prompt, cache_control=cache_control)
            )

        # Add context if provided
        if context:
            context_str = self._format_context(context)
            if context_str:
                messages.append(LLMMessage(role="system", content=f"Context:\n{context_str}"))

        # Add request-specific skill context if skills are enabled
        # This provides skills matched to the specific user request for tool selection
        if self._config.skills_enabled and self._attached_skills:
            skill_context = self.get_skill_context(
                request=user_message,
                include_all_skills=False,  # Only include matched skills
            )
            if skill_context:
                messages.append(
                    LLMMessage(
                        role="system",
                        content=f"Relevant Skills for this Request:\n{skill_context}",
                    )
                )

        # Add user message
        messages.append(LLMMessage(role="user", content=user_message))

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []
        for key, value in context.items():
            if not key.startswith("_") and value is not None:
                relevant_fields.append(f"{key}: {value}")
        return "\n".join(relevant_fields) if relevant_fields else ""

    async def process_message(self, message: str, sender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process an incoming message.

        If llm_client is available, uses LLM + Function Calling to process the message.
        Otherwise, returns available tools info.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Returns:
            Response dictionary
        """
        if self.llm_client and self._tool_schemas:
            # Use LLM mode
            task = {"description": message, "task_id": f"msg_{datetime.utcnow().timestamp()}"}
            result = await self.execute_task(task, {"sender_id": sender_id})
            return {
                "response": result.get("output"),
                "tool_results": result.get("tool_results", []),
                "timestamp": result.get("timestamp"),
            }

        # Direct mode - return available tools info
        available_tools_str = ", ".join(self._available_tools) if self._available_tools else "none"
        return {
            "response": (
                f"ToolAgent {self.name} received message but requires explicit tool tasks. "
                f"Available tools: {available_tools_str}"
            ),
            "available_tools": self._available_tools or [],
        }

    async def execute_task_streaming(
        self, task: Dict[str, Any], context: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a task with streaming tokens, tool calls, and tool results.

        Args:
            task: Task specification with 'description' (LLM mode) or tool specification
            context: Execution context

        Yields:
            Dict[str, Any]: Event dictionaries with streaming tokens, tool calls, and results

        Event types:
            - type='status': Agent status updates
            - type='token': LLM response tokens
            - type='tool_call': Tool being called
            - type='tool_call_update': Incremental tool call data
            - type='tool_calls': Complete tool_calls list
            - type='tool_result': Tool execution result
            - type='tool_error': Tool execution error
            - type='result': Final result

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
            # Check if we should use LLM mode
            task_description = task.get("description") or task.get("prompt") or task.get("task")
            use_llm_mode = (
                self.llm_client is not None
                and self._tool_schemas
                and task_description
                and not task.get("tool")
            )

            if not use_llm_mode:
                # Direct mode - execute and yield result
                result = await self.execute_task(task, context)
                yield {
                    "type": "result",
                    "success": result.get("success", True),
                    "output": result.get("output"),
                    "tool_used": result.get("tool_used"),
                    "execution_time": result.get("execution_time"),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            # LLM streaming mode
            async for event in self._execute_with_llm_streaming(task, context, start_time):
                yield event

        except Exception as e:
            logger.error(f"Streaming task execution failed for {self.agent_id}: {e}")
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)
            self._transition_state(self.state.__class__.ERROR)
            self._current_task_id = None

            yield {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _execute_with_llm_streaming(
        self, task: Dict[str, Any], context: Dict[str, Any], start_time: datetime
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute task using LLM Function Calling with streaming."""
        task_description = self._extract_task_description(task)
        tool_calls_count = 0
        tool_results: List[Dict[str, Any]] = []

        # Transition to busy state
        self._transition_state(self.state.__class__.BUSY)
        self._current_task_id = task.get("task_id")

        yield {
            "type": "status",
            "status": "started",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Build messages
        messages = self._build_messages(task_description, context)

        # Convert schemas to tools format
        tools = [{"type": "function", "function": schema} for schema in self._tool_schemas]

        # Stream LLM response
        response_tokens: List[str] = []
        tool_calls_from_stream = None

        # Import StreamChunk for type checking
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        stream_gen = self.llm_client.stream_text(  # type: ignore[union-attr]
            messages=messages,
            model=self._config.llm_model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            context=context,
            tools=tools,
            tool_choice="auto",
            return_chunks=True,
        )

        async for chunk in stream_gen:
            if isinstance(chunk, StreamChunk):
                if chunk.type == "token" and chunk.content:
                    response_tokens.append(chunk.content)
                    yield {
                        "type": "token",
                        "content": chunk.content,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                elif chunk.type == "tool_call" and chunk.tool_call:
                    yield {
                        "type": "tool_call_update",
                        "tool_call": chunk.tool_call,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                elif chunk.type == "tool_calls" and chunk.tool_calls:
                    tool_calls_from_stream = chunk.tool_calls
                    yield {
                        "type": "tool_calls",
                        "tool_calls": chunk.tool_calls,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            else:
                # Plain string token
                response_tokens.append(chunk)
                yield {
                    "type": "token",
                    "content": chunk,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        llm_response = "".join(response_tokens)

        # Process tool calls if received
        if tool_calls_from_stream:
            for tool_call in tool_calls_from_stream:
                try:
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    tool_name, operation = self._parse_function_name(func_name)

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
                    self._update_tool_stats(tool_name, success=True)

                    tool_results.append({
                        "tool": tool_name,
                        "operation": operation,
                        "parameters": parameters,
                        "result": tool_result,
                        "success": True,
                    })

                    # Yield tool result event
                    yield {
                        "type": "tool_result",
                        "tool_name": tool_name,
                        "result": tool_result,
                        "timestamp": datetime.utcnow().isoformat(),
                    }

                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    yield {
                        "type": "tool_error",
                        "tool_name": func_name if "func_name" in locals() else "unknown",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    tool_results.append({
                        "tool": func_name if "func_name" in locals() else "unknown",
                        "error": str(e),
                        "success": False,
                    })

        # Calculate execution time
        execution_time = (datetime.utcnow() - start_time).total_seconds()

        # Update metrics
        self.update_metrics(
            execution_time=execution_time,
            success=True,
            tool_calls=tool_calls_count,
        )

        # Transition back to active
        self._transition_state(self.state.__class__.ACTIVE)
        self._current_task_id = None
        self.last_active_at = datetime.utcnow()

        # AIECS Fix: Ensure final response is streamed when tokens weren't received
        # Some LLM providers (e.g., Vertex AI) don't stream tokens in function calling mode
        # when the model decides not to call any tools. In this case, yield the complete
        # response as a single token to ensure consumers receive the content.
        tokens_were_streamed = len(response_tokens) > 0
        if not tokens_were_streamed and tool_calls_count == 0 and llm_response:
            # No tokens were streamed and no tools were called - yield response as token
            logger.debug(f"Yielding unstreamed LLM response as fallback token ({len(llm_response)} chars)")
            yield {
                "type": "token",
                "content": llm_response,
                "timestamp": datetime.utcnow().isoformat(),
                "is_fallback": True,  # Flag to indicate this is a fallback, not true streaming
            }

        # Yield final result
        yield {
            "type": "result",
            "success": True,
            "output": tool_results[-1]["result"] if tool_results else llm_response,
            "llm_response": llm_response,
            "tool_results": tool_results,
            "tool_calls_count": tool_calls_count,
            "execution_time": execution_time,
            "tokens_streamed": tokens_were_streamed,  # Add flag for debugging
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def process_message_streaming(
        self, message: str, sender_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Process a message with streaming response.

        Args:
            message: Message content
            sender_id: Optional sender identifier

        Yields:
            str: Response text tokens

        Example:
            ```python
            async for token in agent.process_message_streaming("Search for AI news"):
                print(token, end='', flush=True)
            ```
        """
        try:
            task = {"description": message, "task_id": f"msg_{datetime.utcnow().timestamp()}"}

            async for event in self.execute_task_streaming(task, {"sender_id": sender_id}):
                if event["type"] == "token":
                    yield event["content"]

        except Exception as e:
            logger.error(f"Streaming message processing failed for {self.agent_id}: {e}")
            raise

    async def _execute_tool(
        self,
        tool_name: str,
        operation: Optional[str],
        parameters: Dict[str, Any],
    ) -> Any:
        """
        Execute a tool operation.

        Args:
            tool_name: Tool name
            operation: Operation name (optional for tools with single operation)
            parameters: Operation parameters

        Returns:
            Tool execution result
        """
        tool = self._tool_instances.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not loaded")

        # Execute tool
        if operation:
            result = await tool.run_async(operation, **parameters)
        else:
            # If no operation specified, try to call the tool directly
            if hasattr(tool, "run_async"):
                result = await tool.run_async(**parameters)
            else:
                raise ValueError(f"Tool {tool_name} requires operation to be specified")

        return result

    def _validate_llm_client(self) -> None:
        """Validate LLM client has required methods."""
        if not self.llm_client:
            return

        required_methods = ["generate_text"]
        for method in required_methods:
            if not hasattr(self.llm_client, method):
                raise ValueError(
                    f"LLM client must have '{method}' method. "
                    f"Got: {type(self.llm_client).__name__}"
                )

    def _extract_task_description(self, task: Dict[str, Any]) -> str:
        """Extract task description from various task formats."""
        description = (
            task.get("description")
            or task.get("prompt")
            or task.get("task")
            or task.get("query")
            or task.get("message")
        )
        if not description:
            raise ValueError("Task must contain 'description', 'prompt', 'task', 'query', or 'message'")
        return description

    def _update_tool_stats(self, tool_name: str, success: bool) -> None:
        """Update tool usage statistics."""
        if tool_name not in self._tool_usage_stats:
            self._tool_usage_stats[tool_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
            }

        stats = self._tool_usage_stats[tool_name]
        stats["total_count"] += 1
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1

    def get_tool_stats(self) -> Dict[str, Dict[str, int]]:
        """Get tool usage statistics."""
        return self._tool_usage_stats.copy()

    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return self._available_tools.copy() if self._available_tools else []

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolAgent":
        """
        Deserialize ToolAgent from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ToolAgent instance
        """
        raise NotImplementedError("ToolAgent.from_dict not fully implemented yet")

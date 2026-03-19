"""
Hybrid Agent

Agent implementation combining LLM reasoning with tool execution capabilities.
Uses OpenAI Function Calling for tool use (BetaToolRunner-style loop).

.. deprecated::
    ReAct text format (TOOL:/OPERATION:/PARAMETERS:, FINAL RESPONSE: finish) is no longer
    supported. Use OpenAI-compatible Function Calling with an LLM client that supports
    tools (OpenAI, xAI, Anthropic, Vertex).
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, AsyncGenerator
from datetime import datetime

from aiecs.llm import BaseLLMClient, CacheControl, LLMMessage
from aiecs.tools import BaseTool
from aiecs.domain.agent.tools.schema_generator import ToolSchemaGenerator

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration, ToolObservation
from .exceptions import TaskExecutionError, ToolAccessDeniedError
from .tool_result_matcher import matches_stop_condition

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

    Uses OpenAI Function Calling for tool use (BetaToolRunner-style loop).
    ReAct text format is no longer supported; use Function Calling only.

    **Tool Configuration:**
    - Tool names (List[str]): Backward compatible, tools loaded by name
    - Tool instances (Dict[str, BaseTool]): Pre-configured tools with preserved state

    **LLM Client Configuration:**
    - BaseLLMClient: Standard LLM clients (OpenAI, xAI, Anthropic, Vertex)
    - Custom clients: Any object implementing LLMClientProtocol (duck typing)
    - **Required**: LLM must support Function Calling (tools parameter)

    **Deprecation Notice:**
    ReAct text format (TOOL:/OPERATION:/PARAMETERS:, FINAL RESPONSE: finish) is no longer
    supported. Use OpenAI-compatible Function Calling with supported providers.

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
        max_iterations: Optional[int] = None,
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
            max_iterations: Maximum ReAct iterations (if None, uses config.max_iterations)
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

        # Use config.max_iterations if constructor parameter is None
        # This makes max_iterations consistent with max_tokens (both configurable via config)
        # If max_iterations is explicitly provided, it takes precedence over config
        if max_iterations is None:
            # Use config value (defaults to 10 if not set in config)
            self._max_iterations = config.max_iterations
        else:
            # Constructor parameter explicitly provided, use it
            self._max_iterations = max_iterations

        self._system_prompt: Optional[str] = None
        self._conversation_history: List[LLMMessage] = []
        self._tool_schemas: List[Dict[str, Any]] = []
        self._use_function_calling: bool = False  # Set in _initialize() via _check_function_calling_support()

        logger.info(f"HybridAgent initialized: {agent_id} with LLM ({self.llm_client.provider_name}) " f"and {len(tools) if isinstance(tools, (list, dict)) else 0} tools")

    async def _initialize(self) -> None:
        """Initialize Hybrid agent - validate LLM client, load tools, and build system prompt."""
        # Validate LLM client using BaseAIAgent helper
        self._validate_llm_client()

        # Load tools using shared method from BaseAIAgent
        self._tool_instances = self._initialize_tools_from_config()
        logger.info(f"HybridAgent {self.agent_id} initialized with " f"{len(self._tool_instances)} tools")

        # Generate tool schemas for Function Calling
        self._generate_tool_schemas()

        # Require Function Calling when tools are present
        self._use_function_calling = self._check_function_calling_support()
        if self._tool_instances and not self._use_function_calling:
            provider = getattr(self.llm_client, "provider_name", "unknown")
            raise ValueError(
                "HybridAgent requires an LLM client with Function Calling support when tools are configured. "
                f"Current client ({provider}) does not support tools. "
                "Use OpenAI-compatible clients: OpenAI, xAI, Anthropic, or Google Vertex."
            )

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

    def _build_system_prompts(self) -> List[Dict[str, Any]]:
        """Build multiple system prompts including tool descriptions.

        Overrides base method to add tool info as separate system message.
        ReAct text format is no longer supported; use OpenAI Function Calling.

        Returns:
            List of system prompt dictionaries with content and cache_control
        """
        prompts = super()._build_system_prompts()

        has_custom_system_prompt = self._config.system_prompt is not None or self._config.system_prompts is not None

        parts = []
        if not has_custom_system_prompt:
            parts.append("You are a highly intelligent, responsive, and accurate reasoning agent that can use tools to complete tasks. " "Use the available tools when needed to accomplish the task.")
        if self._available_tools:
            parts.append(f"Available tools: {', '.join(self._available_tools)}")

        if parts:
            prompts.append(
                {
                    "content": "\n\n".join(parts),
                    "cache_control": False,
                }
            )

        return prompts

    def _build_system_prompt(self) -> str:
        """Build system prompt including tool descriptions.

        Legacy method for backward compatibility. Uses _build_system_prompts() and combines
        all prompts into a single string.

        Note: This method is kept for backward compatibility. New code should use
        _build_system_prompts() for better cache control.
        """
        prompts = self._build_system_prompts()
        parts = [p["content"] for p in prompts if p.get("content")]
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
            # Extract task description using shared method
            task_description = self._extract_task_description(task)

            # Merge images from task payload into context (deduplicates merge logic).
            self._merge_task_images(task, context)

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Execute tool loop with exponential backoff retry (handles 429 / transient errors)
            result = await self._execute_with_retry(self._tool_loop, task_description, context)

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
                "success": result.get("success", True),
                "reason": result.get("reason"),
                "output": result.get("final_response"),  # Changed from final_answer
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

    async def execute_task_streaming(self, task: Dict[str, Any], context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
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

            # Merge images from task payload into context (deduplicates merge logic).
            self._merge_task_images(task, context)

            # Transition to busy state
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            # Yield started lifecycle event
            yield {
                "type": "started",
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Execute streaming tool loop with exponential backoff retry.
            # _execute_with_retry cannot wrap async generators, so retry is inlined here.
            from .integration.retry_policy import EnhancedRetryPolicy, ErrorClassifier

            _retry_cfg = self._config.retry_policy
            _policy = EnhancedRetryPolicy(
                max_retries=_retry_cfg.max_retries,
                base_delay=_retry_cfg.base_delay,
                max_delay=_retry_cfg.max_delay,
                exponential_base=_retry_cfg.exponential_factor,
                jitter_factor=_retry_cfg.jitter_factor,
            )
            # Initialise event so the variable is always bound even if _tool_loop_streaming
            # raises before yielding a single event (e.g. all retries exhausted).
            event: Dict[str, Any] = {}
            for _attempt in range(_policy.max_retries + 1):
                try:
                    async for event in self._tool_loop_streaming(task_description, context):
                        yield event
                    break  # success – exit retry loop
                except Exception as _exc:
                    _error_type = ErrorClassifier.classify(_exc)
                    if _attempt >= _policy.max_retries or not ErrorClassifier.is_retryable(_error_type):
                        raise
                    _delay = _policy.calculate_delay(_attempt, _error_type)
                    logger.warning(f"Streaming attempt {_attempt + 1} failed " f"({_error_type.value}). Retrying in {_delay:.2f}s…")
                    await asyncio.sleep(_delay)

            # Get final result from last event
            if event.get("type") == "result":
                result = event
                task_success = result.get("success", True)

                # Calculate execution time
                execution_time = (datetime.utcnow() - start_time).total_seconds()

                # Update metrics (use actual success from result, e.g. False on max_iterations)
                self.update_metrics(
                    execution_time=execution_time,
                    success=task_success,
                    tokens_used=result.get("total_tokens"),
                    tool_calls=result.get("tool_calls_count", 0),
                )

                # Transition back to active
                self._transition_state(self.state.__class__.ACTIVE)
                self._current_task_id = None
                self.last_active_at = datetime.utcnow()

                # Yield completed lifecycle event (symmetric counterpart to "started")
                yield {
                    "type": "completed",
                    "success": task_success,
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat(),
                }

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

    async def process_message_streaming(self, message: str, sender_id: Optional[str] = None) -> AsyncGenerator[str, None]:
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

    async def _tool_loop_streaming(self, task: str, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute tool loop with streaming (BetaToolRunner-style).
        Append-only messages; native tool_use/tool_result; no iteration labels.

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
            logger.debug(f"HybridAgent {self.agent_id} - tool loop iteration {iteration + 1}")

            # Yield iteration_start lifecycle event (fires before each LLM call)
            yield {
                "type": "iteration_start",
                "iteration": iteration + 1,
                "max_iterations": self._max_iterations,
                "remaining": self._max_iterations - iteration - 1,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # THINK: Stream LLM reasoning
            thought_tokens = []
            tool_calls_from_stream = None

            # Require Function Calling when tools are configured
            if self._tool_schemas and not self._use_function_calling:
                provider = getattr(self.llm_client, "provider_name", "unknown")
                raise ValueError(
                    "HybridAgent requires an LLM client with Function Calling support when tools are configured. "
                    f"Current client ({provider}) does not support tools. "
                    "Use OpenAI-compatible clients: OpenAI, xAI, Anthropic, or Google Vertex."
                )
            kwargs: Dict[str, Any] = dict(
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                context=context,
            )
            if self._tool_schemas:
                kwargs["tools"] = [{"type": "function", "function": s} for s in self._tool_schemas]
                kwargs["tool_choice"] = "auto"
                kwargs["return_chunks"] = True
            stream_gen = self.llm_client.stream_text(**kwargs)

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
                        # Yield incremental tool call delta (streaming fragment)
                        yield {
                            "type": "tool_call_delta",
                            "tool_call": chunk.tool_call,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    elif chunk.type == "tool_calls" and chunk.tool_calls:
                        # Complete tool_calls batch received
                        tool_calls_from_stream = chunk.tool_calls
                        yield {
                            "type": "tool_calls_ready",
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

            # Store raw output in steps (no format processing)
            steps.append(
                {
                    "type": "thought",
                    "content": thought_raw.strip(),  # Return raw output without processing
                    "iteration": iteration + 1,
                }
            )

            # Process tool_calls if received from stream
            if tool_calls_from_stream:
                # Add assistant message with BOTH content and tool_calls (align with Claude)
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content=thought_raw.strip() or None,
                        tool_calls=tool_calls_from_stream,
                    )
                )

                # Process each tool call
                for i, tool_call in enumerate(tool_calls_from_stream):
                    tool_name = "unknown"  # initialise so error handler always has a value
                    # Use the call's own id; fall back to a per-index sentinel so that
                    # every tool_result message in a parallel batch has a unique id.
                    tool_call_id = tool_call.get("id") or f"call_{i}"
                    try:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]

                        # Resolve tool name and operation via shared helper.
                        # Raises ValueError with a clear message if the name
                        # cannot be matched even after the underscore-split fallback.
                        tool_name, operation = self._parse_function_name(func_name)

                        # Parse arguments JSON
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

                        # Wrap tool call and result in step
                        steps.append(
                            {
                                "type": "action",
                                "tool": tool_name,
                                "operation": operation,
                                "parameters": parameters,
                                "result": str(tool_result),  # Include result in step
                                "iteration": iteration + 1,
                            }
                        )

                        # Yield tool result event (streaming)
                        yield {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "result": tool_result,
                            "timestamp": datetime.utcnow().isoformat(),
                        }

                        # Check tool result stop conditions: end loop if matched
                        if self._config.tool_result_stop_conditions and matches_stop_condition(tool_result, self._config.tool_result_stop_conditions):
                            final_output = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result)
                            yield {
                                "type": "result",
                                "success": True,
                                "output": final_output,
                                "reasoning_steps": steps,
                                "tool_calls_count": tool_calls_count,
                                "iterations": iteration + 1,
                                "total_tokens": total_tokens,
                                "stop_reason": "tool_result_matched",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            return

                        # Add tool result to messages (for LLM consumption)
                        # Only add the tool result message, assistant message already added above
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result),
                                tool_call_id=tool_call_id,
                            )
                        )

                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        steps.append(
                            {
                                "type": "observation",
                                "content": error_msg,
                                "iteration": iteration + 1,
                                "has_error": True,
                            }
                        )
                        yield {
                            "type": "tool_error",
                            "tool_name": tool_name,
                            "error": str(e),
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=error_msg,
                                tool_call_id=tool_call_id,
                            )
                        )

                # Continue to next iteration
                continue

            # No tool_calls: treat as final response (Function Calling only; no ReAct parsing)
            yield {
                "type": "result",
                "success": True,
                "output": thought_raw.strip(),
                "reasoning_steps": steps,
                "tool_calls_count": tool_calls_count,
                "iterations": iteration + 1,
                "total_tokens": total_tokens,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return

        # Max iterations reached - task did not complete successfully within the limit
        logger.warning(f"HybridAgent {self.agent_id} reached max iterations")
        yield {
            "type": "result",
            "success": False,
            "reason": "max_iterations_reached",
            "output": "Max iterations reached. Unable to complete task fully.",
            "reasoning_steps": steps,
            "tool_calls_count": tool_calls_count,
            "iterations": self._max_iterations,
            "total_tokens": total_tokens,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _tool_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool loop (BetaToolRunner-style).
        Append-only messages; native tool_use/tool_result; no iteration labels.

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary with 'final_response', 'steps', 'iterations'
        """
        steps = []
        tool_calls_count = 0
        total_tokens = 0

        # Build initial messages
        messages = self._build_initial_messages(task, context)

        for iteration in range(self._max_iterations):
            logger.debug(f"HybridAgent {self.agent_id} - tool loop iteration {iteration + 1}")

            # THINK: LLM reasons about next action
            # Require Function Calling when tools are configured
            if self._tool_schemas and not self._use_function_calling:
                provider = getattr(self.llm_client, "provider_name", "unknown")
                raise ValueError(
                    "HybridAgent requires an LLM client with Function Calling support when tools are configured. "
                    f"Current client ({provider}) does not support tools. "
                    "Use OpenAI-compatible clients: OpenAI, xAI, Anthropic, or Google Vertex."
                )
            kwargs: Dict[str, Any] = dict(
                messages=messages,
                model=self._config.llm_model,
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
                context=context,
            )
            if self._tool_schemas:
                kwargs["tools"] = [{"type": "function", "function": s} for s in self._tool_schemas]
                kwargs["tool_choice"] = "auto"
            response = await self.llm_client.generate_text(**kwargs)

            thought_raw = response.content or ""
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

            # Store raw output in steps (no format processing)
            steps.append(
                {
                    "type": "thought",
                    "content": thought_raw.strip(),  # Return raw output without processing
                    "iteration": iteration + 1,
                }
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

                # Add assistant message with BOTH content and tool_calls (align with Claude)
                messages.append(
                    LLMMessage(
                        role="assistant",
                        content=(thought_raw or "").strip() or None,
                        # Fix: use tool_calls_to_process (processed list), not the raw
                        # tool_calls attribute which is None when only function_call is set.
                        tool_calls=tool_calls_to_process or None,
                    )
                )

                # Process each tool call
                for i, tool_call in enumerate(tool_calls_to_process):
                    tool_name = "unknown"  # initialise so error handler always has a value
                    # Use the call's own id; fall back to a per-index sentinel so that
                    # every tool_result message in a parallel batch has a unique id.
                    tool_call_id = tool_call.get("id") or f"call_{i}"
                    try:
                        func_name = tool_call["function"]["name"]
                        func_args = tool_call["function"]["arguments"]

                        # Resolve tool name and operation via shared helper.
                        # Raises ValueError with a clear message if the name
                        # cannot be matched even after the underscore-split fallback.
                        tool_name, operation = self._parse_function_name(func_name)

                        # Parse arguments JSON
                        if isinstance(func_args, str):
                            parameters = json.loads(func_args)
                        else:
                            parameters = func_args if func_args else {}

                        # Execute tool
                        tool_result = await self._execute_tool(tool_name, operation, parameters)
                        tool_calls_count += 1

                        # Wrap tool call and result in step
                        steps.append(
                            {
                                "type": "action",
                                "tool": tool_name,
                                "operation": operation,
                                "parameters": parameters,
                                "result": str(tool_result),  # Include result in step
                                "iteration": iteration + 1,
                            }
                        )

                        # Check tool result stop conditions: end loop if matched
                        if self._config.tool_result_stop_conditions and matches_stop_condition(tool_result, self._config.tool_result_stop_conditions):
                            final_output = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result)
                            return {
                                "final_response": final_output,
                                "steps": steps,
                                "iterations": iteration + 1,
                                "tool_calls_count": tool_calls_count,
                                "total_tokens": total_tokens,
                                "stop_reason": "tool_result_matched",
                            }

                        # Add tool result to messages (for LLM consumption)
                        # Only add the tool result message, assistant message already added above
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result),
                                tool_call_id=tool_call_id,
                            )
                        )

                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        steps.append(
                            {
                                "type": "observation",
                                "content": error_msg,
                                "iteration": iteration + 1,
                                "has_error": True,
                            }
                        )
                        # Add error to messages
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=error_msg,
                                tool_call_id=tool_call_id,
                            )
                        )

                # Continue to next iteration
                continue

            # No tool_calls: treat as final response (Function Calling only; no ReAct parsing)
            return {
                "final_response": thought_raw.strip(),
                "steps": steps,
                "iterations": iteration + 1,
                "tool_calls_count": tool_calls_count,
                "total_tokens": total_tokens,
            }

        # Max iterations reached - task did not complete successfully within the limit
        logger.warning(f"HybridAgent {self.agent_id} reached max iterations")
        return {
            "success": False,
            "reason": "max_iterations_reached",
            "final_response": "Max iterations reached. Unable to complete task fully.",
            "steps": steps,
            "iterations": self._max_iterations,
            "tool_calls_count": tool_calls_count,
            "total_tokens": total_tokens,
        }

    def _build_initial_messages(self, task: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """Build initial messages for tool loop. First user message = raw task only."""
        messages = []

        # Add system prompts (supports multiple system messages with individual cache control)
        system_prompts = self._build_system_prompts()
        for prompt_dict in system_prompts:
            content = prompt_dict.get("content", "")
            if not content:
                continue

            # Determine cache control: use prompt-specific setting if provided, else use global setting
            prompt_cache_control = prompt_dict.get("cache_control")
            if prompt_cache_control is None:
                # Use global setting
                cache_control = CacheControl(type="ephemeral") if self._config.enable_prompt_caching else None
            else:
                # Use prompt-specific setting
                cache_control = CacheControl(type="ephemeral") if prompt_cache_control else None

            messages.append(
                LLMMessage(
                    role="system",
                    content=content,
                    cache_control=cache_control,
                )
            )

        # Collect images from context to attach to task message
        task_images = []

        # Add context if provided
        if context:
            # Special handling: if context contains 'history' as a list of messages,
            # add them as separate user/assistant messages instead of formatting
            history = context.get("history")
            if isinstance(history, list) and len(history) > 0:
                # Check if history contains message-like dictionaries
                for msg in history:
                    if isinstance(msg, dict) and "role" in msg and ("content" in msg or "tool_calls" in msg):
                        # Valid message format - add as separate message
                        # Extract optional fields
                        _raw_images = msg.get("images")
                        # Normalise: keep only non-None/non-empty image values so we
                        # never end up passing [None] to LLMMessage when the key is
                        # explicitly set to None in the history entry.
                        if isinstance(_raw_images, list):
                            msg_images: List[Any] = [img for img in _raw_images if img is not None]
                        elif _raw_images is not None:
                            msg_images = [_raw_images]
                        else:
                            msg_images = []
                        msg_tool_calls = msg.get("tool_calls")
                        msg_tool_call_id = msg.get("tool_call_id")
                        messages.append(
                            LLMMessage(
                                role=msg["role"],
                                content=msg.get("content"),
                                images=msg_images,
                                tool_calls=msg_tool_calls,
                                tool_call_id=msg_tool_call_id,
                            )
                        )
                    elif isinstance(msg, LLMMessage):
                        # Already an LLMMessage instance (may already have images)
                        messages.append(msg)

            # Extract images from context if present
            context_images = context.get("images")
            if context_images:
                if isinstance(context_images, list):
                    task_images.extend(context_images)
                else:
                    task_images.append(context_images)

            # Format remaining context fields (excluding history and images) as Additional Context
            context_without_history = {k: v for k, v in context.items() if k not in ("history", "images")}
            if context_without_history:
                context_str = self._format_context(context_without_history)
                if context_str:
                    messages.append(
                        LLMMessage(
                            role="user",
                            content=f"Additional Context:\n{context_str}",
                        )
                    )

        # Add request-specific skill context if skills are enabled
        # This provides skills matched to the specific task for tool selection guidance
        if self._config.skills_enabled and self._attached_skills:
            skill_context = self.get_skill_context(
                request=task,
                include_all_skills=False,  # Only include matched skills
            )
            if skill_context:
                messages.append(
                    LLMMessage(
                        role="system",
                        content=f"Relevant Skills for this Task:\n{skill_context}",
                    )
                )

        # Add task (first user message = raw request only; no iteration labels)
        task_message = f"Task: {task}"
        messages.append(
            LLMMessage(
                role="user",
                content=task_message,
                images=task_images if task_images else [],
            )
        )

        return messages

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as string."""
        relevant_fields = []
        for key, value in context.items():
            if not key.startswith("_") and value is not None:
                relevant_fields.append(f"{key}: {value}")
        return "\n".join(relevant_fields) if relevant_fields else ""

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
            self._tool_schemas = ToolSchemaGenerator.generate_schemas_for_tool_instances(self._tool_instances)
            logger.info(f"HybridAgent {self.agent_id} generated {len(self._tool_schemas)} tool schemas")
        except Exception as e:
            tool_names = list(self._tool_instances.keys())
            raise RuntimeError(f"Failed to generate tool schemas for tools {tool_names}: {e}. " "Check that all tools have valid type annotations and docstrings.") from e

    def _check_function_calling_support(self) -> bool:
        """
        Check if the LLM client itself supports Function Calling.

        This method is solely responsible for detecting LLM capability — it does
        NOT check whether tools are configured. Tool availability is a separate
        concern handled by callers via ``self._tool_instances`` / ``self._tool_schemas``
        guards, keeping the two concerns cleanly separated.

        Returns:
            True if the LLM client supports Function Calling, False otherwise.
        """
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

    def _parse_function_name(self, func_name: str) -> tuple:
        """Parse a function name returned by the LLM into (tool_name, operation).

        Tries an exact match against registered tool names first.  Only if that
        fails does it fall back to splitting on the first underscore (legacy
        ``tool_operation`` naming convention).  When the fallback candidate is
        also not a known tool the method raises a :class:`ValueError` with an
        actionable message so that callers see the real cause of the failure
        rather than a cryptic "Tool X not loaded" error from ``_execute_tool``.
        """
        # Exact match has highest priority – handles tool names that contain
        # underscores (e.g. "web_search" registered as a single tool).
        if self._tool_instances and func_name in self._tool_instances:
            return func_name, None
        if self._available_tools and func_name in self._available_tools:
            return func_name, None

        # Fallback: split on the first underscore for legacy "tool_operation"
        # naming (e.g. schema name "pandas_filter" → tool="pandas", op="filter").
        parts = func_name.split("_", 1)
        candidate_tool = parts[0]
        candidate_op = parts[1] if len(parts) == 2 else None

        known_tools: set = set(self._tool_instances or {}) | set(self._available_tools or [])
        if known_tools and candidate_tool not in known_tools:
            raise ValueError(
                f"Cannot resolve function name '{func_name}' to a registered tool. "
                f"Exact match failed, and the underscore-split fallback produced "
                f"tool='{candidate_tool}' (operation='{candidate_op}') which is "
                f"also not registered. Available tools: {sorted(known_tools)}. "
                "Ensure the LLM is using a tool name that appears in the schema."
            )

        return candidate_tool, candidate_op

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

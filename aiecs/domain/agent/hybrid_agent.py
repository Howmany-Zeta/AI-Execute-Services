# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
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
import uuid
from typing import Dict, List, Any, Optional, Union, TYPE_CHECKING, AsyncGenerator, Callable, Awaitable
from datetime import datetime

from aiecs.llm import BaseLLMClient, CacheControl, LLMMessage
from aiecs.tools import BaseTool
from aiecs.domain.agent.tools.schema_generator import ToolSchemaGenerator

from .base_agent import BaseAIAgent
from .models import AgentType, AgentConfiguration, ToolObservation, resolve_compression_policy
from .exceptions import TaskExecutionError, ToolAccessDeniedError
from .tool_loop_core import (
    ToolLoopCompressionContext,
    ToolLoopIterationOutcome,
    ToolLoopRunState,
    apply_tool_output_management,
    maybe_compact_before_llm,
    maybe_reactive_compact_on_ptl,
)
from .tool_result_matcher import matches_stop_condition
from aiecs.domain.agent.plugins.context import AgentPluginContext, PluginShortCircuitResult
from aiecs.domain.agent.plugins.hooks.task_boundary import (
    apply_hook_additional_context,
    dispatch_build_messages_hook,
    dispatch_iteration_start_hook,
    dispatch_max_iterations_hook,
    dispatch_prompt_too_long_hook,
    dispatch_llm_error_hook,
    dispatch_stop_hook_for_outcome,
    dispatch_user_prompt_in_history_hook,
    last_assistant_message_preview,
    prepare_and_dispatch_task_entry_hooks,
    run_post_task_phase_with_hooks,
    task_rejection_from_hook_result,
)
from aiecs.domain.agent.plugins.hooks.types import AggregatedHookResult
from aiecs.domain.agent.plugins.builtin.knowledge_plugin import (
    effective_task_description,
    inject_iteration_knowledge_into_messages,
)
from aiecs.domain.agent.plugins.models import PluginPhase

if TYPE_CHECKING:
    from aiecs.llm.protocols import LLMClientProtocol
    from aiecs.domain.agent.integration.protocols import (
        ConfigManagerProtocol,
        CheckpointerProtocol,
    )
    from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
    from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget

logger = logging.getLogger(__name__)


class HybridAgent(BaseAIAgent):
    """
    Hybrid agent combining LLM reasoning with tool execution.

    Uses OpenAI Function Calling for tool use (BetaToolRunner-style loop).
    ReAct text format is no longer supported; use Function Calling only.

    **Plugin-first skill and memory (Phase 2)**:
    Do not call :meth:`~aiecs.domain.agent.skills.mixin.SkillCapableMixin.attach_skills`
    or :meth:`~aiecs.domain.agent.skills.mixin.SkillCapableMixin.get_skill_context` from
    HybridAgent code paths. ``SkillPlugin`` (``AGENT_INIT`` / ``BUILD_MESSAGES``) and
    ``MemoryPlugin`` (``BUILD_MESSAGES`` / ``context.history``) own those behaviors.
    Use :meth:`_build_initial_messages_async` for message assembly; the sync
    :meth:`_build_initial_messages` helper omits plugin phases (legacy/tests only).

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
        plugin_registry: Optional[Any] = None,
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
            plugin_registry=plugin_registry,
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
        self._tool_budget_store: Optional[Any] = None
        self._tool_artifact_port: Optional[Any] = None
        self._session_memory_port: Optional[Any] = None
        self._compression_hook_executor: Optional[Any] = None
        self._compression_progress_emitter: Optional[Any] = None
        self._auto_compact_state: Optional[Any] = None

        logger.info(f"HybridAgent initialized: {agent_id} with LLM ({self.llm_client.provider_name}) " f"and {len(tools) if isinstance(tools, (list, dict)) else 0} tools")

    async def _initialize(self, *, force_reload_plugins: bool = False) -> None:
        """
        Initialize Hybrid agent — validate LLM client, load tools, build system prompt.

        Builtin plugins run via ``super()._initialize()`` (``PluginManager``).
        Skill attachment is **only** performed by ``SkillPlugin.on_agent_init`` when the
        skill plugin is enabled — do not call ``attach_skills`` here.
        """
        await super()._initialize(force_reload_plugins=force_reload_plugins)

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

        await super()._shutdown()
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

    def _format_execute_task_response(
        self,
        inner: Dict[str, Any],
        execution_time: float,
    ) -> Dict[str, Any]:
        """
        Map tool-loop kernel dict to execute_task outer shell (§8.2, §4.4).

        Passthrough when ``inner`` already contains ``output`` (e.g. Knowledge short-circuit).
        """
        if inner.get("output") is not None:
            outer = dict(inner)
            outer.setdefault("execution_time", execution_time)
            outer.setdefault("timestamp", datetime.utcnow().isoformat())
            return outer

        return {
            "success": inner.get("success", True),
            "reason": inner.get("reason"),
            "output": inner.get("final_response"),
            "reasoning_steps": inner.get("steps"),
            "tool_calls_count": inner.get("tool_calls_count"),
            "iterations": inner.get("iterations"),
            "execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _execute_task_with_plugins(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Task kernel: plugin phases + tool loop (§8.2).

        PRE_TASK and PRE_MAIN_LOOP run before the loop; POST_TASK always runs (including
        after PRE_MAIN_LOOP short-circuit).
        """
        task_description = self._extract_task_description(task)
        self._merge_task_images(task, context)

        plugin_ctx = self._make_plugin_context(
            task=task,
            context=context,
            task_description=task_description,
        )
        self._apply_task_plugin_configs(task=task, context=context)

        h5_result = await prepare_and_dispatch_task_entry_hooks(plugin_ctx, task_description=task_description)
        h5_rejection = task_rejection_from_hook_result(h5_result, source="user_prompt_submit")
        if h5_rejection is not None:
            if self._plugin_manager is not None:
                return await run_post_task_phase_with_hooks(self._plugin_manager, plugin_ctx, h5_rejection)
            return h5_rejection

        initial_messages: Optional[List[LLMMessage]] = None
        short = None

        if self._plugin_manager is not None:
            await self._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
            initial_messages = await self._build_initial_messages_async(task_description, context, plugin_ctx)
            h5b_result = await dispatch_user_prompt_in_history_hook(plugin_ctx, initial_messages)
            apply_hook_additional_context(plugin_ctx, initial_messages, h5b_result)
            h5b_rejection = task_rejection_from_hook_result(h5b_result, source="user_prompt_in_history")
            if h5b_rejection is not None:
                return await run_post_task_phase_with_hooks(self._plugin_manager, plugin_ctx, h5b_rejection)
            short = await self._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)
        else:
            initial_messages = await self._build_initial_messages_async(task_description, context, plugin_ctx)

        task_for_loop = effective_task_description(plugin_ctx, task_description)

        if isinstance(short, PluginShortCircuitResult):
            loop_result = dict(short.result)
        else:
            loop_result = await self._execute_with_retry(
                self._tool_loop_with_plugins,
                task_for_loop,
                context,
                plugin_ctx,
                initial_messages=initial_messages,
            )

        if self._plugin_manager is not None:
            loop_result = await run_post_task_phase_with_hooks(
                self._plugin_manager,
                plugin_ctx,
                loop_result,
            )
        return loop_result

    def _assemble_loop_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return tool-loop kernel dict with legacy ``_tool_loop`` keys (§8.4).

        Ensures ``final_response``, ``steps``, ``iterations``, ``tool_calls_count``, and
        ``total_tokens`` are present for ``execute_task`` / POST_TASK consumers.
        """
        return dict(result)

    def _iteration_step_payload(
        self,
        outcome: ToolLoopIterationOutcome,
        iteration: int,
        state: ToolLoopRunState,
    ) -> Dict[str, Any]:
        """Summary passed to ``ON_ITERATION_END`` hooks."""
        return {
            "kind": outcome.kind,
            "iteration": iteration + 1,
            "steps": list(state.steps),
            "tool_calls_count": state.tool_calls_count,
            "total_tokens": state.total_tokens,
        }

    async def _run_tool_loop_with_iteration_hooks(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        plugin_ctx: Optional[AgentPluginContext] = None,
    ) -> Dict[str, Any]:
        """
        LLM+tool iteration loop with optional ``ON_ITERATION_*`` plugin phases (§8.4).

        The loop is driven by a shared ``TaskIterationBudget`` (D5, §4.4) stored at
        ``plugin_state["task.iteration_budget"]``.  Each completed LLM+tool round
        consumes 1 unit; the loop exits when the budget is exhausted or a final
        response is produced.
        """
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget

        _BUDGET_KEY = "task.iteration_budget"
        if plugin_ctx is not None:
            budget: TaskIterationBudget = plugin_ctx.plugin_state.get(_BUDGET_KEY)  # type: ignore[assignment]
            if not isinstance(budget, TaskIterationBudget):
                budget = TaskIterationBudget(limit=self._max_iterations)
                plugin_ctx.plugin_state[_BUDGET_KEY] = budget
        else:
            budget = TaskIterationBudget(limit=self._max_iterations)

        state = ToolLoopRunState()
        iteration = 0
        while budget.remaining > 0:
            logger.debug(f"HybridAgent {self.agent_id} - tool loop iteration {iteration + 1}")
            if plugin_ctx is not None:
                plugin_ctx.plugin_state["task.current_iteration"] = iteration

            if plugin_ctx is not None and self._plugin_manager is not None:
                await self._plugin_manager.run_phase(
                    PluginPhase.ON_ITERATION_START,
                    ctx=plugin_ctx,
                    iteration=iteration,
                )
                messages = inject_iteration_knowledge_into_messages(messages, plugin_ctx)
                await dispatch_iteration_start_hook(plugin_ctx, iteration)

            outcome = await self._run_tool_loop_core_iteration(messages, context, iteration, state, plugin_ctx=plugin_ctx)

            budget.consume(1)

            if plugin_ctx is not None:
                plugin_ctx.plugin_state["task.response_index"] = plugin_ctx.plugin_state.get("task.response_index", 0) + 1

            _dawp_drained_any = False
            # D2-08 / H2-01a: inline drain — parity with streaming path (§6.5, §7.1.3.1).
            if plugin_ctx is not None:
                from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

                try:
                    async for _ in self._drain_pending_dawp_runs("inline", messages, context, plugin_ctx, budget):
                        _dawp_drained_any = True
                except DawpAbortMainError as _exc:
                    logger.warning("HybridAgent (non-streaming): abort_main (inline): %s", _exc)
                    return self._assemble_loop_result(
                        {
                            "success": False,
                            "output": str(_exc),
                            "reason": "dawp_abort_main",
                            "final_response": str(_exc),
                            "steps": list(state.steps),
                            "iterations": iteration + 1,
                            "tool_calls_count": state.tool_calls_count,
                            "total_tokens": state.total_tokens,
                        }
                    )

            if plugin_ctx is not None and self._plugin_manager is not None:
                step = self._iteration_step_payload(outcome, iteration, state)
                step["response_index"] = plugin_ctx.plugin_state["task.response_index"]
                await self._plugin_manager.run_phase(
                    PluginPhase.ON_ITERATION_END,
                    ctx=plugin_ctx,
                    iteration=iteration,
                    step=step,
                )

            # D2-08 / H2-01a: config-path drain (on_response_trigger) — parity with streaming path.
            if plugin_ctx is not None:
                from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError as _AbortErr

                try:
                    async for _ in self._drain_pending_dawp_runs("on_iteration_end", messages, context, plugin_ctx, budget):
                        _dawp_drained_any = True
                except _AbortErr as _exc:
                    logger.warning("HybridAgent (non-streaming): abort_main (on_iteration_end): %s", _exc)
                    return self._assemble_loop_result(
                        {
                            "success": False,
                            "output": str(_exc),
                            "reason": "dawp_abort_main",
                            "final_response": str(_exc),
                            "steps": list(state.steps),
                            "iterations": iteration + 1,
                            "tool_calls_count": state.tool_calls_count,
                            "total_tokens": state.total_tokens,
                        }
                    )

            if outcome.kind == "continue":
                iteration += 1
                continue

            if _dawp_drained_any:
                iteration += 1
                continue

            if outcome.kind in ("final", "stop_match") and outcome.result is not None:
                if plugin_ctx is not None:
                    prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration, messages=messages)
                    if prevent:
                        iteration += 1
                        continue
                return self._assemble_loop_result(outcome.result)

            iteration += 1

        if plugin_ctx is not None:
            await dispatch_max_iterations_hook(
                plugin_ctx,
                state,
                iteration=iteration,
                max_iterations=self._max_iterations,
            )
        return self._assemble_loop_result(self._tool_loop_max_iterations_result(state))

    async def _tool_loop_with_plugins(
        self,
        task_description: str,
        context: Dict[str, Any],
        plugin_ctx: AgentPluginContext,
        *,
        initial_messages: Optional[List[LLMMessage]] = None,
    ) -> Dict[str, Any]:
        """
        Tool loop with plugin-aware messages and ``ON_ITERATION_*`` hooks (§8.4).
        """
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
        from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

        if initial_messages is not None:
            messages = list(initial_messages)
        else:
            messages = await self._build_initial_messages_async(task_description, context, plugin_ctx)

        # D2-08: drain pre_main_loop activations before starting the main loop — parity with
        # the streaming path (§9, D1-09).  Events are consumed and discarded; only side
        # effects (message mutation, budget consumption, abort_main) are preserved.
        _BUDGET_KEY = "task.iteration_budget"
        budget: TaskIterationBudget = plugin_ctx.plugin_state.get(_BUDGET_KEY)  # type: ignore[assignment]
        if not isinstance(budget, TaskIterationBudget):
            budget = TaskIterationBudget(limit=self._max_iterations)
            plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        try:
            async for _ in self._drain_pending_dawp_runs("on_iteration_end", messages, context, plugin_ctx, budget):
                pass  # events discarded in non-streaming path; side effects retained
        except DawpAbortMainError as _exc:
            logger.warning("HybridAgent (non-streaming): abort_main (pre_main_loop): %s", _exc)
            return self._assemble_loop_result(
                {"success": False, "output": str(_exc), "reason": "dawp_abort_main", "final_response": str(_exc), "steps": [], "iterations": 0, "tool_calls_count": 0, "total_tokens": 0}
            )

        return await self._run_tool_loop_with_iteration_hooks(messages, context, plugin_ctx=plugin_ctx)

    async def execute_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task using the plugin-wrapped tool loop (§8.2).

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
            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            inner = await self._execute_task_with_plugins(task, context)

            execution_time = (datetime.utcnow() - start_time).total_seconds()

            self.update_metrics(
                execution_time=execution_time,
                success=inner.get("success", True),
                tokens_used=inner.get("total_tokens"),
                tool_calls=inner.get("tool_calls_count", 0),
            )

            self._transition_state(self.state.__class__.ACTIVE)
            self._current_task_id = None
            self.last_active_at = datetime.utcnow()

            return self._format_execute_task_response(inner, execution_time)

        except Exception as e:
            logger.error(f"Task execution failed for {self.agent_id}: {e}")

            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.update_metrics(execution_time=execution_time, success=False)

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

    def _create_plugin_event_collector(
        self,
    ) -> tuple[List[Dict[str, Any]], Callable[[Dict[str, Any]], Awaitable[None]]]:
        """Buffer plugin framework events for streaming yields (§10.3)."""
        pending: List[Dict[str, Any]] = []

        async def sink(event: Dict[str, Any]) -> None:
            pending.append(event)

        return pending, sink

    async def _yield_pending_plugin_events(
        self,
        pending: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        while pending:
            yield pending.pop(0)

    def _loop_result_from_streaming_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a streaming ``result`` event to tool-loop kernel dict for POST_TASK."""
        return {
            "success": event.get("success", True),
            "reason": event.get("reason"),
            "final_response": event.get("output"),
            "steps": event.get("reasoning_steps", []),
            "tool_calls_count": event.get("tool_calls_count", 0),
            "iterations": event.get("iterations", 0),
            "total_tokens": event.get("total_tokens", 0),
            **({"stop_reason": event["stop_reason"]} if event.get("stop_reason") else {}),
        }

    def _streaming_result_event_from_inner(
        self,
        inner: Dict[str, Any],
        *,
        execution_time: float = 0.0,
    ) -> Dict[str, Any]:
        """Build streaming ``result`` event from kernel dict (§8.2, §8.5)."""
        shell = self._format_execute_task_response(inner, execution_time)
        return {
            "type": "result",
            **shell,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _tool_loop_streaming_with_plugins(
        self,
        task_description: str,
        context: Dict[str, Any],
        plugin_ctx: AgentPluginContext,
        *,
        initial_messages: Optional[List[LLMMessage]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming tool loop with async messages and ``ON_ITERATION_*`` hooks (§8.4, §8.5).

        The loop is driven by a shared ``TaskIterationBudget`` (D5, §4.4).  Each
        completed LLM+tool round consumes 1 unit; ``iteration_start.remaining``
        reflects the pre-consume budget so downstream consumers can track the shared
        pool across main and DAWP iterations.
        """
        from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget

        _BUDGET_KEY = "task.iteration_budget"
        budget: TaskIterationBudget = plugin_ctx.plugin_state.get(_BUDGET_KEY)  # type: ignore[assignment]
        if not isinstance(budget, TaskIterationBudget):
            budget = TaskIterationBudget(limit=self._max_iterations)
            plugin_ctx.plugin_state[_BUDGET_KEY] = budget

        messages = list(initial_messages) if initial_messages is not None else await self._build_initial_messages_async(task_description, context, plugin_ctx)
        state = ToolLoopRunState()
        iteration = 0

        # Drain pre_main_loop activations enqueued by DAWPPlugin.on_pre_main_loop (§9, D1-09).
        # These runs use drain_mode="on_iteration_end" (config path) and must execute
        # before the first main-loop iteration so their output appears first (baseworkflow L38).
        from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

        try:
            async for dawp_event in self._drain_pending_dawp_runs("on_iteration_end", messages, context, plugin_ctx, budget):
                yield dawp_event
        except DawpAbortMainError as _exc:
            logger.warning("HybridAgent: abort_main triggered (pre_main_loop drain): %s", _exc)
            yield self._streaming_result_event_from_inner({"success": False, "output": str(_exc), "reason": "dawp_abort_main"})
            return

        while budget.remaining > 0:
            logger.debug(f"HybridAgent {self.agent_id} - tool loop iteration {iteration + 1}")
            plugin_ctx.plugin_state["task.current_iteration"] = iteration

            if plugin_ctx is not None and self._plugin_manager is not None:
                await self._plugin_manager.run_phase(
                    PluginPhase.ON_ITERATION_START,
                    ctx=plugin_ctx,
                    iteration=iteration,
                )
                messages = inject_iteration_knowledge_into_messages(messages, plugin_ctx)
                await dispatch_iteration_start_hook(plugin_ctx, iteration)

            yield {
                "type": "iteration_start",
                "iteration": iteration + 1,
                "max_iterations": budget.limit,
                "remaining": budget.remaining,
                "timestamp": datetime.utcnow().isoformat(),
            }

            state.last_outcome = None
            async for event in self._run_tool_loop_core_iteration_streaming(messages, context, iteration, state, plugin_ctx=plugin_ctx):
                yield event

            budget.consume(1)

            plugin_ctx.plugin_state["task.response_index"] = plugin_ctx.plugin_state.get("task.response_index", 0) + 1

            # D2-05: Drain tool-path (dawp_start) inline pending runs immediately after
            # the iteration's tool processing completes but BEFORE ON_ITERATION_END.
            # This places DAWP events in the same main-loop iteration as the dawp_start call,
            # matching the baseworkflow timeline (§6.5): tool_result(ack) → inline drain → continue.
            _dawp_drained_any = False
            from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

            try:
                async for dawp_event in self._drain_pending_dawp_runs("inline", messages, context, plugin_ctx, budget):
                    _dawp_drained_any = True
                    yield dawp_event
            except DawpAbortMainError as _exc:
                logger.warning("HybridAgent: abort_main triggered (inline drain): %s", _exc)
                yield self._streaming_result_event_from_inner({"success": False, "output": str(_exc), "reason": "dawp_abort_main"})
                return

            if self._plugin_manager is not None:
                step = self._iteration_step_payload(
                    state.last_outcome or ToolLoopIterationOutcome(kind="continue"),
                    iteration,
                    state,
                )
                step["response_index"] = plugin_ctx.plugin_state["task.response_index"]
                await self._plugin_manager.run_phase(
                    PluginPhase.ON_ITERATION_END,
                    ctx=plugin_ctx,
                    iteration=iteration,
                    step=step,
                )

            # Drain on_response_trigger activations enqueued during ON_ITERATION_END (§6.5, D1-09).
            # FIFO until pending empty or budget exhausted; events yielded inline (R2, R3).
            # Track whether any DAWP events were produced so we can force the main loop
            # to continue after the drain even when this iteration's outcome was "final"
            # (the triggering response is part of context but not the task's final answer).
            try:
                async for dawp_event in self._drain_pending_dawp_runs("on_iteration_end", messages, context, plugin_ctx, budget):
                    _dawp_drained_any = True
                    yield dawp_event
            except DawpAbortMainError as _exc:
                logger.warning("HybridAgent: abort_main triggered (on_iteration_end drain): %s", _exc)
                yield self._streaming_result_event_from_inner({"success": False, "output": str(_exc), "reason": "dawp_abort_main"})
                return

            outcome = state.last_outcome
            if outcome is None or outcome.kind == "continue":
                iteration += 1
                continue

            # R2: if DAWP drained this iteration, the triggering response is context
            # — not the final answer.  Force the main loop to continue so the LLM
            # can produce the actual final response in the next iteration (§6.5).
            if _dawp_drained_any:
                iteration += 1
                continue

            if outcome.kind == "stop_match":
                if plugin_ctx is not None:
                    prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration, messages=messages)
                    if prevent:
                        iteration += 1
                        continue
                return

            if outcome.kind == "final" and outcome.result is not None:
                if plugin_ctx is not None:
                    prevent = await dispatch_stop_hook_for_outcome(plugin_ctx, outcome, iteration, messages=messages)
                    if prevent:
                        iteration += 1
                        continue
                yield self._streaming_result_event_from_inner(outcome.result)
                return

            iteration += 1

        if plugin_ctx is not None:
            await dispatch_max_iterations_hook(
                plugin_ctx,
                state,
                iteration=iteration,
                max_iterations=self._max_iterations,
            )
        yield self._streaming_result_event_from_inner(self._tool_loop_max_iterations_result(state))

    async def _drain_pending_dawp_runs(
        self,
        drain_mode: str,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        plugin_ctx: AgentPluginContext,
        budget: "TaskIterationBudget",
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """FIFO-drain pending DAWP runs matching *drain_mode* (§6.5, D1-09).

        Reads ``plugin_state["dawp.pending"]``, removes entries with the given
        *drain_mode* one at a time, and calls
        :func:`~dawp.prompt_chain_runner.run_prompt_chain` for each.  All events
        are yielded inline to the caller (``_tool_loop_streaming_with_plugins``).

        Draining continues while the queue is non-empty **and** ``budget.remaining > 0``.

        *messages* is passed directly to ``run_prompt_chain``, so assistant messages
        and tool results produced by DAWP steps are appended in-place (default
        ``merge_back: append`` — D2).

        Args:
            drain_mode: ``"on_iteration_end"`` (config path) or ``"inline"`` (tool path,
                        future D2-05).  Only runs whose :attr:`~schema.DawpPendingRun.drain_mode`
                        matches are dequeued; others are left for the appropriate drain point.
            messages:   Conversation history; mutated in-place by the prompt chain runner.
            context:    Execution context forwarded to the LLM.
            plugin_ctx: Current plugin context providing ``plugin_state``.
            budget:     Shared :class:`~dawp.budget.TaskIterationBudget`; passed through
                        to the prompt chain runner.

        Yields:
            All streaming events from :func:`~dawp.prompt_chain_runner.run_prompt_chain`,
            preserving ``loop_scope.kind="dawp"`` tags set by the nested runner.
        """
        from aiecs.domain.agent.plugins.dawp.inject import apply_inject_only, messages_for_dawp_run
        from aiecs.domain.agent.plugins.dawp.loop_scope import (
            LoopScope,
            build_dawp_run_completed,
            build_dawp_run_started,
        )
        from aiecs.domain.agent.plugins.dawp.prompt_chain_runner import run_prompt_chain

        pending: List[Any] = plugin_ctx.plugin_state.get("dawp.pending", [])

        skipped_unresolvable: set[int] = set()

        while pending and budget.remaining > 0:
            # Find the first run matching the drain mode (FIFO), skipping unresolvable this pass
            run = next(
                (r for r in pending if r.drain_mode == drain_mode and id(r) not in skipped_unresolvable),
                None,
            )
            if run is None:
                break

            from aiecs.domain.agent.plugins.dawp.workflow_registry import resolve_workflow_for_run

            workflow = resolve_workflow_for_run(plugin_ctx.plugin_state, run)
            if workflow is None:
                logger.warning(
                    "HybridAgent: no compiled workflow found for pending run" " workflow_id=%r; skipping this pass (D4/D8)",
                    run.workflow_id,
                )
                skipped_unresolvable.add(id(run))
                continue

            skipped_unresolvable.clear()
            pending.remove(run)

            run_id = f"dawp-{uuid.uuid4().hex[:8]}"
            scope = LoopScope(
                kind="dawp",
                run_id=run_id,
                workflow_id=run.workflow_id,
            )
            plugin_ctx.plugin_state["dawp._metrics_run"] = {
                "workflow_id": run.workflow_id,
                "trigger": run.trigger,
                "workflow_source": run.workflow_source,
            }
            logger.debug(
                "HybridAgent[drain=%s]: starting DAWP run %s for workflow=%r (merge_back=%r)",
                drain_mode,
                scope.run_id,
                run.workflow_id,
                run.merge_back,
            )

            # §8.1.1: optional boundary events — emitted only when stream_boundary_events=True.
            emit_boundary = bool(plugin_ctx.plugin_state.get("dawp.stream_boundary_events", False))
            if drain_mode == "inline":
                placement = "inline"
            elif run.config_placement is not None:
                placement = run.config_placement
            else:
                placement = "on_response_trigger"
            if emit_boundary:
                yield build_dawp_run_started(scope, placement=placement, trigger=run.trigger)

            from aiecs.domain.agent.plugins.hooks.dispatch import dispatch_agent_hook
            from aiecs.domain.agent.plugins.hooks.events import AgentHookEvent
            from aiecs.domain.agent.plugins.hooks.payload import (
                build_dawp_run_end_payload,
                build_dawp_run_start_payload,
                build_subagent_start_payload,
            )

            await dispatch_agent_hook(
                plugin_ctx,
                AgentHookEvent.SUBAGENT_START,
                build_subagent_start_payload(
                    agent_id=self.agent_id,
                    workflow_id=run.workflow_id,
                    run_id=run_id,
                    placement=placement,
                    trigger=run.trigger,
                ),
            )

            await dispatch_agent_hook(
                plugin_ctx,
                AgentHookEvent.DAWP_RUN_START,
                build_dawp_run_start_payload(
                    agent_id=self.agent_id,
                    workflow_id=run.workflow_id,
                    run_id=run_id,
                    placement=placement,
                    trigger=run.trigger,
                ),
            )

            # §6.3, D1-12: select message list based on merge_back strategy.
            # "append" → shared reference (DAWP appends in-place, main loop sees all).
            # "inject_only" → copy (DAWP messages stay isolated; summary added after).
            dawp_messages = messages_for_dawp_run(messages, merge_back=run.merge_back)

            # D3: reset success sentinel before each run; run_prompt_chain sets True on dawp_done.
            plugin_ctx.plugin_state["dawp._run_success"] = False

            run_success = False
            try:
                async for event in run_prompt_chain(
                    workflow,
                    dawp_messages,
                    context,
                    plugin_ctx,
                    self,
                    scope=scope,
                    budget=budget,
                ):
                    yield event
                run_success = plugin_ctx.plugin_state.get("dawp._run_success", False)
            finally:
                transcript_path = context.get("agent_transcript_path")
                await dispatch_agent_hook(
                    plugin_ctx,
                    AgentHookEvent.DAWP_RUN_END,
                    build_dawp_run_end_payload(
                        agent_id=self.agent_id,
                        workflow_id=run.workflow_id,
                        run_id=run_id,
                        status="success" if run_success else "failed",
                        abort_main=bool(run.abort_main),
                        last_assistant_message=last_assistant_message_preview(dawp_messages),
                        agent_transcript_path=str(transcript_path) if isinstance(transcript_path, str) else None,
                    ),
                )
                if emit_boundary:
                    yield build_dawp_run_completed(scope, success=run_success)
                from aiecs.domain.agent.plugins.dawp.metrics import get_dawp_metrics

                get_dawp_metrics().record_run(
                    workflow_id=run.workflow_id,
                    trigger=run.trigger,
                    workflow_source=run.workflow_source,
                    success=run_success,
                )
                plugin_ctx.plugin_state["dawp._run_count"] = int(plugin_ctx.plugin_state.get("dawp._run_count", 0)) + 1
                plugin_ctx.plugin_state.pop("dawp._metrics_run", None)

            # Merge handoff / inject_only summary before abort_main so audit trail
            # is preserved in main messages (append: handoff already on shared list).
            handoff = plugin_ctx.plugin_state.pop("dawp._handoff_message", None)
            if run.merge_back == "inject_only":
                if handoff:
                    from aiecs.llm import LLMMessage

                    messages.append(LLMMessage(role="user", content=handoff))
                elif run_success:
                    apply_inject_only(messages, workflow_id=run.workflow_id)

            # D3: if abort_main=True and the run did not complete successfully, raise to
            # signal the main loop to fail the entire task (§7, D3).
            if run.abort_main and not run_success:
                from aiecs.domain.agent.plugins.dawp.schema import DawpAbortMainError

                logger.warning(
                    "HybridAgent[drain=%s]: DAWP run %s for workflow=%r failed " "and abort_main=True; raising DawpAbortMainError (D3)",
                    drain_mode,
                    scope.run_id,
                    run.workflow_id,
                )
                raise DawpAbortMainError(run.workflow_id)

    async def _run_tool_loop_nested_streaming(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        plugin_ctx: AgentPluginContext,
        *,
        scope: "LoopScope",
        budget: "TaskIterationBudget",
        step_iteration_cap: Optional[int],
        all_tools: Optional[List[Any]] = None,
        run_iteration_hooks: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Nested streaming tool loop for a single DAWP step (§6.4, D1-04).

        All events are tagged with ``loop_scope.kind="dawp"`` via ``_with_loop_scope``.
        The shared ``budget`` is consumed 1 per iteration; the ``step_iteration_cap``
        adds a per-step upper bound on top of the shared pool (§4.4, D5).

        ``run_iteration_hooks=False`` (default): ``ON_ITERATION_START`` and
        ``ON_ITERATION_END`` are **not** fired; the DAWP sub-loop is transparent to
        plugins (§6.5).

        ``plugin_state["dawp.active_run_id"]`` is set to ``scope.run_id`` on entry and
        cleared in the ``finally`` block regardless of how the loop exits.

        Tool schemas are filtered via :func:`~dawp.tools_filter.resolve_tools_for_scope`
        (D10 — ``dawp_start`` excluded inside nested runs).
        """
        from aiecs.domain.agent.plugins.dawp.loop_scope import _with_loop_scope
        from aiecs.domain.agent.plugins.dawp.tools_filter import resolve_tools_for_scope

        # Filter tool schemas for DAWP scope (§4.5, D10 — excludes dawp_start etc.)
        base_schemas: List[Dict[str, Any]] = all_tools if all_tools is not None else self._tool_schemas
        filtered_schemas: List[Dict[str, Any]] = resolve_tools_for_scope(base_schemas, scope)

        # Effective cap: min(step_iteration_cap, budget.remaining); None → no extra cap
        effective_cap: int = budget.allocate_for_step(step_iteration_cap)
        nested_consumed = 0

        state = ToolLoopRunState()
        iteration = 0

        plugin_ctx.plugin_state["dawp.active_run_id"] = scope.run_id
        try:
            while budget.remaining > 0 and nested_consumed < effective_cap:
                if run_iteration_hooks and self._plugin_manager is not None:
                    await self._plugin_manager.run_phase(
                        PluginPhase.ON_ITERATION_START,
                        ctx=plugin_ctx,
                        iteration=iteration,
                    )

                # §8.1 (R3): DAWP must emit iteration_start to be homomorphic with main loop.
                yield _with_loop_scope(
                    {
                        "type": "iteration_start",
                        "iteration": iteration + 1,
                        "max_iterations": effective_cap,
                        "remaining": budget.remaining,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    scope,
                )

                state.last_outcome = None
                async for event in self._run_tool_loop_core_iteration_streaming(
                    messages,
                    context,
                    iteration,
                    state,
                    tool_schemas_override=filtered_schemas,
                    plugin_ctx=plugin_ctx,
                ):
                    yield _with_loop_scope(event, scope)

                budget.consume(1)
                nested_consumed += 1

                if run_iteration_hooks and self._plugin_manager is not None:
                    step = self._iteration_step_payload(
                        state.last_outcome or ToolLoopIterationOutcome(kind="continue"),
                        iteration,
                        state,
                    )
                    await self._plugin_manager.run_phase(
                        PluginPhase.ON_ITERATION_END,
                        ctx=plugin_ctx,
                        iteration=iteration,
                        step=step,
                    )

                outcome = state.last_outcome
                if outcome is None or outcome.kind == "continue":
                    iteration += 1
                    continue

                if outcome.kind == "stop_match":
                    return

                if outcome.kind == "final" and outcome.result is not None:
                    yield _with_loop_scope(self._streaming_result_event_from_inner(outcome.result), scope)
                    return

                iteration += 1

        finally:
            plugin_ctx.plugin_state.pop("dawp.active_run_id", None)

        # Budget exhausted or step cap reached without natural termination (D3)
        yield _with_loop_scope(
            self._streaming_result_event_from_inner(self._tool_loop_max_iterations_result(state)),
            scope,
        )

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
            try:
                task_description = self._extract_task_description(task)
            except Exception as exc:
                yield {
                    "type": "error",
                    "error": str(exc),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            self._merge_task_images(task, context)

            self._transition_state(self.state.__class__.BUSY)
            self._current_task_id = task.get("task_id")

            yield {
                "type": "started",
                "timestamp": datetime.utcnow().isoformat(),
            }

            pending_plugin_events, event_sink = self._create_plugin_event_collector()
            plugin_ctx = self._make_plugin_context(
                task=task,
                context=context,
                task_description=task_description,
                event_sink=event_sink,
            )
            self._apply_task_plugin_configs(task=task, context=context)

            h5_result = await prepare_and_dispatch_task_entry_hooks(plugin_ctx, task_description=task_description)
            h5_rejection = task_rejection_from_hook_result(h5_result, source="user_prompt_submit")
            if h5_rejection is not None:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                loop_result = h5_rejection
                if self._plugin_manager is not None:
                    loop_result = await run_post_task_phase_with_hooks(
                        self._plugin_manager,
                        plugin_ctx,
                        loop_result,
                    )
                async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                    yield plugin_event
                result_event = self._streaming_result_event_from_inner(loop_result, execution_time=execution_time)
                yield result_event
                yield {
                    "type": "completed",
                    "success": False,
                    "execution_time": execution_time,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            plugin_configs, merge_log = self._resolve_plugin_configs(task=task, context=context)
            yield {
                "type": "plugin_config_resolved",
                "plugin_count": len(plugin_configs),
                "merge_log_summary": merge_log[:5],
                "timestamp": datetime.utcnow().isoformat(),
            }

            initial_messages: Optional[List[LLMMessage]] = None
            short = None

            if self._plugin_manager is not None:
                async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                    yield plugin_event
                await self._plugin_manager.run_phase(PluginPhase.PRE_TASK, ctx=plugin_ctx)
                async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                    yield plugin_event

                initial_messages = await self._build_initial_messages_async(task_description, context, plugin_ctx)
                h5b_result = await dispatch_user_prompt_in_history_hook(plugin_ctx, initial_messages)
                apply_hook_additional_context(plugin_ctx, initial_messages, h5b_result)
                h5b_rejection = task_rejection_from_hook_result(h5b_result, source="user_prompt_in_history")
                if h5b_rejection is not None:
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    loop_result = await run_post_task_phase_with_hooks(
                        self._plugin_manager,
                        plugin_ctx,
                        h5b_rejection,
                    )
                    async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                        yield plugin_event
                    result_event = self._streaming_result_event_from_inner(loop_result, execution_time=execution_time)
                    yield result_event
                    yield {
                        "type": "completed",
                        "success": False,
                        "execution_time": execution_time,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    return

                short = await self._plugin_manager.run_phase(PluginPhase.PRE_MAIN_LOOP, ctx=plugin_ctx)
                async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                    yield plugin_event

                if isinstance(short, PluginShortCircuitResult):
                    execution_time = (datetime.utcnow() - start_time).total_seconds()
                    loop_result = dict(short.result)
                    loop_result = await run_post_task_phase_with_hooks(
                        self._plugin_manager,
                        plugin_ctx,
                        loop_result,
                    )
                    async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                        yield plugin_event

                    result_event = self._streaming_result_event_from_inner(loop_result, execution_time=execution_time)
                    task_success = result_event.get("success", True)
                    self.update_metrics(
                        execution_time=execution_time,
                        success=task_success,
                        tokens_used=result_event.get("total_tokens"),
                        tool_calls=result_event.get("tool_calls_count", 0),
                    )
                    self._transition_state(self.state.__class__.ACTIVE)
                    self._current_task_id = None
                    self.last_active_at = datetime.utcnow()
                    yield result_event
                    yield {
                        "type": "completed",
                        "success": task_success,
                        "execution_time": execution_time,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    return
            else:
                initial_messages = await self._build_initial_messages_async(task_description, context, plugin_ctx)

            task_for_loop = effective_task_description(plugin_ctx, task_description)

            from .integration.retry_policy import EnhancedRetryPolicy, ErrorClassifier

            _retry_cfg = self._config.retry_policy
            _policy = EnhancedRetryPolicy(
                max_retries=_retry_cfg.max_retries,
                base_delay=_retry_cfg.base_delay,
                max_delay=_retry_cfg.max_delay,
                exponential_base=_retry_cfg.exponential_factor,
                jitter_factor=_retry_cfg.jitter_factor,
            )
            stream_result_event: Optional[Dict[str, Any]] = None
            for _attempt in range(_policy.max_retries + 1):
                try:
                    async for stream_event in self._tool_loop_streaming_with_plugins(
                        task_for_loop,
                        context,
                        plugin_ctx,
                        initial_messages=initial_messages,
                    ):
                        async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                            yield plugin_event
                        if stream_event.get("type") == "result":
                            stream_result_event = stream_event
                        else:
                            yield stream_event
                    break
                except Exception as _exc:
                    _error_type = ErrorClassifier.classify(_exc)
                    if _attempt >= _policy.max_retries or not ErrorClassifier.is_retryable(_error_type):
                        raise
                    _delay = _policy.calculate_delay(_attempt, _error_type)
                    logger.warning(f"Streaming attempt {_attempt + 1} failed " f"({_error_type.value}). Retrying in {_delay:.2f}s…")
                    await asyncio.sleep(_delay)

            if stream_result_event is not None:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                loop_result = self._loop_result_from_streaming_event(stream_result_event)
                loop_result = await run_post_task_phase_with_hooks(
                    self._plugin_manager,
                    plugin_ctx,
                    loop_result,
                )
                async for plugin_event in self._yield_pending_plugin_events(pending_plugin_events):
                    yield plugin_event
                formatted_result = self._streaming_result_event_from_inner(loop_result, execution_time=execution_time)
                yield formatted_result

                task_success = formatted_result.get("success", True)
                self.update_metrics(
                    execution_time=execution_time,
                    success=task_success,
                    tokens_used=formatted_result.get("total_tokens"),
                    tool_calls=formatted_result.get("tool_calls_count", 0),
                )
                self._transition_state(self.state.__class__.ACTIVE)
                self._current_task_id = None
                self.last_active_at = datetime.utcnow()
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

    def _require_function_calling_when_tools_configured(self) -> None:
        """Raise when tools are configured but the LLM client lacks Function Calling."""
        if self._tool_schemas and not self._use_function_calling:
            provider = getattr(self.llm_client, "provider_name", "unknown")
            raise ValueError(
                "HybridAgent requires an LLM client with Function Calling support when tools are configured. "
                f"Current client ({provider}) does not support tools. "
                "Use OpenAI-compatible clients: OpenAI, xAI, Anthropic, or Google Vertex."
            )

    def _build_tool_loop_llm_kwargs(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        *,
        streaming: bool = False,
        tool_schemas_override: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build kwargs for ``generate_text`` / ``stream_text`` in the tool loop.

        Args:
            tool_schemas_override: When provided, use these schemas instead of
                ``self._tool_schemas`` (e.g. for DAWP nested runs that filter
                out excluded tools — §4.5, D10).
        """
        kwargs: Dict[str, Any] = dict(
            messages=messages,
            model=self._config.llm_model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            context=context,
        )
        kwargs.update(self._config.get_llm_call_kwargs())
        schemas = tool_schemas_override if tool_schemas_override is not None else self._tool_schemas
        if schemas:
            kwargs["tools"] = [{"type": "function", "function": s} for s in schemas]
            kwargs["tool_choice"] = "auto"
            if streaming:
                kwargs["return_chunks"] = True
        return kwargs

    def _tool_loop_max_iterations_result(self, state: ToolLoopRunState) -> Dict[str, Any]:
        """Build the max-iterations result dict (sync path)."""
        logger.warning(f"HybridAgent {self.agent_id} reached max iterations")
        return {
            "success": False,
            "reason": "max_iterations_reached",
            "final_response": "Max iterations reached. Unable to complete task fully.",
            "steps": state.steps,
            "iterations": self._max_iterations,
            "tool_calls_count": state.tool_calls_count,
            "total_tokens": state.total_tokens,
        }

    def _build_tool_loop_compression_context(
        self,
        context: Dict[str, Any],
        *,
        policy: Any | None = None,
    ) -> ToolLoopCompressionContext:
        """Build W8/W11 compression context from AgentConfiguration (ADR-007, ADR-009)."""
        from aiecs.domain.context.compression.hooks import HookExecutor, HookRegistry
        from aiecs.domain.context.compression.progress import CompactProgressEmitter
        from aiecs.domain.context.compression.state import AutoCompactState
        from aiecs.domain.context.compression.tool_budget import InMemoryToolBudgetStore
        from aiecs.domain.context.compression.types import (
            InMemorySessionMemoryPort,
            SessionMemoryPort,
            ToolArtifactPort,
        )

        resolved_policy = policy or resolve_compression_policy(self._config)
        enabled = bool(self._config.enable_context_compression and resolved_policy.enabled)
        session_id = str(context.get("session_id") or self.agent_id or "")
        if enabled and self._tool_budget_store is None:
            self._tool_budget_store = InMemoryToolBudgetStore()
        if enabled and self._session_memory_port is None:
            self._session_memory_port = InMemorySessionMemoryPort()
        if enabled and self._auto_compact_state is None:
            self._auto_compact_state = AutoCompactState()
        if enabled and self._compression_hook_executor is None:
            self._compression_hook_executor = HookExecutor(HookRegistry())
        if enabled and self._compression_progress_emitter is None:
            self._compression_progress_emitter = CompactProgressEmitter()

        session_memory = context.get("session_memory_port")
        if session_memory is not None and not isinstance(session_memory, SessionMemoryPort):
            session_memory = None
        if session_memory is None and enabled:
            session_memory = self._session_memory_port

        hooks = context.get("compression_hook_executor") or context.get("hook_executor")
        if hooks is not None and not isinstance(hooks, HookExecutor):
            hooks = None
        if hooks is None and enabled:
            hooks = self._compression_hook_executor

        progress = context.get("compression_progress_emitter")
        if progress is None:
            on_progress = context.get("on_compact_progress")
            if callable(on_progress):
                progress = CompactProgressEmitter(on_progress=on_progress)
        if progress is None and enabled:
            progress = self._compression_progress_emitter

        artifact_port = context.get("tool_artifact_port") or context.get("artifact_port")
        if artifact_port is not None and not isinstance(artifact_port, ToolArtifactPort):
            artifact_port = None
        if artifact_port is None and enabled:
            artifact_port = self._tool_artifact_port

        return ToolLoopCompressionContext(
            enabled=enabled,
            policy=resolved_policy,
            session_id=session_id,
            artifact_port=artifact_port if enabled else None,
            budget_store=self._tool_budget_store if enabled else None,
            session_memory=session_memory if enabled else None,
            hooks=hooks if enabled else None,
            progress=progress if enabled else None,
            llm_client=self.llm_client,
            auto_compact_state=self._auto_compact_state if enabled else None,
        )

    async def _build_tool_loop_compression_context_async(
        self,
        context: Dict[str, Any],
    ) -> ToolLoopCompressionContext:
        """Build compression context with optional F3 layer policy resolver (L3)."""
        from aiecs.domain.context.compression.metadata import LAYER_L3
        from aiecs.domain.context.compression.policy_resolver import resolve_layer_compression_policy

        base_policy = resolve_compression_policy(self._config)
        resolved = await resolve_layer_compression_policy(
            LAYER_L3,
            context=context,
            config=self._config,
            base_policy=base_policy,
        )
        return self._build_tool_loop_compression_context(context, policy=resolved)

    async def _apply_pre_llm_compression(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        plugin_ctx: Optional[AgentPluginContext] = None,
    ) -> None:
        """Run W8/W11 pre-LLM compression in-place on ``messages``."""
        if self._auto_compact_state is not None:
            self._auto_compact_state.proactive_compact_used_this_iteration = False

        compression_ctx = await self._build_tool_loop_compression_context_async(context)
        compacted = await maybe_compact_before_llm(
            messages,
            compression_ctx=compression_ctx,
            plugin_ctx=plugin_ctx,
        )
        messages[:] = compacted

    async def _maybe_compact_after_tool_batch(
        self,
        messages: List[LLMMessage],
        *,
        compression_ctx: ToolLoopCompressionContext,
        context: Dict[str, Any],
        plugin_ctx: Optional[AgentPluginContext] = None,
    ) -> None:
        """F4 turnkey: compact after tool batch when config enabled (post plugin phase)."""
        if not self._config.compact_after_tool_batch:
            return
        if not compression_ctx.enabled:
            return

        policy = compression_ctx.policy or resolve_compression_policy(self._config)
        if not policy.enabled:
            return

        min_tokens = self._config.compact_after_tool_batch_min_tokens
        if min_tokens is not None:
            from aiecs.domain.context.compression.tokens import estimate_message_tokens

            if estimate_message_tokens(messages) < min_tokens:
                return

        from aiecs.domain.context.compression.policy import should_compress
        from aiecs.domain.context.compression.state import AutoCompactState

        if compression_ctx.auto_compact_state is None:
            compression_ctx.auto_compact_state = self._auto_compact_state or AutoCompactState()

        state = compression_ctx.auto_compact_state
        if state.proactive_compact_used_this_iteration:
            return

        if not should_compress(messages, policy, state=state):
            return

        compacted = await maybe_compact_before_llm(
            messages,
            compression_ctx=compression_ctx,
            plugin_ctx=plugin_ctx,
        )
        messages[:] = compacted

    def _normalize_tool_calls_from_response(
        self,
        tool_calls: Any,
        function_call: Any,
    ) -> List[Dict[str, Any]]:
        """Normalize ``tool_calls`` / legacy ``function_call`` to a list."""
        if tool_calls:
            return list(tool_calls)
        if function_call:
            return [
                {
                    "id": "call_0",
                    "type": "function",
                    "function": {
                        "name": function_call["name"],
                        "arguments": function_call["arguments"],
                    },
                }
            ]
        return []

    async def _process_tool_calls_batch(
        self,
        *,
        thought_raw: str,
        tool_calls_to_process: List[Dict[str, Any]],
        messages: List[LLMMessage],
        iteration: int,
        state: ToolLoopRunState,
        event_callback: Optional[Any] = None,
        compression_ctx: Optional[ToolLoopCompressionContext] = None,
        plugin_ctx: Optional[AgentPluginContext] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolLoopIterationOutcome:
        """
        Execute a batch of tool calls, append messages, and update ``state``.

        When ``event_callback`` is provided (streaming), it is awaited with event dicts.
        """
        if compression_ctx is None:
            compression_ctx = ToolLoopCompressionContext(enabled=False)

        from aiecs.domain.agent.plugins.hooks.tool_dispatch import dispatch_tool_with_hooks

        batch_count = len(tool_calls_to_process)
        event_sink_backup = plugin_ctx.event_sink if plugin_ctx is not None else None
        if plugin_ctx is not None and event_callback is not None:

            async def _hook_event_sink(event: Dict[str, Any]) -> None:
                await event_callback(event)

            plugin_ctx.event_sink = _hook_event_sink

        messages.append(
            LLMMessage(
                role="assistant",
                content=(thought_raw or "").strip() or None,
                tool_calls=tool_calls_to_process or None,
            )
        )

        # D13 (D2-04): import here so the check below can use it without a per-iteration import.
        from aiecs.domain.agent.plugins.dawp.tools_filter import DAWP_EXCLUDED_TOOL_NAMES

        try:
            for i, tool_call in enumerate(tool_calls_to_process):
                tool_name = "unknown"
                tool_call_id = tool_call.get("id") or f"call_{i}"
                try:
                    func_name = tool_call["function"]["name"]
                    func_args = tool_call["function"]["arguments"]

                    # D13 (D2-04): dawp_start must be the sole tool_call in its iteration.
                    if func_name in DAWP_EXCLUDED_TOOL_NAMES and batch_count > 1:
                        tool_name = func_name
                        rejection: Dict[str, Any] = {
                            "status": "rejected",
                            "reason": (
                                f"'{func_name}' must be the sole tool_call in this iteration; "
                                f"found {batch_count} concurrent tool calls (D13). "
                                "Call dawp_start alone in a separate turn after other tools complete."
                            ),
                        }
                        if plugin_ctx is not None:
                            hook_result = await dispatch_tool_with_hooks(
                                plugin_ctx,
                                tool_name=tool_name,
                                tool_input={},
                                tool_call_id=tool_call_id,
                                iteration=iteration,
                                batch_tool_call_count=batch_count,
                                batch_index=i,
                                assistant_turn_committed=True,
                                offload=False,
                                kernel_rejection=rejection,
                            )
                            tool_content = hook_result.tool_content or json.dumps(rejection, ensure_ascii=False)
                        else:
                            tool_content = json.dumps(rejection, ensure_ascii=False)

                        state.tool_calls_count += 1
                        state.steps.append(
                            {
                                "type": "action",
                                "tool": tool_name,
                                "operation": None,
                                "parameters": {},
                                "result": str(rejection),
                                "iteration": iteration + 1,
                            }
                        )
                        if event_callback is not None:
                            await event_callback(
                                {
                                    "type": "tool_result",
                                    "tool_name": tool_name,
                                    "result": rejection,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=tool_content,
                                tool_call_id=tool_call_id,
                            )
                        )
                        continue

                    tool_name, operation = self._parse_function_name(func_name)

                    if isinstance(func_args, str):
                        parameters = json.loads(func_args)
                    else:
                        parameters = func_args if func_args else {}

                    if event_callback is not None:
                        await event_callback(
                            {
                                "type": "tool_call",
                                "tool_name": tool_name,
                                "operation": operation,
                                "parameters": parameters,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                    async def _execute(
                        _tool_name: str = tool_name,
                        _operation: str | None = operation,
                        _parameters: Dict[str, Any] = parameters,
                    ) -> Any:
                        return await self._execute_tool(_tool_name, _operation, _parameters)

                    if plugin_ctx is not None:
                        nested_hooks = bool(plugin_ctx.plugin_state.get("dawp.active_run_id"))
                        hook_result = await dispatch_tool_with_hooks(
                            plugin_ctx,
                            tool_name=tool_name,
                            tool_input=parameters,
                            tool_call_id=tool_call_id,
                            iteration=iteration,
                            batch_tool_call_count=batch_count,
                            batch_index=i,
                            assistant_turn_committed=True,
                            offload=True,
                            compression_ctx=compression_ctx,
                            execute_tool=_execute,
                            nested=nested_hooks,
                        )
                    else:
                        hook_result = await self._dispatch_tool_without_hooks(
                            tool_name=tool_name,
                            operation=operation,
                            parameters=parameters,
                            tool_call_id=tool_call_id,
                            compression_ctx=compression_ctx,
                        )

                    if hook_result.blocked or hook_result.error_message:
                        error_content = hook_result.tool_content or hook_result.error_message or hook_result.block_reason
                        state.tool_calls_count += 1
                        state.steps.append(
                            {
                                "type": "observation",
                                "content": error_content,
                                "iteration": iteration + 1,
                                "has_error": True,
                            }
                        )
                        if event_callback is not None:
                            await event_callback(
                                {
                                    "type": "tool_error",
                                    "tool_name": tool_name,
                                    "error": error_content,
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                        messages.append(
                            LLMMessage(
                                role="tool",
                                content=error_content,
                                tool_call_id=tool_call_id,
                            )
                        )
                        continue

                    tool_result = hook_result.tool_output
                    state.tool_calls_count += 1
                    state.steps.append(
                        {
                            "type": "action",
                            "tool": tool_name,
                            "operation": operation,
                            "parameters": parameters,
                            "result": str(tool_result),
                            "iteration": iteration + 1,
                        }
                    )

                    if event_callback is not None:
                        await event_callback(
                            {
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "result": tool_result,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                    if self._config.tool_result_stop_conditions and matches_stop_condition(tool_result, self._config.tool_result_stop_conditions):
                        final_output = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result)
                        result = {
                            "final_response": final_output,
                            "steps": state.steps,
                            "iterations": iteration + 1,
                            "tool_calls_count": state.tool_calls_count,
                            "total_tokens": state.total_tokens,
                            "stop_reason": "tool_result_matched",
                        }
                        if event_callback is not None:
                            await event_callback(
                                {
                                    "type": "result",
                                    "success": True,
                                    "output": final_output,
                                    "reasoning_steps": state.steps,
                                    "tool_calls_count": state.tool_calls_count,
                                    "iterations": iteration + 1,
                                    "total_tokens": state.total_tokens,
                                    "stop_reason": "tool_result_matched",
                                    "timestamp": datetime.utcnow().isoformat(),
                                }
                            )
                        return ToolLoopIterationOutcome(kind="stop_match", result=result)

                    tool_images: List[Union[str, Dict[str, Any]]] = []
                    if isinstance(tool_result, dict) and tool_result.get("_image_b64"):
                        media_type = tool_result.get("_image_media_type", "image/png")
                        tool_images = [f"data:{media_type};base64,{tool_result['_image_b64']}"]
                    tool_content = hook_result.tool_content or (json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result))
                    messages.append(
                        LLMMessage(
                            role="tool",
                            content=tool_content,
                            tool_call_id=tool_call_id,
                            images=tool_images,
                        )
                    )

                    if isinstance(tool_result, dict) and tool_result.get("suppress_from_llm"):
                        from aiecs.domain.agent.plugins.dawp.suppress import apply_suppress_from_llm

                        messages[:] = apply_suppress_from_llm(messages, tool_call_id)

                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    state.steps.append(
                        {
                            "type": "observation",
                            "content": error_msg,
                            "iteration": iteration + 1,
                            "has_error": True,
                        }
                    )
                    if event_callback is not None:
                        await event_callback(
                            {
                                "type": "tool_error",
                                "tool_name": tool_name,
                                "error": str(e),
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )
                    messages.append(
                        LLMMessage(
                            role="tool",
                            content=error_msg,
                            tool_call_id=tool_call_id,
                        )
                    )
        finally:
            if plugin_ctx is not None:
                plugin_ctx.event_sink = event_sink_backup

        if plugin_ctx is not None and self._plugin_manager is not None:
            await self._plugin_manager.run_phase(
                PluginPhase.ON_TOOL_BATCH_END,
                ctx=plugin_ctx,
                iteration=iteration,
                messages=messages,
            )

        if self._config.compact_after_tool_batch:
            batch_ctx = compression_ctx
            if batch_ctx is None or not batch_ctx.enabled:
                batch_ctx = await self._build_tool_loop_compression_context_async(context or {})
            await self._maybe_compact_after_tool_batch(
                messages,
                compression_ctx=batch_ctx,
                context=context or {},
                plugin_ctx=plugin_ctx,
            )

        return ToolLoopIterationOutcome(kind="continue")

    async def _dispatch_tool_without_hooks(
        self,
        *,
        tool_name: str,
        operation: str | None,
        parameters: Dict[str, Any],
        tool_call_id: str,
        compression_ctx: ToolLoopCompressionContext,
    ):
        """Legacy tool path when no plugin context is available."""
        from aiecs.domain.agent.plugins.hooks.tool_dispatch import ToolHookDispatchResult

        tool_result = await self._execute_tool(tool_name, operation, parameters)
        raw_content = json.dumps(tool_result, ensure_ascii=False) if isinstance(tool_result, dict) else str(tool_result)
        tool_content = await apply_tool_output_management(
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_output=raw_content,
            compression_ctx=compression_ctx,
        )
        return ToolHookDispatchResult(
            pre_result=AggregatedHookResult.empty(),
            post_result=AggregatedHookResult.empty(),
            blocked=False,
            block_reason="",
            executed=True,
            tool_output=tool_result,
            tool_content=tool_content,
        )

    async def _run_tool_loop_core_iteration(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        iteration: int,
        state: ToolLoopRunState,
        plugin_ctx: Optional[AgentPluginContext] = None,
    ) -> ToolLoopIterationOutcome:
        """Single non-streaming tool-loop iteration (LLM call + tool batch)."""
        self._require_function_calling_when_tools_configured()
        await self._apply_pre_llm_compression(messages, context, plugin_ctx=plugin_ctx)
        compression_ctx = await self._build_tool_loop_compression_context_async(context)
        kwargs = self._build_tool_loop_llm_kwargs(messages, context, streaming=False)
        try:
            response = await self.llm_client.generate_text(**kwargs)
        except Exception as exc:
            if plugin_ctx is not None:
                await dispatch_prompt_too_long_hook(plugin_ctx, exc, iteration)
            if await maybe_reactive_compact_on_ptl(
                exc,
                messages=messages,
                compression_ctx=compression_ctx,
            ):
                kwargs = self._build_tool_loop_llm_kwargs(messages, context, streaming=False)
                response = await self.llm_client.generate_text(**kwargs)
            else:
                if plugin_ctx is not None:
                    await dispatch_llm_error_hook(plugin_ctx, exc, iteration)
                raise

        thought_raw = response.content or ""
        state.total_tokens += getattr(response, "total_tokens", 0)

        cache_read_tokens = getattr(response, "cache_read_tokens", None)
        cache_creation_tokens = getattr(response, "cache_creation_tokens", None)
        cache_hit = getattr(response, "cache_hit", None)
        if cache_read_tokens is not None or cache_creation_tokens is not None or cache_hit is not None:
            self.update_cache_metrics(
                cache_read_tokens=cache_read_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_hit=cache_hit,
            )

        state.steps.append(
            {
                "type": "thought",
                "content": thought_raw.strip(),
                "iteration": iteration + 1,
            }
        )

        tool_calls = getattr(response, "tool_calls", None)
        function_call = getattr(response, "function_call", None)
        tool_calls_to_process = self._normalize_tool_calls_from_response(tool_calls, function_call)

        if tool_calls_to_process:
            return await self._process_tool_calls_batch(
                thought_raw=thought_raw,
                tool_calls_to_process=tool_calls_to_process,
                messages=messages,
                iteration=iteration,
                state=state,
                compression_ctx=compression_ctx,
                plugin_ctx=plugin_ctx,
                context=context,
            )

        return ToolLoopIterationOutcome(
            kind="final",
            result={
                "final_response": thought_raw.strip(),
                "steps": state.steps,
                "iterations": iteration + 1,
                "tool_calls_count": state.tool_calls_count,
                "total_tokens": state.total_tokens,
            },
        )

    async def _run_tool_loop_core(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Shared LLM+tool iteration loop without plugin iteration hooks (§8.4, DAWP v2.1).

        DAWP ``StepRunner`` uses this entry; ``_tool_loop_with_plugins``
        uses :meth:`_run_tool_loop_with_iteration_hooks` instead.
        """
        return await self._run_tool_loop_with_iteration_hooks(messages, context, plugin_ctx=None)

    async def _run_tool_loop_core_iteration_streaming(
        self,
        messages: List[LLMMessage],
        context: Dict[str, Any],
        iteration: int,
        state: ToolLoopRunState,
        *,
        tool_schemas_override: Optional[List[Dict[str, Any]]] = None,
        plugin_ctx: Optional[AgentPluginContext] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Single streaming tool-loop iteration; yields events then sets ``state.last_outcome``.

        Args:
            tool_schemas_override: Override the agent's default tool schemas for this
                iteration (used by DAWP nested runner to filter excluded tools — §4.5, D10).
        """
        from aiecs.llm.clients.openai_compatible_mixin import StreamChunk

        self._require_function_calling_when_tools_configured()
        await self._apply_pre_llm_compression(messages, context, plugin_ctx=plugin_ctx)
        compression_ctx = await self._build_tool_loop_compression_context_async(context)
        kwargs = self._build_tool_loop_llm_kwargs(messages, context, streaming=True, tool_schemas_override=tool_schemas_override)
        try:
            stream_gen = self.llm_client.stream_text(**kwargs)
        except Exception as exc:
            if plugin_ctx is not None:
                await dispatch_prompt_too_long_hook(plugin_ctx, exc, iteration)
            if await maybe_reactive_compact_on_ptl(
                exc,
                messages=messages,
                compression_ctx=compression_ctx,
            ):
                kwargs = self._build_tool_loop_llm_kwargs(
                    messages,
                    context,
                    streaming=True,
                    tool_schemas_override=tool_schemas_override,
                )
                stream_gen = self.llm_client.stream_text(**kwargs)
            else:
                if plugin_ctx is not None:
                    await dispatch_llm_error_hook(plugin_ctx, exc, iteration)
                raise

        thought_tokens: List[str] = []
        tool_calls_from_stream = None

        async for chunk in stream_gen:
            if isinstance(chunk, StreamChunk):
                if chunk.type == "token" and chunk.content:
                    thought_tokens.append(chunk.content)
                    yield {
                        "type": "token",
                        "content": chunk.content,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                elif chunk.type == "tool_call" and chunk.tool_call:
                    yield {
                        "type": "tool_call_delta",
                        "tool_call": chunk.tool_call,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                elif chunk.type == "tool_calls" and chunk.tool_calls:
                    tool_calls_from_stream = chunk.tool_calls
                    yield {
                        "type": "tool_calls_ready",
                        "tool_calls": chunk.tool_calls,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
            else:
                thought_tokens.append(chunk)
                yield {
                    "type": "token",
                    "content": chunk,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        thought_raw = "".join(thought_tokens)
        state.steps.append(
            {
                "type": "thought",
                "content": thought_raw.strip(),
                "iteration": iteration + 1,
            }
        )

        if tool_calls_from_stream:
            events: List[Dict[str, Any]] = []

            async def _emit(event: Dict[str, Any]) -> None:
                events.append(event)

            outcome = await self._process_tool_calls_batch(
                thought_raw=thought_raw,
                tool_calls_to_process=tool_calls_from_stream,
                messages=messages,
                iteration=iteration,
                state=state,
                event_callback=_emit,
                compression_ctx=compression_ctx,
                plugin_ctx=plugin_ctx,
                context=context,
            )
            for event in events:
                yield event
            state.last_outcome = outcome
            return

        state.last_outcome = ToolLoopIterationOutcome(
            kind="final",
            result={
                "final_response": thought_raw.strip(),
                "steps": state.steps,
                "iterations": iteration + 1,
                "tool_calls_count": state.tool_calls_count,
                "total_tokens": state.total_tokens,
            },
        )

    async def _tool_loop_streaming(self, task: str, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute tool loop with streaming (BetaToolRunner-style).

        Delegates to :meth:`_tool_loop_streaming_with_plugins` without a streaming
        ``event_sink`` (direct callers / legacy tests).
        """
        plugin_ctx = self._make_plugin_context(
            task={"description": task},
            context=context,
            task_description=task,
        )
        async for event in self._tool_loop_streaming_with_plugins(task, context, plugin_ctx):
            yield event

    async def _tool_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool loop (BetaToolRunner-style).
        Append-only messages; native tool_use/tool_result; no iteration labels.

        Delegates iteration to :meth:`_run_tool_loop_core` (§8.4, DAWP-1).

        Args:
            task: Task description
            context: Context dictionary

        Returns:
            Result dictionary with 'final_response', 'steps', 'iterations'
        """
        plugin_ctx = self._make_plugin_context(
            task={"description": task},
            context=context,
            task_description=task,
        )
        messages = await self._build_initial_messages_async(task, context, plugin_ctx)
        return await self._run_tool_loop_core(messages, context)

    def _make_plugin_context(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any],
        task_description: str,
        *,
        event_sink: Optional[Any] = None,
        plugin_state: Optional[Dict[str, Any]] = None,
    ) -> AgentPluginContext:
        """Create per-task plugin context (§5.4, §8.2)."""
        return AgentPluginContext(
            agent=self,
            task=task,
            context=context,
            task_description=task_description,
            plugin_state=dict(plugin_state or {}),
            event_sink=event_sink,
        )

    def _build_initial_messages_system(self) -> List[LLMMessage]:
        """System prompts only (before BUILD_MESSAGES plugin phase)."""
        messages: List[LLMMessage] = []
        for prompt_dict in self._build_system_prompts():
            content = prompt_dict.get("content", "")
            if not content:
                continue

            prompt_cache_control = prompt_dict.get("cache_control")
            if prompt_cache_control is None:
                cache_control = CacheControl(type="ephemeral") if self._config.enable_prompt_caching else None
            else:
                cache_control = CacheControl(type="ephemeral") if prompt_cache_control else None

            messages.append(
                LLMMessage(
                    role="system",
                    content=content,
                    cache_control=cache_control,
                )
            )
        return messages

    def _append_initial_messages_context_and_task(
        self,
        task: str,
        context: Dict[str, Any],
        messages: List[LLMMessage],
    ) -> List[LLMMessage]:
        """Additional Context and Task user message (after BUILD_MESSAGES; §8.3)."""
        task_images: List[Any] = []
        if context:
            context_images = context.get("images")
            if context_images:
                if isinstance(context_images, list):
                    task_images.extend(context_images)
                else:
                    task_images.append(context_images)

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

        messages.append(
            LLMMessage(
                role="user",
                content=f"Task: {task}",
                images=task_images if task_images else [],
            )
        )
        return messages

    async def _build_initial_messages_async(
        self,
        task: str,
        context: Dict[str, Any],
        plugin_ctx: AgentPluginContext,
    ) -> List[LLMMessage]:
        """
        Build initial messages with plugin BUILD_MESSAGES (§8.3, §7.1–§7.2).

        History and skill injection are owned by MemoryPlugin / SkillPlugin.
        """
        messages = self._build_initial_messages_system()
        if self._plugin_manager is not None:
            messages = await self._plugin_manager.run_phase(
                PluginPhase.BUILD_MESSAGES,
                ctx=plugin_ctx,
                messages=messages,
            )
        await dispatch_build_messages_hook(plugin_ctx, messages)
        return self._append_initial_messages_context_and_task(task, context, messages)

    def _build_initial_messages(self, task: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """
        Synchronous message build for legacy callers (no plugin phases).

        Prefer :meth:`_build_initial_messages_async` when plugins must run.
        History and skill blocks are not applied here; use the async path instead.
        """
        messages = self._build_initial_messages_system()
        return self._append_initial_messages_context_and_task(task, context, messages)

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

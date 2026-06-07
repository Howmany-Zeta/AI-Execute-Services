# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWPPlugin — Dynamic Adaptive Work Process builtin plugin (§9, §6.1).

Lifecycle (§9):
  PRE_TASK         — load and compile *.dawp.md; build workflow_activations list;
                     initialise ``plugin_state["dawp.scheduler"]`` + ``"dawp.pending"``
  PRE_MAIN_LOOP    — enqueue ``pre_main_loop`` activations via RunScheduler (§4.2, D7);
                     MUST NOT return ``PluginShortCircuitResult`` (§9)
  ON_ITERATION_END — RunScheduler checkpoint for ``on_response_trigger`` (§4.2.1, §6.5);
                     MUST NOT call LLM or yield streaming events (§6.5)
  BUILD_MESSAGES   — inject trigger_instruction for on_response_trigger workflows (D1-11)
  POST_TASK        — clean up all ``dawp.*`` plugin_state keys; remove temp files

Priority 45 (between knowledge@40 and memory@80). Never returns PluginShortCircuitResult
unless explicit ``abort_main`` is set (constraint D9).
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from aiecs.domain.agent.plugins.base import BaseAgentPlugin
from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.models import PluginMetadata

if TYPE_CHECKING:
    from aiecs.domain.agent.base_agent import BaseAIAgent
    from aiecs.domain.agent.plugins.models import PluginConfig

logger = logging.getLogger(__name__)

PLUGIN_STATE_SCHEDULER_KEY = "dawp.scheduler"
PLUGIN_STATE_WORKFLOW_KEY = "dawp.workflow"
PLUGIN_STATE_PENDING_KEY = "dawp.pending"

# ``plugin_state["dawp.scheduler"]`` holds List[Tuple[str, Activation]] — the
# pre-built workflow_activations list used by every RunScheduler checkpoint call.
# Type alias for clarity:
_WorkflowActivations = list  # list[tuple[str, Activation]]

_CUSTOM_REASONING_DEPRECATION_MSG = "Plugin name 'custom_reasoning' is deprecated and will be removed in a future release. " "Use 'dawp' instead."


class DawpPlugin(BaseAgentPlugin):
    """
    Builtin DAWP plugin.

    D0-05: PRE_TASK loads and compiles the configured *.dawp.md document.
    D2-01: PRE_TASK injects dawp_start (and legacy aliases) into agent._tool_instances;
           POST_TASK removes them and unbinds plugin_state.
    """

    metadata: ClassVar[PluginMetadata] = PluginMetadata(
        name="dawp",
        version="0.1.0",
        description="DAWP (Dynamic Adaptive Work Process) plugin (§6.1, §9)",
        priority=45,
        default_enabled=False,
    )

    def __init__(self, config: PluginConfig, agent: BaseAIAgent) -> None:
        super().__init__(config, agent)
        if config.name == "custom_reasoning":
            warnings.warn(
                _CUSTOM_REASONING_DEPRECATION_MSG,
                DeprecationWarning,
                stacklevel=2,
            )
        # D2-01: create handler instances once; plugin_state bound per-task.
        from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import (
            DawpLegacyAliasHandler,
            DawpStartHandler,
        )

        self._dawp_start_handler = DawpStartHandler()
        self._dawp_legacy_handlers = {
            "dawp_run": DawpLegacyAliasHandler("dawp_run", self._dawp_start_handler),
            "dawp_publish_workflow": DawpLegacyAliasHandler("dawp_publish_workflow", self._dawp_start_handler),
        }

    async def on_pre_task(self, ctx: AgentPluginContext) -> None:
        """Load and compile the DAWP workflow document (§9 PRE_TASK).

        Reads ``document_path`` from plugin options. On success, stores the compiled
        ``DAWPWorkflow`` at ``plugin_state["dawp.workflow"]`` and builds the
        ``plugin_state["dawp.scheduler"]`` workflow_activations list used by every
        RunScheduler checkpoint call.  Compilation errors are logged as warnings
        (plugin continues without a workflow).
        """
        from aiecs.domain.agent.plugins.dawp import document_loader
        from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError
        from aiecs.domain.agent.plugins.dawp.workflow_registry import register_workflow

        import uuid as _uuid

        document_path: str | None = self._config.options.get("document_path")

        ctx.plugin_state[PLUGIN_STATE_WORKFLOW_KEY] = None
        ctx.plugin_state[PLUGIN_STATE_SCHEDULER_KEY] = []  # workflow_activations
        ctx.plugin_state[PLUGIN_STATE_PENDING_KEY] = []
        ctx.plugin_state["dawp.workflows"] = {}
        ctx.plugin_state["dawp._run_count"] = 0

        # D2-02: store limits dict and task_id for dynamic workflow compilation
        ctx.plugin_state["dawp.dynamic_limits"] = self._config.options.get("dynamic_workflow_limits") or {}
        raw_task_id = getattr(self._agent, "_current_task_id", None)
        ctx.plugin_state["dawp.task_id"] = str(raw_task_id) if raw_task_id else str(_uuid.uuid4())

        # §8.1.1: optional boundary events (dawp_run_started / dawp_run_completed)
        ctx.plugin_state["dawp.stream_boundary_events"] = bool(self._config.options.get("stream_boundary_events", False))
        ctx.plugin_state["dawp.plugin_options"] = dict(self._config.options)

        from aiecs.domain.agent.plugins.dawp.document_path_policy import (
            configure_document_path_policy,
        )

        configure_document_path_policy(ctx.plugin_state, self._config.options)

        if document_path:
            path = Path(document_path)
            try:
                workflow = document_loader.compile_file(path)
            except DawpDocumentError as exc:
                logger.warning(
                    "DawpPlugin: failed to compile %s: %s",
                    path,
                    exc,
                )
            except OSError as exc:
                logger.warning(
                    "DawpPlugin: cannot read document %s: %s",
                    path,
                    exc,
                )
            else:
                register_workflow(ctx.plugin_state, workflow)
                # Build reusable (workflow_id, Activation) list for RunScheduler
                workflow_id = workflow.metadata.name
                ctx.plugin_state[PLUGIN_STATE_SCHEDULER_KEY] = [(workflow_id, activation) for activation in workflow.activations]
                logger.debug(
                    "DawpPlugin: loaded workflow %r (%d steps, %d activations) from %s",
                    workflow_id,
                    len(workflow.steps),
                    len(workflow.activations),
                    path,
                )

        # D2-01: inject dawp_start (and legacy aliases) into agent tool registry.
        # Always done regardless of whether a document_path is configured, so
        # the model can call dawp_start with workflow_source='dynamic' too.
        self._inject_dawp_tools(ctx)

    def _inject_dawp_tools(self, ctx: AgentPluginContext) -> None:
        """Inject ``dawp_start`` (and legacy aliases) into the agent's tool registry (D2-01).

        Called from :meth:`on_pre_task` so that ToolPlugin's ``on_agent_init`` has
        already populated ``_tool_instances`` / ``_tool_schemas`` before we extend them.
        Binding ``plugin_state`` enables the handler to access DAWP scheduler state.
        """
        from aiecs.domain.agent.plugins.builtin.tools.dawp_start_tool import (
            DAWP_START_TOOL_SCHEMA,
        )

        handler = self._dawp_start_handler
        handler.bind_plugin_state(ctx.plugin_state)

        agent = self._agent
        instances: dict[str, Any] = getattr(agent, "_tool_instances", None) or {}
        instances["dawp_start"] = handler
        for name, legacy in self._dawp_legacy_handlers.items():
            instances[name] = legacy
        agent._tool_instances = instances

        schemas: list[dict[str, Any]] = list(getattr(agent, "_tool_schemas", None) or [])
        if not any(s.get("name") == "dawp_start" for s in schemas):
            schemas.append(DAWP_START_TOOL_SCHEMA)
        agent._tool_schemas = schemas  # type: ignore[attr-defined]

        logger.debug(
            "DawpPlugin[PRE_TASK]: registered dawp_start tool for agent %s",
            getattr(agent, "agent_id", "unknown"),
        )

    async def on_build_messages(
        self,
        ctx: AgentPluginContext,
        messages: list,
    ) -> list:
        """Inject ``trigger_instruction`` for ``on_response_trigger`` activations (§9, D1-11).

        For every ``on_response_trigger`` activation whose ``trigger_instruction`` is set,
        appends a ``system`` message instructing the main-loop agent when to emit the
        ``dawp_trigger`` token.  ``pre_main_loop`` activations and activations with no
        ``trigger_instruction`` are silently skipped.

        The injected messages are appended after existing system prompts so the main
        agent receives the reminder in its initial context (§9 BUILD_MESSAGES phase).
        """
        from aiecs.llm import LLMMessage

        workflow_activations: _WorkflowActivations = ctx.plugin_state.get(PLUGIN_STATE_SCHEDULER_KEY, [])
        if not workflow_activations:
            return messages

        injected = list(messages)
        for _workflow_id, activation in workflow_activations:
            if activation.placement.type == "on_response_trigger" and activation.trigger_instruction:
                injected.append(
                    LLMMessage(
                        role="system",
                        content=activation.trigger_instruction.strip(),
                    )
                )
        return injected

    async def on_pre_main_loop(self, ctx: AgentPluginContext) -> None:
        """Enqueue ``pre_main_loop`` activations (§9, §4.2, D7).

        Calls :func:`~run_scheduler.schedule_at_checkpoint` with
        ``phase="pre_main_loop"`` to append matching activations to
        ``plugin_state["dawp.pending"]``.  The pending queue is drained by
        HybridAgent (§6.5, D1-09), not here.

        Never returns :class:`~models.PluginShortCircuitResult` (§9 constraint).
        """
        from aiecs.domain.agent.plugins.dawp.enqueue_guard import build_enqueue_guard
        from aiecs.domain.agent.plugins.dawp.run_scheduler import schedule_at_checkpoint

        workflow_activations: _WorkflowActivations = ctx.plugin_state.get(PLUGIN_STATE_SCHEDULER_KEY, [])
        if not workflow_activations:
            return None

        guard = build_enqueue_guard(self._config.options)

        newly = schedule_at_checkpoint(
            workflow_activations,
            phase="pre_main_loop",
            plugin_state=ctx.plugin_state,
            iteration=0,
            enqueue_guard=guard,
        )
        if newly:
            logger.debug(
                "DawpPlugin[PRE_MAIN_LOOP]: enqueued %d run(s): %s",
                len(newly),
                [r.workflow_id for r in newly],
            )
        return None

    async def on_iteration_end(
        self,
        ctx: AgentPluginContext,
        iteration: int,
        step: dict[str, Any],
    ) -> None:
        """RunScheduler checkpoint for ``on_response_trigger`` (§9, §4.2.1, §6.5).

        Extracts the most-recent assistant visible text from the iteration step
        payload and calls :func:`~run_scheduler.schedule_at_checkpoint` with
        ``phase="on_iteration_end"``.  Matching ``on_response_trigger`` activations
        are appended to ``plugin_state["dawp.pending"]``.

        Constraints (§6.5):
        - MUST NOT call the LLM.
        - MUST NOT ``async for`` the nested runner or yield streaming events.
        - Draining the pending queue is HybridAgent's responsibility (D1-09).
        """
        from aiecs.domain.agent.plugins.dawp.enqueue_guard import build_enqueue_guard
        from aiecs.domain.agent.plugins.dawp.run_scheduler import schedule_at_checkpoint

        workflow_activations: _WorkflowActivations = ctx.plugin_state.get(PLUGIN_STATE_SCHEDULER_KEY, [])
        if not workflow_activations:
            return

        # Extract the last assistant "thought" from the step payload
        assistant_text: str | None = None
        for s in reversed(step.get("steps", [])):
            if s.get("type") == "thought":
                assistant_text = s.get("content")
                break

        guard = build_enqueue_guard(self._config.options)

        newly = schedule_at_checkpoint(
            workflow_activations,
            phase="on_iteration_end",
            plugin_state=ctx.plugin_state,
            assistant_text=assistant_text,
            iteration=iteration,
            enqueue_guard=guard,
        )
        if newly:
            logger.debug(
                "DawpPlugin[ON_ITERATION_END]: enqueued %d run(s) at iteration=%d: %s",
                len(newly),
                iteration,
                [r.workflow_id for r in newly],
            )

    async def on_post_task(self, ctx: AgentPluginContext, result: dict[str, Any]) -> dict[str, Any]:
        """Clean up all ``dawp.*`` plugin_state entries, temp files, and tool injections (§9 POST_TASK)."""
        # Collect temp document paths before clearing state
        temp_paths: list[str] = []
        for run in ctx.plugin_state.get(PLUGIN_STATE_PENDING_KEY, []):
            if hasattr(run, "temp_document_path") and run.temp_document_path:
                temp_paths.append(run.temp_document_path)

        # Remove all dawp.* keys
        dawp_keys = [k for k in list(ctx.plugin_state) if k.startswith("dawp.")]
        for key in dawp_keys:
            ctx.plugin_state.pop(key, None)

        # Remove temp files (dynamic workflows persisted by dawp_start D2-02)
        # unless retain_for_debug is set (useful for post-mortem inspection)
        retain_for_debug = bool(self._config.options.get("retain_for_debug", False))
        if not retain_for_debug:
            for path_str in temp_paths:
                try:
                    Path(path_str).unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("DawpPlugin[POST_TASK]: failed to remove temp file %s: %s", path_str, exc)
        elif temp_paths:
            logger.debug(
                "DawpPlugin[POST_TASK]: retain_for_debug=True; keeping %d temp file(s): %s",
                len(temp_paths),
                temp_paths,
            )

        # D2-01: unbind plugin_state and remove dawp_start from agent tool registry
        self._dawp_start_handler.bind_plugin_state(None)
        agent = self._agent
        instances: dict[str, Any] = getattr(agent, "_tool_instances", None) or {}
        _tool_names = {"dawp_start", "dawp_run", "dawp_publish_workflow"}
        for name in _tool_names:
            instances.pop(name, None)
        schemas: list[dict[str, Any]] = getattr(agent, "_tool_schemas", None) or []
        agent._tool_schemas = [s for s in schemas if s.get("name") not in _tool_names]  # type: ignore[attr-defined]

        logger.debug(
            "DawpPlugin[POST_TASK]: cleaned up %d dawp.* keys; %d temp files",
            len(dawp_keys),
            len(temp_paths),
        )
        return result

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
``dawp_start`` built-in tool — D2-01 / D2-02.

Provides the sole model-facing DAWP trigger tool.  When the LLM calls ``dawp_start``,
the handler validates the request, compiles the workflow (static or dynamic path),
enforces D11 hard limits for dynamic workflows, and enqueues a
:class:`~schema.DawpPendingRun` with ``drain_mode="inline"`` for HybridAgent to drain
within the same iteration (§4.3, §5.4).

Design constraints (§4.3, §4.3.2):
  D10  — Reject nested calls when ``dawp.active_run_id`` is set in plugin_state.
  D13  — ``dawp_start`` must be the sole tool_call in its iteration (HybridAgent).
  D12  — ``suppress_from_llm=True`` in ack; paired message suppression by D2-03.

Legacy aliases:
  ``dawp_run`` / ``dawp_publish_workflow`` → forward to the same handler
  with a :class:`DeprecationWarning`.  The agent registers them under separate
  names so the LLM can still use old schemas while the operator migrates.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON function schema (sent to the LLM)
# ---------------------------------------------------------------------------

DAWP_START_TOOL_SCHEMA: dict[str, Any] = {
    "name": "dawp_start",
    "description": (
        "Launch a DAWP (Dynamic Adaptive Work Process) workflow run. "
        "RULE (D13): dawp_start MUST be the ONLY tool call in its iteration — "
        "calling it alongside any other tool in the same turn will be rejected. "
        "If you need other tools first, complete them in earlier turns, then call "
        "dawp_start alone in a dedicated turn. "
        "Use workflow_source='static' for pre-configured workflows (identified by "
        "workflow_id or document_path) or workflow_source='dynamic' to supply "
        "the full *.dawp.md text inline via document_content."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "workflow_source": {
                "type": "string",
                "enum": ["static", "dynamic"],
                "description": "Source of the workflow document: 'static' (pre-registered) or 'dynamic' (inline content).",
            },
            "workflow_id": {
                "type": "string",
                "description": ("Registered workflow ID for workflow_source='static'. " "Optional for 'dynamic' (defaults to 'dynamic-<uuid>')."),
            },
            "document_path": {
                "type": "string",
                "description": "Alternative to workflow_id for workflow_source='static': path to the *.dawp.md file.",
            },
            "document_content": {
                "type": "string",
                "description": "Full *.dawp.md document text. Required when workflow_source='dynamic'.",
            },
        },
        "required": ["workflow_source"],
    },
}


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


async def handle_dawp_start(
    plugin_state: dict[str, Any],
    *,
    workflow_source: str,
    workflow_id: str | None = None,
    document_content: str | None = None,
    document_path: str | None = None,
) -> dict[str, Any]:
    """Core handler: validate, enqueue, return ack or rejection dict.

    Does NOT drain the run; that is HybridAgent's responsibility (§6.5, D2-05).
    D12 suppress uses ``suppress_from_llm=True`` in the tool ack (HybridAgent pairs removal).
    """
    from aiecs.domain.agent.plugins.dawp.schema import DawpPendingRun
    from aiecs.domain.agent.plugins.dawp.workflow_registry import register_workflow

    # D10: reject nested calls
    if plugin_state.get("dawp.active_run_id"):
        return {
            "status": "rejected",
            "reason": "dawp_start cannot be called inside an active DAWP run (D10)",
        }

    if workflow_source == "static":
        workflow = None
        if document_path:
            from aiecs.domain.agent.plugins.dawp.document_path_policy import (
                validate_static_document_path,
            )

            resolved, reject_reason = validate_static_document_path(document_path, plugin_state)
            if reject_reason is not None:
                return {"status": "rejected", "reason": reject_reason}

            from aiecs.domain.agent.plugins.dawp import document_loader
            from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError

            assert resolved is not None
            try:
                workflow = document_loader.compile_file(resolved)
            except DawpDocumentError as exc:
                return {"status": "rejected", "reason": str(exc)}
            except OSError as exc:
                return {"status": "rejected", "reason": f"cannot read document_path: {exc}"}
            register_workflow(plugin_state, workflow)
            effective_id = workflow.metadata.name
            if workflow_id is not None and workflow_id != effective_id:
                return {
                    "status": "rejected",
                    "reason": (f"document_path compiles to workflow_id={effective_id!r}, " f"but workflow_id={workflow_id!r} was requested"),
                }
        elif workflow_id is not None:
            registry = plugin_state.get("dawp.workflows") or {}
            workflow = registry.get(workflow_id)
            if workflow is None:
                legacy = plugin_state.get("dawp.workflow")
                if legacy is not None and legacy.metadata.name == workflow_id:
                    workflow = legacy
            if workflow is None:
                return {
                    "status": "rejected",
                    "reason": f"workflow_id={workflow_id!r} not found in registry",
                }
            effective_id = workflow_id
        else:
            workflow = plugin_state.get("dawp.workflow")
            if workflow is None:
                return {
                    "status": "rejected",
                    "reason": ("no compiled workflow in plugin_state; " "provide workflow_id, document_path, or configure DawpPlugin document_path"),
                }
            effective_id = workflow.metadata.name

    elif workflow_source == "dynamic":
        if not document_content:
            return {
                "status": "rejected",
                "reason": "document_content is required when workflow_source='dynamic'",
            }

        limits: dict[str, Any] = plugin_state.get("dawp.dynamic_limits") or {}

        # Check require_remaining_budget before expensive compilation
        require_budget = int(limits.get("require_remaining_budget", 3))
        budget = plugin_state.get("task.iteration_budget")
        if budget is not None and hasattr(budget, "remaining"):
            if budget.remaining < require_budget:
                return {
                    "status": "rejected",
                    "reason": (f"insufficient remaining budget: need {require_budget}, " f"have {budget.remaining}"),
                }

        # Compile with limits (raises DawpDocumentError on violations)
        from aiecs.domain.agent.plugins.dawp import document_loader
        from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError

        try:
            workflow = document_loader.compile(
                document_content,
                dynamic_workflow_limits=limits or None,
            )
        except DawpDocumentError as exc:
            return {"status": "rejected", "reason": str(exc)}

        # Write temp file for audit and replay
        from aiecs.domain.agent.plugins.dawp.temp_store import write_task_temp_md

        task_id: str = plugin_state.get("dawp.task_id") or "unknown"
        try:
            temp_path = write_task_temp_md(document_content, task_id=task_id)
        except OSError as exc:
            logger.warning("dawp_start: failed to write temp file: %s", exc)
            temp_path = None

        effective_id = workflow.metadata.name
        register_workflow(plugin_state, workflow)
        run = DawpPendingRun(
            trigger="tool",
            workflow_source="dynamic",
            workflow_id=effective_id,
            temp_document_path=str(temp_path) if temp_path else None,
            enqueued_at_iteration=plugin_state.get("task.current_iteration", 0),
            drain_mode="inline",
        )
        from aiecs.domain.agent.plugins.dawp.enqueue_guard import append_pending_run_if_allowed

        guard_reason = append_pending_run_if_allowed(plugin_state, run)
        if guard_reason is not None:
            return {"status": "rejected", "reason": guard_reason}

        logger.debug(
            "dawp_start: enqueued dynamic DawpPendingRun workflow_id=%r temp=%s",
            effective_id,
            temp_path,
        )
        return {
            "status": "accepted",
            "workflow_id": effective_id,
            "workflow_source": "dynamic",
            "suppress_from_llm": True,
        }

    else:
        return {
            "status": "rejected",
            "reason": f"unknown workflow_source={workflow_source!r}; expected 'static' or 'dynamic'",
        }

    # Enqueue pending run for inline drain (HybridAgent inline path)
    run = DawpPendingRun(
        trigger="tool",
        workflow_source="static",
        workflow_id=effective_id,
        enqueued_at_iteration=plugin_state.get("task.current_iteration", 0),
        drain_mode="inline",
    )
    from aiecs.domain.agent.plugins.dawp.enqueue_guard import append_pending_run_if_allowed

    guard_reason = append_pending_run_if_allowed(plugin_state, run)
    if guard_reason is not None:
        return {"status": "rejected", "reason": guard_reason}

    return {
        "status": "accepted",
        "workflow_id": effective_id,
        "workflow_source": workflow_source,
        "suppress_from_llm": True,
    }


# ---------------------------------------------------------------------------
# Callable wrappers registered in agent._tool_instances
# ---------------------------------------------------------------------------


class DawpStartHandler:
    """Plugin-managed callable for the ``dawp_start`` tool.

    ``plugin_state`` is bound per-task by :class:`~dawp_plugin.DawpPlugin`
    via :meth:`bind_plugin_state`; it is ``None`` between tasks.
    """

    name = "dawp_start"

    def __init__(self) -> None:
        self._plugin_state: dict[str, Any] | None = None

    def bind_plugin_state(self, plugin_state: dict[str, Any] | None) -> None:
        """Attach (or detach) the current task's plugin_state."""
        self._plugin_state = plugin_state

    async def run_async(
        self,
        *,
        workflow_source: str,
        workflow_id: str | None = None,
        document_content: str | None = None,
        document_path: str | None = None,
    ) -> dict[str, Any]:
        return await handle_dawp_start(
            self._plugin_state if self._plugin_state is not None else {},
            workflow_source=workflow_source,
            workflow_id=workflow_id,
            document_content=document_content,
            document_path=document_path,
        )


class DawpLegacyAliasHandler:
    """Forwards legacy tool names (``dawp_run``, ``dawp_publish_workflow``) to ``dawp_start``.

    Emits :class:`DeprecationWarning` on each call (§4.3, D8/D9 — merged/deprecated).
    """

    def __init__(self, legacy_name: str, delegate: DawpStartHandler) -> None:
        self.name = legacy_name
        self._delegate = delegate

    async def run_async(self, **kwargs: Any) -> dict[str, Any]:
        warnings.warn(
            f"Tool {self.name!r} is deprecated; use 'dawp_start' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self._delegate.run_async(**kwargs)

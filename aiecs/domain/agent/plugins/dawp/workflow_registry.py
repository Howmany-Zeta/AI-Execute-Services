# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Workflow registry for DAWP runs — multi-workflow and dynamic drain resolution.

Stores compiled :class:`~schema.DAWPWorkflow` objects keyed by ``metadata.name`` so
HybridAgent can resolve any pending :class:`~schema.DawpPendingRun`, including
dynamic ``dawp_start`` runs and multi-workflow config activations (R6).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aiecs.domain.agent.plugins.dawp.schema import DAWPWorkflow, DawpPendingRun

logger = logging.getLogger(__name__)

PLUGIN_STATE_WORKFLOWS_KEY = "dawp.workflows"
PLUGIN_STATE_WORKFLOW_KEY = "dawp.workflow"


def register_workflow(plugin_state: dict[str, Any], workflow: DAWPWorkflow) -> str:
    """Register *workflow* under ``dawp.workflows[<name>]`` and return its id."""
    workflow_id = workflow.metadata.name
    registry: dict[str, DAWPWorkflow] = plugin_state.setdefault(PLUGIN_STATE_WORKFLOWS_KEY, {})
    registry[workflow_id] = workflow
    # Primary alias: first registered or explicit reload of configured document
    if plugin_state.get(PLUGIN_STATE_WORKFLOW_KEY) is None:
        plugin_state[PLUGIN_STATE_WORKFLOW_KEY] = workflow
    return workflow_id


def resolve_workflow_for_run(
    plugin_state: dict[str, Any],
    run: DawpPendingRun,
) -> DAWPWorkflow | None:
    """Resolve the compiled workflow for *run*, or ``None`` when unavailable."""
    registry: dict[str, DAWPWorkflow] = plugin_state.get(PLUGIN_STATE_WORKFLOWS_KEY) or {}
    workflow = registry.get(run.workflow_id)
    if workflow is not None:
        return workflow

    legacy = plugin_state.get(PLUGIN_STATE_WORKFLOW_KEY)
    if isinstance(legacy, DAWPWorkflow) and legacy.metadata.name == run.workflow_id:
        return legacy

    if run.temp_document_path:
        from aiecs.domain.agent.plugins.dawp import document_loader
        from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError

        path = Path(run.temp_document_path)
        try:
            workflow = document_loader.compile_file(path)
        except (DawpDocumentError, OSError) as exc:
            logger.warning(
                "workflow_registry: failed to compile temp document %s for workflow=%r: %s",
                path,
                run.workflow_id,
                exc,
            )
            return None
        register_workflow(plugin_state, workflow)
        return workflow

    return None

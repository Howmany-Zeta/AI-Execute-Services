# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Runtime ``enqueue_guard`` built from ``PluginConfig.options.enqueue_guard`` (§4.1.2).
"""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.plugins.dawp.run_scheduler import EnqueueGuard
from aiecs.domain.agent.plugins.dawp.schema import DawpPendingRun

_RUN_COUNT_KEY = "dawp._run_count"


def build_enqueue_guard(options: dict[str, Any]) -> EnqueueGuard | None:
    """Return an :data:`~run_scheduler.EnqueueGuard` from plugin options, or ``None``."""
    guard_opts = options.get("enqueue_guard")
    if not isinstance(guard_opts, dict) or not guard_opts:
        return None

    allowed = guard_opts.get("allowed_workflows", "*")
    max_runs = guard_opts.get("max_runs_per_task")
    require_budget = guard_opts.get("require_remaining_budget")

    allowed_list: list[str] | None
    if allowed == "*":
        allowed_list = None
    elif isinstance(allowed, list):
        allowed_list = [str(w) for w in allowed]
    else:
        allowed_list = None

    def guard(run: DawpPendingRun, plugin_state: dict[str, Any]) -> bool:
        if allowed_list is not None and run.workflow_id not in allowed_list:
            return False

        if max_runs is not None:
            executed = int(plugin_state.get(_RUN_COUNT_KEY, 0))
            pending = len(plugin_state.get("dawp.pending", []))
            if executed + pending >= int(max_runs):
                return False

        if require_budget is not None:
            budget = plugin_state.get("task.iteration_budget")
            if budget is not None and hasattr(budget, "remaining"):
                if budget.remaining < int(require_budget):
                    return False

        return True

    return guard


def check_enqueue_allowed(
    run: DawpPendingRun,
    plugin_state: dict[str, Any],
    *,
    options: dict[str, Any] | None = None,
) -> str | None:
    """Return a rejection reason when *run* is blocked by guard, else ``None``."""
    opts = options if options is not None else plugin_state.get("dawp.plugin_options") or {}
    guard = build_enqueue_guard(opts)
    if guard is None:
        return None
    if guard(run, plugin_state):
        return None
    return "enqueue_guard blocked this DAWP run (§4.1.2)"


def append_pending_run_if_allowed(
    plugin_state: dict[str, Any],
    run: DawpPendingRun,
) -> str | None:
    """Append *run* to ``dawp.pending`` when guard allows; return rejection reason else."""
    reason = check_enqueue_allowed(run, plugin_state)
    if reason is not None:
        return reason
    plugin_state.setdefault("dawp.pending", []).append(run)
    return None

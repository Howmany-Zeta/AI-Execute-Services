# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
RunScheduler — DAWP activation matcher and pending-run enqueuer (§6.2, §4.2, D7).

Evaluates workflow activations at each checkpoint and appends matching
:class:`~aiecs.domain.agent.plugins.dawp.schema.DawpPendingRun` entries to
``plugin_state["dawp.pending"]`` (FIFO).

Supported placement types (§4.2)
---------------------------------
``pre_main_loop``
    Matches when ``phase="pre_main_loop"`` is passed.  One enqueue per workflow per
    call; no text-scan required.

``on_response_trigger``
    Matches when ``phase="on_iteration_end"`` and the ``dawp_trigger`` token appears
    on a *scannable line* (§6.0.2.2) of *assistant_text*.  Respects ``trigger_once``
    via ``plugin_state["dawp.triggered.<token>"]`` (managed by
    :func:`~completion.matches_response_trigger`).

Design constraints
------------------
- **No draining** — this module only enqueues.  HybridAgent drains (§6.5, D1-09).
- **FIFO** — matching runs are appended in ``workflow_activations`` order.
- **R6 compliance** — all matching activations at the same checkpoint are enqueued;
  no cap unless ``enqueue_guard`` blocks them.

References: CUSTOM_REASONING_PLUGIN_DESIGN.md §6.2, §4.2, §4.2.1, R6.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal

from typing import cast

from aiecs.domain.agent.plugins.dawp.completion import matches_response_trigger
from aiecs.domain.agent.plugins.dawp.schema import Activation, DawpPendingRun

logger = logging.getLogger(__name__)

_PENDING_KEY = "dawp.pending"

# ---------------------------------------------------------------------------
# Guard type alias
# ---------------------------------------------------------------------------

EnqueueGuard = Callable[[DawpPendingRun, dict[str, Any]], bool]
"""
``(pending_run, plugin_state) -> bool`` — return ``True`` to allow, ``False`` to block.

Reserved for D11 budget and rate-limit checks.  Pass ``None`` to the scheduler to
disable all guarding.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_pending_queue(plugin_state: dict[str, Any]) -> list[DawpPendingRun]:
    """Return (and lazily create) ``plugin_state["dawp.pending"]``."""
    if _PENDING_KEY not in plugin_state:
        plugin_state[_PENDING_KEY] = []
    return cast(list[DawpPendingRun], plugin_state[_PENDING_KEY])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def schedule_at_checkpoint(
    workflow_activations: list[tuple[str, Activation]],
    phase: Literal["pre_main_loop", "on_iteration_end"],
    plugin_state: dict[str, Any],
    *,
    assistant_text: str | None = None,
    iteration: int = 0,
    enqueue_guard: EnqueueGuard | None = None,
) -> list[DawpPendingRun]:
    """Evaluate activations at *phase* and enqueue matching runs (§6.2).

    Iterates *workflow_activations* in order (FIFO), checks each against the current
    checkpoint, and appends a :class:`~schema.DawpPendingRun` to
    ``plugin_state["dawp.pending"]`` for every match that passes *enqueue_guard*.

    Args:
        workflow_activations:
            ``[(workflow_id, Activation), ...]`` — all config-path activations for
            the current task.  A single workflow may contribute multiple activations.
        phase:
            ``"pre_main_loop"`` — fires before the main loop starts; matches
            :class:`~schema.PreMainLoopPlacement` activations.

            ``"on_iteration_end"`` — fires at the end of each main-loop iteration;
            matches :class:`~schema.OnResponseTriggerPlacement` activations whose
            ``dawp_trigger`` appears on a scannable line of *assistant_text*.
        plugin_state:
            Mutable ``AgentPluginContext.plugin_state``.  The scheduler reads/writes:

            - ``"dawp.pending"`` — FIFO queue of :class:`~schema.DawpPendingRun`
              (auto-created if absent).
            - ``"dawp.triggered.<token>"`` — trigger_once guard flags (maintained
              by :func:`~completion.matches_response_trigger`).
        assistant_text:
            Most-recent assistant response (raw; ``<thinking>`` stripped internally).
            Required for ``on_response_trigger`` matching; ignored for
            ``pre_main_loop``.  Passing ``None`` suppresses ``on_response_trigger``
            matching with a debug warning.
        iteration:
            Current main-loop iteration counter; recorded in
            :attr:`~schema.DawpPendingRun.enqueued_at_iteration` for auditing.
        enqueue_guard:
            Optional :data:`EnqueueGuard` invoked after placement matching and
            before appending.  ``False`` → run silently blocked (D11 hook point).

    Returns:
        Newly-appended :class:`~schema.DawpPendingRun` objects (empty list when no
        activation matched or all were blocked by *enqueue_guard*).

    Note:
        This function never drains the pending queue.  Draining is performed by
        HybridAgent in the ``on_iteration_end`` and ``inline`` drain paths (§6.5).
    """
    pending = _ensure_pending_queue(plugin_state)
    newly_enqueued: list[DawpPendingRun] = []

    for workflow_id, activation in workflow_activations:
        placement = activation.placement
        matched = False

        if phase == "pre_main_loop" and placement.type == "pre_main_loop":
            matched = True

        elif phase == "on_iteration_end" and placement.type == "on_response_trigger":
            if assistant_text is None:
                logger.debug(
                    "RunScheduler: on_response_trigger skipped for workflow=%r" " — no assistant_text provided",
                    workflow_id,
                )
            else:
                matched = matches_response_trigger(
                    assistant_text,
                    placement.dawp_trigger,
                    trigger_once=placement.trigger_once,
                    plugin_state=plugin_state,
                )

        if not matched:
            continue

        run = DawpPendingRun(
            trigger="config",
            workflow_source="static",
            workflow_id=workflow_id,
            enqueued_at_iteration=iteration,
            drain_mode="on_iteration_end",
            merge_back=activation.merge_back,
            config_placement=placement.type,
        )

        if enqueue_guard is not None and not enqueue_guard(run, plugin_state):
            logger.debug("RunScheduler: enqueue_guard blocked run for workflow=%r", workflow_id)
            continue

        pending.append(run)
        newly_enqueued.append(run)
        logger.debug(
            "RunScheduler: enqueued %r run for workflow=%r at iteration=%d",
            placement.type,
            workflow_id,
            iteration,
        )

    return newly_enqueued

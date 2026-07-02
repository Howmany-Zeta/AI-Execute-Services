# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
PromptChainRunner — DAWP Prompt Chain + Marker Completion state machine (§6.0).

State machine (§6.0.1):

    PromptActive  ──────────────────────────────────┐
        │  LLM+tool round; no Marker seen            │
        │                                            │
        ▼  Prompt Completion Marker detected         │ is_last + prompt_marker (mis-label)
    NextPrompt ──── more steps? ──► PromptActive ◄──┘
        │
        │  DAWP Completion Marker detected
        ▼
    DAWP run complete → restore main loop

Each step corresponds to one ``<Prompt N>`` compiled by ``document_loader`` into a
:class:`~aiecs.domain.agent.plugins.dawp.schema.DAWPStep`.

Per step, the runner:

1. Injects the step prompt as a ``user`` message (§6.0.5 format).
2. Loops, calling
   :meth:`~aiecs.domain.agent.hybrid_agent.HybridAgent._run_tool_loop_nested_streaming`
   **one iteration at a time** (``step_iteration_cap=1``).  This lets the runner
   inspect the assistant text after every LLM+tool round and detect the Marker
   early.
3. When the LLM produces a natural ``"final"`` text (``success=True`` in the
   ``result`` event), evaluates :func:`~completion.prompt_step_complete` to
   determine the next state.
4. Advances to the next step (``"prompt_done"``) or ends the run (``"dawp_done"``).
5. On step failure or budget exhaustion mid-run, exits with handoff message (§7);
   ``abort_main`` on the pending run is handled in HybridAgent drain (D3).

References: §6.0, §6.0.1, §6.0.2, §6.0.5, D3, D5.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from aiecs.llm import LLMMessage

from aiecs.domain.agent.plugins.context import AgentPluginContext
from aiecs.domain.agent.plugins.dawp.budget import TaskIterationBudget
from aiecs.domain.agent.plugins.dawp.loop_scope import LoopScope
from aiecs.domain.agent.plugins.dawp.schema import DAWPWorkflow
from aiecs.domain.agent.plugins.dawp.step_handoff import build_dawp_handoff_message

logger = logging.getLogger(__name__)

_REASON_CAP_WITHOUT_MARKER = "step iteration limit reached without the required completion marker"
_REASON_BUDGET_BEFORE_STEP = "shared task iteration budget exhausted before this step"
_REASON_BUDGET_MID_STEP = "shared task iteration budget exhausted during this step"


def _record_handoff(
    workflow: DAWPWorkflow,
    step_messages: list[LLMMessage],
    plugin_ctx: AgentPluginContext,
    *,
    failed_step_index: int,
    reason: str,
) -> str:
    """Append handoff user message and store for inject_only merge."""
    message = build_dawp_handoff_message(
        workflow,
        failed_step_index=failed_step_index,
        reason=reason,
    )
    step_messages.append(LLMMessage(role="user", content=message))
    plugin_ctx.plugin_state["dawp._handoff_message"] = message
    plugin_ctx.plugin_state["dawp._run_success"] = False
    return message


# ---------------------------------------------------------------------------
# §6.0.5 Prompt injection template
# ---------------------------------------------------------------------------

_INJECTION_TEMPLATE = "[DAWP prompt {step_index}: {step_id}]\n\n" "{action}\n\n" "{instruction}\n\n" "---\n" "Output the following line when this prompt is fully complete:\n" "{completion_marker}"


def build_step_injection(
    step_index: int,
    step_id: str,
    action: str,
    instruction: str,
    completion_marker: str,
) -> str:
    """Build the user-message injection for a DAWP step (§6.0.5).

    Args:
        step_index:         0-based index of the step (``N`` in ``<Prompt N>``).
        step_id:            Human-readable slug from ``DAWPStep.id``.
        action:             ``Contract.action`` prefix shared by all steps.
        instruction:        Step-specific body text from ``<Prompt N>``.
        completion_marker:  ``prompt_marker`` (non-last) or ``dawp_marker`` (last).

    Returns:
        Formatted injection string; should be wrapped in ``LLMMessage(role="user", ...)``.
    """
    return _INJECTION_TEMPLATE.format(
        step_index=step_index,
        step_id=step_id,
        action=action,
        instruction=instruction,
        completion_marker=completion_marker,
    )


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------


async def run_prompt_chain(
    workflow: DAWPWorkflow,
    messages: list[LLMMessage],
    context: dict[str, Any],
    plugin_ctx: AgentPluginContext,
    agent: Any,
    *,
    scope: LoopScope,
    budget: TaskIterationBudget,
    default_step_cap: int | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Drive a complete DAWP Prompt Chain run (§6.0 state machine).

    Iterates through every :class:`~schema.DAWPStep` in *workflow*, injecting each
    step prompt and running the LLM+tool mini-loop via
    :meth:`~HybridAgent._run_tool_loop_nested_streaming`.

    The function yields all streaming events produced by the nested runner,
    transparently forwarding the ``loop_scope`` already embedded by D1-04.

    Args:
        workflow:         Compiled DAWP workflow (from ``document_loader``).
        messages:         Conversation history at the point the DAWP run starts.
                          **Mutated in-place** as tool calls and tool results
                          accumulate across iterations (same semantics as the main loop).
        context:          Execution context forwarded verbatim to the LLM call.
        plugin_ctx:       Current plugin context (``plugin_state``, registry).
        agent:            :class:`~HybridAgent` instance providing the nested runner.
        scope:            Base :class:`LoopScope` for the run (``kind="dawp"``,
                          ``run_id`` and ``workflow_id`` already set by the caller).
        budget:           Shared :class:`~budget.TaskIterationBudget` (D5); each
                          LLM+tool round consumes 1 unit.
        default_step_cap: Fallback per-step iteration cap when
                          ``DAWPStep.max_iterations`` is ``None``.  ``None`` means
                          no per-step cap beyond the shared budget.

    Yields:
        All streaming events from ``_run_tool_loop_nested_streaming``, including
        ``iteration_start``, ``token``, ``tool_calls_ready``, ``tool_result``, and
        ``result`` events.  Each event already carries ``loop_scope.kind="dawp"``
        (added by D1-04).

    Note:
        ``messages`` is extended in-place by ``_process_tool_calls_batch`` inside
        the nested runner.  Callers that need a pristine copy should pass
        ``list(original_messages)`` before calling this function.
    """
    contract = workflow.spec.contract
    # Work on the caller's list; tool results are appended across steps
    step_messages = messages

    from aiecs.domain.agent.plugins.dawp.temporal_memory_context import (
        inject_temporal_memory_facts_into_messages,
    )

    step_messages = inject_temporal_memory_facts_into_messages(step_messages, plugin_ctx)

    plugin_state = plugin_ctx.plugin_state
    plugin_state["dawp._steps_completed"] = []
    plugin_state.pop("dawp._failed_step_index", None)

    from aiecs.domain.agent.plugins.dawp.step_handlers import (
        StepIterationContext,
        evaluate_step_completion,
    )
    from aiecs.domain.agent.plugins.dawp.loop_scope import (
        build_dawp_step_completed,
        build_dawp_step_started,
    )

    for step_idx, step in enumerate(workflow.steps):
        if budget.remaining == 0:
            logger.debug(
                "PromptChainRunner[%s]: budget exhausted before step %d; handoff (D3)",
                scope.run_id,
                step_idx,
            )
            _record_handoff(
                workflow,
                step_messages,
                plugin_ctx,
                failed_step_index=step_idx,
                reason=_REASON_BUDGET_BEFORE_STEP,
            )
            plugin_state["dawp._failed_step_index"] = step_idx
            return

        is_last = step_idx == len(workflow.steps) - 1
        completion_marker = contract.dawp_marker if is_last else contract.prompt_marker

        step_scope = LoopScope(
            kind="dawp",
            run_id=scope.run_id,
            workflow_id=scope.workflow_id,
            step_id=step.id,
            step_index=step_idx,
            prompt_index=step_idx,
        )

        yield build_dawp_step_started(step_scope)

        # ── §6.0.5 Inject step prompt ────────────────────────────────────
        injection = build_step_injection(
            step_index=step_idx,
            step_id=step.id,
            action=contract.action,
            instruction=step.instruction,
            completion_marker=completion_marker,
        )
        step_messages.append(LLMMessage(role="user", content=injection))
        logger.debug(
            "PromptChainRunner[%s]: injected prompt for step %d (%s)",
            scope.run_id,
            step_idx,
            step.id,
        )

        # ── Per-step iteration cap (§4.4) ────────────────────────────────
        step_cap: int | None = step.max_iterations if step.max_iterations is not None else default_step_cap
        step_consumed = 0
        step_advanced = False  # True when this step produced a valid Marker

        from aiecs.domain.agent.plugins.dawp.metrics import get_dawp_metrics, metrics_labels_from_plugin_state

        step_labels = metrics_labels_from_plugin_state(plugin_ctx.plugin_state)
        metrics = get_dawp_metrics()

        # ── PromptActive inner loop ──────────────────────────────────────
        with metrics.observe_step_duration(
            workflow_id=step_labels["workflow_id"],
            trigger=step_labels["trigger"],  # type: ignore[arg-type]
            workflow_source=step_labels["workflow_source"],  # type: ignore[arg-type]
        ):
            while budget.remaining > 0 and not step_advanced:
                if step_cap is not None and step_consumed >= step_cap:
                    logger.debug(
                        "PromptChainRunner[%s]: step %d cap (%d) exhausted without Marker",
                        scope.run_id,
                        step_idx,
                        step_cap,
                    )
                    break

                result_output: str | None = None
                result_success: bool | None = None
                had_tool_calls = False

                # Run exactly one LLM+tool iteration via the nested streaming runner.
                # ``step_iteration_cap=1`` ensures we get control back after each round
                # so we can evaluate the Marker without waiting for the full step.
                async for event in agent._run_tool_loop_nested_streaming(
                    step_messages,
                    context,
                    plugin_ctx,
                    scope=step_scope,
                    budget=budget,
                    step_iteration_cap=1,
                ):
                    yield event
                    if event.get("type") in ("tool_calls_ready", "tool_result"):
                        had_tool_calls = True
                    if event.get("type") == "result":
                        result_output = event.get("output")
                        result_success = event.get("success", True)

                step_consumed += 1

                # Budget exhausted → D3: abort this run (main loop continues)
                if budget.is_exhausted:
                    logger.debug(
                        "PromptChainRunner[%s]: budget exhausted during step %d (D3)",
                        scope.run_id,
                        step_idx,
                    )
                    yield build_dawp_step_completed(step_scope, success=False)
                    _record_handoff(
                        workflow,
                        step_messages,
                        plugin_ctx,
                        failed_step_index=step_idx,
                        reason=_REASON_BUDGET_MID_STEP,
                    )
                    plugin_state["dawp._failed_step_index"] = step_idx
                    return

                if result_success:
                    completion = evaluate_step_completion(
                        StepIterationContext(
                            assistant_text=result_output or "",
                            is_last=is_last,
                            had_tool_calls=had_tool_calls,
                            result_success=True,
                            completion=step.completion,
                        )
                    )
                    logger.debug(
                        "PromptChainRunner[%s]: step %d result=%r",
                        scope.run_id,
                        step_idx,
                        completion,
                    )

                    if completion == "dawp_done":
                        yield build_dawp_step_completed(step_scope, success=True)
                        plugin_ctx.plugin_state["dawp._run_success"] = True
                        return

                    if completion == "prompt_done":
                        step_advanced = True

                    # "continue" → either:
                    #   - No Marker seen yet → another iteration of this step
                    #   - Last step mis-labelled with prompt_marker (§6.0.2 末步规则)

        if step_advanced:
            plugin_state.setdefault("dawp._steps_completed", []).append(step_idx)
            yield build_dawp_step_completed(step_scope, success=True)
            continue

        logger.debug(
            "PromptChainRunner[%s]: step %d incomplete; exiting run with handoff",
            scope.run_id,
            step_idx,
        )
        yield build_dawp_step_completed(step_scope, success=False)
        _record_handoff(
            workflow,
            step_messages,
            plugin_ctx,
            failed_step_index=step_idx,
            reason=_REASON_CAP_WITHOUT_MARKER,
        )
        plugin_state["dawp._failed_step_index"] = step_idx
        return

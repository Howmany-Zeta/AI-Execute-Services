# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
DAWP step failure handoff — standard main-loop message when a run ends incomplete (§7).

Product decision (2026-06-07): on step failure, **exit the DAWP loop** (do not continue
to later steps), append a standard user message listing incomplete step titles, and let
the main-loop LLM decide next actions.
"""

from __future__ import annotations

from aiecs.domain.agent.plugins.dawp.schema import DAWPStep, DAWPWorkflow

_HANDOFF_HEADER = "[DAWP RUN INCOMPLETE: {workflow_id}]"
_HANDOFF_BODY = (
    "The structured DAWP workflow ended before all steps completed.\n"
    "Reason: {reason}\n\n"
    "{completed_section}"
    "{incomplete_section}\n"
    "Continue in the main loop: decide whether to finish remaining work manually, "
    "retry a step, or conclude the task."
)


def step_display_title(step: DAWPStep) -> str:
    """Human-readable step label (id + first instruction line when present)."""
    headline = step.instruction.strip().split("\n", 1)[0].strip()
    if headline and headline.lower() != step.id.lower():
        if len(headline) > 120:
            headline = headline[:117] + "..."
        return f"{step.id} — {headline}"
    return step.id


def build_dawp_handoff_message(
    workflow: DAWPWorkflow,
    *,
    failed_step_index: int,
    reason: str,
) -> str:
    """Build the standard handoff message appended to main-loop messages."""
    steps = workflow.steps
    workflow_id = workflow.metadata.name

    completed_lines: list[str] = []
    for idx in range(failed_step_index):
        completed_lines.append(f"- {step_display_title(steps[idx])}")

    incomplete_lines = [f"- {step_display_title(steps[idx])}" for idx in range(failed_step_index, len(steps))]

    completed_section = ""
    if completed_lines:
        completed_section = "Completed steps:\n" + "\n".join(completed_lines) + "\n\n"

    incomplete_section = "Incomplete steps:\n" + "\n".join(incomplete_lines)

    return (
        _HANDOFF_HEADER.format(workflow_id=workflow_id)
        + "\n\n"
        + _HANDOFF_BODY.format(
            reason=reason,
            completed_section=completed_section,
            incomplete_section=incomplete_section,
        )
    )

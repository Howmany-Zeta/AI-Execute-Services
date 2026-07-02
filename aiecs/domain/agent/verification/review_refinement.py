# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
CollaborativeWorkflowEngine ``review_refinement`` template helpers (A-11).

Task/prompt builders aligned with ``REVIEW_REFINEMENT_PHASE_CONFIG`` on
:class:`~aiecs.domain.community.collaborative_workflow.CollaborativeWorkflowEngine`.
"""

from __future__ import annotations

from typing import Any, Literal, Sequence

from aiecs.domain.agent.verification.models import AcceptanceCriterion, FeedbackItem, Verdict, coerce_verdict_kind
from aiecs.domain.community.collaborative_workflow import REVIEW_REFINEMENT_PHASE_CONFIG

ReviewRole = Literal["fact", "style"]

REVIEW_REFINEMENT_TEMPLATE: dict[str, Any] = {
    "phase": "review_refinement",
    **REVIEW_REFINEMENT_PHASE_CONFIG,
}


def build_review_refinement_task(
    *,
    role: ReviewRole,
    task: dict[str, Any],
    result: dict[str, Any],
    criteria: Sequence[AcceptanceCriterion],
) -> dict[str, Any]:
    """Independent review contract for one CWE perspective — no executor FC history."""
    output = result.get("output") or result.get("final_response") or ""
    return {
        **REVIEW_REFINEMENT_TEMPLATE,
        "task_id": f"cwe_{role}_{task.get('task_id', 'unknown')}",
        "review_contract": "gvr_cwe_review_refinement_v1",
        "role": role,
        "description": task.get("description", ""),
        "criteria": [c.to_dict() for c in criteria],
        "deliverable": {
            "output": output,
            "success": result.get("success"),
        },
    }


def build_review_refinement_prompt(
    *,
    role: ReviewRole,
    task: dict[str, Any],
    result: dict[str, Any],
    criteria: Sequence[AcceptanceCriterion],
) -> str:
    """One-shot prompt for a single sequential CWE role."""
    review_task = build_review_refinement_task(role=role, task=task, result=result, criteria=criteria)
    criteria_lines = "\n".join(f"- {c.criterion_id}: {c.description}" for c in criteria) or "- (none listed)"
    focus = "factual accuracy and evidence" if role == "fact" else "clarity, tone, and presentation"
    return (
        f"[GVR CWE review_refinement — {role} perspective]\n"
        f"Focus: {focus}\n"
        f"Task: {review_task['description']}\n"
        f"Deliverable:\n{review_task['deliverable']['output']}\n\n"
        f"Acceptance criteria:\n{criteria_lines}\n\n"
        "Respond with PASS/FAIL/PARTIAL and structured gap/fix items per criterion."
    )


def review_refinement_response_to_verdict(
    review: dict[str, Any],
    *,
    role: ReviewRole,
    criteria: Sequence[AcceptanceCriterion],
) -> Verdict:
    """Map a single-role CWE payload to A-1 ``Verdict``."""
    if "passed" in review and "kind" in review:
        verdict = Verdict.from_dict(review)
        if verdict.feedback:
            verdict.feedback = f"[{role}] {verdict.feedback}"
        return verdict

    passed = bool(review.get("passed", review.get("approved", False)))
    raw_kind = str(review.get("kind", "")).upper()
    parsed_kind = coerce_verdict_kind(raw_kind)
    if parsed_kind is not None:
        kind = parsed_kind
    elif review.get("partial"):
        kind = "PARTIAL"
    else:
        kind = "PASS" if passed else "FAIL"

    feedback = str(review.get("feedback", ""))
    if feedback:
        feedback = f"[{role}] {feedback}"

    feedback_items: list[FeedbackItem] = []
    for item in review.get("feedback_items") or []:
        if isinstance(item, FeedbackItem):
            feedback_items.append(item)
        elif isinstance(item, dict):
            feedback_items.append(FeedbackItem.from_dict(item))

    failed_criteria = list(review.get("failed_criteria") or [])
    if not failed_criteria and not passed and criteria:
        failed_criteria = [c.criterion_id for c in criteria]

    return Verdict(
        passed=passed,
        kind=kind,
        score=review.get("score"),
        failed_criteria=failed_criteria,
        feedback=feedback,
        feedback_items=feedback_items,
        missing=list(review.get("missing") or []),
    )

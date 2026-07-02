# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Peer review mini-Verdict helpers (A-5)."""

from __future__ import annotations

from typing import Any, Sequence

from aiecs.domain.agent.verification.criteria import normalize_acceptance_criteria
from aiecs.domain.agent.verification.models import AcceptanceCriterion, FeedbackItem, Verdict, coerce_verdict_kind
from aiecs.domain.agent.verification.peer_review_policy_models import (
    PEER_REVIEW_HIGH_CRITERIA_FLOOR,
    PeerReviewPolicy,
)


def coerce_criteria(
    criteria: Sequence[AcceptanceCriterion | dict[str, Any]] | None,
    *,
    task: dict[str, Any] | None = None,
) -> list[AcceptanceCriterion]:
    if criteria is not None:
        out: list[AcceptanceCriterion] = []
        for item in criteria:
            if isinstance(item, AcceptanceCriterion):
                out.append(item)
            elif isinstance(item, dict):
                out.append(AcceptanceCriterion.from_dict(item))
        return out
    if task is not None:
        goal_payload = task.get("goal") or {"success_criteria": task.get("success_criteria")}
        if goal_payload:
            return normalize_acceptance_criteria(goal_payload)
    return []


def assert_peer_review_eligible(
    criteria: list[AcceptanceCriterion],
    policy: PeerReviewPolicy | None,
) -> None:
    count = len(criteria)
    if count >= PEER_REVIEW_HIGH_CRITERIA_FLOOR:
        raise ValueError(f"Goals with >={PEER_REVIEW_HIGH_CRITERIA_FLOOR} acceptance criteria MUST NOT use " "peer_review alone; use full verifier or deterministic gate path.")
    if policy is not None and policy.enabled and count > policy.max_criteria:
        raise ValueError(f"Criteria count {count} exceeds peer_review_policy.max_criteria={policy.max_criteria}")


def build_peer_review_task(
    *,
    task: dict[str, Any],
    result: dict[str, Any],
    criteria: list[AcceptanceCriterion],
) -> dict[str, Any]:
    """Independent review contract — no executor system prompt or FC history."""
    output = result.get("output") or result.get("final_response") or ""
    return {
        "description": task.get("description", ""),
        "task_id": f"peer_review_{task.get('task_id', 'unknown')}",
        "review_contract": "gvr_peer_review_v1",
        "criteria": [c.to_dict() for c in criteria],
        "deliverable": {
            "output": output,
            "success": result.get("success"),
        },
    }


def build_peer_review_fallback_prompt(
    *,
    task: dict[str, Any],
    result: dict[str, Any],
    criteria: list[AcceptanceCriterion],
) -> str:
    """One-shot review prompt for reviewers without ``review_result``."""
    output = result.get("output") or result.get("final_response") or ""
    criteria_lines = "\n".join(f"- {c.criterion_id}: {c.description}" for c in criteria) or "- (none listed)"
    return (
        "[GVR peer review — independent contract]\n"
        f"Task: {task.get('description', '')}\n"
        f"Deliverable:\n{output}\n\n"
        f"Acceptance criteria:\n{criteria_lines}\n\n"
        "Respond with PASS/FAIL/PARTIAL and structured gap/fix items per criterion."
    )


def peer_review_response_to_verdict(
    review: dict[str, Any],
    *,
    criteria: list[AcceptanceCriterion],
) -> Verdict:
    """Map legacy peer review payloads to A-1 ``Verdict`` subset."""
    if "passed" in review and "kind" in review:
        return Verdict.from_dict(review)

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

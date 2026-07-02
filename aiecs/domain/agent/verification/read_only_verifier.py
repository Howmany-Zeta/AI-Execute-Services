# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Example read-only adversarial verifier (A-1).

Uses deliverable refs and result text only — no executor system prompt or
mutable conversation access.
"""

from __future__ import annotations

import json
from typing import Any, Union

from aiecs.domain.agent.models import AgentGoal

from .models import AcceptanceCriterion, EvidenceItem, FeedbackItem, Verdict, VerdictKind, VerificationContext


class ReadOnlyAdversarialVerifier:
    """
    Deterministic read-only verifier: checks criteria keywords appear in result
    payload and declared deliverable refs are present.
    """

    kind: str = "read_only_adversarial"

    async def verify(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any]],
        result: dict[str, Any],
        criteria: list[AcceptanceCriterion],
        context: VerificationContext,
    ) -> Verdict:
        body = json.dumps(result, default=str).lower()
        failed: list[str] = []
        feedback_items: list[FeedbackItem] = []
        evidence: list[EvidenceItem] = []
        missing: list[str] = []

        for criterion in criteria:
            needle = (criterion.description or criterion.criterion_id).strip().lower()
            if not needle:
                continue
            ok = needle in body
            if not ok:
                failed.append(criterion.criterion_id)
                feedback_items.append(
                    FeedbackItem(
                        criterion_id=criterion.criterion_id,
                        gap=f"Expected content matching '{criterion.description or criterion.criterion_id}' not found in result.",
                        fix="Include required deliverable content in task result.",
                        severity="high",
                    )
                )
            evidence.append(
                EvidenceItem.model_validate(
                    {
                        "criterion_id": criterion.criterion_id,
                        "pass": ok,
                        "artifact_ref": "task_result",
                        "quote": (needle[:120] if ok else "not found")[:120],
                    }
                )
            )

        for ref in context.deliverable_refs:
            if ref.lower() not in body:
                missing.append(ref)

        passed = not failed and not missing
        kind: VerdictKind = "PASS" if passed else "FAIL"
        feedback = "Read-only verification passed." if passed else "Read-only verification found gaps."
        return Verdict(
            passed=passed,
            kind=kind,
            failed_criteria=failed,
            feedback=feedback,
            feedback_items=feedback_items,
            missing=missing,
            evidence=evidence,
        )

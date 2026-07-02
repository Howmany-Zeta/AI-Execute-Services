# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Verifier protocol and verdict merge helpers (A-1)."""

from __future__ import annotations

from typing import Any, Protocol, Union, runtime_checkable

from aiecs.domain.agent.models import AgentGoal

from .models import AcceptanceCriterion, Verdict, VerdictKind, VerificationContext


@runtime_checkable
class Verifier(Protocol):
    """LLM or deterministic verification implementation."""

    async def verify(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any]],
        result: dict[str, Any],
        criteria: list[AcceptanceCriterion],
        context: VerificationContext,
    ) -> Verdict:
        """Run verification with isolated context (no executor conversation)."""
        ...


def merge_verdicts(verdicts: list[Verdict]) -> Verdict:
    """Merge multiple verifier outputs into one Verdict."""
    if not verdicts:
        return Verdict(
            passed=True,
            kind="NA",
            feedback="No verifiers registered.",
        )
    if len(verdicts) == 1:
        return verdicts[0]

    passed = all(v.passed for v in verdicts)
    kinds = {v.kind for v in verdicts}
    kind: VerdictKind
    if "FAIL" in kinds:
        kind = "FAIL"
    elif "PARTIAL" in kinds:
        kind = "PARTIAL"
    elif kinds == {"NA"}:
        kind = "NA"
    else:
        kind = "PASS" if passed else "FAIL"

    scores = [v.score for v in verdicts if v.score is not None]
    score = sum(scores) / len(scores) if scores else None

    failed_criteria: list[str] = []
    feedback_items = []
    missing: list[str] = []
    evidence = []
    feedback_parts: list[str] = []
    for v in verdicts:
        failed_criteria.extend(v.failed_criteria)
        feedback_items.extend(v.feedback_items)
        missing.extend(v.missing)
        evidence.extend(v.evidence)
        if v.feedback:
            feedback_parts.append(v.feedback)

    return Verdict(
        passed=passed,
        kind=kind,
        score=score,
        failed_criteria=sorted(set(failed_criteria)),
        feedback=" ".join(feedback_parts).strip(),
        feedback_items=feedback_items,
        missing=sorted(set(missing)),
        evidence=evidence,
    )

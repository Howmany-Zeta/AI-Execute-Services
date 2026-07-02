# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Gate aggregate → Verdict conversion for A-2 policy consumption (A-4)."""

from __future__ import annotations

from typing import Any

from aiecs.domain.agent.verification.models import FeedbackItem, Verdict, VerdictKind

from .gate_criterion import resolve_gate_criterion_id
from .models import AggregatedGateScore, GateScore


def gate_score_to_verdict(
    gate_score: GateScore,
    *,
    gate_kind: str | None = None,
    goal: Any = None,
) -> Verdict:
    """Convert a single gate score to a Verdict subset."""
    kind: VerdictKind = "PASS" if gate_score.passed else "FAIL"
    criterion_id = resolve_gate_criterion_id(gate_kind or gate_score.kind, goal=goal)
    feedback_items = [
        FeedbackItem(
            criterion_id=criterion_id,
            gap=issue,
            fix=f"Resolve gate issue for {criterion_id}",
            severity="high" if gate_score.critical else "medium",
        )
        for issue in gate_score.issues
    ]
    return Verdict(
        passed=gate_score.passed,
        kind=kind,
        score=gate_score.score,
        failed_criteria=[criterion_id] if not gate_score.passed else [],
        feedback="; ".join(gate_score.issues) if gate_score.issues else ("Gate passed." if gate_score.passed else "Gate failed."),
        feedback_items=feedback_items,
        missing=[],
        evidence=[],
    )


def gate_aggregate_to_verdict(aggregate: AggregatedGateScore, *, goal: Any = None) -> Verdict:
    """Convert aggregated gate output to Verdict for A-2 / hook blocking."""
    kind: VerdictKind = "PASS" if aggregate.passed else "FAIL"
    feedback_items = [
        FeedbackItem(
            criterion_id=resolve_gate_criterion_id(gs.kind, goal=goal),
            gap=issue,
            fix="Address gate issue and resubmit deliverable.",
            severity="high",
        )
        for gs in aggregate.gate_scores
        for issue in gs.issues
    ]
    return Verdict(
        passed=aggregate.passed,
        kind=kind,
        score=aggregate.score,
        failed_criteria=list(aggregate.failed_criteria),
        feedback="; ".join(aggregate.issues) if aggregate.issues else ("All gates passed." if aggregate.passed else "Gate aggregate failed."),
        feedback_items=feedback_items,
        missing=[],
        evidence=[],
    )

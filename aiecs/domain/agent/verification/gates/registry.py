# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""GateRegistry — register and run deterministic gates (A-4)."""

from __future__ import annotations

import logging
from typing import Any, Iterable, Union

from aiecs.domain.agent.models import AgentGoal

from .citation_url_gate import CitationUrlGate
from .gate_criterion import resolve_gate_criterion_id
from .models import AggregatedGateScore, GateScore
from .protocol import DeterministicGate
from .spec_gate import SpecGate

logger = logging.getLogger(__name__)

BUILTIN_GATES: dict[str, DeterministicGate] = {
    "spec_gate": SpecGate(),
    "citation_gate": CitationUrlGate(),
    "citation_url_gate": CitationUrlGate(),
}

# Built-in gate ids are reference implementations for contract tests — not production validators.
REFERENCE_BUILTIN_GATE_IDS: frozenset[str] = frozenset(BUILTIN_GATES.keys())


class GateRegistry:
    """Registry of DeterministicGate implementations."""

    def __init__(self) -> None:
        self._gates: dict[str, DeterministicGate] = {}

    def register(self, gate: DeterministicGate) -> None:
        self._gates[gate.kind] = gate

    def register_by_id(self, gate_id: str) -> None:
        normalized = gate_id.strip().lower()
        if normalized not in BUILTIN_GATES:
            raise ValueError(f"Unknown deterministic gate id: {gate_id!r}. Known: {sorted(BUILTIN_GATES)}")
        self.register(BUILTIN_GATES[normalized])

    @property
    def gate_ids(self) -> list[str]:
        return list(self._gates.keys())

    def run_all(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any], None],
        result: dict[str, Any],
        work_snapshot: dict[str, Any],
        skip_threshold: float = 85.0,
    ) -> AggregatedGateScore:
        """Run all registered gates and aggregate scores (OpenDraft ≥85 pattern)."""
        if not self._gates:
            return AggregatedGateScore(score=100.0, passed=True, issues=[])

        scores: list[GateScore] = []
        all_issues: list[str] = []
        failed: list[str] = []
        for gate in self._gates.values():
            gate_score = gate.score(goal=goal, result=result, work_snapshot=work_snapshot)
            scores.append(gate_score)
            all_issues.extend(gate_score.issues)
            if not gate_score.passed or gate_score.score < skip_threshold:
                failed.append(resolve_gate_criterion_id(gate, goal=goal))

        if scores:
            aggregate_score = sum(s.score for s in scores) / len(scores)
        else:
            aggregate_score = 100.0

        critical_fail = any(s.critical and not s.passed for s in scores)
        passed = not critical_fail and aggregate_score >= skip_threshold and not failed

        return AggregatedGateScore(
            score=aggregate_score,
            gate_scores=scores,
            issues=all_issues,
            passed=passed,
            failed_criteria=failed,
        )


def is_reference_only_gate_config(gate_ids: Iterable[str] | None) -> bool:
    """True when config uses only built-in reference gates (no custom production gates)."""
    if not gate_ids:
        return False
    normalized = {str(gate_id).strip().lower() for gate_id in gate_ids}
    return bool(normalized) and normalized.issubset(REFERENCE_BUILTIN_GATE_IDS)


def build_gate_registry_from_config(gate_ids: Iterable[str] | None) -> GateRegistry:
    """Build registry from AgentConfiguration.deterministic_gates list."""
    registry = GateRegistry()
    if not gate_ids:
        return registry
    gate_id_list = [str(gate_id) for gate_id in gate_ids]
    if is_reference_only_gate_config(gate_id_list):
        logger.warning(
            "deterministic_gates uses reference-only built-ins (%s); "
            "these are heuristic contract-test gates, not production acceptance validators. "
            "Register custom DeterministicGate implementations and/or use L1 VERIFY + LLM Verifier "
            "paths before treating L2 gate pass as production GVR.",
            sorted({gid.strip().lower() for gid in gate_id_list}),
        )
    for gate_id in gate_id_list:
        registry.register_by_id(gate_id)
    return registry

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Map deterministic gate kinds to acceptance criterion ids (GVR interchange)."""

from __future__ import annotations

from typing import Any, Union

from aiecs.domain.agent.models import AgentGoal
from aiecs.domain.agent.verification.criteria import normalize_acceptance_criteria

from .protocol import DeterministicGate

# Config registry ids may alias the same gate implementation kind.
_GATE_KIND_ALIASES: dict[str, str] = {
    "citation_gate": "citation_url_gate",
}

# Host work_state.Verdict.failed_criteria expects acceptance criterion ids, not gate ids.
_GATE_DEFAULT_CRITERION_IDS: dict[str, str] = {
    "spec_gate": "criterion_spec_structure",
    "citation_url_gate": "criterion_citation_urls",
}


def normalize_gate_kind(gate_kind: str) -> str:
    normalized = gate_kind.strip().lower()
    return _GATE_KIND_ALIASES.get(normalized, normalized)


def resolve_gate_criterion_id(
    gate: Union[DeterministicGate, str],
    *,
    goal: Union[AgentGoal, dict[str, Any], None] = None,
) -> str:
    """
    Resolve the acceptance criterion id for a gate failure.

    Priority: goal criterion with matching ``kind`` → gate.criterion_id override →
    built-in default map → normalized gate kind (custom gates should bind via goal).
    """
    gate_obj: DeterministicGate | None = None
    if isinstance(gate, str):
        gate_kind = gate
    else:
        gate_obj = gate
        gate_kind = gate.kind

    normalized = normalize_gate_kind(gate_kind)
    for criterion in normalize_acceptance_criteria(goal or {}):
        if not criterion.kind:
            continue
        if normalize_gate_kind(criterion.kind) == normalized:
            return criterion.criterion_id

    override = getattr(gate_obj, "criterion_id", None) if gate_obj is not None else None
    if isinstance(override, str) and override.strip():
        return override.strip()

    return _GATE_DEFAULT_CRITERION_IDS.get(normalized, normalized)

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""SpecGate — GIVEN/WHEN/THEN structural check (A-4)."""

from __future__ import annotations

import json
import re
from typing import Any, Union

from aiecs.domain.agent.models import AgentGoal

from .models import GateScore

_GIVEN = re.compile(r"\bGIVEN\b", re.IGNORECASE)
_WHEN = re.compile(r"\bWHEN\b", re.IGNORECASE)
_THEN = re.compile(r"\bTHEN\b", re.IGNORECASE)


def _extract_text(*, result: dict[str, Any], work_snapshot: dict[str, Any]) -> str:
    for source in (work_snapshot, result):
        for key in ("text", "output", "final_response", "content", "deliverable_text"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
        deliverables = source.get("deliverables")
        if isinstance(deliverables, dict):
            for val in deliverables.values():
                if isinstance(val, str) and val.strip():
                    return val
    return json.dumps(result, default=str)


class SpecGate:
    """
    Deterministic GIVEN/WHEN/THEN acceptance structure gate (reference impl).

    **Heuristic only:** passes when the words GIVEN, WHEN, and THEN appear
    anywhere in the deliverable text (case-insensitive word boundaries).
    This is intentionally lightweight for A-4 contract tests — not a structural
    parser. False positives are possible (e.g. prose mentioning "when" in passing).

    Production GVR MUST NOT treat SpecGate pass as full acceptance; combine with
    L1 VERIFY, LLM verifiers, or host-defined strict gates.
    """

    kind: str = "spec_gate"
    criterion_id: str = "criterion_spec_structure"

    def score(
        self,
        *,
        goal: Union[AgentGoal, dict[str, Any], None],
        result: dict[str, Any],
        work_snapshot: dict[str, Any],
    ) -> GateScore:
        text = _extract_text(result=result, work_snapshot=work_snapshot)
        has_given = bool(_GIVEN.search(text))
        has_when = bool(_WHEN.search(text))
        has_then = bool(_THEN.search(text))
        present = sum([has_given, has_when, has_then])
        score = round(100.0 * present / 3.0, 1)
        issues: list[str] = []
        if not has_given:
            issues.append("Missing GIVEN section")
        if not has_when:
            issues.append("Missing WHEN section")
        if not has_then:
            issues.append("Missing THEN section")
        passed = present == 3
        return GateScore(
            kind=self.kind,
            score=score,
            issues=issues,
            passed=passed,
            critical=not passed,
        )

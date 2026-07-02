# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""CweVerifierPolicy configuration model (A-11)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

H1_DELIVERY_KINDS = frozenset({"report", "analysis"})
H1_MIN_CRITERIA = 5


class CweVerifierPolicy(BaseModel):
    """Engine-level CWE multi-perspective verifier (A-11). Default off preserves rc4."""

    enabled: bool = False

    model_config = ConfigDict(extra="forbid")


def resolve_cwe_verifier_policy(raw: Any) -> CweVerifierPolicy | None:
    """Coerce AgentConfiguration.cwe_verifier to CweVerifierPolicy."""
    if raw is None:
        return None
    if isinstance(raw, CweVerifierPolicy):
        return raw
    if isinstance(raw, dict):
        return CweVerifierPolicy.model_validate(raw)
    raise TypeError(f"Unsupported cwe_verifier type: {type(raw)!r}")

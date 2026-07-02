# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""PeerReviewPolicy configuration model (A-5)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Goals with this many criteria or more MUST NOT use peer_review alone (A-5).
PEER_REVIEW_HIGH_CRITERIA_FLOOR = 5


class PeerReviewPolicy(BaseModel):
    """Engine-level peer review eligibility (A-5). Default off preserves rc4."""

    enabled: bool = False
    max_criteria: int = Field(default=2, ge=0)

    model_config = ConfigDict(extra="forbid")


def resolve_peer_review_policy(raw: Any) -> PeerReviewPolicy | None:
    """Coerce AgentConfiguration.peer_review_policy to PeerReviewPolicy."""
    if raw is None:
        return None
    if isinstance(raw, PeerReviewPolicy):
        return raw
    if isinstance(raw, dict):
        return PeerReviewPolicy.model_validate(raw)
    raise TypeError(f"Unsupported peer_review_policy type: {type(raw)!r}")

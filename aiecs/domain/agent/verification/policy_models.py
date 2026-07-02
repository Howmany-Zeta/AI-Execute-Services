# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""VerificationPolicy configuration model (A-2)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class WhenToVerify(str, Enum):
    """When the engine auto-runs verification_policy."""

    ON_TASK_COMPLETED = "on_task_completed"
    ON_STOP = "on_stop"
    NEVER = "never"


DEFAULT_SKIP_THRESHOLD_BY_KIND: dict[str, float] = {
    "factual": 90.0,
    "procedural": 90.0,
    "generative": 78.0,
    "creative": 78.0,
}


def resolve_verification_policy(raw: Any) -> VerificationPolicy | None:
    """Coerce AgentConfiguration.verification_policy to VerificationPolicy."""
    if raw is None:
        return None
    if isinstance(raw, VerificationPolicy):
        return raw
    if isinstance(raw, dict):
        return VerificationPolicy.model_validate(raw)
    raise TypeError(f"Unsupported verification_policy type: {type(raw)!r}")


class VerificationPolicy(BaseModel):
    """Engine-level verify-fix loop configuration (A-2)."""

    enabled: bool = False
    when_to_verify: WhenToVerify = WhenToVerify.ON_TASK_COMPLETED
    max_refines_per_goal: int = Field(default=2, ge=0)
    skip_threshold: float = Field(default=85.0, ge=0.0, le=100.0)
    skip_threshold_by_kind: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_SKIP_THRESHOLD_BY_KIND))
    registered_verifiers: list[str] = Field(default_factory=list)
    blocking: bool = True

    model_config = ConfigDict(extra="forbid")

    def effective_skip_threshold(self, goal_kind: Optional[str]) -> float:
        if goal_kind and goal_kind in self.skip_threshold_by_kind:
            return float(self.skip_threshold_by_kind[goal_kind])
        return self.skip_threshold

    def should_run_for_trigger(self, trigger: str) -> bool:
        if not self.enabled or self.when_to_verify == WhenToVerify.NEVER:
            return False
        return bool(self.when_to_verify.value == trigger)

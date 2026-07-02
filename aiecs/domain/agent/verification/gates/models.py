# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Gate score models (A-4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GateScore(BaseModel):
    """Score from a single DeterministicGate run."""

    kind: str
    score: float = Field(ge=0.0, le=100.0)
    issues: list[str] = Field(default_factory=list)
    passed: bool = True
    critical: bool = False

    model_config = ConfigDict(extra="forbid")


class AggregatedGateScore(BaseModel):
    """Aggregate of all registered gate scores."""

    score: float = Field(ge=0.0, le=100.0)
    gate_scores: list[GateScore] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    passed: bool = True
    failed_criteria: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

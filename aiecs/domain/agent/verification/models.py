# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Structured verification models for GVR (A-1)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

VerdictKind = Literal["PASS", "FAIL", "PARTIAL", "NA"]
VerificationPhase = Literal["task_completed", "stop", "explicit"]

_VERDICT_KIND_VALUES = frozenset({"PASS", "FAIL", "PARTIAL", "NA"})


def coerce_verdict_kind(value: str) -> VerdictKind | None:
    """Parse a string into a known verdict kind, or None if unrecognized."""
    upper = value.upper()
    if upper in _VERDICT_KIND_VALUES:
        return upper  # type: ignore[return-value]
    return None


class FeedbackItem(BaseModel):
    """Structured gap/fix item for REFINE feedback."""

    criterion_id: str
    gap: str
    fix: str
    severity: str = "medium"

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FeedbackItem":
        return cls.model_validate(data)


class EvidenceItem(BaseModel):
    """Per-criterion evidence snippet."""

    criterion_id: str
    pass_: bool = Field(alias="pass")
    artifact_ref: str
    quote: str = Field(max_length=120)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("quote")
    @classmethod
    def _validate_quote_length(cls, value: str) -> str:
        if len(value) > 120:
            raise ValueError("evidence quote must be at most 120 characters")
        return value

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls.model_validate(data)


class AcceptanceCriterion(BaseModel):
    """Structured acceptance criterion for verification."""

    criterion_id: str
    description: str = ""
    kind: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AcceptanceCriterion":
        return cls.model_validate(data)


class Verdict(BaseModel):
    """Machine-readable verification result (GVR interchange type)."""

    passed: bool
    kind: VerdictKind
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    failed_criteria: list[str] = Field(default_factory=list)
    feedback: str = ""
    feedback_items: list[FeedbackItem] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Verdict":
        return cls.model_validate(data)

    @classmethod
    def json_schema(cls) -> dict[str, Any]:
        return cls.model_json_schema()


class VerificationContext(BaseModel):
    """Minimal verification packet — no executor system prompt."""

    deliverable_refs: list[str] = Field(default_factory=list)
    gate_issues: list[str] = Field(default_factory=list)
    registry_snapshot: dict[str, Any] = Field(default_factory=dict)
    goal_snapshot: dict[str, Any] = Field(default_factory=dict)
    iteration: Optional[int] = None
    phase: Optional[VerificationPhase] = None

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VerificationContext":
        return cls.model_validate(data)

"""
Unit tests for GVR verification models (A-1).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aiecs.domain.agent.verification.models import (
    AcceptanceCriterion,
    EvidenceItem,
    FeedbackItem,
    Verdict,
    VerificationContext,
)


@pytest.mark.unit
class TestVerdictRoundTrip:
    def test_fixture_example_round_trip(self) -> None:
        fixture_path = Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "gvr_verdict_v1.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        example = payload["examples"][0]
        verdict = Verdict.from_dict(example)
        assert verdict.kind == "FAIL"
        assert verdict.passed is False
        assert verdict.failed_criteria == ["criterion_spec_structure"]
        round_trip = verdict.to_dict()
        assert round_trip["passed"] == example["passed"]
        assert round_trip["kind"] == example["kind"]
        assert len(round_trip["evidence"]) == 1

    def test_to_dict_from_dict_preserves_fields(self) -> None:
        original = Verdict(
            passed=True,
            kind="PASS",
            score=95.0,
            failed_criteria=[],
            feedback="ok",
            feedback_items=[
                FeedbackItem(
                    criterion_id="c1",
                    gap="",
                    fix="",
                    severity="low",
                )
            ],
            missing=[],
            evidence=[
                EvidenceItem(
                    criterion_id="c1",
                    pass_=True,
                    artifact_ref="out.md",
                    quote="short quote",
                )
            ],
        )
        restored = Verdict.from_dict(original.to_dict())
        assert restored == original

    def test_json_schema_export(self) -> None:
        schema = Verdict.json_schema()
        assert schema["title"] == "Verdict"
        assert "passed" in schema.get("properties", {})

    def test_evidence_quote_max_length(self) -> None:
        with pytest.raises(ValueError):
            EvidenceItem(
                criterion_id="c1",
                pass_=True,
                artifact_ref="x",
                quote="x" * 121,
            )


@pytest.mark.unit
class TestVerificationContext:
    def test_minimal_context_fields(self) -> None:
        ctx = VerificationContext(
            deliverable_refs=["output.md"],
            gate_issues=["spec"],
            registry_snapshot={"registered_verifiers": ["read_only"]},
            goal_snapshot={"goal_id": "g1"},
            iteration=2,
            phase="task_completed",
        )
        data = ctx.to_dict()
        restored = VerificationContext.from_dict(data)
        assert restored.deliverable_refs == ["output.md"]
        assert restored.phase == "task_completed"

    def test_context_has_no_prompt_fields(self) -> None:
        ctx = VerificationContext()
        keys = set(ctx.model_fields.keys())
        assert "system_prompt" not in keys
        assert "conversation" not in keys

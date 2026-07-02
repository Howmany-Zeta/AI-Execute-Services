"""
Unit tests for deterministic gates (A-4).
"""

from __future__ import annotations

import pytest

from aiecs.domain.agent.verification.gates.citation_url_gate import CitationUrlGate
from aiecs.domain.agent.verification.gates.conversion import gate_aggregate_to_verdict
from aiecs.domain.agent.verification.gates.registry import (
    GateRegistry,
    build_gate_registry_from_config,
    is_reference_only_gate_config,
)
from aiecs.domain.agent.verification.gates.spec_gate import SpecGate


@pytest.mark.unit
class TestSpecGate:
    def test_pass_with_given_when_then(self) -> None:
        gate = SpecGate()
        score = gate.score(
            goal=None,
            result={"output": "GIVEN context\nWHEN action\nTHEN outcome"},
            work_snapshot={},
        )
        assert score.passed is True
        assert score.score == 100.0

    def test_fail_missing_sections(self) -> None:
        gate = SpecGate()
        score = gate.score(goal=None, result={"output": "plain summary only"}, work_snapshot={})
        assert score.passed is False
        assert score.critical is True
        assert len(score.issues) == 3

    def test_heuristic_false_positive_keywords_anywhere(self) -> None:
        """Reference impl: keywords anywhere in prose can pass — not structural validation."""
        gate = SpecGate()
        score = gate.score(
            goal=None,
            result={
                "output": "This essay mentions when we GIVEN up and THEN stopped.",
            },
            work_snapshot={},
        )
        assert score.passed is True


@pytest.mark.unit
class TestCitationUrlGate:
    def test_invalid_url_fails(self) -> None:
        gate = CitationUrlGate()
        score = gate.score(
            goal=None,
            result={"output": "See https:///bad and [link](TODO)"},
            work_snapshot={},
        )
        assert score.passed is False
        assert score.issues

    def test_valid_url_passes(self) -> None:
        gate = CitationUrlGate()
        score = gate.score(
            goal=None,
            result={"output": "Reference https://example.com/docs"},
            work_snapshot={},
        )
        assert score.passed is True

    def test_no_urls_vacuous_pass_reference_impl(self) -> None:
        """Reference impl: absence of URLs/links is not a citation failure."""
        gate = CitationUrlGate()
        score = gate.score(
            goal=None,
            result={"output": "Plain summary with no links or URLs."},
            work_snapshot={},
        )
        assert score.passed is True
        assert score.score == 100.0
        assert score.issues == []


@pytest.mark.unit
class TestReferenceGateConfig:
    def test_reference_only_gate_config_detected(self) -> None:
        assert is_reference_only_gate_config(["spec_gate"]) is True
        assert is_reference_only_gate_config(["spec_gate", "citation_gate"]) is True
        assert is_reference_only_gate_config(None) is False
        assert is_reference_only_gate_config([]) is False

    def test_build_reference_gates_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        with caplog.at_level(logging.WARNING):
            build_gate_registry_from_config(["spec_gate"])
        assert any("reference-only built-ins" in record.message for record in caplog.records)


@pytest.mark.unit
class TestGateRegistry:
    def test_build_from_config(self) -> None:
        registry = build_gate_registry_from_config(["spec_gate", "citation_gate"])
        assert set(registry.gate_ids) == {"spec_gate", "citation_url_gate"}

    def test_unknown_gate_raises(self) -> None:
        registry = GateRegistry()
        with pytest.raises(ValueError, match="Unknown deterministic gate"):
            registry.register_by_id("unknown_gate")

    def test_aggregate_skip_threshold(self) -> None:
        registry = build_gate_registry_from_config(["spec_gate"])
        aggregate = registry.run_all(
            goal=None,
            result={"output": "no structure"},
            work_snapshot={},
            skip_threshold=85.0,
        )
        assert aggregate.passed is False
        assert aggregate.score < 85.0
        assert aggregate.failed_criteria == ["criterion_spec_structure"]
        verdict = gate_aggregate_to_verdict(aggregate)
        assert verdict.passed is False
        assert verdict.kind == "FAIL"
        assert verdict.failed_criteria == ["criterion_spec_structure"]

    def test_failed_criteria_uses_goal_bound_criterion_id(self) -> None:
        from aiecs.domain.agent.models import AgentGoal
        from aiecs.domain.agent.verification.models import AcceptanceCriterion

        registry = build_gate_registry_from_config(["spec_gate"])
        goal = AgentGoal(
            description="report",
            success_criteria=[
                AcceptanceCriterion(
                    criterion_id="custom_spec_criterion",
                    description="Structured spec sections",
                    kind="spec_gate",
                )
            ],
        )
        aggregate = registry.run_all(
            goal=goal,
            result={"output": "plain summary only"},
            work_snapshot={},
            skip_threshold=85.0,
        )
        assert aggregate.failed_criteria == ["custom_spec_criterion"]

    def test_citation_gate_failure_maps_to_criterion_id(self) -> None:
        registry = build_gate_registry_from_config(["citation_gate"])
        aggregate = registry.run_all(
            goal=None,
            result={"output": "See https:///bad and [link](TODO)"},
            work_snapshot={},
            skip_threshold=85.0,
        )
        assert aggregate.failed_criteria == ["criterion_citation_urls"]

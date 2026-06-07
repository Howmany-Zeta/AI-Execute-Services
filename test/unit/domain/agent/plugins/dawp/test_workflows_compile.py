"""
D0-06 — Workflow compile integration tests.

Compiles all *.dawp.md fixtures under
  issue_report/new_function_request/agent_system_design/workflows/
and makes golden / snapshot assertions on step count, step IDs, markers,
activation fields, instruction presence, and appendix presence.

These are integration-level tests; they do NOT duplicate the unit-level
error-path coverage from test_document_loader.py (D0-03).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.dawp.document_loader import compile_file

_WORKFLOWS_DIR = (
    Path(__file__).parents[6]
    / "issue_report"
    / "new_function_request"
    / "agent_system_design"
    / "workflows"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _step_ids(wf) -> list[str]:
    return [s.id for s in wf.steps]


def _step_is_last(wf) -> list[bool]:
    return [s.completion.is_last for s in wf.steps]


# ---------------------------------------------------------------------------
# dawp-template.dawp.md
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpTemplateCompile:
    """Golden assertions for dawp-template.dawp.md (pre_main_loop template)."""

    @pytest.fixture(scope="class")
    def wf(self):
        return compile_file(_WORKFLOWS_DIR / "dawp-template.dawp.md")

    def test_metadata_name(self, wf):
        assert wf.metadata.name == "REPLACE_WORKFLOW_NAME"

    def test_metadata_trigger_hint_absent(self, wf):
        assert wf.metadata.trigger_hint is None

    def test_activation_count(self, wf):
        assert len(wf.activations) == 1

    def test_activation_placement_type(self, wf):
        assert wf.activations[0].placement.type == "pre_main_loop"

    def test_activation_max_iterations_per_prompt(self, wf):
        assert wf.activations[0].max_iterations_per_prompt == 4

    def test_activation_merge_back(self, wf):
        assert wf.activations[0].merge_back == "append"

    def test_activation_no_trigger_instruction(self, wf):
        assert wf.activations[0].trigger_instruction is None

    def test_step_count(self, wf):
        assert len(wf.steps) == 2

    def test_step_ids(self, wf):
        # Both headings are the placeholder "REPLACE_STEP_TITLE" → same slug
        assert _step_ids(wf) == ["replace-step-title", "replace-step-title"]

    def test_is_last_flags(self, wf):
        assert _step_is_last(wf) == [False, True]

    def test_contract_prompt_marker(self, wf):
        assert wf.spec.contract.prompt_marker == "<STEP_DONE>"

    def test_contract_dawp_marker(self, wf):
        assert wf.spec.contract.dawp_marker == "<DAWP_HANDOFF>"

    def test_all_steps_inherit_markers(self, wf):
        for step in wf.steps:
            assert step.completion.prompt_marker == "<STEP_DONE>"
            assert step.completion.dawp_marker == "<DAWP_HANDOFF>"

    def test_instruction_non_empty(self, wf):
        assert wf.spec.instruction.strip() != ""

    def test_appendix_non_empty(self, wf):
        assert wf.spec.appendix.strip() != ""


# ---------------------------------------------------------------------------
# dawp-example.dawp.md
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDawpExampleCompile:
    """Golden assertions for dawp-example.dawp.md (8-step first-principles analysis)."""

    @pytest.fixture(scope="class")
    def wf(self):
        return compile_file(_WORKFLOWS_DIR / "dawp-example.dawp.md")

    def test_metadata_name(self, wf):
        assert wf.metadata.name == "First Principles Intent Analysis"

    def test_metadata_trigger_hint(self, wf):
        assert wf.metadata.trigger_hint == "First user request in a task; before main execution loop"

    def test_activation_count(self, wf):
        assert len(wf.activations) == 1

    def test_activation_placement_type(self, wf):
        assert wf.activations[0].placement.type == "pre_main_loop"

    def test_activation_max_iterations_per_prompt(self, wf):
        assert wf.activations[0].max_iterations_per_prompt == 4

    def test_activation_merge_back(self, wf):
        assert wf.activations[0].merge_back == "append"

    def test_activation_no_trigger_instruction(self, wf):
        assert wf.activations[0].trigger_instruction is None

    def test_step_count(self, wf):
        # Prompts 0–7 inclusive
        assert len(wf.steps) == 8

    def test_step_ids_golden(self, wf):
        expected = [
            "fundamental-question-beneath-the-surface-request",
            "deconstruct-to-first-principles",
            "non-obvious-angles",
            "core-objective-and-scope",
            "expectations-and-constraints",
            "knowledge-domains",
            "methodology-selection",
            "execution-mode-and-handoff",
        ]
        assert _step_ids(wf) == expected

    def test_is_last_flags(self, wf):
        # Only the final step is last
        flags = _step_is_last(wf)
        assert flags == [False] * 7 + [True]

    def test_contract_prompt_marker(self, wf):
        assert wf.spec.contract.prompt_marker == "<STEP_DONE>"

    def test_contract_dawp_marker(self, wf):
        assert wf.spec.contract.dawp_marker == "<DAWP_HANDOFF>"

    def test_all_steps_inherit_markers(self, wf):
        for step in wf.steps:
            assert step.completion.prompt_marker == "<STEP_DONE>"
            assert step.completion.dawp_marker == "<DAWP_HANDOFF>"

    def test_instruction_mentions_first_principles(self, wf):
        assert "first-principles" in wf.spec.instruction.lower() or "first principles" in wf.spec.instruction.lower()

    def test_appendix_contains_node_table(self, wf):
        assert "Node" in wf.spec.appendix
        assert "Maps to" in wf.spec.appendix

    def test_first_step_instruction_contains_surface_request(self, wf):
        assert "surface request" in wf.steps[0].instruction.lower()

    def test_last_step_instruction_mentions_handoff(self, wf):
        assert "handoff" in wf.steps[-1].instruction.lower() or "Handoff" in wf.steps[-1].instruction


# ---------------------------------------------------------------------------
# ooda.dawp.md
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOodaCompile:
    """Golden assertions for ooda.dawp.md (6-step OODA review cycle, on_response_trigger)."""

    @pytest.fixture(scope="class")
    def wf(self):
        return compile_file(_WORKFLOWS_DIR / "ooda.dawp.md")

    def test_metadata_name(self, wf):
        assert wf.metadata.name == "OODA Strategic Research Cycle"

    def test_metadata_trigger_hint(self, wf):
        hint = wf.metadata.trigger_hint
        assert hint is not None
        assert "OODA" in hint or "observation" in hint.lower() or "cycles" in hint.lower()

    def test_activation_count(self, wf):
        assert len(wf.activations) == 1

    def test_activation_placement_type(self, wf):
        assert wf.activations[0].placement.type == "on_response_trigger"

    def test_activation_dawp_trigger(self, wf):
        assert wf.activations[0].placement.dawp_trigger == "<START_OODA_REVIEW>"  # type: ignore[union-attr]

    def test_activation_trigger_once(self, wf):
        assert wf.activations[0].placement.trigger_once is True  # type: ignore[union-attr]

    def test_activation_max_iterations_per_prompt(self, wf):
        assert wf.activations[0].max_iterations_per_prompt == 6

    def test_activation_merge_back(self, wf):
        assert wf.activations[0].merge_back == "append"

    def test_activation_trigger_instruction_present(self, wf):
        ti = wf.activations[0].trigger_instruction
        assert ti is not None
        assert "<START_OODA_REVIEW>" in ti

    def test_step_count(self, wf):
        # Prompts 0–5 inclusive
        assert len(wf.steps) == 6

    def test_step_ids_golden(self, wf):
        expected = [
            "first-principles-intent-analysis-cycle-1",
            "assess-complexity-and-select-execution-mode",
            "task-decomposition-if-full-ooda",
            "tactical-execution-discipline",
            "bootstrap-ooda-documents-first-cycle-only",
            "ooda-strategic-review-cycle",
        ]
        assert _step_ids(wf) == expected

    def test_is_last_flags(self, wf):
        flags = _step_is_last(wf)
        assert flags == [False] * 5 + [True]

    def test_contract_prompt_marker(self, wf):
        assert wf.spec.contract.prompt_marker == "<OODA_STEP_DONE>"

    def test_contract_dawp_marker(self, wf):
        assert wf.spec.contract.dawp_marker == "<OODA_REVIEW_COMPLETE>"

    def test_all_steps_inherit_markers(self, wf):
        for step in wf.steps:
            assert step.completion.prompt_marker == "<OODA_STEP_DONE>"
            assert step.completion.dawp_marker == "<OODA_REVIEW_COMPLETE>"

    def test_instruction_mentions_ooda(self, wf):
        assert "OODA" in wf.spec.instruction

    def test_appendix_contains_phase_table(self, wf):
        # Appendix has a table mapping Prompt → Phase
        assert "Phase" in wf.spec.appendix
        assert "Bootstrap" in wf.spec.appendix or "Intent" in wf.spec.appendix

    def test_step_4_bootstrap_mentions_research_track(self, wf):
        assert "Research Track" in wf.steps[4].instruction

    def test_step_5_ooda_review_mentions_observe(self, wf):
        assert "Observe" in wf.steps[5].instruction


# ---------------------------------------------------------------------------
# Parametrised: all workflow files must compile without error
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "filename",
    [
        "dawp-template.dawp.md",
        "dawp-example.dawp.md",
        "ooda.dawp.md",
    ],
)
def test_all_workflows_compile_without_error(filename: str) -> None:
    """Every *.dawp.md fixture in the workflows directory must compile cleanly."""
    path = _WORKFLOWS_DIR / filename
    wf = compile_file(path)
    assert wf.metadata.name, f"{filename}: metadata.name must be non-empty"
    assert len(wf.activations) >= 1, f"{filename}: must have at least one activation"

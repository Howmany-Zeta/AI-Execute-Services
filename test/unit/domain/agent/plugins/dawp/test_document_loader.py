"""
Unit tests for aiecs/domain/agent/plugins/dawp/document_loader.py (D0-03).

Covers:
- Standard and comment-wrapped front matter formats
- Metadata normalisation (name, trigger_hint, placement, scheduling fields)
- Rejected placements (after_response_index, on_tool_result_trigger) with line numbers
- Contract grammar: Action + Prompt / DAWP Completion Markers
- Missing / malformed markers → DawpDocumentError
- Same markers → DawpDocumentError (Contract validation)
- <Prompt N> steps: count, order, id slug, is_last flag
- Nested markdown fence inside a Prompt block (parsing robustness)
- ## Appendix is not a step
- Compile real fixture files: dawp-template, dawp-example, ooda
- dynamic_workflow_limits parameter is accepted without error
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aiecs.domain.agent.plugins.dawp.document_loader import compile, compile_file
from aiecs.domain.agent.plugins.dawp.schema import DawpDocumentError

# Path to the author workflow fixtures (workspace root is 7 levels up from this file)
_WORKFLOWS_DIR = Path(__file__).parents[6] / "issue_report" / "new_function_request" / "agent_system_design" / "workflows"

# ---------------------------------------------------------------------------
# Minimal valid document helpers
# ---------------------------------------------------------------------------

_MINIMAL_STD = """\
---
name: test-wf
placement: pre_main_loop
---

## Contract

### Action

Do work.

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

## Prompt

<Prompt 0>
### First step

Do something.
</Prompt 0>
"""

_MINIMAL_COMMENT_WRAPPED = """\
<!-- Metadata Start-->
---
name: comment-wf
placement: pre_main_loop
---
<!-- Metadata End-->

## Contract

### Action

Act.

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

## Prompt

<Prompt 0>
### Only step
Content.
</Prompt 0>
"""


# ---------------------------------------------------------------------------
# Front matter parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFrontMatter:
    def test_standard_front_matter(self):
        wf = compile(_MINIMAL_STD)
        assert wf.metadata.name == "test-wf"

    def test_comment_wrapped_front_matter(self):
        wf = compile(_MINIMAL_COMMENT_WRAPPED)
        assert wf.metadata.name == "comment-wf"

    def test_name_required(self):
        src = "---\nplacement: pre_main_loop\n---\n\n## Contract\n\n### Prompt Completion Marker: `<S>`\n\n### DAWP Completion Marker: `<D>`\n"
        with pytest.raises(DawpDocumentError, match="missing 'name'"):
            compile(src)

    def test_trigger_hint_from_trigger_field(self):
        src = """\
---
name: wf
placement: pre_main_loop
trigger: Run on first request
---

## Contract

### Action

x

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        assert wf.metadata.trigger_hint == "Run on first request"

    def test_missing_placement_defaults_to_pre_main_loop(self):
        src = """\
---
name: wf
---

## Contract

### Action

x

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        assert wf.activations[0].placement.type == "pre_main_loop"

    def test_on_response_trigger_with_dawp_trigger(self):
        src = """\
---
name: wf
placement: on_response_trigger
dawp_trigger: <START_WF>
trigger_once: true
---

## Contract

### Action

x

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        act = wf.activations[0]
        assert act.placement.type == "on_response_trigger"
        assert act.placement.dawp_trigger == "<START_WF>"  # type: ignore[union-attr]
        assert act.placement.trigger_once is True  # type: ignore[union-attr]

    def test_on_response_trigger_missing_dawp_trigger(self):
        src = """\
---
name: wf
placement: on_response_trigger
---

## Contract

### Prompt Completion Marker: `<S>`

### DAWP Completion Marker: `<D>`
"""
        with pytest.raises(DawpDocumentError, match="dawp_trigger"):
            compile(src)

    def test_scheduling_fields_parsed(self):
        src = """\
---
name: wf
placement: pre_main_loop
max_iterations_per_prompt: 4
merge_back: inject_only
trigger_instruction: "Output <X> when ready."
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        act = wf.activations[0]
        assert act.max_iterations_per_prompt == 4
        assert act.merge_back == "inject_only"
        assert "Output <X>" in (act.trigger_instruction or "")


# ---------------------------------------------------------------------------
# Rejected placements (v2.3+)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRejectedPlacements:
    def _src_with_placement(self, placement: str) -> str:
        return (
            f"---\nname: wf\nplacement: {placement}\n---\n\n"
            "## Contract\n\n### Prompt Completion Marker: `<S>`\n\n### DAWP Completion Marker: `<D>`\n"
        )

    def test_after_response_index_rejected(self):
        src = self._src_with_placement("after_response_index")
        with pytest.raises(DawpDocumentError, match="after_response_index"):
            compile(src)

    def test_after_response_index_includes_line_number(self):
        src = self._src_with_placement("after_response_index")
        try:
            compile(src, path="test.dawp.md")
        except DawpDocumentError as exc:
            assert exc.line is not None, "line number must be set"
            assert exc.path == "test.dawp.md"
        else:
            pytest.fail("DawpDocumentError not raised")

    def test_on_tool_result_trigger_rejected(self):
        src = self._src_with_placement("on_tool_result_trigger")
        with pytest.raises(DawpDocumentError, match="on_tool_result_trigger"):
            compile(src)

    def test_unknown_placement_rejected(self):
        src = self._src_with_placement("runtime")
        with pytest.raises(DawpDocumentError, match="unknown placement"):
            compile(src)


# ---------------------------------------------------------------------------
# Contract parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContractParsing:
    def test_extracts_markers(self):
        wf = compile(_MINIMAL_STD)
        assert wf.spec.contract.prompt_marker == "<STEP_DONE>"
        assert wf.spec.contract.dawp_marker == "<DAWP_HANDOFF>"

    def test_extracts_action_text(self):
        src = """\
---
name: wf
---

## Contract

### Action

Do work step by step.
Check each result carefully.

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        assert "Do work step by step" in wf.spec.contract.action
        assert "Check each result" in wf.spec.contract.action

    def test_missing_contract_section(self):
        src = "---\nname: wf\n---\n\n## Prompt\n\n<Prompt 0>\nHello\n</Prompt 0>\n"
        with pytest.raises(DawpDocumentError, match="Contract"):
            compile(src)

    def test_missing_prompt_completion_marker(self):
        src = """\
---
name: wf
---

## Contract

### Action

x

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        with pytest.raises(DawpDocumentError, match="Prompt Completion Marker"):
            compile(src)

    def test_missing_dawp_completion_marker(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`
"""
        with pytest.raises(DawpDocumentError, match="DAWP Completion Marker"):
            compile(src)

    def test_same_markers_rejected(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<SAME>`

### DAWP Completion Marker: `<SAME>`
"""
        with pytest.raises(DawpDocumentError, match="must differ"):
            compile(src)

    def test_invalid_marker_format_rejected(self):
        """Lowercase token in marker heading raises DawpDocumentError."""
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<step_done>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        with pytest.raises(DawpDocumentError):
            compile(src)

    def test_marker_token_missing_backticks(self):
        """Token not in backticks cannot be found → DawpDocumentError."""
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: <STEP_DONE>

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        with pytest.raises(DawpDocumentError, match="backticks"):
            compile(src)


# ---------------------------------------------------------------------------
# Prompt step parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStepParsing:
    def test_single_step_is_last(self):
        wf = compile(_MINIMAL_STD)
        assert len(wf.steps) == 1
        assert wf.steps[0].completion.is_last is True

    def test_step_id_from_heading_slug(self):
        wf = compile(_MINIMAL_STD)
        assert wf.steps[0].id == "first-step"

    def test_step_fallback_id_when_no_heading(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

<Prompt 0>
No heading here, just text.
</Prompt 0>
"""
        wf = compile(src)
        assert wf.steps[0].id == "prompt-0"

    def test_multiple_steps_order_and_is_last(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

<Prompt 0>
### Alpha

First.
</Prompt 0>

<Prompt 1>
### Beta

Second.
</Prompt 1>

<Prompt 2>
### Gamma

Third.
</Prompt 2>
"""
        wf = compile(src)
        assert len(wf.steps) == 3
        assert wf.steps[0].id == "alpha"
        assert wf.steps[0].completion.is_last is False
        assert wf.steps[1].id == "beta"
        assert wf.steps[1].completion.is_last is False
        assert wf.steps[2].id == "gamma"
        assert wf.steps[2].completion.is_last is True

    def test_steps_inherit_contract_markers(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<OODA_STEP_DONE>`

### DAWP Completion Marker: `<OODA_COMPLETE>`

<Prompt 0>
### Step A
x
</Prompt 0>

<Prompt 1>
### Step B
y
</Prompt 1>
"""
        wf = compile(src)
        for step in wf.steps:
            assert step.completion.prompt_marker == "<OODA_STEP_DONE>"
            assert step.completion.dawp_marker == "<OODA_COMPLETE>"

    def test_zero_steps_allowed(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        assert wf.steps == []

    def test_nested_markdown_fence_inside_prompt(self):
        """Fenced code blocks inside a <Prompt N> block must not break parsing."""
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

<Prompt 0>
### With fence

Use this code:

```python
x = 1
y = 2
```

And this table:

| col | val |
|-----|-----|
| a   | 1   |

End with `<STEP_DONE>`.
</Prompt 0>

<Prompt 1>
### After fence

Follow up.
</Prompt 1>
"""
        wf = compile(src)
        assert len(wf.steps) == 2
        assert "```python" in wf.steps[0].instruction
        assert wf.steps[1].completion.is_last is True

    def test_prompt_numbers_are_sorted(self):
        """Steps appear in prompt number order even if written out of order in the file."""
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

<Prompt 2>
### Third
C
</Prompt 2>

<Prompt 0>
### First
A
</Prompt 0>

<Prompt 1>
### Second
B
</Prompt 1>
"""
        wf = compile(src)
        assert [s.id for s in wf.steps] == ["first", "second", "third"]


# ---------------------------------------------------------------------------
# Instruction and Appendix
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInstructionAndAppendix:
    def test_instruction_extracted(self):
        src = """\
---
name: wf
---

## Instruction:

**Background:** test background.

**Objective:** Do the thing.

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`
"""
        wf = compile(src)
        assert "test background" in wf.spec.instruction
        assert "Do the thing" in wf.spec.instruction

    def test_appendix_not_a_step(self):
        src = """\
---
name: wf
---

## Contract

### Prompt Completion Marker: `<STEP_DONE>`

### DAWP Completion Marker: `<DAWP_HANDOFF>`

<Prompt 0>
### Step
x
</Prompt 0>

## Appendix

| Node | Maps to |
|------|---------|
| 0    | Phase 1 |
"""
        wf = compile(src)
        assert len(wf.steps) == 1
        assert "Node" in wf.spec.appendix
        assert "Phase 1" in wf.spec.appendix

    def test_missing_appendix_yields_empty_string(self):
        wf = compile(_MINIMAL_STD)
        assert wf.spec.appendix == ""


# ---------------------------------------------------------------------------
# dynamic_workflow_limits hook
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDynamicLimitsHook:
    def test_limits_accepted_without_error(self):
        limits = {
            "max_prompts": 12,
            "max_iterations_per_prompt": 6,
            "max_contract_action_chars": 8000,
            "max_document_bytes": 256_000,
            "require_remaining_budget": 3,
        }
        wf = compile(_MINIMAL_STD, dynamic_workflow_limits=limits)
        assert wf.metadata.name == "test-wf"

    def test_none_limits_accepted(self):
        wf = compile(_MINIMAL_STD, dynamic_workflow_limits=None)
        assert wf.metadata.name == "test-wf"


# ---------------------------------------------------------------------------
# Compile real fixture files
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFixtureFiles:
    def test_compile_dawp_template(self):
        path = _WORKFLOWS_DIR / "dawp-template.dawp.md"
        wf = compile_file(path)
        assert wf.metadata.name == "REPLACE_WORKFLOW_NAME"
        assert wf.activations[0].placement.type == "pre_main_loop"
        assert len(wf.steps) == 2
        assert wf.steps[-1].completion.is_last is True
        assert wf.spec.contract.prompt_marker == "<STEP_DONE>"
        assert wf.spec.contract.dawp_marker == "<DAWP_HANDOFF>"

    def test_compile_dawp_example(self):
        path = _WORKFLOWS_DIR / "dawp-example.dawp.md"
        wf = compile_file(path)
        assert wf.metadata.name == "First Principles Intent Analysis"
        assert wf.activations[0].placement.type == "pre_main_loop"
        # 8 prompts (0–7)
        assert len(wf.steps) == 8
        assert wf.steps[0].completion.is_last is False
        assert wf.steps[-1].completion.is_last is True
        assert wf.spec.contract.prompt_marker == "<STEP_DONE>"
        assert wf.spec.contract.dawp_marker == "<DAWP_HANDOFF>"
        assert wf.spec.appendix != ""

    def test_compile_ooda(self):
        path = _WORKFLOWS_DIR / "ooda.dawp.md"
        wf = compile_file(path)
        assert wf.metadata.name == "OODA Strategic Research Cycle"
        act = wf.activations[0]
        assert act.placement.type == "on_response_trigger"
        assert act.placement.dawp_trigger == "<START_OODA_REVIEW>"  # type: ignore[union-attr]
        assert act.placement.trigger_once is True  # type: ignore[union-attr]
        # 6 prompts (0–5)
        assert len(wf.steps) == 6
        assert wf.steps[-1].completion.is_last is True
        assert wf.spec.contract.prompt_marker == "<OODA_STEP_DONE>"
        assert wf.spec.contract.dawp_marker == "<OODA_REVIEW_COMPLETE>"
        # trigger_instruction should be populated
        assert act.trigger_instruction is not None
        assert "<START_OODA_REVIEW>" in act.trigger_instruction

    def test_compile_file_error_path_included(self):
        """compile_file propagates path to DawpDocumentError."""
        import tempfile, os

        bad_src = "---\nname: wf\n---\n\n## Contract\n\n### Prompt Completion Marker: `<S>`\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dawp.md", delete=False, encoding="utf-8"
        ) as f:
            f.write(bad_src)
            tmp_path = f.name
        try:
            with pytest.raises(DawpDocumentError) as exc_info:
                compile_file(tmp_path)
            assert exc_info.value.path == tmp_path
        finally:
            os.unlink(tmp_path)

---
name: trigger-inline
placement: on_response_trigger
dawp_trigger: <START_INLINE_REVIEW>
trigger_instruction: |
  When the analysis phase is complete, output this line alone (not inside code blocks):
  <START_INLINE_REVIEW>
trigger_once: true
max_iterations_per_prompt: 4
merge_back: append
---

## Instruction:

**Background:** Mid-loop inline review workflow for testing on_response_trigger detection.

**Purpose:** Verify that the trigger token activates DAWP only when it appears on a scannable line (§6.0.2.2).

**Timing:** Activated when the main agent outputs `<START_INLINE_REVIEW>` on a standalone line (not inside ``` code blocks or > blockquotes).

**Objective:** Complete a 2-step review and return control to the main loop.

---

## Contract

### Action

Perform a structured inline review. Follow each prompt instruction precisely.

### Prompt Completion Marker: `<INLINE_STEP_DONE>`

### DAWP Completion Marker: `<INLINE_REVIEW_COMPLETE>`

---

## Prompt

<Prompt 0>
### Gather Evidence

Review the available information and summarize key findings. Be concise.

</Prompt 0>

<Prompt 1>
### Synthesise

Based on the gathered evidence, provide a final synthesis and recommendation.

</Prompt 1>

---

## Appendix

This workflow is used exclusively in automated tests. Do not use in production.

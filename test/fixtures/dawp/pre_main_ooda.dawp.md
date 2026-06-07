---
name: pre-main-ooda
placement: pre_main_loop
max_iterations_per_prompt: 6
merge_back: append
---

## Instruction:

**Background:** OODA-style pre_main_loop workflow used in D1-13 integration tests.

**Purpose:** Verify custom contract markers and pre_main_loop execution.

**Timing:** Runs once before the main agent loop starts.

**Objective:** Complete a 2-step OODA review using custom markers, then hand off to the main loop.

---

## Contract

### Action

Analyse the situation using the OODA cycle. Follow each prompt precisely.

### Prompt Completion Marker: `<OODA_STEP_DONE>`

### DAWP Completion Marker: `<OODA_HANDOFF>`

---

## Prompt

<Prompt 0>
### Observe and Orient

Gather observations and orient them into a coherent picture.

</Prompt 0>

<Prompt 1>
### Decide and Act

Based on orientation, decide and describe the action to take.

</Prompt 1>

---

## Appendix

Used exclusively in D1-13 automated integration tests.

# GVR deterministic gate semantics (A-4)

## Aggregate score and skip_threshold

Deterministic gates produce individual `GateScore` values (`score` 0..100, `passed`, `issues`, `critical`).

`GateRegistry.run_all()` aggregates with the **OpenDraft ≥85 pattern**:

| Rule | Behavior |
|------|----------|
| **Aggregate score** | Arithmetic mean of registered gate scores |
| **Default threshold** | `AgentConfiguration.gvr_gate_skip_threshold` (default **85.0**) |
| **Pass** | Aggregate ≥ threshold **and** no critical gate failure **and** no gate below threshold |
| **Fail** | Any critical gate fails, or aggregate < threshold |

Failed acceptance criterion ids are listed in `AggregatedGateScore.failed_criteria` (mapped from gate kinds via `resolve_gate_criterion_id`; built-in defaults: `spec_gate` → `criterion_spec_structure`, `citation_url_gate` / `citation_gate` → `criterion_citation_urls`). Goal criteria with matching ``kind`` override defaults for REFINE/EXPAND mapping.

## Gate → Verdict conversion

Use `gate_aggregate_to_verdict(aggregate)` for A-2 `verification_policy` and A-8 hook blocking feedback.

## Built-in gates

| Config id | Class | Checks |
|-----------|-------|--------|
| `spec_gate` | `SpecGate` | **Heuristic:** word-boundary match for GIVEN / WHEN / THEN anywhere in text |
| `citation_gate`, `citation_url_gate` | `CitationUrlGate` | URL format + dangling markdown links |

### Reference implementation limits (A-4)

Built-in gates are **deterministic reference implementations** for L2 pre-exit and
contract tests. They are **not production-grade acceptance validators**. Do not
enable `deterministic_gates: [spec_gate, citation_gate]` alone and treat L2 pass
as full GVR acceptance — that is a common misconfiguration.

| Gate | Limitation |
|------|------------|
| `SpecGate` | Keyword presence only — no section structure, ordering, or semantic validation. Text like `"when discussing GIVEN assumptions..."` can false-pass. |
| `CitationUrlGate` | URL shape + dangling `[text](url)` heuristics only. **No URLs and no markdown links → vacuous pass (score 100).** Does not require citations to exist. |

**Production GVR:** register custom `DeterministicGate` implementations or sink to
host L1 VERIFY / LLM `Verifier` paths. L2 gate pass does not replace L1 VERIFY (B1).

`build_gate_registry_from_config()` logs a **warning** when `deterministic_gates`
contains only built-in reference ids.

## Configuration

```yaml
deterministic_gates: [spec_gate, citation_gate]
gvr_gate_skip_threshold: 85
```

When `deterministic_gates` is null/empty, registry is empty and rc4 behavior is preserved.

## L2 vs L1 VERIFY (B1 strategy)

**L2 gate pre-check pass does NOT skip host L1 VERIFY.** python-middleware MUST still run L1 VERIFY phase after L2 pre-exit passes.

## Coexistence with HookPlugin (A-8)

Pre-exit order inside tool loop:

1. **`verification_policy` (A-2)** when `enabled=true` and `when_to_verify` matches the checkpoint (`on_task_completed` pre-exit or `on_stop` STOP hook path)
2. **A-8 fallback** when policy is disabled or the checkpoint trigger does not match `when_to_verify`:
   - **`on_task_completed`:** gates (if configured) + in-loop `TASK_COMPLETED` hook
   - **`on_stop`:** gates only (if configured) — STOP hook runs afterward via `dispatch_stop_hook_for_outcome`
3. Dispatch in-loop `TASK_COMPLETED` hook with enriched payload (`goal_id`, `gate_scores`, `failed_criteria`) — **task_completed path only**
4. Gate fail → inject data-only user message → continue FC loop
5. Hook `action=block` → same refine path (merged with gate feedback when both block)
6. If not blocked → existing STOP hook (H6) may still request `preventContinuation`

**HybridAgent default:** final / `stop_match` outcomes call pre-exit with
`trigger=on_task_completed` before the STOP hook. Gate-only hosts that disable
`verification_policy` still get SpecGate pre-check on that path; `on_stop` A-8
gate fallback covers direct `run_gvr_pre_exit(..., trigger="on_stop")` callers
and the STOP hook path when policy is off.

**Priority:** `verification_policy` > HookPlugin blocking > default complete.

**Dedupe:** Policy runner records checkpoints as `{goal_id}:{iteration}:{trigger}` in `plugin_state["gvr.verified_checkpoints"]` to avoid double-verify on the same iteration.

L2 deterministic gates share a trigger-independent checkpoint `{goal_id}:{iteration}:gates` in `plugin_state["gvr.gate_checkpoints"]`. After gates run on `on_task_completed` (policy or A-8), the `on_stop` A-8 fallback skips re-evaluation for the same iteration — preventing double SpecGate/Citation runs and a second gate blocking message when the task_completed path already passed.

Hook-only path: set `enable_gvr_pre_exit_hooks: true` in task context or register `TASK_COMPLETED` hooks without enabling gates.

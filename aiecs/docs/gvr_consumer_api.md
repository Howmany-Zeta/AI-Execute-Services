# GVR Consumer API (MasterController / python-middleware)

**Version baseline:** aiecs `2.1.0rc4` → GA  
**Contract test:** `tests/contract/test_aiecs_gvr_surface.py`  
**Verdict fixture:** `tests/fixtures/gvr_verdict_v1.json` (co-owned with python-middleware `work_state.Verdict`)  
**Field mapping:** [gvr_verdict_field_mapping.md](./gvr_verdict_field_mapping.md)

This document lists the **stable GVR-facing API surface** for python-middleware MasterController integration. Symbols marked **(baseline)** exist in 2.1.0rc4. Symbols marked **(GA target)** ship in the `add-gvr-agentic-loop-primitives` change train.

---

## Semver policy

| Bump | Rule |
|------|------|
| **Patch** | Bug fixes only; no contract-test signature changes |
| **Minor** | Additive only — new symbols, new optional config keys, new enum values; existing GVR contract symbols remain backward compatible |
| **Major** | Breaking changes to contract-test-covered symbols; requires explicit breaking-change review (see below) and ≥1 release consumer follow-up window before removal |

**Consumer pinning:** python-middleware MAY pin `aiecs==X.Y.Z`. Contract test failure on a new rc **blocks adoption** of new primitives but does **not** block host GVR ship on a prior pin.

---

## Breaking-change review process

1. Open PR with `CHANGELOG.md` entry under **Breaking** describing each GVR-facing change.
2. Update `tests/contract/test_aiecs_gvr_surface.py` snapshots intentionally (not silently).
3. Bump **major** version when removing or renaming contract-covered symbols or changing required method signatures.
4. Publish migration notes in `aiecs/docs/migration_2.1.0rc4_to_ga.md` (or successor) before GA/rc promotion.
5. Notify python-middleware MC GVR team; allow ≥1 release cycle before removing deprecated aliases.

### Known opt-in breaking changes (GA GVR train)

| Symbol | Change | When it bites |
|--------|--------|---------------|
| `BaseAIAgent.request_peer_review` | Return type `dict` → `Verdict` | Any caller enabling peer review / A-5 |

See [migration_2.1.0rc4_to_ga.md §5 Breaking changes (opt-in GVR surfaces)](./migration_2.1.0rc4_to_ga.md#5-breaking-changes-opt-in-gvr-surfaces).

---

## Minimum symbol list

### Core agent (baseline)

| Symbol | Module | Notes |
|--------|--------|-------|
| `HybridAgent` | `aiecs.domain.agent.hybrid_agent` | L2 execution engine |
| `BaseAIAgent` | `aiecs.domain.agent.base_agent` | `execute_with_recovery`, `request_peer_review` |
| `AgentGoal` | `aiecs.domain.agent.models` | Flat goal model; extended in GA (A-3) |
| `AgentConfiguration` | `aiecs.domain.agent.models` | Includes `compact_after_tool_batch` (F4) |
| `GoalStatus`, `GoalPriority` | `aiecs.domain.agent.models` | Goal enums |

### HookPlugin (baseline)

| Symbol | Module | Notes |
|--------|--------|-------|
| `HookPlugin` | `aiecs.domain.agent.plugins.builtin.hook_plugin` | HookPlugin v2.1 |
| `AgentHookEvent` | `aiecs.domain.agent.plugins.hooks.events` | Includes `TASK_COMPLETED`, `STOP` |
| `PluginPhase` | `aiecs.domain.agent.plugins.models` | Includes `ON_TOOL_BATCH_END` |

### DAWP (baseline)

| Symbol | Module | Notes |
|--------|--------|-------|
| `DawpPlugin` | `aiecs.domain.agent.plugins.builtin.dawp_plugin` | L2 prompt-chain plugin |

### Verification (GA target — A-1, A-2, A-4, A-5, A-11)

| Symbol | Module | Notes |
|--------|--------|-------|
| `Verdict` | `aiecs.domain.agent.verification.models` | Structured verification result |
| `FeedbackItem`, `EvidenceItem` | same | Verdict sub-types |
| `AcceptanceCriterion` | same | Structured goal criteria |
| `VerificationContext` | same | Verifier context packet (no executor prompt) |
| `Verifier` | `aiecs.domain.agent.verification.verifier` | Protocol |
| `VerificationPolicy` | `aiecs.domain.agent.models` | Engine verify-fix config |
| `VerificationExhausted` | `aiecs.domain.agent.verification` | Max refines exception |
| `normalize_acceptance_criteria` | `aiecs.domain.agent.verification` | Read-time criteria coercion (D1-A) |
| `DeterministicGate`, `GateRegistry` | `aiecs.domain.agent.verification.gates` | Pure-code gates |
| `SpecGate`, `CitationUrlGate` | same | Reference implementations |
| `HybridAgent.verify` | `aiecs.domain.agent.hybrid_agent` | Optional L1/L2 hook |

### Goal graph (GA target — A-3)

| Symbol | Module | Notes |
|--------|--------|-------|
| `GoalGraph` | `aiecs.domain.agent.goal_graph` | Hierarchical goals |
| `GoalGraph.decompose` | same | Host-initiated; `NotImplementedError` without decomposer (D2-A1) |

### Loop detection (GA target — A-7)

| Symbol | Module | Notes |
|--------|--------|-------|
| `LoopSignal` | `aiecs.domain.agent.loop_detection` | Read-only stall signals |
| `LoopDetectionService` | same | Triple-window tracker |

### DAWP structured result (GA target — A-6)

| Symbol | Module | Notes |
|--------|--------|-------|
| `DAWPResult` | `aiecs.domain.agent.verification.dawp_result` | Terminal handoff to host WorkState |

### Recovery (GA target — A-9)

| Symbol | Module | Notes |
|--------|--------|-------|
| `RecoveryResult` | `aiecs.domain.agent.models` | Structured recovery outcome |

### Compression (GA target — A-10)

| Symbol / config | Module | Notes |
|-----------------|--------|-------|
| `compact_after_tool_batch` | `aiecs.domain.agent.models.AgentConfiguration` | F4 mid-iteration batch-end compaction (baseline rc4) |
| GVR preservation | `aiecs.domain.context.compression.gvr_preserve` | Skips criteria/deliverable tool results during microcompact |

Enable `compact_after_tool_batch=true` for long sub-goals inside one FC iteration.
Keep F1 (`compact_formatted_transcript`) at GVR goal boundaries — see
[context_compression_integration.md](./host/context_compression_integration.md) §GVR compression boundaries.

### CWE verifier (GA target — A-11)

| Symbol | Module | Notes |
|--------|--------|-------|
| `CweVerifier` | `aiecs.domain.agent.verification.cwe_verifier` | Optional H1 multi-perspective path |

---

## Configuration keys (GVR-relevant)

### Baseline (2.1.0rc4)

| Key | Type | Default | Issue |
|-----|------|---------|-------|
| `compact_after_tool_batch` | bool | `false` | A-10 / F4 |
| `compact_after_tool_batch_min_tokens` | int \| null | `null` | F4 |

### GA target (default off)

| Key | Type | Default | Issue |
|-----|------|---------|-------|
| `verification_policy.enabled` | bool | `false` | A-2 |
| `verification_policy.when_to_verify` | enum | `on_task_completed` | A-2 |
| `verification_policy.max_refines_per_goal` | int | `2` | A-2 |
| `verification_policy.skip_threshold` | float | `85` | A-2 |
| `verification_policy.skip_threshold_by_kind` | dict | see migration guide | A-2 |
| `verification_policy.registered_verifiers` | list[str] | `[]` | A-2 |
| `verification_policy.blocking` | bool | `true` | A-2 |
| `peer_review_policy.enabled` | bool | `false` | A-5 |
| `peer_review_policy.max_criteria` | int | `2` | A-5 |
| `loop_detection.enabled` | bool | `false` | A-7 |
| `loop_detection.window_size` | int | `20` | A-7 |
| `loop_detection.repeat_threshold` | int | `3` | A-7 |
| `loop_detection.hook_on_detect` | bool | `false` | A-7 |
| `dawp_emit_structured_result` | bool | `false` | A-6 |
| `goal_graph.default_decomposer` | enum | `none` | A-3 |
| `cwe_verifier.enabled` | bool | `false` | A-11 |

HookPlugin blocking and gate registry are configured via HookPlugin options and `GateRegistry.register()` respectively (see migration guide).

**Reference gates (A-4):** built-in `spec_gate` / `citation_gate` are heuristic contract-test sinks only. Production adoption path **A** requires custom `DeterministicGate` registration or L1 VERIFY — see [gvr_gate_semantics.md](./gvr_gate_semantics.md).

---

## § Adoption paths (ADR-018 A/B/C)

**Delivery vs adoption:** aiecs delivers all primitives (M-8, A-1…A-11) with **defaults off**. python-middleware enables features incrementally per the matrix below after contract tests pass.

| Issue | aiecs delivers | Default | Path A (full L2 sink) | Path B (host fallback) | Path C (partial) |
|-------|----------------|---------|------------------------|------------------------|------------------|
| M-8 | ✅ | — | Contract tests green → evaluate | Pin rc4 | — |
| A-1 | ✅ | verify off | Verifier + `HybridAgent.verify` | `spawn_subagent(verifier)` + host JSON | Shared schema + host spawn |
| A-2 | ✅ | policy off | **A** if A-1 + A-4 ready | L1 `run_gvr_loop` | HookPlugin pre-check only |
| A-3 | ✅ | GoalGraph unused | **A** if host code drops **>30%** | Full host `work_state.py` | Dual-write not recommended |
| A-4 | ✅ | empty registry | Spec/Citation L2 sink | L1 `gates/*` | — |
| A-5 | ✅ | peer_review off | QUICK path | Full verifier | — |
| A-6 | ✅ | opt-in | Host DAWPResult adapter | spawn_subagent plan C | Pre-Phase-4: no integration |
| A-7 | ✅ | loop detection off | Engine signal + host DECIDE | Host `stall_detection.py` | Hybrid |
| A-8 | ✅ | Hook blocking off | L2 stop_hook refine | L1 VERIFY only | A-2 C fallback |
| A-9 | ✅ | unchanged | `execute_with_recovery` | Host try/except ESCALATE | — |
| A-10 | ✅ | compact flag false | Mid-iteration batch compact | GVR boundary F1 only | — |
| A-11 | ✅ | CWE off | H1 CWE path | Dual verifier spawn | Optional |

### Locked design decisions (A-3)

- **D1-A + D1-A1:** `AgentGoal` extended in place; JSON emits `goal_id` / `parent_goal_id`; GVR aliases `id` / `parent_id` on read; legacy string `success_criteria` stored until GoalGraph upgrade; Verifier/Gate coerce at read via `normalize_acceptance_criteria`.
- **D2-A + D2-A1:** `GoalGraph.decompose` raises `NotImplementedError` without host `decomposer=`; builtin LLM decomposer deferred to future proposal.

---

## Related documents

- [migration_2.1.0rc4_to_ga.md](./migration_2.1.0rc4_to_ga.md) — upgrade guide
- [gvr_dawp_result.md](./gvr_dawp_result.md) — A-6 DAWPResult + host adapter sample
- [gvr_recovery_semantics.md](./gvr_recovery_semantics.md) — A-9 recovery strategies + VerificationExhausted ESCALATE
- [gvr_goal_graph_mapping.md](./gvr_goal_graph_mapping.md) — A-3 GoalGraph / WorkState field mapping
- [gvr_loop_detection.md](./gvr_loop_detection.md) — A-7 loop signals + host EC=0 hybrid use
- [host/context_compression_integration.md](./host/context_compression_integration.md) — F1/F4 compression (A-10)
- python-middleware: `issue_report/agent/Agent_issues_v2.md`, ADR-018

---

## CHANGELOG template sections (GVR releases)

When preparing a GVR-related release, include subsections under `[Unreleased]` or version heading:

```markdown
### GVR — Verdict / Verification (A-1, A-2, A-4, A-5, A-11)
- ...

### GVR — HookPlugin blocking (A-8)
- ...

### GVR — GoalGraph (A-3)
- ...

### GVR — Loop detection (A-7)
- ...

### GVR — DAWPResult (A-6)
- ...

### GVR — Recovery (A-9)
- ...

### GVR — Compression (A-10)
- ...

### GVR — Consumer API / Contract (M-8)
- ...
```

# Migration guide: aiecs 2.1.0rc4 → GA (GVR consumers)

This guide is for **python-middleware MasterController GVR** integrators upgrading from `aiecs==2.1.0rc4` to GA.

**Prerequisites:** Read [gvr_consumer_api.md](./gvr_consumer_api.md) for the full symbol list and ADR-018 adoption matrix.

---

## 1. Upgrade checklist

1. Pin new version: `pip install aiecs==2.1.0` (or latest GA rc).
2. Run consumer contract tests: `pytest tests/contract/test_aiecs_gvr_surface.py` (python-middleware) or the aiecs copy in this repo.
3. Confirm **baseline tier** tests pass without enabling new config flags.
4. Enable GVR primitives incrementally per adoption path (see §4).
5. Align `work_state.Verdict` with `tests/fixtures/gvr_verdict_v1.json`.

---

## 2. Default behavior (no config changes)

With all GVR flags at defaults (`verification_policy.enabled=false`, HookPlugin blocking off, empty gate registry, CWE off, GoalGraph unused):

- `HybridAgent.execute_task_streaming` behavior matches **2.1.0rc4**.
- `set_goal(success_criteria=str)` unchanged.
- `compact_after_tool_batch=false` unless explicitly enabled (F4).

---

## 3. Symbol-by-symbol migration

### M-8 — Contract baseline

- Add CI job running `tests/contract/test_aiecs_gvr_surface.py` against pinned aiecs.
- Import shared fixture: `tests/fixtures/gvr_verdict_v1.json`.

### A-1 — Verdict / Verifier

```python
from aiecs.domain.agent.verification.models import Verdict, VerificationContext
from aiecs.domain.agent.verification import normalize_acceptance_criteria

verdict = Verdict.from_dict(payload)  # round-trip with host work_state.Verdict
```

- Map host `work_state.Verdict` fields 1:1 (see fixture).
- `VerificationContext` MUST NOT include executor system prompt.

### A-2 — verification_policy

```yaml
verification_policy:
  enabled: false          # opt-in
  when_to_verify: on_task_completed  # on_task_completed | on_stop | never
  max_refines_per_goal: 2
  skip_threshold: 85
  skip_threshold_by_kind:
    factual: 90
    procedural: 90
    generative: 78
    creative: 78
  registered_verifiers: [spec_gate, citation_gate]
  blocking: true
```

**Adoption:** Path **A** only when A-1 + A-4 (V-4 B) are ready; else Path **C** (HookPlugin-only pre-check).

Priority when multiple mechanisms enabled: `verification_policy` > HookPlugin > default complete.

### A-3 — AgentGoal / GoalGraph

- **Storage:** JSON continues to use `goal_id`, `parent_goal_id` by default (D1-A1).
- **Read:** GVR code may use `.id` / `.parent_id` aliases.
- **Criteria:** Legacy string stored until GoalGraph upgrade; Verifier/Gate use `normalize_acceptance_criteria(goal)` at read time only.
- **Decompose:** Host must pass `decomposer=` to `GoalGraph.decompose`; default raises `NotImplementedError`.

### A-4 — Gate registry

Register SpecGate / CitationUrlGate for L2 pre-exit. L2 pass does **not** skip host L1 VERIFY (B1 strategy).

### A-8 — HookPlugin blocking

Enable structured `{action, feedback, feedback_items}` on `TASK_COMPLETED` / `STOP`. Data-only feedback — no “please reflect” templates.

### A-5 — peer_review

> **Breaking (opt-in GA surface):** `request_peer_review(...)` return type changed from
> **`dict` → `Verdict`**. This is a **minor semver additive change** to the method
> signature when peer review is invoked; callers using `review["approved"]` or
> `review.get("passed")` on a dict **must migrate** before enabling A-5.

```python
# rc4 (dict)
review = await agent.request_peer_review(task, result)
if review.get("approved"):
    ...

# GA (Verdict)
from aiecs.domain.agent.verification.models import Verdict

review = await agent.request_peer_review(task, result, criteria=[...])
if review.passed:
    ...
# serialized round-trip
review = Verdict.from_dict(payload)
```

`request_peer_review(..., criteria=...)` returns a `Verdict` mini subset parseable via `Verdict.from_dict()`.

```yaml
peer_review_policy:
  enabled: false
  max_criteria: 2
```

Goals with **≥5** acceptance criteria MUST NOT use peer_review alone — use full verifier or gate path.

### A-6 — DAWPResult

Structured terminal handoff from L2 DAWP prompt-chain runs. See [gvr_dawp_result.md](./gvr_dawp_result.md).

```yaml
dawp_emit_structured_result: false   # opt-in terminal dawp_result streaming event
```

DAWP is **L2 only** — does not replace L1 GVR. Partial/failed/aborted statuses MUST NOT silent-pass.

### A-9 — execute_with_recovery

See [gvr_recovery_semantics.md](./gvr_recovery_semantics.md). `RecoveryResult` + `execute_with_recovery_streaming`; ABORT propagates `VerificationExhausted` → host ESCALATE.

### A-7 — Loop detection

See [gvr_loop_detection.md](./gvr_loop_detection.md). `LoopDetectionService` + `LoopSignal` for host DECIDE; combine with EC=0 and verdict-improvement rules.

### A-10 — Compression

See [host/context_compression_integration.md](./host/context_compression_integration.md) §GVR compression boundaries.
Enable `compact_after_tool_batch=true` for long sub-goals; F1 at GVR boundaries remains compatible.
Microcompact preserves tool results referencing `deliverable_refs` / acceptance criteria.

### A-11 — CWE verifier

Optional for H1 goals only (`cwe_verifier.enabled=true`). Dual verifier spawn remains fallback when off.
Sequential fact→style roles via `CweVerifier` wrapping `review_refinement` template.

---

## § Adoption paths (ADR-018)

Full adoption matrix: [gvr_consumer_api.md](./gvr_consumer_api.md#-adoption-paths-adr-018-abc).

Recommended consumer enable order (after M-8 contract tests green):

1. A-1 Verdict schema + A-4 gates + A-8 Hook blocking
2. A-2 verification_policy (Path A criteria)
3. A-5, A-7, A-9, A-10 (P2 enhancements)
4. A-3, A-6, A-11 (P3 — adoption thresholds)

---

## 4. Recommended adoption order

1. M-8 contract tests green
2. A-1 Verdict schema + fixture alignment
3. A-4 gates + A-8 Hook blocking
4. A-2 verification_policy (if Path A criteria met)
5. A-5, A-7, A-9, A-10 (P2 enhancements)
6. A-3, A-6, A-11 (P3 — only if adoption thresholds met)

---

## 5. Breaking changes (opt-in GVR surfaces)

Defaults-off preserves rc4 runtime behavior, but **adopting** these GA primitives
introduces caller migrations:

| Surface | Change | Migration |
|---------|--------|-----------|
| **A-5 `request_peer_review`** | Return type `dict` → `Verdict` | Use `review.passed` / `Verdict.from_dict()` instead of `review["approved"]` |
| **A-1 `Verdict` schema** | New canonical type | Map host `work_state.Verdict` via [gvr_verdict_field_mapping.md](./gvr_verdict_field_mapping.md) |
| **A-3 `AgentGoal` JSON** | Emits `goal_id` / `parent_goal_id` (aliases on read) | Accept both canonical and GVR alias keys on deserialize |

No breaking changes when GVR flags remain at rc4 defaults and peer review is not invoked.

---

## 6. Breaking changes (none expected rc4 → GA with defaults off)

GA release is **additive** when defaults are unchanged. Breaking changes require major semver bump and entries in CHANGELOG **Breaking** section per [gvr_consumer_api.md](./gvr_consumer_api.md#breaking-change-review-process).

---

## References

- [Agent_issues_v2.md](https://github.com/) — consumer issue backlog (python-middleware repo)
- ADR-018 — mc-gvr-agentic-upgrade pending decisions
- OpenSpec change: `add-gvr-agentic-loop-primitives`

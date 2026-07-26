# GVR loop detection (A-7)

## Purpose

Engine exposes **read-only** `LoopSignal` values when the tool loop repeats the same `(tool_name, args_hash, result_hash)` triple within a sliding window. Host GVR DECIDE combines signals with EC=0 stall rules and verdict-improvement checks — the engine does not auto-abort.

## Configuration

```yaml
loop_detection:
  enabled: false
  window_size: 20
  repeat_threshold: 3
  hook_on_detect: false
```

| Key | Default | Notes |
|-----|---------|-------|
| `enabled` | `false` | rc4 behavior when off |
| `window_size` | `20` | Sliding window of tool triples |
| `repeat_threshold` | `3` | Fire signal when same triple count ≥ threshold |
| `hook_on_detect` | `false` | Dispatch optional `ON_LOOP_DETECTED` HookPlugin event |

## LoopSignal fields

| Field | Meaning |
|-------|---------|
| `repeated_triple_count` | Count of the most repeated triple in the current window |
| `last_triples` | Recent triples (`tool_name`, `args_hash`, `result_hash`) |
| `idle_iterations` | Consecutive FC iterations without tool calls |
| `effective_cycles` | `floor(repeated_triple_count / repeat_threshold)` when threshold met |

Query via `HybridAgent.get_loop_signals()` or `plugin_state["gvr.loop_signal"]` after detection.

## Hybrid use with host EC=0 rules

Recommended host DECIDE integration:

1. Read `LoopSignal` from engine after each tool-loop iteration or on `ON_LOOP_DETECTED`.
2. Combine with host **EC=0** (empty-cycle) counters — engine `idle_iterations` complements but does not replace host stall detection.
3. Require **verdict improvement** before continuing REFINE when loop signal fires (avoid infinite refine on identical failures).
4. Map sustained loops to ESCALATE or SIMPLIFY per host policy; engine signal alone does not terminate the loop.

## Performance note

When `loop_detection.enabled=false` (default), `LoopDetectionService.record_tool_call` returns immediately with no window maintenance. Benchmark expectation: negligible overhead on hot path when disabled.

## Optional hook

When `hook_on_detect=true`, the engine dispatches `ON_LOOP_DETECTED` with payload `{ signal, iteration, agent_id, task_id }`. Hook handlers MUST NOT mutate executor system prompt; use structured feedback only.

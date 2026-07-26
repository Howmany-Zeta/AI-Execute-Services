# GVR DAWPResult (A-6)

## Layering

**DAWP is L2 prompt-chain execution.** It does **not** replace the L1 GVR state machine (`run_gvr_loop`, DECOMPOSE, VERIFY, DECIDE) in python-middleware.

Use `DAWPResult` for structured handoff after terminal DAWP runs; host adapters map fields to `GoalNode.deliverable_refs` and `intra_steps`.

## Enabling structured terminal events

Default **off** (rc4-compatible). Opt in via config or task context:

```yaml
dawp_emit_structured_result: true
```

Or per task: `context["dawp_emit_structured_result"] = True`.

When enabled, `execute_task_streaming` yields an additional terminal event after each drained DAWP run:

```json
{
  "type": "dawp_result",
  "success": false,
  "dawp_result": {
    "status": "partial",
    "deliverable_refs": [],
    "partial_artifacts": [{"kind": "handoff_message", "content": "..."}],
    "criteria_progress": {"steps_completed": 1, "steps_total": 3},
    "chain_state": {"run_id": "...", "workflow_id": "..."},
    "error": "..."
  }
}
```

Optional callback: `context["dawp_result_callback"] = async def _(result: DAWPResult): ...`

## Status semantics

| Status | Meaning | Silent pass? |
|--------|---------|--------------|
| `completed` | DAWP completion marker seen | No — explicit pass (`passed=True`) |
| `partial` | Some steps completed, run ended early | **No** |
| `failed` | No steps completed successfully | **No** |
| `aborted` | `abort_main=True` and run failed | **No** |

Host adapters MUST NOT treat `partial`, `failed`, or `aborted` as success.

## Host adapter sample (WorkState / GoalNode)

```python
from aiecs.domain.agent.verification.dawp_result import DAWPResult

def apply_dawp_result_to_goal_node(node: GoalNode, result: DAWPResult) -> None:
    if not result.passed:
        node.status = "failed" if result.status == "failed" else "partial"
    node.deliverable_refs.extend(result.deliverable_refs)
    node.intra_steps.append(
        {
            "kind": "dawp_chain",
            "status": result.status,
            "chain_state": result.chain_state,
            "criteria_progress": result.criteria_progress,
            "artifacts": result.partial_artifacts,
            "error": result.error,
        }
    )
```

## Backward compatibility (task 9.6)

With `dawp_emit_structured_result=false` (default):

- Existing DAWP drain, hooks, and boundary events behave as in 2.1.0rc4
- No `dawp_result` terminal event is emitted
- Opt-in DAWP plugin path unchanged

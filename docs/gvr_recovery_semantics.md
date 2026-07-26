# GVR execute_with_recovery semantics (A-9)

## Overview

`BaseAIAgent.execute_with_recovery()` applies a strategy chain when task execution fails. Default `execute_task` / `execute_task_streaming` behavior is **unchanged** when recovery is not invoked.

## RecoveryResult

When `structured=True`, returns:

| Field | Description |
|-------|-------------|
| `success` | Whether any strategy produced a successful result |
| `result` | Final task result dict when successful |
| `strategies_attempted` | Ordered strategy names tried |
| `errors` | Per-strategy error summaries |
| `terminal_error` | Final error when all strategies fail |
| `escalation_reason` | e.g. `verification_exhausted` for host ESCALATE |
| `verdict` | Final `Verdict` payload when verification exhausted |

## Strategy chain (default)

1. **RETRY** — exponential backoff via `_execute_with_retry(execute_task, ...)`
2. **SIMPLIFY** — heuristic task simplification, then `execute_task`
3. **FALLBACK** — `_execute_with_fallback`
4. **DELEGATE** — capable peer agent (requires `collaboration_enabled`)

Add **ABORT** as terminal strategy to stop retrying and surface terminal errors.

## VerificationExhausted → host ESCALATE (10.3)

When `execute_task` / streaming raises `VerificationExhausted` during recovery:

- If **ABORT** is in the strategy list: exception is **re-raised** (non-structured) or returned as `RecoveryResult(escalation_reason="verification_exhausted")` (structured)
- Host GVR DECIDE maps this to **ESCALATE**

## Streaming path (`execute_with_recovery_streaming`)

Each strategy starts a **fresh** `execute_task_streaming` session:

- Yields all intermediate streaming events unchanged
- On first terminal `result` event with `success=True`, yields `recovery_result` and stops
- On `VerificationExhausted`, yields `recovery_result` with escalation metadata, then re-raises when ABORT is configured

Subagent / DAWP nested streams pass through transparently.

## Example: verify fail → RETRY → SIMPLIFY → ABORT

```python
from aiecs.domain.agent.models import RecoveryStrategy
from aiecs.domain.agent.exceptions import VerificationExhausted

strategies = [
    RecoveryStrategy.RETRY,
    RecoveryStrategy.SIMPLIFY,
    RecoveryStrategy.ABORT,
]

try:
    outcome = await agent.execute_with_recovery(
        task,
        context,
        strategies=strategies,
        structured=True,
    )
    if isinstance(outcome, RecoveryResult) and outcome.escalation_reason == "verification_exhausted":
        host_escalate(outcome.verdict)
except VerificationExhausted as exc:
    host_escalate(exc.verdict)
```

Streaming variant:

```python
async for event in agent.execute_with_recovery_streaming(task, context, strategies=strategies):
    if event["type"] == "recovery_result":
        recovery = event["recovery"]
        if recovery.get("escalation_reason") == "verification_exhausted":
            host_escalate(recovery.get("verdict"))
    else:
        handle_stream_event(event)
```

## Default execute unchanged (10.5)

`execute_task` and `execute_task_streaming` without calling recovery wrappers match 2.1.0rc4 behavior.

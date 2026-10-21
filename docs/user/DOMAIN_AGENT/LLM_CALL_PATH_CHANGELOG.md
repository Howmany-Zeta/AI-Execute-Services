# Caller Changelog: Shortened Agent LLM Call Path

Audience: anyone calling `LLMAgent`, `ToolAgent`, or `HybridAgent`.

Method signatures, constructors, streaming event names, and `execute_task` / `execute_with_recovery` shapes are unchanged. You do not need to rewrite call sites. A few **behaviors** changed. Adjust only if your code relied on the old ones.

## No migration required

These stay the same:

- Constructor arguments
- `execute_task(task, context)` / `execute_task_streaming(task, context)`
- `process_message(message)` / `process_message_streaming(message)`
- `execute_with_recovery` / `execute_with_recovery_streaming` signatures and default strategy order (`RETRY` → `SIMPLIFY` → …)
- Streaming event types (`started`, `token`, `tool_call`, `result`, `error`, …)
- LLM client construction (`XAIClient()`, `OpenAIClient()`, …)

## What callers should know

### 1. `process_message_streaming` raises on failure

Previously an `error` event from `execute_task_streaming` was dropped. The async for-loop finished with no tokens, which looked like a successful empty reply.

Now the same failure raises `TaskExecutionError`. If the stream produced no tokens but `result.output` has text (Vertex function-call mode, fallback body), that text is yielded once. Tokens already forwarded are not repeated.

```python
from aiecs.domain.agent.exceptions import TaskExecutionError

try:
    async for token in agent.process_message_streaming(user_text):
        print(token, end="", flush=True)
except TaskExecutionError as exc:
    # model / tool / disconnect failure — do not treat as empty success
    handle_failure(exc)
```

`execute_task_streaming` still yields `{"type": "error", ...}` and does not raise for those events.

### 2. A failed task leaves the agent `ACTIVE`

After hook reject, tool/model failure, cancel, or `aclose()`, the agent returns to `ACTIVE` and clears `_current_task_id`. The next user message can enter `BUSY` without `activate()`.

Do not branch on “task failed ⇒ `state == ERROR`”. `ERROR` now means **initialize failed**; `execute_task` refuses that agent.

```python
# after a failed execute_task
assert agent.state.value == "active"   # ready for the next message

# initialize() failed
# execute_task raises TaskExecutionError: "Agent is not ready"
```

### 3. ToolAgent reports tool failure as `success: false`

If the last tool raises, `execute_task` / streaming `result` no longer KeyError and no longer claim success with a missing `result`. Check `success` before using `output`.

```python
result = await tool_agent.execute_task({"description": "..."}, {})
if not result.get("success"):
    raise RuntimeError(result.get("output") or "tool failed")
```

### 4. Recovery `RETRY` runs the original task once

`execute_with_recovery` still starts with `RETRY`, then `SIMPLIFY`. `RETRY` calls `execute_task` (or `execute_task_streaming`) **once** on the original task. Rate limits (429 / 529) retry inside that call at the model entry. Tools are not replayed by an outer loop.

If `RETRY` raises, the next strategy is `SIMPLIFY` on the simplified task. Do not expect recovery to re-run the whole tool loop `max_retries` times.

## Unchanged for typical hosts

- Plugin phases (PRE_TASK, BUILD_MESSAGES, DAWP, GVR)
- Hybrid tool-loop iteration count and budget consume-on-success
- Stream event payloads (`token`, `tool_call_delta`, `thought_signature` on chunks)
- Prompt-cache hit/miss is now implicit. See [IMPLICIT_CACHE_MIGRATION.md](./IMPLICIT_CACHE_MIGRATION.md) for `cache_status`, `cache_hit`, and OpenAI `session_id`.

## Checklist

- [ ] Catch `TaskExecutionError` around `process_message_streaming`
- [ ] Treat empty streaming output as “no tokens yet”, not as success, if you still drain `execute_task_streaming` yourself
- [ ] After a failed task, send the next message; do not require `activate()`
- [ ] Read ToolAgent `success` before using `output`
- [ ] If you wrapped `execute_with_recovery` assuming whole-task retries, rely on inner model retry instead

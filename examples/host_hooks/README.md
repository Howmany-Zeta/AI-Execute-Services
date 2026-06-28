# Host hook integration snippets (H4-01)

Copy targets for **python-middleware** (`app/services/multi_task/`). This repo ships
aiecs only; Host wiring for permission UI and SSE lives in the application repo.

## Enable HookPlugin

```yaml
# agent config snippet
plugins:
  - name: hook
    enabled: true
    options:
      paths:
        - ./security/hooks.json   # or use examples/host_hooks/hooks.json
      allow_command_hooks: false  # set true only with hardened argv hooks
      hook_allowed_http_hosts:
        - audit.example.internal
      hook_model: gpt-4o-mini   # optional; per-hook model override in hooks.json wins
```

**Prompt/agent hooks** use the agent's `llm_client` unless you inject
`options.hook_api_client`. They share inference rate limits and billing with the main loop —
prefer HTTP hooks or a dedicated client for production audit paths. See
`docs/developer/DOMAIN_AGENT/HOOKS.md` (Prompt/agent hooks and LLM client).

Manifest-only security packs: add top-level ``hooks: ./hooks.json`` to a plugin
manifest; ``derive_plugin_configs`` auto-enables ``hook@builtin`` (§9.1.1).

## H7 / v2 permission stack

```python
from examples.host_hooks.host_context import (
    hook_notification_callback,
    hook_permission_checker,
    permission_checker,
    permission_prompt,
)

context = {
    "session_id": session_id,
    "permission_checker": permission_checker,  # v2 preferred
    "hook_permission_checker": hook_permission_checker,  # legacy v1 stub
    "permission_prompt": permission_prompt,
    "hook_notification_callback": hook_notification_callback,
    "hook_allowed_http_hosts": {"audit.example.internal"},
}

result = await agent.execute_task(task, context)
```

Flow (v2): ``permission_checker`` → ``permission_request`` → ``dispatch_host_notification`` (H7) →
``permission_prompt`` → (on deny: ``permission_denied`` + H2) → H1/H2 via ``dispatch_tool_with_hooks``.

## Streaming SSE bridge (H4-02)

```python
from aiecs.host.hooks import agent_hook_event_to_sse_payload

async def event_sink(event: dict):
    if event.get("type") == "agent_hook":
        payload = agent_hook_event_to_sse_payload(
            event,
            session_id=session_id,
            task_id=task.get("task_id"),
        )
        await sse_emit(payload)  # host transport — NOT in aiecs
```

See ``docs/developer/HOST_MIGRATION_HOOKS.md`` for the full checklist.

# Host migration — Agent Hooks (HookPlugin H4)

Guide for **python-middleware** integrating HookPlugin after H0–H3 land in aiecs.
Host code lives under `app/services/multi_task/`. This repo ships reference material
under `aiecs/host/hooks/`, `examples/host_hooks/`, and `docs/developer/DOMAIN_AGENT/HOOKS.md`.

## Prerequisites

- aiecs with `hook@builtin` (H0–H3 complete)
- HybridAgent or ToolAgent with plugins enabled

## Enable HookPlugin

### Explicit config

```yaml
plugins:
  - name: hook
    enabled: true
    options:
      paths:
        - ./security/hooks.json
      allow_command_hooks: false
      hook_allowed_http_hosts:
        - audit.example.internal
```

Snippet: `examples/host_hooks/hooks.json`

### Manifest-only security pack (§9.1.1)

When a discovered manifest declares `hooks: ./hooks.json` and no explicit hook
plugin config exists, `derive_plugin_configs` produces one enabled `PluginConfig(name="hook")`
merging all manifest hook paths.

When explicit `{name: hook, enabled: false}` exists, hooks stay inactive and startup warns.

### Policy lock (production)

Use `policy_plugins` with `policy_locked: true` to prepend tenant hook paths that
cannot be disabled by task-level overrides.

## H7 — Host notification callbacks (§6.6)

Hooks.json `notification` entries are **not executable in v1**. Runtime H7 uses Host
context callbacks only:

| Context key | Role |
|-------------|------|
| `hook_permission_checker` | `(tool_name, tool_input) → (needs_confirm, reason)` |
| `hook_notification_callback` | Unified async sink for H7 payload (preferred) |
| `permission_prompt` | `(tool_name, reason) → bool` — legacy UI gate after H7 |

**Order on confirmation path:** `resolve_tool_confirmation` → `dispatch_host_notification`
(H7) → `permission_prompt` → H1 (if approved) or H2-only (if denied).

Copy targets: `examples/host_hooks/host_context.py`

```python
context = {
    "hook_permission_checker": hook_permission_checker,
    "hook_notification_callback": hook_notification_callback,
    "permission_prompt": permission_prompt,
    "hook_allowed_http_hosts": {"audit.example.internal"},
}
```

Optional HookPlugin config matcher when no checker is set:

```yaml
options:
  confirm_tools: "write_*"
```

## Command hook hardening (§12)

- Set `allow_command_hooks: true` only when required.
- Command hooks use `shell=False`, argv list, stdin JSON payload, minimal env.
- HTTP hooks require host in `hook_allowed_http_hosts` (fail closed).
- Never commit secrets in hooks.json; use env allowlist via `hook_env_allowlist`.
- **H1/H2 `tool_input` is sent verbatim** to command stdin / HTTP POST — no value redaction (unlike H5 `context_keys`). Do not pass raw tokens or credentials in tool arguments when command/HTTP hooks are enabled. See [HOOKS.md](./DOMAIN_AGENT/HOOKS.md) — *H1/H2 tool_input exposure*.

## Prompt/agent hooks — LLM sharing (production)

Prompt and agent hooks use `resolve_hook_prompt_client()` → the agent's main `llm_client`
unless `options.hook_api_client` is set. Wiring is correct; **operational coupling** remains:

- Hook validation shares **quota, latency, and billing** with task inference
- `hook_model` changes model id only — does not isolate rate limits or spend
- No LLM client → prompt hooks fail clearly (`block_on_failure` blocks the event)

| Mitigation | Isolates quota/billing? |
|------------|-------------------------|
| HTTP hooks instead of prompt hooks | Yes (off inference path) |
| `options.hook_api_client` | Yes (Host-injected `SupportsHookPrompt`) |
| `options.hook_model` | No (cost reduction on same client only) |

See [DOMAIN_AGENT/HOOKS.md](./DOMAIN_AGENT/HOOKS.md) — *Prompt/agent hooks and LLM client*.

## Streaming observability (H4-02)

HybridAgent `execute_task_streaming` accepts `event_sink` on plugin context.
`dispatch_agent_hook` emits:

```json
{"type": "agent_hook", "event": "pre_tool_use", "blocked": false, "hook_count": 1, "duration_ms": 12.3}
```

Map to host SSE:

```python
from aiecs.host.hooks import agent_hook_event_to_sse_payload

payload = agent_hook_event_to_sse_payload(event, session_id=sid, task_id=tid)
```

Host owns transport; aiecs only shapes payloads (same pattern as M4 compression bridge).

## Compression bridge (H3 recap)

When HookPlugin is enabled, H3/H4 fire only through `bridge_compression.py` inside
`maybe_compact_before_llm`. Host `compression_hook_executor` is merged per D-10 order;
do not register duplicate pre/post compact hooks on both systems without understanding merge.

## Checklist

| Step | Action |
|------|--------|
| 1 | Add `hook@builtin` to agent config or manifest hooks pack |
| 2 | Ship `hooks.json` with HTTP/prompt hooks (command only if hardened) |
| 3 | Wire H7 callbacks on `execute_task` context |
| 4 | Set `hook_allowed_http_hosts` for each audit endpoint |
| 5 | Optional: map `agent_hook` SSE via `aiecs.host.hooks` |
| 6 | Verify with `pytest test/unit/domain/agent/plugins/hooks/` |

See also: [DOMAIN_AGENT/HOOKS.md](./DOMAIN_AGENT/HOOKS.md), [HOST_MIGRATION_M4.md](./HOST_MIGRATION_M4.md).

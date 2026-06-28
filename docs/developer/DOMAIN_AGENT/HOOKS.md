# Agent Hooks (HookPlugin)

Developer guide for declarative agent hooks via `hook@builtin` and `hooks.json`.

**Reference**: [OpenHarness hooks reference](../../issue_report/agent/reference/OPENHARNESS_HOOKS_REFERENCE.md)

## Emit model (§2)

Hooks attach at three mechanisms:

| Mechanism | Examples | Invocation |
|-----------|----------|------------|
| Phase callback | H8, H9, H11, H15 | `HookPlugin.on_*` → `dispatch_agent_hook()` (SSE telemetry) |
| Agent hot-path | H5, H12, H13, H14, H1/H2, H6, H18–H21 | `dispatch_agent_hook()` in agent loop |
| Bridge | H3, H4 | `bridge_compression.py` (H3+) |

## Host integration (H4)

- H7 notifications: `hook_permission_checker`, `hook_notification_callback`, `permission_prompt` on task `context` — not hooks.json executors (v1).
- SSE: `aiecs.host.hooks.agent_hook_event_to_sse_payload` maps streaming `agent_hook` events for Host transport.
- Migration guide: [HOST_MIGRATION_HOOKS.md](../HOST_MIGRATION_HOOKS.md); examples: `examples/host_hooks/`.

## Session hooks vs agent lifecycle (§4.5)

| Concept | v1 behavior |
|---------|-------------|
| `session_start` / H8 | Fires on **agent instance** `AGENT_INIT` (`HookPlugin.on_agent_init`), not Host chat session open |
| `session_end` / H9 | Fires on **agent instance** `AGENT_SHUTDOWN` |
| Product session (idle timeout, multi-task) | Host responsibility; not emitted by HybridAgent v1 |

### H8/H9 during `PluginManager.initialize()`

`PluginManager.initialize()` runs `on_agent_init` with **`task={}` and `context={}`** — there is no task yet, so **`session_id` is absent** on the init-time H8 payload unless Host injects it into agent config before init (unusual) or fires a separate product-session hook at chat open.

| Field on H8 at init | Typical value |
|---------------------|---------------|
| `agent_id` | Set from agent instance |
| `session_id` | `null` / omitted (empty init context) |
| `reason` | From `context["session_start_reason"]` or `session_reason` if pre-seeded on init ctx |

Per-task hooks (H5, H1/H2, etc.) use the real task `context` with Host `session_id`. Do not treat init-time H8 as Host product session start unless you explicitly wire `session_id` into the init context.

## Pre-tool block does not short-circuit subsequent hooks (§5.1.3)

**Product expectation (AIEcs v1/v2):** When a high-priority hook returns `blocked=True`, **lower-priority hooks on the same event still run** (serial audit). Tool execution or compaction is blocked via the aggregate `blocked` flag, but remaining hooks execute so audit/logging hooks always fire.

| Aspect | AIEcs | Some Harness implementations |
|--------|-------|------------------------------|
| After block | Later hooks still run | May short-circuit remaining hooks |
| Gate decision | `AggregatedHookResult.blocked` (any hook) | Varies |
| Rationale | Audit trail over latency | Fail-fast on first deny |

This is **intentional** — not a bug. Do not rely on short-circuit side effects in lower-priority hooks. Regression: `test_serial_execution_all_hooks_run_even_after_block`.

Future opt-in short-circuit (ADR-002 backlog `short_circuit_on_block`) is **not** enabled by default.

## Merge and priority (§5.1.1–§5.1.2)

- **Multi-source merge**: manifest paths, inline hooks, and `hooks.json` files append in load order; duplicate fingerprints dedupe.
- **Priority**: hooks on the same event sort **descending** by `priority`; ties keep stable source order.
- **CC `{matcher, hooks:[]}` wrapper**: outer `matcher` applies to nested hooks that omit their own `matcher`; explicit per-hook matchers win.
- **ADR-002 deferred CC events** (e.g. `PostToolUseFailure`, `PermissionDenied`) warn and are not registered in v1 unless `strict_cc_hooks: true` (fail-fast).

## Aggregation merge order (§5.1.3)

When multiple hooks run on one event (serial, highest `priority` first):

| Field | Merge rule |
|-------|------------|
| `blocked` | `True` if **any** hook blocked |
| `reason` | First blocked hook's reason |
| `modified_output`, `updated_mcp_output` | **Last** non-empty value (forward scan) |
| `updated_input` | Shallow-merge all dicts; later hooks override keys |
| `permission_decision`, `additional_context` | **Last** hook with a value (reverse scan — lowest priority wins) |
| `prevent_continuation` | Last explicit signal (reverse scan) |

Hook authors: lower-priority audit hooks can still run after a block; output fields from the last hook in the chain win unless documented otherwise above.

## H5 `context_keys` redaction (§5.2)

H5 `user_prompt_submit` payload includes **key names only**, never values:

- Keys starting with `_` are omitted
- Secret-like keys (`api_key`, `token`, `password`, etc.) are omitted
- Host may set `context["hook_context_keys_allowlist"]` to override (Host assumes leak risk)

## H1/H2 `tool_input` exposure (§5.2 — no value redaction)

Unlike H5, **H1/H2 payloads include the full `tool_input` dict with values** — CC-style hook contract for audit hooks.

| Sink | What receives `tool_input` |
|------|----------------------------|
| **Command hooks** | Full event JSON on **stdin**; also `AIECS_HOOK_PAYLOAD` env (entire payload) |
| **HTTP hooks** | POST body `{ "event": "...", "payload": { "tool_input": ... } }` |
| **Prompt/agent hooks** | Embedded in `$ARGUMENTS` JSON in the LLM prompt |

**There is no built-in redaction** for tool argument values (no `hook_tool_input_allowlist` / denylist today). If Hosts or tools pass tokens, passwords, or credentials in tool args, command subprocesses and remote HTTP endpoints **will receive them**.

### Mitigations (Host / operator)

| Control | Scope |
|---------|--------|
| **`allow_command_hooks: false`** (default) | Disables command hooks entirely |
| **`hook_allowed_http_hosts`** | Restrict HTTP hooks to trusted audit endpoints only |
| **Tool design** | Pass secret references (env var names, vault IDs) — not raw secrets — in tool args |
| **Hook type choice** | Prefer HTTP to a hardened internal audit service over command hooks on shared workers |
| **H5-style discipline** | Do not assume future automatic redaction; treat hook destinations as **data processors** |

### Contrast with H5

| Payload field | Values included? |
|-----------------|------------------|
| H5 `context_keys` | **Key names only** (values never sent) |
| H1/H2 `tool_input` | **Full JSON** (all keys and values) |

Future work (not in v1/v2): optional `hook_tool_input_redact_keys` or allowlist on task context — tracked as Host hardening backlog, not implemented.


| Scenario | Hooks fire? |
|----------|-------------|
| No hook config, no manifest hooks | No (plugin not loaded) |
| Explicit `enabled: true` | Yes |
| Manifest-only pack | Auto-enable via `derive_plugin_configs` |
| `enabled: false` + manifest paths | No registry; startup warn |
| `policy_locked: true` | Force enable |

## Security (§12)

- **`allow_command_hooks`** (canonical): must be `true` to load `type: command` hooks
- Command hooks: **no shell**, argv list, payload on **stdin JSON**, minimal env (no parent inherit)
- HTTP hooks: host must be in `hook_allowed_http_hosts`; non-2xx responses block when `block_on_failure=true`
- **Event budget**: `event_timeout_seconds` caps total wall-clock time for the serial hook chain; exceeding the budget **blocks** the event (fail-closed for H1/H3 gates)
- Prompt/agent: `$ARGUMENTS` → JSON embed only (command hooks use stdin JSON; argv is never expanded)

## Prompt/agent hooks and LLM client (production)

**Wiring (correct):** `resolve_hook_prompt_client()` adapts `agent.llm_client` through `AgentLLMHookPromptClient` in `HookPlugin._create_executor()` (see `test_hook_plugin.py`). Agents **without** an LLM client fail prompt hooks with a clear error; `block_on_failure=true` blocks the event.

**Operational coupling (by design):** Prompt/agent hooks share the task LLM client unless Host sets `hook_api_client`. Hook validation competes with inference for quota, latency, and spend — not a wiring bug.

| Coupling | Default | Isolated when |
|----------|---------|---------------|
| **Quota / rate limits** | Same provider TPM/RPM as task `generate_text` | Separate `hook_api_client` (different key or provider) |
| **Latency** | Serial hook LLM calls add RTT before tool/compact gates | HTTP hooks, or dedicated hook client |
| **Model selection** | Per-hook `model` → `hook_model` → `llm_model` on **same** client | `hook_model` picks a cheaper id; full isolation needs `hook_api_client` |
| **Billing** | No aiecs hook line-item; tokens on shared usage path | Host wrapper tagging `context`, or separate credentials |
| **Connection pool** | Same SDK / HTTP session as inference | Separate client instance |

| Topic | Behavior |
|-------|----------|
| **Resolution** | `prompt_client.py`; override via `HookPlugin.options.hook_api_client` or `api_client` |
| **Extra LLM kwargs** | `AgentConfiguration.get_llm_call_kwargs()` forwarded (e.g. `thinking_config`) |

Hook LLM calls use `temperature=0.0` and `max_tokens=512` — independent of task sampling except shared `extra_llm_kwargs`.

### Host isolation options

No separate hook billing meter in aiecs. Without `hook_api_client`, count hook LLM volume in task SLO and spend.

1. **HTTP hooks** — audit off the inference path (recommended when hooks must not compete with user LLM).
2. **`hook_api_client`** — inject `SupportsHookPrompt` before `PluginManager.initialize()` (separate client, API key, or billing wrapper).
3. **`hook_model`** — cheaper model on the **same** client (cost only; **does not** isolate quota or billing).

```yaml
plugins:
  - name: hook
    enabled: true
    options:
      hook_model: gpt-4o-mini   # same client, different model id only
```

```python
# Host: inject before PluginManager.initialize()
class BillingTaggedHookClient:
    async def complete_hook_prompt(self, *, prompt: str, model: str | None, max_tokens: int) -> str:
        response = await audit_llm.generate_text(
            messages=[LLMMessage(role="user", content=prompt)],
            model=model or "gpt-4o-mini",
            max_tokens=max_tokens,
            context={"usage_category": "agent_hook", "bill_to": "audit"},
        )
        return response.content

hook_config.options["hook_api_client"] = BillingTaggedHookClient()
```

## Agent coverage (file checklist)

| Agent | Hook events (v1 plan) |
|-------|----------------------|
| `hybrid_agent.py` | H1–H6, H11–H21 (H1+ in later phases) |
| `tool_agent.py` | H1/H2/H5/H6 via shared helpers (H1+) |
| `llm_agent.py` | H5/H12/H13 (H2-04) |

## Module layout

```
aiecs/domain/agent/plugins/hooks/
├── events.py
├── schemas.py
├── registry.py
├── executor.py
├── loader.py
├── types.py
├── payload.py
├── dispatch.py
├── notifications.py
├── bridge_compression.py
├── task_boundary.py
└── tool_dispatch.py
```

## v2 permission stack (ADR-002 P0)

v2 adds programmatic permission events distinct from H1 hook blocks (design D-V2-06).

| Event | When | H1 runs? |
|-------|------|----------|
| `permission_request` | Checker returns `ask` | No (yet) |
| `permission_denied` (H22) | Checker/user deny before audit | No |
| `pre_tool_use` (H1) | After permission allow | Yes |
| `post_tool_use` (H2) | Always once per invocation | N/A |
| `post_tool_use_failure` | After `_execute_tool` raises, before H2 | After H1 |

### `permission_checker` protocol

Inject on task context (preferred over legacy `hook_permission_checker`):

```python
from aiecs.domain.agent.plugins.hooks.permission import PermissionDecision

async def permission_checker(tool_name, tool_input, context) -> PermissionDecision:
    if tool_name.startswith("write_"):
        return PermissionDecision.ask("Confirm write")
    return PermissionDecision.allow()
```

Legacy `hook_permission_checker` returning `(True, reason)` still maps to `ask`. On exception, both legacy and v2 checkers **fail closed** (H22 + H2, H1 skipped).

**Observability:** Both checkers log checker exceptions at **`warning`** with `exc_info` (deny is identical; only legacy used to be louder — now aligned).

### PreToolUse hook outputs (§17)

After H1 aggregation, before execute:

- `updated_input` — merged into tool arguments (last wins)
- `permissionDecision` — `allow` | `ask` | `deny` from hook JSON
- Post H2: `updated_mcp_output` for `mcp__*` tools; `modified_output` for others

### H2 payload: `blocked` vs `permission_denied` (§7.6.2)

Aligns with permission matrix **PERM-03/04** (see `test_v2_permissions.py`):

| Deny source | H1 fired? | H2 fields | Notes |
|-------------|-----------|-----------|-------|
| Pre-H1 `permission_checker` / user deny (PERM-03) | No | `permission_denied=true`, `blocked=true` | Policy gate (H22 path) |
| H1 hook `blocked=true` (PERM-04) | Yes | `blocked=true` only | Hook rejection; **not** `permission_denied` |
| Post-H1 hook `permissionDecision: deny` | Yes | `blocked=true` only | Same as PERM-04 — hook audit after H1 ran |

Hook authors comparing to §7.6.2: **`permission_denied` is reserved for pre-H1 policy/user denies (H22)**. Post-H1 hook denies use `blocked` only so consumers can distinguish policy gates from hook audit decisions. Regression: `test_h1_permission_decision_deny_sets_blocked_not_permission_denied`.

### Normative dispatch order

See [design D-V2-06](../../openspec/changes/add-agent-hook-v2-semantic-parity/design.md): access → permission → H22/H2 on deny → H1 → updated_input → execute → PTUF → H2.

## v2 compression metadata (Epic 3 — F1/F2)

F1 `compact_formatted_transcript()` (L2) and F2 `PreCompactContext.metadata` enrich H3/H4 payloads.

| Layer | Entry | Who sets F2 metadata | Hook bridge |
|-------|-------|----------------------|-------------|
| L2 | `aiecs.host.compression.compact_formatted_transcript` | Host / F1 caller (`build_pre_compact_metadata`) | Host-driven H3 when wired |
| L3 | `maybe_compact_before_llm` → `auto_compact_if_needed` | `tool_loop_core` passes `compact_metadata` (`layer=L3`, `session_id`, `estimated_tokens`, …) | `bridge_compression.py` |

### F2 coverage by entry point (§17 payload enrichment)

F2 **unlocks** §17 H3/H4 fields; the bridge **never synthesizes** them — it forwards
`PreCompactContext.metadata` / `PostCompactContext.metadata` only.

| Entry | F2 on H3/H4 | Notes |
|-------|-------------|-------|
| L3 proactive `maybe_compact_before_llm` | **Yes** | `build_pre_compact_metadata(layer=L3, …)` |
| L3 reactive `on_prompt_too_long` (PTL) | **No** | Omits `compact_metadata` today — thin H3 |
| L2 `compact_formatted_transcript` (F1) | **Yes** | `layer=L2`, `formatted_transcript=True` |
| `ContextEngine.compress_on_append_if_needed` | **No** | Direct orchestrator call without metadata |
| Host `l2_mc_adapter.auto_compact_if_needed` | **No** | Host MC path; no F2 overlay unless caller adds it |
| Orchestrator post-hook (H4) | **Partial** | `build_post_compact_metadata(layer, checkpoint)` when `pre_meta` had `layer` |

**Not a v1 defect** (cross-ref §2): v1 H0→H4 may ship thin payloads; full §17 enrichment is v2.0 / Epic 3 F2.
Primary L3 hot path and L2 F1 are wired; remaining rows are backlog unless the caller passes `compact_metadata`.

### H3/H4 payload pass-through (not synthesized in bridge)

`bridge_compression.py` forwards `PreCompactContext.metadata` / `PostCompactContext.metadata` to
`build_pre_compact_payload` / `build_post_compact_payload` **as-is**. The bridge does not invent
`layer`, `estimated_tokens`, or `formatted_transcript` — upstream compression code must populate
metadata (F2 contract in `domain/context/compression/metadata.py`).

| Field | When present on H3 payload |
|-------|----------------------------|
| `layer` | `metadata["layer"]` set (L3 tool loop: `layer=L3`; L2 Host: `layer=L2`) |
| `estimated_tokens` | `metadata["estimated_tokens"]` (L3: from `estimate_message_tokens`; L2/F7: `estimate_transcript_tokens`) |
| `formatted_transcript` | `metadata["formatted_transcript"]` true (L2 transcript compact) |
| `session_id` | `metadata["session_id"]` when provided |
| `checkpoint` (H4) | `metadata["checkpoint"]` from orchestrator post context; bridge may merge from `result.compact_metadata` |

**Thin payloads** on paths in the “No” rows above — not a bridge bug; upstream must populate F2 metadata.
Epic 3 cross-ref: [AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md](../../issue_report/agent/AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md). Tests: `test_v2_compression_notification`, `test_h3_compression_bridge`.

Enable v2 hooks.json notification executors with `HookPlugin.options.enable_v2_hooks: true`.
Order: registry `notification` hooks → `hook_notification_callback` → `permission_prompt`.

## v2.1 lifecycle (§17)

Task kernel order when plugins are enabled:

1. H5 `user_prompt_submit` — `continue:false` rejects before `PRE_TASK`
2. `PRE_TASK` plugin phase
3. `BUILD_MESSAGES` + user task row
4. H5b `user_prompt_in_history` — `additionalContext` merged into messages / `plugin_state["hook.additional_context"]`
5. `PRE_MAIN_LOOP` plugin phase

### H11 `pre_main_loop` block is non-blocking (§7.6 footnote)

H11 fires in `HookPlugin.on_pre_main_loop` before DAWP pre-loop drain. When hooks return `blocked=true` (including **event budget exceed** / `block_on_failure`), HookPlugin **logs a warning and continues** — the main tool loop still runs.

| Signal | Effect on main loop |
|--------|---------------------|
| H11 `blocked=true` | Warning logged; loop **continues** (v1 intentional) |
| KnowledgePlugin `PluginShortCircuitResult` | **Does** skip tool loop (plugin phase short-circuit, not H11) |

Do not use H11 `blocked` as a task gate in v1; use H5 `continue:false`, H6 `preventContinuation`, or plugin short-circuit instead.

### H6 `preventContinuation`

When the H6 `stop` hook aggregate returns `preventContinuation: true` (or `continue: false`), the tool loop re-enters instead of returning the final result (streaming and non-streaming paths).

### Session hooks (H8/H9)

See [Session hooks vs agent lifecycle (§4.5)](#session-hooks-vs-agent-lifecycle-45) for init-time empty context and Host product session boundaries.

### Subagent events — `subagent_stop` vs `dawp_run_end` (§4.3)

Harness **`SubagentStop`** maps to AIEcs **`dawp_run_end`** (H17). There is no separate swarm coordinator in HybridAgent.

| Surface | Value | Notes |
|---------|-------|-------|
| Canonical enum | `AgentHookEvent.DAWP_RUN_END` (`"dawp_run_end"`) | HybridAgent emit path (`_drain_pending_dawp_runs`) |
| Deprecated enum | `AgentHookEvent.SUBAGENT_STOP` (`"subagent_stop"`) | Kept for CC parity; **do not register hooks under this key in code** |
| hooks.json keys | `SubagentStop`, `subagent_stop`, `dawp_run_end` | Loader **`normalize_event_key`** rewrites aliases → `DAWP_RUN_END` with deprecation warning |

Hooks registered via hooks.json under the legacy names **do fire** (stored under `dawp_run_end`). Programmatic `registry.get_hooks(AgentHookEvent.SUBAGENT_STOP)` would miss them — use `DAWP_RUN_END` only in Python.

- `subagent_start` fires when a DAWP run is dequeued (before `dawp_run_start`)
- `dawp_run_end` payloads may include `last_assistant_message` and `agent_transcript_path`
- `stop_failure` fires when H6 hook execution fails (fail-open: loop still stops)
- `task_completed` fires on success when hooks are registered or `context["enable_task_completed_hook"]=true`

### F3 `CompressionPolicyResolver`

Optional resolver on `context["compression_policy_resolver"]` or `AgentConfiguration.compression_policy_resolver` selects L2 vs L3 `CompressionPolicy` chains.

### F4 `ON_TOOL_BATCH_END`

Plugin phase (not hooks.json) fired after each tool batch completes, before the next LLM call. Implement `on_tool_batch_end(ctx, iteration, messages)` on custom plugins.

## References

- v1 change: `openspec/changes/add-agent-hook-plugin/`
- v2 change: `openspec/changes/add-agent-hook-v2-semantic-parity/`
- ADR-002: [ADR-002-cc-hook-v1-deferred-increments.md](../../issue_report/agent/adr/ADR-002-cc-hook-v1-deferred-increments.md)
- Epic 3 cross-ref: [AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md](../../issue_report/agent/AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md)

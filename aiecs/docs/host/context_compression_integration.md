# Context compression — host integration guide

This document is the **canonical host integration guide** shipped inside the `aiecs`
PyPI wheel (`aiecs/docs/host/context_compression_integration.md`). It explains how
**python-middleware** (and other hosts) integrate with the aiecs context compression
kernel without duplicating OpenHarness `run_query` or Claude Code UI/SSE layers.

For the full host orchestration plan, see the python-middleware repo:
[PLAN_AIECS_CONTEXT_COMPRESSION_ORCHESTRATION.md](https://github.com/Howmany-Zeta/python-middleware/blob/main/issue_report/agent/PLAN_AIECS_CONTEXT_COMPRESSION_ORCHESTRATION.md).

## Four-layer host model

| Layer | Owner | When compact runs | Primary entry |
|-------|-------|-------------------|---------------|
| **L1** | Host | Warning thresholds (70/80/90%); optional L1 compact | `should_compress` + host SSE |
| **L2** | Host | MC recursive task boundary; formatted `{role, content}` history | `compact_formatted_transcript` (F1) |
| **L3** | aiecs HybridAgent | Tool-loop pre-LLM gate; optional mid-iteration batch-end (G1) | `maybe_compact_before_llm` |
| **CE** | aiecs ContextEngine | Post-append token-based compact (O8) | `compress_on_append_if_needed` |

**Out of aiecs:** YAML config UI, SSE event names, i18n, GrowthBook flags.

### F1–F7 API mapping table (2.1.0rc2 baseline)

| ID | Symbol | Import path | Layer |
|----|--------|-------------|-------|
| **F1** | `compact_formatted_transcript` | `aiecs.host.compression` | L2 |
| **F2** | `build_pre_compact_metadata`, `build_post_compact_metadata` | `aiecs.domain.context.compression.metadata` | L2 / L3 / CE |
| **F3** | `CompressionPolicyResolver`, `resolve_layer_compression_policy` | `aiecs.domain.context.compression.policy_resolver` | L2 / L3 |
| **F4** | `PluginPhase.ON_TOOL_BATCH_END` | `aiecs.domain.agent.plugins.models` | L3 (plugin phase; G1 batch-end compaction) |
| **F5** | `RETRY_COMPACT_PROGRESS_PHASES`, `compact_progress_event_to_sse_payload` | `aiecs.host.compression.progress_bridge` | L2 / L3 |
| **F6** | This document | `aiecs/docs/host/context_compression_integration.md` (wheel) | Host |
| **F7** | `estimate_transcript_tokens` | `aiecs.host.compression` | L1 / L2 |

> **G5 (Epic 4):** `estimate_transcript_tokens` is re-exported from
> `aiecs.host.compression` for L1/L2 DX.

## Feature gates

### `USE_AIECS_COMPRESSION` — L2 gate

The environment flag selects whether the host routes L2 boundary compaction through
aiecs adapters. It does **not** enable L3 HybridAgent compaction.

```python
from aiecs.host.compression.config import use_aiecs_compression

if use_aiecs_compression():
    # Route MC recursive boundary through aiecs L2 adapters
    ...
```

Implementation: `aiecs/host/compression/config.py` reads `USE_AIECS_COMPRESSION`
(`1` / `true` / `yes` / `on`). Host keeps L1 warn-only policy and L2 boundary
*when* to compact; this flag only selects the adapter path.

### `enable_context_compression` — L3 gate

L3 tool-loop compaction is controlled on agent bootstrap via `AgentConfiguration`:

```python
from aiecs.domain.agent.models import AgentConfiguration

config = AgentConfiguration(
    enable_context_compression=True,
    context_window_limit=200_000,
    compression_policy={...},  # optional ADR-007 override
)
```

When `enable_context_compression=False` and no `compression_policy` override is set,
HybridAgent skips proactive compaction (`maybe_compact_before_llm` no-op).

## L3 wiring checklist

Wire these on the agent execution context (or HybridAgent instance attributes) before
the tool loop runs:

| Context key / attribute | Purpose |
|-------------------------|---------|
| `compression_hook_executor` | O6 pre/post compact hooks (`HookExecutor`) |
| `on_compact_progress` | Callback for O7 `CompactProgressEmitter` events |
| `tool_artifact_port` | A9 offload storage (MinIO/S3) |
| `session_memory_port` | A15 external session memory text |
| `compression_policy_resolver` | F3 layer-specific policy (L2 vs L3 chains) |

HybridAgent resolves ports in `_build_tool_loop_compression_context_async`:

```python
context = {
    "compression_hook_executor": hook_executor,
    "on_compact_progress": lambda event: host_sse.emit("context_compact_progress", event),
    "tool_artifact_port": s3_tool_artifact_port,
    "session_memory_port": session_memory_port,
    "compression_policy_resolver": my_resolver,
}
```

Optional: set `AgentConfiguration.compression_policy_resolver` instead of (or in
addition to) the context dict key.

## L2 — use F1; avoid legacy full chain on text dumps

**Do not** run the full L3 microcompact/collapse chain on formatted MC text dumps.
Use **F1** for L2 formatted history:

```python
from aiecs.host.compression import compact_formatted_transcript

rows, did_compact = await compact_formatted_transcript(
    formatted_history,
    llm_client=llm_client,
    session_id=session_id,
    context=context,
    config=agent_configuration,
)
```

Default F1 chain is `("llm",)` only — inequivalent to the L3 full policy chain.

### Legacy adapter migration (G3)

All formatted transcript text dumps passed to
`compact_at_mc_recursive_boundary` **always delegate to F1**
`compact_formatted_transcript` (llm-only chain), including explicit tuple strategies
such as ``strategy=("microcompact",)``. The ``strategy`` argument is ignored for text
dumps so legacy microcompact chains cannot run on plain ``{role, content}`` rows.

Structured history (messages with ``tool_calls`` / ``tool_call_id``) still uses the
orchestrator path with the requested strategy. Prefer F1 directly for new L2 code.

| Concern | L2 (Host MC transcript) | L3 (HybridAgent tool loop) |
|---------|---------------------------|----------------------------|
| Input shape | `{role, content}` dict rows | `LLMMessage[]` with tool calls |
| Entry API | `compact_formatted_transcript()` | `maybe_compact_before_llm()` |
| Default chain | `("llm",)` only | Full policy chain from `CompressionPolicy` |
| Layer metadata (F2) | `layer=L2`, `formatted_transcript=True` | `layer=L3` |

## ContextEngine — `compress_on_append` + `compression_policy` (O8)

For Scholar / multi-task Phase 4 paths that append conversation turns outside the
HybridAgent tool loop:

```python
from aiecs.domain.context.context_engine import ContextEngine
from aiecs.domain.context.compression.policy import CompressionPolicy

policy = CompressionPolicy(
    enabled=True,
    context_window_tokens=200_000,
    chain=("microcompact", "collapse", "session_memory", "llm"),
)

engine = ContextEngine(
    llm_client=llm_client,
    compression_policy=policy,
    compress_on_append=True,
    hook_executor=hook_executor,
    progress_emitter=progress_emitter,
)

await engine.add_conversation_message(
    session_id,
    role="user",
    content="...",
    strategy="truncate",
)
```

When `compression_policy.enabled` or `compress_on_append=True`, legacy
`CompressionConfig.auto_compress_on_limit` (message count) delegates to token-based
`compress_on_append_if_needed` (O8). O8 passes F2 metadata with `layer=CE` to
PRE/POST compact hooks.

Summary message role follows `CompressionPolicy.summary_role` (default `"user"`).
Scholar hosts that relied on `"system"` summaries may pass
`compression_summary_role="system"` on `ContextEngine` construction.

## Fail-open (W8e) and F5 retry progress phases

L3 proactive compaction is **fail-open**: errors in `maybe_compact_before_llm` /
`auto_compact_if_needed` log and return the original messages rather than failing the
agent iteration.

Map progress phases to host SSE via `aiecs.host.compression.progress_bridge`:

```python
from aiecs.host.compression import (
    RETRY_COMPACT_PROGRESS_PHASES,
    compact_progress_event_to_sse_payload,
)

async for event in emitter.iter_compact_progress():
    if event.phase in RETRY_COMPACT_PROGRESS_PHASES:
        # compact_retry — recoverable LLM summarize failure
        # compact_retry_prompt_too_long — reactive PTL compact
        ...
    payload = compact_progress_event_to_sse_payload(event, session_id=session_id)
```

Standard phases include: `hooks_start`, `microcompact_*`, `context_collapse_*`,
`session_memory_*`, `compact_start`, `compact_done`, `compact_failed`,
`compact_retry`, `compact_retry_prompt_too_long`.

## HookPlugin bridge — when to enable

When HookPlugin is enabled on the agent, L3 compaction merges legacy compression
`HookExecutor` with hooks.json H3/H4 via a single bridge:

```python
from aiecs.domain.agent.plugins.hooks.bridge_compression import resolve_bridged_compression_hooks

hooks = resolve_bridged_compression_hooks(compression_hooks, plugin_ctx)
```

Enable the bridge when:

1. `HookPlugin` is registered and enabled (`plugin_ctx.get_plugin("hook")`), **and**
2. Either compression `HookExecutor` has pre/post hooks **or** hooks.json defines
   `pre_compact` / `post_compact`.

Block from either source skips compaction. H3/H4 payloads are **metadata pass-through**
— the bridge forwards `ctx.metadata` and does not synthesize F2 fields.

## F4 — mid-iteration batch end

`PluginPhase.ON_TOOL_BATCH_END` fires after each tool batch in HybridAgent. This is
**not** a hooks.json event. Custom plugins implement `on_tool_batch_end` for optional
mid-iteration compaction; the builtin turnkey runs **after** the plugin phase.

### GVR compression boundaries (A-10)

Long sub-goals inside one FC iteration can grow context before the next GVR goal
boundary. Use **two complementary strategies**:

| Boundary | Mechanism | When |
|----------|-----------|------|
| **GVR goal boundary (L1)** | Host `compact_formatted_transcript` / F1 on formatted history | Between goals, REFINE cycles, session checkpoints |
| **Tool-batch boundary (L2)** | `compact_after_tool_batch=true` + F4 turnkey | Mid-iteration after each tool batch in HybridAgent |

**Recommendation:** enable F4 for spawn-long-await or multi-batch sub-goals; keep F1 at
GVR boundaries for cross-goal continuity. Both can be active — F4 debounces against
proactive pre-LLM compact within the same iteration.

**GVR preservation:** microcompact skips tool results whose content references
`deliverable_refs`, `acceptance_criteria`, `criterion_id`, or `success_criteria` (see
`aiecs.domain.context.compression.gvr_preserve`). Criteria-related evidence MUST NOT
be cleared during mid-iteration compaction.

**F1 compatibility:** `compact_formatted_transcript` (F1) remains the host-facing L2
formatted-history path at GVR boundaries. F4 batch-end compaction uses the same
orchestrator chain (`maybe_compact_before_llm`) and respects the same GVR preservation
rules — F1 and F4 are complementary, not mutually exclusive.

### Turnkey batch-end compaction (G1)

Enable on agent bootstrap — host maps `AIECS_COMPACT_AFTER_TOOL_BATCH` to config:

```python
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.context.compression.policy import CompressionPolicy

config = AgentConfiguration(
    enable_context_compression=True,
    compact_after_tool_batch=True,
    compact_after_tool_batch_min_tokens=50_000,  # optional extra gate
)
```

**Plugin priority:** custom `on_tool_batch_end` plugins run in `ON_TOOL_BATCH_END`
phase first; builtin turnkey evaluates afterward via shared `ToolLoopCompressionContext`
and `maybe_compact_before_llm`. **Per-iteration debounce:** at the start of each tool-loop
iteration, `AutoCompactState.proactive_compact_used_this_iteration` is cleared; when
pre-LLM proactive compact succeeds, the flag is set so batch-end skips a second compact
in the same iteration (even if tool output pushes tokens back over threshold).

### Spawn-long-await scenario

Long-running tool batches inside one iteration (e.g. `spawn_subagent` blocking until
subagent completes) can grow context before the next MC recursive boundary. With
`compact_after_tool_batch=True`, HybridAgent compacts after each tool batch when no
proactive compact ran yet this iteration and token pressure exceeds policy threshold.

```python
config = AgentConfiguration(
    enable_context_compression=True,
    compact_after_tool_batch=True,
    compression_policy=CompressionPolicy(
        enabled=True,
        context_window_tokens=200_000,
        chain=("microcompact", "collapse", "session_memory", "llm"),
    ),
)
```

Custom plugin (optional — runs before builtin):

```python
async def on_tool_batch_end(self, ctx):
    messages = ctx.get("messages")
    # custom compact via maybe_compact_before_llm ...
```

## A5 — chunked LLM summarization (G7)

`CompressionPolicy.summary_chunk_size: int | None = None` (default `None`) preserves
2.1.0rc2 single-summarize behavior. When set (e.g. `131072` for long sessions), the
LLM compact step splits oversized older segments into token-bounded chunks, summarizes
each chunk, and merges into **one** summary message.

```python
from aiecs.domain.context.compression.policy import CompressionPolicy

policy = CompressionPolicy(
    enabled=True,
    chain=("microcompact", "collapse", "session_memory", "llm"),
    summary_chunk_size=131_072,
)
```

Relationship:

- **L2 F1:** llm-only path uses the orchestrator llm step → A5 applies automatically.
- **L3 orchestrator:** full chain llm step passes `summary_chunk_size` from policy.
- **ContextEngine:** `_compress_with_summarization` honors `compression_policy.summary_chunk_size`.
- **`None`:** backward compatible — single LLM summarize call (2.1.0rc2 behavior).

Long-session guidance: start with `131072` (128k tokens per chunk) on 200k+ context
windows; tune down if merge quality drops or up if PTL retries increase.

## Core APIs reference

### CompressionPolicy (O1)

```python
from aiecs.domain.context.compression.policy import CompressionPolicy
from aiecs.domain.agent.models import resolve_compression_policy

policy = resolve_compression_policy(agent_config)
```

### Proactive compact (O3)

```python
from aiecs.domain.context.compression.orchestrator import auto_compact_if_needed
from aiecs.domain.context.compression.state import AutoCompactState

messages, did_compact = await auto_compact_if_needed(
    messages,
    policy=policy,
    state=AutoCompactState(),
    llm_client=llm_client,
    session_id=session_id,
    hooks=hook_executor,
    progress=progress_emitter,
)
```

### L3 hot path

```python
from aiecs.domain.agent.tool_loop_core import maybe_compact_before_llm, ToolLoopCompressionContext

compacted = await maybe_compact_before_llm(messages, compression_ctx=ctx, plugin_ctx=plugin_ctx)
```

### F3 — CompressionPolicyResolver

```python
from dataclasses import replace

def resolver(*, layer: str, context, base_policy):
    if layer == "L2":
        return replace(base_policy, chain=("llm",))
    return base_policy

context["compression_policy_resolver"] = resolver
```

### F7 — token estimate (L1/L2)

```python
from aiecs.host.compression import estimate_transcript_tokens

estimated = estimate_transcript_tokens(formatted_history)
```

## Host ports (implement in production)

| Port | Purpose |
|------|---------|
| `ToolArtifactPort` | A9 offload storage (MinIO/S3) |
| `ToolBudgetStore` | A8 persistent budget map |
| `SessionMemoryPort` | A15 external session memory text |

NoOp defaults ship in aiecs; production hosts supply adapters (e.g.
`aiecs.host.compression.S3ToolArtifactPort`).

## Migration — integration layer deprecation (G6)

`ContextCompressor` emits :class:`DeprecationWarning` on construction; **removal
target: aiecs 2.2.0**. `CompressionStrategy` remains as a legacy enum alias mapping
to kernel truncation / LLM compact primitives.

New code should use:

- `auto_compact_if_needed` / `maybe_compact_before_llm` (L3)
- `compact_formatted_transcript` (L2 F1)
- ContextEngine `compress_on_append_if_needed` (CE / O8)

Avoid **new** internal imports of
`aiecs.domain.agent.integration.context_compressor` outside the integration module
and its re-export surfaces (`aiecs.domain.agent`, `aiecs.domain`).

## References

- Epic 1 algorithms: `issue_report/memory/AIECS_ISSUE_CONTEXT_COMPRESSION_ALGORITHMS.md`
- Epic 2 orchestration: `issue_report/memory/AIECS_ISSUE_CONTEXT_COMPRESSION_EPIC2_ORCHESTRATION.md`
- Epic 3 Host follow-up: `issue_report/agent/AIECS_ISSUE_CONTEXT_COMPRESSION_FOLLOWUP_HOST.md`
- Epic 4 polish: `issue_report/agent/AIECS_ISSUE_CONTEXT_COMPRESSION_EPIC4_POLISH.md`
- Hook + compression cross-ref: `issue_report/agent/AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md`
- python-middleware plan: [PLAN_AIECS_CONTEXT_COMPRESSION_ORCHESTRATION.md](https://github.com/Howmany-Zeta/python-middleware/blob/main/issue_report/agent/PLAN_AIECS_CONTEXT_COMPRESSION_ORCHESTRATION.md)

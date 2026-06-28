# Context compression — host integration guide (O10)

This document explains how **python-middleware** (and other hosts) integrate with
`aiecs.domain.context.compression` without duplicating OpenHarness `run_query` or
Claude Code UI/SSE layers.

## Layer model

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| **L1** | Host | Warning thresholds (70/80/90%), SSE `context_warning`, optional compact |
| **L2** | Host | Recursive task boundary compact, MC `formatted_history` adapters |
| **L3** | aiecs HybridAgent | Tool-loop offload (W11), proactive gate (O2/O3), reactive PTL (O5) |
| **Kernel** | aiecs | Algorithms W1–W12 (Epic 1) |
| **Orchestration** | aiecs | Policy, hooks, progress, `auto_compact_if_needed` (Epic 2) |

**Out of aiecs:** YAML config UI, SSE event names, i18n, GrowthBook flags.

## Core APIs

### CompressionPolicy (O1)

```python
from aiecs.domain.context.compression.policy import CompressionPolicy

policy = CompressionPolicy(
    enabled=True,
    context_window_tokens=200_000,
    buffer_tokens=13_000,
    preserve_recent=12,
    chain=("microcompact", "collapse", "session_memory", "llm"),
)
```

Map from `AgentConfiguration`:

| Host field | `CompressionPolicy` field |
|------------|---------------------------|
| `enable_context_compression` | `enabled` |
| `context_window_limit` | `context_window_tokens` |
| `compression_policy` (dict/dataclass) | full override (ADR-007) |

Use `resolve_compression_policy(agent_config)` in agent bootstrap.

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
    hooks=hook_executor,          # optional O6
    progress=progress_emitter,    # optional O7
    strategy=("microcompact",), # optional chain override
)
```

### Hooks (O6)

```python
from aiecs.domain.context.compression.hooks import HookEvent, HookExecutor, HookRegistry
from aiecs.domain.context.compression.types import PreCompactContext, PreCompactResult

registry = HookRegistry()

async def audit_pre(ctx: PreCompactContext) -> PreCompactResult:
    # block=True skips compact; append_instructions merges into LLM prompt
    return PreCompactResult(append_instructions="Preserve billing IDs.")

registry.register(HookEvent.PRE_COMPACT, audit_pre)
executor = HookExecutor(registry)
```

Post hooks receive `PostCompactContext(summary_text=..., result=CompactionResult)`.

### Progress (O7)

```python
from aiecs.domain.context.compression.progress import CompactProgressEmitter

def on_progress(event):
    # Host maps event.phase → SSE / logs
    ...

emitter = CompactProgressEmitter(on_progress=on_progress)

# Or async iterator:
async for event in emitter.iter_compact_progress():
    ...
```

Phases include: `hooks_start`, `microcompact_*`, `context_collapse_*`,
`session_memory_*`, `compact_start`, `compact_done`, `compact_failed`,
`compact_retry` (recoverable failure retry), and `compact_retry_prompt_too_long`
(reactive PTL compact). Map to SSE via
[`progress_bridge.py`](../../aiecs/host/compression/progress_bridge.py) (F5).

## Epic 3 — L2 vs L3 decision table (F1–F7)

| Concern | L2 (Host MC transcript) | L3 (HybridAgent tool loop) |
|---------|---------------------------|----------------------------|
| **Input shape** | `{role, content}` dict rows / formatted history | `LLMMessage[]` with tool calls |
| **Entry API** | `compact_formatted_transcript()` or `compact_at_mc_recursive_boundary()` | `maybe_compact_before_llm()` |
| **Default chain** | `("llm",)` only — **no microcompact/collapse** on text dumps | Full policy chain from `CompressionPolicy` |
| **Hook bridge** | Host injects `HookExecutor` / optional HookPlugin via context | Single entry: `bridge_compression` + hooks.json H3/H4 |
| **Layer metadata (F2)** | `layer=L2`, `formatted_transcript=True` | `layer=L3` |
| **Policy resolver (F3)** | `context["compression_policy_resolver"]` or `AgentConfiguration.compression_policy_resolver` | Same resolver; L3 wired in `_build_tool_loop_compression_context_async` |
| **Progress (F5)** | Pass `CompactProgressEmitter` to L2 adapters | HybridAgent `on_compact_progress` / emitter in compression context |
| **Token estimate (F7)** | `estimate_transcript_tokens(history)` for H3 `estimated_tokens` | `estimate_message_tokens(messages)` in L3 metadata |

**Do not** run the full L3 microcompact/collapse chain on formatted MC text dumps.
Use F1 for L2; use L3 only for ReAct tool-loop messages.

### F1 — formatted transcript compact

```python
from aiecs.host.compression import compact_formatted_transcript

rows, did = await compact_formatted_transcript(
    formatted_history,
    llm_client=llm_client,
    session_id=session_id,
    context=context,              # optional F3 resolver
    config=agent_configuration,   # optional F3 resolver
)
```

Prefer this over `compact_at_mc_recursive_boundary(..., strategy="summarize")` when
you need guaranteed llm-only L2 semantics (F1-04).

### F3 — CompressionPolicyResolver

```python
def resolver(*, layer: str, context, base_policy: CompressionPolicy) -> CompressionPolicy:
    if layer == "L2":
        return replace(base_policy, chain=("llm",))
    return base_policy

context["compression_policy_resolver"] = resolver
# or AgentConfiguration(compression_policy_resolver=resolver)
```

### HookPlugin bridge — single H3/H4 entry (§6.7.1)

When HookPlugin is enabled, L3 compaction uses `bridge_compression.py` only:

1. Compression `HookExecutor` pre/post (legacy context inject)
2. hooks.json `pre_compact` / `post_compact` via `AgentHookExecutor`

Block from either source skips compaction. H3/H4 payloads are **metadata pass-through**:
`bridge_compression.py` maps `ctx.metadata` into hook payloads and does not synthesize F2
fields. L3 HybridAgent supplies metadata via `tool_loop_core` → `build_pre_compact_metadata`.
See [HOOKS.md](./DOMAIN_AGENT/HOOKS.md) (v2 compression metadata — H3/H4 payload pass-through).

### F4 — mid-iteration batch end (plugins only)

`PluginPhase.ON_TOOL_BATCH_END` fires after each tool batch in HybridAgent; this is
**not** a hooks.json event. Implement `on_tool_batch_end` on custom plugins for
optional mid-iteration compaction.

### ContextEngine compress-on-append (O8)

```python
from aiecs.domain.context.context_engine import ContextEngine

engine = ContextEngine(
    llm_client=llm_client,
    compression_policy=policy,
    compress_on_append=True,
    hook_executor=executor,
    progress_emitter=emitter,
)

await engine.add_conversation_message(
    session_id,
    role="user",
    content="...",
    strategy="truncate",  # optional; maps to chain via resolve_compact_chain
)
```

Legacy `CompressionConfig.auto_compress_on_limit` (message count) still works when
`compress_on_append` and `compression_policy` are disabled. When policy is enabled,
`auto_compress_on_limit` delegates to token-based `compress_on_append_if_needed`.

### MemoryPlugin (O8 path)

When `AgentConfiguration.enable_context_compression` or `compression_policy` is set,
`MemoryPlugin.on_post_task` calls `ContextEngine.compress_on_append_if_needed` with
`strategy=policy.chain` after persisting turns.

## Host mapping examples

### L1 — warning only

Host calls `should_compress(messages, policy)` for threshold checks; emit SSE without
calling `auto_compact_if_needed` unless product policy allows L1 compact.

### L2 — recursive boundary

Host converts dict history → `LLMMessage` list, calls `auto_compact_if_needed` with
MC-only chain at recursive boundaries; does not duplicate HybridAgent O3 gate.

### L3 — agent loop

HybridAgent uses `maybe_compact_before_llm` → `auto_compact_if_needed` (M3 GA).
Host may subscribe to `CompactProgressEmitter` and forward phases to SSE.

## Ports (host implements)

| Port | Purpose |
|------|---------|
| `ToolArtifactPort` | A9 offload storage (MinIO/S3) |
| `ToolBudgetStore` | A8 persistent budget map |
| `SessionMemoryPort` | A15 external session memory text |

NoOp defaults ship in aiecs; production hosts supply adapters.

## References

- Epic 1 algorithms: `issue_report/memory/AIECS_ISSUE_CONTEXT_COMPRESSION_ALGORITHMS.md`
- Epic 2 orchestration: `issue_report/memory/AIECS_ISSUE_CONTEXT_COMPRESSION_EPIC2_ORCHESTRATION.md`
- Epic 3 Host follow-up: `issue_report/agent/AIECS_ISSUE_CONTEXT_COMPRESSION_FOLLOWUP_HOST.md`
- Hook + compression cross-ref: `issue_report/agent/AIECS_HOOK_COMPRESSION_EPIC3_CROSSREF.md`
- Agent hook v2: [HOOKS.md](./DOMAIN_AGENT/HOOKS.md)
- **M4 host migration (CC-091–105):** [HOST_MIGRATION_M4.md](./HOST_MIGRATION_M4.md)
- Deprecation plan: `issue_report/memory/HOST_GENERAL_COMPRESSION_DEPRECATION.md`
- ADRs: `issue_report/memory/adr.md`

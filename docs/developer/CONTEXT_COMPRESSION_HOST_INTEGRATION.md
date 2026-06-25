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
`session_memory_*`, `compact_start`, `compact_done`, `compact_failed`.

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
- **M4 host migration (CC-091–105):** [HOST_MIGRATION_M4.md](./HOST_MIGRATION_M4.md)
- Deprecation plan: `issue_report/memory/HOST_GENERAL_COMPRESSION_DEPRECATION.md`
- ADRs: `issue_report/memory/adr.md`

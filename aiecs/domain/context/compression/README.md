# Context compression kernel (M1–M2)

`aiecs.domain.context.compression` is the shared algorithm kernel for ContextEngine,
integration `ContextCompressor`, and HybridAgent tool-loop compression.

## Milestone scope

| Milestone | Tasks | Delivered |
|-----------|-------|-----------|
| **M1 alpha** | CC-001 – CC-055 | Kernel primitives W1–W12, CE/integration delegation |
| **M2 rc1** | CC-056 – CC-072 | W11 tool budget + HybridAgent hot path (W8 inline gate) |
| **M3 GA** | CC-073 – CC-090 | Epic 2 orchestrator (O3), hooks, `compress_on_append` |

M2 uses **inline** `should_compress_messages` in `tool_loop_core.maybe_compact_before_llm`.
M3 replaces that gate with `CompressionPolicy` + `auto_compact_if_needed` (O3).
M3 GA adds hooks (O6), progress (O7), public `CompactionResult` (O9), and ContextEngine `compress_on_append` (O8).

## Algorithm coverage (A1–A23)

| ID | Algorithm | Module | M1 | M2 | Notes |
|----|-----------|--------|:--:|:--:|-------|
| A1 | Token estimate | `tokens.py` | ✅ | ✅ | Block-level; shared gate |
| A2 | Tail keep / drop head | `truncation.py` / CE | ✅ | ✅ | CE `_compress_with_truncation` |
| A3 | Earlier placeholder | `truncation.py` | ✅ | ✅ | general golden semantics |
| A4 | LLM summary compact | `llm_compact.py` | ✅ | ✅ | HybridAgent via chain |
| A5 | Chunked LLM summary | — | ❌ | ❌ | Optional Phase 7 |
| A6 | Semantic dedup | CE only | ✅ | ✅ | **aiecs extension** (ADR-005) |
| A7 | Microcompact | `microcompact.py` | ✅ | ✅ | Compact chain step 1 |
| A8 | Tool result budget | `tool_budget.py` | ❌ | ✅ | `InMemoryToolBudgetStore` |
| A9 | Tool output offload | `tool_budget.py` | ❌ | ✅ | `ToolArtifactPort` |
| A10 | Context collapse | `collapse.py` | ✅ | ✅ | Chain step 2 |
| A11 | PTL head-drop | `ptl.py` | ✅ | ✅ | LLM compact retry |
| A12 | Truncate middle | `truncation.py` | ✅ | ✅ | integration delegate |
| A13 | Token budget from tail | `truncation.py` | ✅ | ✅ | preserve_recent |
| A14 | Deterministic summary | `legacy.py` | ✅ | ✅ | Session memory fallback |
| A15 | Session memory compact | `session_memory.py` | ✅ | ✅ | Chain step 3 |
| A16 | API context_management | — | ❌ | ❌ | Provider-specific |
| A17 | cache_edits | — | ❌ | ❌ | Anthropic-only |
| A18 | Boundary / snip view | — | ❌ | ❌ | REPL product feature |
| A19 | Image placeholders | `images.py` | ✅ | ✅ | Pre-LLM compact input |
| A20 | Multi-section dict | host | ❌ | ❌ | python-middleware general |
| A21 | Char hard truncate | integration | ✅ | ✅ | `compress_text` |
| A22 | Tool pair safe split | `pairs.py` | ✅ | ✅ | Required before any head drop |
| A23 | Hybrid multi-strategy | CE only | ✅ | ✅ | **aiecs extension** (ADR-005) |

## HybridAgent hot path (ADR-009)

```
execute tool → apply_tool_output_management (W11 A9 offload)
→ append preview tool_result
→ maybe_compact_before_llm (A8 budget + W8 gate + compact chain)
→ generate_text / stream_text
```

Implementation: `aiecs/domain/agent/tool_loop_core.py` — HybridAgent delegates; no duplicate logic in `hybrid_agent.py`.

## Ports (ADR-002)

| Port | Default | Host injects |
|------|---------|--------------|
| `ToolArtifactPort` | NoOp (inline preview only) | MinIO / S3 |
| `ToolBudgetStore` | NoOp | Redis / PG (M3+) |
| `SessionMemoryPort` | NoOp | Disk summary source |

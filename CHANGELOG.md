# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also `docs/changelog.rst` for historical release notes.

## [Unreleased]


## [2.1.0rc5] - 2026-07-02 (Pre-release)

### GVR — Consumer API / Contract (M-8)

- **`aiecs/docs/gvr_consumer_api.md`:** GVR-facing symbol list, semver policy, breaking-change review process, ADR-018 adoption matrix (A/B/C).
- **`aiecs/docs/migration_2.1.0rc4_to_ga.md`:** Upgrade guide for python-middleware GVR integrators.
- **`tests/contract/test_aiecs_gvr_surface.py`:** Baseline (rc4) + GA-target contract tiers; CI contract job.
- **`tests/fixtures/gvr_verdict_v1.json`:** Shared Verdict JSON Schema skeleton (co-owned with host `work_state.Verdict`).

### GVR — Verdict / Verification (A-1, A-2, A-4, A-5, A-11)

- **`aiecs.domain.agent.verification`:** `Verdict`, `FeedbackItem`, `EvidenceItem`, `AcceptanceCriterion`, `VerificationContext`, `Verifier` protocol, `normalize_acceptance_criteria`, `ReadOnlyAdversarialVerifier` example.
- **`HybridAgent.verify()` / `register_verifier()`:** optional L1/L2 verification hook (defaults off when not invoked).
- **`aiecs/docs/gvr_verdict_field_mapping.md`:** 1:1 mapping to python-middleware `work_state.Verdict`.
- **`aiecs.domain.agent.verification.gates`:** `GateRegistry`, `SpecGate`, `CitationUrlGate`, `gate_aggregate_to_verdict`; config via `deterministic_gates`.
- **`aiecs/docs/gvr_gate_semantics.md`:** aggregate score + skip_threshold (OpenDraft ≥85).
- **`VerificationPolicy` / `run_gvr_pre_exit`:** engine verify-fix loop with `VerificationExhausted` at max refines.
- **`PeerReviewPolicy` / `request_peer_review` → `Verdict`:** QUICK-path mini-Verdict (≥5 criteria blocked).
- **`CweVerifier` / `review_refinement` template (A-11):** sequential fact→style H1 multi-perspective verifier; `cwe_verifier.enabled` default off.

### GVR — HookPlugin blocking (A-8)

- Hook JSON schema: `{action, feedback, feedback_items}` on `TASK_COMPLETED` / `STOP`.
- In-loop pre-exit `TASK_COMPLETED` + gate fail injects data-only user message and continues FC loop.
- Enriched hook payload: `goal_id`, `gate_scores`, `failed_criteria`.

### GVR — GoalGraph (A-3)

- **`AgentGoal` GVR extensions:** `verdict_history`, `origin`, `id`/`parent_id` read aliases; union `success_criteria`.
- **`GoalGraph` API:** `add_goal`, `close_goal`, `next_open_goal`, `spawn_subgoals`, `decompose` (host `decomposer=` only).
- **`aiecs/docs/gvr_goal_graph_mapping.md`:** WorkState / GoalNode field mapping.

### GVR — Loop detection (A-7)

- **`LoopDetectionService` / `LoopSignal`:** sliding-window triple repeat detection; optional `ON_LOOP_DETECTED` hook.
- **`aiecs/docs/gvr_loop_detection.md`:** hybrid use with host EC=0 rules.

### GVR — DAWPResult (A-6)

- **`DAWPResult`:** structured terminal handoff (`status`, `deliverable_refs`, `criteria_progress`, …).
- **`dawp_emit_structured_result`:** opt-in streaming terminal event; partial/failed does not silent-pass.
- **`aiecs/docs/gvr_dawp_result.md`:** L2 prompt-chain handoff; host adapter sample.

### GVR — Recovery (A-9)

- **`RecoveryResult` / `execute_with_recovery_streaming`:** structured recovery outcomes.
- **ABORT + `VerificationExhausted`:** propagates to host ESCALATE contract.
- **`aiecs/docs/gvr_recovery_semantics.md`:** strategy semantics for streaming paths.

### GVR — Compression (A-10)

- **GVR preservation in microcompact:** `gvr_preserve` skips tool results referencing `deliverable_refs` / acceptance criteria.
- **Docs:** GVR goal-boundary (F1) vs tool-batch-boundary (F4) strategy in `context_compression_integration.md`.
- **F4 + F1 compatibility:** mid-iteration `compact_after_tool_batch` complements boundary F1 compaction.


## [2.1.0rc4] - 2026-06-29 (Pre-release)

## [2.1.0rc3] - 2026-06-28 (Pre-release)

### Added

- **Epic 4 context compression polish (G1–G7):** F4 turnkey `AgentConfiguration.compact_after_tool_batch` + batch-end compaction in HybridAgent; F6 host integration guide packaged in wheel (`aiecs/docs/host/context_compression_integration.md`); G3 legacy L2 adapter redirect to F1; G4 ContextEngine O8 `layer=CE` metadata and `CompressionPolicy.summary_role`; G5 `estimate_transcript_tokens` re-export from `aiecs.host.compression`; **G7 A5** `CompressionPolicy.summary_chunk_size` chunked LLM summarization.

### Changed

- **`compact_at_mc_recursive_boundary`:** formatted transcript text dumps delegate to F1 (no legacy microcompact on `strategy="summarize"`).
- **`ContextEngine`:** O8 compact passes F2 `layer=CE` metadata; summarization honors `CompressionPolicy.summary_role` (default `"user"`) with optional `compression_summary_role` override.

### Deprecated

- **`integration.ContextCompressor`:** emits `DeprecationWarning` on construction; removal planned for **2.2.0**. Use orchestrator / host compression APIs documented in `aiecs/docs/host/context_compression_integration.md`.


## [2.1.0rc2] - 2026-06-28 (Pre-release)

### Added

- **Agent HookPlugin v2 (V2.0–V2.1):** `permission_checker` protocol, `permission_request` / `permission_denied` (H22), `post_tool_use_failure`, PreToolUse `updated_input` / `permissionDecision`, MCP H2 `updated_mcp_output`; hooks.json `notification` executable when `HookPlugin.options.enable_v2_hooks=true`.
- **Hook lifecycle v2.1:** H5b `user_prompt_in_history`, H5/H5b `continue:false` task rejection, H6 `preventContinuation`, `subagent_start`, enriched `dawp_run_end`, `stop_failure`, `task_completed`; session hooks include Host `session_id` / `reason`.
- **Plugin phase `ON_TOOL_BATCH_END`:** fires after each tool batch in HybridAgent (plugin extension only, not hooks.json).
- **Compression Epic 3 (F1–F7):** `compact_formatted_transcript` (L2), F2 layer metadata on H3/H4, `CompressionPolicyResolver` (L2/L3), `compact_retry` / `compact_retry_prompt_too_long` progress phases, `estimate_transcript_tokens`, Host SSE mapping in `progress_bridge.py`; extended [CONTEXT_COMPRESSION_HOST_INTEGRATION.md](docs/developer/CONTEXT_COMPRESSION_HOST_INTEGRATION.md).
- **Agent HookPlugin (H0–H4):** `hook@builtin` declarative hooks (`hooks.json` subset), unified `dispatch_agent_hook` / `dispatch_tool_with_hooks`, compression bridge (H3/H4), loop/task boundary hooks (H5–H21), DAWP run hooks (H16/H17).
- **Host hook migration (H4):** `aiecs.host.hooks` SSE payload bridge, `examples/host_hooks/`, `docs/developer/HOST_MIGRATION_HOOKS.md`.

### Changed

- **HybridAgent task kernel order:** H5 → `PRE_TASK` → `BUILD_MESSAGES` → H5b → `PRE_MAIN_LOOP` (sync + streaming).
- **H3/H4 hook payloads:** include `layer`, `formatted_transcript`, `estimated_tokens` when F2/F7 metadata present.


## [2.1.0rc1] - 2026-06-27 (Pre-release)

### Removed

- **`aiecs.tools.docs`**: built-in document tools (parser, creator, writer, layout, content insertion, AI orchestrators, PPT). Migrated to MCP server services; source snapshot at `test/archived/mcp_migration_2026/aiecs_tools_docs/`. Tests/examples archived under `test/archived/mcp_migration_2026/` and `examples/archived/mcp_migration_2026/`.

### Added

- **`aiecs.domain.context.compression`** (Phase 0 / M1 alpha in development): constants, `ContentBlock` model, Port + NoOp stubs, and LLMMessage / ConversationMessage adapters (ADR-011 foundation)
- **Phase 1 compression kernel primitives (W1–W4, W10):** `split_preserving_tool_pairs`, `sanitize_messages_for_compaction`, `microcompact_messages`, `try_context_collapse`, `truncate_head_for_ptl_retry`, `replace_images_for_compaction`
- **Phase 2 summarization chain (W5–W7, W9):** `compact_conversation`, `try_session_memory_compaction`, legacy `compact_messages`, internal `build_post_compact_messages`; `ContextEngine` / `integration.ContextCompressor` delegate to kernel (M1 alpha scope)
- **Phase 3 token/truncation unification (W8a, W12):** `estimate_message_tokens`, `should_compress_messages`, `compress_with_earlier_placeholder`, `truncate_middle`; full `integration.ContextCompressor` + ContextEngine truncate delegation (M1 boundary CC-001–CC-055)
- **Phase 3.5 tool output management (W11):** `offload_tool_output_if_needed` (A9), `enforce_tool_result_budget` (A8), `ToolArtifactPort` / `InMemoryToolBudgetStore` with NoOp defaults (M2 scope CC-056–CC-062)
- **Phase 4 HybridAgent compression (W8/W11, M2 rc1):** `CompressionPolicy`, `resolve_compression_policy`, `tool_loop_core` hooks (`apply_tool_output_management`, `maybe_compact_before_llm`), HybridAgent hot-path delegation (CC-063–CC-072). W8b gate is inline until M3 O3 orchestrator.
- **Phase 5 Epic 2 orchestrator (O1–O5, M3 prep):** `should_compress`, `AutoCompactState`, `auto_compact_if_needed`, `on_prompt_too_long`; `maybe_compact_before_llm` delegates to O3 (CC-073–CC-077).
- **Phase 6 Epic 2 GA (O6–O10, M3 / 2.1.0):** `HookRegistry` / `HookExecutor` (PRE/POST compact), `CompactProgressEvent` + callback/async iterator, public `CompactionResult` exports, ContextEngine `compress_on_append` with token policy and strategy override, MemoryPlugin O8 wiring, host integration guide (CC-083–CC-090).
- **Phase 7 host migration helpers (M4, CC-091–095 in aiecs):** `aiecs.host.compression` (S3 `ToolArtifactPort`, SSE payload bridge, L2 MC adapter, `USE_AIECS_COMPRESSION`), `examples/host_compression/`, `scripts/validate_l3_compression_e2e.py`, `docs/developer/HOST_MIGRATION_M4.md`.


## [2.1.0] - 2026-06-25

### Added

- Context compression Epic 2 observability and host integration (O6–O10): hooks, progress events, `compress_on_append`, public `CompactionResult`, `docs/developer/CONTEXT_COMPRESSION_HOST_INTEGRATION.md`

### Changed

- `ContextEngine.auto_compress_on_limit` delegates to token-based `compress_on_append_if_needed` when `compression_policy` is enabled (legacy message-count path preserved when policy is off)
- `maybe_compact_before_llm` uses shared O3 orchestrator (no duplicate inline gate at M3 GA)


## [2.0.0rc2] - 2026-06-10 (Pre-release)

### Fixed

- **temporal-graphiti:** Relax `openai` pin for `graphiti-core` compatibility; Vertex-first LLM/embedder for L1 Graphiti
- Add `temporal-graphiti-neo4j` optional extra for Neo4j-only installs

### Added

- **L1 temporal memory (Phase 0–2):** `TemporalMemoryStore` Port, `TemporalMemoryEngine`, `create_temporal_memory_store()`, `NoOpTemporalMemoryStore`, optional `GraphitiTemporalMemoryStore` (`TM_BACKEND=graphiti`)
- **`temporal_memory@builtin` plugin** (`TemporalMemoryPlugin`, priority 85, default disabled) — PRE_TASK search, POST_TASK ingest after `memory` (80), optional fact injection in BUILD_MESSAGES
- **Settings:** `TM_ENABLED`, `TM_BACKEND`, `TM_GRAPH_BACKEND`, FalkorDB/Neo4j URLs, `TM_INGEST_ASYNC`, `TM_SEARCH_LIMIT`, `TM_GROUP_ID_PREFIX`; `AgentConfiguration.temporal_memory_enabled`
- **Optional extra:** `pip install aiecs[temporal-graphiti]` (customer-side `graphiti-core`; not in core wheel per ADR-003)
- **Docs / example:** [docs/developer/DOMAIN_TEMPORAL_MEMORY.md](docs/developer/DOMAIN_TEMPORAL_MEMORY.md), [examples/temporal_memory/](examples/temporal_memory/)


## [2.0.0rc1] - 2026-06-07 (Pre-release)

> **Release Candidate 1** for the upcoming **2.0.0** breaking release. This
> pre-release build is intended for early adopters and integration testing; the
> stable **2.0.0** final will follow after validation.

### Removed
- Embedded knowledge graph implementation (use **private** `aiecs-kg` if licensed)
- Built-in tools: apisource, scraper_tool, statistics, knowledge_graph tools
- `KnowledgeAwareAgent`, `GraphAwareAgentMixin`, `GraphMemoryMixin`

### Migration
- L2: customer installs private `aiecs-kg`, `KG_ENABLED=true`, `KnowledgePlugin`
- Agents: `HybridAgent` + knowledge plugin
- Tools: fork removed modules or custom `BaseTool`
- AIECS does **not** ship or test private KG

### AIECS Core slimdown — deprecated module freeze (Phase 0)

Per [ADR-002](issue_report/new_function_request/temporal_kg_memory/adr/ADR-002-aiecs-tools-module-deprecation.md) and [AIECS_SLIMDOWN_EXECUTION_PLAN.md](issue_report/new_function_request/temporal_kg_memory/AIECS_SLIMDOWN_EXECUTION_PLAN.md):

**No new features** may be added to the following modules until they are removed in **2.0.0** (Phase 4):

| Area | Paths |
|------|--------|
| KG tools | `aiecs/tools/knowledge_graph/` |
| APIs | `aiecs/tools/apisource/` |
| Scraper | `aiecs/tools/scraper_tool/` |
| Statistics | `aiecs/tools/statistics/` |
| Agents | `aiecs/domain/agent/knowledge_aware_agent.py`, `aiecs/domain/agent/graph_aware_mixin.py` |

Bug fixes and security patches only. Phase 1–3 are non-breaking; Phase 4 (**2.0.0**) will physically delete these surfaces.

**Version plan:** Phase 1–3 = minor; Phase 4 = **2.0.0** breaking. Phase 3 monorepo KG deletion does **not** wait on private `aiecs-kg` ([ADR-003](issue_report/new_function_request/temporal_kg_memory/adr/ADR-003-aiecs-kg-private-independent.md)).

### Deprecated (Phase 1 — removal in 2.0.0)

Importing or instantiating these surfaces emits `DeprecationWarning` until Phase 4 deletion:

| Symbol / path | Replacement |
|---------------|-------------|
| `aiecs.tools.apisource` | Fork or custom `BaseTool` |
| `aiecs.tools.scraper_tool` | Fork or custom `BaseTool` |
| `aiecs.tools.statistics` | Fork or custom `BaseTool` |
| `aiecs.tools.knowledge_graph` (`kg_builder`, `graph_search`, `graph_reasoning`) | Customer-built KG tools + `KnowledgePlugin` (ADR-001) |
| `KnowledgeAwareAgent` | `HybridAgent` + `knowledge@builtin` |
| `GraphAwareAgentMixin` | `KnowledgePlugin` |

**Tool auto-discovery allowlist:** `task_tools`, `search_tool` only (`aiecs/tools/__init__.py`).

### Added (Phase 2 — L2 integration shell)

- `aiecs/infrastructure/knowledge/`: `GraphStoreProtocol`, `NoOpGraphStore`, `create_graph_store()` / `resolve_kg_enabled()`
- `Settings`: `KG_ENABLED` (default `false`), `KG_BACKEND_MODULE` (default `aiecs_kg`)
- `KnowledgePlugin.on_agent_init` wires graph store via factory; `derive_default_plugins` enables `knowledge@builtin` only for non-NoOp stores

# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

See also `docs/changelog.rst` for historical release notes.

## [Unreleased]

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

**Tool auto-discovery allowlist:** `task_tools`, `docs`, `search_tool` only (`aiecs/tools/__init__.py`).

### Added (Phase 2 — L2 integration shell)

- `aiecs/infrastructure/knowledge/`: `GraphStoreProtocol`, `NoOpGraphStore`, `create_graph_store()` / `resolve_kg_enabled()`
- `Settings`: `KG_ENABLED` (default `false`), `KG_BACKEND_MODULE` (default `aiecs_kg`)
- `KnowledgePlugin.on_agent_init` wires graph store via factory; `derive_default_plugins` enables `knowledge@builtin` only for non-NoOp stores

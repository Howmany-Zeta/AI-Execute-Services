# Temporal Memory (L1)

Developer guide for AIECS **L1 temporal memory**: episodic ingest, fact search, and the `temporal_memory@builtin` plugin.

**Status:** L1 MVP (Phase 0–2) — Port, Engine, optional Graphiti backend, `TemporalMemoryPlugin`.

**Related:**

- [TEMPORAL_KG_MEMORY_INDEX.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_INDEX.md)
- [TEMPORAL_KG_MEMORY_DESIGN.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_DESIGN.md)
- [DOMAIN_CONTEXT.md](./DOMAIN_CONTEXT.md) — L0/L1 episode_bridge sequence
- [MIGRATION_GRAPH_MEMORY_TO_L1.md](./MIGRATION_GRAPH_MEMORY_TO_L1.md) — GraphMemoryMixin → L1
- [PLUGIN_SYSTEM.md](./DOMAIN_AGENT/PLUGIN_SYSTEM.md) — plugin phases and POST_TASK ordering
- [ADR-003](../../issue_report/new_function_request/temporal_kg_memory/adr/ADR-003-aiecs-kg-private-independent.md) — L2 private KG is customer-side; L1 is independent

---

## 1. L0 / L1 / L2 responsibilities

| Layer | Mechanism | Storage | Optional dependency |
|-------|-----------|---------|---------------------|
| **L0** | `memory@builtin` (`MemoryPlugin`) | In-process / session memory on the agent | None (core) |
| **L1** | `temporal_memory@builtin` (`TemporalMemoryPlugin`) | `TemporalMemoryStore` Port → Graphiti or NoOp | Customer installs `graphiti-core` (see §3) |
| **L2** | `knowledge@builtin` (`KnowledgePlugin`) | `GraphStore` via `create_graph_store()` | Customer private `aiecs-kg` module (ADR-003) |

L1 and L2 are **separate**: temporal facts (time-valid episodes) are not merged into L2 `GraphStore`. Phase 3 `UnifiedMemoryRetriever` (not in L1 MVP) will combine retrieval only.

**Boundaries (ADR-003):**

- AIECS **core wheel** does not bundle `graphiti-core` or proprietary KG packages.
- Domain and agent layers must not `import graphiti_core`; only `aiecs/infrastructure/temporal_memory/graphiti/` may lazy-import Graphiti.
- Do not use `pip install aiecs[knowledge-graph]` as an official install path (removed in 2.0 slimdown).

---

## 2. Architecture

```
HybridAgent
  └─ TemporalMemoryPlugin (priority 85, default_enabled=false)
        └─ TemporalMemoryEngine
              └─ create_temporal_memory_store(Settings)
                    ├─ NoOpTemporalMemoryStore     [TM_ENABLED=false or TM_BACKEND=none]
                    └─ GraphitiTemporalMemoryStore [TM_BACKEND=graphiti + optional install]
```

| Path | Role |
|------|------|
| `aiecs/domain/temporal_memory/` | Port (`TemporalMemoryStore`), `TemporalMemoryEngine`, models, `group_id` |
| `aiecs/infrastructure/temporal_memory/` | `create_temporal_memory_store()`, `NoOpTemporalMemoryStore`, `graphiti/` adapter |
| `aiecs/domain/agent/plugins/builtin/temporal_memory_plugin.py` | Lifecycle hooks (no Graphiti imports) |

---

## 3. Installation matrix

| Profile | AIECS install | Temporal memory | Graph backend |
|---------|---------------|-----------------|----------------|
| **core** | `pip install aiecs` | Off — `TM_ENABLED=false` or unset, `TM_BACKEND=none` | N/A |
| **+ Graphiti (L1)** | `pip install aiecs` + customer optional extra below | On — `TM_ENABLED=true`, `TM_BACKEND=graphiti` | FalkorDB (default) or Neo4j |

**Customer-side Graphiti install (choose one):**

```bash
# Recommended: AIECS optional extra (wraps graphiti-core[falkordb])
pip install "aiecs[temporal-graphiti]"

# Or install Graphiti directly (same dependency, no AIECS extra)
pip install "graphiti-core[falkordb]"
```

Run FalkorDB (or configure Neo4j) per [Graphiti](https://github.com/getzep/graphiti) documentation. AIECS open-source CI does **not** require Graphiti; integration tests use `pytest -m graphiti` and skip without `TM_FALKORDB_URL`.

**L2 (independent):** private knowledge graph via `KG_ENABLED=true` and `KG_BACKEND_MODULE` — see [PLUGIN_SYSTEM.md §7](./DOMAIN_AGENT/PLUGIN_SYSTEM.md#7-knowledge-graph-migration-20).

---

## 4. Configuration (`TM_*`)

Settings live in `aiecs/config/config.py` (env aliases in `.env.example`).

| Field | Env | Default | Description |
|-------|-----|---------|-------------|
| `tm_enabled` | `TM_ENABLED` | `false` | Master switch; when false, factory returns `NoOpTemporalMemoryStore` |
| `tm_backend` | `TM_BACKEND` | `none` | `none` \| `graphiti` \| `postgres` (`postgres` = Phase 5 stub) |
| `tm_graph_backend` | `TM_GRAPH_BACKEND` | `falkordb` | Graphiti driver: `falkordb` \| `neo4j` |
| `tm_falkordb_url` | `TM_FALKORDB_URL` | `redis://localhost:6379` | FalkorDB URL when `TM_GRAPH_BACKEND=falkordb` |
| `tm_neo4j_uri` | `TM_NEO4J_URI` | `""` | Neo4j bolt URI |
| `tm_neo4j_user` | `TM_NEO4J_USER` | `""` | Neo4j user |
| `tm_neo4j_password` | `TM_NEO4J_PASSWORD` | `""` | Neo4j password |
| `tm_ingest_async` | `TM_INGEST_ASYNC` | `true` | POST_TASK ingest via background asyncio queue |
| `tm_store_raw_episode` | `TM_STORE_RAW_EPISODE` | `false` | Persist raw episode text in Graphiti (PII caution) |
| `tm_search_limit` | `TM_SEARCH_LIMIT` | `10` | Default fact search limit |
| `tm_group_id_prefix` | `TM_GROUP_ID_PREFIX` | `aiecs` | Namespace prefix for Graphiti `group_id` values |
| `tm_search_primary_group_only` | `TM_SEARCH_PRIMARY_GROUP_ONLY` | `false` | Search only primary session `group_id` |
| `tm_ingest_all_group_ids` | `TM_INGEST_ALL_GROUP_IDS` | `false` | Ingest episode into every resolved `group_id` |
| `tm_search_cache_enabled` | `TM_SEARCH_CACHE_ENABLED` | `true` | In-process TTL cache for search |
| `tm_search_cache_ttl_seconds` | `TM_SEARCH_CACHE_TTL_SECONDS` | `30` | Search cache TTL (seconds) |
| `tm_search_cache_max_size` | `TM_SEARCH_CACHE_MAX_SIZE` | `256` | Search cache max entries |
| `tm_episode_body_max_chars` | `TM_EPISODE_BODY_MAX_CHARS` | `4000` | Max episode body length before ingest |

**Agent configuration:**

| Field | Default | Description |
|-------|---------|-------------|
| `temporal_memory_enabled` | `false` | Request L1 plugin wiring on the agent |

Plugin **derive** enables `temporal_memory@builtin` only when `temporal_memory_enabled=true` **and** `create_temporal_memory_store()` is not `NoOpTemporalMemoryStore`.

**Both are required** (common misconfiguration):

| `temporal_memory_enabled` | `TM_ENABLED` + Graphiti store | Result |
|---------------------------|-------------------------------|--------|
| `false` | any | Plugin disabled (debug log); env alone is insufficient |
| `true` | `false` / NoOp | Derive + `on_agent_init` disable (NoOp store) |
| `true` | `true` + graphiti installed | L1 active |

Tests: `test_temporal_memory_enable_conditions.py`.

**Minimal Graphiti env example:**

```bash
TM_ENABLED=true
TM_BACKEND=graphiti
TM_GRAPH_BACKEND=falkordb
TM_FALKORDB_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...   # Graphiti extraction may use OpenAI via aiecs LLM adapter
```

---

## 5. TemporalMemoryPlugin lifecycle

| Phase | Hook | Behavior |
|-------|------|----------|
| `AGENT_INIT` | `on_agent_init` | `create_temporal_memory_store()` → `TemporalMemoryEngine`; NoOp → disable plugin |
| `PRE_TASK` | `on_pre_task` | `search_facts` → `plugin_state["temporal_memory.facts"]` |
| `BUILD_MESSAGES` | `on_build_messages` | Optional inject `TEMPORAL MEMORY FACTS:` block (`inject_facts`, default true) |
| `POST_TASK` | `on_post_task` | Ingest episode from task result (**after** `memory@builtin`, priority 80 → 85); write ingest `plugin_state` keys (§5.1) |
| `AGENT_SHUTDOWN` | `on_agent_shutdown` | `store.close()`; release ingest queue refcount if `TM_INGEST_ASYNC` (worker stops only when no agents hold the queue) |

**POST_TASK order:** `memory` (80) persists L0 session memory first; `temporal_memory` (85) ingests the completed turn into the graph backend.

**Async ingest (`TM_INGEST_ASYNC`):** the plugin enqueues `TemporalMemoryEngine.ingest_from_task` on a process-wide worker. Refcounted `acquire` / `release` allows multiple agents per process; shutting down one agent does not stop the queue while others are active. The engine always calls `ingest_episode` (sync Port); store-level `ingest_episode_async` schedules Graphiti I/O on the event loop when invoked directly.

### 5.1 `plugin_state` keys (L1 / L2 boundary)

| Key | Writer | Consumers |
|-----|--------|-----------|
| `temporal_memory.facts` | `TemporalMemoryPlugin` `PRE_TASK` | `on_build_messages`; custom reasoning plugins |
| `temporal_memory.ingest_job_id` | `TemporalMemoryPlugin` `POST_TASK` | Phase 4 `MemoryPlugin` metadata (correlation id) |
| `temporal_memory.episode_id` | `TemporalMemoryPlugin` `POST_TASK` (after ingest) | Phase 4 episode bridge |
| `temporal_memory.group_id` | `TemporalMemoryPlugin` `POST_TASK` (after ingest) | Phase 4 episode bridge |
| `knowledge.augmented_task` | `KnowledgePlugin` | HybridAgent `BUILD_MESSAGES` |
| `knowledge.iteration_context` | `KnowledgePlugin` | Tool-loop retrieval |

**L1 / L2 separation:** `KnowledgePlugin` does **not** read or merge `temporal_memory.facts`. Use `aiecs.domain.memory.retrieve_for_task` (`UnifiedMemoryRetriever`) when a caller needs combined L1+L2 retrieval without shared storage.

**Phase 4 episode_bridge:** Because POST_TASK runs **memory (80) before temporal_memory (85)**, the assistant turn is **deferred** when `temporal_memory_enabled=true` (`memory.pending_assistant`). `TemporalMemoryPlugin` calls `flush_pending_assistant_turn` after ingest with `build_l0_temporal_metadata`. Without L1, behavior matches Phase 0–2 (immediate assistant write). Custom plugin chains must call flush explicitly or rely on shutdown hooks. See [DOMAIN_CONTEXT.md](./DOMAIN_CONTEXT.md) and `episode_bridge.py`.

**Async ingest ordering:** `temporal_memory.ingest_job_id` is written before the worker runs; `episode_id` / `group_id` after ingest. L0 metadata flush runs after both are set (sync path) or after worker completion (async path). Do not treat `job_id` as a substitute for `episode_id`.

**UnifiedMemoryRetriever (TM-070/071):** `aiecs.domain.memory.retrieve_for_task` is a **read-only, opt-in API** — not wired into `TemporalMemoryPlugin` or `KnowledgePlugin`. Call it explicitly when merging L1 + L2 retrieval; plugins keep separate storage paths per ADR-003.

**PII (TM-075):** `TemporalMemoryEngine.ingest_from_task` runs `redact_episode_body` before `ingest_episode`. When `TM_STORE_RAW_EPISODE=false`, overlong bodies are truncated with a hash suffix; when `true`, bodies are kept up to `TM_EPISODE_BODY_MAX_CHARS`. Graphiti `store_raw_episode_content` still follows `TM_STORE_RAW_EPISODE`.

**Contrast with L2 `knowledge@builtin` (priority 40):**

| | L1 temporal | L2 knowledge |
|---|-------------|--------------|
| Purpose | Time-valid facts / episodes | Entity graph augmentation & reasoning |
| Short-circuit | No | `PRE_MAIN_LOOP` graph short-circuit |
| Default | Disabled | Disabled (enabled when non-NoOp `graph_store`) |
| Config flag | `temporal_memory_enabled` | `graph_store` + `KG_*` env |

---

## 6. Enable on HybridAgent

```python
from aiecs.domain.agent import HybridAgent
from aiecs.domain.agent.models import AgentConfiguration
from aiecs.domain.agent.plugins.models import PluginConfig

config = AgentConfiguration(
    goal="Assistant with temporal memory",
    temporal_memory_enabled=True,
    plugins=[
        PluginConfig(name="memory", enabled=True),
        PluginConfig(name="temporal_memory", enabled=True, options={"inject_facts": True}),
    ],
)

agent = HybridAgent(
    agent_id="agent-001",
    name="Temporal Assistant",
    llm_client=llm_client,
    tools=[],
    config=config,
)
await agent.initialize()
```

See [examples/temporal_memory/README.md](../../examples/temporal_memory/README.md) and `minimal_agent.py`.

---

## 7. Graphiti adapter behavior and L1 limits

### Search and retrieval (Graphiti backend)

| Port field | L1 MVP behavior |
|------------|-----------------|
| `valid_at` | Mapped to Graphiti edge filters: fact valid at instant *T* (`valid_at <= T` and `invalid_at` null or `> T`). |
| `SearchFilters.entity_types` | Mapped to Graphiti `node_labels`. |
| `SearchFilters.center_node_uuid` | Passed as Graphiti `center_node_uuid` (rerank anchor). |
| `SearchFilters.excluded_entity_types` | Post-filter on Graphiti results using `metadata['entity_labels']` from edge attributes; no-op when labels absent. Postgres backend ignores. |
| `get_fact(fact_id)` | Loads `EntityEdge` by UUID via Graphiti driver (not search approximation). |

Callers should not assume full bi-temporal query expressiveness until Phase 3 (`search_`, post-filters, TM-067).

### Initialization and degradation (TM-069 deferred)

| Layer | Behavior |
|-------|----------|
| `create_temporal_memory_store()` | Returns `NoOpTemporalMemoryStore` only on missing graphiti-core (`ImportError`). Does **not** probe FalkorDB/Neo4j. |
| `TemporalMemoryPlugin.on_agent_init` | On `initialize()` failure: logs warning, **`store.close()`** (best-effort), plugin stays disabled. Agent continues without L1. |
| Factory runtime fallback to NoOp | Planned **TM-069** (Phase 3), not L1 MVP. |

---

## 8. Verification (L1 MVP)

Acceptance checks are defined in [TEMPORAL_KG_MEMORY_L1_TASKS_BY_FILE.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_L1_TASKS_BY_FILE.md) **TM-058**:

```bash
pytest test/unit/domain/agent/plugins/test_temporal_memory_plugin.py -q
pytest test/unit/domain/agent/plugins/test_plugin_manager_order.py -q
TM_BACKEND=none pytest test/unit/domain/agent/plugins -q
openspec validate add-temporal-memory-l1 --strict
```

Integration (optional): `pytest test/integration/temporal_memory -m graphiti` with `TM_FALKORDB_URL` set.

**CI scope:** L1 acceptance is the scoped suites above plus `pytest test/unit/domain/agent/plugins/test_temporal_memory_plugin.py`. Full `pytest test/unit` is tracked against `artifacts/l1_ci_baseline.txt`; pre-existing failures outside L1 are not part of the L1 MVP gate.

---

## 9. Module map

| Path | Purpose |
|------|---------|
| `domain/temporal_memory/ports.py` | `TemporalMemoryStore` Protocol |
| `domain/temporal_memory/engine.py` | `ingest_from_task`, `search_for_task` |
| `domain/temporal_memory/pii.py` | `redact_episode_body` (ingest size / PII guard) |
| `domain/temporal_memory/search_cache.py` | Process-local search TTL cache |
| `domain/memory/unified_retriever.py` | Read-only L1+L2 merge (not used by plugins) |
| `infrastructure/temporal_memory/store_factory.py` | `create_temporal_memory_store()` |
| `infrastructure/temporal_memory/graphiti/store.py` | Graphiti adapter (lazy import) |
| `infrastructure/temporal_memory/graphiti/search_filters.py` | Port ``SearchFilters`` / ``valid_at`` → Graphiti |
| `domain/agent/plugins/builtin/temporal_memory_plugin.py` | Builtin plugin |
| `infrastructure/temporal_memory/ingest_queue.py` | Async POST_TASK ingest when `TM_INGEST_ASYNC` |

# Runbook — Temporal Memory (L1)

Operational guide for AIECS **L1 temporal memory** (Graphiti optional). Cross-links: [DOMAIN_TEMPORAL_MEMORY.md](../DOMAIN_TEMPORAL_MEMORY.md), [TEMPORAL_KG_MEMORY_INDEX.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_INDEX.md), [docker/temporal-memory/README.md](../../docker/temporal-memory/README.md).

---

## 1. Installation matrix

| Profile | Install | Temporal L1 | Graph backend |
|---------|---------|-------------|---------------|
| **Core only** | `pip install aiecs` | Off (`TM_ENABLED=false` or unset) | N/A |
| **L1 + Graphiti** | `pip install "aiecs[temporal-graphiti]"` or `pip install "graphiti-core[falkordb]"` | On (`TM_ENABLED=true`, `TM_BACKEND=graphiti`) | FalkorDB (default) or Neo4j |
| **L2 knowledge** | Customer private `aiecs-kg` (ADR-003) | Independent of L2 | N/A for L1 compose |

Local FalkorDB (optional):

```bash
docker compose -f docker/temporal-memory/docker-compose.yml up -d
```

---

## 2. Enable checklist

**Environment (`.env` or shell):**

| Check | Variable | Expected |
|-------|----------|----------|
| Master switch | `TM_ENABLED` | `true` |
| Backend | `TM_BACKEND` | `graphiti` |
| Graph driver | `TM_GRAPH_BACKEND` | `falkordb` or `neo4j` |
| FalkorDB URL | `TM_FALKORDB_URL` | Reachable (e.g. `redis://localhost:6379`) |
| LLM for extraction | `OPENAI_API_KEY` | Set if Graphiti uses OpenAI via adapter |
| Async ingest | `TM_INGEST_ASYNC` | `true` (default) or `false` for sync debug |
| Search cache | `TM_SEARCH_CACHE_ENABLED` | `true` (default) for repeat-query latency |
| PII guard | `TM_STORE_RAW_EPISODE` | `false` (default) unless raw storage required |
| Body limit | `TM_EPISODE_BODY_MAX_CHARS` | `4000` (default) |

**Agent configuration:**

| Check | Field | Expected |
|-------|-------|----------|
| Request L1 plugin | `AgentConfiguration.temporal_memory_enabled` | `true` |
| Plugin entry | `plugins[]` includes `temporal_memory` with `enabled: true` | Present |
| Derive gate | `create_temporal_memory_store()` not `NoOpTemporalMemoryStore` | Graphiti installed + `TM_ENABLED=true` |

**Smoke test:**

```bash
poetry run pytest test/unit/domain/agent/plugins/test_temporal_memory_plugin.py -q
```

---

## 3. Failure tree

```
Temporal memory not active?
├─ temporal_memory_enabled=false → enable on AgentConfiguration
├─ TM_ENABLED=false or TM_BACKEND=none → set TM_ENABLED=true, TM_BACKEND=graphiti
├─ graphiti-core not installed → pip install "aiecs[temporal-graphiti]"
├─ create_temporal_memory_store() returns NoOp (ImportError) → install graphiti-core; check logs
├─ Plugin on_agent_init: initialize() failed (FalkorDB down, bad URL)
│   └─ Scheme B (TM-069): store.close() best-effort; temporal_memory_enabled=false; agent continues
├─ OPENAI_API_KEY missing / invalid → Graphiti LLM extraction fails on ingest; check warnings
└─ POST_TASK ingest errors → logged "Temporal memory ingest failed"; execute_task still succeeds
```

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| No facts in PRE_TASK | NoOp store or plugin disabled | §2 checklist |
| Init warning + disabled plugin | FalkorDB connection refused | `docker compose -f docker/temporal-memory/docker-compose.yml up -d`; verify `TM_FALKORDB_URL` |
| Empty search results | Wrong `group_id` / tenant scope | Check `session_id`, `tenant_id` in context; `TM_SEARCH_PRIMARY_GROUP_ONLY` |
| High search latency | Cold Graphiti / no cache | Enable `TM_SEARCH_CACHE_ENABLED`; repeat query should hit cache |

---

## 4. Observability

**Prometheus metrics** (`aiecs/infrastructure/temporal_memory/metrics.py`):

| Metric | Labels | Meaning |
|--------|--------|---------|
| `tm_backend_active` | `backend` | Active backend gauge (none/graphiti/postgres) |
| `tm_ingest_total` | `backend`, `status` | Ingest ok/error counter |
| `tm_search_duration_seconds` | `backend`, `cache` | Search latency (`hit` / `miss` / `off`) |
| `tm_search_cache_hits_total` | — | Search cache hits |
| `tm_search_cache_misses_total` | — | Search cache misses |
| `tm_ingest_queue_depth` | — | Async ingest queue depth |
| `tm_plugin_enabled` | — | Plugin enabled (0/1) |

Metrics no-op when `prometheus_client` is unavailable.

**Log keywords:**

- `Temporal memory ingest failed` — ingest exception (swallowed at engine)
- `TemporalMemoryPlugin init failed` — `initialize()` failure; plugin disabled
- `Graphiti background ingest failed` — async Graphiti ingest task error
- `Temporal memory ingest queue job failed` — queued POST_TASK worker error

**Health:** `GraphitiTemporalMemoryStore.health_check()` → `ready: true/false` (not exposed on HTTP by default).

---

## 5. Optional integration tests

Graphiti + FalkorDB tests are **not** default CI gates.

```bash
export TM_FALKORDB_URL=redis://localhost:6379
export OPENAI_API_KEY=sk-...

poetry run pytest test/integration/temporal_memory -m graphiti -q
```

Load / performance (mock baseline; optional real DB):

```bash
export TM_LOAD_TEST=1
poetry run pytest test/performance/temporal_memory -m performance -q
```

Report template: [L1_LOAD_TEST_REPORT.md](../../issue_report/new_function_request/temporal_kg_memory/artifacts/L1_LOAD_TEST_REPORT.md).

**OpenSpec:**

```bash
openspec validate add-temporal-memory-l1 --strict
```

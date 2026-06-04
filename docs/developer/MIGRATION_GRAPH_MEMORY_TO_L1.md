# Migration: GraphMemoryMixin → L1 Temporal Memory

Guide for moving from deprecated **GraphMemoryMixin** / **ContextEngineWithGraph** patterns to **TemporalMemoryPlugin** + optional Graphiti (L1).

**Related:** [DOMAIN_TEMPORAL_MEMORY.md](./DOMAIN_TEMPORAL_MEMORY.md) · [DOMAIN_CONTEXT.md](./DOMAIN_CONTEXT.md) · [TEMPORAL_KG_MEMORY_INDEX.md](../../issue_report/new_function_request/temporal_kg_memory/TEMPORAL_KG_MEMORY_INDEX.md)

---

## 1. Deprecated vs replacement

| Deprecated (2.0 removed from core) | Replacement |
|-----------------------------------|-------------|
| `GraphMemoryMixin` | `TemporalMemoryPlugin` + `TemporalMemoryEngine` |
| `ContextEngineWithGraph` | `ContextEngine` (L0) + L1 `TemporalMemoryStore` Port |
| `graph_memory_enabled` on agent | `AgentConfiguration.temporal_memory_enabled` |
| Monorepo `aiecs/domain/knowledge_graph` | Customer private `aiecs-kg` via `KnowledgePlugin` (L2, ADR-003) |
| `KnowledgeAwareAgent` / `GraphAwareAgentMixin` | `HybridAgent` + plugins |

L1 stores **time-valid facts/episodes** (Graphiti). L2 stores **enterprise KG** entities — separate layer, not a drop-in replacement for GraphMemoryMixin.

---

## 2. Configuration migration

| Old / informal | New (L1) |
|--------------|----------|
| `graph_memory_enabled=true` | `temporal_memory_enabled=true` on `AgentConfiguration` |
| Implicit graph on ContextEngine | `TM_ENABLED=true`, `TM_BACKEND=graphiti` |
| Embedded FalkorDB assumptions | `TM_FALKORDB_URL=redis://host:6379` |
| — | `TM_GRAPH_BACKEND=falkordb` or `neo4j` + `TM_NEO4J_*` |

**L2 (unchanged contract):** `KG_ENABLED=true`, `KG_BACKEND_MODULE=<customer_module>` — independent of L1.

---

## 3. Plugin YAML example

```yaml
# AgentConfiguration.plugins (illustrative)
plugins:
  - name: memory
    enabled: true
  - name: temporal_memory
    enabled: true
    options:
      inject_facts: true
      facts_limit: 10
  - name: knowledge
    enabled: false   # enable when customer installs private aiecs-kg
```

**Environment:**

```bash
pip install "aiecs[temporal-graphiti]"
export TM_ENABLED=true
export TM_BACKEND=graphiti
export TM_FALKORDB_URL=redis://localhost:6379
export OPENAI_API_KEY=sk-...
```

---

## 4. Data migration

**AIECS does not automatically migrate** legacy graph-memory or monorepo KG data into Graphiti.

Customers must:

1. Export or ETL historical episodes/facts into Graphiti (or accept a fresh L1 graph).
2. Keep L0 conversation history in ContextEngine / Redis+PG as today.
3. Use **episode_bridge** metadata (`temporal_episode_id` on L0 messages) only for **new** turns after enabling L1.

See [DOMAIN_CONTEXT.md](./DOMAIN_CONTEXT.md) for the one-way bridge (Agent task → L1 ingest → L0 metadata pointer). **Cold archive does not trigger L1 ingest.**

---

## 5. Verification

```bash
# No GraphMemory types in core
rg 'GraphMemoryMixin|ContextEngineWithGraph' aiecs   # expect 0 hits

pytest test/unit/domain/agent/plugins/test_temporal_memory_plugin.py -q
pytest test/unit/domain/agent/plugins/test_memory_plugin_temporal_bridge.py -q
```

Audit record: [L1_PHASE4_GRAPH_MEMORY_AUDIT.txt](../../issue_report/new_function_request/temporal_kg_memory/artifacts/L1_PHASE4_GRAPH_MEMORY_AUDIT.txt).

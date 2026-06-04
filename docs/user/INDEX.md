# AIECS User Documentation Index

Entry point for user-facing guides. Developer migration notes: [MIGRATION_2_0.md](../developer/MIGRATION_2_0.md).

## Installation matrix (2.0.0+)

Choose the install profile that matches your deployment. AIECS core stays small; memory backends are **optional** and installed on the **customer** side where noted.

| Profile | Install command | Temporal memory (L1) | Knowledge graph (L2) | Core agents & tools |
|---------|-----------------|----------------------|----------------------|---------------------|
| **core** | `pip install aiecs` | No (`TM_BACKEND=none` or unset) | No (`KG_ENABLED=false`, default) | `HybridAgent`, `task_tools`, `docs`, `search_tool` |
| **+graphiti (L1)** | `pip install graphiti-core[falkordb]` or `pip install aiecs[temporal-graphiti]` (customer) + core above | Yes — `TM_ENABLED=true`, `TM_BACKEND=graphiti`, FalkorDB/Neo4j per [DOMAIN_TEMPORAL_MEMORY.md](../developer/DOMAIN_TEMPORAL_MEMORY.md) | No | Same as core |
| **+private KG** | Customer installs licensed `aiecs-kg` (or compatible module) + core above | Optional (independent of L2) | Yes — `KG_ENABLED=true`, `KG_BACKEND_MODULE=<module>` | `KnowledgePlugin` via factory; **not** bundled in PyPI core |

### Notes

- **core** is the only profile validated in AIECS open-source CI (`core-slim` job). No `networkx`, embedded KG, apisource, scraper, or statistics packages.
- **+graphiti (L1)** is optional; the core wheel does **not** bundle `graphiti-core`. Customers install Graphiti and set `TM_BACKEND=graphiti`. AIECS CI uses unit mocks; integration tests are `pytest -m graphiti` (optional).
- **+private KG** is entirely customer-side (ADR-003). AIECS documents the `KG_ENABLED` / `KG_BACKEND_MODULE` contract only; it does not publish or test proprietary KG wheels.

### Environment quick reference

| Goal | Variables |
|------|-----------|
| Default core | `KG_ENABLED=false` |
| Private L2 graph | `KG_ENABLED=true`, `KG_BACKEND_MODULE=aiecs_kg` (example) |
| L1 temporal memory | `TM_ENABLED=true`, `TM_BACKEND=graphiti`, `TM_FALKORDB_URL`, `AgentConfiguration.temporal_memory_enabled=true` |

## Documentation map

| Area | Index |
|------|--------|
| Agents | [DOMAIN_AGENT/README.md](./DOMAIN_AGENT/README.md) |
| Temporal memory (L1) | [DOMAIN_TEMPORAL_MEMORY.md](../developer/DOMAIN_TEMPORAL_MEMORY.md) |
| Hybrid agent config | [DOMAIN_AGENT/HYBRID_AGENT_CONFIGURATION.md](./DOMAIN_AGENT/HYBRID_AGENT_CONFIGURATION.md) |
| Context | [DOMAIN_CONTEXT/INDEX.md](./DOMAIN_CONTEXT/INDEX.md) |
| Community | [DOMAIN_COMMUNITY/INDEX.md](./DOMAIN_COMMUNITY/INDEX.md) |
| Tools | [TOOLS/TOOL_CONFIGURATION.md](./TOOLS/TOOL_CONFIGURATION.md) |
| Usage | [USAGE_GUIDE.md](./USAGE_GUIDE.md) |

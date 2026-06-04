# Temporal Memory — local Graphiti stack

Minimal Docker Compose for **L1 temporal memory** development with Graphiti + FalkorDB.

**TM-073:** This stack runs **FalkorDB only** (no AIECS app container). Run agents and `pytest` on the host against `localhost:6379`.

## Quick start

```bash
cd docker/temporal-memory
docker compose up -d
docker compose ps
```

From the AIECS repo root (host network):

```bash
export TM_ENABLED=true
export TM_BACKEND=graphiti
export TM_FALKORDB_URL=redis://localhost:6379
export OPENAI_API_KEY=sk-...
export temporal_memory_enabled=true

poetry run pytest test/integration/temporal_memory -m graphiti -q
```

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | FalkorDB service (port 6379) |
| `.env.example` | Suggested `TM_*` and agent flags |

## Neo4j (optional)

Uncomment the `neo4j` service in `docker-compose.yml` and set:

```bash
TM_GRAPH_BACKEND=neo4j
TM_NEO4J_URI=bolt://localhost:7687
TM_NEO4J_USER=neo4j
TM_NEO4J_PASSWORD=password
```

## Not included (ADR-003)

Private **aiecs-kg** / L2 knowledge graph images are **not** part of this stack. Use customer-side `KG_ENABLED` and `KG_BACKEND_MODULE` separately.

## Related docs

- [DOMAIN_TEMPORAL_MEMORY.md](../../docs/developer/DOMAIN_TEMPORAL_MEMORY.md)
- [runbooks/TEMPORAL_MEMORY.md](../../docs/developer/runbooks/TEMPORAL_MEMORY.md)

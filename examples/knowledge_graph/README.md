# Knowledge graph examples (legacy monorepo)

The embedded KG **engine** in this monorepo (`aiecs/domain/knowledge_graph`, `aiecs/application/knowledge_graph`, `aiecs/infrastructure/graph_storage`) is being removed per the AIECS slimdown plan. The engine moves to **private `aiecs-kg`** (customer-installed; not published in AIECS `pyproject.toml`).

**Agent integration (supported path):**

- Use `HybridAgent` with `knowledge@builtin` (`KnowledgePlugin`).
- Set `KG_ENABLED=true` when a compatible private graph store is available.

**Not supported in core after slimdown:**

- Built-in tools `kg_builder`, `graph_search`, `graph_reasoning` (ADR-001).
- `KnowledgeAwareAgent` (deprecated → removed in 2.0.0).

Runnable demos were moved to `examples/archived/slimdown_2_0_2026/knowledge_graph/` (they depended on removed monorepo KG modules).

# Archived — AIECS 2.0 slimdown (removed APIs)

**Archived:** 2026-05-28  
**Reason:** Tests import modules removed in AIECS 2.0 (`knowledge_graph`, `graph_storage`, `apisource`, `statistics`, KG tools).

These paths are **not** in `pyproject.toml` `testpaths`. Restore only against a private `aiecs-kg` fork or historical tag.

## Contents

| Path | Former location |
|------|-----------------|
| `integration/agent/test_agent_*.py` | `test/integration/agent/` |
| `integration/tools/test_migrated_tools_integration.py` | `test/integration/tools/` |
| `e2e/workflows/test_agent_workflows.py` | `test/e2e/workflows/` |
| `scalability/test_*.py` | `test/scalability/` |
| `performance/test_graph_storage_benchmarks.py` | `test/performance/` |
| `test_migration_from_integration_kg.py` | `test/archived/` |
| `test_statistical_analyzer_tool.py` | `test/archived/` |

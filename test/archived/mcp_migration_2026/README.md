# Archived — MCP migration (document tools)

**Archived:** 2026-06-26  
**Reason:** Tests and examples import `aiecs.tools.docs`, removed from AIECS core.

These paths are **not** in `pyproject.toml` `testpaths`. Restore only against MCP server tools, a historical tag, or the source snapshot under `aiecs_tools_docs/`.

## Contents

| Path | Former location |
|------|-----------------|
| `docs/test_*.py` | `test/unit/tools/`, `test/unit/application/orchestrators/`, `test/e2e/tools/` |
| `docs/test_tools_docs/` | `test/tools/docs/` |
| `integration/tools/test_developer_customization_integration.py` | `test/integration/tools/` |
| `aiecs_tools_docs/` | `aiecs/tools/docs/` |

Examples: `examples/archived/mcp_migration_2026/docs/`

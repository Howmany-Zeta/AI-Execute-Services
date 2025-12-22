# Archived Tests

This directory contains tests that have been archived because they reference obsolete APIs or deleted functionality.

Tests are archived rather than deleted to preserve history and potentially restore them if needed.

## Archive Date: December 21, 2025

## Archived Files

### Duplicate Conftest (Removed to eliminate duplication)
- `conftest_main_tests_duplicate.py` (originally from unit_tests/main_tests/)

**Reason**: This conftest duplicated 7 fixtures already present in `test/configs/conftest.py`:
- test_data_dir
- sample_csv_file
- temp_csv_file
- tool_executor
- execution_utils
- operation_executor_config
- operation_executor

**Impact**: The main_tests now use fixtures from the main conftest, eliminating maintenance burden

**Date Archived**: 2025-12-21

---

### Migration Tests (migrate_graph_store doesn't exist)
- `test_migration.py` from integration_tests/knowledge_graph/
- `test_edge_cases.py` from unit_tests/graph_storage/ (partial - migration imports)
- `test_error_handling.py` from unit_tests/graph_storage/ (partial - migration imports)

**Reason**: These tests import `migrate_graph_store` function which doesn't exist in `aiecs.infrastructure.graph_storage.migration`. The actual migration functionality uses the `GraphStorageMigrator` class and `migrate_sqlite_to_postgres` function instead.

**Status**: Archived on 2025-12-21

### Stats Tool Tests (StatsSettings doesn't exist) - ARCHIVED
- `test_stats_tool_comprehensive.py`  
- `test_stats_tool.py`
- `test_statistical_analyzer_tool.py`

**Reason**: These tests import `StatsSettings` class which doesn't exist. After the BaseSettings refactoring, the configuration is accessed via `StatsTool.Config`.

**Error**: `ImportError: cannot import name 'StatsSettings' from 'aiecs.tools.task_tools.stats_tool'`

**Status**: Archived on 2025-12-21. Tests may need to be rewritten to use `StatsTool.Config` instead.

## Restoration Notes

If you need to restore any of these tests:

1. Check if the referenced functionality has been re-implemented
2. Update import statements to use current APIs
3. Update test assertions to match current behavior
4. Move back to appropriate test directory
5. Run pytest to verify the test works

## Related Changes

See: `openspec/changes/add-cicd-testing-workflow/`
- BROKEN_TESTS_DETAILED.md
- FIX_STRATEGY_MATRIX.md

# Entity Linker Candidate Retrieval Test Coverage Analysis

## Code Paths in `_get_candidate_entities()`

The implementation has three code paths:

1. **Main Path**: Uses `get_all_entities()` if available
2. **Fallback Path 1**: Uses `text_search()` if `get_all_entities()` unavailable
3. **Fallback Path 2**: Returns empty list if neither method available

## Test Coverage Analysis

### Tests Using Main Path (get_all_entities)

These tests use `InMemoryGraphStore` which HAS `get_all_entities()`, so they test the **main path**:

- ✅ `test_get_candidate_entities_by_type` - Tests main path with type filtering
- ✅ `test_get_candidate_entities_with_limit` - Tests main path with pagination
- ✅ `test_get_candidate_entities_with_tenant_context` - Tests main path with tenant isolation
- ✅ `test_get_candidate_entities_empty_store` - Tests main path with empty store
- ✅ `test_get_candidate_entities_nonexistent_type` - Tests main path with invalid type

**Note**: These tests verify the main implementation works correctly, but they don't test fallback behavior.

### Tests Using Fallback Paths

These tests specifically test fallback behavior:

- ✅ `test_get_candidate_entities_fallback_to_text_search` - Tests fallback to `text_search()` when `get_all_entities()` raises AttributeError
- ✅ `test_get_candidate_entities_fallback_to_empty_list` - Tests final fallback to empty list when neither method available
- ✅ `test_get_candidate_entities_handles_exceptions` - Tests exception handling (main path fails, falls back gracefully)

### Tests for `_link_by_name()` Optimization

- ✅ `test_link_by_name_uses_text_search_when_available` - Tests that `_link_by_name()` uses `text_search()` optimization (main path)
- ✅ `test_link_by_name_fallback_to_candidates` - Tests fallback to candidate enumeration when `text_search()` unavailable
- ✅ `test_link_by_name_no_match` - Tests main path with no matches
- ✅ `test_link_by_name_no_name_property` - Tests main path with missing name property

## Summary

**Main Path Coverage**: ✅ Good (5 tests)
**Fallback Path Coverage**: ✅ Good (3 tests)
**Exception Handling**: ✅ Covered (1 test)
**Integration Coverage**: ✅ Covered (integration tests with different stores)

## Recommendation

The test suite has good coverage of both main and fallback paths. However, to be more explicit about testing fallbacks, consider:

1. Adding a test that verifies `text_search()` is actually called when `get_all_entities()` is unavailable
2. Adding a test that verifies the empty list fallback is used when both methods unavailable
3. Adding integration tests with `SQLiteGraphStore` (which may not have `get_all_entities()`) to test real-world fallback scenarios

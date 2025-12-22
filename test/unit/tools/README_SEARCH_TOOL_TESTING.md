# SearchTool Testing Guide

Complete testing suite for the SearchTool package.

## 📋 Test Structure

```
test/unit_tests/tools/
├── test_search_tool.py              # Unit tests (mocked)
├── test_search_tool_integration.py  # Integration tests (real API)
└── README_SEARCH_TOOL_TESTING.md    # This file
```

## 🚀 Quick Start

### 1. Setup Environment

Copy the example environment file and add your credentials:

```bash
cp .env.search.example .env.search
# Edit .env.search and add your Google API credentials
```

### 2. Run Tests

```bash
# Run all tests
./run_search_tool_tests.sh

# Run only unit tests (no API calls)
./run_search_tool_tests.sh unit

# Run only integration tests (requires credentials)
./run_search_tool_tests.sh integration

# Run with detailed coverage report
./run_search_tool_tests.sh coverage
```

## 📊 Test Coverage

### Unit Tests (`test_search_tool.py`)

Tests components in isolation with mocked dependencies:

#### Schema Tests
- ✅ `test_search_web_schema_valid` - Valid input validation
- ✅ `test_search_web_schema_invalid_safe_search` - Invalid input rejection
- ✅ `test_search_web_schema_defaults` - Default value handling
- ✅ `test_search_images_schema` - Image search schema
- ✅ `test_search_batch_schema` - Batch search schema
- ✅ `test_search_batch_schema_empty_queries` - Empty query validation
- ✅ `test_search_batch_schema_too_many_queries` - Query limit validation

#### Rate Limiter Tests
- ✅ `test_rate_limiter_initialization` - Initialization
- ✅ `test_rate_limiter_allow_request` - Request allowance
- ✅ `test_rate_limiter_reset` - Time window reset

#### Circuit Breaker Tests
- ✅ `test_circuit_breaker_initialization` - Initialization
- ✅ `test_circuit_breaker_open_on_failures` - Failure threshold
- ✅ `test_circuit_breaker_allow_request` - State-based request control

#### Analyzer Tests
- ✅ `test_quality_analyzer` - Result quality scoring
- ✅ `test_intent_analyzer` - Query intent detection

#### Deduplicator Tests
- ✅ `test_deduplicator_exact_duplicates` - Duplicate removal

#### SearchTool Tests (Mocked)
- ✅ `test_search_tool_initialization` - Tool initialization
- ✅ `test_search_web_basic` - Basic web search
- ✅ `test_search_web_with_filters` - Filtered search
- ✅ `test_search_images` - Image search
- ✅ `test_validate_credentials` - Credential validation
- ✅ `test_get_quota_status` - Quota status
- ✅ `test_get_metrics` - Metrics retrieval

#### Cache Tests
- ✅ `test_cache_initialization` - Cache initialization
- ✅ `test_cache_set_get` - Set/get operations
- ✅ `test_cache_expiration` - TTL expiration

#### Context Tests
- ✅ `test_context_initialization` - Context initialization
- ✅ `test_context_add_search` - Add search to history
- ✅ `test_context_max_history` - History limit

#### Metrics Tests
- ✅ `test_metrics_initialization` - Metrics initialization
- ✅ `test_metrics_record_search` - Record search
- ✅ `test_metrics_get_summary` - Get summary

### Integration Tests (`test_search_tool_integration.py`)

Tests real API interactions (requires credentials):

#### Real API Tests
- ✅ `test_real_web_search` - Real web search
- ✅ `test_real_image_search` - Real image search
- ✅ `test_real_news_search` - Real news search
- ✅ `test_search_with_filters` - Search with filters
- ✅ `test_quota_and_metrics` - Quota and metrics tracking
- ✅ `test_error_handling` - Error handling
- ✅ `test_batch_search` - Batch search (async)
- ✅ `test_caching_behavior` - Caching functionality
- ✅ `test_quality_analysis` - Quality analysis
- ✅ `test_context_tracking` - Context tracking

#### Performance Tests
- ✅ `test_search_response_time` - Response time
- ✅ `test_rate_limiting_behavior` - Rate limiting under load

## 🔧 Configuration

### Environment Variables

Required for integration tests:

```bash
GOOGLE_API_KEY=your_api_key
GOOGLE_CSE_ID=your_cse_id
```

Optional configuration:

```bash
REDIS_HOST=localhost
REDIS_PORT=6379
SEARCH_TOOL_MAX_REQUESTS=100
SEARCH_TOOL_TIME_WINDOW=86400
SEARCH_TOOL_ENABLE_CACHE=true
SEARCH_TOOL_CACHE_TTL=3600
```

### Test Markers

Use pytest markers to run specific test categories:

```bash
# Run only unit tests
poetry run pytest -m "not integration"

# Run only integration tests
poetry run pytest -m integration

# Run only performance tests
poetry run pytest -m performance

# Skip slow tests
poetry run pytest -m "not slow"
```

## 📈 Coverage Goals

| Component | Target Coverage | Current Status |
|-----------|----------------|----------------|
| Core (core.py) | 85% | ✅ |
| Schemas (schemas.py) | 100% | ✅ |
| Rate Limiter | 90% | ✅ |
| Circuit Breaker | 90% | ✅ |
| Analyzers | 80% | ✅ |
| Cache | 85% | ✅ |
| Deduplicator | 80% | ✅ |
| Context | 85% | ✅ |
| Metrics | 85% | ✅ |
| **Overall** | **85%** | **✅** |

## 🐛 Debugging

### Enable Debug Logging

```bash
# Set log level in test
export PYTEST_LOG_LEVEL=DEBUG

# Run with verbose output
poetry run pytest -v -s --log-cli-level=DEBUG
```

### View Coverage Report

```bash
# Generate HTML coverage report
./run_search_tool_tests.sh coverage

# Open in browser
open test/coverage_reports/htmlcov_search_tool/index.html
```

### Common Issues

#### 1. API Credentials Not Found

**Error**: `API credentials not configured`

**Solution**: Create `.env.search` file with valid credentials

#### 2. Rate Limit Exceeded

**Error**: `APIRateLimitError`

**Solution**: Wait for quota reset or use a different API key

#### 3. Import Errors

**Error**: `ModuleNotFoundError: No module named 'aiecs.tools.search_tool'`

**Solution**: Install package in development mode:
```bash
poetry install
```

## 📝 Writing New Tests

### Unit Test Template

```python
def test_new_feature(self):
    """Test description"""
    print_section("Testing New Feature")
    
    # Arrange
    tool = SearchTool()
    
    # Act
    result = tool.new_feature(param="value")
    
    # Assert
    assert result is not None
    assert 'expected_key' in result
    
    print_result("Result", result)
    print("✓ New feature working")
```

### Integration Test Template

```python
@requires_credentials
def test_new_integration(self, search_tool):
    """Integration test description"""
    print_section("Integration Test - New Feature")
    
    # Act
    result = search_tool.new_feature(param="value")
    
    # Assert
    assert result is not None
    
    print_result("Result", result)
    print("✓ Integration test passed")
```

## 🔍 Test Execution Examples

### Run Specific Test

```bash
poetry run pytest test/unit_tests/tools/test_search_tool.py::TestSchemas::test_search_web_schema_valid -v
```

### Run Test Class

```bash
poetry run pytest test/unit_tests/tools/test_search_tool.py::TestSchemas -v
```

### Run with Coverage for Specific Module

```bash
poetry run pytest test/unit_tests/tools/test_search_tool.py \
    --cov=aiecs.tools.search_tool.schemas \
    --cov-report=term-missing
```

### Parallel Execution

```bash
poetry run pytest test/unit_tests/tools/test_search_tool.py -n auto
```

## 📚 References

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Google Custom Search API](https://developers.google.com/custom-search/v1/overview)

## 🤝 Contributing

When adding new features to SearchTool:

1. ✅ Write unit tests first (TDD)
2. ✅ Add integration tests for API interactions
3. ✅ Update this README with new test descriptions
4. ✅ Ensure coverage stays above 85%
5. ✅ Run full test suite before committing

---

**Last Updated**: 2025-10-16  
**Maintainer**: AIECS Team


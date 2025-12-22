# Unified Test Structure for AIECS

## Overview

The test directory has been restructured to use a single, unified `conftest.py` that provides consistent fixtures and configuration for all tests across the project.

## Test Structure

```
test/
├── conftest.py                                    # 🔧 Unified configuration for all tests
├── data/                                          # 📁 Test data files (centralized location)
│   ├── sample_data.csv                           # Main test data (name,age,salary,department)
│   ├── numeric_data.csv                          # Numeric analysis test data
│   ├── categorical_data.csv                      # Categorical analysis test data
│   ├── time_series_data.csv                      # Time series test data
│   ├── large_test_data.csv                       # Performance testing data
│   ├── test_data.json                            # JSON format test data
│   └── test_data.xlsx                            # Excel format test data
├── test_stats_tool.py                            # 🧪 Stats tool tests
├── test_operation_executor_comprehensive.py      # 🧪 Comprehensive operation executor tests
├── test_operation_executor_production_readiness.py # 🧪 Production readiness tests
├── test_*.py                                     # 🧪 Other tool tests
├── PRODUCTION_READINESS_ASSESSMENT.md           # 📋 Production assessment
└── UNIFIED_TEST_STRUCTURE.md                    # 📋 This documentation
```

**✅ Clean Structure Achieved:**
- All test data consolidated in `test/data/` directory
- No duplicate data files in root directory
- Consistent data format across all tests

## Unified conftest.py Features

### 🔧 **Core Fixtures**
- `tool_executor` - ToolExecutor instance with optimized config
- `execution_utils` - ExecutionUtils instance for operation management
- `operation_executor` - OperationExecutor instance for testing
- `event_loop` - Async event loop for pytest-asyncio

### 📁 **Data Fixtures**
- `test_data_dir` - Path to test data directory
- `sample_csv_file` - Basic CSV file for general testing
- `temp_csv_file` - Temporary CSV file (auto-cleanup)
- `stats_test_data` - Comprehensive test data for stats tool
- `large_test_data` - Large dataset for performance testing

### 🛡️ **Environment Setup**
- Automatic tool discovery
- Environment variable configuration
- Dependency skip flags for heavy tools
- Logging level management
- Graceful error handling for missing dependencies

### 🏷️ **Test Markers**
- `@pytest.mark.slow` - For performance/load tests
- `@pytest.mark.integration` - For integration tests
- `@pytest.mark.security` - For security tests
- `@pytest.mark.performance` - For performance tests

## Test Categories

### 1. **Functional Tests** ✅
- **Location**: `test_operation_executor_comprehensive.py`
- **Coverage**: Core functionality, integration, error handling
- **Status**: 62 tests passing
- **Purpose**: Verify basic functionality works correctly

### 2. **Production Readiness Tests** 🔒
- **Location**: `test_operation_executor_production_readiness.py`
- **Coverage**: Security, performance, reliability, monitoring
- **Status**: 17 tests passing
- **Purpose**: Ensure system is ready for production deployment

### 3. **Tool Tests** 🔧
- **Location**: `test_*_tool.py` files
- **Coverage**: Individual tool functionality
- **Status**: Working with unified conftest
- **Purpose**: Test specific tool implementations

## Running Tests

### **All Tests**
```bash
poetry run pytest test/ -v
```

### **By Category**
```bash
# Functional tests
poetry run pytest test/test_operation_executor_comprehensive.py -v

# Production readiness tests
poetry run pytest test/test_operation_executor_production_readiness.py -v

# Tool tests
poetry run pytest test/test_stats_tool.py -v
```

### **By Marker**
```bash
# Security tests only
poetry run pytest -m security -v

# Performance tests only
poetry run pytest -m performance -v

# Skip slow tests
poetry run pytest -m "not slow" -v
```

### **Specific Test Classes**
```bash
# Security validation
poetry run pytest test/test_operation_executor_production_readiness.py::TestSecurityAndValidation -v

# Performance testing
poetry run pytest test/test_operation_executor_production_readiness.py::TestPerformanceAndLoad -v
```

## Configuration Benefits

### ✅ **Consistency**
- All tests use the same fixtures and configuration
- Consistent environment setup across all test files
- Unified error handling and dependency management

### ✅ **Maintainability**
- Single source of truth for test configuration
- Easy to update fixtures for all tests
- Centralized environment variable management

### ✅ **Reliability**
- Automatic cleanup of temporary files
- Graceful handling of missing dependencies
- Consistent logging and error reporting

### ✅ **Performance**
- Session-scoped fixtures for expensive operations
- Optimized tool discovery and caching
- Efficient test data management

## Migration from Old Structure

### **Removed Files**
- `test/main_tesst/conftest.py` - Merged into unified conftest
- `test/conftest_stats.py` - Functionality integrated
- `test/conftest.py.backup` - Archived

### **Moved Files**
- `test/main_tesst/test_operation_executor_comprehensive.py` → `test/`
- `test/main_tesst/test_operation_executor_production_readiness.py` → `test/`

### **Updated Files**
- All test files now use the unified conftest.py
- Environment variables standardized
- Fixture names consistent across all tests

## Production Deployment Checklist

### ✅ **Functional Tests** (Required)
- [x] Core operation execution
- [x] Batch processing
- [x] Error handling
- [x] Tool integration

### ✅ **Security Tests** (Critical)
- [x] Parameter injection protection
- [x] Resource exhaustion protection
- [x] Access control validation
- [x] Input size limits

### ✅ **Performance Tests** (Critical)
- [x] High concurrency handling
- [x] Memory usage monitoring
- [x] Rate limiting effectiveness
- [x] Tool lifecycle management

### ✅ **Reliability Tests** (Important)
- [x] Failure recovery
- [x] Partial batch failures
- [x] Resource cleanup
- [x] Timeout handling

### ✅ **Monitoring Tests** (Important)
- [x] Statistics collection
- [x] Error tracking
- [x] Health checks
- [x] Configuration validation

## Next Steps

1. **Run comprehensive test suite** before any deployment
2. **Monitor test results** in CI/CD pipeline
3. **Add new tests** using the unified conftest structure
4. **Update documentation** as tests evolve

## Usage Examples

### **Adding New Tests**
```python
# test/test_new_feature.py
import pytest

def test_new_feature(operation_executor, sample_csv_file):
    """Test using unified fixtures."""
    result = operation_executor.execute_operation(
        "stats.read_data", {"file_path": sample_csv_file}
    )
    assert result is not None
```

### **Using Test Data**
```python
def test_with_test_data(stats_test_data):
    """Test using pre-configured test data."""
    numeric_file = stats_test_data['numeric']
    categorical_file = stats_test_data['categorical']
    # Use the files in your test
```

### **Custom Markers**
```python
@pytest.mark.slow
@pytest.mark.performance
def test_performance_feature():
    """Performance test with custom markers."""
    pass
```

The unified test structure provides a solid foundation for both development testing and production readiness validation.

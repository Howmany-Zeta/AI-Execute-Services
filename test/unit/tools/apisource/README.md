# APISource Tool Test Suite

Comprehensive test suite for the APISource tool and all its components. Tests real functionality without mocks to verify actual behavior and output.

## 📋 Test Coverage

### Test Files

1. **test_apisource_tool.py** - Main tool functionality
   - Initialization and configuration
   - Provider management
   - Query operations
   - Search functionality
   - Error handling
   - Caching
   - Metrics collection

2. **test_providers.py** - All API providers
   - FRED (Federal Reserve Economic Data)
   - News API
   - World Bank
   - US Census Bureau
   - Provider registry
   - Parameter validation
   - Error handling

3. **test_intelligence.py** - Intelligence modules
   - Query intent analyzer
   - Query enhancer
   - Data fusion engine
   - Search enhancer

4. **test_reliability.py** - Reliability modules
   - Smart error handler
   - Fallback strategy
   - Retry mechanisms
   - Error classification

5. **test_monitoring.py** - Monitoring and metrics
   - Detailed metrics collection
   - Health score calculation
   - Performance tracking
   - Response time percentiles

6. **test_utils.py** - Utility functions
   - Data validators
   - Outlier detection
   - Time gap detection
   - Data quality checks

7. **test_integration.py** - End-to-end integration tests
   - Complete workflows
   - Error recovery scenarios
   - Performance scenarios
   - Real-world use cases

## 🚀 Quick Start

### Prerequisites

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Set up API keys:**
   
   Copy the `.env.apisource` file and fill in your API keys:
   ```bash
   # The .env.apisource file is already in the project root
   # Edit it to add your API keys
   ```

   Get your free API keys:
   - FRED: https://fred.stlouisfed.org/docs/api/api_key.html
   - News API: https://newsapi.org/register
   - Census: https://api.census.gov/data/key_signup.html
   - World Bank: No API key needed!

### Running Tests

#### Run all tests (excluding network tests):
```bash
poetry run pytest test/unit_tests/tools/apisource -v -s
```

#### Run with coverage report:
```bash
poetry run python test/scripts/run_apisource_coverage.py
```

#### Run all tests including network tests:
```bash
poetry run python test/scripts/run_apisource_coverage.py --all
```

#### Run only network tests:
```bash
poetry run python test/scripts/run_apisource_coverage.py --network
```

#### Run integration tests:
```bash
poetry run python test/scripts/run_apisource_coverage.py --integration
```

#### Run specific test file:
```bash
poetry run python test/scripts/run_apisource_coverage.py --file test_providers.py
```

#### Run specific test class or function:
```bash
poetry run pytest test/unit_tests/tools/apisource/test_providers.py::TestFREDProvider -v -s
poetry run pytest test/unit_tests/tools/apisource/test_providers.py::TestFREDProvider::test_search_series -v -s
```

## 📊 Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.network` - Tests that require network access
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.provider` - Provider-specific tests

### Filter by markers:
```bash
# Skip network tests
poetry run pytest test/unit_tests/tools/apisource -m "not network" -v

# Run only network tests
poetry run pytest test/unit_tests/tools/apisource -m "network" -v

# Run only integration tests
poetry run pytest test/unit_tests/tools/apisource -m "integration" -v

# Skip slow tests
poetry run pytest test/unit_tests/tools/apisource -m "not slow" -v
```

## 🎯 Coverage Goals

- **Target Coverage:** 85%+
- **Current Coverage:** Run tests to see current coverage
- **Coverage Report:** `test/coverage_reports/htmlcov_apisource/index.html`

### View coverage report:
```bash
# Run tests with coverage
poetry run python test/scripts/run_apisource_coverage.py

# Open HTML report
open test/coverage_reports/htmlcov_apisource/index.html
```

## 🔍 Debug Output

All tests include debug output for manual verification:

- Request/response details
- Performance metrics
- Data quality information
- Error messages and recovery suggestions

### Enable verbose output:
```bash
poetry run pytest test/unit_tests/tools/apisource -v -s
```

The `-s` flag shows all print statements, including debug output.

## 📝 Test Configuration

Configuration is loaded from `.env.apisource`:

```bash
# API Keys
FRED_API_KEY=your_key_here
NEWSAPI_API_KEY=your_key_here
CENSUS_API_KEY=your_key_here

# Test Configuration
RUN_NETWORK_TESTS=true
RUN_SLOW_TESTS=false
RUN_INTEGRATION_TESTS=true
TEST_TIMEOUT=300
API_REQUEST_TIMEOUT=30
COVERAGE_THRESHOLD=85

# Debug Configuration
DEBUG_MODE=true
VERBOSE_API_CALLS=true
```

## 🧪 Test Structure

Each test file follows this structure:

```python
class TestFeatureName:
    """Test specific feature"""
    
    def test_basic_functionality(self, debug_output):
        """Test basic functionality with debug output"""
        print("\n=== Testing Feature ===")
        
        # Test code here
        
        debug_output("Test Results", {
            'key': 'value'
        })
        
        print("✓ Test passed")
```

## 🛠️ Fixtures

Common fixtures available in `conftest.py`:

- `api_keys` - API keys from environment
- `test_config` - Test configuration
- `fred_config`, `newsapi_config`, etc. - Provider-specific configs
- `skip_if_no_api_key` - Skip test if API key not available
- `debug_output` - Helper for formatted debug output
- `assert_valid_response` - Validate API response structure
- `measure_performance` - Measure test performance

## 📈 Performance Testing

Performance is measured for all network operations:

```python
def test_operation(self, measure_performance):
    measure_performance.start()
    
    # Operation here
    
    duration = measure_performance.stop()
    measure_performance.print_result("Operation name")
```

## 🐛 Troubleshooting

### Tests fail with "API key not found"
- Make sure `.env.apisource` exists and contains your API keys
- Check that the environment variables are loaded correctly

### Network tests timeout
- Increase `API_REQUEST_TIMEOUT` in `.env.apisource`
- Check your internet connection
- Some APIs may have rate limits

### Coverage below 85%
- Run with `--all` flag to include all tests
- Check which lines are not covered in the HTML report
- Add tests for uncovered code paths

## 📚 Additional Resources

- [APISource Tool Documentation](../../../../aiecs/tools/apisource/README.md)
- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/)
- [News API Documentation](https://newsapi.org/docs)
- [World Bank API Documentation](https://datahelpdesk.worldbank.org/knowledgebase/topics/125589)
- [Census API Documentation](https://www.census.gov/data/developers/guidance.html)

## 🤝 Contributing

When adding new tests:

1. Follow the existing test structure
2. Include debug output for verification
3. Add appropriate markers (`@pytest.mark.network`, etc.)
4. Update this README if adding new test files
5. Ensure coverage remains above 85%

## 📞 Support

For issues or questions:
- Check the test logs in `test/logs/apisource_tests.log`
- Review the coverage report for uncovered code
- Check the main README for tool documentation


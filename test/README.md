# Test Directory - AIECS Testing Guide

**Last Updated**: December 21, 2025  
**Version**: 2.0 (Restructured for CI/CD)

This directory contains all tests for the AIECS project, organized according to the testing pyramid and clean architecture principles.

---

## 📁 New Directory Structure (2.0)

```
test/
├── conftest.py                      # ⭐ Global pytest configuration (auto-marking, fixtures)
├── fixtures/                        # 🎁 Shared test fixtures
│   ├── __init__.py
│   ├── data.py                      # Test data fixtures (CSV, JSON, documents)
│   ├── llm.py                       # LLM mocks and test clients
│   └── storage.py                   # Storage, executor, database fixtures
│
├── unit/                            # 🧪 Unit Tests (70% - Fast, isolated)
│   ├── domain/                      # Domain layer tests
│   │   ├── agent/                   # Agent domain logic
│   │   ├── community/               # Community domain
│   │   ├── context/                 # Context management
│   │   └── knowledge_graph/         # Knowledge graph domain
│   ├── infrastructure/              # Infrastructure layer tests
│   │   ├── graph_storage/           # Graph storage implementations
│   │   ├── messaging/               # Message queue, events
│   │   └── monitoring/              # Metrics, tracing
│   ├── application/                 # Application services
│   ├── llm/                         # LLM client tests
│   └── tools/                       # Tool tests (largest test suite)
│
├── integration/                     # 🔗 Integration Tests (20% - Service interactions)
│   ├── agent/                       # Agent integration tests
│   ├── knowledge_graph/             # KG integration tests
│   ├── llm/                         # LLM integration tests
│   ├── tools/                       # Tool integration tests
│   └── community/                   # Community integration tests
│
├── e2e/                             # 🌍 End-to-End Tests (10% - Real APIs)
│   ├── conftest.py                  # E2E-specific config (API keys, cost tracking)
│   ├── base.py                      # E2E base classes and utilities
│   ├── llm/                         # Real LLM API tests
│   │   ├── test_openai.py           # OpenAI/GPT tests
│   │   ├── test_googleai.py         # Google AI/Gemini tests
│   │   ├── test_vertex.py           # Vertex AI tests
│   │   └── test_xai.py              # xAI/Grok tests
│   ├── tools/                       # Real tool API tests
│   │   ├── test_search.py           # Google Custom Search
│   │   └── test_apisource.py        # FRED, NewsAPI
│   └── workflows/                   # Complete workflow tests
│       └── test_agent_workflows.py  # Agent + LLM + Tools
│
├── performance/                     # ⚡ Performance Tests (Manual)
│
├── archived/                        # 🗄️ Archived tests (obsolete/broken)
│   ├── README.md                    # Archiving documentation
│   └── [archived test files]
│
└── data/                            # 📊 Test data files
    ├── sample.csv
    ├── sample.json
    ├── test_data.xlsx
    └── ...

# Old structure (maintained for compatibility)
├── unit_tests/                      # Legacy unit tests (being migrated)
├── integration_tests/               # Legacy integration tests
├── community_test/                  # Legacy community tests
├── performance_tests/               # Legacy performance tests
├── configs/                         # Legacy config files
└── scripts/                         # Legacy test scripts
```

---

## 🎯 Testing Pyramid

Our tests follow the testing pyramid principle:

```
       /\
      /E2E\       10% (~24 tests) - Real APIs, workflows
     /----\       Cost: ~$0.05/run
    / Int \       20% (~150 tests) - Redis, PostgreSQL
   /-------\      Duration: ~5 minutes
  /  Unit  \      70% (~3,500 tests) - Mocked, fast
 /---------\      Duration: ~1 minute
```

### Test Distribution

| Type | Count | Duration | Frequency | Cost |
|------|-------|----------|-----------|------|
| **Unit** | ~3,500 | < 1 min | Every push | Free |
| **Integration** | ~150 | < 5 min | Push to main | Free |
| **E2E** | ~24 | < 15 min | Weekly/Release | ~$0.05 |
| **Performance** | ~10 | < 2 min | Manual | Free |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
poetry install

# Install dev dependencies (includes pytest, pytest-cov, pytest-asyncio, etc.)
poetry install --with dev

# Verify installation
poetry run pytest --version
```

### Run All Tests (Basic)

```bash
# Run all tests (unit + integration + e2e)
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run with coverage
poetry run pytest --cov=aiecs --cov-report=html
```

---

## 🧪 Running Tests by Type

### 1. Unit Tests (Fast, No External Dependencies)

**Run all unit tests:**
```bash
poetry run pytest test/unit/ -m unit
```

**Run by domain:**
```bash
# Domain layer
poetry run pytest test/unit/domain/

# Infrastructure layer
poetry run pytest test/unit/infrastructure/

# LLM clients
poetry run pytest test/unit/llm/

# Tools (largest suite)
poetry run pytest test/unit/tools/
```

**Run specific test file:**
```bash
poetry run pytest test/unit/tools/test_pandas_tool.py -v
```

**With coverage:**
```bash
poetry run pytest test/unit/ -m unit \
  --cov=aiecs \
  --cov-report=html \
  --cov-report=term-missing
```

---

### 2. Integration Tests (Requires Services)

**Prerequisites:**
- Redis (port 6379)
- PostgreSQL (port 5432) - optional

**Start services with Docker:**
```bash
# Start Redis
docker run -d --name redis-test -p 6379:6379 redis:7-alpine

# Start PostgreSQL (if needed)
docker run -d --name postgres-test \
  -e POSTGRES_USER=test_user \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=test_db \
  -p 5432:5432 \
  postgres:15-alpine
```

**Run integration tests:**
```bash
# All integration tests
poetry run pytest test/integration/ -m integration

# By category
poetry run pytest test/integration/agent/
poetry run pytest test/integration/knowledge_graph/
poetry run pytest test/integration/llm/
```

**With environment variables:**
```bash
REDIS_HOST=localhost REDIS_PORT=6379 \
poetry run pytest test/integration/ -m integration
```

**Stop services:**
```bash
docker stop redis-test postgres-test
docker rm redis-test postgres-test
```

---

### 3. E2E Tests (Requires API Keys)

**⚠️ Warning**: E2E tests use real API keys and may incur costs (~$0.05 per run)

**Prerequisites:**

1. Create `.env` file in project root:
```bash
# Copy example
cp .env.example .env

# Edit .env with your API keys
nano .env
```

2. Required API keys:
```bash
# LLM Providers
OPENAI_API_KEY=sk-...
GOOGLEAI_API_KEY=...
VERTEX_PROJECT_ID=your-project
VERTEX_LOCATION=us-central1
XAI_API_KEY=...

# Tools
GOOGLE_CSE_ID=...
GOOGLE_CSE_API_KEY=...
```

**Run E2E tests:**

```bash
# All E2E tests (costs ~$0.05)
poetry run pytest test/e2e/ -m e2e

# By provider (cheaper)
poetry run pytest test/e2e/ -m "e2e and openai"     # OpenAI only
poetry run pytest test/e2e/ -m "e2e and google"     # Google AI only
poetry run pytest test/e2e/ -m "e2e and vertex"     # Vertex AI only
poetry run pytest test/e2e/ -m "e2e and xai"        # xAI only

# By category
poetry run pytest test/e2e/llm/                     # All LLM tests
poetry run pytest test/e2e/tools/                   # All tool tests
poetry run pytest test/e2e/workflows/               # All workflow tests

# Specific test file
poetry run pytest test/e2e/llm/test_openai.py -v

# Exclude expensive tests
poetry run pytest test/e2e/ -m "e2e and not expensive"
```

**Cost Estimates:**
- Single provider test: ~$0.00003 (OpenAI) to $0.000005 (Google)
- Search test: ~$0.01
- Full E2E suite: < $0.05

---

### 4. Performance Tests

```bash
# Run performance tests
poetry run pytest test/performance/ -m performance

# With profiling
poetry run pytest test/performance/ -m performance --profile
```

---

## 🎯 Using Test Markers

Pytest markers allow selective test execution:

### Primary Test Level Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only E2E tests
pytest -m e2e

# Run only performance tests
pytest -m performance
```

### Dependency Markers

```bash
# Tests requiring API keys
pytest -m requires_api

# Tests requiring Redis
pytest -m requires_redis

# Tests requiring PostgreSQL
pytest -m requires_postgres
```

### Provider-Specific Markers (E2E)

```bash
# OpenAI tests
pytest -m "e2e and openai"

# Google AI tests
pytest -m "e2e and google"

# Vertex AI tests
pytest -m "e2e and vertex"

# xAI tests
pytest -m "e2e and xai"
```

### Special Markers

```bash
# Exclude slow tests
pytest -m "not slow"

# Exclude expensive tests (high API cost)
pytest -m "not expensive"

# Security tests only
pytest -m security

# Async tests
pytest -m asyncio
```

### Combining Markers

```bash
# Unit tests only, excluding slow tests
pytest -m "unit and not slow"

# E2E tests for OpenAI only
pytest -m "e2e and openai"

# Integration tests requiring Redis
pytest -m "integration and requires_redis"

# All tests except E2E
pytest -m "not e2e"
```

---

## 📊 Coverage Reports

### Generate Coverage Report

```bash
# HTML report (best for browsing)
poetry run pytest test/unit/ -m unit \
  --cov=aiecs \
  --cov-report=html \
  --cov-report=term-missing

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage by Test Type

```bash
# Unit test coverage
pytest test/unit/ -m unit --cov=aiecs --cov-report=html

# Integration test coverage
pytest test/integration/ -m integration --cov=aiecs --cov-report=html

# Combined coverage
pytest test/unit/ test/integration/ \
  -m "unit or integration" \
  --cov=aiecs \
  --cov-report=html
```

### Coverage Thresholds

```bash
# Fail if coverage below 80%
pytest --cov=aiecs --cov-fail-under=80
```

---

## 🔧 Advanced Testing

### Run Tests in Parallel

```bash
# Install pytest-xdist
poetry add --dev pytest-xdist

# Run with 4 workers
pytest -n 4 test/unit/

# Auto-detect CPU cores
pytest -n auto test/unit/
```

### Run Tests with Timeout

```bash
# Default timeout: 300 seconds (5 minutes)
pytest test/unit/

# Custom timeout
pytest test/unit/ --timeout=60
```

### Debug Failing Tests

```bash
# Stop on first failure
pytest -x test/unit/

# Drop into debugger on failure
pytest --pdb test/unit/

# Show local variables on failure
pytest -l test/unit/

# Verbose traceback
pytest --tb=long test/unit/
```

### Re-run Failed Tests

```bash
# Run tests, save failures
pytest test/unit/ --lf

# Run only last failed tests
pytest --lf

# Run failed first, then others
pytest --ff
```

---

## 🧹 Clean Cache Before Testing

Sometimes pytest cache can cause false positives/negatives:

```bash
# Clean all cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
rm -rf .pytest_cache

# Clean coverage data
rm -rf .coverage htmlcov/

# Then run tests
poetry run pytest test/unit/
```

---

## 🎭 Test Fixtures

### Global Fixtures (test/conftest.py)

Available to all tests:
- `event_loop` - Async event loop
- `test_data_dir` - Path to test data directory
- `setup_test_environment` - Environment setup (auto-used)

### Data Fixtures (test/fixtures/data.py)

- `sample_csv_file` - Sample CSV file
- `temp_csv_file` - Temporary CSV for testing
- `stats_test_data` - Statistical test data
- `large_test_data` - Large dataset for performance tests
- `sample_json_data` - JSON test data
- `sample_documents` - Document fixtures

### LLM Fixtures (test/fixtures/llm.py)

- `mock_llm_client` - Mock LLM client
- `mock_openai_client` - Mock OpenAI client
- `mock_google_client` - Mock Google AI client
- `mock_vertex_client` - Mock Vertex client
- `llm_config` - LLM configuration
- `sample_chat_messages` - Test chat messages

### Storage Fixtures (test/fixtures/storage.py)

- `temp_dir` - Temporary directory
- `temp_file` - Temporary file
- `tool_executor` - Tool executor instance
- `operation_executor` - Operation executor
- `mock_storage` - Mock storage backend
- `redis_config` - Redis configuration
- `postgres_config` - PostgreSQL configuration

### E2E Fixtures (test/e2e/conftest.py)

- `openai_api_key` - OpenAI API key from env
- `google_api_key` - Google API key
- `vertex_config` - Vertex AI config
- `xai_api_key` - xAI API key
- `google_cse_config` - Google CSE config
- `cost_tracker` - API call cost tracking

---

## 📝 Writing New Tests

### Unit Test Template

```python
"""
Unit tests for MyModule.

Tests the core functionality of MyModule with mocked dependencies.
"""

import pytest
from aiecs.module import MyModule


@pytest.mark.unit
class TestMyModule:
    """Unit tests for MyModule."""
    
    def test_basic_functionality(self):
        """Test basic functionality."""
        module = MyModule()
        result = module.do_something()
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        module = MyModule()
        result = await module.do_something_async()
        assert result is not None
```

### Integration Test Template

```python
"""
Integration tests for MyModule.

Tests MyModule with real services (Redis, PostgreSQL).
"""

import pytest


@pytest.mark.integration
@pytest.mark.requires_redis
class TestMyModuleIntegration:
    """Integration tests for MyModule."""
    
    def test_with_redis(self, redis_config):
        """Test with real Redis connection."""
        # Test implementation
        pass
```

### E2E Test Template

```python
"""
E2E tests for MyWorkflow.

Tests complete workflow with real APIs.
"""

import pytest
from test.e2e.base import E2ETestBase


@pytest.mark.e2e
@pytest.mark.expensive
@pytest.mark.requires_api
class TestMyWorkflowE2E(E2ETestBase):
    """E2E tests for MyWorkflow."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, openai_api_key, cost_tracker):
        """Test complete workflow with real API."""
        # Test implementation
        pass
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Ensure project is installed
poetry install

# Check Python path
poetry run python -c "import aiecs; print(aiecs.__file__)"
```

#### 2. Service Connection Errors
```bash
# Check services are running
docker ps

# Test Redis connection
redis-cli ping

# Test PostgreSQL connection
psql -h localhost -U test_user -d test_db
```

#### 3. E2E Tests Skipped
- **Cause**: API keys not configured
- **Solution**: Add keys to `.env` file

#### 4. Tests Hang or Timeout
- Check for infinite loops
- Verify service connectivity
- Increase timeout in `pyproject.toml`

#### 5. Flaky Tests
- Clean cache: `rm -rf .pytest_cache`
- Run in isolation: `pytest test/path/to/test.py::test_name`
- Check for race conditions in async tests

---

## 📚 Additional Resources

- **Main Documentation**: `/docs/`
- **CI/CD Workflows**: `/.github/workflows/README.md`
- **OpenSpec Changes**: `/openspec/changes/add-cicd-testing-workflow/`
- **Archived Tests**: `/test/archived/README.md`

### External Documentation

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Poetry Documentation](https://python-poetry.org/docs/)

---

## 🤝 Contributing

When adding new tests:

1. **Choose the right directory**: 
   - `unit/` for isolated, fast tests
   - `integration/` for service interaction tests
   - `e2e/` for end-to-end workflow tests

2. **Use appropriate markers**:
   - Add `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.e2e`
   - Auto-marking applies based on directory (see `test/conftest.py`)

3. **Follow naming conventions**:
   - Test files: `test_*.py`
   - Test classes: `Test*`
   - Test functions: `test_*`

4. **Keep tests fast**:
   - Unit: < 1 second
   - Integration: < 5 seconds
   - E2E: < 30 seconds

5. **Use fixtures**:
   - Reuse fixtures from `test/fixtures/`
   - Create domain-specific fixtures in subdirectory `conftest.py`

6. **Document tests**:
   - Add docstrings to test classes and methods
   - Explain what is being tested and why

7. **Update this README**:
   - When adding new test categories
   - When adding new fixtures
   - When changing test structure

---

## 📊 Test Statistics

**Current Test Count** (as of Dec 21, 2025):

| Category | Old Location | New Location | Count |
|----------|-------------|--------------|-------|
| Unit - Tools | `unit_tests/tools/` | `unit/tools/` | ~26 files |
| Unit - Domain | `unit_tests/agent/` | `unit/domain/` | ~15 files |
| Unit - Infrastructure | `unit_tests/graph_storage/` | `unit/infrastructure/` | ~12 files |
| Integration | `integration_tests/` | `integration/` | ~15 files |
| E2E (New) | N/A | `e2e/` | 8 files, 24+ tests |
| Performance | `performance_tests/` | `performance/` | ~10 files |
| Community | `community_test/` | `integration/community/` | ~12 files |

**Total**: ~3,700+ tests across all categories

---

## 🎯 CI/CD Integration

Tests are automatically run in GitHub Actions:

- **Unit Tests**: Every push/PR (Python 3.11 & 3.12)
- **Integration Tests**: Push/PR to main
- **Code Quality**: Every push/PR (Black, Flake8, MyPy, Bandit)
- **E2E Tests**: Manual, release, or weekly

See `.github/workflows/README.md` for details.

---

**Maintained By**: AIECS Team  
**Last Updated**: December 21, 2025  
**Version**: 2.0

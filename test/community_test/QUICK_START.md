# Community Tests - Quick Start Guide

## 🚀 Quick Commands

### Run All Tests
```bash
poetry run pytest test/community_test/ -v
```

### Run with Coverage (HTML Report)
```bash
poetry run pytest test/community_test/ \
  --cov=aiecs/domain/community \
  --cov-report=html \
  --cov-report=term-missing
```

### View Coverage Report
```bash
xdg-open htmlcov/index.html
```

### Run Specific Test File
```bash
# Community manager tests
poetry run pytest test/community_test/test_community_manager.py -v

# Decision engine tests
poetry run pytest test/community_test/test_decision_engine.py -v

# Analytics tests
poetry run pytest test/community_test/test_analytics.py -v

# Communication tests
poetry run pytest test/community_test/test_communication.py -v
```

### Run Single Test
```bash
poetry run pytest test/community_test/test_community_manager.py::TestCommunityCreation::test_create_basic_community -v
```

### Quick Test (No Coverage)
```bash
poetry run pytest test/community_test/ -q
```

### With Debug Logging
```bash
poetry run pytest test/community_test/ -v --log-cli-level=DEBUG
```

### Quiet Mode
```bash
poetry run pytest test/community_test/ -q --tb=no
```

## 📊 Current Status

- **73/79 tests passing** (92.4% pass rate)
- **66.80% code coverage**
- **~20 seconds** execution time

## 🎯 Test Organization

```
test/community_test/
├── __init__.py                      # Package init
├── conftest.py                      # Shared fixtures
├── test_analytics.py                # Analytics & metrics (9 tests)
├── test_communication.py            # Messaging & events (11 tests)
├── test_community_manager.py        # Core management (34 tests)
├── test_decision_engine.py          # Decisions & voting (9 tests)
├── test_integration.py              # Integration scenarios (10 tests)
├── test_resource_manager.py         # Resources (13 tests, 6 failing)
├── test_shared_context.py           # Context sharing (13 tests)
├── README.md                        # Full documentation
├── TEST_SUMMARY.md                  # Detailed results
└── QUICK_START.md                   # This file
```

## 🔧 Troubleshooting

### Tests Timeout
```bash
poetry run pytest test/community_test/ --timeout=600
```

### Import Errors
Make sure you're in the project root:
```bash
cd /home/coder1/python-middleware-dev
poetry run pytest test/community_test/
```

### Can't Find pytest
Install test dependencies:
```bash
poetry add --group dev pytest pytest-asyncio pytest-cov pytest-timeout
```

## 📖 More Information

- See `README.md` for detailed test documentation
- See `TEST_SUMMARY.md` for coverage analysis
- See individual test files for specific feature tests


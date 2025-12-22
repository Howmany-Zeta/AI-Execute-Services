"""
APISource Tool Test Suite

Comprehensive tests for the APISource tool and all its components.
Tests real functionality without mocks to verify actual behavior.

Test Structure:
- test_apisource_tool.py: Main tool functionality
- test_providers.py: All API providers (FRED, News API, World Bank, Census)
- test_intelligence.py: Intelligence modules (query analyzer, data fusion, search enhancer)
- test_reliability.py: Reliability modules (error handler, fallback strategy)
- test_monitoring.py: Monitoring and metrics
- test_utils.py: Utility functions and validators
- test_integration.py: End-to-end integration tests

Run all tests:
    poetry run pytest test/unit_tests/tools/apisource -v -s

Run with coverage:
    poetry run pytest test/unit_tests/tools/apisource --cov=aiecs.tools.apisource --cov-report=html --cov-report=term-missing

Run specific test file:
    poetry run pytest test/unit_tests/tools/apisource/test_providers.py -v -s

Run with markers:
    poetry run pytest test/unit_tests/tools/apisource -m "not network" -v
    poetry run pytest test/unit_tests/tools/apisource -m "network" -v
    poetry run pytest test/unit_tests/tools/apisource -m "integration" -v
"""


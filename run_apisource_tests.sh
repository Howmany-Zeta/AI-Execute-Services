#!/bin/bash
# Run APISource tests with API keys from .env.apisource

# Load environment variables from .env.apisource
if [ -f ".env.apisource" ]; then
    # Use set -a to automatically export all variables
    set -a
    source .env.apisource
    set +a

    echo "✓ Loaded environment variables from .env.apisource"
    echo "  FRED_API_KEY: ${FRED_API_KEY:0:10}..."
    echo "  NEWSAPI_API_KEY: ${NEWSAPI_API_KEY:0:10}..."
    echo "  CENSUS_API_KEY: ${CENSUS_API_KEY:0:10}..."
else
    echo "⚠ .env.apisource not found"
fi

# Run tests
poetry run pytest test/unit_tests/tools/test_apisource_tool.py \
    --cov=aiecs.tools.task_tools.apisource_tool \
    --cov=aiecs.tools.api_sources \
    --cov-report=term-missing \
    --cov-report=html:test/coverage_reports/htmlcov_apisource \
    --cov-fail-under=85 \
    -v -s \
    "$@"


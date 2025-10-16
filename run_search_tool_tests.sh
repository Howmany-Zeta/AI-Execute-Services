#!/bin/bash
#
# Run SearchTool Tests with Coverage
#
# Usage:
#   ./run_search_tool_tests.sh              # Run all tests
#   ./run_search_tool_tests.sh unit         # Run only unit tests
#   ./run_search_tool_tests.sh integration  # Run only integration tests
#   ./run_search_tool_tests.sh coverage     # Run with detailed coverage report
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  SearchTool Test Runner${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check for .env.search file
if [ ! -f ".env.search" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env.search file not found${NC}"
    echo "   Integration tests will be skipped without API credentials"
    echo "   Create .env.search with:"
    echo "     GOOGLE_API_KEY=your_api_key"
    echo "     GOOGLE_CSE_ID=your_cse_id"
    echo ""
fi

# Determine test mode
MODE=${1:-all}

case $MODE in
    unit)
        echo -e "${GREEN}Running unit tests only...${NC}"
        poetry run pytest test/unit_tests/tools/test_search_tool.py \
            --cov=aiecs.tools.search_tool \
            --cov-report=term-missing \
            --cov-report=html:test/coverage_reports/htmlcov_search_tool \
            -v -s \
            -m "not integration" \
            "${@:2}"
        ;;
    
    integration)
        echo -e "${GREEN}Running integration tests only...${NC}"
        poetry run pytest test/unit_tests/tools/test_search_tool_integration.py \
            -v -s \
            -m integration \
            "${@:2}"
        ;;
    
    coverage)
        echo -e "${GREEN}Running all tests with detailed coverage...${NC}"
        poetry run pytest test/unit_tests/tools/test_search_tool.py \
            test/unit_tests/tools/test_search_tool_integration.py \
            --cov=aiecs.tools.search_tool \
            --cov-report=term-missing \
            --cov-report=html:test/coverage_reports/htmlcov_search_tool \
            --cov-fail-under=80 \
            -v -s \
            "${@:2}"
        
        echo ""
        echo -e "${GREEN}Coverage report generated at:${NC}"
        echo "  test/coverage_reports/htmlcov_search_tool/index.html"
        ;;
    
    all|*)
        echo -e "${GREEN}Running all tests...${NC}"
        poetry run pytest test/unit_tests/tools/test_search_tool.py \
            test/unit_tests/tools/test_search_tool_integration.py \
            --cov=aiecs.tools.search_tool \
            --cov-report=term-missing \
            --cov-report=html:test/coverage_reports/htmlcov_search_tool \
            -v -s \
            "${@:2}"
        ;;
esac

echo ""
echo -e "${GREEN}✓ Tests completed${NC}"


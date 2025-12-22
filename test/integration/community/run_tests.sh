#!/bin/bash
# Community Domain Test Suite Runner

echo "=================================="
echo "Community Domain Module Test Suite"
echo "=================================="
echo ""

cd /home/coder1/python-middleware-dev

echo "📋 Running tests with coverage..."
echo ""

poetry run pytest test/community_test/ \
  --cov=aiecs/domain/community \
  --cov-report=html \
  --cov-report=term-missing \
  -v \
  --tb=short

echo ""
echo "=================================="
echo "✅ Test run complete!"
echo ""
echo "📊 Coverage report saved to: htmlcov/index.html"
echo ""
echo "To view the HTML report:"
echo "  xdg-open htmlcov/index.html"
echo ""
echo "Or on Mac:"
echo "  open htmlcov/index.html"
echo ""
echo "=================================="



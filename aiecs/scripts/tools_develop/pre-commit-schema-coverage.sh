#!/bin/bash
# Pre-commit hook for schema coverage validation
# This script can be used as a git pre-commit hook or standalone

set -e

# Configuration
MIN_COVERAGE=${MIN_COVERAGE:-90}
VERBOSE=${VERBOSE:-false}

echo "🔍 Checking schema coverage for all tools..."
echo "Minimum coverage threshold: ${MIN_COVERAGE}%"

# Run schema coverage check
if command -v aiecs-tools-schema-coverage &> /dev/null; then
    # Use CLI command if available
    if [ "$VERBOSE" = "true" ]; then
        aiecs-tools-schema-coverage --min-coverage "$MIN_COVERAGE" --format json > /tmp/schema_coverage_check.json
    else
        aiecs-tools-schema-coverage --min-coverage "$MIN_COVERAGE" --format json > /tmp/schema_coverage_check.json 2>/dev/null
    fi
    
    # Parse JSON to check if any tools are below threshold
    python3 << EOF
import json
import sys

try:
    with open('/tmp/schema_coverage_check.json', 'r') as f:
        data = json.load(f)
    
    summary = data.get('summary', {})
    coverage = summary.get('coverage_percentage', 0)
    
    if coverage < $MIN_COVERAGE:
        print(f"❌ Schema coverage is {coverage:.1f}%, below threshold of $MIN_COVERAGE%")
        sys.exit(1)
    else:
        print(f"✅ Schema coverage is {coverage:.1f}%, meets threshold of $MIN_COVERAGE%")
        
        # Check individual tools
        tools_below_threshold = []
        for tool_name, tool_data in data.get('tools', {}).items():
            tool_coverage = tool_data.get('coverage_percentage', 0)
            if tool_coverage < $MIN_COVERAGE:
                tools_below_threshold.append((tool_name, tool_coverage))
        
        if tools_below_threshold:
            print(f"\n⚠️  {len(tools_below_threshold)} tool(s) below threshold:")
            for tool_name, coverage in sorted(tools_below_threshold, key=lambda x: x[1]):
                print(f"   - {tool_name}: {coverage:.1f}%")
            sys.exit(1)
        
        sys.exit(0)
except Exception as e:
    print(f"Error checking coverage: {e}")
    sys.exit(1)
EOF

else
    # Fallback to Python module
    python3 -m aiecs.scripts.tools_develop.validate_tool_schemas --min-coverage "$MIN_COVERAGE" --export-coverage /tmp/schema_coverage.json
fi

echo "✅ Schema coverage check passed!"


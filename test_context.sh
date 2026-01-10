#!/bin/bash
# Test script to verify context parameter support

echo "Testing context parameter support across LLM clients and agents..."
echo ""

poetry run python test_context_parameter.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ All context parameter tests passed!"
else
    echo ""
    echo "✗ Context parameter tests failed!"
    exit 1
fi


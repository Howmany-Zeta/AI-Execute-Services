#!/bin/bash

# Script to run the weasel library patch using poetry
# This ensures we're working within the correct virtual environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Running Weasel Library Patch via Poetry"
echo "=========================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Please run this script from the python-middleware directory"
    exit 1
fi

# Check if poetry is available
if ! command -v poetry &> /dev/null; then
    echo "❌ Error: Poetry is not installed or not in PATH"
    echo "Please install poetry first: https://python-poetry.org/docs/#installation"
    exit 1
fi

# Run the Python patch script using poetry
echo "🚀 Running patch script with poetry..."
poetry run python3 scripts/fix_weasel_validator.py

echo ""
echo "🎉 Patch execution completed!"
echo ""
echo "Next steps:"
echo "1. Try running your tests again with: poetry run pytest"
echo "2. If the issue persists, you may need to restart your development environment"

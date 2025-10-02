#!/bin/bash

# Comprehensive script to fix weasel library duplicate validator function error
# This script provides multiple approaches to patch the issue

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Weasel Library Patcher"
echo "========================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Function to check if we're in the right directory
check_project_structure() {
    if [ ! -f "$PROJECT_DIR/pyproject.toml" ]; then
        echo "❌ Error: pyproject.toml not found. Please run this script from the python-middleware directory"
        exit 1
    fi
}

# Function to get poetry virtual environment path
get_venv_path() {
    cd "$PROJECT_DIR"
    local venv_path
    venv_path=$(poetry env info --path 2>/dev/null || echo "")

    if [ -z "$venv_path" ]; then
        echo "❌ Error: Could not find poetry virtual environment"
        echo "Please make sure poetry is installed and the virtual environment is created"
        echo "Try running: poetry install"
        exit 1
    fi

    echo "$venv_path"
}

# Function to apply the patch
apply_patch() {
    local venv_path="$1"
    local schemas_file="$venv_path/lib/python3.10/site-packages/weasel/schemas.py"

    echo "📁 Target file: $schemas_file"

    if [ ! -f "$schemas_file" ]; then
        echo "❌ Error: weasel schemas.py file not found"
        echo "The weasel package might not be installed or in a different location"
        exit 1
    fi

    # Create backup
    local backup_file="${schemas_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$schemas_file" "$backup_file"
    echo "💾 Backup created: $backup_file"

    # Check if already patched
    if grep -q "allow_reuse=True" "$schemas_file"; then
        echo "✅ File already contains allow_reuse=True - may already be patched"
        echo "Checking if the specific issue is resolved..."
    fi

    # Show current problematic content
    echo ""
    echo "📖 Current content around the problematic area:"
    echo "------------------------------------------------"
    sed -n '85,95p' "$schemas_file" | nl -ba -v85
    echo "------------------------------------------------"
    echo ""

    # Apply the patch using Python for more precise control
    python3 << EOF
import re
import sys

schemas_file = "$schemas_file"

try:
    with open(schemas_file, 'r') as f:
        content = f.read()

    # Pattern to find @validator and @root_validator decorators that need allow_reuse=True
    # Look for the specific problematic validator
    pattern = r'(@(?:root_)?validator\([^)]*\))\s*\n(\s*def\s+check_legacy_keys)'

    def fix_validator(match):
        decorator = match.group(1)
        func_def = match.group(2)

        # Add allow_reuse=True if not present
        if 'allow_reuse' not in decorator:
            # Remove the closing parenthesis and add allow_reuse=True
            fixed_decorator = decorator[:-1] + ', allow_reuse=True)'
            return fixed_decorator + '\n' + func_def
        return match.group(0)

    # Apply the fix
    fixed_content = re.sub(pattern, fix_validator, content)

    # Also fix any other @validator or @root_validator decorators that might have the same issue
    general_pattern = r'(@(?:root_)?validator\([^)]*)\)(?=\s*\n\s*def)'

    def fix_general_validator(match):
        decorator = match.group(1)
        if 'allow_reuse' not in decorator:
            return decorator + ', allow_reuse=True)'
        return match.group(0)

    fixed_content = re.sub(general_pattern, fix_general_validator, fixed_content)

    # Write back the fixed content
    with open(schemas_file, 'w') as f:
        f.write(fixed_content)

    print("✅ Patch applied successfully")

except Exception as e:
    print(f"❌ Error applying patch: {e}")
    sys.exit(1)
EOF

    # Show the patched content
    echo ""
    echo "📖 Patched content:"
    echo "-------------------"
    sed -n '85,95p' "$schemas_file" | nl -ba -v85
    echo "-------------------"
    echo ""

    # Verify the patch
    if grep -q "allow_reuse=True" "$schemas_file"; then
        echo "✅ Verification: allow_reuse=True found in the file"
    else
        echo "⚠️  Warning: allow_reuse=True not found after patching"
    fi

    echo "💾 Original file backed up to: $backup_file"
}

# Function to test the fix
test_fix() {
    echo ""
    echo "🧪 Testing the fix..."
    cd "$PROJECT_DIR"

    # Try to import the problematic module
    if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from aiecs.tools.task_tools.research_tool import *
    print('✅ Import successful - fix appears to work!')
except Exception as e:
    print(f'❌ Import still fails: {e}')
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ Fix verification successful!"
    else
        echo "⚠️  Fix verification failed - you may need to restart your Python environment"
    fi
}

# Main execution
main() {
    echo "Starting patch process..."

    check_project_structure

    local venv_path
    venv_path=$(get_venv_path)
    echo "📍 Virtual environment: $venv_path"

    apply_patch "$venv_path"

    test_fix

    echo ""
    echo "🎉 Weasel library patch completed!"
    echo ""
    echo "Next steps:"
    echo "1. Try running your tests again"
    echo "2. If the issue persists, you may need to restart your Python environment"
    echo "3. To revert changes, restore from the backup file shown above"
}

# Run the main function
main "$@"

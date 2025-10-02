#!/bin/bash

# Script to fix weasel library duplicate validator function error
# This script patches the weasel schemas.py file to add allow_reuse=True

set -e

echo "🔧 Starting weasel library patch for duplicate validator function..."

# Get the poetry virtual environment path
VENV_PATH=$(poetry env info --path 2>/dev/null || echo "")

if [ -z "$VENV_PATH" ]; then
    echo "❌ Error: Could not find poetry virtual environment"
    echo "Please make sure you're in the project directory and poetry is installed"
    exit 1
fi

echo "📍 Found virtual environment at: $VENV_PATH"

# Path to the problematic weasel schemas.py file
WEASEL_SCHEMAS_FILE="$VENV_PATH/lib/python3.10/site-packages/weasel/schemas.py"

if [ ! -f "$WEASEL_SCHEMAS_FILE" ]; then
    echo "❌ Error: weasel schemas.py file not found at $WEASEL_SCHEMAS_FILE"
    exit 1
fi

echo "📁 Found weasel schemas.py at: $WEASEL_SCHEMAS_FILE"

# Create backup of original file
BACKUP_FILE="${WEASEL_SCHEMAS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
cp "$WEASEL_SCHEMAS_FILE" "$BACKUP_FILE"
echo "💾 Created backup at: $BACKUP_FILE"

# Check if the file already has allow_reuse=True
if grep -q "allow_reuse=True" "$WEASEL_SCHEMAS_FILE"; then
    echo "✅ File already patched with allow_reuse=True"
    exit 0
fi

# Apply the patch using sed
# Look for @validator and @root_validator decorators and add allow_reuse=True if not present
echo "🔨 Applying patch..."

# First, let's check the current content around the problematic line
echo "📖 Current content around line 89:"
sed -n '85,95p' "$WEASEL_SCHEMAS_FILE"

# Apply the patch - add allow_reuse=True to validator decorators that don't have it
sed -i.tmp '
/^[[:space:]]*@\(root_\)\?validator(/,/^[[:space:]]*def/ {
    /^[[:space:]]*@\(root_\)\?validator(/ {
        # If the line contains @validator or @root_validator but not allow_reuse, add it
        /allow_reuse/! {
            s/@\(root_\)\?validator(\([^)]*\))/@\1validator(\2, allow_reuse=True)/
        }
    }
}
' "$WEASEL_SCHEMAS_FILE"

# Remove the temporary file
rm -f "${WEASEL_SCHEMAS_FILE}.tmp"

echo "✅ Patch applied successfully!"

# Show the patched content
echo "📖 Patched content around line 89:"
sed -n '85,95p' "$WEASEL_SCHEMAS_FILE"

# Verify the patch by checking if allow_reuse=True is now present
if grep -q "allow_reuse=True" "$WEASEL_SCHEMAS_FILE"; then
    echo "✅ Verification successful: allow_reuse=True found in file"
else
    echo "⚠️  Warning: allow_reuse=True not found after patching"
fi

echo "🎉 Weasel library patch completed!"
echo "📝 Backup saved at: $BACKUP_FILE"
echo ""
echo "You can now run your tests again. If you need to revert the changes:"
echo "cp '$BACKUP_FILE' '$WEASEL_SCHEMAS_FILE'"

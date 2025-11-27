#!/usr/bin/env python3
"""
Script to fix weasel library duplicate validator function error.
This script patches the weasel schemas.py file to add allow_reuse=True to duplicate validators.
"""

import os
import sys
import shutil
from datetime import datetime
import re


def get_weasel_path():
    """Get the weasel package path in the current Python environment."""
    try:
        import weasel  # type: ignore[import-untyped]
        import inspect

        weasel_file = inspect.getfile(weasel)
        weasel_dir = os.path.dirname(weasel_file)
        return os.path.join(weasel_dir, "schemas.py")
    except ImportError:
        print("❌ Error: weasel package not found")
        print("Please install aiecs with all dependencies")
        return None
    except Exception as e:
        print(f"❌ Error finding weasel package: {e}")
        return None


def backup_file(file_path):
    """Create a backup of the file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.backup.{timestamp}"
    shutil.copy2(file_path, backup_path)
    return backup_path


def fix_weasel_schemas(schemas_file_path):
    """Fix the weasel schemas.py file by adding allow_reuse=True to validators."""

    print(f"📁 Processing file: {schemas_file_path}")

    # Read the original file
    with open(schemas_file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already patched
    if "allow_reuse=True" in content:
        print("✅ File already patched with allow_reuse=True")
        return True

    # Create backup
    backup_path = backup_file(schemas_file_path)
    print(f"💾 Created backup at: {backup_path}")

    # Show current problematic area
    lines = content.split("\n")
    print("\n📖 Current content around line 89:")
    for i, line in enumerate(lines[84:94], 85):
        print(f"{i:3d} | {line}")

    # Pattern to match both @validator and @root_validator decorators without
    # allow_reuse
    validator_pattern = r"(@(?:root_)?validator\([^)]*)\)(?!\s*,\s*allow_reuse=True)"

    # Replace @validator(...) or @root_validator(...) with allow_reuse=True if
    # not already present
    def replace_validator(match):
        validator_call = match.group(1)
        # Check if allow_reuse is already in the parameters
        if "allow_reuse" in validator_call:
            return match.group(0)  # Return unchanged
        else:
            return f"{validator_call}, allow_reuse=True)"

    # Apply the fix
    fixed_content = re.sub(validator_pattern, replace_validator, content)

    # Write the fixed content back
    with open(schemas_file_path, "w", encoding="utf-8") as f:
        f.write(fixed_content)

    # Show the fixed content
    fixed_lines = fixed_content.split("\n")
    print("\n📖 Patched content around line 89:")
    for i, line in enumerate(fixed_lines[84:94], 85):
        print(f"{i:3d} | {line}")

    # Verify the fix
    if "allow_reuse=True" in fixed_content:
        print("✅ Verification successful: allow_reuse=True found in file")
        return True
    else:
        print("⚠️  Warning: allow_reuse=True not found after patching")
        return False


def main():
    """Main function to execute the patch."""
    print("🔧 Starting weasel library patch for duplicate validator function...")

    # Get weasel schemas.py path
    schemas_file = get_weasel_path()
    if not schemas_file:
        sys.exit(1)

    print(f"📍 Found weasel schemas.py at: {schemas_file}")

    if not os.path.exists(schemas_file):
        print(f"❌ Error: weasel schemas.py file not found at {schemas_file}")
        sys.exit(1)

    # Apply the fix
    success = fix_weasel_schemas(schemas_file)

    if success:
        print("\n🎉 Weasel library patch completed successfully!")
        print("\nYou can now run your tests again.")
        print("\nIf you need to revert the changes, restore from the backup file.")
    else:
        print("\n❌ Patch may not have been applied correctly. Please check manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()

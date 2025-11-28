#!/usr/bin/env python3
"""
AIECS Version Manager

A script to manage version numbers across multiple files in the AIECS project.
Updates version numbers in:
- aiecs/__init__.py (__version__)
- aiecs/main.py (FastAPI app version and health check version)
- pyproject.toml (project version)

Usage:
    aiecs-version --version 1.2.0
    aiecs-version --bump patch
    aiecs-version --bump minor
    aiecs-version --bump major
    aiecs-version --show
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional, Tuple


class VersionManager:
    """Manages version numbers across AIECS project files"""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the version manager with project root path"""
        if project_root is None:
            # Find project root by looking for pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent

            if project_root is None:
                raise RuntimeError("Could not find project root (pyproject.toml)")

        self.project_root = project_root
        self.files = {
            "init": project_root / "aiecs" / "__init__.py",
            "main": project_root / "aiecs" / "main.py",
            "pyproject": project_root / "pyproject.toml",
        }

    def get_current_version(self) -> str:
        """Get the current version from __init__.py"""
        init_file = self.files["init"]
        if not init_file.exists():
            raise FileNotFoundError(f"Could not find {init_file}")

        content = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if not match:
            raise ValueError("Could not find __version__ in __init__.py")

        return match.group(1)

    def parse_version(self, version: str) -> Tuple[int, int, int]:
        """Parse version string into major, minor, patch components"""
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", version)
        if not match:
            raise ValueError(f"Invalid version format: {version}. Expected format: X.Y.Z")

        return int(match.group(1)), int(match.group(2)), int(match.group(3))

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """Bump version based on type (major, minor, patch)"""
        major, minor, patch = self.parse_version(current_version)

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', or 'patch'")

        return f"{major}.{minor}.{patch}"

    def update_init_file(self, new_version: str) -> None:
        """Update version in aiecs/__init__.py"""
        init_file = self.files["init"]
        content = init_file.read_text(encoding="utf-8")

        # Update __version__ line
        content = re.sub(
            r'(__version__\s*=\s*["\'])([^"\']+)(["\'])',
            rf"\g<1>{new_version}\g<3>",
            content,
        )

        init_file.write_text(content, encoding="utf-8")
        print(f'✓ Updated {init_file.relative_to(self.project_root)}: __version__ = "{new_version}"')

    def update_main_file(self, new_version: str) -> None:
        """Update version in aiecs/main.py"""
        main_file = self.files["main"]
        content = main_file.read_text(encoding="utf-8")

        # Update FastAPI app version
        content = re.sub(r'(version=")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content)

        # Update health check version
        content = re.sub(r'("version":\s*")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content)

        main_file.write_text(content, encoding="utf-8")
        print(f"✓ Updated {main_file.relative_to(self.project_root)}: FastAPI version and health check version")

    def update_pyproject_file(self, new_version: str) -> None:
        """Update version in pyproject.toml"""
        pyproject_file = self.files["pyproject"]
        content = pyproject_file.read_text(encoding="utf-8")

        # Update project version (only in [project] section, not in [project.scripts])
        # Use a more specific pattern that only matches within [project] section
        # Pattern: match [project] section, then find version line before next [section]
        lines = content.split('\n')
        in_project_section = False
        updated = False
        
        for i, line in enumerate(lines):
            # Check if we're entering [project] section
            if line.strip() == '[project]':
                in_project_section = True
                continue
            
            # Check if we're leaving [project] section (entering another section)
            if in_project_section and line.strip().startswith('[') and line.strip() != '[project]':
                in_project_section = False
                break
            
            # Update version line if we're in [project] section
            if in_project_section and re.match(r'^\s*version\s*=\s*"', line):
                lines[i] = re.sub(
                    r'^(\s*version\s*=\s*")([^"]+)(")',
                    rf'\g<1>{new_version}\g<3>',
                    line,
                )
                updated = True
                break
        
        if not updated:
            raise ValueError("Could not find version in [project] section of pyproject.toml")
        
        content = '\n'.join(lines)
        pyproject_file.write_text(content, encoding="utf-8")
        print(f"✓ Updated {pyproject_file.relative_to(self.project_root)}: project version")

    def update_version(self, new_version: str) -> None:
        """Update version in all files"""
        # Validate version format
        self.parse_version(new_version)

        print(f"Updating version to {new_version}...")
        print()

        # Update all files
        self.update_init_file(new_version)
        self.update_main_file(new_version)
        self.update_pyproject_file(new_version)

        print()
        print(f"✓ Successfully updated version to {new_version} in all files!")

    def show_version(self) -> None:
        """Show current version"""
        try:
            version = self.get_current_version()
            print(f"Current version: {version}")
        except Exception as e:
            print(f"Error getting current version: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point for the version manager"""
    # Always use 'aiecs-version' as program name for consistent help text
    # regardless of how the script is invoked (module or entry point)
    parser = argparse.ArgumentParser(
        prog='aiecs-version',
        description="AIECS Version Manager - Update version numbers across project files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aiecs-version --version 1.2.0          # Set specific version
  aiecs-version --bump patch             # Bump patch version (1.1.0 -> 1.1.1)
  aiecs-version --bump minor             # Bump minor version (1.1.0 -> 1.2.0)
  aiecs-version --bump major             # Bump major version (1.1.0 -> 2.0.0)
  aiecs-version --show                   # Show current version
        """,
    )

    # Create mutually exclusive group for version options
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("--version", "-v", type=str, help="Set specific version (e.g., 1.2.0)")
    version_group.add_argument(
        "--bump",
        "-b",
        choices=["major", "minor", "patch"],
        help="Bump version: major (X.0.0), minor (X.Y.0), or patch (X.Y.Z)",
    )
    version_group.add_argument("--show", "-s", action="store_true", help="Show current version")

    args = parser.parse_args()

    try:
        manager = VersionManager()

        if args.show:
            manager.show_version()
        elif args.version:
            manager.update_version(args.version)
        elif args.bump:
            current_version = manager.get_current_version()
            new_version = manager.bump_version(current_version, args.bump)
            print(f"Bumping {args.bump} version: {current_version} -> {new_version}")
            print()
            manager.update_version(new_version)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

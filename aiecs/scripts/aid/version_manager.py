#!/usr/bin/env python3
# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
AIECS Version Manager

A script to manage version numbers across multiple files in the AIECS project.
Updates version numbers in:
- aiecs/__init__.py (__version__)
- aiecs/main.py (FastAPI app version and health check version)
- pyproject.toml (project version)
- CHANGELOG.md (release section from [Unreleased])

Usage:
    aiecs-version --version 1.2.0
    aiecs-version --version 2.0.0rc2
    aiecs-version --bump patch
    aiecs-version --bump rc
    aiecs-version --show
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional


_VERSION_PATTERN = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)"
    r"(?:"
    r"(rc)(\d+)"
    r"|(a)(\d+)"
    r"|(b)(\d+)"
    r"|\.?(dev)(\d+)"
    r")?$"
)


@dataclass(frozen=True)
class ParsedVersion:
    major: int
    minor: int
    patch: int
    prerelease_kind: Optional[str] = None
    prerelease_num: Optional[int] = None

    @property
    def base(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def render(self) -> str:
        if self.prerelease_kind is None or self.prerelease_num is None:
            return self.base
        if self.prerelease_kind == "dev":
            return f"{self.base}.dev{self.prerelease_num}"
        return f"{self.base}{self.prerelease_kind}{self.prerelease_num}"


class VersionManager:
    """Manages version numbers across AIECS project files"""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the version manager with project root path"""
        if project_root is None:
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
            "changelog": project_root / "CHANGELOG.md",
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

    def parse_version(self, version: str) -> ParsedVersion:
        """Parse X.Y.Z or X.Y.ZrcN / X.Y.ZaN / X.Y.ZbN / X.Y.Z.devN."""
        match = _VERSION_PATTERN.match(version.strip())
        if not match:
            raise ValueError(
                f"Invalid version format: {version}. "
                "Expected X.Y.Z or X.Y.Z with optional rcN, aN, bN, or .devN suffix"
            )

        major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if match.group(4) == "rc":
            return ParsedVersion(major, minor, patch, "rc", int(match.group(5)))
        if match.group(6) == "a":
            return ParsedVersion(major, minor, patch, "a", int(match.group(7)))
        if match.group(8) == "b":
            return ParsedVersion(major, minor, patch, "b", int(match.group(9)))
        if match.group(10) == "dev":
            return ParsedVersion(major, minor, patch, "dev", int(match.group(11)))

        return ParsedVersion(major, minor, patch)

    def is_prerelease(self, version: str) -> bool:
        return self.parse_version(version).prerelease_kind is not None

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """Bump version based on type (major, minor, patch, rc)."""
        parsed = self.parse_version(current_version)

        if bump_type == "rc":
            if parsed.prerelease_kind == "rc" and parsed.prerelease_num is not None:
                return ParsedVersion(parsed.major, parsed.minor, parsed.patch, "rc", parsed.prerelease_num + 1).render()
            return ParsedVersion(parsed.major, parsed.minor, parsed.patch, "rc", 1).render()

        if bump_type == "major":
            parsed = ParsedVersion(parsed.major + 1, 0, 0)
        elif bump_type == "minor":
            parsed = ParsedVersion(parsed.major, parsed.minor + 1, 0)
        elif bump_type == "patch":
            parsed = ParsedVersion(parsed.major, parsed.minor, parsed.patch + 1)
        else:
            raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', 'patch', or 'rc'")

        return parsed.render()

    def update_init_file(self, new_version: str) -> None:
        """Update version in aiecs/__init__.py"""
        init_file = self.files["init"]
        content = init_file.read_text(encoding="utf-8")

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

        content = re.sub(r'(version=")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content)
        content = re.sub(r'("version":\s*")([^"]+)(")', rf"\g<1>{new_version}\g<3>", content)

        main_file.write_text(content, encoding="utf-8")
        print(f"✓ Updated {main_file.relative_to(self.project_root)}: FastAPI version and health check version")

    def update_pyproject_file(self, new_version: str) -> None:
        """Update version in pyproject.toml ([project] and [tool.poetry] sections)"""
        pyproject_file = self.files["pyproject"]
        content = pyproject_file.read_text(encoding="utf-8")

        lines = content.split("\n")
        current_section: Optional[str] = None
        updated_sections: set[str] = set()

        for i, line in enumerate(lines):
            section_match = re.match(r"^\[(.+)\]$", line.strip())
            if section_match:
                current_section = section_match.group(1)
                continue

            if current_section in ("project", "tool.poetry") and re.match(r'^\s*version\s*=\s*"', line):
                lines[i] = re.sub(
                    r'^(\s*version\s*=\s*")([^"]+)(")',
                    rf"\g<1>{new_version}\g<3>",
                    line,
                )
                updated_sections.add(current_section)

        if "project" not in updated_sections:
            raise ValueError("Could not find version in [project] section of pyproject.toml")

        content = "\n".join(lines)
        pyproject_file.write_text(content, encoding="utf-8")
        print(f"✓ Updated {pyproject_file.relative_to(self.project_root)}: project version")
        if "tool.poetry" in updated_sections:
            print(f"✓ Updated {pyproject_file.relative_to(self.project_root)}: poetry version")

    def update_changelog_file(self, new_version: str, release_date: Optional[date] = None) -> None:
        """Promote [Unreleased] notes into a dated release section for new_version."""
        changelog_file = self.files["changelog"]
        if not changelog_file.exists():
            raise FileNotFoundError(f"Could not find {changelog_file}")

        content = changelog_file.read_text(encoding="utf-8")
        # Exact section title only (avoid matching 2.1.0 inside 2.1.0rc10)
        if re.search(rf"^## \[{re.escape(new_version)}\](?:\s|$)", content, re.MULTILINE):
            raise ValueError(f"CHANGELOG.md already contains section for [{new_version}]")

        release_date = release_date or date.today()
        suffix = " (Pre-release)" if self.is_prerelease(new_version) else ""
        header = f"## [{new_version}] - {release_date.isoformat()}{suffix}"

        pattern = r"(## \[Unreleased\]\s*\n)(.*?)(\n## \[)"
        match = re.search(pattern, content, re.DOTALL)
        if not match:
            raise ValueError("Could not find ## [Unreleased] section in CHANGELOG.md")

        unreleased_body = match.group(2).strip()
        if unreleased_body:
            replacement = f"{match.group(1)}\n{header}\n\n{unreleased_body}\n\n{match.group(3)}"
        else:
            replacement = f"{match.group(1)}\n{header}\n\n{match.group(3)}"

        updated = content[: match.start()] + replacement + content[match.end() :]
        changelog_file.write_text(updated, encoding="utf-8")
        print(f"✓ Updated {changelog_file.relative_to(self.project_root)}: added [{new_version}] release section")

    def update_version(self, new_version: str, *, update_changelog: bool = True, release_date: Optional[date] = None) -> None:
        """Update version in all files and optionally promote CHANGELOG [Unreleased]."""
        self.parse_version(new_version)

        print(f"Updating version to {new_version}...")
        print()

        self.update_init_file(new_version)
        self.update_main_file(new_version)
        self.update_pyproject_file(new_version)
        if update_changelog:
            self.update_changelog_file(new_version, release_date=release_date)

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
    parser = argparse.ArgumentParser(
        prog="aiecs-version",
        description="AIECS Version Manager - Update version numbers across project files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aiecs-version --version 1.2.0          # Set specific version
  aiecs-version --version 2.0.0rc2       # Set pre-release version
  aiecs-version --bump patch             # Bump patch version (1.1.0 -> 1.1.1)
  aiecs-version --bump rc                # Bump rc (2.0.0rc1 -> 2.0.0rc2; 2.0.0 -> 2.0.0rc1)
  aiecs-version --bump minor             # Bump minor version (1.1.0 -> 1.2.0)
  aiecs-version --bump major             # Bump major version (1.1.0 -> 2.0.0)
  aiecs-version --show                   # Show current version
        """,
    )

    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument("--version", "-v", type=str, help="Set specific version (e.g., 1.2.0 or 2.0.0rc2)")
    version_group.add_argument(
        "--bump",
        "-b",
        choices=["major", "minor", "patch", "rc"],
        help="Bump version: major, minor, patch, or rc (pre-release)",
    )
    version_group.add_argument("--show", "-s", action="store_true", help="Show current version")

    parser.add_argument(
        "--no-changelog",
        action="store_true",
        help="Skip updating CHANGELOG.md",
    )
    parser.add_argument(
        "--release-date",
        type=str,
        help="Release date for CHANGELOG section (YYYY-MM-DD; default: today)",
    )

    args = parser.parse_args()

    try:
        manager = VersionManager()
        release_date = date.fromisoformat(args.release_date) if args.release_date else None

        if args.show:
            manager.show_version()
        elif args.version:
            manager.update_version(args.version, update_changelog=not args.no_changelog, release_date=release_date)
        elif args.bump:
            current_version = manager.get_current_version()
            new_version = manager.bump_version(current_version, args.bump)
            print(f"Bumping {args.bump} version: {current_version} -> {new_version}")
            print()
            manager.update_version(new_version, update_changelog=not args.no_changelog, release_date=release_date)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

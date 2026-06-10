"""Unit tests for aiecs.scripts.aid.version_manager."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from aiecs.scripts.aid.version_manager import VersionManager


@pytest.fixture
def version_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "aiecs").mkdir(parents=True)
    (root / "aiecs" / "__init__.py").write_text('__version__ = "2.0.0rc1"\n', encoding="utf-8")
    (root / "aiecs" / "main.py").write_text(
        'app = None\nversion="2.0.0rc1"\n'
        'def health():\n    return {"status": "healthy", "service": "aiecs", "version": "2.0.0rc1"}\n',
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        '[tool.poetry]\nname = "aiecs"\nversion = "2.0.0rc1"\n\n[project]\nname = "aiecs"\nversion = "2.0.0rc1"\n',
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Fixed\n\n- pending fix\n\n## [2.0.0rc1] - 2026-06-07 (Pre-release)\n\n### Added\n\n- first rc\n",
        encoding="utf-8",
    )
    return root


def test_parse_version_stable() -> None:
    manager = VersionManager(Path("."))
    parsed = manager.parse_version("1.2.3")
    assert parsed.render() == "1.2.3"
    assert not manager.is_prerelease("1.2.3")


def test_parse_version_prerelease_variants() -> None:
    manager = VersionManager(Path("."))
    assert manager.parse_version("2.0.0rc2").render() == "2.0.0rc2"
    assert manager.parse_version("2.0.0a1").render() == "2.0.0a1"
    assert manager.parse_version("2.0.0b3").render() == "2.0.0b3"
    assert manager.parse_version("2.0.0.dev4").render() == "2.0.0.dev4"
    assert manager.is_prerelease("2.0.0rc2")


def test_parse_version_rejects_invalid() -> None:
    manager = VersionManager(Path("."))
    with pytest.raises(ValueError, match="Invalid version format"):
        manager.parse_version("2.0-rc2")


def test_bump_rc_from_existing_prerelease() -> None:
    manager = VersionManager(Path("."))
    assert manager.bump_version("2.0.0rc1", "rc") == "2.0.0rc2"


def test_bump_rc_from_stable_starts_at_rc1() -> None:
    manager = VersionManager(Path("."))
    assert manager.bump_version("2.0.0", "rc") == "2.0.0rc1"


def test_bump_patch_clears_prerelease() -> None:
    manager = VersionManager(Path("."))
    assert manager.bump_version("2.0.0rc2", "patch") == "2.0.1"


def test_update_version_and_changelog(version_project: Path) -> None:
    manager = VersionManager(version_project)
    manager.update_version("2.0.0rc2", update_changelog=True, release_date=date(2026, 6, 10))

    assert (version_project / "aiecs" / "__init__.py").read_text(encoding="utf-8") == '__version__ = "2.0.0rc2"\n'
    changelog = (version_project / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [Unreleased]" in changelog
    assert "## [2.0.0rc2] - 2026-06-10 (Pre-release)" in changelog
    assert "- pending fix" in changelog
    assert changelog.index("## [Unreleased]") < changelog.index("## [2.0.0rc2]")
    assert changelog.index("## [2.0.0rc2]") < changelog.index("## [2.0.0rc1]")


def test_update_version_skip_changelog(version_project: Path) -> None:
    manager = VersionManager(version_project)
    before = (version_project / "CHANGELOG.md").read_text(encoding="utf-8")
    manager.update_version("2.0.0rc2", update_changelog=False)
    after = (version_project / "CHANGELOG.md").read_text(encoding="utf-8")
    assert before == after


def test_update_changelog_rejects_duplicate(version_project: Path) -> None:
    manager = VersionManager(version_project)
    with pytest.raises(ValueError, match="already contains section"):
        manager.update_changelog_file("2.0.0rc1")

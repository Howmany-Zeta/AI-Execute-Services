# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Load external plugin manifests from disk (§9.1, P3-06).

Supports ``aiecs-plugin.yaml`` / ``plugin.json`` paths and directory discovery.
Remote install is out of scope.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from aiecs.domain.agent.plugins.errors import raise_plugin_dependency_error
from aiecs.domain.agent.plugins.identifier import parse_plugin_identifier
from aiecs.domain.agent.plugins.schema.manifest import (
    PluginManifest,
    parse_manifest_json,
    parse_manifest_yaml,
)

if TYPE_CHECKING:
    from aiecs.domain.agent.models import AgentConfiguration
    from aiecs.domain.agent.plugins.registry import PluginRegistry

_MANIFEST_FILENAMES = (
    "aiecs-plugin.yaml",
    "aiecs-plugin.yml",
    "plugin.json",
)


def _manifest_file_in_directory(directory: Path) -> Path | None:
    for name in _MANIFEST_FILENAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def load_manifest_from_path(path: Path | str) -> PluginManifest:
    """
    Load a manifest from a file or directory.

    When ``path`` is a directory, the first matching ``aiecs-plugin.yaml`` /
    ``aiecs-plugin.yml`` / ``plugin.json`` file is used.
    """
    manifest_path = Path(path)
    if manifest_path.is_dir():
        resolved = _manifest_file_in_directory(manifest_path)
        if resolved is None:
            raise FileNotFoundError(f"no manifest file ({', '.join(_MANIFEST_FILENAMES)}) in {manifest_path}")
        manifest_path = resolved

    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest file not found: {manifest_path}")

    suffix = manifest_path.suffix.lower()
    text = manifest_path.read_text(encoding="utf-8")
    if suffix in (".yaml", ".yml"):
        return parse_manifest_yaml(text)
    if suffix == ".json":
        return parse_manifest_json(text)
    raise ValueError(f"unsupported manifest extension {suffix!r}; expected .yaml, .yml, or .json")


def discover_manifest_paths(directory: Path | str) -> list[Path]:
    """Return manifest file paths found directly under ``directory`` (non-recursive)."""
    root = Path(directory)
    if not root.is_dir():
        return []
    paths: list[Path] = []
    for name in _MANIFEST_FILENAMES:
        candidate = root / name
        if candidate.is_file():
            paths.append(candidate)
    return paths


def collect_manifests_from_config(config: AgentConfiguration) -> list[PluginManifest]:
    """Load manifests referenced by ``plugin_manifest_paths`` and ``extra_plugin_dirs``."""
    manifests: list[PluginManifest] = []
    seen_names: set[str] = set()

    for raw_path in config.plugin_manifest_paths:
        manifest = load_manifest_from_path(raw_path)
        if manifest.name in seen_names:
            continue
        seen_names.add(manifest.name)
        manifests.append(manifest)

    for raw_dir in config.extra_plugin_dirs:
        for manifest_path in discover_manifest_paths(raw_dir):
            manifest = load_manifest_from_path(manifest_path)
            if manifest.name in seen_names:
                continue
            seen_names.add(manifest.name)
            manifests.append(manifest)

    return manifests


def _dependency_short_name(dependency_name: str) -> str:
    return parse_plugin_identifier(dependency_name).name


def _available_dependency_names(
    manifests: list[PluginManifest],
    registry: PluginRegistry | None,
) -> set[str]:
    names = {manifest.name for manifest in manifests}
    if registry is not None:
        names.update(registry._entries.keys())
    return names


def sort_manifests_by_dependencies(
    manifests: list[PluginManifest],
    registry: PluginRegistry | None = None,
) -> list[PluginManifest]:
    """
    Topologically sort manifests by ``dependencies`` (placeholder for P3-06).

    Raises:
        PluginDependencyErrorException: When a dependency is not registered or present
            in the manifest batch.
    """
    if not manifests:
        return []

    by_name = {manifest.name: manifest for manifest in manifests}
    available = _available_dependency_names(manifests, registry)

    for manifest in manifests:
        for dep in manifest.dependencies:
            dep_name = _dependency_short_name(dep.name)
            if dep_name not in available:
                raise_plugin_dependency_error(
                    f"manifest {manifest.name!r} depends on unresolved plugin {dep.name!r}",
                    plugin_id=manifest.name,
                    details={"dependency": dep.name},
                )

    ordered: list[PluginManifest] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise_plugin_dependency_error(
                f"circular manifest dependency involving {name!r}",
                plugin_id=name,
            )
        manifest = by_name.get(name)
        if manifest is None:
            return
        visiting.add(name)
        for dep in manifest.dependencies:
            dep_name = _dependency_short_name(dep.name)
            if dep_name in by_name:
                visit(dep_name)
        visiting.remove(name)
        visited.add(name)
        ordered.append(manifest)

    for manifest in manifests:
        visit(manifest.name)

    return ordered

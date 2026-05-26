# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Load and compare plugin parity golden fixtures (§12.1).

Fixtures live under ``tests/fixtures/plugin_parity/`` (YAML). Use
``capture_fixture_spec`` from :mod:`capture` to refresh expectations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from aiecs.domain.agent.plugins.testing.capture import capture_fixture_spec

_DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parents[5] / "tests" / "fixtures" / "plugin_parity"


@dataclass(frozen=True)
class ParityCase:
    """One YAML parity fixture and its parsed spec."""

    path: Path
    name: str
    spec: dict[str, Any]

    @property
    def expect(self) -> dict[str, Any]:
        block = self.spec.get("expect")
        if not isinstance(block, dict):
            raise ValueError(f"{self.path}: missing or invalid 'expect' block")
        return block

    @property
    def parity_mode(self) -> str | None:
        mode = self.spec.get("parity_mode")
        return str(mode) if mode else None

    @property
    def task(self) -> dict[str, Any]:
        task = self.spec.get("task")
        return dict(task) if isinstance(task, dict) else {"description": "Parity test task"}

    @property
    def context(self) -> dict[str, Any]:
        ctx = self.spec.get("context")
        return dict(ctx) if isinstance(ctx, dict) else {}


@dataclass
class ParityCaptureResult:
    """Normalized outputs from a live HybridAgent run."""

    messages_normalized: list[dict[str, Any]] = field(default_factory=list)
    tool_schema_names: list[str] = field(default_factory=list)
    plugin_state_keys: list[str] = field(default_factory=list)
    execute_task_response: dict[str, Any] = field(default_factory=dict)
    streaming_phase_sequence: list[dict[str, Any]] = field(default_factory=list)
    sync_phase_sequence: list[dict[str, Any]] = field(default_factory=list)


def default_fixtures_dir() -> Path:
    """Repository ``tests/fixtures/plugin_parity`` directory."""
    return _DEFAULT_FIXTURES_DIR


def list_parity_fixtures(fixtures_dir: Path | None = None) -> list[Path]:
    """Sorted paths to ``hybrid_*.yaml`` parity fixtures."""
    root = fixtures_dir or default_fixtures_dir()
    return sorted(root.glob("hybrid_*.yaml"))


def load_parity_fixture(path: Path | str) -> ParityCase:
    """Load a YAML fixture into a :class:`ParityCase`."""
    fixture_path = Path(path)
    spec = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError(f"{fixture_path}: expected mapping at root")
    name = str(spec.get("name") or fixture_path.stem)
    return ParityCase(path=fixture_path, name=name, spec=spec)


async def capture_parity_case(case: ParityCase) -> ParityCaptureResult:
    """Run HybridAgent for a fixture spec and return normalized capture fields."""
    raw = await capture_fixture_spec(case.spec)
    return ParityCaptureResult(
        messages_normalized=list(raw.get("messages_normalized") or []),
        tool_schema_names=list(raw.get("tool_schema_names") or []),
        plugin_state_keys=list(raw.get("plugin_state_keys") or []),
        execute_task_response=dict(raw.get("execute_task_response") or {}),
        streaming_phase_sequence=list(raw.get("streaming_phase_sequence") or []),
        sync_phase_sequence=list(raw.get("sync_phase_sequence") or []),
    )


def compare_parity_expect(
    expect: dict[str, Any],
    got: ParityCaptureResult,
    *,
    check_messages: bool = True,
    check_tool_schemas: bool = True,
    check_plugin_state_keys: bool = True,
    check_execute_response: bool = True,
    check_streaming_phases: bool = True,
) -> list[str]:
    """
    Compare expected golden fields to captured output.

    Returns a list of human-readable mismatch descriptions (empty if equal).
    """
    mismatches: list[str] = []

    if check_messages and "messages_normalized" in expect:
        if got.messages_normalized != expect.get("messages_normalized"):
            mismatches.append("messages_normalized")
    if check_tool_schemas and "tool_schema_names" in expect:
        if got.tool_schema_names != expect.get("tool_schema_names"):
            mismatches.append("tool_schema_names")
    if check_plugin_state_keys and "plugin_state_keys" in expect:
        if got.plugin_state_keys != expect.get("plugin_state_keys", []):
            mismatches.append("plugin_state_keys")
    if check_execute_response and "execute_task_response" in expect:
        if got.execute_task_response != expect.get("execute_task_response"):
            mismatches.append("execute_task_response")

    if check_streaming_phases and "streaming_phase_sequence" in expect:
        if got.streaming_phase_sequence != expect.get("streaming_phase_sequence"):
            mismatches.append("streaming_phase_sequence")
        if got.sync_phase_sequence != expect.get("sync_phase_sequence"):
            mismatches.append("sync_phase_sequence")
        if got.streaming_phase_sequence != got.sync_phase_sequence:
            mismatches.append("streaming_vs_sync_phase_mismatch")

    return mismatches

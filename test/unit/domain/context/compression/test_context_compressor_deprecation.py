"""G6: ContextCompressor deprecation and internal import guard."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aiecs.domain.agent.integration.context_compressor import ContextCompressor

ALLOWED_CONTEXT_COMPRESSOR_SYMBOL_PATHS = {
    "aiecs/domain/agent/integration/context_compressor.py",
    "aiecs/domain/agent/integration/__init__.py",
    "aiecs/domain/agent/__init__.py",
    "aiecs/domain/__init__.py",
}

_DIRECT_INTEGRATION_IMPORT_MARKERS = (
    "integration.context_compressor",
    "from .context_compressor import",
)

_CONTEXT_COMPRESSOR_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+\S+\s+import\s+.*ContextCompressor|import\s+.*ContextCompressor)",
)


def _imports_context_compressor_symbol(text: str) -> bool:
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if _CONTEXT_COMPRESSOR_IMPORT_RE.match(line):
            return True
    return False


def test_context_compressor_init_emits_deprecation_warning() -> None:
    with pytest.warns(DeprecationWarning, match="2.2.0"):
        ContextCompressor(max_tokens=100)


def test_no_new_internal_context_compressor_imports() -> None:
    """Guard: aiecs internals must not import ContextCompressor directly or via barrels (G6)."""
    repo_root = Path(__file__).resolve().parents[4]
    aiecs_root = repo_root / "aiecs"
    violations: list[str] = []

    for path in sorted(aiecs_root.rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        if rel in ALLOWED_CONTEXT_COMPRESSOR_SYMBOL_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in _DIRECT_INTEGRATION_IMPORT_MARKERS):
            violations.append(f"{rel}: direct integration.context_compressor import")
        elif _imports_context_compressor_symbol(text):
            violations.append(f"{rel}: ContextCompressor symbol import (including barrel re-exports)")

    assert not violations, "Unexpected context_compressor imports:\n" + "\n".join(violations)

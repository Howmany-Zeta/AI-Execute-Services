# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Static ``document_path`` allowlist for ``dawp_start`` (§5.4 security).

LLM-supplied paths must resolve under configured roots or match a pre-registered
plugin ``document_path`` — arbitrary filesystem reads are rejected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_DAWP_SUFFIX = ".dawp.md"


def configure_document_path_policy(
    plugin_state: dict[str, Any],
    options: dict[str, Any],
) -> None:
    """Populate ``dawp.allowed_document_*`` keys from plugin options."""
    roots: list[str] = []
    files: set[str] = set()

    configured = options.get("document_path")
    if configured:
        resolved = Path(str(configured)).resolve()
        files.add(str(resolved))
        roots.append(str(resolved.parent))

    for raw in options.get("allowed_document_roots") or []:
        roots.append(str(Path(str(raw)).resolve()))

    plugin_state["dawp.allowed_document_roots"] = roots
    plugin_state["dawp.allowed_document_files"] = sorted(files)


def validate_static_document_path(
    document_path: str,
    plugin_state: dict[str, Any],
) -> tuple[Path | None, str | None]:
    """Return ``(resolved_path, None)`` or ``(None, rejection_reason)``."""
    try:
        requested = Path(document_path).resolve()
    except OSError as exc:
        return None, f"invalid document_path: {exc}"

    if not requested.is_file():
        return None, f"document_path does not exist: {document_path!r}"

    if requested.suffix != ".md" and not str(requested).endswith(_DAWP_SUFFIX):
        return None, "document_path must be a *.dawp.md file"

    allowed_files = set(plugin_state.get("dawp.allowed_document_files") or [])
    if str(requested) in allowed_files:
        return requested, None

    allowed_roots = plugin_state.get("dawp.allowed_document_roots") or []
    if not allowed_roots and not allowed_files:
        return None, ("document_path via dawp_start is disabled; use workflow_id or " "configure DawpPlugin.options.document_path / allowed_document_roots")

    for root_str in allowed_roots:
        root = Path(root_str)
        try:
            requested.relative_to(root)
            return requested, None
        except ValueError:
            continue

    return None, f"document_path {document_path!r} is not under allowed DAWP document roots"

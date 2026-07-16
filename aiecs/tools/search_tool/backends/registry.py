# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Grounding backend registry and built-in name canonicalization (M-D.5 §3.8).
"""

from __future__ import annotations

from ..constants import ValidationError
from .protocol import GroundingSearchBackend

BUILTIN_BACKEND_ALIASES: dict[str, str] = {
    "google": "google_cse",
    "cse": "google_cse",
    "google_cse": "google_cse",
    "gemini": "gemini",
    "grok": "grok",
    "auto": "auto",
}

BUILTIN_CANONICAL_NAMES = frozenset({"gemini", "grok", "google_cse", "auto"})


def normalize_backend_name(name: str) -> str:
    """Lowercase trim + map built-in aliases. Custom backend names pass through unchanged."""
    stripped = (name or "").strip()
    if not stripped:
        return ""
    key = stripped.lower()
    if key in BUILTIN_BACKEND_ALIASES:
        return BUILTIN_BACKEND_ALIASES[key]
    return stripped


def normalize_provider_chain(comma_separated: str) -> list[str]:
    """Normalize comma-separated provider chain; dedupe while preserving order."""
    if not comma_separated or not comma_separated.strip():
        return []
    seen: set[str] = set()
    result: list[str] = []
    for token in comma_separated.split(","):
        normalized = normalize_backend_name(token)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


class GroundingBackendRegistry:
    """Registry of built-in and consumer-injected grounding search backends."""

    def __init__(self) -> None:
        self._backends: dict[str, GroundingSearchBackend] = {}

    def register(self, backend: GroundingSearchBackend) -> None:
        """Register a backend under its canonical ``name``."""
        self._backends[backend.name] = backend

    def get(self, name: str) -> GroundingSearchBackend | None:
        """Look up a backend by built-in alias/canonical name or exact custom name."""
        stripped = (name or "").strip()
        if not stripped:
            return None
        canonical = normalize_backend_name(stripped)
        if canonical in self._backends:
            return self._backends[canonical]
        if stripped in self._backends:
            return self._backends[stripped]
        return None

    def list_names(self) -> list[str]:
        """Return registered backend names in insertion order."""
        return list(self._backends.keys())

    def has_configured_backend(self) -> bool:
        """Return True when at least one registered backend is configured."""
        return any(backend.is_configured() for backend in self._backends.values())

    def validate_forced_backend_name(self, name: str) -> str:
        """Validate forced ``grounding_provider``; raise for unknown built-in tokens."""
        stripped = (name or "").strip()
        if not stripped:
            raise ValidationError("grounding_provider cannot be empty")
        canonical = normalize_backend_name(stripped)
        if canonical in BUILTIN_CANONICAL_NAMES:
            return canonical
        if self.get(stripped) is not None:
            return stripped
        raise ValidationError(f"Unknown grounding_provider '{name}'. " "Canonical built-in names: gemini, grok, google_cse")

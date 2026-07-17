# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Grounding search backend protocol (M-D.5).

Defines SearchCallParams, BackendRawResult, and the GroundingSearchBackend
interface used by the router and built-in/custom backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SearchCallParams:
    """Unified call context — mirrors search_web() + post-intent merged filters (§3.6)."""

    query: str
    original_query: str
    num_results: int
    start_index: int = 1
    language: str = "en"
    country: str = "us"
    safe_search: str = "medium"
    date_restrict: str | None = None
    file_type: str | None = None
    exclude_terms: list[str] | None = None
    allowed_domains: list[str] | None = None
    blocked_domains: list[str] | None = None
    timeout_seconds: float = 30.0


@dataclass
class BackendRawResult:
    """Raw provider response before normalization into SearchTool envelope."""

    success: bool
    answer: str | None = None
    citations: list[dict[str, Any]] = field(default_factory=list)
    # Lightweight Gemini sentence↔chunk alignment (Layer A; independent of raw dump).
    grounding_chunks: list[dict[str, Any]] = field(default_factory=list)
    grounding_supports: list[dict[str, Any]] = field(default_factory=list)
    provider_native: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    backend: str = ""
    params_applied: list[str] = field(default_factory=list)
    params_ignored: list[str] = field(default_factory=list)


@runtime_checkable
class GroundingSearchBackend(Protocol):
    """Protocol for built-in and consumer-injected grounding search backends."""

    name: str

    def is_configured(self) -> bool:
        """Return True when this backend has credentials/config to attempt search."""
        ...

    def search(self, params: SearchCallParams) -> BackendRawResult:
        """Execute a synchronous search; must not raise for HTTP/API failures (§3.10)."""
        ...

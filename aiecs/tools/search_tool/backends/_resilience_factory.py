# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Shared resilience guard factory for grounding backends."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..resilience import BackendResilienceGuard

if TYPE_CHECKING:
    from ..core import SearchTool


def build_grounding_resilience_guard(backend_name: str, config: SearchTool.Config) -> BackendResilienceGuard:
    """
    Build an isolated guard for a grounding/custom backend.

    Uses ``SearchTool.Config`` grounding_* fields (``SEARCH_TOOL_GROUNDING_*``).
    Optional per-backend overrides when set, e.g. ``gemini_rate_limit_requests``
    (``SEARCH_TOOL_GEMINI_RATE_LIMIT_REQUESTS``) — §3.11.
    """
    prefix = (backend_name or "").strip().lower().replace("-", "_")
    return BackendResilienceGuard(
        backend_name,
        rate_limit_requests=_resolve_int(
            config,
            f"{prefix}_rate_limit_requests",
            "grounding_rate_limit_requests",
            60,
        ),
        rate_limit_window=_resolve_int(
            config,
            f"{prefix}_rate_limit_window",
            "grounding_rate_limit_window",
            3600,
        ),
        circuit_breaker_threshold=_resolve_int(
            config,
            f"{prefix}_circuit_breaker_threshold",
            "grounding_circuit_breaker_threshold",
            5,
        ),
        circuit_breaker_timeout=_resolve_int(
            config,
            f"{prefix}_circuit_breaker_timeout",
            "grounding_circuit_breaker_timeout",
            60,
        ),
    )


def _resolve_int(
    config: object,
    override_field: str,
    default_field: str,
    fallback: int,
) -> int:
    override = getattr(config, override_field, None)
    if override is not None:
        return int(override)
    value = getattr(config, default_field, None)
    if value is not None:
        return int(value)
    return fallback

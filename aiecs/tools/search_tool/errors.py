# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Search failure envelopes and three-tier error policy (M-D.5 §3.10)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .backends.protocol import BackendRawResult
from .backends.registry import GroundingBackendRegistry, normalize_backend_name, normalize_provider_chain
from .constants import (
    AuthenticationError,
    CircuitBreakerOpenError,
    QuotaExceededError,
    RateLimitError,
    SearchAPIError,
    SearchToolError,
    ValidationError,
)
from .error_handler import AgentFriendlyErrorHandler
from .router import RoutingMetadata

if TYPE_CHECKING:
    from .core import SearchTool

# Built-ins that do not count as "grounding" for CSE-only detection.
_CSE_ONLY_BACKEND_NAMES = frozenset({"google_cse", "auto"})


class AllBackendsExhaustedError(SearchToolError):
    """Synthetic exception when every backend in the provider chain failed or was skipped."""

    def __init__(self, message: str, *, technical_details: str | None = None) -> None:
        super().__init__(message)
        self.technical_details = technical_details or message


@dataclass(frozen=True)
class SearchRoutingContext:
    """Inputs for Tier C failure envelope construction."""

    routing_metadata: RoutingMetadata
    last_raw: BackendRawResult
    search_error_mode: str
    response_time_ms: float
    query: str
    enhanced_query: str
    intent_metadata: dict[str, Any] | None = None


def is_cse_only_deployment(
    config: SearchTool.Config,
    *,
    registry: GroundingBackendRegistry | None = None,
) -> bool:
    """
    True when effective routing is CSE-only (legacy raise semantics).

    Auto mode is CSE-only only when **no** built-in grounding credentials and
    **no** configured non-CSE registry backends (custom Exa, etc.) are present.
    Chain tokens outside ``gemini`` / ``grok`` / ``google_cse`` also disqualify
    CSE-only when ``registry`` is omitted (conservative; prefer Tier C).
    """
    provider = normalize_backend_name(getattr(config, "grounding_provider", "auto") or "auto")
    if provider == "google_cse":
        return True
    if provider != "auto":
        return False

    from .backends.credentials import CredentialResolver

    resolver = CredentialResolver(config)
    if resolver.resolve_gemini_auth_mode() is not None or resolver.resolve_grok_auth_mode() is not None:
        return False

    if registry is not None:
        for name in registry.list_names():
            canonical = normalize_backend_name(name) or name
            if canonical in _CSE_ONLY_BACKEND_NAMES:
                continue
            backend = registry.get(name)
            if backend is not None and backend.is_configured():
                return False
        return True

    # No registry: custom names in the provider chain ⇒ not CSE-only (§8).
    chain_raw = getattr(config, "grounding_provider_chain", None) or "gemini,grok,google_cse"
    for name in normalize_provider_chain(str(chain_raw)):
        if name not in ("gemini", "grok", "google_cse"):
            return False
    return True


def should_raise_for_search_error(
    error: Exception,
    config: SearchTool.Config,
    *,
    cse_only: bool,
) -> bool:
    """Return True when policy selects Tier A/B raise instead of Tier C return-dict."""
    mode = getattr(config, "search_error_mode", "auto") or "auto"
    if mode == "raise":
        return True
    if mode == "return_dict":
        return False
    if isinstance(error, (ValidationError, RateLimitError, CircuitBreakerOpenError)):
        return True
    if cse_only and isinstance(error, (SearchAPIError, AuthenticationError, QuotaExceededError)):
        return True
    return False


def resolve_routing_outcome(
    routing_metadata: RoutingMetadata,
    last_raw: BackendRawResult,
) -> str:
    if routing_metadata.forced_provider:
        return "forced_backend_failed"
    attempted = len(routing_metadata.provider_chain_attempted)
    skipped = len(routing_metadata.provider_chain_skipped)
    failed = len(routing_metadata.provider_chain_failed)
    if attempted == 0 or (skipped == attempted and failed == 0):
        return "no_backends_configured"
    return "all_backends_exhausted"


def _technical_details_from_routing(routing_metadata: RoutingMetadata) -> str:
    parts: list[str] = []
    for entry in routing_metadata.provider_chain_failed:
        parts.append(f"{entry['backend']}: {entry.get('message', '')}")
    if not parts and routing_metadata.provider_chain_skipped:
        parts.append("skipped: " + ", ".join(f"{s['backend']}({s['reason']})" for s in routing_metadata.provider_chain_skipped))
    return "; ".join(parts) if parts else "no backend returned results"


def build_search_failure_envelope(
    routing_context: SearchRoutingContext,
    *,
    error_handler: AgentFriendlyErrorHandler | None = None,
) -> dict[str, Any]:
    """Build Tier C failure dict compatible with successful search_web shape."""
    handler = error_handler or AgentFriendlyErrorHandler()
    metadata = routing_context.routing_metadata
    last_raw = routing_context.last_raw
    routing_outcome = resolve_routing_outcome(metadata, last_raw)

    technical_details = _technical_details_from_routing(metadata)
    if last_raw.error:
        technical_details = technical_details or last_raw.error

    synthetic = AllBackendsExhaustedError(
        "Web search failed: no backend returned results.",
        technical_details=technical_details,
    )
    error_info = handler.format_error_for_agent(synthetic, {})
    error_info["error_type"] = routing_outcome
    error_info["user_message"] = "Web search failed: no backend returned results."
    error_info["technical_details"] = technical_details

    search_metadata: dict[str, Any] = {
        "routing_outcome": routing_outcome,
        "backend_used": metadata.backend_used,
        "provider_chain_attempted": list(metadata.provider_chain_attempted),
        "provider_chain_skipped": list(metadata.provider_chain_skipped),
        "provider_chain_failed": list(metadata.provider_chain_failed),
        "search_error_mode": routing_context.search_error_mode,
        "original_query": routing_context.query,
        "enhanced_query": routing_context.enhanced_query,
    }
    if routing_context.intent_metadata:
        search_metadata.update(routing_context.intent_metadata)

    return {
        "success": False,
        "results": [],
        "low_signal": [],
        "must_scrape_urls": [],
        "next_steps": [
            "All configured search backends failed; verify SEARCH_TOOL_* credentials " "or set grounding_provider=google_cse",
        ],
        "_search_metadata": search_metadata,
        "_error": error_info,
        "_metadata": {
            "query": routing_context.query,
            "enhanced_query": routing_context.enhanced_query,
            "response_time_ms": routing_context.response_time_ms,
            "timestamp": time.time(),
        },
    }


def build_search_failure_envelope_from_exception(
    error: Exception,
    *,
    query: str,
    enhanced_query: str,
    search_error_mode: str,
    response_time_ms: float,
    error_handler: AgentFriendlyErrorHandler | None = None,
    intent_metadata: dict[str, Any] | None = None,
    circuit_breaker_timeout: int = 60,
) -> dict[str, Any]:
    """Build Tier C envelope from a single raised SearchToolError (CSE-only return_dict path)."""
    handler = error_handler or AgentFriendlyErrorHandler()
    error_info = handler.format_error_for_agent(
        error,
        {"circuit_breaker_timeout": circuit_breaker_timeout},
    )

    search_metadata: dict[str, Any] = {
        "routing_outcome": "single_backend_failed",
        "backend_used": "google_cse",
        "search_error_mode": search_error_mode,
        "original_query": query,
        "enhanced_query": enhanced_query,
    }
    if intent_metadata:
        search_metadata.update(intent_metadata)

    return {
        "success": False,
        "results": [],
        "low_signal": [],
        "must_scrape_urls": [],
        "next_steps": [
            "Search failed; verify SEARCH_TOOL_* credentials or retry with a simpler query",
        ],
        "_search_metadata": search_metadata,
        "_error": error_info,
        "_metadata": {
            "query": query,
            "enhanced_query": enhanced_query,
            "response_time_ms": response_time_ms,
            "timestamp": time.time(),
        },
    }


def should_return_tier_c_for_router_failure(
    config: SearchTool.Config,
    routing_metadata: RoutingMetadata,
) -> bool:
    """Tier C when auto mode walked/skipped multiple backends; always for return_dict."""
    mode = getattr(config, "search_error_mode", "auto") or "auto"
    if mode == "return_dict":
        return True
    if mode == "raise":
        return False
    chain_touch_count = len(routing_metadata.provider_chain_attempted) + len(routing_metadata.provider_chain_skipped)
    return chain_touch_count >= 2

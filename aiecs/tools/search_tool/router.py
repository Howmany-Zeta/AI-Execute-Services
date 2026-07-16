# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Grounding search router — chain walk, fail-open, backend pinning (M-D.5 §11)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from .backends.protocol import BackendRawResult, SearchCallParams
from .backends.registry import GroundingBackendRegistry, normalize_backend_name, normalize_provider_chain
from .constants import AuthenticationError

if TYPE_CHECKING:
    from .core import SearchTool


@dataclass
class RoutingMetadata:
    """Observability for a single router dispatch."""

    backend_used: str | None = None
    provider_chain: list[str] = field(default_factory=list)
    provider_chain_attempted: list[str] = field(default_factory=list)
    provider_chain_skipped: list[dict[str, str]] = field(default_factory=list)
    provider_chain_failed: list[dict[str, str]] = field(default_factory=list)
    forced_provider: str | None = None

    def chain_tail_after(self, backend: str) -> list[str]:
        """Backends after ``backend`` in the configured chain (§3.7 batch fail-open)."""
        if backend not in self.provider_chain:
            return []
        index = self.provider_chain.index(backend)
        return self.provider_chain[index + 1 :]


@dataclass
class BatchRoutingContext:
    """Pin + budget state for one ``search_batch`` call (M-D.5 §3.7)."""

    mode: str  # pin_on_first_success | per_query
    pinned_backend: str | None = None
    chain_tail: list[str] = field(default_factory=list)
    first_query_chain_attempted: list[str] = field(default_factory=list)
    per_query_backend_used: list[str] = field(default_factory=list)
    budget_seconds: float = 15.0
    deadline: float | None = None

    def start_deadline(self, *, now: float | None = None) -> None:
        """Set monotonic deadline from budget (call once at batch start)."""
        start = time.monotonic() if now is None else now
        self.deadline = start + self.budget_seconds

    def remaining_seconds(self, *, now: float | None = None) -> float:
        if self.deadline is None:
            return self.budget_seconds
        current = time.monotonic() if now is None else now
        return max(0.0, self.deadline - current)

    def per_query_timeout(
        self,
        remaining_queries: int,
        grounding_timeout_seconds: float,
        *,
        now: float | None = None,
    ) -> float:
        """``min(grounding_timeout, remaining_budget / remaining_queries)``."""
        if remaining_queries <= 0:
            return 0.0
        remaining = self.remaining_seconds(now=now)
        return min(grounding_timeout_seconds, remaining / remaining_queries)


class GroundingRouter:
    """Walk provider chains with fail-open semantics; never raises inside chain attempts."""

    DEFAULT_CHAIN = "gemini,grok,google_cse"

    def __init__(
        self,
        registry: GroundingBackendRegistry,
        config: SearchTool.Config,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._registry = registry
        self._config = config
        self._logger = logger or logging.getLogger(__name__)

    def search_with_chain(
        self,
        params: SearchCallParams,
        *,
        grounding_provider: str | None = None,
    ) -> tuple[BackendRawResult, RoutingMetadata]:
        """Walk chain until success or exhaustion; Tier B raise for forced misconfiguration."""
        provider = grounding_provider or getattr(self._config, "grounding_provider", "auto") or "auto"
        provider = normalize_backend_name(provider)

        if provider != "auto":
            return self._search_forced(params, provider)

        chain = self._configured_chain()
        metadata = RoutingMetadata(provider_chain=list(chain))
        return self._walk_chain(params, chain, metadata)

    def search_pinned(self, params: SearchCallParams, *, backend: str) -> BackendRawResult:
        """Call a single pinned backend (batch Q2+ default path)."""
        canonical = normalize_backend_name(backend)
        backend_impl = self._registry.get(canonical)
        if backend_impl is None:
            return BackendRawResult(
                success=False,
                error=f"Unknown backend '{backend}'",
                error_type="unknown_backend",
                backend=canonical,
            )
        if not backend_impl.is_configured():
            return BackendRawResult(
                success=False,
                error=f"Backend '{canonical}' is not configured",
                error_type="not_configured",
                backend=canonical,
            )
        if self._is_circuit_open(backend_impl):
            return BackendRawResult(
                success=False,
                error=f"Circuit open for backend '{canonical}'",
                error_type="circuit_open",
                backend=canonical,
            )
        return backend_impl.search(params)

    def search_chain_tail(
        self,
        params: SearchCallParams,
        *,
        backends: list[str],
    ) -> tuple[BackendRawResult, RoutingMetadata]:
        """Fail-open tail walk for a single batch sibling (pin unchanged)."""
        metadata = RoutingMetadata(provider_chain=list(backends))
        return self._walk_chain(params, backends, metadata)

    def search_for_batch(
        self,
        ctx: BatchRoutingContext,
        params: SearchCallParams,
        *,
        query_index: int,
        grounding_timeout_seconds: float,
        remaining_queries: int,
        grounding_provider: str | None = None,
    ) -> tuple[BackendRawResult, RoutingMetadata, bool]:
        """
        Dispatch one batch query under pin / per_query rules (§3.7).

        Returns ``(raw, routing_metadata, used_pinned_backend)``.
        """
        timeout = ctx.per_query_timeout(remaining_queries, grounding_timeout_seconds)
        params = replace(params, timeout_seconds=timeout)

        if ctx.mode == "per_query" or ctx.pinned_backend is None:
            raw, routing = self.search_with_chain(params, grounding_provider=grounding_provider)
            if query_index == 0 and not ctx.first_query_chain_attempted:
                ctx.first_query_chain_attempted = list(routing.provider_chain_attempted)
            if ctx.mode == "pin_on_first_success" and raw.success and routing.backend_used:
                ctx.pinned_backend = routing.backend_used
                ctx.chain_tail = routing.chain_tail_after(routing.backend_used)
            ctx.per_query_backend_used.append(routing.backend_used or raw.backend or "")
            return raw, routing, False

        pinned = ctx.pinned_backend
        assert pinned is not None
        routing = RoutingMetadata(
            provider_chain=[pinned, *ctx.chain_tail],
            provider_chain_attempted=[pinned],
        )
        raw = self.search_pinned(params, backend=pinned)
        if raw.success:
            routing.backend_used = pinned
            ctx.per_query_backend_used.append(pinned)
            return raw, routing, True

        routing.provider_chain_failed.append(self._failure_record(pinned, raw))
        if ctx.chain_tail:
            raw, tail_meta = self.search_chain_tail(params, backends=list(ctx.chain_tail))
            routing.provider_chain_attempted.extend(tail_meta.provider_chain_attempted)
            routing.provider_chain_skipped.extend(tail_meta.provider_chain_skipped)
            routing.provider_chain_failed.extend(tail_meta.provider_chain_failed)
            routing.backend_used = tail_meta.backend_used
            ctx.per_query_backend_used.append(tail_meta.backend_used or raw.backend or pinned)
            return raw, routing, True

        ctx.per_query_backend_used.append(raw.backend or pinned)
        return raw, routing, True

    def _search_forced(
        self,
        params: SearchCallParams,
        provider: str,
    ) -> tuple[BackendRawResult, RoutingMetadata]:
        canonical = self._registry.validate_forced_backend_name(provider)
        metadata = RoutingMetadata(forced_provider=canonical, provider_chain=[canonical])
        backend_impl = self._registry.get(canonical)
        if backend_impl is None:
            return (
                BackendRawResult(
                    success=False,
                    error=f"Unknown backend '{canonical}'",
                    error_type="unknown_backend",
                    backend=canonical,
                ),
                metadata,
            )

        if not backend_impl.is_configured():
            raise AuthenticationError(f"grounding_provider={canonical} is not configured; " f"set SEARCH_TOOL_* credentials for {canonical}")

        metadata.provider_chain_attempted.append(canonical)
        if self._is_circuit_open(backend_impl):
            metadata.provider_chain_skipped.append({"backend": canonical, "reason": "circuit_open"})
            return (
                BackendRawResult(
                    success=False,
                    error=f"Circuit open for backend '{canonical}'",
                    error_type="circuit_open",
                    backend=canonical,
                ),
                metadata,
            )

        raw = backend_impl.search(params)
        if raw.success:
            metadata.backend_used = canonical
            return raw, metadata

        metadata.provider_chain_failed.append(self._failure_record(canonical, raw))
        return raw, metadata

    def _walk_chain(
        self,
        params: SearchCallParams,
        chain: list[str],
        metadata: RoutingMetadata,
    ) -> tuple[BackendRawResult, RoutingMetadata]:
        last_result = BackendRawResult(
            success=False,
            error="No backends configured in provider chain",
            error_type="no_backends_configured",
            backend="",
        )

        for backend_name in chain:
            metadata.provider_chain_attempted.append(backend_name)
            backend_impl = self._registry.get(backend_name)
            if backend_impl is None:
                metadata.provider_chain_skipped.append({"backend": backend_name, "reason": "unknown"})
                continue

            if not backend_impl.is_configured():
                metadata.provider_chain_skipped.append({"backend": backend_name, "reason": "not_configured"})
                continue

            if self._is_circuit_open(backend_impl):
                metadata.provider_chain_skipped.append({"backend": backend_name, "reason": "circuit_open"})
                continue

            raw = backend_impl.search(params)
            if raw.success:
                metadata.backend_used = backend_name
                return raw, metadata

            metadata.provider_chain_failed.append(self._failure_record(backend_name, raw))
            last_result = raw

        return (
            BackendRawResult(
                success=False,
                error=last_result.error or "All configured search backends failed",
                error_type=last_result.error_type or "all_backends_exhausted",
                backend=last_result.backend,
            ),
            metadata,
        )

    def _configured_chain(self) -> list[str]:
        chain_value = getattr(self._config, "grounding_provider_chain", None) or self.DEFAULT_CHAIN
        return normalize_provider_chain(chain_value)

    @staticmethod
    def _is_circuit_open(backend_impl: Any) -> bool:
        resilience = getattr(backend_impl, "resilience", None)
        if resilience is None:
            return False
        return bool(resilience.is_circuit_open())

    @staticmethod
    def _failure_record(backend_name: str, raw: BackendRawResult) -> dict[str, str]:
        return {
            "backend": backend_name,
            "error_type": raw.error_type or "unknown",
            "message": raw.error or "",
        }

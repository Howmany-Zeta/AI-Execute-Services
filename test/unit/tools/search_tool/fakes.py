"""Fake grounding backends for M-D.5 router tests."""

from __future__ import annotations

from aiecs.tools.search_tool.backends.protocol import BackendRawResult, SearchCallParams
from aiecs.tools.search_tool.constants import CircuitBreakerOpenError, RateLimitError, SearchAPIError
from aiecs.tools.search_tool.resilience import BackendResilienceGuard


class FakeGroundingBackend:
    """Configurable fake backend implementing GroundingSearchBackend duck typing."""

    def __init__(
        self,
        name: str,
        *,
        configured: bool = True,
        succeed: bool = True,
        succeed_sequence: list[bool] | None = None,
        error: str | None = None,
        error_type: str | None = None,
        citations: list[dict] | None = None,
        grounding_chunks: list[dict] | None = None,
        grounding_supports: list[dict] | None = None,
        resilience: BackendResilienceGuard | None = None,
    ) -> None:
        self.name = name
        self._configured = configured
        self._succeed = succeed
        self._succeed_sequence = list(succeed_sequence) if succeed_sequence is not None else None
        self._error = error or "simulated failure"
        self._error_type = error_type or "simulated_failure"
        self._citations = citations or [{"url": "https://example.com", "title": "Example"}]
        self._grounding_chunks = list(grounding_chunks or [])
        self._grounding_supports = list(grounding_supports or [])
        self.resilience = resilience or BackendResilienceGuard(
            name,
            rate_limit_requests=60,
            rate_limit_window=3600,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=60,
        )
        self.search_calls: list[SearchCallParams] = []

    def is_configured(self) -> bool:
        return self._configured

    def _should_succeed(self) -> bool:
        if self._succeed_sequence is not None:
            if not self._succeed_sequence:
                return False
            return self._succeed_sequence.pop(0)
        return self._succeed

    def search(self, params: SearchCallParams) -> BackendRawResult:
        self.search_calls.append(params)
        if self._should_succeed():
            citations = list(self._citations)
            provider_native = None
            # CSE normalize path expects provider_native.items (§10)
            if self.name == "google_cse":
                provider_native = {
                    "items": [
                        {
                            "title": c.get("title", ""),
                            "link": c.get("url") or c.get("link") or "",
                            "snippet": c.get("snippet", ""),
                            "displayLink": c.get("domain") or c.get("displayLink") or "",
                        }
                        for c in citations
                    ]
                }
            return BackendRawResult(
                success=True,
                answer="fake answer",
                citations=citations,
                grounding_chunks=list(self._grounding_chunks),
                grounding_supports=list(self._grounding_supports),
                backend=self.name,
                params_applied=["query"],
                provider_native=provider_native,
            )

        try:
            def _do_search() -> BackendRawResult:
                raise SearchAPIError(self._error)

            self.resilience.execute(_do_search)
        except RateLimitError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="rate_limit_exceeded",
                backend=self.name,
            )
        except CircuitBreakerOpenError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="circuit_open",
                backend=self.name,
            )
        except SearchAPIError:
            pass

        return BackendRawResult(
            success=False,
            error=self._error,
            error_type=self._error_type,
            backend=self.name,
        )

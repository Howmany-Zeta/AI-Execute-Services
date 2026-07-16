# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Google Custom Search backend (M-D.5 §9.3)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

from ..constants import (
    AuthenticationError,
    CircuitBreakerOpenError,
    QuotaExceededError,
    RateLimitError,
    SearchAPIError,
)
from ..resilience import BackendResilienceGuard
from .protocol import BackendRawResult, SearchCallParams

if TYPE_CHECKING:
    from ..core import SearchTool

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.oauth2 import service_account

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    HttpError = Exception


class GoogleCseBackend:
    """Built-in Google Custom Search fallback backend."""

    name = "google_cse"

    def __init__(self, config: SearchTool.Config, *, logger: logging.Logger | None = None) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._service: Any | None = None
        self._credentials: Any | None = None
        self.resilience = BackendResilienceGuard(
            self.name,
            rate_limit_requests=config.rate_limit_requests,
            rate_limit_window=config.rate_limit_window,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_timeout=config.circuit_breaker_timeout,
        )

    @property
    def service(self) -> Any | None:
        """Expose lazy CSE client for test injection."""
        return self._service

    @service.setter
    def service(self, value: Any) -> None:
        self._service = value

    def is_configured(self) -> bool:
        if self._config.google_api_key and self._config.google_cse_id:
            return True
        if self._config.google_application_credentials:
            return os.path.exists(self._config.google_application_credentials)
        return False

    def _ensure_client(self) -> None:
        if self._service is not None:
            return

        if not GOOGLE_API_AVAILABLE:
            raise AuthenticationError("Google API client libraries not available. " "Install with: pip install google-api-python-client google-auth google-auth-httplib2")

        if self._config.google_api_key and self._config.google_cse_id:
            try:
                self._service = build(
                    "customsearch",
                    "v1",
                    developerKey=self._config.google_api_key,
                    cache_discovery=False,
                )
                self._logger.info("Initialized with API key")
                return
            except Exception as exc:
                self._logger.warning("Failed to initialize with API key: %s", exc)

        if self._config.google_application_credentials:
            creds_path = self._config.google_application_credentials
            if os.path.exists(creds_path):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=["https://www.googleapis.com/auth/cse"],
                    )
                    self._credentials = credentials
                    self._service = build(
                        "customsearch",
                        "v1",
                        credentials=credentials,
                        cache_discovery=False,
                    )
                    self._logger.info("Initialized with service account")
                    return
                except Exception as exc:
                    self._logger.warning("Failed to initialize with service account: %s", exc)

        raise AuthenticationError("No valid Google API credentials found. Set GOOGLE_API_KEY and GOOGLE_CSE_ID")

    def search(
        self,
        params: SearchCallParams,
        *,
        extra_api_params: dict[str, Any] | None = None,
    ) -> BackendRawResult:
        """Execute CSE search; returns structured result (no raise per protocol §3.10)."""
        if not self.is_configured():
            return BackendRawResult(
                success=False,
                error="Google CSE credentials not configured",
                error_type="auth",
                backend=self.name,
            )

        try:
            raw = self.resilience.execute(lambda: self._execute_cse_request(params, extra_api_params=extra_api_params))
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
        except QuotaExceededError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="quota_exceeded",
                backend=self.name,
            )
        except AuthenticationError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="auth",
                backend=self.name,
            )
        except SearchAPIError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="search_api_error",
                backend=self.name,
            )
        except Exception as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="search_api_error",
                backend=self.name,
            )

        api_params, params_applied = self._build_api_params(params, extra_api_params)
        citations = self._items_to_citations(raw.get("items", []))
        citations = self._apply_domain_filters(citations, params, params_applied)

        return BackendRawResult(
            success=True,
            citations=citations,
            provider_native=raw,
            backend=self.name,
            params_applied=params_applied,
            params_ignored=self._params_ignored(params),
        )

    def _execute_cse_request(
        self,
        params: SearchCallParams,
        *,
        extra_api_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_client()
        api_params, _ = self._build_api_params(params, extra_api_params)
        assert self._service is not None
        try:
            result = self._service.cse().list(**api_params).execute()
            return cast(dict[str, Any], result)
        except HttpError as exc:
            if exc.resp.status == 429:
                raise QuotaExceededError(f"API quota exceeded: {exc}") from exc
            if exc.resp.status == 403:
                raise AuthenticationError(f"Authentication failed: {exc}") from exc
            raise SearchAPIError(f"Search API error: {exc}") from exc
        except Exception as exc:
            raise SearchAPIError(f"Unexpected error: {exc}") from exc

    def _build_api_params(
        self,
        params: SearchCallParams,
        extra_api_params: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], list[str]]:
        query = params.query
        if params.exclude_terms:
            # One CSE unary minus per term (List[str] contract matches SearchWebSchema).
            query = f"{query} " + " ".join(f"-{term}" for term in params.exclude_terms)

        api_params: dict[str, Any] = {
            "q": query,
            "cx": self._config.google_cse_id,
            "num": min(params.num_results, 10),
            "start": params.start_index,
            "lr": f"lang_{params.language}",
            "cr": f"country{params.country.upper()}",
            "safe": params.safe_search,
        }
        params_applied = [
            "query",
            "num_results",
            "start_index",
            "language",
            "country",
            "safe_search",
        ]

        if params.date_restrict:
            api_params["dateRestrict"] = params.date_restrict
            params_applied.append("date_restrict")
        if params.file_type:
            api_params["fileType"] = params.file_type
            params_applied.append("file_type")
        if params.exclude_terms:
            params_applied.append("exclude_terms")

        if extra_api_params:
            api_params.update(extra_api_params)

        return api_params, params_applied

    @staticmethod
    def _params_ignored(params: SearchCallParams) -> list[str]:
        return []

    @staticmethod
    def _items_to_citations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        for item in items:
            citations.append(
                {
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "domain": item.get("displayLink", ""),
                }
            )
        return citations

    def _apply_domain_filters(
        self,
        citations: list[dict[str, Any]],
        params: SearchCallParams,
        params_applied: list[str],
    ) -> list[dict[str, Any]]:
        allowed = {domain.lower() for domain in (params.allowed_domains or [])}
        blocked = {domain.lower() for domain in (params.blocked_domains or [])}
        if not allowed and not blocked:
            return citations

        if params.allowed_domains:
            params_applied.append("allowed_domains")
        if params.blocked_domains:
            params_applied.append("blocked_domains")

        filtered: list[dict[str, Any]] = []
        for citation in citations:
            host = self._citation_host(citation)
            if blocked and host in blocked:
                continue
            if allowed and host not in allowed:
                continue
            filtered.append(citation)
        return filtered

    @staticmethod
    def _citation_host(citation: dict[str, Any]) -> str:
        domain = str(citation.get("domain", "")).lower()
        if domain:
            return domain.lstrip("www.")
        url = str(citation.get("url", ""))
        if not url:
            return ""
        host = urlparse(url).netloc.lower()
        return host.lstrip("www.")

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Grok grounding backend — sync OpenAI client (M-D.5 §9.2 / §3.4 / §3.12).

Paths
-----
* **xAI direct** — ``OpenAI(base_url=https://api.x.ai/v1)`` + API key (primary).
* **Vertex MaaS** — ``OpenAI(base_url=.../endpoints/openapi)`` + sync GCP token
  refresh (copied from ``VertexMaaSClient`` pattern; that class is **not** imported).

Phase 3 spike (MaaS ``web_search``)
-----------------------------------
* Target model form: ``xai/{grounding_model_grok}`` (default ``xai/grok-4.5``).
* Spike status: **unconfirmed in this environment** — keep
  ``SEARCH_TOOL_GROK_MAAS_WEB_SEARCH_ENABLED=false`` (default) until ops validate
  ``web_search`` on the MaaS openapi endpoint for the target model.
* When spike passes: set ``grok_maas_web_search_enabled=true``. Auto MaaS then
  **always** TTL-probes ``web_search`` (enable alone is not enough).
* Forced ``grok_grounding_auth=vertex_maas`` may skip the probe unless
  ``grok_maas_capability_probe=true`` (ops/debug).

Gating (§3.12)
--------------
* Auto + MaaS-only + enable false → ``is_configured()`` false (no MaaS HTTP).
* Auto + enable true → capability probe required; unsupported → skip.
* Forced ``vertex_maas`` attempts regardless of enable; probe optional.
* Probe unsupported (cached) → auto skips; forced returns
  ``error_type=maas_web_search_unsupported``.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable
from urllib.parse import urlparse

from ..constants import CircuitBreakerOpenError, RateLimitError, ValidationError
from ..resilience import BackendResilienceGuard
from ._resilience_factory import build_grounding_resilience_guard
from .credentials import (
    CredentialResolver,
    GrokAuthMode,
    SyncMaasTokenProvider,
    build_maas_openapi_base_url,
)
from .protocol import BackendRawResult, SearchCallParams

if TYPE_CHECKING:
    from ..core import SearchTool

try:
    from openai import OpenAI
    from openai import APIStatusError, AuthenticationError as OpenAIAuthenticationError

    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    OPENAI_AVAILABLE = False
    OpenAI = None  # type: ignore[assignment,misc]
    APIStatusError = Exception  # type: ignore[assignment,misc]
    OpenAIAuthenticationError = Exception  # type: ignore[assignment,misc]

XAI_BASE_URL = "https://api.x.ai/v1"
_MAX_DOMAIN_FILTERS = 5
_CSE_ONLY_PARAMS = (
    "date_restrict",
    "file_type",
    "safe_search",
    "exclude_terms",
    "start_index",
)


def _to_maas_api_model(model_name: str) -> str:
    """Return ``publisher/model`` form required by Vertex MaaS openapi."""
    if "/" in model_name:
        return model_name
    return f"xai/{model_name}"


class GrokGroundingBackend:
    """Built-in Grok web_search via sync ``openai.OpenAI`` (xAI + gated MaaS)."""

    name = "grok"

    def __init__(
        self,
        config: SearchTool.Config,
        *,
        logger: logging.Logger | None = None,
        credential_resolver: CredentialResolver | None = None,
        resilience: BackendResilienceGuard | None = None,
        client_factory: Callable[..., Any] | None = None,
        maas_token_provider: SyncMaasTokenProvider | None = None,
    ) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._credential_resolver = credential_resolver or CredentialResolver(config)
        self.resilience = resilience or build_grounding_resilience_guard(self.name, config)
        self._client_factory = client_factory or (OpenAI if OPENAI_AVAILABLE else None)
        self._client: Any | None = None
        self._client_auth_mode: GrokAuthMode | None = None
        self._maas_token_provider = maas_token_provider
        self._maas_web_search_capable: bool | None = None
        self._maas_probe_monotonic: float | None = None

    def is_configured(self) -> bool:
        auth_mode = self._credential_resolver.resolve_grok_auth_mode()
        if auth_mode == "xai":
            return True
        if auth_mode != "vertex_maas":
            return False

        forced = self._is_forced_vertex_maas()
        if not self._should_verify_maas_capability():
            # Forced + probe disabled: ops/debug path trusts the spike without HTTP.
            return True

        capable = self._cached_maas_capability()
        if capable is None:
            try:
                capable = self.probe_maas_web_search_support()
            except Exception:
                # Transient probe failure — stay eligible; search may retry.
                return True
        if capable:
            return True
        # Cached unsupported: auto skips; forced still "configured" (fast-fail on search).
        return forced

    @property
    def auth_mode(self) -> GrokAuthMode | None:
        return self._credential_resolver.resolve_grok_auth_mode()

    def probe_maas_web_search_support(
        self,
        client: Any | None = None,
        model: str | None = None,
    ) -> bool:
        """Minimal ``responses.create`` + ``web_search``; TTL-caches unsupported.

        Transient errors are re-raised (not cached as negative).
        """
        cached = self._cached_maas_capability()
        if cached is not None:
            return cached

        probe_client = client or self._ensure_client("vertex_maas")
        api_model = _to_maas_api_model(model or getattr(self._config, "grounding_model_grok", None) or "grok-4.5")
        try:
            probe_client.responses.create(
                model=api_model,
                input=[{"role": "user", "content": "ping"}],
                tools=[{"type": "web_search"}],
                max_output_tokens=1,
            )
        except Exception as exc:
            if self._is_unsupported_tool_error(exc):
                self._set_maas_capability(False)
                self._logger.warning(
                    "MaaS web_search unsupported for model %s; caching negative result",
                    api_model,
                )
                return False
            raise

        self._set_maas_capability(True)
        if not bool(getattr(self._config, "grok_maas_web_search_enabled", False)):
            self._logger.info(
                "MaaS web_search probe passed for %s; enable " "SEARCH_TOOL_GROK_MAAS_WEB_SEARCH_ENABLED to use in auto mode",
                api_model,
            )
        return True

    def search(self, params: SearchCallParams) -> BackendRawResult:
        auth_mode = self._credential_resolver.resolve_grok_auth_mode()
        if auth_mode is None:
            return BackendRawResult(
                success=False,
                error="Grok grounding is not configured",
                error_type="not_configured",
                backend=self.name,
            )

        self._validate_domain_filters(params)
        params_applied, params_ignored = self._classify_params(params)

        if auth_mode == "vertex_maas":
            unsupported = self._maas_unsupported_fast_fail(
                params_applied=params_applied,
                params_ignored=params_ignored,
            )
            if unsupported is not None:
                return unsupported

        try:
            return self.resilience.execute(lambda: self._execute_search(params, auth_mode, params_applied, params_ignored))
        except ValidationError:
            raise
        except RateLimitError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="rate_limit_exceeded",
                backend=self.name,
                params_applied=params_applied,
                params_ignored=params_ignored,
            )
        except CircuitBreakerOpenError as exc:
            return BackendRawResult(
                success=False,
                error=str(exc),
                error_type="circuit_open",
                backend=self.name,
                params_applied=params_applied,
                params_ignored=params_ignored,
            )
        except Exception as exc:
            return self._failure_from_exception(
                exc,
                auth_mode=auth_mode,
                params_applied=params_applied,
                params_ignored=params_ignored,
            )

    def _execute_search(
        self,
        params: SearchCallParams,
        auth_mode: GrokAuthMode,
        params_applied: list[str],
        params_ignored: list[str],
    ) -> BackendRawResult:
        try:
            client = self._ensure_client(auth_mode)
            model = getattr(self._config, "grounding_model_grok", None) or "grok-4.5"
            api_model = _to_maas_api_model(model) if auth_mode == "vertex_maas" else model
            tools = [self._build_web_search_tool(params)]
            response = client.responses.create(
                model=api_model,
                input=[{"role": "user", "content": params.query}],
                tools=tools,
            )
        except ValidationError:
            raise
        except Exception as exc:
            if auth_mode == "vertex_maas" and self._is_unsupported_tool_error(exc):
                self._set_maas_capability(False)
                return BackendRawResult(
                    success=False,
                    error=str(exc),
                    error_type="maas_web_search_unsupported",
                    backend=self.name,
                    params_applied=params_applied,
                    params_ignored=params_ignored,
                    provider_native=self._provider_native(auth_mode),
                )
            return self._failure_from_exception(
                exc,
                auth_mode=auth_mode,
                params_applied=params_applied,
                params_ignored=params_ignored,
            )

        return self._parse_response(
            response,
            auth_mode=auth_mode,
            params_applied=params_applied,
            params_ignored=params_ignored,
            params=params,
            web_search_tool=tools[0],
        )

    def _maas_unsupported_fast_fail(
        self,
        *,
        params_applied: list[str],
        params_ignored: list[str],
    ) -> BackendRawResult | None:
        if not self._should_verify_maas_capability():
            return None
        capable = self._cached_maas_capability()
        if capable is None:
            try:
                capable = self.probe_maas_web_search_support()
            except Exception:
                return None
        if capable is False:
            return BackendRawResult(
                success=False,
                error="Vertex MaaS web_search is not supported for the configured model",
                error_type="maas_web_search_unsupported",
                backend=self.name,
                params_applied=params_applied,
                params_ignored=params_ignored,
                provider_native=self._provider_native("vertex_maas"),
            )
        return None

    def _is_forced_vertex_maas(self) -> bool:
        return (self._optional_config_str("grok_grounding_auth") or "auto").lower() == "vertex_maas"

    def _should_verify_maas_capability(self) -> bool:
        """Auto MaaS always probes; forced probes only when the probe flag is on."""
        if self._is_forced_vertex_maas():
            return bool(getattr(self._config, "grok_maas_capability_probe", False))
        # Auto reached vertex_maas only when grok_maas_web_search_enabled=true.
        return True

    def _ensure_client(self, auth_mode: GrokAuthMode) -> Any:
        if not OPENAI_AVAILABLE or self._client_factory is None:
            raise RuntimeError("openai package is not available. Install with: pip install openai")

        timeout = float(getattr(self._config, "grounding_timeout_seconds", 30.0) or 30.0)

        if auth_mode == "xai":
            if self._client is not None and self._client_auth_mode == "xai":
                return self._client
            api_key = self._resolve_xai_api_key()
            if not api_key:
                raise RuntimeError("SEARCH_TOOL_GROK_API_KEY / SEARCH_TOOL_XAI_API_KEY is not set")
            self._client = self._client_factory(
                api_key=api_key,
                base_url=XAI_BASE_URL,
                timeout=timeout,
            )
            self._client_auth_mode = "xai"
            self._logger.info("Grok grounding client initialized (xai sync_openai)")
            return self._client

        # vertex_maas — refresh token when near expiry
        provider = self._get_maas_token_provider()
        if self._client is not None and self._client_auth_mode == "vertex_maas" and not provider.needs_refresh():
            return self._client

        project, location = self._resolve_maas_project_location()
        token = provider.get_access_token()
        base_url = build_maas_openapi_base_url(project, location)
        self._client = self._client_factory(
            api_key=token,
            base_url=base_url,
            timeout=timeout,
        )
        self._client_auth_mode = "vertex_maas"
        self._logger.info("Grok grounding client initialized (vertex_maas sync_openai)")
        return self._client

    def _get_maas_token_provider(self) -> SyncMaasTokenProvider:
        if self._maas_token_provider is None:
            self._maas_token_provider = SyncMaasTokenProvider(
                credentials_path=self._optional_config_str("google_application_credentials_vertex_maas"),
                fallback_credentials_path=self._optional_config_str("google_application_credentials"),
            )
        return self._maas_token_provider

    def _resolve_maas_project_location(self) -> tuple[str, str]:
        project = self._optional_config_str("vertex_project_id_maas")
        location = self._optional_config_str("vertex_location_maas") or "global"
        if project:
            return project, location

        if bool(getattr(self._config, "allow_llm_credential_fallback", False)):
            from aiecs.config.config import get_settings

            settings = get_settings()
            project_val = getattr(settings, "maas_vertex_project_id", None)
            if callable(project_val):
                project_val = project_val()
            project = str(project_val).strip() if project_val else ""
            if not project:
                project = CredentialResolver._settings_str(settings, "vertex_project_id_maas") or CredentialResolver._settings_str(settings, "vertex_project_id") or ""
            loc_val = getattr(settings, "maas_vertex_location", None)
            if callable(loc_val):
                loc_val = loc_val()
            if loc_val:
                location = str(loc_val).strip() or location
            if project:
                return project, location

        raise RuntimeError("SEARCH_TOOL_VERTEX_PROJECT_ID_MAAS (or LLM fallback) is required for vertex_maas")

    def _build_web_search_tool(self, params: SearchCallParams) -> dict[str, Any]:
        tool: dict[str, Any] = {"type": "web_search"}
        filters: dict[str, list[str]] = {}
        if params.allowed_domains:
            filters["allowed_domains"] = list(params.allowed_domains)
        if params.blocked_domains:
            filters["excluded_domains"] = list(params.blocked_domains)
        if filters:
            tool["filters"] = filters
        return tool

    def _parse_response(
        self,
        response: Any,
        *,
        auth_mode: GrokAuthMode,
        params_applied: list[str],
        params_ignored: list[str],
        params: SearchCallParams | None = None,
        web_search_tool: dict[str, Any] | None = None,
    ) -> BackendRawResult:
        answer = self._extract_output_text(response)
        citations = self._citations_from_response(response)
        provider_native = self._provider_native(
            auth_mode,
            params=params,
            web_search_tool=web_search_tool,
            response=response,
        )

        if not citations:
            return BackendRawResult(
                success=False,
                answer=answer or None,
                error="Grok web_search returned no citations",
                error_type="empty_citations",
                backend=self.name,
                params_applied=params_applied,
                params_ignored=params_ignored,
                provider_native=provider_native,
            )

        return BackendRawResult(
            success=True,
            answer=answer or None,
            citations=citations,
            backend=self.name,
            params_applied=params_applied,
            params_ignored=params_ignored,
            provider_native=provider_native,
        )

    def _provider_native(
        self,
        auth_mode: GrokAuthMode,
        *,
        params: SearchCallParams | None = None,
        web_search_tool: dict[str, Any] | None = None,
        response: Any | None = None,
    ) -> dict[str, Any]:
        native: dict[str, Any] = {
            "grok_auth_mode": auth_mode,
            "grok_client_mode": "sync_openai",
            "grok_maas_web_search_capable": self._maas_web_search_capable,
        }
        if params is not None:
            if params.allowed_domains:
                native["allowed_domains_applied"] = list(params.allowed_domains)
            if params.blocked_domains:
                native["excluded_domains_applied"] = list(params.blocked_domains)
        if web_search_tool is not None:
            native["web_search_tool"] = web_search_tool
        if bool(getattr(self._config, "grok_include_raw_grounding", False)) and response is not None:
            native["responses_create_response"] = self._serialize_sdk_value(response)
        return native

    @staticmethod
    def _serialize_sdk_value(value: Any) -> Any:
        """Best-effort JSON-safe dump of OpenAI SDK pydantic / namespace objects."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        type_name = type(value).__name__
        if type_name in {"MagicMock", "Mock", "AsyncMock", "NonCallableMagicMock"}:
            return {"_unserializable": type_name}
        if hasattr(value, "model_dump"):
            try:
                return value.model_dump(mode="json", exclude_none=True)
            except Exception:
                try:
                    return value.model_dump(exclude_none=True)
                except Exception:
                    pass
        if isinstance(value, dict):
            return {str(k): GrokGroundingBackend._serialize_sdk_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [GrokGroundingBackend._serialize_sdk_value(v) for v in value]
        raw_dict = getattr(value, "__dict__", None)
        if isinstance(raw_dict, dict) and raw_dict:
            return {str(k): GrokGroundingBackend._serialize_sdk_value(v) for k, v in raw_dict.items() if not str(k).startswith("_")}
        return {"_repr": repr(value)}

    def _cached_maas_capability(self) -> bool | None:
        if self._maas_web_search_capable is None or self._maas_probe_monotonic is None:
            return None
        ttl = int(getattr(self._config, "maas_capability_probe_ttl_seconds", 3600) or 3600)
        if time.monotonic() - self._maas_probe_monotonic >= ttl:
            self._maas_web_search_capable = None
            self._maas_probe_monotonic = None
            return None
        return self._maas_web_search_capable

    def _set_maas_capability(self, capable: bool) -> None:
        self._maas_web_search_capable = capable
        self._maas_probe_monotonic = time.monotonic()

    @staticmethod
    def _is_unsupported_tool_error(exc: Exception) -> bool:
        message = str(exc).lower()
        markers = (
            "web_search",
            "unsupported tool",
            "tool not supported",
            "tools are not supported",
            "invalid tool",
            "unknown tool",
        )
        if any(m in message for m in markers):
            # Prefer tool/capability wording over generic failures.
            if "tool" in message or "web_search" in message:
                return True
        code = getattr(exc, "status_code", None)
        if code == 400 and ("tool" in message or "web_search" in message):
            return True
        return False

    @staticmethod
    def _extract_output_text(response: Any) -> str:
        text = getattr(response, "output_text", None)
        if isinstance(text, str) and text.strip():
            return text
        parts: list[str] = []
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", None) or []:
                if getattr(content, "type", None) == "output_text":
                    chunk = getattr(content, "text", None)
                    if chunk:
                        parts.append(str(chunk))
        return "".join(parts)

    @staticmethod
    def _citations_from_response(response: Any) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        seen: set[str] = set()

        raw_citations = getattr(response, "citations", None) or []
        for entry in raw_citations:
            if isinstance(entry, str):
                url = entry
                title = ""
            else:
                url = getattr(entry, "url", None) or (entry.get("url") if isinstance(entry, dict) else None) or ""
                title = getattr(entry, "title", None) or (entry.get("title") if isinstance(entry, dict) else "") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            citations.append(
                {
                    "url": url,
                    "title": title,
                    "domain": urlparse(url).netloc,
                    "snippet": "",
                }
            )

        if citations:
            return citations

        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", None) or []:
                for annotation in getattr(content, "annotations", None) or []:
                    url = getattr(annotation, "url", None) or ""
                    if not url or url in seen:
                        continue
                    seen.add(url)
                    citations.append(
                        {
                            "url": url,
                            "title": getattr(annotation, "title", None) or "",
                            "domain": urlparse(url).netloc,
                            "snippet": "",
                        }
                    )
        return citations

    def _failure_from_exception(
        self,
        exc: Exception,
        *,
        auth_mode: GrokAuthMode | None,
        params_applied: list[str],
        params_ignored: list[str],
    ) -> BackendRawResult:
        error_type = "search_api_error"
        message = str(exc)

        # Resilience guard exceptions (should be caught in search(); keep typed).
        if isinstance(exc, RateLimitError):
            error_type = "rate_limit_exceeded"
        elif isinstance(exc, CircuitBreakerOpenError):
            error_type = "circuit_open"
        elif OPENAI_AVAILABLE and isinstance(exc, OpenAIAuthenticationError):
            error_type = "auth"
        elif OPENAI_AVAILABLE and isinstance(exc, APIStatusError):
            code = getattr(exc, "status_code", None)
            message = getattr(exc, "message", None) or message
            if code in (401, 403):
                error_type = "auth"
            elif code == 429:
                error_type = "quota_exceeded"
            elif code == 503:
                error_type = "http_503"
            elif code in (408, 504):
                error_type = "timeout"
            else:
                error_type = f"http_{code}" if code else "search_api_error"
        elif isinstance(exc, TimeoutError) or exc.__class__.__name__ in (
            "TimeoutException",
            "ReadTimeout",
            "ConnectTimeout",
            "APITimeoutError",
        ):
            error_type = "timeout"

        self._logger.warning("Grok grounding failed (%s): %s", error_type, message)
        return BackendRawResult(
            success=False,
            error=message,
            error_type=error_type,
            backend=self.name,
            params_applied=params_applied,
            params_ignored=params_ignored,
            provider_native=self._provider_native(auth_mode) if auth_mode else None,
        )

    def _resolve_xai_api_key(self) -> str | None:
        for field in ("grok_api_key", "xai_api_key"):
            value = getattr(self._config, field, None)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _optional_config_str(self, field_name: str) -> str | None:
        value = getattr(self._config, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _validate_domain_filters(params: SearchCallParams) -> None:
        allowed = list(params.allowed_domains or [])
        blocked = list(params.blocked_domains or [])
        if allowed and blocked:
            raise ValidationError("Grok web_search: allowed_domains and blocked_domains are mutually exclusive")
        if len(allowed) > _MAX_DOMAIN_FILTERS:
            raise ValidationError(f"Grok web_search: allowed_domains supports at most {_MAX_DOMAIN_FILTERS} entries")
        if len(blocked) > _MAX_DOMAIN_FILTERS:
            raise ValidationError(f"Grok web_search: blocked_domains supports at most {_MAX_DOMAIN_FILTERS} entries")

    @staticmethod
    def _classify_params(params: SearchCallParams) -> tuple[list[str], list[str]]:
        applied = ["query"]
        ignored: list[str] = []
        for name in _CSE_ONLY_PARAMS:
            value = getattr(params, name, None)
            if name == "start_index":
                if value not in (None, 1):
                    ignored.append(name)
                continue
            if name == "safe_search":
                if value not in (None, "medium"):
                    ignored.append(name)
                continue
            if value:
                ignored.append(name)
        if params.allowed_domains:
            applied.append("allowed_domains")
        if params.blocked_domains:
            applied.append("blocked_domains")
        return applied, ignored

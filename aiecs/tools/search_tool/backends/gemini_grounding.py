# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Gemini grounding backend — Google GenAI + Vertex dual auth (M-D.5 §9.1 / §7.1)."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from ..constants import CircuitBreakerOpenError, RateLimitError
from ..resilience import BackendResilienceGuard
from ._resilience_factory import build_grounding_resilience_guard
from .credentials import CredentialResolver, GeminiAuthMode
from .protocol import BackendRawResult, SearchCallParams

if TYPE_CHECKING:
    from ..core import SearchTool

try:
    from google import genai
    from google.genai import types as genai_types
    from google.genai import errors as genai_errors

    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    GENAI_AVAILABLE = False
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]
    genai_errors = None  # type: ignore[assignment]

_CSE_ONLY_PARAMS = (
    "date_restrict",
    "file_type",
    "safe_search",
    "exclude_terms",
    "start_index",
)


class GeminiGroundingBackend:
    """Built-in Gemini Google Search grounding (sync ``genai.Client``)."""

    name = "gemini"

    def __init__(
        self,
        config: SearchTool.Config,
        *,
        logger: logging.Logger | None = None,
        credential_resolver: CredentialResolver | None = None,
        resilience: BackendResilienceGuard | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self._config = config
        self._logger = logger or logging.getLogger(__name__)
        self._credential_resolver = credential_resolver or CredentialResolver(config)
        self.resilience = resilience or build_grounding_resilience_guard(self.name, config)
        self._client_factory = client_factory or (genai.Client if GENAI_AVAILABLE else None)
        self._client: Any | None = None
        self._client_auth_mode: GeminiAuthMode | None = None

    def is_configured(self) -> bool:
        return self._credential_resolver.resolve_gemini_auth_mode() is not None

    @property
    def auth_mode(self) -> GeminiAuthMode | None:
        """Resolved auth mode for the next / last client (``googleai`` | ``vertex``)."""
        return self._credential_resolver.resolve_gemini_auth_mode()

    def search(self, params: SearchCallParams) -> BackendRawResult:
        auth_mode = self._credential_resolver.resolve_gemini_auth_mode()
        if auth_mode is None:
            return BackendRawResult(
                success=False,
                error="Gemini grounding is not configured",
                error_type="not_configured",
                backend=self.name,
            )

        params_applied, params_ignored = self._classify_params(params)

        try:
            raw = self.resilience.execute(lambda: self._execute_grounding(params, auth_mode))
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

        return raw

    def _execute_grounding(self, params: SearchCallParams, auth_mode: GeminiAuthMode) -> BackendRawResult:
        params_applied, params_ignored = self._classify_params(params)
        try:
            client = self._ensure_client(auth_mode)
            model = getattr(self._config, "grounding_model_gemini", None) or "gemini-2.5-flash"
            temperature = float(getattr(self._config, "gemini_grounding_temperature", 1.0) or 1.0)
            config = self._build_generate_config(params, auth_mode=auth_mode, temperature=temperature)
            response = client.models.generate_content(
                model=model,
                contents=params.query,
                config=config,
            )
        except Exception as exc:
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
            blocked_domains=params.blocked_domains,
        )

    def _ensure_client(self, auth_mode: GeminiAuthMode) -> Any:
        if self._client is not None and self._client_auth_mode == auth_mode:
            return self._client

        if not GENAI_AVAILABLE or self._client_factory is None:
            raise RuntimeError("google-genai is not available. Install with: pip install google-genai")

        if auth_mode == "googleai":
            api_key = self._resolve_googleai_api_key()
            if not api_key:
                raise RuntimeError("SEARCH_TOOL_GEMINI_API_KEY is not set")
            self._client = self._client_factory(api_key=api_key)
            self._client_auth_mode = "googleai"
            self._logger.info("Gemini grounding client initialized (googleai)")
            return self._client

        project = self._optional_config("vertex_project_id")
        if not project:
            raise RuntimeError("SEARCH_TOOL_VERTEX_PROJECT_ID is not set")
        location = self._optional_config("vertex_location") or "global"
        credentials = self._load_vertex_credentials()

        http_kwargs: dict[str, Any] = {"api_version": "v1"}
        # Honor enterprise flag for Vertex grounding endpoint selection.
        if self._use_enterprise_grounding():
            http_kwargs["headers"] = {"X-Goog-User-Project": project}

        http_options = genai_types.HttpOptions(**http_kwargs)
        self._client = self._client_factory(
            vertexai=True,
            project=project,
            location=location,
            credentials=credentials,
            http_options=http_options,
        )
        self._client_auth_mode = "vertex"
        self._logger.info(
            "Gemini grounding client initialized (vertex project=%s location=%s enterprise=%s)",
            project,
            location,
            self._use_enterprise_grounding(),
        )
        return self._client

    def _build_generate_config(
        self,
        params: SearchCallParams,
        *,
        auth_mode: GeminiAuthMode,
        temperature: float,
    ) -> Any:
        exclude_domains = list(params.blocked_domains) if params.blocked_domains else None
        use_enterprise = auth_mode == "vertex" and self._use_enterprise_grounding()

        if use_enterprise:
            tool = genai_types.Tool(
                enterprise_web_search=genai_types.EnterpriseWebSearch(
                    exclude_domains=exclude_domains,
                )
            )
        else:
            google_search_kwargs: dict[str, Any] = {}
            if exclude_domains and auth_mode == "vertex":
                google_search_kwargs["exclude_domains"] = exclude_domains
            tool = genai_types.Tool(google_search=genai_types.GoogleSearch(**google_search_kwargs))

        timeout_ms = int(max(params.timeout_seconds, 0) * 1000) or None
        http_options = genai_types.HttpOptions(timeout=timeout_ms) if timeout_ms else None
        return genai_types.GenerateContentConfig(
            tools=[tool],
            temperature=temperature,
            http_options=http_options,
        )

    def _parse_response(
        self,
        response: Any,
        *,
        auth_mode: GeminiAuthMode,
        params_applied: list[str],
        params_ignored: list[str],
        blocked_domains: list[str] | None,
    ) -> BackendRawResult:
        answer = getattr(response, "text", None)
        grounding_meta = self._extract_grounding_metadata(response)
        citations = self._citations_from_grounding(grounding_meta)
        if blocked_domains:
            blocked = {d.lower().lstrip(".") for d in blocked_domains}
            citations = [c for c in citations if not any((c.get("domain") or urlparse(c.get("url", "")).netloc).lower().endswith(b) for b in blocked)]

        gemini_grounding = self.build_gemini_grounding_passthrough(grounding_meta)
        provider_native: dict[str, Any] = {
            "gemini_auth_mode": auth_mode,
            "gemini_grounding": gemini_grounding,
            "enterprise_web_search": bool(auth_mode == "vertex" and self._use_enterprise_grounding()),
            "exclude_domains_applied": list(blocked_domains or []),
        }
        if bool(getattr(self._config, "gemini_include_raw_grounding", False)):
            provider_native["grounding_metadata"] = self._serialize_sdk_value(grounding_meta)
            provider_native["generate_content_response"] = self._serialize_sdk_value(response)

        if not citations:
            return BackendRawResult(
                success=False,
                answer=answer,
                error="Gemini grounding returned no citation URLs",
                error_type="empty_grounding_chunks",
                backend=self.name,
                params_applied=params_applied,
                params_ignored=params_ignored,
                provider_native=provider_native,
            )

        return BackendRawResult(
            success=True,
            answer=answer,
            citations=citations,
            backend=self.name,
            params_applied=params_applied,
            params_ignored=params_ignored,
            provider_native=provider_native,
        )

    @staticmethod
    def _extract_grounding_metadata(response: Any) -> Any | None:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return None
        first = candidates[0]
        return getattr(first, "grounding_metadata", None)

    @staticmethod
    def _serialize_sdk_value(value: Any) -> Any:
        """Best-effort JSON-safe dump of google-genai pydantic / namespace objects."""
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
            return {str(k): GeminiGroundingBackend._serialize_sdk_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [GeminiGroundingBackend._serialize_sdk_value(v) for v in value]
        raw_dict = getattr(value, "__dict__", None)
        if isinstance(raw_dict, dict) and raw_dict:
            return {str(k): GeminiGroundingBackend._serialize_sdk_value(v) for k, v in raw_dict.items() if not str(k).startswith("_")}
        return {"_repr": repr(value)}

    @staticmethod
    def _citations_from_grounding(grounding_meta: Any) -> list[dict[str, Any]]:
        if grounding_meta is None:
            return []
        chunks = getattr(grounding_meta, "grounding_chunks", None) or []
        citations: list[dict[str, Any]] = []
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if web is None:
                continue
            uri = getattr(web, "uri", None) or ""
            if not uri:
                continue
            citations.append(
                {
                    "url": uri,
                    "title": getattr(web, "title", None) or "",
                    "domain": getattr(web, "domain", None) or urlparse(uri).netloc,
                    "snippet": "",
                }
            )
        return citations

    @staticmethod
    def build_gemini_grounding_passthrough(grounding_meta: Any) -> dict[str, Any]:
        """Build §3.13 TOS passthrough block for ``_search_metadata.gemini_grounding``."""
        web_search_queries: list[str] = []
        search_entry_point: dict[str, Any] = {}
        if grounding_meta is not None:
            queries = getattr(grounding_meta, "web_search_queries", None) or []
            web_search_queries = [str(q) for q in queries if q]
            entry = getattr(grounding_meta, "search_entry_point", None)
            if entry is not None:
                rendered = getattr(entry, "rendered_content", None)
                if rendered:
                    search_entry_point["rendered_content"] = rendered
                sdk_blob = getattr(entry, "sdk_blob", None)
                if sdk_blob is not None:
                    search_entry_point["sdk_blob"] = sdk_blob

        rendered_content = search_entry_point.get("rendered_content") or ""
        return {
            "web_search_queries": web_search_queries,
            "search_entry_point": search_entry_point,
            "requires_search_suggestions_ui": bool(rendered_content),
        }

    def _failure_from_exception(
        self,
        exc: Exception,
        *,
        auth_mode: GeminiAuthMode | None,
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
        elif GENAI_AVAILABLE and genai_errors is not None and isinstance(exc, genai_errors.APIError):
            code = getattr(exc, "code", None)
            message = getattr(exc, "message", None) or message
            if code in (401, 403):
                error_type = "auth"
            elif code == 429:
                error_type = "quota_exceeded"
            elif code in (408, 504):
                error_type = "timeout"
            else:
                error_type = f"http_{code}" if code else "search_api_error"
        elif isinstance(exc, TimeoutError) or exc.__class__.__name__ in (
            "TimeoutException",
            "ReadTimeout",
            "ConnectTimeout",
        ):
            error_type = "timeout"

        self._logger.warning("Gemini grounding failed (%s): %s", error_type, message)
        return BackendRawResult(
            success=False,
            error=message,
            error_type=error_type,
            backend=self.name,
            params_applied=params_applied,
            params_ignored=params_ignored,
            provider_native={"gemini_auth_mode": auth_mode} if auth_mode else None,
        )

    def _resolve_googleai_api_key(self) -> str | None:
        return self._optional_config("gemini_api_key") or self._optional_config("googleai_api_key")

    def _load_vertex_credentials(self) -> Any | None:
        specific = self._optional_config("google_application_credentials_vertex_gemini") or ""
        fallback = self._optional_config("google_application_credentials") or ""
        from aiecs.llm.utils.gcp_credentials import load_optional_service_account_credentials

        if specific and not os.path.isfile(specific):
            raise RuntimeError(f"Gemini Vertex credentials file not found: {specific}")
        if not specific and fallback and not os.path.isfile(fallback):
            raise RuntimeError(f"Google Cloud credentials file not found: {fallback}")

        return load_optional_service_account_credentials(
            specific_path=specific,
            fallback_path=fallback,
        )

    @staticmethod
    def _use_enterprise_grounding() -> bool:
        value = (os.environ.get("GOOGLE_GENAI_USE_ENTERPRISE") or "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def _optional_config(self, field_name: str) -> str | None:
        value = getattr(self._config, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

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

        if params.blocked_domains:
            applied.append("blocked_domains")
        if params.allowed_domains:
            ignored.append("allowed_domains")
        if params.language and params.language != "en":
            ignored.append("language")
        if params.country and params.country != "us":
            ignored.append("country")
        return applied, ignored

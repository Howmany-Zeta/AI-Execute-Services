# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
SEARCH_TOOL_* credential resolution with opt-in LLM Settings fallback (M-D.5 §3.5, §7).

Also provides sync Vertex MaaS token helpers for Grok grounding (§3.4 / §3.12) —
mirrors ``VertexMaaSClient`` refresh logic without importing that class.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Callable, Literal

if TYPE_CHECKING:
    from ..core import SearchTool

logger = logging.getLogger(__name__)

GeminiAuthMode = Literal["googleai", "vertex"]
GrokAuthMode = Literal["xai", "vertex_maas"]

_TOKEN_REFRESH_BUFFER = timedelta(minutes=5)

_fallback_warned_backends: set[str] = set()


def log_fallback_warning_once(backend: str, *, log: logging.Logger | None = None) -> None:
    """Log LLM Settings fallback warning once per backend per process."""
    if backend in _fallback_warned_backends:
        return
    _fallback_warned_backends.add(backend)
    (log or logger).warning(
        "SearchTool using LLM Settings fallback for %s; " "set dedicated SEARCH_TOOL_* keys for production billing isolation",
        backend,
    )


def reset_fallback_warning_state_for_tests() -> None:
    """Clear process-wide fallback warning dedupe state (tests only)."""
    _fallback_warned_backends.clear()


def build_maas_openapi_base_url(project_id: str, location: str = "global") -> str:
    """Build Vertex MaaS OpenAI-compatible openapi base URL (sync; §9.2)."""
    project = project_id.strip()
    loc = (location or "global").strip() or "global"
    if loc == "global":
        return f"https://aiplatform.googleapis.com/v1/" f"projects/{project}/locations/global/endpoints/openapi"
    return f"https://{loc}-aiplatform.googleapis.com/v1/" f"projects/{project}/locations/{loc}/endpoints/openapi"


class SyncMaasTokenProvider:
    """Sync GCP access-token provider for MaaS OpenAI clients (no VertexMaaSClient)."""

    def __init__(
        self,
        *,
        credentials_path: str | None = None,
        fallback_credentials_path: str | None = None,
    ) -> None:
        self._credentials_path = credentials_path or ""
        self._fallback_credentials_path = fallback_credentials_path or ""
        self._credentials: Any | None = None
        self._token_expiry: datetime | None = None

    def needs_refresh(self) -> bool:
        if self._credentials is None or self._token_expiry is None:
            return True
        return datetime.now(tz=timezone.utc) >= (self._token_expiry - _TOKEN_REFRESH_BUFFER)

    def get_access_token(self) -> str:
        """Refresh when needed and return a non-empty access token string."""
        if not self.needs_refresh():
            token = getattr(self._credentials, "token", None)
            if isinstance(token, str) and token:
                return token

        try:
            import google.auth
            import google.auth.transport.requests
        except ImportError as exc:
            raise RuntimeError("google-auth is required for Vertex MaaS Grok credentials") from exc

        from aiecs.llm.utils.gcp_credentials import load_optional_service_account_credentials

        spec = self._credentials_path
        fb = self._fallback_credentials_path
        if spec and not os.path.isfile(spec):
            raise RuntimeError(f"Vertex MaaS credentials file not found: {spec}")
        if not spec and fb and not os.path.isfile(fb):
            raise RuntimeError(f"Google Cloud credentials file not found: {fb}")

        explicit = load_optional_service_account_credentials(specific_path=spec, fallback_path=fb)
        try:
            if explicit is not None:
                credentials = explicit
            else:
                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
        except Exception as exc:
            raise RuntimeError(f"Failed to obtain GCP credentials for MaaS Grok: {exc}") from exc

        self._credentials = credentials
        if hasattr(credentials, "expiry") and credentials.expiry:
            expiry = credentials.expiry
            self._token_expiry = expiry if expiry.tzinfo else expiry.replace(tzinfo=timezone.utc)
        else:
            self._token_expiry = datetime.now(tz=timezone.utc) + timedelta(hours=1)

        token = credentials.token
        if not isinstance(token, str) or not token:
            raise RuntimeError("GCP access token missing or invalid after credentials.refresh()")
        return token


CredentialSource = Literal["search_tool", "llm_fallback"]


class CredentialResolver:
    """Resolve Gemini/Grok auth modes from SEARCH_TOOL_* with optional LLM fallback."""

    def __init__(
        self,
        config: SearchTool.Config,
        *,
        settings_loader: Callable[[], object] | None = None,
    ) -> None:
        self._config = config
        self._settings_loader = settings_loader
        self._llm_settings: object | None = None
        self._llm_settings_loaded = False

    def resolve_credential_source(self, backend: str) -> CredentialSource | None:
        """
        Return ``search_tool`` | ``llm_fallback`` for observability (§3.5 / §10).

        ``None`` when the backend is unconfigured or is a consumer custom name.
        Does not emit extra fallback warnings (silent Settings probe).
        """
        from .registry import normalize_backend_name

        name = normalize_backend_name(backend) or (backend or "").strip()
        if name == "gemini":
            return self._gemini_credential_source()
        if name == "grok":
            return self._grok_credential_source()
        if name == "google_cse":
            if self._optional_str("google_api_key") and self._optional_str("google_cse_id"):
                return "search_tool"
            return None
        return None

    def resolve_gemini_auth_mode(self) -> GeminiAuthMode | None:
        """Return ``googleai``, ``vertex``, or ``None`` when Gemini is not configured."""
        mode = (self._optional_str("gemini_grounding_auth") or "auto").lower()

        if mode == "googleai":
            if self._has_search_tool_gemini_googleai_key():
                return "googleai"
            return self._resolve_gemini_googleai_from_llm_fallback()

        if mode == "vertex":
            if self._has_search_tool_gemini_vertex():
                return "vertex"
            return self._resolve_gemini_vertex_from_llm_fallback()

        if self._has_search_tool_gemini_googleai_key():
            return "googleai"
        if self._has_search_tool_gemini_vertex():
            return "vertex"
        googleai = self._resolve_gemini_googleai_from_llm_fallback()
        if googleai is not None:
            return googleai
        return self._resolve_gemini_vertex_from_llm_fallback()

    def resolve_grok_auth_mode(self) -> GrokAuthMode | None:
        """Return ``xai``, ``vertex_maas``, or ``None`` when Grok is not configured."""
        mode = (self._optional_str("grok_grounding_auth") or "auto").lower()
        maas_enabled = bool(getattr(self._config, "grok_maas_web_search_enabled", False))

        if mode == "xai":
            if self._has_search_tool_grok_xai_key():
                return "xai"
            return self._resolve_grok_xai_from_llm_fallback()

        if mode == "vertex_maas":
            # Forced mode does not require grok_maas_web_search_enabled (§3.12).
            if self._has_search_tool_grok_maas():
                return "vertex_maas"
            return self._resolve_grok_maas_from_llm_fallback(maas_enabled=True)

        if self._has_search_tool_grok_xai_key():
            return "xai"
        if maas_enabled and self._has_search_tool_grok_maas():
            return "vertex_maas"
        xai = self._resolve_grok_xai_from_llm_fallback()
        if xai is not None:
            return xai
        return self._resolve_grok_maas_from_llm_fallback(maas_enabled=maas_enabled)

    def _optional_str(self, field_name: str) -> str | None:
        value = getattr(self._config, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _has_search_tool_gemini_googleai_key(self) -> bool:
        return bool(self._optional_str("gemini_api_key") or self._optional_str("googleai_api_key"))

    def _has_search_tool_gemini_vertex(self) -> bool:
        project = self._optional_str("vertex_project_id")
        if not project:
            return False
        return bool(self._optional_str("google_application_credentials_vertex_gemini") or self._optional_str("google_application_credentials"))

    def _has_search_tool_grok_xai_key(self) -> bool:
        return bool(self._optional_str("grok_api_key") or self._optional_str("xai_api_key"))

    def _has_search_tool_grok_maas(self) -> bool:
        project = self._optional_str("vertex_project_id_maas")
        if not project:
            return False
        return bool(self._optional_str("google_application_credentials_vertex_maas") or self._optional_str("google_application_credentials"))

    def _gemini_credential_source(self) -> CredentialSource | None:
        mode = (self._optional_str("gemini_grounding_auth") or "auto").lower()
        if mode == "googleai":
            if self._has_search_tool_gemini_googleai_key():
                return "search_tool"
            return "llm_fallback" if self._llm_has_gemini_googleai() else None
        if mode == "vertex":
            if self._has_search_tool_gemini_vertex():
                return "search_tool"
            return "llm_fallback" if self._llm_has_gemini_vertex() else None
        if self._has_search_tool_gemini_googleai_key() or self._has_search_tool_gemini_vertex():
            return "search_tool"
        if self._llm_has_gemini_googleai() or self._llm_has_gemini_vertex():
            return "llm_fallback"
        return None

    def _grok_credential_source(self) -> CredentialSource | None:
        mode = (self._optional_str("grok_grounding_auth") or "auto").lower()
        maas_enabled = bool(getattr(self._config, "grok_maas_web_search_enabled", False))
        if mode == "xai":
            if self._has_search_tool_grok_xai_key():
                return "search_tool"
            return "llm_fallback" if self._llm_has_grok_xai() else None
        if mode == "vertex_maas":
            if self._has_search_tool_grok_maas():
                return "search_tool"
            return "llm_fallback" if self._llm_has_grok_maas(maas_enabled=True) else None
        if self._has_search_tool_grok_xai_key():
            return "search_tool"
        if maas_enabled and self._has_search_tool_grok_maas():
            return "search_tool"
        if self._llm_has_grok_xai():
            return "llm_fallback"
        if self._llm_has_grok_maas(maas_enabled=maas_enabled):
            return "llm_fallback"
        return None

    def _llm_has_gemini_googleai(self) -> bool:
        settings = self._load_llm_settings()
        return bool(settings and self._settings_str(settings, "googleai_api_key"))

    def _llm_has_gemini_vertex(self) -> bool:
        settings = self._load_llm_settings()
        return bool(settings and self._settings_has_vertex_gemini(settings))

    def _llm_has_grok_xai(self) -> bool:
        settings = self._load_llm_settings()
        if settings is None:
            return False
        return bool(self._settings_str(settings, "xai_api_key") or self._settings_str(settings, "grok_api_key"))

    def _llm_has_grok_maas(self, *, maas_enabled: bool) -> bool:
        if not maas_enabled:
            return False
        settings = self._load_llm_settings()
        return bool(settings and self._settings_has_vertex_maas(settings))

    def _allow_llm_fallback(self) -> bool:
        return bool(getattr(self._config, "allow_llm_credential_fallback", False))

    def _load_llm_settings(self) -> object | None:
        if not self._allow_llm_fallback():
            return None
        if self._llm_settings_loaded:
            return self._llm_settings
        if self._settings_loader is None:
            from aiecs.config.config import get_settings

            self._llm_settings = get_settings()
        else:
            self._llm_settings = self._settings_loader()
        self._llm_settings_loaded = True
        return self._llm_settings

    def _resolve_gemini_googleai_from_llm_fallback(self) -> Literal["googleai"] | None:
        settings = self._load_llm_settings()
        if settings is None:
            return None
        api_key = self._settings_str(settings, "googleai_api_key")
        if not api_key:
            return None
        log_fallback_warning_once("gemini")
        return "googleai"

    def _resolve_gemini_vertex_from_llm_fallback(self) -> Literal["vertex"] | None:
        settings = self._load_llm_settings()
        if settings is None or not self._settings_has_vertex_gemini(settings):
            return None
        log_fallback_warning_once("gemini")
        return "vertex"

    def _resolve_grok_xai_from_llm_fallback(self) -> Literal["xai"] | None:
        settings = self._load_llm_settings()
        if settings is None:
            return None
        if not (self._settings_str(settings, "xai_api_key") or self._settings_str(settings, "grok_api_key")):
            return None
        log_fallback_warning_once("grok")
        return "xai"

    def _resolve_grok_maas_from_llm_fallback(self, *, maas_enabled: bool) -> Literal["vertex_maas"] | None:
        if not maas_enabled:
            return None
        settings = self._load_llm_settings()
        if settings is None or not self._settings_has_vertex_maas(settings):
            return None
        log_fallback_warning_once("grok")
        return "vertex_maas"

    @staticmethod
    def _settings_str(settings: object, field_name: str) -> str | None:
        value = getattr(settings, field_name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _settings_has_vertex_gemini(settings: object) -> bool:
        project = CredentialResolver._settings_str(settings, "vertex_project_id")
        if not project:
            return False
        return bool(CredentialResolver._settings_str(settings, "google_application_credentials_vertex_gemini") or CredentialResolver._settings_str(settings, "google_application_credentials"))

    @staticmethod
    def _settings_has_vertex_maas(settings: object) -> bool:
        project = getattr(settings, "maas_vertex_project_id", None)
        if callable(project):
            project = project()
        project_text = str(project).strip() if project else ""
        if not project_text:
            project_text = CredentialResolver._settings_str(settings, "vertex_project_id_maas") or ""
            if not project_text:
                project_text = CredentialResolver._settings_str(settings, "vertex_project_id") or ""
        if not project_text:
            return False
        return bool(CredentialResolver._settings_str(settings, "google_application_credentials_vertex_maas") or CredentialResolver._settings_str(settings, "google_application_credentials"))

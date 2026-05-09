# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""
Vertex AI MaaS (Model-as-a-Service) client.

Provides a unified OpenAI-compatible entry point for all partner / open models
hosted on Vertex AI Model Garden MaaS, including:

  * xAI Grok   – model IDs like ``grok-4.20-reasoning``, ``grok-4.20-non-reasoning``
  * Qwen        – model IDs like ``qwen3-235b-a22b-instruct-2507-maas``
  * Llama       – model IDs like ``llama-4-maverick-17b-128e-instruct-maas``
  * DeepSeek    – model IDs like ``deepseek-v3-2-maas``
  * Mistral     – model IDs like ``mistral-medium-3``
  * and others available as MaaS on Model Garden

All models share the same Vertex AI OpenAI-compatible endpoint:

    https://{location}-aiplatform.googleapis.com/v1/projects/{project}/
        locations/{location}/endpoints/openapi

Authentication uses project/region
``VERTEX_PROJECT_ID_MAAS`` / ``VERTEX_LOCATION_MAAS``, or falls back to
``VERTEX_PROJECT_ID`` / ``VERTEX_LOCATION``.
Prefer ``GOOGLE_APPLICATION_CREDENTIALS_VERTEX_MAAS``; otherwise
``GOOGLE_APPLICATION_CREDENTIALS`` (or ADC). Access tokens are cached and
refreshed automatically 5 minutes before expiry. Credentials are loaded per
client without overwriting process-global ``GOOGLE_APPLICATION_CREDENTIALS``.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI

from aiecs.config.config import get_settings
from aiecs.llm.clients.base_client import (
    BaseLLMClient,
    LLMMessage,
    LLMResponse,
    ProviderNotAvailableError,
    RateLimitError,
)
from aiecs.llm.clients.openai_compatible_mixin import OpenAICompatibleFunctionCallingMixin

logger = logging.getLogger(__name__)

# Refresh the GCP access token this many minutes before it expires.
_TOKEN_REFRESH_BUFFER = timedelta(minutes=5)

# Model-name prefix → publisher (informational; used for logging only).
_PUBLISHER_BY_PREFIX: Dict[str, str] = {
    "grok": "xai",
    "qwen": "qwen",
    "llama": "meta",
    "deepseek": "deepseek",
    "mistral": "mistralai",
    "codestral": "mistralai",
    "minimax": "minimax",
    "kimi": "moonshot",
    "glm": "zhipuai",
    "gpt-oss": "openai",
}


def _infer_publisher(model_name: str) -> str:
    """Return the publisher name inferred from the model-name prefix."""
    lower = model_name.lower()
    for prefix, publisher in _PUBLISHER_BY_PREFIX.items():
        if lower.startswith(prefix):
            return publisher
    return "unknown"


def _to_api_model(model_name: str) -> str:
    """Return the ``<publisher>/<model>`` form required by the Vertex AI openapi endpoint.

    If *model_name* already contains a ``/`` it is returned unchanged, so
    callers can pass a fully-qualified name directly.
    """
    if "/" in model_name:
        return model_name
    publisher = _infer_publisher(model_name)
    if publisher == "unknown":
        return model_name  # best-effort; the API will reject if wrong
    return f"{publisher}/{model_name}"


class VertexMaaSClient(BaseLLMClient, OpenAICompatibleFunctionCallingMixin):
    """Vertex AI MaaS unified client for partner / open models.

    Uses project/region ``VERTEX_PROJECT_ID_MAAS`` / ``VERTEX_LOCATION_MAAS``,
    or falls back to ``VERTEX_PROJECT_ID`` / ``VERTEX_LOCATION``.
    GCP Application Default Credentials or a per-client service-account JSON
    path are used for authentication; the access token is refreshed transparently before expiry.
    """

    def __init__(self) -> None:
        super().__init__("VertexMaaS")
        self.settings = get_settings()
        self._openai_client: Optional[AsyncOpenAI] = None
        self._credentials: Any = None
        self._token_expiry: Optional[datetime] = None

    # ------------------------------------------------------------------ helpers

    def _get_base_url(self) -> str:
        project_id = self.settings.maas_vertex_project_id
        if not project_id:
            raise ProviderNotAvailableError("Vertex AI project ID not configured (VERTEX_PROJECT_ID_MAAS or VERTEX_PROJECT_ID)")
        location = self.settings.maas_vertex_location or "us-central1"

        if location == "global":
            # Global endpoint: hostname has no location prefix.
            # Required for partner models such as xAI Grok.
            return f"https://aiplatform.googleapis.com/v1/" f"projects/{project_id}/locations/global/endpoints/openapi"
        return f"https://{location}-aiplatform.googleapis.com/v1/" f"projects/{project_id}/locations/{location}/endpoints/openapi"

    def _token_needs_refresh(self) -> bool:
        """Return True when no token exists or it expires within the buffer window."""
        if self._credentials is None or self._token_expiry is None:
            return True
        return datetime.now(tz=timezone.utc) >= (self._token_expiry - _TOKEN_REFRESH_BUFFER)

    def _refresh_credentials(self) -> str:
        """Obtain / refresh GCP credentials and return a fresh access token."""
        try:
            import google.auth
            import google.auth.transport.requests
        except ImportError:
            raise ProviderNotAvailableError("google-auth is not installed. Install with: pip install google-auth")

        from aiecs.llm.utils.gcp_credentials import load_optional_service_account_credentials

        spec = self.settings.google_application_credentials_vertex_maas
        fb = self.settings.google_application_credentials

        if spec and not os.path.isfile(spec):
            raise ProviderNotAvailableError(f"Vertex MaaS credentials file not found: {spec}")
        if not spec and fb and not os.path.isfile(fb):
            raise ProviderNotAvailableError(f"Google Cloud credentials file not found: {fb}")

        explicit = load_optional_service_account_credentials(specific_path=spec, fallback_path=fb)
        try:
            if explicit is not None:
                credentials = explicit
            else:
                credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            credentials.refresh(auth_req)
        except Exception as exc:
            raise ProviderNotAvailableError(f"Failed to obtain GCP credentials: {exc}") from exc

        self._credentials = credentials
        # Cache expiry; fall back to 1 hour when not provided by the credential type.
        if hasattr(credentials, "expiry") and credentials.expiry:
            self._token_expiry = credentials.expiry.replace(tzinfo=timezone.utc)
        else:
            self._token_expiry = datetime.now(tz=timezone.utc) + timedelta(hours=1)

        self.logger.debug(f"GCP token refreshed, expires at {self._token_expiry.isoformat()}")
        token = credentials.token
        if not isinstance(token, str) or not token:
            raise ProviderNotAvailableError(
                "GCP access token missing or invalid after credentials.refresh().",
            )
        return token

    def _get_openai_client(self) -> AsyncOpenAI:
        """Return an ``AsyncOpenAI`` client backed by a fresh GCP access token."""
        if self._openai_client is None or self._token_needs_refresh():
            token = self._refresh_credentials()
            base_url = self._get_base_url()
            self._openai_client = AsyncOpenAI(
                base_url=base_url,
                api_key=token,
                timeout=360.0,
            )
            self.logger.info(f"VertexMaaS client initialised: {base_url}")
        return self._openai_client

    # ---------------------------------------------------------------- public API

    async def generate_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        input_price: Optional[float] = None,
        output_price: Optional[float] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion via the Vertex AI MaaS OpenAI-compatible endpoint."""
        client = self._get_openai_client()
        selected_model = model or self._get_default_model() or "grok-4.20-non-reasoning"
        api_model = _to_api_model(selected_model)  # e.g. "xai/grok-4.1-fast-non-reasoning"
        self.logger.debug(f"generate_text: model={selected_model} api_model={api_model}")

        try:
            response = await self._generate_text_with_function_calling(
                client=client,
                messages=messages,
                model=api_model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                input_price=input_price,
                output_price=output_price,
                **kwargs,
            )
            response.provider = self.provider_name
            response.model = selected_model  # expose user-facing name, not publisher-prefixed one
            return response
        except Exception as exc:
            if "rate limit" in str(exc).lower() or "429" in str(exc):
                raise RateLimitError(f"VertexMaaS rate limit exceeded: {exc}") from exc
            self.logger.error(f"VertexMaaS API error: {exc}")
            raise

    async def stream_text(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Any] = None,
        return_chunks: bool = False,
        input_price: Optional[float] = None,
        output_price: Optional[float] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Any, None]:
        """Stream a completion via the Vertex AI MaaS OpenAI-compatible endpoint."""
        client = self._get_openai_client()
        selected_model = model or self._get_default_model() or "grok-4.20-non-reasoning"
        api_model = _to_api_model(selected_model)
        self.logger.debug(f"stream_text: model={selected_model} api_model={api_model}")

        try:
            async for chunk in self._stream_text_with_function_calling(
                client=client,
                messages=messages,
                model=api_model,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=functions,
                tools=tools,
                tool_choice=tool_choice,
                return_chunks=return_chunks,
                **kwargs,
            ):
                yield chunk
        except Exception as exc:
            if "rate limit" in str(exc).lower() or "429" in str(exc):
                raise RateLimitError(f"VertexMaaS rate limit exceeded: {exc}") from exc
            self.logger.error(f"VertexMaaS streaming error: {exc}")
            raise

    async def close(self) -> None:
        """Release the underlying httpx client."""
        if self._openai_client is not None:
            await self._openai_client.close()
            self._openai_client = None

# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Bridge aiecs LLM settings/clients to Graphiti LLMClient and EmbedderClient."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable
from typing import Any, cast

from aiecs.config.config import Settings, get_settings
from aiecs.llm.clients.base_client import LLMMessage

logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_CHAT_MODEL = "gpt-4.1-mini"
_DEFAULT_OPENAI_SMALL_MODEL = "gpt-4.1-nano"
_DEFAULT_VERTEX_CHAT_MODEL = "gemini-2.5-flash"
_DEFAULT_VERTEX_SMALL_MODEL = "gemini-2.5-flash"
_DEFAULT_VERTEX_EMBEDDING_MODEL = "gemini-embedding-001"
_JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL | re.IGNORECASE)


def resolve_tm_llm_provider(settings: Settings | None = None) -> str:
    """Pick an aiecs LLM provider name from configured credentials (Vertex-first)."""
    settings = settings or get_settings()
    if settings.has_vertex_gcp_credentials_configured():
        return "Vertex"
    if (settings.googleai_api_key or "").strip():
        return "GoogleAI"
    if (settings.openai_api_key or "").strip():
        return "OpenAI"
    if (settings.xai_api_key or settings.grok_api_key or "").strip():
        return "xAI"
    if (settings.openrouter_api_key or "").strip():
        return "OpenRouter"
    return "OpenAI"


def resolve_tm_embedder_provider(settings: Settings | None = None) -> str | None:
    """Pick an embedder provider from configured credentials (Vertex-first)."""
    settings = settings or get_settings()
    if _has_vertex_embedder_config(settings):
        return "Vertex"
    if (settings.openai_api_key or "").strip():
        return "OpenAI"
    if (settings.googleai_api_key or "").strip():
        return "GoogleAI"
    return None


def _has_vertex_embedder_config(settings: Settings) -> bool:
    """True when Vertex AI embeddings can be initialized (project + GCP credentials)."""
    return bool((settings.vertex_project_id or "").strip() and settings.has_vertex_gcp_credentials_configured())


def _default_chat_models(provider: str) -> tuple[str, str]:
    if provider in ("VertexAI", "Vertex"):
        return _DEFAULT_VERTEX_CHAT_MODEL, _DEFAULT_VERTEX_SMALL_MODEL
    return _DEFAULT_OPENAI_CHAT_MODEL, _DEFAULT_OPENAI_SMALL_MODEL


def _strip_json_fences(content: str) -> str:
    text = content.strip()
    match = _JSON_FENCE_PATTERN.match(text)
    if match:
        return match.group(1).strip()
    return text


def _extract_json_dict(content: str) -> dict[str, Any]:
    """Parse JSON object from model text, tolerating markdown fences and prose wrappers."""
    text = _strip_json_fences(content)
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"value": parsed}
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
            return {"value": parsed}
        except json.JSONDecodeError:
            pass

    return {"content": content}


def _parse_structured_response(content: str, response_model: type[Any] | None) -> dict[str, Any]:
    text = _strip_json_fences(content)
    if response_model is not None and text:
        model_validate_json = getattr(response_model, "model_validate_json", None)
        if callable(model_validate_json):
            try:
                validated = model_validate_json(text)
                model_dump = getattr(validated, "model_dump", None)
                if callable(model_dump):
                    dumped = model_dump()
                    if isinstance(dumped, dict):
                        return dumped
            except Exception:
                logger.debug("Pydantic model_validate_json failed; falling back to JSON extraction", exc_info=True)
    return _extract_json_dict(content)


def _structured_output_kwargs(aiecs_client: Any) -> dict[str, Any]:
    provider = (getattr(aiecs_client, "provider_name", None) or "").strip()
    if provider in ("Vertex", "GoogleAI"):
        return {"response_mime_type": "application/json"}
    if provider in ("OpenAI", "OpenRouter", "xAI", "VertexMaaS"):
        return {"response_format": {"type": "json_object"}}
    return {}


def _embedder_text_from_input(input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]]) -> str:
    if isinstance(input_data, str):
        return input_data
    if isinstance(input_data, list):
        if not input_data:
            return ""
        first = input_data[0]
        if isinstance(first, str):
            return first
    raise TypeError(f"Unsupported embedder input type: {type(input_data).__name__}")


def build_graphiti_llm_clients(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[Any, Any]:
    """
    Build Graphiti LLM + embedder clients from aiecs Settings.

    Provider resolution is Vertex-first via :func:`resolve_tm_llm_provider`.

    When ``provider`` is ``OpenAI`` and ``OPENAI_API_KEY`` is set, uses native Graphiti
    OpenAI clients. Otherwise wraps :func:`aiecs.llm.client_resolver.resolve_llm_client`
    for chat. Embeddings use Vertex/Gemini when GCP credentials are configured, else
    OpenAI when ``OPENAI_API_KEY`` is set, else Google AI Studio when ``GOOGLEAI_API_KEY``
    is set.
    """
    settings = settings or get_settings()
    provider_name = provider or resolve_tm_llm_provider(settings)

    if (settings.openai_api_key or "").strip() and provider_name == "OpenAI":
        return _build_native_openai_clients(settings, model=model)

    return _build_aiecs_wrapped_clients(settings, provider=provider_name, model=model)


def _build_native_openai_clients(
    settings: Settings,
    *,
    model: str | None,
) -> tuple[Any, Any]:
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.llm_client.config import LLMConfig
    from graphiti_core.llm_client.openai_client import OpenAIClient

    chat_model = model or _DEFAULT_OPENAI_CHAT_MODEL
    config = LLMConfig(
        api_key=settings.openai_api_key,
        model=chat_model,
        small_model=_DEFAULT_OPENAI_SMALL_MODEL,
    )
    llm = OpenAIClient(config=config)
    embedder = OpenAIEmbedder(
        OpenAIEmbedderConfig(api_key=settings.openai_api_key),
    )
    return llm, embedder


def _build_aiecs_wrapped_clients(
    settings: Settings,
    *,
    provider: str,
    model: str | None,
) -> tuple[Any, Any]:
    from graphiti_core.llm_client.config import LLMConfig

    from aiecs.llm.client_resolver import resolve_llm_client

    chat_model, small_model = _default_chat_models(provider)
    aiecs_llm = resolve_llm_client(provider, model=model)
    config = LLMConfig(model=model or chat_model, small_model=small_model)
    llm = AiecsGraphitiLLMClient(config, aiecs_llm, default_model=model or chat_model, small_model=small_model)
    embedder = _build_embedder_client(settings)
    return llm, embedder


def _build_embedder_client(settings: Settings) -> Any:
    provider = resolve_tm_embedder_provider(settings)
    if provider == "Vertex":
        from aiecs.llm.client_resolver import resolve_llm_client

        aiecs_client = resolve_llm_client("Vertex")
        return AiecsGraphitiEmbedderClient(aiecs_client, embedding_model=_DEFAULT_VERTEX_EMBEDDING_MODEL)
    if provider == "OpenAI":
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

        return OpenAIEmbedder(OpenAIEmbedderConfig(api_key=settings.openai_api_key))
    if provider == "GoogleAI":
        from graphiti_core.embedder.gemini import GeminiEmbedder, GeminiEmbedderConfig

        return GeminiEmbedder(GeminiEmbedderConfig(api_key=settings.googleai_api_key, embedding_model=_DEFAULT_VERTEX_EMBEDDING_MODEL))
    raise ValueError("Graphiti embedder requires Vertex/GCP credentials, OPENAI_API_KEY, or GOOGLEAI_API_KEY " "(or use TM_BACKEND=none).")


class AiecsGraphitiEmbedderClient:
    """
    Graphiti-compatible embedder delegating to an aiecs provider client.

    Subclasses graphiti ``EmbedderClient`` at runtime to avoid import when graphiti is absent.
    """

    def __new__(cls, aiecs_client: Any, *, embedding_model: str = _DEFAULT_VERTEX_EMBEDDING_MODEL) -> Any:
        from graphiti_core.embedder.client import EmbedderClient

        class _Impl(EmbedderClient):
            def __init__(self, aiecs_client: Any, *, embedding_model: str) -> None:
                super().__init__()
                self._aiecs = aiecs_client
                self._embedding_model = embedding_model

            async def create(
                self,
                input_data: str | list[str] | Iterable[int] | Iterable[Iterable[int]],
            ) -> list[float]:
                text = _embedder_text_from_input(input_data)
                vectors = await self._aiecs.get_embeddings([text], model=self._embedding_model)
                if not vectors:
                    raise ValueError("No embeddings returned from aiecs embedder client")
                return cast(list[float], vectors[0])

            async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
                if not input_data_list:
                    return []
                batch = await self._aiecs.get_embeddings(input_data_list, model=self._embedding_model)
                return cast(list[list[float]], batch)

        return _Impl(aiecs_client, embedding_model=embedding_model)


class AiecsGraphitiLLMClient:
    """
    Graphiti-compatible LLM client delegating to an aiecs provider client.

    Subclasses graphiti ``LLMClient`` at runtime to avoid import when graphiti is absent.
    """

    def __new__(
        cls,
        config: Any,
        aiecs_client: Any,
        *,
        default_model: str | None = None,
        small_model: str | None = None,
    ) -> Any:
        from graphiti_core.llm_client import LLMClient as GraphitiLLMClient

        class _Impl(GraphitiLLMClient):
            def __init__(
                self,
                config: Any,
                aiecs_client: Any,
                *,
                default_model: str | None = None,
                small_model: str | None = None,
            ) -> None:
                super().__init__(config, cache=False)
                self._aiecs = aiecs_client
                self._default_model = default_model or config.model
                self._small_model = small_model or config.small_model

            def _model_for_size(self, model_size: Any) -> str:
                from graphiti_core.llm_client.config import ModelSize

                if model_size == ModelSize.small:
                    return self.small_model or self._small_model or _DEFAULT_OPENAI_SMALL_MODEL
                return getattr(self, "model", None) or self.config.model or self._default_model

            async def _generate_response_with_retry(
                self,
                messages: list[Any],
                response_model: type[Any] | None = None,
                max_tokens: int = 8192,
                model_size: Any = None,
            ) -> dict[str, Any]:
                """Unwrap token tuple so Graphiti callers receive a plain dict."""
                result = await self._generate_response(messages, response_model, max_tokens, model_size)
                if isinstance(result, tuple) and len(result) == 3:
                    parsed, input_tokens, output_tokens = result
                    self.token_tracker.record("", input_tokens, output_tokens)
                    if isinstance(parsed, dict):
                        return parsed
                    return {"value": parsed}
                if isinstance(result, dict):
                    return result
                return {"value": result}

            async def _generate_response(
                self,
                messages: list[Any],
                response_model: type[Any] | None = None,
                max_tokens: int = 8192,
                model_size: Any = None,
            ) -> tuple[dict[str, Any], int, int]:
                from graphiti_core.llm_client.config import ModelSize

                if model_size is None:
                    model_size = ModelSize.medium

                aiecs_messages = [LLMMessage(role=m.role, content=m.content or "") for m in messages]
                model = self._model_for_size(model_size)
                llm_kwargs: dict[str, Any] = {}
                if response_model is not None:
                    llm_kwargs.update(_structured_output_kwargs(self._aiecs))
                    llm_kwargs.setdefault("temperature", 0.0)

                response = await self._aiecs.generate_text(
                    aiecs_messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=self.temperature if response_model is None else llm_kwargs.pop("temperature", 0.0),
                    **llm_kwargs,
                )
                content = (response.content or "").strip()
                input_tokens = response.prompt_tokens or 0
                output_tokens = response.completion_tokens or 0

                if response_model is not None:
                    parsed = _parse_structured_response(content, response_model)
                    return parsed, input_tokens, output_tokens

                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        return parsed, input_tokens, output_tokens
                except json.JSONDecodeError:
                    pass
                return {"content": content}, input_tokens, output_tokens

        return _Impl(config, aiecs_client, default_model=default_model, small_model=small_model)

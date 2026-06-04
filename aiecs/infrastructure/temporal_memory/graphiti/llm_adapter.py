# /*---------------------------------------------------------------------------------------------
#  *  Copyright (c) IRETBL Corporation. All rights reserved.
#  *  Licensed under the Apache-2.0. See License.txt in the project root for license information.
#  *--------------------------------------------------------------------------------------------*/
"""Bridge aiecs LLM settings/clients to Graphiti LLMClient and EmbedderClient."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiecs.config.config import Settings, get_settings
from aiecs.llm.clients.base_client import LLMMessage

logger = logging.getLogger(__name__)

_DEFAULT_CHAT_MODEL = "gpt-4.1-mini"
_DEFAULT_SMALL_MODEL = "gpt-4.1-nano"


def resolve_tm_llm_provider(settings: Settings | None = None) -> str:
    """Pick an aiecs LLM provider name from configured API keys."""
    settings = settings or get_settings()
    if (settings.openai_api_key or "").strip():
        return "OpenAI"
    if (settings.xai_api_key or settings.grok_api_key or "").strip():
        return "xAI"
    if settings.has_vertex_gcp_credentials_configured() or (settings.googleai_api_key or "").strip():
        return "VertexAI"
    if (settings.openrouter_api_key or "").strip():
        return "OpenRouter"
    return "OpenAI"


def build_graphiti_llm_clients(
    settings: Settings | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> tuple[Any, Any]:
    """
    Build Graphiti LLM + embedder clients from aiecs Settings.

    When ``OPENAI_API_KEY`` is set, uses native Graphiti OpenAI clients (best compatibility).
    Otherwise wraps :func:`aiecs.llm.client_resolver.resolve_llm_client` for chat and OpenAI
    embeddings when an OpenAI key is available for embedder-only.
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

    chat_model = model or _DEFAULT_CHAT_MODEL
    config = LLMConfig(
        api_key=settings.openai_api_key,
        model=chat_model,
        small_model=_DEFAULT_SMALL_MODEL,
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

    aiecs_llm = resolve_llm_client(provider, model=model)
    config = LLMConfig(model=model or _DEFAULT_CHAT_MODEL, small_model=_DEFAULT_SMALL_MODEL)
    llm = AiecsGraphitiLLMClient(config, aiecs_llm, default_model=model)
    embedder = _build_embedder_client(settings)
    return llm, embedder


def _build_embedder_client(settings: Settings) -> Any:
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise ValueError("Graphiti embedder requires OPENAI_API_KEY (or use TM_BACKEND=none). " "Embedding bridge for non-OpenAI providers is not yet implemented.")
    return OpenAIEmbedder(OpenAIEmbedderConfig(api_key=api_key))


class AiecsGraphitiLLMClient:
    """
    Graphiti-compatible LLM client delegating to an aiecs provider client.

    Subclasses graphiti ``LLMClient`` at runtime to avoid import when graphiti is absent.
    """

    def __new__(cls, config: Any, aiecs_client: Any, *, default_model: str | None = None) -> Any:
        from graphiti_core.llm_client import LLMClient as GraphitiLLMClient

        class _Impl(GraphitiLLMClient):
            def __init__(self, config: Any, aiecs_client: Any, *, default_model: str | None = None) -> None:
                super().__init__(config, cache=False)
                self._aiecs = aiecs_client
                self._default_model = default_model or config.model

            def _model_for_size(self, model_size: Any) -> str:
                from graphiti_core.llm_client.config import ModelSize

                if model_size == ModelSize.small:
                    return self.small_model or _DEFAULT_SMALL_MODEL
                return self.model or self._default_model

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
                response = await self._aiecs.generate_text(
                    aiecs_messages,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                )
                content = (response.content or "").strip()
                input_tokens = response.prompt_tokens or 0
                output_tokens = response.completion_tokens or 0

                if response_model is not None:
                    parsed = json.loads(content) if content else {}
                    if not isinstance(parsed, dict):
                        parsed = {"value": parsed}
                    return parsed, input_tokens, output_tokens

                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        return parsed, input_tokens, output_tokens
                except json.JSONDecodeError:
                    pass
                return {"content": content}, input_tokens, output_tokens

        return _Impl(config, aiecs_client, default_model=default_model)

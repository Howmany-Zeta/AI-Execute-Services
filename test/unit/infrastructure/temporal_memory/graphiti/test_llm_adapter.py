"""Unit tests for Graphiti LLM/embedder adapter (Vertex-first resolution)."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from aiecs.config.config import Settings
from aiecs.infrastructure.temporal_memory.graphiti import llm_adapter

pytestmark = pytest.mark.unit


def _settings(**overrides: Any) -> Settings:
    """Build Settings without loading local .env (keeps tests isolated)."""
    base: dict[str, Any] = {
        "openai_api_key": "",
        "googleai_api_key": "",
        "vertex_project_id": "",
        "google_application_credentials": "",
        "google_application_credentials_vertex_gemini": "",
        "google_application_credentials_vertex_anthropic": "",
        "google_application_credentials_vertex_maas": "",
    }
    base.update(overrides)
    return Settings.model_construct(**base)


@pytest.fixture
def mock_graphiti_modules() -> None:
    """Register minimal graphiti_core stubs so adapter imports succeed in unit tests."""
    embedder_client_mod = types.ModuleType("graphiti_core.embedder.client")

    class EmbedderClient:
        def __init__(self) -> None:
            pass

        async def create(self, input_data: Any) -> list[float]:
            raise NotImplementedError

        async def create_batch(self, input_data_list: list[str]) -> list[list[float]]:
            raise NotImplementedError

    embedder_client_mod.EmbedderClient = EmbedderClient

    openai_mod = types.ModuleType("graphiti_core.embedder.openai")

    class OpenAIEmbedderConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    class OpenAIEmbedder:
        def __init__(self, config: Any) -> None:
            self.config = config

    openai_mod.OpenAIEmbedder = OpenAIEmbedder
    openai_mod.OpenAIEmbedderConfig = OpenAIEmbedderConfig

    llm_config_mod = types.ModuleType("graphiti_core.llm_client.config")

    class LLMConfig:
        def __init__(self, **kwargs: Any) -> None:
            self.__dict__.update(kwargs)

    llm_config_mod.LLMConfig = LLMConfig
    llm_config_mod.ModelSize = MagicMock(small="small", medium="medium")

    llm_client_mod = types.ModuleType("graphiti_core.llm_client")

    class LLMClient:
        def __init__(self, config: Any, cache: bool = False) -> None:
            self.config = config

    llm_client_mod.LLMClient = LLMClient

    openai_client_mod = types.ModuleType("graphiti_core.llm_client.openai_client")

    class OpenAIClient:
        def __init__(self, config: Any) -> None:
            self.config = config

    openai_client_mod.OpenAIClient = OpenAIClient

    saved = {name: sys.modules.get(name) for name in (
        "graphiti_core.embedder.client",
        "graphiti_core.embedder.openai",
        "graphiti_core.llm_client.config",
        "graphiti_core.llm_client",
        "graphiti_core.llm_client.openai_client",
    )}
    sys.modules["graphiti_core.embedder.client"] = embedder_client_mod
    sys.modules["graphiti_core.embedder.openai"] = openai_mod
    sys.modules["graphiti_core.llm_client.config"] = llm_config_mod
    sys.modules["graphiti_core.llm_client"] = llm_client_mod
    sys.modules["graphiti_core.llm_client.openai_client"] = openai_client_mod
    yield
    for name, module in saved.items():
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def test_resolve_tm_llm_provider_prefers_vertex_over_openai() -> None:
    settings = _settings(
        openai_api_key="sk-test",
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    assert llm_adapter.resolve_tm_llm_provider(settings) == "VertexAI"


def test_resolve_tm_llm_provider_openai_when_no_vertex() -> None:
    settings = _settings(openai_api_key="sk-test")
    assert llm_adapter.resolve_tm_llm_provider(settings) == "OpenAI"


def test_resolve_tm_llm_provider_vertex_from_googleai_key() -> None:
    settings = _settings(googleai_api_key="google-ai-key")
    assert llm_adapter.resolve_tm_llm_provider(settings) == "VertexAI"


def test_resolve_tm_embedder_provider_prefers_vertex_over_openai() -> None:
    settings = _settings(
        openai_api_key="sk-test",
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    assert llm_adapter.resolve_tm_embedder_provider(settings) == "VertexAI"


def test_resolve_tm_embedder_provider_openai_when_no_vertex() -> None:
    settings = _settings(openai_api_key="sk-test")
    assert llm_adapter.resolve_tm_embedder_provider(settings) == "OpenAI"


def test_resolve_tm_embedder_provider_googleai_when_no_vertex_or_openai() -> None:
    settings = _settings(googleai_api_key="google-ai-key")
    assert llm_adapter.resolve_tm_embedder_provider(settings) == "GoogleAI"


def test_resolve_tm_embedder_provider_none_when_unconfigured() -> None:
    settings = _settings()
    assert llm_adapter.resolve_tm_embedder_provider(settings) is None


def test_default_chat_models_vertex() -> None:
    chat, small = llm_adapter._default_chat_models("VertexAI")
    assert chat == "gemini-2.5-flash"
    assert small == "gemini-2.5-flash"


def test_build_embedder_client_vertex_without_openai_key(mock_graphiti_modules: None) -> None:
    settings = _settings(
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    mock_vertex = MagicMock()
    with patch("aiecs.llm.client_resolver.resolve_llm_client", return_value=mock_vertex) as resolve:
        embedder = llm_adapter._build_embedder_client(settings)

    resolve.assert_called_once_with("VertexAI")
    assert embedder.__class__.__name__ == "_Impl"
    assert embedder._aiecs is mock_vertex
    assert embedder._embedding_model == "gemini-embedding-001"


def test_build_embedder_client_openai_when_no_vertex(mock_graphiti_modules: None) -> None:
    settings = _settings(openai_api_key="sk-test")
    embedder = llm_adapter._build_embedder_client(settings)
    assert embedder.__class__.__name__ == "OpenAIEmbedder"
    assert embedder.config.kwargs["api_key"] == "sk-test"


def test_build_embedder_client_raises_when_unconfigured() -> None:
    settings = _settings()
    with pytest.raises(ValueError, match="Graphiti embedder requires"):
        llm_adapter._build_embedder_client(settings)


@pytest.mark.asyncio
async def test_aiecs_graphiti_embedder_client_create_and_batch(mock_graphiti_modules: None) -> None:
    mock_client = MagicMock()

    async def _get_embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
        if len(texts) == 1:
            return [[0.1, 0.2, 0.3]]
        return [[0.4, 0.5], [0.6, 0.7]]

    mock_client.get_embeddings = _get_embeddings

    embedder = llm_adapter.AiecsGraphitiEmbedderClient(mock_client, embedding_model="gemini-embedding-001")
    single = await embedder.create("hello")
    batch = await embedder.create_batch(["a", "b"])

    assert single == [0.1, 0.2, 0.3]
    assert batch == [[0.4, 0.5], [0.6, 0.7]]


def test_build_graphiti_llm_clients_vertex_returns_non_openai_embedder(mock_graphiti_modules: None) -> None:
    settings = _settings(
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    mock_llm = MagicMock()
    mock_embedder = MagicMock()

    with patch("aiecs.llm.client_resolver.resolve_llm_client", return_value=mock_llm):
        with patch.object(llm_adapter, "_build_embedder_client", return_value=mock_embedder) as build_embedder:
            with patch.object(llm_adapter, "AiecsGraphitiLLMClient", return_value=mock_llm) as llm_cls:
                llm, embedder = llm_adapter.build_graphiti_llm_clients(settings)

    build_embedder.assert_called_once_with(settings)
    llm_cls.assert_called_once()
    call_kwargs = llm_cls.call_args.kwargs
    assert call_kwargs["default_model"] == "gemini-2.5-flash"
    assert call_kwargs["small_model"] == "gemini-2.5-flash"
    assert llm is mock_llm
    assert embedder is mock_embedder


def test_build_graphiti_llm_clients_native_openai_when_explicit_provider(mock_graphiti_modules: None) -> None:
    settings = _settings(
        openai_api_key="sk-test",
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    native = (MagicMock(), MagicMock())

    with patch.object(llm_adapter, "_build_native_openai_clients", return_value=native) as native_builder:
        llm, embedder = llm_adapter.build_graphiti_llm_clients(settings, provider="OpenAI")

    native_builder.assert_called_once_with(settings, model=None)
    assert (llm, embedder) == native

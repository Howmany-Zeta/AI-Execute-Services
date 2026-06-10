"""Unit tests for Graphiti LLM/embedder adapter (Vertex-first resolution)."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

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

    class ModelSize:
        small = "small"
        medium = "medium"

    llm_config_mod.LLMConfig = LLMConfig
    llm_config_mod.ModelSize = ModelSize

    token_tracker_mod = types.ModuleType("graphiti_core.llm_client.token_tracker")

    class TokenUsageTracker:
        def __init__(self) -> None:
            self.records: list[tuple[str, int, int]] = []

        def record(self, prompt_name: str, input_tokens: int, output_tokens: int) -> None:
            self.records.append((prompt_name, input_tokens, output_tokens))

    token_tracker_mod.TokenUsageTracker = TokenUsageTracker

    llm_client_mod = types.ModuleType("graphiti_core.llm_client")

    class LLMClient:
        MAX_RETRIES = 0

        def __init__(self, config: Any, cache: bool = False) -> None:
            self.config = config
            self.token_tracker = TokenUsageTracker()

        async def generate_response(
            self,
            messages: list[Any],
            response_model: type[Any] | None = None,
            max_tokens: int | None = None,
            model_size: Any = None,
            group_id: str | None = None,
            prompt_name: str | None = None,
            *,
            attribute_extraction: bool = False,
        ) -> dict[str, Any]:
            _ = group_id, prompt_name, attribute_extraction
            return await self._generate_response_with_retry(messages, response_model, max_tokens or 8192, model_size)

        async def _generate_response_with_retry(
            self,
            messages: list[Any],
            response_model: type[Any] | None = None,
            max_tokens: int = 8192,
            model_size: Any = None,
        ) -> dict[str, Any]:
            result = await self._generate_response(messages, response_model, max_tokens, model_size)
            if isinstance(result, tuple) and len(result) == 3:
                parsed, input_tokens, output_tokens = result
                self.token_tracker.record("", input_tokens, output_tokens)
                return parsed
            return result

        async def _generate_response(self, *args: Any, **kwargs: Any) -> Any:
            raise NotImplementedError

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
        "graphiti_core.llm_client.token_tracker",
        "graphiti_core.llm_client",
        "graphiti_core.llm_client.openai_client",
    )}
    sys.modules["graphiti_core.embedder.client"] = embedder_client_mod
    sys.modules["graphiti_core.embedder.openai"] = openai_mod
    sys.modules["graphiti_core.llm_client.config"] = llm_config_mod
    sys.modules["graphiti_core.llm_client.token_tracker"] = token_tracker_mod
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
    assert llm_adapter.resolve_tm_llm_provider(settings) == "Vertex"


def test_resolve_tm_llm_provider_openai_when_no_vertex() -> None:
    settings = _settings(openai_api_key="sk-test")
    assert llm_adapter.resolve_tm_llm_provider(settings) == "OpenAI"


def test_resolve_tm_llm_provider_googleai_when_no_vertex() -> None:
    settings = _settings(googleai_api_key="google-ai-key")
    assert llm_adapter.resolve_tm_llm_provider(settings) == "GoogleAI"


def test_resolve_tm_embedder_provider_prefers_vertex_over_openai() -> None:
    settings = _settings(
        openai_api_key="sk-test",
        vertex_project_id="my-project",
        google_application_credentials_vertex_gemini="/path/to/creds.json",
    )
    assert llm_adapter.resolve_tm_embedder_provider(settings) == "Vertex"


def test_default_chat_models_vertex_aliases() -> None:
    for provider in ("Vertex", "VertexAI"):
        chat, small = llm_adapter._default_chat_models(provider)
        assert chat == "gemini-2.5-flash"
        assert small == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_aiecs_graphiti_embedder_client_create_accepts_single_element_list(mock_graphiti_modules: None) -> None:
    mock_client = MagicMock()

    async def _get_embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
        assert texts == ["query text"]
        return [[0.1, 0.2, 0.3]]

    mock_client.get_embeddings = _get_embeddings
    embedder = llm_adapter.AiecsGraphitiEmbedderClient(mock_client)
    assert await embedder.create(["query text"]) == [0.1, 0.2, 0.3]


def test_extract_json_dict_strips_markdown_fence() -> None:
    parsed = llm_adapter._extract_json_dict('```json\n{"extracted_entities": []}\n```')
    assert parsed == {"extracted_entities": []}


def test_parse_structured_response_uses_pydantic_model() -> None:
    class ExtractedEntities(BaseModel):
        extracted_entities: list[str] = Field(default_factory=list)

    parsed = llm_adapter._parse_structured_response('{"extracted_entities": ["Alice"]}', ExtractedEntities)
    assert parsed == {"extracted_entities": ["Alice"]}


@pytest.mark.asyncio
async def test_aiecs_graphiti_llm_client_generate_response_returns_dict(mock_graphiti_modules: None) -> None:
    class ExtractedEntities(BaseModel):
        extracted_entities: list[str] = Field(default_factory=list)

    class Message:
        def __init__(self, role: str, content: str) -> None:
            self.role = role
            self.content = content

    mock_client = MagicMock()
    mock_client.provider_name = "Vertex"

    async def _generate_text(*args: Any, **kwargs: Any) -> Any:
        _ = args
        assert kwargs.get("response_mime_type") == "application/json"
        response = MagicMock()
        response.content = '{"extracted_entities": ["Bob"]}'
        response.prompt_tokens = 3
        response.completion_tokens = 5
        return response

    mock_client.generate_text = _generate_text

    from graphiti_core.llm_client.config import LLMConfig

    llm = llm_adapter.AiecsGraphitiLLMClient(
        LLMConfig(model="gemini-2.5-flash", small_model="gemini-2.5-flash"),
        mock_client,
    )

    result = await llm.generate_response([Message(role="user", content="hi")], response_model=ExtractedEntities)
    assert isinstance(result, dict)
    validated = ExtractedEntities(**result)
    assert validated.extracted_entities == ["Bob"]

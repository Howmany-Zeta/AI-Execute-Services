"""
Tests for Entity Extraction LLM Configuration

Tests the ability to configure custom LLM clients for entity extraction.
"""

import pytest
from typing import List, AsyncGenerator
from aiecs.application.knowledge_graph.extractors.llm_entity_extractor import LLMEntityExtractor
from aiecs.llm import LLMClientFactory, LLMMessage, LLMResponse


class MockCustomEntityExtractionClient:
    """Mock custom LLM client for entity extraction testing"""

    def __init__(self, provider_name: str = "custom-entity-llm"):
        self.provider_name = provider_name
        self.closed = False

    async def generate_text(
        self, messages, model=None, temperature=None, max_tokens=None, **kwargs
    ):
        """Mock generate_text that returns entity extraction JSON"""
        # Return mock entity extraction response
        content = """[
  {
    "type": "Person",
    "properties": {"name": "Alice", "age": 30},
    "confidence": 0.95
  },
  {
    "type": "Company",
    "properties": {"name": "Tech Corp"},
    "confidence": 0.90
  }
]"""
        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=model or "custom-model",
            prompt_tokens=100,
            completion_tokens=50,
            tokens_used=150,
        )

    async def stream_text(
        self, messages, model=None, temperature=None, max_tokens=None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Mock stream_text"""
        tokens = ["Mock ", "streaming ", "response"]
        for token in tokens:
            yield token

    async def close(self):
        """Mock close"""
        self.closed = True

    async def get_embeddings(self, texts, model=None, **kwargs):
        """Mock get_embeddings"""
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.fixture
def cleanup_factory():
    """Cleanup factory after each test"""
    yield
    # Clear custom clients
    LLMClientFactory._custom_clients.clear()


@pytest.mark.asyncio
async def test_entity_extractor_with_custom_client(cleanup_factory):
    """Test LLMEntityExtractor with custom LLM client"""
    # Register custom client
    custom_client = MockCustomEntityExtractionClient("entity-llm")
    LLMClientFactory.register_custom_provider("entity-llm", custom_client)

    # Create extractor with custom client
    extractor = LLMEntityExtractor(
        llm_client=custom_client,
        temperature=0.1,
        max_tokens=2000,
    )

    # Extract entities
    text = "Alice, a 30-year-old data scientist, works at Tech Corp."
    entities = await extractor.extract_entities(text)

    # Verify entities were extracted
    assert len(entities) == 2
    assert entities[0].entity_type == "Person"
    assert entities[0].properties["name"] == "Alice"
    assert entities[1].entity_type == "Company"
    assert entities[1].properties["name"] == "Tech Corp"


@pytest.mark.asyncio
async def test_entity_extractor_from_config(cleanup_factory):
    """Test LLMEntityExtractor.from_config() with custom provider"""
    # Register custom client
    custom_client = MockCustomEntityExtractionClient("my-entity-llm")
    LLMClientFactory.register_custom_provider("my-entity-llm", custom_client)

    # Create extractor from config
    extractor = LLMEntityExtractor.from_config(
        provider="my-entity-llm",
        model="custom-model",
        temperature=0.1,
        max_tokens=2000,
    )

    # Verify client was resolved
    assert extractor.llm_client is not None
    assert extractor.llm_client.provider_name == "my-entity-llm"

    # Extract entities
    text = "Alice works at Tech Corp."
    entities = await extractor.extract_entities(text)

    # Verify extraction worked
    assert len(entities) == 2


@pytest.mark.asyncio
async def test_entity_extractor_without_custom_client(cleanup_factory):
    """Test LLMEntityExtractor falls back to LLM manager when no custom client"""
    # Create extractor without custom client (will use LLM manager)
    extractor = LLMEntityExtractor(
        provider=None,  # Will use default
        temperature=0.1,
        max_tokens=2000,
    )

    # Verify no custom client
    assert extractor.llm_client is None
    assert extractor.provider is None


@pytest.mark.asyncio
async def test_entity_extractor_from_config_no_provider(cleanup_factory):
    """Test LLMEntityExtractor.from_config() without provider uses defaults"""
    # Create extractor from config without provider
    extractor = LLMEntityExtractor.from_config()

    # Verify defaults were used
    assert extractor.temperature == 0.1  # Default from config
    assert extractor.max_tokens == 2000  # Default from config


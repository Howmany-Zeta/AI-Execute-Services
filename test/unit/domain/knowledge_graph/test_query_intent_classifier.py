"""
Tests for Query Intent Classifier

Tests the QueryIntentClassifier for RAG strategy selection.
"""

import pytest
from typing import AsyncGenerator
from aiecs.application.knowledge_graph.retrieval import QueryIntentClassifier, RetrievalStrategy
from aiecs.llm import LLMMessage, LLMResponse


class MockStrategySelectionClient:
    """Mock LLM client for strategy selection testing"""

    def __init__(self, provider_name: str = "strategy-llm"):
        self.provider_name = provider_name
        self.closed = False
        self.call_count = 0

    async def generate_text(
        self, messages, model=None, temperature=None, max_tokens=None, **kwargs
    ):
        """Mock generate_text that returns strategy classification"""
        self.call_count += 1

        # Extract query from messages
        query = messages[0].content if messages else ""

        # Simple mock classification based on keywords in the query
        # Look for the actual query after "Query: " in the prompt
        if "Query:" in query:
            actual_query = query.split("Query:")[1].strip().strip('"')
        else:
            actual_query = query

        # Classify based on keywords
        if "connected" in actual_query.lower() or "path" in actual_query.lower():
            strategy = "MULTI_HOP"
        elif "find all" in actual_query.lower() or "of type" in actual_query.lower():
            strategy = "FILTERED"
        elif "important" in actual_query.lower() or "key" in actual_query.lower():
            strategy = "PAGERANK"
        else:
            strategy = "VECTOR_SEARCH"

        return LLMResponse(
            content=strategy,
            provider=self.provider_name,
            model=model or "gpt-3.5-turbo",
            prompt_tokens=50,
            completion_tokens=5,
            tokens_used=55,
        )

    async def stream_text(
        self, messages, model=None, temperature=None, max_tokens=None, **kwargs
    ) -> AsyncGenerator[str, None]:
        """Mock stream_text"""
        tokens = ["VECTOR", "_", "SEARCH"]
        for token in tokens:
            yield token

    async def close(self):
        """Mock close"""
        self.closed = True

    async def get_embeddings(self, texts, model=None, **kwargs):
        """Mock get_embeddings"""
        return [[0.1, 0.2, 0.3] for _ in texts]


@pytest.mark.asyncio
async def test_classifier_with_llm_multi_hop():
    """Test classifier with LLM for multi-hop query"""
    client = MockStrategySelectionClient()
    classifier = QueryIntentClassifier(llm_client=client)

    strategy = await classifier.classify_intent("How is Alice connected to Bob?")

    assert strategy == RetrievalStrategy.MULTI_HOP
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_classifier_with_llm_filtered():
    """Test classifier with LLM for filtered query"""
    client = MockStrategySelectionClient()
    classifier = QueryIntentClassifier(llm_client=client)

    strategy = await classifier.classify_intent("Find all entities of type Person")

    assert strategy == RetrievalStrategy.FILTERED
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_classifier_with_llm_pagerank():
    """Test classifier with LLM for PageRank query"""
    client = MockStrategySelectionClient()
    classifier = QueryIntentClassifier(llm_client=client)

    strategy = await classifier.classify_intent("What are the most important entities?")

    assert strategy == RetrievalStrategy.PAGERANK
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_classifier_with_llm_vector_search():
    """Test classifier with LLM for vector search query"""
    client = MockStrategySelectionClient()
    classifier = QueryIntentClassifier(llm_client=client)

    strategy = await classifier.classify_intent("What is similar to this concept?")

    assert strategy == RetrievalStrategy.VECTOR_SEARCH
    assert client.call_count == 1


@pytest.mark.asyncio
async def test_classifier_caching():
    """Test that classifier caches results"""
    client = MockStrategySelectionClient()
    classifier = QueryIntentClassifier(llm_client=client, enable_caching=True)

    query = "How is Alice connected to Bob?"

    # First call
    strategy1 = await classifier.classify_intent(query)
    assert client.call_count == 1

    # Second call (should use cache)
    strategy2 = await classifier.classify_intent(query)
    assert client.call_count == 1  # No additional call
    assert strategy1 == strategy2


@pytest.mark.asyncio
async def test_classifier_without_llm_rule_based():
    """Test classifier falls back to rule-based when no LLM"""
    classifier = QueryIntentClassifier(llm_client=None)

    # Multi-hop query
    strategy = await classifier.classify_intent("How is Alice connected to Bob?")
    assert strategy == RetrievalStrategy.MULTI_HOP

    # Filtered query
    strategy = await classifier.classify_intent("Find all entities with property X")
    assert strategy == RetrievalStrategy.FILTERED

    # PageRank query
    strategy = await classifier.classify_intent("What are the most important entities?")
    assert strategy == RetrievalStrategy.PAGERANK

    # Default to vector search (no matching keywords)
    strategy = await classifier.classify_intent("What is quantum computing?")
    assert strategy == RetrievalStrategy.VECTOR_SEARCH


@pytest.mark.asyncio
async def test_classifier_empty_query():
    """Test classifier raises error for empty query"""
    classifier = QueryIntentClassifier(llm_client=None)

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await classifier.classify_intent("")

    with pytest.raises(ValueError, match="Query cannot be empty"):
        await classifier.classify_intent("   ")


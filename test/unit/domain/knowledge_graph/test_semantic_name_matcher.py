"""
Unit tests for SemanticNameMatcher and LRUEmbeddingCache.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from aiecs.application.knowledge_graph.fusion.semantic_name_matcher import (
    SemanticNameMatcher,
    SemanticMatcherConfig,
    SemanticMatchResult,
    LRUEmbeddingCache,
)


class TestLRUEmbeddingCache:
    """Tests for LRUEmbeddingCache."""

    def test_basic_get_set(self):
        """Test basic get/set operations."""
        cache = LRUEmbeddingCache(max_size=100)

        embedding = [0.1, 0.2, 0.3]
        cache.set("test", embedding)

        result = cache.get("test")
        assert result == embedding

    def test_case_insensitive(self):
        """Test case-insensitive lookup."""
        cache = LRUEmbeddingCache(max_size=100)

        embedding = [0.1, 0.2, 0.3]
        cache.set("Albert Einstein", embedding)

        # Should find with different casing
        assert cache.get("albert einstein") == embedding
        assert cache.get("ALBERT EINSTEIN") == embedding

    def test_miss_returns_none(self):
        """Test that missing key returns None."""
        cache = LRUEmbeddingCache(max_size=100)
        assert cache.get("nonexistent") is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = LRUEmbeddingCache(max_size=3)

        # Fill cache
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.set("c", [3.0])

        # Access 'a' to make it recently used
        cache.get("a")

        # Add new item - should evict 'b' (least recently used)
        cache.set("d", [4.0])

        assert cache.get("a") is not None  # Still there (recently used)
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") is not None  # Still there
        assert cache.get("d") is not None  # New item

    def test_invalidate(self):
        """Test cache invalidation."""
        cache = LRUEmbeddingCache(max_size=100)

        cache.set("test", [0.1, 0.2])
        assert cache.get("test") is not None

        result = cache.invalidate("test")
        assert result is True
        assert cache.get("test") is None

        # Invalidating non-existent key returns False
        assert cache.invalidate("nonexistent") is False

    def test_invalidate_many(self):
        """Test bulk invalidation."""
        cache = LRUEmbeddingCache(max_size=100)

        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.set("c", [3.0])

        removed = cache.invalidate_many(["a", "c", "nonexistent"])
        assert removed == 2

        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is None

    def test_clear(self):
        """Test cache clear."""
        cache = LRUEmbeddingCache(max_size=100)

        cache.set("a", [1.0])
        cache.set("b", [2.0])

        cache.clear()

        assert cache.size() == 0
        assert cache.get("a") is None

    def test_stats(self):
        """Test cache statistics."""
        cache = LRUEmbeddingCache(max_size=100)

        cache.set("a", [1.0])
        cache.get("a")  # Hit
        cache.get("a")  # Hit
        cache.get("b")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 2/3
        assert stats["size"] == 1

    def test_contains(self):
        """Test contains method."""
        cache = LRUEmbeddingCache(max_size=100)

        cache.set("test", [0.1])

        assert cache.contains("test") is True
        assert cache.contains("TEST") is True  # Case insensitive
        assert cache.contains("nonexistent") is False


class TestSemanticNameMatcher:
    """Tests for SemanticNameMatcher."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client for testing."""
        client = AsyncMock()
        client.provider_name = "test"
        return client

    @pytest.fixture
    def matcher(self, mock_llm_client):
        """Create matcher with mock client."""
        config = SemanticMatcherConfig(
            similarity_threshold=0.85,
            cache_max_size=100,
            enabled=True,
        )
        return SemanticNameMatcher(config=config, llm_client=mock_llm_client)

    def test_cosine_similarity_opposite(self, matcher):
        """Test cosine similarity for opposite vectors."""
        e1 = [1.0, 0.0, 0.0]
        e2 = [-1.0, 0.0, 0.0]
        similarity = matcher.cosine_similarity(e1, e2)
        assert similarity == pytest.approx(-1.0)

    def test_cosine_similarity_empty(self, matcher):
        """Test cosine similarity with empty vectors."""
        assert matcher.cosine_similarity([], [1.0]) == 0.0
        assert matcher.cosine_similarity([1.0], []) == 0.0

    @pytest.mark.asyncio
    async def test_get_embedding_cached(self, matcher, mock_llm_client):
        """Test that embeddings are cached."""
        embedding = [0.1, 0.2, 0.3]
        mock_llm_client.get_embeddings = AsyncMock(return_value=[embedding])

        # First call - should hit API
        result1 = await matcher.get_embedding("Albert Einstein")
        assert result1 == embedding
        assert mock_llm_client.get_embeddings.call_count == 1

        # Second call - should use cache
        result2 = await matcher.get_embedding("Albert Einstein")
        assert result2 == embedding
        assert mock_llm_client.get_embeddings.call_count == 1  # No additional API call

    @pytest.mark.asyncio
    async def test_match_returns_result(self, matcher, mock_llm_client):
        """Test match returns SemanticMatchResult."""
        # Same embedding = perfect match
        embedding = [0.5, 0.5, 0.5, 0.5]
        mock_llm_client.get_embeddings = AsyncMock(return_value=[embedding])

        result = await matcher.match("Name A", "Name B")

        assert isinstance(result, SemanticMatchResult)
        assert result.name1 == "Name A"
        assert result.name2 == "Name B"
        assert result.similarity == pytest.approx(1.0)
        assert result.is_match is True

    @pytest.mark.asyncio
    async def test_match_below_threshold(self, matcher, mock_llm_client):
        """Test match below threshold returns is_match=False."""
        # Different embeddings
        mock_llm_client.get_embeddings = AsyncMock(side_effect=[
            [[1.0, 0.0, 0.0]],  # First name
            [[0.0, 1.0, 0.0]],  # Second name (orthogonal)
        ])

        result = await matcher.match("Name A", "Name B")

        assert result.similarity == pytest.approx(0.0)
        assert result.is_match is False

    @pytest.mark.asyncio
    async def test_match_disabled(self, mock_llm_client):
        """Test match when semantic matching is disabled."""
        config = SemanticMatcherConfig(enabled=False)
        matcher = SemanticNameMatcher(config=config, llm_client=mock_llm_client)

        result = await matcher.match("Name A", "Name B")

        assert result.similarity == 0.0
        assert result.is_match is False
        # Should not call API
        mock_llm_client.get_embeddings.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_best_match(self, matcher, mock_llm_client):
        """Test find_best_match returns best candidate."""
        # Create embeddings with different similarities
        target = [1.0, 0.0, 0.0]
        candidate1 = [0.9, 0.1, 0.0]  # High similarity
        candidate2 = [0.0, 1.0, 0.0]  # Low similarity
        candidate3 = [0.95, 0.05, 0.0]  # Highest similarity

        mock_llm_client.get_embeddings = AsyncMock(side_effect=[
            [target],  # Target
            [candidate1, candidate2, candidate3],  # Candidates batch
        ])

        result = await matcher.find_best_match(
            "target",
            ["candidate1", "candidate2", "candidate3"],
            threshold=0.5,
        )

        assert result is not None
        assert result[0] == "candidate3"  # Best match
        assert result[1] > 0.9  # High similarity

    @pytest.mark.asyncio
    async def test_find_best_match_no_match(self, matcher, mock_llm_client):
        """Test find_best_match returns None when no match above threshold."""
        mock_llm_client.get_embeddings = AsyncMock(side_effect=[
            [[1.0, 0.0, 0.0]],  # Target
            [[0.0, 1.0, 0.0]],  # Candidate (orthogonal)
        ])

        result = await matcher.find_best_match(
            "target",
            ["candidate"],
            threshold=0.9,
        )

        assert result is None

    def test_invalidate_cache(self, matcher):
        """Test cache invalidation through matcher."""
        matcher.cache.set("test", [0.1])

        assert matcher.cache.contains("test")
        result = matcher.invalidate_cache("test")
        assert result is True
        assert not matcher.cache.contains("test")

    def test_get_cache_stats(self, matcher):
        """Test getting cache statistics."""
        stats = matcher.get_cache_stats()
        assert "size" in stats
        assert "hits" in stats
        assert "misses" in stats

    def test_cosine_similarity_identical(self, matcher):
        """Test cosine similarity for identical vectors."""
        embedding = [1.0, 0.0, 0.0]
        similarity = matcher.cosine_similarity(embedding, embedding)
        assert similarity == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self, matcher):
        """Test cosine similarity for orthogonal vectors."""
        e1 = [1.0, 0.0, 0.0]
        e2 = [0.0, 1.0, 0.0]
        similarity = matcher.cosine_similarity(e1, e2)
        assert similarity == pytest.approx(0.0)


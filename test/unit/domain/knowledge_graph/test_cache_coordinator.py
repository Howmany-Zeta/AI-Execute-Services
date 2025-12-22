"""
Unit tests for CacheCoordinator.
"""

import pytest
import asyncio
from unittest.mock import MagicMock

from aiecs.application.knowledge_graph.fusion.cache_coordinator import (
    CacheCoordinator,
    InvalidationResult,
)
from aiecs.application.knowledge_graph.fusion.semantic_name_matcher import (
    LRUEmbeddingCache,
)
from aiecs.domain.knowledge_graph.models.entity import Entity


class TestCacheCoordinator:
    """Tests for CacheCoordinator."""

    @pytest.fixture
    def cache(self):
        """Create embedding cache for testing."""
        return LRUEmbeddingCache(max_size=100)

    @pytest.fixture
    def coordinator(self, cache):
        """Create coordinator with cache."""
        coord = CacheCoordinator(embedding_cache=cache)
        return coord

    @pytest.fixture
    def sample_entity(self):
        """Create sample entity for testing."""
        return Entity(
            id="entity_123",
            entity_type="Person",
            properties={
                "name": "Albert Einstein",
                "_known_aliases": ["A. Einstein", "Einstein"],
                "_aliases": ["Prof. Einstein"],
            }
        )

    def test_init_with_cache(self, cache):
        """Test initialization with embedding cache."""
        coordinator = CacheCoordinator(embedding_cache=cache)
        assert coordinator._get_embedding_cache() is cache

    def test_set_embedding_cache(self):
        """Test setting embedding cache after init."""
        coordinator = CacheCoordinator()
        cache = LRUEmbeddingCache(max_size=50)

        coordinator.set_embedding_cache(cache)
        assert coordinator._get_embedding_cache() is cache

    @pytest.mark.asyncio
    async def test_on_entity_delete(self, coordinator, cache, sample_entity):
        """Test cache invalidation on entity delete."""
        # Pre-populate cache
        cache.set("Albert Einstein", [0.1, 0.2])
        cache.set("A. Einstein", [0.1, 0.2])
        cache.set("Einstein", [0.1, 0.2])
        cache.set("Prof. Einstein", [0.1, 0.2])
        cache.set("Other Name", [0.3, 0.4])  # Should not be invalidated

        result = await coordinator.on_entity_delete(sample_entity)

        assert result.success is True
        assert "albert einstein" in [n.lower() for n in result.affected_names]
        assert result.embeddings_invalidated >= 3  # At least primary + aliases

        # Verify cache state
        assert not cache.contains("Albert Einstein")
        assert not cache.contains("A. Einstein")
        assert cache.contains("Other Name")

    @pytest.mark.asyncio
    async def test_on_entity_merge(self, coordinator, cache):
        """Test cache invalidation on entity merge."""
        old_entity1 = Entity(
            id="entity_1",
            entity_type="Person",
            properties={"name": "Albert Einstein", "_known_aliases": ["Einstein"]}
        )
        old_entity2 = Entity(
            id="entity_2",
            entity_type="Person",
            properties={"name": "A. Einstein"}
        )
        new_entity = Entity(
            id="entity_merged",
            entity_type="Person",
            properties={"name": "Albert Einstein", "_known_aliases": ["Einstein", "A. Einstein"]}
        )

        # Pre-populate cache
        cache.set("Albert Einstein", [0.1])
        cache.set("Einstein", [0.2])
        cache.set("A. Einstein", [0.3])
        cache.set("Unrelated", [0.4])

        result = await coordinator.on_entity_merge(
            [old_entity1, old_entity2],
            new_entity
        )

        assert result.success is True
        assert result.embeddings_invalidated >= 3

        # Verify affected names collected from all entities
        assert not cache.contains("Albert Einstein")
        assert not cache.contains("Einstein")
        assert not cache.contains("A. Einstein")
        assert cache.contains("Unrelated")

    @pytest.mark.asyncio
    async def test_on_alias_update(self, coordinator, cache):
        """Test cache invalidation on alias update."""
        cache.set("old_alias", [0.1])
        cache.set("new_alias", [0.2])
        cache.set("unchanged", [0.3])

        result = await coordinator.on_alias_update(
            entity_id="entity_123",
            old_aliases=["old_alias"],
            new_aliases=["new_alias"],
        )

        assert result.success is True
        assert not cache.contains("old_alias")
        assert not cache.contains("new_alias")
        assert cache.contains("unchanged")

    @pytest.mark.asyncio
    async def test_invalidate_for_names(self, coordinator, cache):
        """Test direct invalidation for names."""
        cache.set("name1", [0.1])
        cache.set("name2", [0.2])
        cache.set("name3", [0.3])

        result = await coordinator.invalidate_for_names(["name1", "name2"])

        assert result.success is True
        assert result.embeddings_invalidated == 2
        assert not cache.contains("name1")
        assert not cache.contains("name2")
        assert cache.contains("name3")

    def test_verify_invariant_passes(self, coordinator, cache):
        """Test invariant verification passes when cache is clear."""
        # Cache doesn't contain the names
        result = coordinator.verify_invariant(
            "test_operation",
            {"name1", "name2"}
        )
        assert result is True

    def test_verify_invariant_fails(self, coordinator, cache):
        """Test invariant verification fails when names still in cache."""
        cache.set("name1", [0.1])

        result = coordinator.verify_invariant(
            "test_operation",
            {"name1", "name2"}
        )
        assert result is False

    def test_get_stats(self, coordinator, cache):
        """Test getting coordinator statistics."""
        stats = coordinator.get_stats()

        assert "invalidation_count" in stats
        assert "names_invalidated" in stats
        assert stats["has_embedding_cache"] is True

    @pytest.mark.asyncio
    async def test_stats_updated_after_invalidation(self, coordinator, cache):
        """Test stats are updated after invalidation."""
        cache.set("name1", [0.1])
        cache.set("name2", [0.2])

        await coordinator.invalidate_for_names(["name1", "name2"])

        stats = coordinator.get_stats()
        assert stats["invalidation_count"] == 1
        assert stats["names_invalidated"] == 2

    def test_reset_stats(self, coordinator):
        """Test resetting statistics."""
        coordinator._invalidation_count = 10
        coordinator._names_invalidated = 100

        coordinator.reset_stats()

        stats = coordinator.get_stats()
        assert stats["invalidation_count"] == 0
        assert stats["names_invalidated"] == 0

    @pytest.mark.asyncio
    async def test_empty_names_handled(self, coordinator, cache):
        """Test that empty name lists are handled gracefully."""
        result = await coordinator.invalidate_for_names([])

        assert result.success is True
        assert result.embeddings_invalidated == 0

    @pytest.mark.asyncio
    async def test_entity_without_aliases(self, coordinator, cache):
        """Test entity with no aliases."""
        entity = Entity(
            id="entity_456",
            entity_type="Thing",
            properties={"name": "Simple Entity"}
        )

        cache.set("Simple Entity", [0.1])

        result = await coordinator.on_entity_delete(entity)

        assert result.success is True
        assert not cache.contains("Simple Entity")


class TestCacheCoordinatorWithSemanticMatcher:
    """Tests for CacheCoordinator integrated with SemanticNameMatcher."""

    @pytest.fixture
    def semantic_matcher(self):
        """Create mock semantic matcher."""
        from aiecs.application.knowledge_graph.fusion.semantic_name_matcher import (
            SemanticNameMatcher,
            SemanticMatcherConfig,
        )
        from unittest.mock import AsyncMock

        config = SemanticMatcherConfig(enabled=True, cache_max_size=100)
        mock_client = AsyncMock()
        mock_client.provider_name = "test"
        return SemanticNameMatcher(config=config, llm_client=mock_client)

    def test_coordinator_uses_matcher_cache(self, semantic_matcher):
        """Test coordinator uses cache from semantic matcher."""
        coordinator = CacheCoordinator(semantic_matcher=semantic_matcher)

        # Should use the matcher's cache
        cache = coordinator._get_embedding_cache()
        assert cache is semantic_matcher.cache

    @pytest.mark.asyncio
    async def test_invalidate_through_matcher(self, semantic_matcher):
        """Test invalidation through matcher's cache."""
        coordinator = CacheCoordinator(semantic_matcher=semantic_matcher)

        # Add to matcher's cache
        semantic_matcher.cache.set("test_name", [0.1, 0.2])

        # Invalidate through coordinator
        result = await coordinator.invalidate_for_names(["test_name"])

        assert result.success is True
        assert not semantic_matcher.cache.contains("test_name")


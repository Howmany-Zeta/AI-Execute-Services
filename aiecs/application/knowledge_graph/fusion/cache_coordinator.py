"""
Cache Coordinator for Knowledge Graph Entity Fusion.

Coordinates cache invalidation between alias index and embedding cache
to prevent stale data after entity operations.

Invariant: No alias index update should complete without corresponding
embedding cache invalidation.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Set, TYPE_CHECKING

from aiecs.domain.knowledge_graph.models.entity import Entity

if TYPE_CHECKING:
    from .alias_index import AliasIndex
    from .semantic_name_matcher import SemanticNameMatcher, LRUEmbeddingCache

logger = logging.getLogger(__name__)


@dataclass
class InvalidationResult:
    """Result of cache invalidation operation."""
    affected_names: Set[str]
    alias_entries_removed: int
    embeddings_invalidated: int
    success: bool
    error: Optional[str] = None


class CacheCoordinator:
    """
    Coordinates cache invalidation between alias index and embedding cache.

    Ensures that when the alias index is updated, the embedding cache is
    also invalidated to prevent stale embeddings from being used.

    Key invariant: No alias index update completes without corresponding
    embedding cache invalidation.

    Example:
        ```python
        coordinator = CacheCoordinator(alias_index, semantic_matcher)

        # On entity merge
        await coordinator.on_entity_merge(old_entities, new_entity)

        # On entity delete
        await coordinator.on_entity_delete(entity)

        # On alias update
        await coordinator.on_alias_update(entity_id, old_aliases, new_aliases)
        ```
    """

    def __init__(
        self,
        alias_index: Optional["AliasIndex"] = None,
        semantic_matcher: Optional["SemanticNameMatcher"] = None,
        embedding_cache: Optional["LRUEmbeddingCache"] = None,
    ):
        """
        Initialize cache coordinator.

        Args:
            alias_index: Alias index to coordinate (optional)
            semantic_matcher: Semantic matcher with embedding cache (optional)
            embedding_cache: Direct embedding cache reference (optional,
                            uses semantic_matcher.cache if not provided)
        """
        self._alias_index = alias_index
        self._semantic_matcher = semantic_matcher
        self._embedding_cache = embedding_cache
        self._lock = asyncio.Lock()

        # Statistics
        self._invalidation_count = 0
        self._names_invalidated = 0

    def set_alias_index(self, alias_index: "AliasIndex") -> None:
        """Set the alias index reference."""
        self._alias_index = alias_index

    def set_semantic_matcher(self, semantic_matcher: "SemanticNameMatcher") -> None:
        """Set the semantic matcher reference."""
        self._semantic_matcher = semantic_matcher

    def set_embedding_cache(self, cache: "LRUEmbeddingCache") -> None:
        """Set the embedding cache reference directly."""
        self._embedding_cache = cache

    def _get_embedding_cache(self) -> Optional["LRUEmbeddingCache"]:
        """Get the embedding cache from matcher or direct reference."""
        if self._embedding_cache is not None:
            return self._embedding_cache
        if self._semantic_matcher is not None:
            return self._semantic_matcher.cache
        return None

    def _get_entity_name(self, entity: Entity) -> str:
        """Get the primary name of an entity."""
        # Entity stores name in properties, not as a direct attribute
        return entity.properties.get("name", "")

    def _get_entity_aliases(self, entity: Entity) -> Set[str]:
        """Get all aliases for an entity."""
        aliases: Set[str] = set()

        # Add primary name
        name = self._get_entity_name(entity)
        if name:
            aliases.add(name)

        # Add known aliases
        known_aliases = entity.properties.get("_known_aliases", [])
        if isinstance(known_aliases, list):
            aliases.update(known_aliases)

        # Add historical aliases (from previous merges)
        historical = entity.properties.get("_aliases", [])
        if isinstance(historical, list):
            aliases.update(historical)

        return aliases

    async def on_entity_merge(
        self,
        old_entities: List[Entity],
        new_entity: Entity,
    ) -> InvalidationResult:
        """
        Handle cache invalidation on entity merge.

        Collects all names from old entities and invalidates both
        alias index entries and embedding cache entries.

        Args:
            old_entities: Entities being merged (will be deleted)
            new_entity: Resulting merged entity

        Returns:
            InvalidationResult with details
        """
        async with self._lock:
            affected_names: Set[str] = set()

            # Collect all names from old entities
            for entity in old_entities:
                affected_names.add(self._get_entity_name(entity))
                affected_names.update(self._get_entity_aliases(entity))

            # Also include new entity names (in case they changed)
            affected_names.add(self._get_entity_name(new_entity))
            affected_names.update(self._get_entity_aliases(new_entity))

            # Remove empty strings
            affected_names.discard("")

            return await self._invalidate_names(affected_names)

    async def on_entity_delete(self, entity: Entity) -> InvalidationResult:
        """
        Handle cache invalidation on entity delete.

        Invalidates all names associated with the deleted entity.

        Args:
            entity: Entity being deleted

        Returns:
            InvalidationResult with details
        """
        async with self._lock:
            affected_names: Set[str] = set()

            # Collect all names from entity
            affected_names.add(self._get_entity_name(entity))
            affected_names.update(self._get_entity_aliases(entity))

            # Remove empty strings
            affected_names.discard("")

            return await self._invalidate_names(affected_names)

    async def on_alias_update(
        self,
        entity_id: str,
        old_aliases: List[str],
        new_aliases: List[str],
    ) -> InvalidationResult:
        """
        Handle cache invalidation on alias update.

        Invalidates embeddings for both old and new aliases.

        Args:
            entity_id: Entity whose aliases changed
            old_aliases: Previous aliases
            new_aliases: New aliases

        Returns:
            InvalidationResult with details
        """
        async with self._lock:
            affected_names: Set[str] = set(old_aliases) | set(new_aliases)
            affected_names.discard("")

            return await self._invalidate_names(affected_names)

    async def invalidate_for_names(
        self, names: List[str]
    ) -> InvalidationResult:
        """
        Directly invalidate cache entries for given names.

        Args:
            names: Names to invalidate

        Returns:
            InvalidationResult with details
        """
        async with self._lock:
            affected_names = set(names)
            affected_names.discard("")
            return await self._invalidate_names(affected_names)

    async def _invalidate_names(
        self, names: Set[str]
    ) -> InvalidationResult:
        """
        Internal method to invalidate cache entries for names.

        Args:
            names: Set of names to invalidate

        Returns:
            InvalidationResult with details
        """
        if not names:
            return InvalidationResult(
                affected_names=set(),
                alias_entries_removed=0,
                embeddings_invalidated=0,
                success=True,
            )

        alias_removed = 0
        embeddings_invalidated = 0

        try:
            # Invalidate alias index entries
            # Each remove_alias() call removes exactly one alias entry (if it exists)
            # and returns True on success, so we count each successful removal
            if self._alias_index is not None:
                for name in names:
                    removed = await self._alias_index.remove_alias(name)
                    if removed:
                        alias_removed += 1

            # Invalidate embedding cache
            cache = self._get_embedding_cache()
            if cache is not None:
                embeddings_invalidated = cache.invalidate_many(list(names))

            # Update statistics
            self._invalidation_count += 1
            self._names_invalidated += len(names)

            logger.debug(
                f"Cache invalidation: {len(names)} names, "
                f"{alias_removed} alias entries removed, "
                f"{embeddings_invalidated} embeddings invalidated"
            )

            return InvalidationResult(
                affected_names=names,
                alias_entries_removed=alias_removed,
                embeddings_invalidated=embeddings_invalidated,
                success=True,
            )

        except Exception as e:
            logger.error(f"Cache invalidation failed: {e}")
            return InvalidationResult(
                affected_names=names,
                alias_entries_removed=0,
                embeddings_invalidated=0,
                success=False,
                error=str(e),
            )

    def verify_invariant(self, operation: str, affected_names: Set[str]) -> bool:
        """
        Verify the cache coordination invariant.

        Checks that all affected names have been properly invalidated
        from the embedding cache.

        Args:
            operation: Name of the operation for logging
            affected_names: Names that should have been invalidated

        Returns:
            True if invariant holds, False otherwise
        """
        cache = self._get_embedding_cache()
        if cache is None:
            # No cache to check
            return True

        # Check if any affected names are still in cache
        still_cached = []
        for name in affected_names:
            if cache.contains(name):
                still_cached.append(name)

        if still_cached:
            logger.error(
                f"INVARIANT VIOLATION in {operation}: "
                f"{len(still_cached)} names still in embedding cache: {still_cached[:5]}"
            )
            return False

        return True

    def get_stats(self) -> dict:
        """Get coordination statistics."""
        return {
            "invalidation_count": self._invalidation_count,
            "names_invalidated": self._names_invalidated,
            "has_alias_index": self._alias_index is not None,
            "has_semantic_matcher": self._semantic_matcher is not None,
            "has_embedding_cache": self._get_embedding_cache() is not None,
        }

    def reset_stats(self) -> None:
        """Reset coordination statistics."""
        self._invalidation_count = 0
        self._names_invalidated = 0

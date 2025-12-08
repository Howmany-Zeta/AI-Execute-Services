"""
Alias-Based Matching

Provides O(1) alias lookup for entity matching using the AliasIndex.
Supports alias propagation during entity merge operations.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.application.knowledge_graph.fusion.alias_index import (
    AliasIndex,
    AliasEntry,
    MatchType,
)

logger = logging.getLogger(__name__)


@dataclass
class AliasMatchResult:
    """Result of alias-based entity lookup"""
    entity_id: str
    matched_alias: str
    match_type: MatchType
    confidence: float


class AliasMatcher:
    """
    Alias-based entity matching with O(1) lookup.
    
    Uses AliasIndex for fast alias lookups and supports alias propagation
    during entity merge operations.
    
    Entity `_known_aliases` Property:
    Entities can define known aliases in their properties:
    ```python
    entity = Entity(
        id="person_123",
        entity_type="Person",
        properties={
            "name": "Albert Einstein",
            "_known_aliases": ["A. Einstein", "Einstein", "Albert"]
        }
    )
    ```
    
    Example:
        ```python
        matcher = AliasMatcher()
        
        # Initialize index from entities
        await matcher.build_index(entities)
        
        # O(1) lookup
        match = await matcher.lookup("A. Einstein")
        if match:
            print(f"Found: {match.entity_id}")
        
        # Alias propagation on merge
        await matcher.propagate_aliases(
            source_entity_id="person_456",
            target_entity_id="person_123"
        )
        ```
    """

    def __init__(self, alias_index: Optional[AliasIndex] = None):
        """
        Initialize AliasMatcher.
        
        Args:
            alias_index: Optional AliasIndex instance (creates new one if not provided)
        """
        self._index = alias_index or AliasIndex()

    @property
    def alias_index(self) -> AliasIndex:
        """Get the underlying AliasIndex"""
        return self._index

    async def build_index(self, entities: List[Entity]) -> int:
        """
        Build alias index from a list of entities.

        Extracts aliases from:
        1. Entity name (properties["name"])
        2. Known aliases (properties["_known_aliases"])
        3. Historical aliases (properties["_aliases"])

        Args:
            entities: List of entities to index

        Returns:
            Number of aliases indexed
        """
        total_count = 0

        for entity in entities:
            entity_aliases = self._extract_aliases(entity)
            for alias in entity_aliases:
                await self._index.add_alias(
                    alias=alias.lower(),
                    entity_id=entity.id,
                    match_type=MatchType.ALIAS,
                )
                total_count += 1

        logger.info(f"Built alias index with {total_count} aliases from {len(entities)} entities")
        return total_count

    def _extract_aliases(self, entity: Entity) -> Set[str]:
        """
        Extract all aliases from an entity.
        
        Sources:
        1. Entity name
        2. _known_aliases property
        3. _aliases property (from previous merges)
        
        Args:
            entity: Entity to extract aliases from
            
        Returns:
            Set of alias strings
        """
        aliases = set()
        
        # Get main name
        name = entity.properties.get("name") or entity.properties.get("title") or ""
        if name:
            aliases.add(name)
        
        # Get known aliases
        known_aliases = entity.properties.get("_known_aliases", [])
        if isinstance(known_aliases, list):
            aliases.update(known_aliases)
        
        # Get historical aliases (from merges)
        historical_aliases = entity.properties.get("_aliases", [])
        if isinstance(historical_aliases, list):
            aliases.update(historical_aliases)
        
        return aliases

    async def lookup(self, name: str) -> Optional[AliasMatchResult]:
        """
        Look up an entity by alias.

        O(1) lookup via AliasIndex.

        Args:
            name: Name or alias to look up

        Returns:
            AliasMatchResult if found, None otherwise
        """
        entry = await self._index.lookup(name)
        if entry:
            return AliasMatchResult(
                entity_id=entry.entity_id,
                matched_alias=name.lower(),  # The alias is the key we looked up
                match_type=entry.match_type,
                confidence=0.98,  # Default confidence for alias match
            )
        return None

    async def add_entity(self, entity: Entity) -> int:
        """
        Add entity aliases to the index.

        Args:
            entity: Entity to add

        Returns:
            Number of aliases added
        """
        aliases = self._extract_aliases(entity)
        count = 0

        for alias in aliases:
            await self._index.add_alias(
                alias=alias.lower(),
                entity_id=entity.id,
                match_type=MatchType.ALIAS,
            )
            count += 1

        return count

    async def remove_entity(self, entity_id: str) -> int:
        """
        Remove all aliases for an entity from the index.

        Args:
            entity_id: Entity ID to remove

        Returns:
            Number of aliases removed
        """
        return await self._index.remove_entity_aliases(entity_id)

    async def propagate_aliases(
        self,
        source_entity_id: str,
        target_entity_id: str,
    ) -> int:
        """
        Propagate aliases from source entity to target entity during merge.

        Used when merging duplicate entities:
        1. Get all aliases pointing to source entity
        2. Update them to point to target entity

        This is an atomic operation using transactions.

        Args:
            source_entity_id: Entity being merged (will be deleted)
            target_entity_id: Entity receiving the merge

        Returns:
            Number of aliases propagated
        """
        # Get all aliases for source entity (list of alias strings)
        source_aliases = await self._index.get_entity_aliases(source_entity_id)

        if not source_aliases:
            return 0

        # Use transaction for atomic update
        async with self._index.transaction() as tx:
            # Remove aliases from source using transaction context
            for alias in source_aliases:
                await tx.delete(alias)

            # Add aliases to target using transaction context
            for alias in source_aliases:
                entry = AliasEntry(
                    entity_id=target_entity_id,
                    match_type=MatchType.ALIAS,
                )
                await tx.set(alias, entry)

        logger.info(
            f"Propagated {len(source_aliases)} aliases from {source_entity_id} to {target_entity_id}"
        )
        return len(source_aliases)

    async def find_matching_entity(
        self,
        candidate_names: List[str],
    ) -> Optional[AliasMatchResult]:
        """
        Find an entity matching any of the candidate names.

        Tries each candidate name in order and returns the first match.

        Args:
            candidate_names: List of names to try

        Returns:
            AliasMatchResult if any name matches, None otherwise
        """
        for name in candidate_names:
            match = await self.lookup(name)
            if match:
                return match
        return None

    async def get_entity_aliases(self, entity_id: str) -> List[str]:
        """
        Get all aliases for an entity.

        Args:
            entity_id: Entity ID

        Returns:
            List of alias strings
        """
        # get_entity_aliases already returns List[str]
        return await self._index.get_entity_aliases(entity_id)

    async def size(self) -> int:
        """Get number of aliases in the index"""
        return await self._index.size()


def get_known_aliases(entity: Entity) -> List[str]:
    """
    Get known aliases from an entity's properties.

    Helper function to access the _known_aliases property.

    Args:
        entity: Entity to get aliases from

    Returns:
        List of known aliases (empty list if none)
    """
    return entity.properties.get("_known_aliases", [])


def set_known_aliases(entity: Entity, aliases: List[str]) -> None:
    """
    Set known aliases on an entity.

    Helper function to set the _known_aliases property.

    Args:
        entity: Entity to update
        aliases: List of aliases to set
    """
    entity.properties["_known_aliases"] = aliases


def add_known_alias(entity: Entity, alias: str) -> None:
    """
    Add a known alias to an entity.

    Args:
        entity: Entity to update
        alias: Alias to add
    """
    aliases = entity.properties.get("_known_aliases", [])
    if alias not in aliases:
        aliases.append(alias)
    entity.properties["_known_aliases"] = aliases


def merge_aliases(target: Entity, source: Entity) -> List[str]:
    """
    Merge aliases from source entity into target entity.

    Used during entity merge operations. Combines:
    - Source entity name
    - Source _known_aliases
    - Source _aliases

    Into target's _known_aliases (avoiding duplicates).

    Args:
        target: Entity receiving aliases
        source: Entity providing aliases

    Returns:
        List of newly added aliases
    """
    # Get existing target aliases
    target_aliases = set(get_known_aliases(target))
    # Normalize to lowercase for case-insensitive comparison
    target_aliases_normalized = {a.lower() for a in target_aliases}
    target_name = target.properties.get("name", "").lower()

    # Collect source aliases
    source_name = source.properties.get("name", "")
    source_known = source.properties.get("_known_aliases", [])
    source_historical = source.properties.get("_aliases", [])

    # Validate that source_known and source_historical are lists
    if not isinstance(source_known, list):
        source_known = []
    if not isinstance(source_historical, list):
        source_historical = []

    # Find new aliases to add
    new_aliases = []

    for alias in [source_name] + source_known + source_historical:
        if alias:
            alias_lower = alias.lower()
            # Case-insensitive comparison: check normalized versions
            if alias_lower != target_name and alias_lower not in target_aliases_normalized:
                target_aliases.add(alias)
                target_aliases_normalized.add(alias_lower)
                new_aliases.append(alias)

    # Update target
    set_known_aliases(target, list(target_aliases))

    return new_aliases


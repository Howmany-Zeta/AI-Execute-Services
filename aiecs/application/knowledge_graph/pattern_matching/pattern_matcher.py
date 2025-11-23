"""
Pattern Matching Engine

Implements graph pattern matching for custom query execution.

Phase: 3.3 - Full Custom Query Execution
Version: 1.0
"""

from typing import List, Dict, Any, Optional
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern
from aiecs.infrastructure.graph_storage.base import GraphStore


class PatternMatch:
    """
    Represents a single pattern match result

    Attributes:
        entities: Matched entities
        relations: Matched relations
        bindings: Variable bindings (if pattern uses variables)
        score: Match score (0.0-1.0)
    """

    def __init__(
        self,
        entities: List[Entity],
        relations: List[Relation],
        bindings: Optional[Dict[str, Any]] = None,
        score: float = 1.0,
    ):
        self.entities = entities
        self.relations = relations
        self.bindings = bindings or {}
        self.score = score

    def __repr__(self) -> str:
        return f"PatternMatch(entities={len(self.entities)}, relations={len(self.relations)}, score={self.score})"


class PatternMatcher:
    """
    Graph Pattern Matching Engine

    Executes pattern matching queries against a graph store.
    Supports:
    - Single pattern matching
    - Multiple pattern matching (AND semantics)
    - Optional pattern matching
    - Cycle detection and handling
    - Result projection and aggregation
    """

    def __init__(self, graph_store: GraphStore):
        """
        Initialize pattern matcher

        Args:
            graph_store: Graph storage backend
        """
        self.graph_store = graph_store

    async def match_pattern(
        self,
        pattern: PathPattern,
        start_entity_id: Optional[str] = None,
        max_matches: int = 100,
    ) -> List[PatternMatch]:
        """
        Match a single pattern in the graph

        Args:
            pattern: Pattern to match
            start_entity_id: Optional starting entity ID
            max_matches: Maximum number of matches to return

        Returns:
            List of pattern matches
        """
        matches = []

        if start_entity_id:
            # Start from specific entity
            start_entity = await self.graph_store.get_entity(start_entity_id)
            if not start_entity:
                return []

            # Find paths matching the pattern
            paths = await self._find_matching_paths(start_entity, pattern, max_matches)

            for path in paths:
                match = PatternMatch(entities=path.nodes, relations=path.edges, score=1.0)
                matches.append(match)
        else:
            # Find all entities matching the pattern
            # This is more expensive - iterate through all entities
            all_entities = await self._get_all_entities(pattern.entity_types)

            for entity in all_entities[:max_matches]:
                paths = await self._find_matching_paths(entity, pattern, max_matches=1)

                if paths:
                    match = PatternMatch(
                        entities=paths[0].nodes,
                        relations=paths[0].edges,
                        score=1.0,
                    )
                    matches.append(match)

                    if len(matches) >= max_matches:
                        break

        return matches

    async def match_multiple_patterns(
        self,
        patterns: List[PathPattern],
        start_entity_id: Optional[str] = None,
        max_matches: int = 100,
    ) -> List[PatternMatch]:
        """
        Match multiple patterns (AND semantics)

        All patterns must match for a result to be included.

        Args:
            patterns: List of patterns to match
            start_entity_id: Optional starting entity ID
            max_matches: Maximum number of matches to return

        Returns:
            List of pattern matches where all patterns matched
        """
        if not patterns:
            return []

        # Match first pattern
        first_matches = await self.match_pattern(patterns[0], start_entity_id, max_matches)

        if len(patterns) == 1:
            return first_matches

        # Filter matches that also match remaining patterns
        combined_matches = []

        for match in first_matches:
            # Check if remaining patterns match
            all_match = True
            combined_entities = list(match.entities)
            combined_relations = list(match.relations)

            for pattern in patterns[1:]:
                # Try to match pattern starting from any entity in current
                # match
                pattern_matched = False

                for entity in match.entities:
                    sub_matches = await self.match_pattern(pattern, entity.id, max_matches=1)

                    if sub_matches:
                        # Add new entities and relations
                        for sub_match in sub_matches:
                            combined_entities.extend(sub_match.entities)
                            combined_relations.extend(sub_match.relations)
                        pattern_matched = True
                        break

                if not pattern_matched:
                    all_match = False
                    break

            if all_match:
                combined_match = PatternMatch(
                    entities=combined_entities,
                    relations=combined_relations,
                    score=match.score,
                )
                combined_matches.append(combined_match)

        return combined_matches[:max_matches]

    async def match_optional_patterns(
        self,
        required_patterns: List[PathPattern],
        optional_patterns: List[PathPattern],
        start_entity_id: Optional[str] = None,
        max_matches: int = 100,
    ) -> List[PatternMatch]:
        """
        Match required patterns with optional patterns

        Required patterns must match. Optional patterns are included if they match.

        Args:
            required_patterns: Patterns that must match
            optional_patterns: Patterns that may or may not match
            start_entity_id: Optional starting entity ID
            max_matches: Maximum number of matches to return

        Returns:
            List of pattern matches
        """
        # Match required patterns first
        required_matches = await self.match_multiple_patterns(required_patterns, start_entity_id, max_matches)

        if not optional_patterns:
            return required_matches

        # Try to extend with optional patterns
        extended_matches = []

        for match in required_matches:
            combined_entities = list(match.entities)
            combined_relations = list(match.relations)

            # Try to match each optional pattern
            for pattern in optional_patterns:
                for entity in match.entities:
                    sub_matches = await self.match_pattern(pattern, entity.id, max_matches=1)

                    if sub_matches:
                        # Add optional entities and relations
                        for sub_match in sub_matches:
                            combined_entities.extend(sub_match.entities)
                            combined_relations.extend(sub_match.relations)
                        break

            extended_match = PatternMatch(
                entities=combined_entities,
                relations=combined_relations,
                score=match.score,
            )
            extended_matches.append(extended_match)

        return extended_matches

    async def _find_matching_paths(
        self,
        start_entity: Entity,
        pattern: PathPattern,
        max_matches: int = 100,
    ) -> List[Path]:
        """
        Find paths matching a pattern starting from an entity

        Args:
            start_entity: Starting entity
            pattern: Pattern to match
            max_matches: Maximum number of paths to return

        Returns:
            List of matching paths
        """
        # Use graph store's traverse method with pattern constraints
        paths = await self.graph_store.traverse(
            start_entity.id,
            relation_type=(pattern.relation_types[0] if pattern.relation_types else None),
            max_depth=pattern.max_depth,
            max_results=max_matches,
        )

        # Filter paths based on pattern constraints
        matching_paths = []

        for path in paths:
            if self._path_matches_pattern(path, pattern):
                matching_paths.append(path)

        return matching_paths

    def _path_matches_pattern(self, path: Path, pattern: PathPattern) -> bool:
        """
        Check if a path matches a pattern

        Args:
            path: Path to check
            pattern: Pattern to match against

        Returns:
            True if path matches pattern
        """
        # Check path length
        if len(path.edges) < pattern.min_path_length:
            return False

        if len(path.edges) > pattern.max_depth:
            return False

        # Check entity types
        if pattern.entity_types:
            for entity in path.nodes:
                if entity.entity_type not in pattern.entity_types:
                    return False

        # Check relation types
        if pattern.relation_types:
            for relation in path.edges:
                if relation.relation_type not in pattern.relation_types:
                    return False

        # Check required relation sequence
        if pattern.required_relation_sequence:
            if len(path.edges) != len(pattern.required_relation_sequence):
                return False

            for i, relation in enumerate(path.edges):
                if relation.relation_type != pattern.required_relation_sequence[i]:
                    return False

        # Check cycles
        if not pattern.allow_cycles:
            entity_ids = [entity.id for entity in path.nodes]
            if len(entity_ids) != len(set(entity_ids)):
                return False

        # Check excluded entities
        if pattern.excluded_entity_ids:
            for entity in path.nodes:
                if entity.id in pattern.excluded_entity_ids:
                    return False

        return True

    async def _get_all_entities(self, entity_types: Optional[List[str]] = None) -> List[Entity]:
        """
        Get all entities, optionally filtered by type

        Args:
            entity_types: Optional list of entity types to filter by

        Returns:
            List of entities
        """
        # This is a placeholder - actual implementation depends on graph store
        # For now, we'll return empty list and rely on start_entity_id
        # In a real implementation, this would query the graph store for all
        # entities
        return []

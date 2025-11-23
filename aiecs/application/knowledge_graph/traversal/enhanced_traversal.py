"""
Enhanced Graph Traversal

Provides advanced traversal capabilities with PathPattern support,
cycle detection, and sophisticated path filtering.
"""

from typing import List, Optional
from collections import deque
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.path_pattern import (
    PathPattern,
    TraversalDirection,
)
from aiecs.infrastructure.graph_storage.base import GraphStore


class EnhancedTraversal:
    """
    Enhanced Graph Traversal Service

    Provides advanced traversal capabilities beyond basic BFS:
    - PathPattern-based traversal
    - Cycle detection and handling
    - Depth-limited traversal with constraints
    - Path filtering by pattern

    Example:
        ```python
        traversal = EnhancedTraversal(graph_store)

        # Define pattern
        pattern = PathPattern(
            relation_types=["WORKS_FOR", "LOCATED_IN"],
            max_depth=2,
            allow_cycles=False
        )

        # Traverse with pattern
        paths = await traversal.traverse_with_pattern(
            start_entity_id="person_1",
            pattern=pattern,
            max_results=10
        )
        ```
    """

    def __init__(self, graph_store: GraphStore):
        """
        Initialize enhanced traversal service

        Args:
            graph_store: Graph storage backend to use
        """
        self.graph_store = graph_store

    async def traverse_with_pattern(
        self,
        start_entity_id: str,
        pattern: PathPattern,
        max_results: int = 100,
    ) -> List[Path]:
        """
        Traverse graph following a path pattern

        Args:
            start_entity_id: Starting entity ID
            pattern: Path pattern to follow
            max_results: Maximum number of paths to return

        Returns:
            List of paths matching the pattern
        """
        start_entity = await self.graph_store.get_entity(start_entity_id)
        if start_entity is None:
            return []

        # Check if start entity is allowed
        if not pattern.is_entity_allowed(start_entity.id, start_entity.entity_type):
            return []

        paths: List[Path] = []
        # visited_in_path: Set[str] = set() if not pattern.allow_cycles else
        # None  # Reserved for future use

        # BFS with pattern matching
        queue: deque = deque()
        queue.append(
            {
                "entity": start_entity,
                "path_entities": [start_entity],
                "path_edges": [],
                "depth": 0,
                "visited": ({start_entity.id} if not pattern.allow_cycles else set()),
            }
        )

        while queue and len(paths) < max_results:
            current = queue.popleft()
            current_entity = current["entity"]
            current_depth = current["depth"]
            path_entities = current["path_entities"]
            path_edges = current["path_edges"]
            visited_nodes = current["visited"]

            # Add path if it meets length requirements
            if pattern.is_valid_path_length(len(path_edges)):
                path = Path(nodes=path_entities, edges=path_edges)
                paths.append(path)

            # Continue traversal if not at max depth
            if not pattern.should_continue_traversal(current_depth):
                continue

            # Get neighbors based on pattern direction
            # pattern.direction is already a string due to use_enum_values=True
            direction_str = pattern.direction if isinstance(pattern.direction, str) else pattern.direction.value
            neighbors = await self.graph_store.get_neighbors(
                current_entity.id,
                relation_type=None,  # We'll filter by pattern
                direction=direction_str,
            )

            for neighbor in neighbors:
                # Check if entity is allowed
                if not pattern.is_entity_allowed(neighbor.id, neighbor.entity_type):
                    continue

                # Check for cycles
                if not pattern.allow_cycles and neighbor.id in visited_nodes:
                    continue

                # Get the relation between current and neighbor
                # We need to find the actual relation
                relation = await self._find_relation(current_entity.id, neighbor.id, pattern.direction)

                if relation is None:
                    continue

                # Check if relation is allowed at this depth
                if not pattern.is_relation_allowed(relation.relation_type, current_depth):
                    continue

                # For incoming direction, we need to reverse the relation for path construction
                # because paths expect edges[i].source_id == nodes[i].id
                direction_str = pattern.direction if isinstance(pattern.direction, str) else pattern.direction.value
                if direction_str == "incoming":
                    # Reverse the relation: if we have e1->e2 and we're going from e2 to e1,
                    # the path needs e2->e1 (source=current, target=neighbor)
                    path_relation = Relation(
                        id=f"{relation.id}_reversed",
                        relation_type=relation.relation_type,
                        source_id=current_entity.id,
                        target_id=neighbor.id,
                        weight=relation.weight,
                    )
                else:
                    path_relation = relation

                # Create new path state
                new_path_entities = path_entities + [neighbor]
                new_path_edges = path_edges + [path_relation]
                new_visited = visited_nodes | {neighbor.id} if not pattern.allow_cycles else visited_nodes

                queue.append(
                    {
                        "entity": neighbor,
                        "path_entities": new_path_entities,
                        "path_edges": new_path_edges,
                        "depth": current_depth + 1,
                        "visited": new_visited,
                    }
                )

        return paths

    async def _find_relation(self, source_id: str, target_id: str, direction: TraversalDirection) -> Optional[Relation]:
        """
        Find the relation between two entities

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            direction: Traversal direction (can be enum or string)

        Returns:
            Relation if found, None otherwise
        """
        # Try to find the actual relation in the graph store
        # This works with both InMemoryGraphStore and SQLiteGraphStore

        # Handle both enum and string directions
        direction_str = direction if isinstance(direction, str) else direction.value
        direction_enum = TraversalDirection(direction_str) if isinstance(direction, str) else direction

        if direction_enum == TraversalDirection.OUTGOING or direction_enum == TraversalDirection.BOTH:
            # Look for outgoing relations from source
            neighbors = await self.graph_store.get_neighbors(source_id, relation_type=None, direction="outgoing")
            for neighbor in neighbors:
                if neighbor.id == target_id:
                    # Found the neighbor, now get the relation
                    # This is a workaround - ideally get_neighbors would return relations too
                    # For now, check if the store exposes relations
                    from aiecs.infrastructure.graph_storage.in_memory import (
                        InMemoryGraphStore,
                    )

                    if isinstance(self.graph_store, InMemoryGraphStore):
                        for rel in self.graph_store.relations.values():
                            if rel.source_id == source_id and rel.target_id == target_id:
                                return rel
                    else:
                        # For SQLite or other stores, try to get the relation
                        # This is a placeholder - real implementation would
                        # query the DB
                        return Relation(
                            id=f"rel_{source_id}_{target_id}",
                            relation_type="CONNECTED_TO",
                            source_id=source_id,
                            target_id=target_id,
                        )

        if direction_enum == TraversalDirection.INCOMING or direction_enum == TraversalDirection.BOTH:
            # Look for incoming relations to source (i.e., outgoing from
            # target)
            neighbors = await self.graph_store.get_neighbors(target_id, relation_type=None, direction="outgoing")
            for neighbor in neighbors:
                if neighbor.id == source_id:
                    from aiecs.infrastructure.graph_storage.in_memory import (
                        InMemoryGraphStore,
                    )

                    if isinstance(self.graph_store, InMemoryGraphStore):
                        for rel in self.graph_store.relations.values():
                            if rel.source_id == target_id and rel.target_id == source_id:
                                return rel
                    else:
                        return Relation(
                            id=f"rel_{target_id}_{source_id}",
                            relation_type="CONNECTED_TO",
                            source_id=target_id,
                            target_id=source_id,
                        )

        return None

    def detect_cycles(self, path: Path) -> bool:
        """
        Detect if a path contains cycles (repeated nodes)

        Args:
            path: Path to check

        Returns:
            True if path contains cycles
        """
        entity_ids = path.get_entity_ids()
        return len(entity_ids) != len(set(entity_ids))

    def filter_paths_without_cycles(self, paths: List[Path]) -> List[Path]:
        """
        Filter out paths that contain cycles

        Args:
            paths: List of paths to filter

        Returns:
            List of paths without cycles
        """
        return [path for path in paths if not self.detect_cycles(path)]

    async def find_all_paths_between(
        self,
        source_id: str,
        target_id: str,
        pattern: Optional[PathPattern] = None,
        max_paths: int = 10,
    ) -> List[Path]:
        """
        Find all paths between two entities matching a pattern

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            pattern: Optional path pattern to follow
            max_paths: Maximum number of paths to return

        Returns:
            List of paths from source to target
        """
        if pattern is None:
            pattern = PathPattern(max_depth=5, allow_cycles=False)

        # Traverse from source
        all_paths = await self.traverse_with_pattern(
            start_entity_id=source_id,
            pattern=pattern,
            max_results=max_paths * 10,  # Get more paths for filtering
        )

        # Filter paths that end at target
        target_paths = [path for path in all_paths if path.end_entity.id == target_id]

        return target_paths[:max_paths]

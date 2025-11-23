"""
PathPattern Domain Model

Represents a pattern for graph traversal specifications.
"""

from typing import List, Optional, Set
from pydantic import BaseModel, Field
from enum import Enum


class TraversalDirection(str, Enum):
    """Direction for graph traversal"""

    OUTGOING = "outgoing"
    INCOMING = "incoming"
    BOTH = "both"


class PathPattern(BaseModel):
    """
    Path Pattern for Graph Traversal

    Specifies constraints and preferences for graph traversal operations.
    Used to control how the graph is explored and which paths are valid.

    Attributes:
        relation_types: Optional list of allowed relation types
        entity_types: Optional list of allowed entity types
        direction: Traversal direction (outgoing, incoming, both)
        max_depth: Maximum path length
        allow_cycles: Whether to allow revisiting nodes
        required_relation_sequence: Optional sequence of relation types that must be followed

    Example:
        ```python
        # Find paths following WORKS_FOR -> LOCATED_IN pattern
        pattern = PathPattern(
            relation_types=["WORKS_FOR", "LOCATED_IN"],
            required_relation_sequence=["WORKS_FOR", "LOCATED_IN"],
            max_depth=2,
            allow_cycles=False
        )
        ```
    """

    relation_types: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed relation types (None = all types allowed)",
    )

    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Optional list of allowed entity types (None = all types allowed)",
    )

    direction: TraversalDirection = Field(
        default=TraversalDirection.OUTGOING,
        description="Direction for traversal",
    )

    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum path length (number of hops)",
    )

    allow_cycles: bool = Field(default=False, description="Whether to allow revisiting nodes (cycles)")

    required_relation_sequence: Optional[List[str]] = Field(
        default=None,
        description="Optional sequence of relation types that must be followed in order",
    )

    min_path_length: int = Field(default=1, ge=1, description="Minimum path length to return")

    excluded_entity_ids: Set[str] = Field(
        default_factory=set,
        description="Set of entity IDs to exclude from traversal",
    )

    def is_relation_allowed(self, relation_type: str, depth: int = 0) -> bool:
        """
        Check if a relation type is allowed at the current depth

        Args:
            relation_type: Relation type to check
            depth: Current depth in the traversal (0-indexed)

        Returns:
            True if the relation is allowed
        """
        # Check required sequence if specified
        if self.required_relation_sequence:
            if depth >= len(self.required_relation_sequence):
                return False
            return relation_type == self.required_relation_sequence[depth]

        # Check allowed types if specified
        if self.relation_types:
            return relation_type in self.relation_types

        # All types allowed if no constraints
        return True

    def is_entity_allowed(self, entity_id: str, entity_type: str) -> bool:
        """
        Check if an entity is allowed in the path

        Args:
            entity_id: Entity ID to check
            entity_type: Entity type to check

        Returns:
            True if the entity is allowed
        """
        # Check excluded entities
        if entity_id in self.excluded_entity_ids:
            return False

        # Check allowed types if specified
        if self.entity_types:
            return entity_type in self.entity_types

        # All entities allowed if no constraints
        return True

    def is_valid_path_length(self, length: int) -> bool:
        """
        Check if a path length is valid according to the pattern

        Args:
            length: Path length to check

        Returns:
            True if the length is valid
        """
        return self.min_path_length <= length <= self.max_depth

    def should_continue_traversal(self, depth: int) -> bool:
        """
        Check if traversal should continue at the current depth

        Args:
            depth: Current depth in the traversal

        Returns:
            True if traversal should continue
        """
        return depth < self.max_depth

    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        parts = [f"depth={self.max_depth}"]

        if self.relation_types:
            parts.append(f"relations={','.join(self.relation_types)}")

        if self.entity_types:
            parts.append(f"entities={','.join(self.entity_types)}")

        if self.required_relation_sequence:
            parts.append(f"sequence={' -> '.join(self.required_relation_sequence)}")

        if self.allow_cycles:
            parts.append("allow_cycles")

        return f"PathPattern({', '.join(parts)})"

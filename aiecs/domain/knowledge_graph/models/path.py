"""
Path Domain Model

Represents a path through the knowledge graph (sequence of entities and relations).
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class Path(BaseModel):
    """
    Knowledge Graph Path

    Represents a path through the knowledge graph as a sequence of entities
    connected by relations. Paths are results of graph traversal operations.

    Attributes:
        nodes: Sequence of entities in the path
        edges: Sequence of relations connecting the entities
        score: Optional relevance score for the path
        length: Number of hops in the path

    Example:
        ```python
        path = Path(
            nodes=[entity1, entity2, entity3],
            edges=[relation1_2, relation2_3],
            score=0.85
        )
        ```

    Invariants:
        - len(edges) == len(nodes) - 1 (for a valid path)
        - edges[i].source_id == nodes[i].id
        - edges[i].target_id == nodes[i+1].id
    """

    nodes: List[Entity] = Field(..., min_length=1, description="Sequence of entities in the path")

    edges: List[Relation] = Field(
        default_factory=list,
        description="Sequence of relations connecting entities",
    )

    score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Relevance score for the path (0.0-1.0)",
    )

    class Config:
        arbitrary_types_allowed = True

    @field_validator("edges")
    @classmethod
    def validate_path_structure(cls, v: List[Relation], info) -> List[Relation]:
        """Validate that edges match nodes structure"""
        nodes = info.data.get("nodes", [])
        if not nodes:
            return v

        # Check edge count
        if len(v) != len(nodes) - 1:
            if len(v) > 0:  # Only raise error if edges are provided
                raise ValueError(f"Number of edges ({len(v)}) must be len(nodes) - 1 ({len(nodes) - 1})")

        # Validate edge connectivity (if we have edges)
        for i, edge in enumerate(v):
            if i < len(nodes) - 1:
                expected_source = nodes[i].id
                expected_target = nodes[i + 1].id

                if edge.source_id != expected_source:
                    raise ValueError(f"Edge {i} source_id ({edge.source_id}) doesn't match " f"node {i} id ({expected_source})")

                if edge.target_id != expected_target:
                    raise ValueError(f"Edge {i} target_id ({edge.target_id}) doesn't match " f"node {i+1} id ({expected_target})")

        return v

    @property
    def length(self) -> int:
        """
        Get path length (number of hops)

        Returns:
            Number of edges in the path
        """
        return len(self.edges)

    @property
    def start_entity(self) -> Entity:
        """
        Get the starting entity of the path

        Returns:
            First entity in the path
        """
        return self.nodes[0]

    @property
    def end_entity(self) -> Entity:
        """
        Get the ending entity of the path

        Returns:
            Last entity in the path
        """
        return self.nodes[-1]

    def get_entity_ids(self) -> List[str]:
        """
        Get list of entity IDs in the path

        Returns:
            List of entity IDs
        """
        return [node.id for node in self.nodes]

    def get_relation_types(self) -> List[str]:
        """
        Get list of relation types in the path

        Returns:
            List of relation types
        """
        return [edge.relation_type for edge in self.edges]

    def contains_entity(self, entity_id: str) -> bool:
        """
        Check if path contains a specific entity

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity is in the path
        """
        return entity_id in self.get_entity_ids()

    def contains_relation_type(self, relation_type: str) -> bool:
        """
        Check if path contains a specific relation type

        Args:
            relation_type: Relation type to check

        Returns:
            True if relation type is in the path
        """
        return relation_type in self.get_relation_types()

    def __str__(self) -> str:
        if not self.edges:
            return f"Path({self.nodes[0]})"

        path_str = str(self.nodes[0].id)
        for edge, node in zip(self.edges, self.nodes[1:]):
            path_str += f" -[{edge.relation_type}]-> {node.id}"

        if self.score is not None:
            path_str += f" (score={self.score:.3f})"

        return f"Path({path_str})"

    def __repr__(self) -> str:
        return f"Path(length={self.length}, nodes={len(self.nodes)}, score={self.score})"

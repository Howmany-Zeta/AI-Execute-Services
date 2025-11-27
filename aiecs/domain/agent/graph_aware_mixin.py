"""
Graph-Aware Agent Mixin

Provides reusable knowledge graph functionality for agents.
Can be mixed into any agent class to add graph capabilities.
"""

import logging
from typing import Dict, List, Any, Optional, Set, TYPE_CHECKING

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path

if TYPE_CHECKING:
    from aiecs.infrastructure.graph_storage.protocols import GraphAwareAgentMixinProtocol
    from aiecs.infrastructure.graph_storage.base import GraphStore

logger = logging.getLogger(__name__)


class GraphAwareAgentMixin:
    """
    Mixin to add knowledge graph capabilities to any agent.

    Provides:
    - Graph store integration
    - Knowledge formatting utilities
    - Graph query helpers
    - Entity/relation utilities

    This mixin expects the class it's mixed into to implement `GraphAwareAgentMixinProtocol`,
    specifically the `graph_store` attribute.

    Usage:
        class MyAgent(BaseAIAgent, GraphAwareAgentMixin):
            def __init__(self, graph_store, ...):
                super().__init__(...)
                self.graph_store = graph_store
    """

    if TYPE_CHECKING:
        # Type hint for mypy: this mixin expects GraphAwareAgentMixinProtocol
        graph_store: Optional["GraphStore"]

    # ==================== Knowledge Formatting ====================

    def format_entity(self, entity: Entity, include_properties: bool = True) -> str:
        """
        Format a single entity as a readable string.

        Args:
            entity: Entity to format
            include_properties: Whether to include properties

        Returns:
            Formatted string

        Example:
            >>> entity = Entity(id="alice", entity_type="Person", properties={"name": "Alice"})
            >>> mixin.format_entity(entity)
            "Person: alice (name=Alice)"
        """
        parts = [f"{entity.entity_type}: {entity.id}"]

        if include_properties and entity.properties:
            props_str = ", ".join(f"{k}={v}" for k, v in entity.properties.items())
            parts.append(f"({props_str})")

        return " ".join(parts)

    def format_entities(self, entities: List[Entity], max_items: int = 10) -> str:
        """
        Format a list of entities as a readable string.

        Args:
            entities: List of entities to format
            max_items: Maximum number of entities to include

        Returns:
            Formatted string with one entity per line

        Example:
            >>> entities = [Entity(id="alice", entity_type="Person", ...), ...]
            >>> mixin.format_entities(entities)
            "- Person: alice (name=Alice)\n- Company: tech_corp (name=TechCorp)"
        """
        if not entities:
            return ""

        lines = []
        for entity in entities[:max_items]:
            lines.append(f"- {self.format_entity(entity)}")

        if len(entities) > max_items:
            lines.append(f"... and {len(entities) - max_items} more")

        return "\n".join(lines)

    def format_relation(self, relation: Relation, include_entities: bool = False) -> str:
        """
        Format a relation as a readable string.

        Args:
            relation: Relation to format
            include_entities: Whether to fetch and include entity details

        Returns:
            Formatted string

        Example:
            >>> relation = Relation(id="r1", source_id="alice", target_id="bob", relation_type="KNOWS")
            >>> mixin.format_relation(relation)
            "alice --[KNOWS]--> bob"
        """
        if include_entities and hasattr(self, "graph_store") and self.graph_store:
            # Fetch entity details (async, but this is a sync method)
            # In production, this would be async
            return f"{relation.source_id} --[{relation.relation_type}]--> {relation.target_id}"

        return f"{relation.source_id} --[{relation.relation_type}]--> {relation.target_id}"

    def format_path(self, path: Path, include_properties: bool = False) -> str:
        """
        Format a graph path as a readable string.

        Args:
            path: Path to format
            include_properties: Whether to include entity properties

        Returns:
            Formatted string showing the path

        Example:
            >>> path = Path(nodes=[e1, e2], edges=[r1], weight=1.0)
            >>> mixin.format_path(path)
            "alice --[KNOWS]--> bob --[WORKS_FOR]--> tech_corp"
        """
        if not path.nodes:
            return ""

        parts = []

        # Add first node
        parts.append(self.format_entity(path.nodes[0], include_properties))

        # Add edges and subsequent nodes
        for i, edge in enumerate(path.edges):
            parts.append(f"--[{edge.relation_type}]-->")
            if i + 1 < len(path.nodes):
                parts.append(self.format_entity(path.nodes[i + 1], include_properties))

        return " ".join(parts)

    def format_knowledge_summary(
        self,
        entities: List[Entity],
        relations: Optional[List[Relation]] = None,
        max_entities: int = 5,
        max_relations: int = 5,
    ) -> str:
        """
        Format a summary of knowledge (entities and relations).

        Args:
            entities: List of entities
            relations: Optional list of relations
            max_entities: Maximum entities to show
            max_relations: Maximum relations to show

        Returns:
            Formatted summary string
        """
        lines = []

        if entities:
            lines.append(f"Entities ({len(entities)}):")
            lines.append(self.format_entities(entities, max_items=max_entities))

        if relations:
            lines.append(f"\nRelations ({len(relations)}):")
            for rel in relations[:max_relations]:
                lines.append(f"  {self.format_relation(rel)}")
            if len(relations) > max_relations:
                lines.append(f"  ... and {len(relations) - max_relations} more")

        return "\n".join(lines)

    # ==================== Graph Query Utilities ====================

    async def find_entity_by_property(
        self,
        entity_type: Optional[str] = None,
        property_name: str = "name",
        property_value: Any = None,
        limit: int = 10,
    ) -> List[Entity]:
        """
        Find entities by property value.

        Args:
            entity_type: Optional filter by entity type
            property_name: Property name to search
            property_value: Property value to match
            limit: Maximum results

        Returns:
            List of matching entities

        Example:
            >>> entities = await mixin.find_entity_by_property(
            ...     entity_type="Person",
            ...     property_name="name",
            ...     property_value="Alice"
            ... )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return []

        # This is a simplified implementation
        # In production, would use proper graph query or filtering
        try:
            # For now, return empty - would need graph query support
            # This is a placeholder for future enhancement
            return []
        except Exception as e:
            logger.error(f"Error finding entity by property: {e}")
            return []

    async def get_entity_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
        limit: int = 10,
    ) -> List[Entity]:
        """
        Get neighboring entities for a given entity.

        Args:
            entity_id: Entity ID
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            limit: Maximum results

        Returns:
            List of neighboring entities

        Example:
            >>> neighbors = await mixin.get_entity_neighbors(
            ...     entity_id="alice",
            ...     relation_type="KNOWS",
            ...     direction="outgoing"
            ... )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return []

        try:
            neighbors = await self.graph_store.get_neighbors(
                entity_id=entity_id,
                relation_type=relation_type,
                direction=direction,
            )
            return neighbors[:limit]
        except Exception as e:
            logger.error(f"Error getting neighbors: {e}")
            return []

    async def find_paths_between(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 3,
        relation_types: Optional[List[str]] = None,
    ) -> List[Path]:
        """
        Find paths between two entities.

        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            max_depth: Maximum path depth
            relation_types: Optional filter by relation types

        Returns:
            List of paths

        Example:
            >>> paths = await mixin.find_paths_between(
            ...     source_id="alice",
            ...     target_id="tech_corp",
            ...     max_depth=2
            ... )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return []

        try:
            # Use graph store's find_paths method
            paths = await self.graph_store.find_paths(
                source_entity_id=source_id,
                target_entity_id=target_id,
                max_depth=max_depth,
                max_paths=10,
            )

            # Filter by relation types if specified
            if relation_types:
                filtered_paths = []
                for path in paths:
                    # Check if all edges match relation types
                    if all(edge.relation_type in relation_types for edge in path.edges):
                        filtered_paths.append(path)
                return filtered_paths

            return paths
        except Exception as e:
            logger.error(f"Error finding paths: {e}")
            return []

    async def get_entity_subgraph(
        self,
        entity_id: str,
        max_depth: int = 2,
        relation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get a subgraph centered around an entity.

        Args:
            entity_id: Center entity ID
            max_depth: Maximum depth for traversal
            relation_types: Optional filter by relation types

        Returns:
            Dictionary with 'entities' and 'relations' lists

        Example:
            >>> subgraph = await mixin.get_entity_subgraph(
            ...     entity_id="alice",
            ...     max_depth=2
            ... )
            >>> print(f"Entities: {len(subgraph['entities'])}")
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return {"entities": [], "relations": []}

        try:
            entities = []
            relations: List[Any] = []
            visited: Set[str] = {entity_id}

            # Get center entity
            center = await self.graph_store.get_entity(entity_id)
            if not center:
                return {"entities": [], "relations": []}

            entities.append(center)
            current_level = [entity_id]

            for depth in range(max_depth):
                next_level = []

                for e_id in current_level:
                    neighbors = await self.graph_store.get_neighbors(
                        entity_id=e_id,
                        relation_type=None,  # Get all relation types
                        direction="both",
                    )

                    for neighbor in neighbors:
                        if neighbor.id not in visited:
                            visited.add(neighbor.id)
                            entities.append(neighbor)
                            next_level.append(neighbor.id)

                    # Note: In a full implementation, we'd also collect relations
                    # This is simplified

                current_level = next_level
                if not current_level:
                    break

            return {
                "entities": [e.model_dump() for e in entities],
                "relations": relations,
            }
        except Exception as e:
            logger.error(f"Error getting subgraph: {e}")
            return {"entities": [], "relations": []}

    async def search_entities(
        self,
        query: Optional[str] = None,
        entity_types: Optional[List[str]] = None,
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Entity]:
        """
        Search for entities using vector search or filtering.

        Args:
            query: Optional search query (for vector search)
            entity_types: Optional filter by entity types
            limit: Maximum results
            threshold: Similarity threshold for vector search

        Returns:
            List of matching entities

        Example:
            >>> entities = await mixin.search_entities(
            ...     query="engineer at tech company",
            ...     entity_types=["Person"],
            ...     limit=5
            ... )
        """
        if not hasattr(self, "graph_store") or self.graph_store is None:
            logger.warning("GraphStore not available")
            return []

        try:
            # If query provided, try vector search
            if query:
                # Note: This would require embedding generation
                # For now, this is a placeholder
                # In production: generate embedding and use vector_search
                pass

            # For now, return empty
            # In production, would use vector_search or filtering
            return []
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []

    # ==================== Knowledge Context Utilities ====================

    def extract_entity_mentions(self, text: str) -> List[str]:
        """
        Extract potential entity mentions from text.

        Simple implementation - in production would use NER or more sophisticated methods.

        Args:
            text: Text to analyze

        Returns:
            List of potential entity IDs or names

        Example:
            >>> mentions = mixin.extract_entity_mentions("Alice works at TechCorp")
            >>> # Returns: ["Alice", "TechCorp"]
        """
        # Simple implementation - split by common delimiters
        # In production, would use NER or entity linking
        words = text.split()
        mentions = []

        # Look for capitalized words (potential entity names)
        for word in words:
            if word and word[0].isupper() and len(word) > 1:
                mentions.append(word.strip(".,!?;:"))

        return mentions

    def build_knowledge_context_prompt(
        self,
        entities: List[Entity],
        relations: Optional[List[Relation]] = None,
        max_length: int = 500,
    ) -> str:
        """
        Build a prompt section with knowledge context.

        Args:
            entities: List of entities to include
            relations: Optional list of relations
            max_length: Maximum length of formatted text

        Returns:
            Formatted prompt section

        Example:
            >>> prompt = mixin.build_knowledge_context_prompt(
            ...     entities=[alice, bob],
            ...     relations=[knows_rel]
            ... )
            >>> # Returns formatted string for inclusion in prompt
        """
        lines = ["RELEVANT KNOWLEDGE:"]

        # Add entities
        if entities:
            lines.append("\nEntities:")
            entity_text = self.format_entities(entities, max_items=5)
            lines.append(entity_text)

        # Add relations
        if relations:
            lines.append("\nRelations:")
            for rel in relations[:5]:
                lines.append(f"  {self.format_relation(rel)}")

        full_text = "\n".join(lines)

        # Truncate if too long
        if len(full_text) > max_length:
            full_text = full_text[:max_length] + "..."

        return full_text

    def validate_graph_store(self) -> bool:
        """
        Validate that graph store is available and initialized.

        Returns:
            True if graph store is available, False otherwise
        """
        if not hasattr(self, "graph_store"):
            return False

        if self.graph_store is None:
            return False

        # Could add more validation (e.g., ping the store)
        return True

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with graph statistics

        Example:
            >>> stats = mixin.get_graph_stats()
            >>> print(f"Entities: {stats['entity_count']}")
        """
        if not self.validate_graph_store():
            return {"available": False, "entity_count": 0, "relation_count": 0}

        try:
            # Use graph store's get_stats if available
            graph_store = getattr(self, "graph_store", None)  # type: ignore[attr-defined]
            if graph_store is not None and hasattr(graph_store, "get_stats"):
                stats = graph_store.get_stats()  # type: ignore[attr-defined]
                # Normalize stats format
                return {
                    "available": True,
                    "entity_count": stats.get("entities", stats.get("nodes", "unknown")),
                    "relation_count": stats.get("relations", stats.get("edges", "unknown")),
                    **stats,  # Include all original stats
                }

            # Otherwise return basic info
            return {
                "available": True,
                "entity_count": "unknown",
                "relation_count": "unknown",
            }
        except Exception as e:
            logger.error(f"Error getting graph stats: {e}")
            return {"available": False, "error": str(e)}

"""
Knowledge Fusion Orchestrator

High-level orchestrator for cross-document entity merging and knowledge fusion.
"""

from typing import List, Dict, Set, Tuple
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import EntityDeduplicator
from aiecs.application.knowledge_graph.fusion.entity_linker import EntityLinker


class KnowledgeFusion:
    """
    Orchestrate knowledge fusion across multiple documents

    After extracting entities and relations from multiple documents,
    this class performs cross-document fusion to:
    - Identify entities that appear in multiple documents
    - Merge duplicate entities across documents
    - Resolve conflicts in entity properties
    - Track provenance (which documents contributed to each entity)

    Example:
        ```python
        fusion = KnowledgeFusion(graph_store)

        # After processing multiple documents
        await fusion.fuse_cross_document_entities(
            similarity_threshold=0.9
        )

        print(f"Merged {fusion.entities_merged} entities across documents")
        ```
    """

    def __init__(
        self,
        graph_store: GraphStore,
        similarity_threshold: float = 0.90  # High threshold for cross-document fusion
    ):
        """
        Initialize knowledge fusion orchestrator

        Args:
            graph_store: Graph storage containing entities to fuse
            similarity_threshold: Minimum similarity for cross-document merging
        """
        self.graph_store = graph_store
        self.similarity_threshold = similarity_threshold
        self.entities_merged = 0
        self.conflicts_resolved = 0

    async def fuse_cross_document_entities(
        self,
        entity_types: List[str] = None
    ) -> Dict[str, int]:
        """
        Perform cross-document entity fusion

        Args:
            entity_types: Optional list of entity types to fuse (None = all types)

        Returns:
            Dictionary with fusion statistics
        """
        stats = {
            "entities_analyzed": 0,
            "entities_merged": 0,
            "conflicts_resolved": 0,
            "merge_groups": 0
        }

        # TODO: Implement full cross-document fusion
        # This would involve:
        # 1. Querying all entities of each type from graph
        # 2. Running similarity matching across all pairs
        # 3. Finding merge candidates
        # 4. Resolving property conflicts
        # 5. Updating graph with merged entities

        # For now, this is a placeholder that demonstrates the concept
        # In Phase 3 (SQLite) and Phase 6 (PostgreSQL), we'll implement
        # efficient queries for this operation

        return stats

    async def resolve_property_conflicts(
        self,
        entities: List[Entity]
    ) -> Entity:
        """
        Resolve conflicts when merging entities with different property values

        Strategies:
        - Prefer most recent value (if timestamps available)
        - Prefer most confident source
        - Prefer most complete value (non-empty over empty)
        - Keep all values as list (for truly conflicting data)

        Args:
            entities: List of entities to merge

        Returns:
            Merged entity with resolved conflicts
        """
        if not entities:
            raise ValueError("Cannot merge empty entity list")

        if len(entities) == 1:
            return entities[0]

        # Use first entity as base
        merged = entities[0]
        conflicting_properties = {}

        # Merge properties from all entities
        for entity in entities[1:]:
            for key, value in entity.properties.items():
                if key.startswith("_"):
                    # Skip internal properties
                    continue

                if key not in merged.properties:
                    # Property doesn't exist in merged, add it
                    merged.properties[key] = value
                elif merged.properties[key] != value:
                    # Conflict detected
                    if key not in conflicting_properties:
                        conflicting_properties[key] = [merged.properties[key]]
                    conflicting_properties[key].append(value)

        # Store conflicting values
        if conflicting_properties:
            merged.properties["_property_conflicts"] = conflicting_properties
            self.conflicts_resolved += len(conflicting_properties)

        # Merge provenance information
        provenances = []
        for entity in entities:
            prov = entity.properties.get("_provenance")
            if prov:
                provenances.append(prov)
        if provenances:
            merged.properties["_provenance_merged"] = provenances

        return merged

    async def track_entity_provenance(
        self,
        entity_id: str
    ) -> List[str]:
        """
        Get list of documents that contributed to an entity

        Args:
            entity_id: Entity ID

        Returns:
            List of document sources
        """
        entity = await self.graph_store.get_entity(entity_id)
        if not entity:
            return []

        sources = []

        # Check single provenance
        if "_provenance" in entity.properties:
            prov = entity.properties["_provenance"]
            if isinstance(prov, dict) and "source" in prov:
                sources.append(prov["source"])

        # Check merged provenances
        if "_provenance_merged" in entity.properties:
            merged_provs = entity.properties["_provenance_merged"]
            if isinstance(merged_provs, list):
                for prov in merged_provs:
                    if isinstance(prov, dict) and "source" in prov:
                        sources.append(prov["source"])

        return list(set(sources))  # Remove duplicates


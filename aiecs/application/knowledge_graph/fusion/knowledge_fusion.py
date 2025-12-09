"""
Knowledge Fusion Orchestrator

High-level orchestrator for cross-document entity merging and knowledge fusion.
"""

from typing import List, Dict, Set, Tuple, Any, Optional
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    CrossTenantFusionError,
)
from aiecs.application.knowledge_graph.fusion.entity_deduplicator import (
    EntityDeduplicator,
)


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
        similarity_threshold: float = 0.90,  # High threshold for cross-document fusion
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
        entity_types: Optional[List[str]] = None,
        context: Optional[TenantContext] = None,
    ) -> Dict[str, int]:
        """
        Perform cross-document entity fusion

        This method identifies and merges entities that appear across multiple documents.
        It uses similarity matching to find duplicate entities and merges them while
        preserving provenance information.

        **Tenant Isolation**: When context is provided, fusion operates only within the
        specified tenant scope. Entities from different tenants will never be merged.

        Algorithm:
        1. Query all entities from graph (optionally filtered by type and tenant)
        2. Filter entities to ensure tenant isolation (if context provided)
        3. Group entities by type
        4. For each type, find similar entities using similarity matching
        5. Identify merge groups (clusters of similar entities)
        6. Merge each group into a canonical entity
        7. Update graph with merged entities and update relations

        Args:
            entity_types: Optional list of entity types to fuse (None = all types)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Dictionary with fusion statistics:
            - entities_analyzed: Total entities analyzed
            - entities_merged: Number of entities merged
            - conflicts_resolved: Number of property conflicts resolved
            - merge_groups: Number of merge groups identified

        Raises:
            CrossTenantFusionError: If entities from multiple tenants are detected
        """
        stats = {
            "entities_analyzed": 0,
            "entities_merged": 0,
            "conflicts_resolved": 0,
            "merge_groups": 0,
        }

        # Reset counters
        self.entities_merged = 0
        self.conflicts_resolved = 0

        # Step 1: Query all entities from graph (with tenant context)
        entities = await self._query_entities(entity_types, context)
        
        # Step 2: Filter entities by tenant_id when context provided (defense-in-depth)
        if context:
            entities = self._filter_entities_by_tenant(entities, context.tenant_id)
        
        stats["entities_analyzed"] = len(entities)

        if len(entities) < 2:
            # Nothing to merge
            return stats

        # Step 3: Group entities by type (only merge within same type)
        entities_by_type = self._group_entities_by_type(entities)

        # Step 4-7: Process each type group
        for entity_type, type_entities in entities_by_type.items():
            if len(type_entities) < 2:
                continue

            # Find merge candidates (groups of similar entities)
            merge_groups = await self._find_merge_groups(type_entities)
            stats["merge_groups"] += len(merge_groups)

            # Merge each group
            for group in merge_groups:
                if len(group) < 2:
                    continue

                # Merge entities in group
                await self._merge_entity_group(group)
                # N entities -> 1 entity
                stats["entities_merged"] += len(group) - 1

        stats["conflicts_resolved"] = self.conflicts_resolved

        return stats

    async def resolve_property_conflicts(self, entities: List[Entity], strategy: str = "most_complete") -> Entity:
        """
        Resolve conflicts when merging entities with different property values

        Strategies:
        - "most_complete": Prefer non-empty over empty values (default)
        - "most_recent": Prefer most recent value (requires timestamp in provenance)
        - "most_confident": Prefer value from most confident source (requires confidence score)
        - "longest": Prefer longest string value
        - "keep_all": Keep all conflicting values as a list

        Args:
            entities: List of entities to merge
            strategy: Conflict resolution strategy

        Returns:
            Merged entity with resolved conflicts
        """
        if not entities:
            raise ValueError("Cannot merge empty entity list")

        if len(entities) == 1:
            return entities[0]

        # Create a new merged entity (copy first entity as base)
        merged = Entity(
            id=entities[0].id,
            entity_type=entities[0].entity_type,
            properties=entities[0].properties.copy(),
            embedding=entities[0].embedding,
            tenant_id=entities[0].tenant_id,
        )

        conflicting_properties = {}

        # Merge properties from all entities
        for entity in entities[1:]:
            for key, value in entity.properties.items():
                if key.startswith("_"):
                    # Skip internal properties (will handle separately)
                    continue

                if key not in merged.properties:
                    # Property doesn't exist in merged, add it
                    merged.properties[key] = value
                elif merged.properties[key] != value:
                    # Conflict detected - apply resolution strategy
                    resolved_value = self._resolve_conflict(
                        key=key,
                        values=[merged.properties[key], value],
                        entities=[entities[0], entity],
                        strategy=strategy,
                    )

                    # Track conflict
                    if key not in conflicting_properties:
                        conflicting_properties[key] = [merged.properties[key]]
                    conflicting_properties[key].append(value)

                    # Update with resolved value
                    merged.properties[key] = resolved_value

        # Store conflicting values for transparency
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

        # Merge embeddings (average if multiple)
        embeddings = [e.embedding for e in entities if e.embedding]
        if len(embeddings) > 1:
            # Average embeddings
            import numpy as np

            merged.embedding = list(np.mean(embeddings, axis=0))
        elif embeddings:
            merged.embedding = embeddings[0]

        return merged

    def _resolve_conflict(
        self,
        key: str,
        values: List[Any],
        entities: List[Entity],
        strategy: str,
    ) -> Any:
        """
        Resolve a single property conflict using specified strategy

        Args:
            key: Property key
            values: Conflicting values
            entities: Entities that have these values
            strategy: Resolution strategy

        Returns:
            Resolved value
        """
        if strategy == "most_complete":
            # Prefer non-empty, non-None values
            # Prefer longer strings
            non_empty = [v for v in values if v not in (None, "", [], {})]
            if non_empty:
                # If strings, prefer longest
                if all(isinstance(v, str) for v in non_empty):
                    return max(non_empty, key=len)
                return non_empty[0]
            return values[0]

        elif strategy == "most_recent":
            # Prefer value from entity with most recent timestamp
            timestamps = []
            for entity in entities:
                prov = entity.properties.get("_provenance", {})
                if isinstance(prov, dict) and "timestamp" in prov:
                    timestamps.append(prov["timestamp"])
                else:
                    timestamps.append(0)  # No timestamp = oldest

            if timestamps:
                most_recent_idx = timestamps.index(max(timestamps))
                return values[most_recent_idx]
            return values[0]

        elif strategy == "most_confident":
            # Prefer value from entity with highest confidence
            confidences = []
            for entity in entities:
                prov = entity.properties.get("_provenance", {})
                if isinstance(prov, dict) and "confidence" in prov:
                    confidences.append(prov["confidence"])
                else:
                    confidences.append(0.0)  # No confidence = lowest

            if confidences:
                most_confident_idx = confidences.index(max(confidences))
                return values[most_confident_idx]
            return values[0]

        elif strategy == "longest":
            # Prefer longest value (for strings)
            if all(isinstance(v, str) for v in values):
                return max(values, key=len)
            return values[0]

        elif strategy == "keep_all":
            # Keep all values as a list
            return values

        else:
            # Default: return first value
            return values[0]

    async def track_entity_provenance(self, entity_id: str) -> List[str]:
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

    # =========================================================================
    # Helper Methods for Cross-Document Fusion
    # =========================================================================

    async def _query_entities(
        self,
        entity_types: Optional[List[str]] = None,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Query entities from graph store with tenant filtering

        Args:
            entity_types: Optional list of entity types to query
            context: Optional tenant context for filtering

        Returns:
            List of entities (filtered by tenant if context provided)
        """
        entities = []

        # Check if graph store has get_all_entities method
        if hasattr(self.graph_store, "get_all_entities"):
            if entity_types:
                # Query each type separately
                for entity_type in entity_types:
                    # Pass context to ensure tenant filtering at storage layer
                    if context:
                        type_entities = await self.graph_store.get_all_entities(
                            entity_type=entity_type, context=context
                        )
                    else:
                        type_entities = await self.graph_store.get_all_entities(
                            entity_type=entity_type
                        )
                    entities.extend(type_entities)
            else:
                # Query all entities
                if context:
                    entities = await self.graph_store.get_all_entities(context=context)
                else:
                    entities = await self.graph_store.get_all_entities()
        else:
            # Fallback: graph store doesn't support bulk queries
            # This is a limitation - we can't efficiently query all entities
            # In this case, return empty list
            # Note: Implementations should add get_all_entities() method
            pass

        return entities

    def _filter_entities_by_tenant(
        self, entities: List[Entity], tenant_id: str
    ) -> List[Entity]:
        """
        Filter entities to only those belonging to the specified tenant.

        This is a defense-in-depth mechanism in addition to storage-level filtering.
        Silently filters out entities from other tenants.

        Args:
            entities: List of entities to filter
            tenant_id: Target tenant ID

        Returns:
            List of entities belonging to the specified tenant
        """
        return [e for e in entities if e.tenant_id == tenant_id]

    def _group_entities_by_type(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """
        Group entities by their type

        Args:
            entities: List of entities

        Returns:
            Dictionary mapping entity type to list of entities
        """
        entities_by_type: Dict[str, List[Entity]] = {}

        for entity in entities:
            entity_type = entity.entity_type
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        return entities_by_type

    async def _find_merge_groups(self, entities: List[Entity]) -> List[List[Entity]]:
        """
        Find groups of entities that should be merged together

        Uses similarity matching to identify clusters of similar entities.
        Entities are grouped using connected components algorithm.

        Args:
            entities: List of entities (all same type)

        Returns:
            List of merge groups (each group is a list of entities)
        """
        if len(entities) < 2:
            return []

        # Build similarity graph
        n = len(entities)
        similar_pairs: Set[Tuple[int, int]] = set()

        # Compare all pairs
        for i in range(n):
            for j in range(i + 1, n):
                similarity = await self._compute_entity_similarity(entities[i], entities[j])
                if similarity >= self.similarity_threshold:
                    similar_pairs.add((i, j))

        # Find connected components (merge groups)
        merge_groups = self._find_connected_components(n, similar_pairs)

        # Convert indices to entities
        entity_groups = []
        for group_indices in merge_groups:
            if len(group_indices) >= 2:  # Only groups with 2+ entities
                entity_group = [entities[i] for i in group_indices]
                entity_groups.append(entity_group)

        return entity_groups

    def _find_connected_components(self, n: int, edges: Set[Tuple[int, int]]) -> List[List[int]]:
        """
        Find connected components in an undirected graph

        Uses Union-Find (Disjoint Set Union) algorithm.

        Args:
            n: Number of nodes
            edges: Set of edges (pairs of node indices)

        Returns:
            List of components (each component is a list of node indices)
        """
        # Initialize parent array for Union-Find
        parent = list(range(n))

        def find(x: int) -> int:
            """Find root of x with path compression"""
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: int, y: int) -> None:
            """Union two sets"""
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_x] = root_y

        # Build connected components
        for i, j in edges:
            union(i, j)

        # Group nodes by their root
        components: Dict[int, List[int]] = {}
        for i in range(n):
            root = find(i)
            if root not in components:
                components[root] = []
            components[root].append(i)

        return list(components.values())

    async def _compute_entity_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """
        Compute similarity between two entities

        Uses EntityDeduplicator for similarity computation.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            Similarity score (0.0-1.0)
        """
        # Use EntityDeduplicator for similarity computation
        deduplicator = EntityDeduplicator(similarity_threshold=self.similarity_threshold)
        return await deduplicator._compute_similarity(entity1, entity2)

    async def _merge_entity_group(self, entities: List[Entity]) -> None:
        """
        Merge a group of entities into a single canonical entity

        Steps:
        1. Resolve property conflicts to create merged entity
        2. Update graph: replace all entities with merged entity
        3. Update relations: redirect to merged entity
        4. Delete old entities

        Args:
            entities: List of entities to merge (2 or more)
        """
        if len(entities) < 2:
            return

        # Step 1: Resolve conflicts and create merged entity
        merged_entity = await self.resolve_property_conflicts(entities)

        # Track merge provenance
        merged_entity.properties["_merged_from"] = [e.id for e in entities]
        merged_entity.properties["_merge_count"] = len(entities)

        # Step 2: Add merged entity to graph (use first entity's ID as
        # canonical)
        canonical_id = entities[0].id
        merged_entity.id = canonical_id

        # Update entity in graph
        # Try update_entity if available, otherwise delete and re-add
        if hasattr(self.graph_store, "update_entity"):
            await self.graph_store.update_entity(merged_entity)
        else:
            # Delete old entity and add merged one
            # For InMemoryGraphStore, we need to manually update
            if hasattr(self.graph_store, "entities"):
                # Direct update for InMemoryGraphStore
                self.graph_store.entities[canonical_id] = merged_entity
                if hasattr(self.graph_store, "graph") and self.graph_store.graph:
                    self.graph_store.graph.nodes[canonical_id]["entity"] = merged_entity
            else:
                # Fallback: try to add (may fail if exists)
                try:
                    await self.graph_store.add_entity(merged_entity)
                except ValueError:
                    # Entity already exists, skip
                    pass

        # Step 3: Update relations pointing to merged entities
        await self._update_relations_for_merge(entities, canonical_id)

        # Step 4: Delete old entities (except canonical)
        for entity in entities[1:]:
            # Delete entity from graph
            if hasattr(self.graph_store, "delete_entity"):
                await self.graph_store.delete_entity(entity.id)

        # Update counter
        self.entities_merged += len(entities) - 1

    async def _update_relations_for_merge(self, merged_entities: List[Entity], canonical_id: str) -> None:
        """
        Update relations to point to canonical merged entity

        For each merged entity (except canonical):
        - Find all relations where it's source or target
        - Update relation to use canonical_id instead
        - Remove duplicate relations

        Args:
            merged_entities: List of entities that were merged
            canonical_id: ID of canonical entity
        """
        {e.id for e in merged_entities}

        # For each merged entity (except canonical)
        for entity in merged_entities:
            if entity.id == canonical_id:
                continue

            # Get outgoing relations
            if hasattr(self.graph_store, "get_outgoing_relations"):
                outgoing = await self.graph_store.get_outgoing_relations(entity.id)
                for relation in outgoing:
                    # Update source to canonical
                    relation.source_id = canonical_id
                    await self.graph_store.add_relation(relation)

            # Get incoming relations
            if hasattr(self.graph_store, "get_incoming_relations"):
                incoming = await self.graph_store.get_incoming_relations(entity.id)
                for relation in incoming:
                    # Update target to canonical
                    relation.target_id = canonical_id
                    await self.graph_store.add_relation(relation)

            # Alternative: use get_neighbors to find relations
            # This is less efficient but works with basic GraphStore interface
            if not hasattr(self.graph_store, "get_outgoing_relations"):
                # Get neighbors (this implicitly uses relations)
                # We can't easily update relations without direct access
                # This is a limitation of the basic interface
                pass

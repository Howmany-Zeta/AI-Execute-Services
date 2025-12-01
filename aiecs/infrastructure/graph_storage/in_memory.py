"""
In-Memory Graph Store Implementation

Implements Tier 1 of GraphStore interface using networkx.
Tier 2 methods work automatically via default implementations.

This is ideal for:
- Development and testing
- Small graphs (< 100K nodes)
- Prototyping
- Scenarios where persistence is not required
"""

from typing import Any, List, Optional, Dict, Set
import networkx as nx  # type: ignore[import-untyped]
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.property_storage import (
    PropertyOptimizer,
    PropertyStorageConfig,
    PropertyIndex,
)


class InMemoryGraphStore(GraphStore):
    """
    In-Memory Graph Store using NetworkX

    **Implementation Strategy**:
    - Uses networkx.DiGraph for graph structure
    - Stores Entity objects as node attributes
    - Stores Relation objects as edge attributes
    - Implements ONLY Tier 1 methods
    - Tier 2 methods (traverse, find_paths, etc.) work automatically!

    **Features**:
    - Fast for small-medium graphs
    - No external dependencies
    - Full Python ecosystem integration
    - Rich graph algorithms from networkx

    **Limitations**:
    - Not persistent (lost on restart)
    - Limited by RAM
    - No concurrent access control
    - No vector search optimization

    Example:
        ```python
        store = InMemoryGraphStore()
        await store.initialize()

        # Add entities
        entity = Entity(id="person_1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        # Tier 2 methods work automatically
        paths = await store.traverse("person_1", max_depth=3)
        ```
    """

    def __init__(
        self,
        property_storage_config: Optional[PropertyStorageConfig] = None,
    ) -> None:
        """
        Initialize in-memory graph store

        Args:
            property_storage_config: Optional configuration for property storage optimization.
                                     Enables sparse storage, compression, and indexing.
        """
        self.graph: Optional[nx.DiGraph] = None
        self.entities: Dict[str, Entity] = {}
        self.relations: Dict[str, Relation] = {}
        self._initialized = False

        # Property storage optimization
        self._property_optimizer: Optional[PropertyOptimizer] = None
        if property_storage_config is not None:
            self._property_optimizer = PropertyOptimizer(property_storage_config)

    # =========================================================================
    # TIER 1 IMPLEMENTATION - Core CRUD Operations
    # =========================================================================

    async def initialize(self) -> None:
        """Initialize the in-memory graph"""
        if self._initialized:
            return

        self.graph = nx.DiGraph()
        self.entities = {}
        self.relations = {}
        self._initialized = True

    async def close(self) -> None:
        """Close and cleanup (nothing to do for in-memory)"""
        self.graph = None
        self.entities = {}
        self.relations = {}
        self._initialized = False

    async def add_entity(self, entity: Entity) -> None:
        """
        Add entity to graph

        Args:
            entity: Entity to add

        Raises:
            ValueError: If entity already exists
            RuntimeError: If store not initialized
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        if entity.id in self.entities:
            raise ValueError(f"Entity with ID '{entity.id}' already exists")

        # Apply property optimization if enabled
        if self._property_optimizer is not None:
            # Apply sparse storage (remove None values)
            entity.properties = self._property_optimizer.optimize_properties(entity.properties)
            # Index properties for fast lookup
            self._property_optimizer.index_entity(entity.id, entity.properties)

        # Add to networkx graph
        if self.graph is None:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")
        self.graph.add_node(entity.id, entity=entity)

        # Add to entity index
        self.entities[entity.id] = entity

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """
        Get entity by ID

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        if not self._initialized:
            return None

        return self.entities.get(entity_id)

    async def add_relation(self, relation: Relation) -> None:
        """
        Add relation to graph

        Args:
            relation: Relation to add

        Raises:
            ValueError: If relation already exists or entities don't exist
            RuntimeError: If store not initialized
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        if relation.id in self.relations:
            raise ValueError(f"Relation with ID '{relation.id}' already exists")

        # Validate entities exist
        if relation.source_id not in self.entities:
            raise ValueError(f"Source entity '{relation.source_id}' not found")
        if relation.target_id not in self.entities:
            raise ValueError(f"Target entity '{relation.target_id}' not found")

        # Add to networkx graph
        if self.graph is None:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")
        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            relation=relation,
        )

        # Add to relation index
        self.relations[relation.id] = relation

    async def get_relation(self, relation_id: str) -> Optional[Relation]:
        """
        Get relation by ID

        Args:
            relation_id: Relation ID

        Returns:
            Relation if found, None otherwise
        """
        if not self._initialized:
            return None

        return self.relations.get(relation_id)

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[Entity]:
        """
        Get neighboring entities

        Args:
            entity_id: Entity ID to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of neighboring entities
        """
        if not self._initialized or self.graph is None or entity_id not in self.graph:
            return []

        neighbors = []

        # Get outgoing neighbors
        if direction in ("outgoing", "both"):
            for target_id in self.graph.successors(entity_id):
                # Check relation type filter
                if relation_type:
                    edge_data = self.graph.get_edge_data(entity_id, target_id)
                    if edge_data:
                        relation = edge_data.get("relation")
                        if relation and relation.relation_type == relation_type:
                            if target_id in self.entities:
                                neighbors.append(self.entities[target_id])
                else:
                    if target_id in self.entities:
                        neighbors.append(self.entities[target_id])

        # Get incoming neighbors
        if direction in ("incoming", "both"):
            for source_id in self.graph.predecessors(entity_id):
                # Check relation type filter
                if relation_type:
                    edge_data = self.graph.get_edge_data(source_id, entity_id)
                    if edge_data:
                        relation = edge_data.get("relation")
                        if relation and relation.relation_type == relation_type:
                            if source_id in self.entities:
                                neighbors.append(self.entities[source_id])
                else:
                    if source_id in self.entities:
                        neighbors.append(self.entities[source_id])

        return neighbors

    def get_outgoing_relations(self, entity_id: str) -> List[Relation]:
        """
        Get all outgoing relations for an entity (synchronous method for query optimizer).

        Args:
            entity_id: Entity ID to get outgoing relations for

        Returns:
            List of outgoing Relation objects
        """
        if not self._initialized or self.graph is None or entity_id not in self.graph:
            return []

        relations = []
        for target_id in self.graph.successors(entity_id):
            edge_data = self.graph.get_edge_data(entity_id, target_id)
            if edge_data:
                relation = edge_data.get("relation")
                if relation:
                    relations.append(relation)

        return relations

    def get_incoming_relations(self, entity_id: str) -> List[Relation]:
        """
        Get all incoming relations for an entity (synchronous method for query optimizer).

        Args:
            entity_id: Entity ID to get incoming relations for

        Returns:
            List of incoming Relation objects
        """
        if not self._initialized or self.graph is None or entity_id not in self.graph:
            return []

        relations = []
        for source_id in self.graph.predecessors(entity_id):
            edge_data = self.graph.get_edge_data(source_id, entity_id)
            if edge_data:
                relation = edge_data.get("relation")
                if relation:
                    relations.append(relation)

        return relations

    async def get_all_entities(self, entity_type: Optional[str] = None, limit: Optional[int] = None) -> List[Entity]:
        """
        Get all entities, optionally filtered by type

        Args:
            entity_type: Optional filter by entity type
            limit: Optional limit on number of entities

        Returns:
            List of entities
        """
        if not self._initialized:
            return []

        entities = list(self.entities.values())

        # Filter by entity type if specified
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        # Apply limit if specified
        if limit:
            entities = entities[:limit]

        return entities

    # =========================================================================
    # BULK OPERATIONS - Optimized implementations
    # =========================================================================

    async def add_entities_bulk(self, entities: List[Entity]) -> int:
        """
        Add multiple entities in bulk (optimized).

        Bypasses individual add_entity() calls for better performance.

        Args:
            entities: List of entities to add

        Returns:
            Number of entities successfully added
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        added = 0
        for entity in entities:
            if entity.id in self.entities:
                continue  # Skip existing entities

            # Apply property optimization if enabled
            if self._property_optimizer is not None:
                entity.properties = self._property_optimizer.optimize_properties(entity.properties)
                self._property_optimizer.index_entity(entity.id, entity.properties)

            # Add to graph and index
            self.graph.add_node(entity.id, entity=entity)
            self.entities[entity.id] = entity
            added += 1

        return added

    async def add_relations_bulk(self, relations: List[Relation]) -> int:
        """
        Add multiple relations in bulk (optimized).

        Bypasses individual add_relation() calls for better performance.

        Args:
            relations: List of relations to add

        Returns:
            Number of relations successfully added
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        added = 0
        for relation in relations:
            if relation.id in self.relations:
                continue  # Skip existing relations

            # Validate entities exist
            if relation.source_id not in self.entities:
                continue
            if relation.target_id not in self.entities:
                continue

            # Add edge
            self.graph.add_edge(
                relation.source_id,
                relation.target_id,
                key=relation.id,
                relation=relation,
            )
            self.relations[relation.id] = relation
            added += 1

        return added

    # =========================================================================
    # TIER 2 METHODS - Inherited from base class
    # =========================================================================
    # traverse(), find_paths(), subgraph_query(), execute_query()
    # work automatically through default implementations!

    # =========================================================================
    # OPTIONAL: Override Tier 2 methods for optimization
    # =========================================================================

    async def vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
    ) -> List[tuple]:
        """
        Optimized vector search for in-memory store

        Performs brute-force cosine similarity over all entities with embeddings.

        Args:
            query_embedding: Query vector
            entity_type: Optional filter by entity type
            max_results: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)

        Returns:
            List of (entity, similarity_score) tuples, sorted descending
        """
        if not self._initialized:
            return []

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        import numpy as np

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        scored_entities = []

        for entity in self.entities.values():
            # Filter by entity type if specified
            if entity_type and entity.entity_type != entity_type:
                continue

            # Skip entities without embeddings
            if not entity.embedding:
                continue

            # Compute cosine similarity
            entity_vec = np.array(entity.embedding, dtype=np.float32)
            entity_norm = np.linalg.norm(entity_vec)

            if entity_norm == 0:
                continue

            # Cosine similarity
            similarity = np.dot(query_vec, entity_vec) / (query_norm * entity_norm)
            # Normalize to 0-1 range
            similarity = (similarity + 1) / 2

            # Filter by threshold
            if similarity >= score_threshold:
                scored_entities.append((entity, float(similarity)))

        # Sort by score descending and return top results
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[:max_results]

    async def text_search(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
        method: str = "bm25",
    ) -> List[tuple]:
        """
        Optimized text search for in-memory store

        Performs text similarity search over entity properties using BM25, Jaccard,
        cosine similarity, or Levenshtein distance.

        Args:
            query_text: Query text string
            entity_type: Optional filter by entity type
            max_results: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            method: Similarity method ("bm25", "jaccard", "cosine", "levenshtein")

        Returns:
            List of (entity, similarity_score) tuples, sorted descending
        """
        if not self._initialized:
            return []

        if not query_text:
            return []

        from aiecs.application.knowledge_graph.search.text_similarity import (
            BM25Scorer,
            jaccard_similarity_text,
            cosine_similarity_text,
            normalized_levenshtein_similarity,
        )

        # Get candidate entities
        entities = list(self.entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        if not entities:
            return []

        scored_entities = []

        # Extract text from entities (combine properties into searchable text)
        entity_texts = []
        for entity in entities:
            # Combine all string properties into searchable text
            text_parts = []
            for key, value in entity.properties.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, (list, tuple)):
                    text_parts.extend(str(v) for v in value if isinstance(v, str))
            entity_text = " ".join(text_parts)
            entity_texts.append((entity, entity_text))

        if method == "bm25":
            # Use BM25 scorer
            corpus = [text for _, text in entity_texts]
            scorer = BM25Scorer(corpus)
            scores = scorer.score(query_text)

            for (entity, _), score in zip(entity_texts, scores):
                if score >= score_threshold:
                    scored_entities.append((entity, float(score)))

        elif method == "jaccard":
            for entity, text in entity_texts:
                score = jaccard_similarity_text(query_text, text)
                if score >= score_threshold:
                    scored_entities.append((entity, score))

        elif method == "cosine":
            for entity, text in entity_texts:
                score = cosine_similarity_text(query_text, text)
                if score >= score_threshold:
                    scored_entities.append((entity, score))

        elif method == "levenshtein":
            for entity, text in entity_texts:
                score = normalized_levenshtein_similarity(query_text, text)
                if score >= score_threshold:
                    scored_entities.append((entity, score))

        else:
            raise ValueError(f"Unknown text search method: {method}. Use 'bm25', 'jaccard', 'cosine', or 'levenshtein'")

        # Sort by score descending and return top results
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[:max_results]

    async def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int = 5,
        max_paths: int = 10,
    ) -> List:
        """
        Optimized path finding using networkx algorithms

        Overrides default implementation to use networkx.all_simple_paths
        for better performance.
        """
        from aiecs.domain.knowledge_graph.models.path import Path

        if not self._initialized:
            return []

        if self.graph is None or source_entity_id not in self.graph or target_entity_id not in self.graph:
            return []

        try:
            # Use networkx's optimized path finding
            paths = []
            for node_path in nx.all_simple_paths(
                self.graph,
                source_entity_id,
                target_entity_id,
                cutoff=max_depth,
            ):
                # Convert node IDs to Entity and Relation objects
                entities = [self.entities[node_id] for node_id in node_path if node_id in self.entities]

                # Get relations between consecutive nodes
                edges = []
                for i in range(len(node_path) - 1):
                    edge_data = self.graph.get_edge_data(node_path[i], node_path[i + 1])
                    if edge_data and "relation" in edge_data:
                        edges.append(edge_data["relation"])

                if len(entities) == len(node_path):
                    paths.append(Path(nodes=entities, edges=edges))

                if len(paths) >= max_paths:
                    break

            return paths

        except nx.NetworkXNoPath:
            return []

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_stats(self) -> Dict[str, int]:
        """
        Get graph statistics

        Returns:
            Dictionary with node count, edge count, etc.
        """
        if not self._initialized:
            return {"nodes": 0, "edges": 0, "entities": 0, "relations": 0}

        if self.graph is None:
            return {"nodes": 0, "edges": 0, "entities": 0, "relations": 0}
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "entities": len(self.entities),
            "relations": len(self.relations),
        }

    def clear(self) -> None:
        """Clear all data from the graph"""
        if self._initialized and self.graph is not None:
            self.graph.clear()
            self.entities.clear()
            self.relations.clear()
            if self._property_optimizer is not None:
                self._property_optimizer.property_index.clear()

    # =========================================================================
    # PROPERTY OPTIMIZATION METHODS
    # =========================================================================

    @property
    def property_optimizer(self) -> Optional[PropertyOptimizer]:
        """Get the property optimizer if configured"""
        return self._property_optimizer

    def lookup_by_property(self, property_name: str, value: Any) -> Set[str]:
        """
        Look up entity IDs by property value using the property index.

        This is much faster than scanning all entities when the property is indexed.

        Args:
            property_name: Property name to search
            value: Property value to match

        Returns:
            Set of matching entity IDs
        """
        if self._property_optimizer is None:
            return set()
        return self._property_optimizer.lookup_by_property(property_name, value)

    async def get_entities_by_property(
        self,
        property_name: str,
        value: Any,
    ) -> List[Entity]:
        """
        Get entities by property value.

        Uses property index if available, otherwise scans all entities.

        Args:
            property_name: Property name to search
            value: Property value to match

        Returns:
            List of matching entities
        """
        # Try indexed lookup first
        if self._property_optimizer is not None:
            entity_ids = self._property_optimizer.lookup_by_property(property_name, value)
            if entity_ids:
                return [self.entities[eid] for eid in entity_ids if eid in self.entities]

        # Fall back to scan
        return [
            entity for entity in self.entities.values()
            if entity.properties.get(property_name) == value
        ]

    def add_indexed_property(self, property_name: str) -> None:
        """
        Add a property to the index for fast lookups.

        Args:
            property_name: Property name to index
        """
        if self._property_optimizer is None:
            self._property_optimizer = PropertyOptimizer()

        self._property_optimizer.add_indexed_property(property_name)

        # Index existing entities
        for entity_id, entity in self.entities.items():
            if property_name in entity.properties:
                self._property_optimizer.property_index.add_to_index(
                    entity_id, property_name, entity.properties[property_name]
                )

    def __str__(self) -> str:
        stats = self.get_stats()
        return f"InMemoryGraphStore(entities={stats['entities']}, relations={stats['relations']})"

    def __repr__(self) -> str:
        return self.__str__()

"""
In-Memory Graph Store Implementation

Implements Tier 1 of GraphStore interface using networkx.
Tier 2 methods work automatically via default implementations.

This is ideal for:
- Development and testing
- Small graphs (< 100K nodes)
- Prototyping
- Scenarios where persistence is not required

Multi-tenancy Support:
- Tenant-partitioned graphs using OrderedDict for LRU tracking
- Global graph for tenant_id=None (never evicted)
- Configurable max_tenant_graphs with LRU eviction
- Environment variable KG_INMEMORY_MAX_TENANTS for configuration
"""

import os
from collections import OrderedDict
from typing import Any, List, Optional, Dict, Set, Tuple
import networkx as nx  # type: ignore[import-untyped]
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext, CrossTenantRelationError
from aiecs.infrastructure.graph_storage.property_storage import (
    PropertyOptimizer,
    PropertyStorageConfig,
    PropertyIndex,
)

# Default maximum number of tenant graphs to keep in memory
DEFAULT_MAX_TENANT_GRAPHS = 100
ENV_MAX_TENANTS = "KG_INMEMORY_MAX_TENANTS"


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

    **Multi-Tenancy Support**:
    - Tenant-partitioned graphs: Each tenant has its own nx.DiGraph
    - Global graph for tenant_id=None (never evicted, backward compatible)
    - LRU eviction: When max_tenant_graphs exceeded, least recently used tenant evicted
    - Configure via max_tenant_graphs param or KG_INMEMORY_MAX_TENANTS env var

    **Limitations**:
    - Not persistent (lost on restart)
    - Limited by RAM
    - No concurrent access control
    - No vector search optimization

    Example:
        ```python
        store = InMemoryGraphStore()
        await store.initialize()

        # Single-tenant usage (backward compatible)
        entity = Entity(id="person_1", entity_type="Person", properties={"name": "Alice"})
        await store.add_entity(entity)

        # Multi-tenant usage
        from aiecs.infrastructure.graph_storage.tenant import TenantContext
        context = TenantContext(tenant_id="acme-corp")
        await store.add_entity(entity, context=context)

        # Tier 2 methods work automatically with tenant isolation
        paths = await store.traverse("person_1", max_depth=3, context=context)
        ```
    """

    def __init__(
        self,
        property_storage_config: Optional[PropertyStorageConfig] = None,
        max_tenant_graphs: Optional[int] = None,
    ) -> None:
        """
        Initialize in-memory graph store

        Args:
            property_storage_config: Optional configuration for property storage optimization.
                                     Enables sparse storage, compression, and indexing.
            max_tenant_graphs: Maximum number of tenant graphs to keep in memory.
                              When exceeded, least recently used tenant is evicted.
                              Default: 100 (or KG_INMEMORY_MAX_TENANTS env var)
        """
        # Determine max tenant graphs from param, env var, or default
        if max_tenant_graphs is not None:
            self._max_tenant_graphs = max_tenant_graphs
        else:
            env_value = os.environ.get(ENV_MAX_TENANTS)
            if env_value:
                try:
                    self._max_tenant_graphs = int(env_value)
                except ValueError:
                    self._max_tenant_graphs = DEFAULT_MAX_TENANT_GRAPHS
            else:
                self._max_tenant_graphs = DEFAULT_MAX_TENANT_GRAPHS

        # Global graph for tenant_id=None (never evicted)
        self._global_graph: Optional[nx.DiGraph] = None
        self._global_entities: Dict[str, Entity] = {}
        self._global_relations: Dict[str, Relation] = {}

        # Tenant-partitioned storage with LRU tracking
        # OrderedDict maintains insertion order; move_to_end() for LRU
        self._tenant_graphs: OrderedDict[str, nx.DiGraph] = OrderedDict()
        self._tenant_entities: Dict[str, Dict[str, Entity]] = {}
        self._tenant_relations: Dict[str, Dict[str, Relation]] = {}

        # Legacy attributes for backward compatibility
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

        # Initialize global graph (for tenant_id=None)
        self._global_graph = nx.DiGraph()
        self._global_entities = {}
        self._global_relations = {}

        # Initialize tenant storage
        self._tenant_graphs = OrderedDict()
        self._tenant_entities = {}
        self._tenant_relations = {}

        # Legacy references point to global storage for backward compatibility
        self.graph = self._global_graph
        self.entities = self._global_entities
        self.relations = self._global_relations

        self._initialized = True

    async def close(self) -> None:
        """Close and cleanup (nothing to do for in-memory)"""
        # Clear global storage
        self._global_graph = None
        self._global_entities = {}
        self._global_relations = {}

        # Clear tenant storage
        self._tenant_graphs.clear()
        self._tenant_entities.clear()
        self._tenant_relations.clear()

        # Clear legacy references
        self.graph = None
        self.entities = {}
        self.relations = {}

        self._initialized = False

    # =========================================================================
    # MULTI-TENANCY HELPERS
    # =========================================================================

    def _get_tenant_id(self, context: Optional[TenantContext]) -> Optional[str]:
        """Extract tenant_id from context, returns None for global namespace."""
        return context.tenant_id if context else None

    def _get_graph(self, tenant_id: Optional[str]) -> nx.DiGraph:
        """
        Get the graph for a tenant with LRU tracking.

        Args:
            tenant_id: Tenant ID or None for global namespace

        Returns:
            networkx DiGraph for the tenant

        Note:
            - Global graph (tenant_id=None) is never evicted
            - Tenant graphs are evicted LRU when max_tenant_graphs exceeded
        """
        if tenant_id is None:
            # Global namespace - never evicted
            if self._global_graph is None:
                self._global_graph = nx.DiGraph()
            return self._global_graph

        # Tenant-specific graph
        if tenant_id in self._tenant_graphs:
            # Move to end for LRU tracking (most recently used)
            self._tenant_graphs.move_to_end(tenant_id)
            return self._tenant_graphs[tenant_id]

        # Create new tenant graph
        self._evict_if_needed()
        graph = nx.DiGraph()
        self._tenant_graphs[tenant_id] = graph
        self._tenant_entities[tenant_id] = {}
        self._tenant_relations[tenant_id] = {}
        return graph

    def _get_entities_dict(self, tenant_id: Optional[str], update_lru: bool = True) -> Dict[str, Entity]:
        """Get entities dict for a tenant.
        
        Args:
            tenant_id: Tenant ID or None for global namespace
            update_lru: Whether to update LRU tracking (default: True)
        """
        if tenant_id is None:
            return self._global_entities
        # Update LRU tracking if tenant exists
        if update_lru and tenant_id in self._tenant_graphs:
            self._tenant_graphs.move_to_end(tenant_id)
        if tenant_id not in self._tenant_entities:
            self._tenant_entities[tenant_id] = {}
        return self._tenant_entities[tenant_id]

    def _get_relations_dict(self, tenant_id: Optional[str], update_lru: bool = True) -> Dict[str, Relation]:
        """Get relations dict for a tenant.
        
        Args:
            tenant_id: Tenant ID or None for global namespace
            update_lru: Whether to update LRU tracking (default: True)
        """
        if tenant_id is None:
            return self._global_relations
        # Update LRU tracking if tenant exists
        if update_lru and tenant_id in self._tenant_graphs:
            self._tenant_graphs.move_to_end(tenant_id)
        if tenant_id not in self._tenant_relations:
            self._tenant_relations[tenant_id] = {}
        return self._tenant_relations[tenant_id]

    def _evict_if_needed(self) -> None:
        """Evict least recently used tenant if max_tenant_graphs exceeded."""
        while len(self._tenant_graphs) >= self._max_tenant_graphs:
            # Pop the first item (least recently used)
            evicted_tenant_id, _ = self._tenant_graphs.popitem(last=False)
            # Clean up associated data
            self._tenant_entities.pop(evicted_tenant_id, None)
            self._tenant_relations.pop(evicted_tenant_id, None)

    def get_tenant_count(self) -> int:
        """
        Get the number of tenant graphs currently in memory.

        Returns:
            Number of tenant graphs (excludes global graph)
        """
        return len(self._tenant_graphs)

    def get_tenant_ids(self) -> List[str]:
        """
        Get list of tenant IDs currently in memory.

        Returns:
            List of tenant IDs (excludes global namespace)
        """
        return list(self._tenant_graphs.keys())

    # =========================================================================
    # TIER 1 CRUD OPERATIONS
    # =========================================================================

    async def add_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
        """
        Add entity to graph

        Args:
            entity: Entity to add
            context: Optional tenant context for multi-tenant isolation

        Raises:
            ValueError: If entity already exists
            RuntimeError: If store not initialized
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities = self._get_entities_dict(tenant_id)

        if entity.id in entities:
            raise ValueError(f"Entity with ID '{entity.id}' already exists")

        # Set tenant_id on entity if context provided and entity doesn't have one
        if tenant_id is not None and entity.tenant_id is None:
            entity.tenant_id = tenant_id

        # Apply property optimization if enabled
        if self._property_optimizer is not None:
            # Apply sparse storage (remove None values)
            entity.properties = self._property_optimizer.optimize_properties(entity.properties)
            # Index properties for fast lookup
            self._property_optimizer.index_entity(entity.id, entity.properties)

        # Add to networkx graph
        graph.add_node(entity.id, entity=entity)

        # Add to entity index
        entities[entity.id] = entity

    async def get_entity(self, entity_id: str, context: Optional[TenantContext] = None) -> Optional[Entity]:
        """
        Get entity by ID

        Args:
            entity_id: Entity ID
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Entity if found, None otherwise
        """
        if not self._initialized:
            return None

        tenant_id = self._get_tenant_id(context)
        entities = self._get_entities_dict(tenant_id)
        return entities.get(entity_id)

    async def add_relation(self, relation: Relation, context: Optional[TenantContext] = None) -> None:
        """
        Add relation to graph

        Args:
            relation: Relation to add
            context: Optional tenant context for multi-tenant isolation

        Raises:
            ValueError: If relation already exists or entities don't exist
            CrossTenantRelationError: If source and target entities belong to different tenants
            RuntimeError: If store not initialized
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities = self._get_entities_dict(tenant_id)
        relations = self._get_relations_dict(tenant_id)

        if relation.id in relations:
            raise ValueError(f"Relation with ID '{relation.id}' already exists")

        # Validate entities exist within the same tenant scope
        source_entity = entities.get(relation.source_id)
        target_entity = entities.get(relation.target_id)

        if source_entity is None:
            raise ValueError(f"Source entity '{relation.source_id}' not found")
        if target_entity is None:
            raise ValueError(f"Target entity '{relation.target_id}' not found")

        # Enforce same-tenant constraint
        if tenant_id is not None:
            source_tenant = source_entity.tenant_id
            target_tenant = target_entity.tenant_id
            if source_tenant != target_tenant:
                raise CrossTenantRelationError(source_tenant, target_tenant)

        # Set tenant_id on relation if context provided and relation doesn't have one
        if tenant_id is not None and relation.tenant_id is None:
            relation.tenant_id = tenant_id

        # Add to networkx graph
        graph.add_edge(
            relation.source_id,
            relation.target_id,
            key=relation.id,
            relation=relation,
        )

        # Add to relation index
        relations[relation.id] = relation

    async def get_relation(self, relation_id: str, context: Optional[TenantContext] = None) -> Optional[Relation]:
        """
        Get relation by ID

        Args:
            relation_id: Relation ID
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Relation if found, None otherwise
        """
        if not self._initialized:
            return None

        tenant_id = self._get_tenant_id(context)
        relations = self._get_relations_dict(tenant_id)
        return relations.get(relation_id)

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get neighboring entities

        Args:
            entity_id: Entity ID to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of neighboring entities
        """
        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities = self._get_entities_dict(tenant_id)

        if entity_id not in graph:
            return []

        neighbors = []

        # Get outgoing neighbors
        if direction in ("outgoing", "both"):
            for target_id in graph.successors(entity_id):
                # Check relation type filter
                if relation_type:
                    edge_data = graph.get_edge_data(entity_id, target_id)
                    if edge_data:
                        relation = edge_data.get("relation")
                        if relation and relation.relation_type == relation_type:
                            if target_id in entities:
                                neighbors.append(entities[target_id])
                else:
                    if target_id in entities:
                        neighbors.append(entities[target_id])

        # Get incoming neighbors
        if direction in ("incoming", "both"):
            for source_id in graph.predecessors(entity_id):
                # Check relation type filter
                if relation_type:
                    edge_data = graph.get_edge_data(source_id, entity_id)
                    if edge_data:
                        relation = edge_data.get("relation")
                        if relation and relation.relation_type == relation_type:
                            if source_id in entities:
                                neighbors.append(entities[source_id])
                else:
                    if source_id in entities:
                        neighbors.append(entities[source_id])

        return neighbors

    async def get_outgoing_relations(self, entity_id: str, context: Optional[TenantContext] = None) -> List[Relation]:
        """
        Get all outgoing relations for an entity.

        Args:
            entity_id: Entity ID to get outgoing relations for
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of outgoing Relation objects
        """
        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)

        if entity_id not in graph:
            return []

        relations = []
        for target_id in graph.successors(entity_id):
            edge_data = graph.get_edge_data(entity_id, target_id)
            if edge_data:
                relation = edge_data.get("relation")
                if relation:
                    relations.append(relation)

        return relations

    async def get_incoming_relations(self, entity_id: str, context: Optional[TenantContext] = None) -> List[Relation]:
        """
        Get all incoming relations for an entity.

        Args:
            entity_id: Entity ID to get incoming relations for
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of incoming Relation objects
        """
        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)

        if entity_id not in graph:
            return []

        relations = []
        for source_id in graph.predecessors(entity_id):
            edge_data = graph.get_edge_data(source_id, entity_id)
            if edge_data:
                relation = edge_data.get("relation")
                if relation:
                    relations.append(relation)

        return relations

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get all entities, optionally filtered by type

        Args:
            entity_type: Optional filter by entity type
            limit: Optional limit on number of entities
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of entities
        """
        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)
        entities = list(entities_dict.values())

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

    async def add_entities_bulk(self, entities: List[Entity], context: Optional[TenantContext] = None) -> int:
        """
        Add multiple entities in bulk (optimized).

        Bypasses individual add_entity() calls for better performance.

        Args:
            entities: List of entities to add
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Number of entities successfully added
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities_dict = self._get_entities_dict(tenant_id)

        added = 0
        for entity in entities:
            if entity.id in entities_dict:
                continue  # Skip existing entities

            # Set tenant_id on entity if context provided
            if tenant_id is not None and entity.tenant_id is None:
                entity.tenant_id = tenant_id

            # Apply property optimization if enabled
            if self._property_optimizer is not None:
                entity.properties = self._property_optimizer.optimize_properties(entity.properties)
                self._property_optimizer.index_entity(entity.id, entity.properties)

            # Add to graph and index
            graph.add_node(entity.id, entity=entity)
            entities_dict[entity.id] = entity
            added += 1

        return added

    async def add_relations_bulk(self, relations: List[Relation], context: Optional[TenantContext] = None) -> int:
        """
        Add multiple relations in bulk (optimized).

        Bypasses individual add_relation() calls for better performance.

        Args:
            relations: List of relations to add
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Number of relations successfully added
        """
        if not self._initialized:
            raise RuntimeError("GraphStore not initialized. Call initialize() first.")

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities_dict = self._get_entities_dict(tenant_id)
        relations_dict = self._get_relations_dict(tenant_id)

        added = 0
        for relation in relations:
            if relation.id in relations_dict:
                continue  # Skip existing relations

            # Validate entities exist
            if relation.source_id not in entities_dict:
                continue
            if relation.target_id not in entities_dict:
                continue

            # Set tenant_id on relation if context provided
            if tenant_id is not None and relation.tenant_id is None:
                relation.tenant_id = tenant_id

            # Add edge
            graph.add_edge(
                relation.source_id,
                relation.target_id,
                key=relation.id,
                relation=relation,
            )
            relations_dict[relation.id] = relation
            added += 1

        return added

    # =========================================================================
    # TIER 2 METHODS - Optimized overrides with multi-tenancy support
    # =========================================================================

    async def traverse(
        self,
        start_entity_id: str,
        relation_type: Optional[str] = None,
        max_depth: int = 3,
        max_results: int = 100,
        context: Optional[TenantContext] = None,
    ) -> List:
        """
        Optimized graph traversal using BFS within tenant boundaries.

        Args:
            start_entity_id: Starting entity ID
            relation_type: Optional filter by relation type
            max_depth: Maximum traversal depth
            max_results: Maximum number of paths to return
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of paths found during traversal
        """
        from collections import deque
        from aiecs.domain.knowledge_graph.models.path import Path

        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities_dict = self._get_entities_dict(tenant_id)

        start_entity = entities_dict.get(start_entity_id)
        if start_entity is None:
            return []

        paths: List[Path] = []
        visited: Set[str] = set()
        queue: deque = deque([(start_entity, [])])  # (entity, edges_path)

        while queue and len(paths) < max_results:
            current_entity, edges_path = queue.popleft()
            current_depth = len(edges_path)

            if current_entity.id in visited:
                continue
            visited.add(current_entity.id)

            # Create path for this node
            if current_depth > 0:  # Don't add single-node paths
                nodes_path = [entities_dict[start_entity_id]]
                for edge in edges_path:
                    target_entity = entities_dict.get(edge.target_id)
                    if target_entity:
                        nodes_path.append(target_entity)

                if len(nodes_path) == len(edges_path) + 1:
                    paths.append(Path(nodes=nodes_path, edges=edges_path))

            # Explore neighbors if not at max depth
            if current_depth < max_depth:
                for target_id in graph.successors(current_entity.id):
                    if target_id in visited:
                        continue

                    # Get edge data for relation type filtering
                    edge_data = graph.get_edge_data(current_entity.id, target_id)
                    if edge_data:
                        relation = edge_data.get("relation")
                        if relation:
                            # Filter by relation type if specified
                            if relation_type and relation.relation_type != relation_type:
                                continue

                            target_entity = entities_dict.get(target_id)
                            if target_entity:
                                queue.append((target_entity, edges_path + [relation]))

        return paths

    async def vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
        context: Optional[TenantContext] = None,
    ) -> List[Tuple[Entity, float]]:
        """
        Optimized vector search for in-memory store

        Performs brute-force cosine similarity over all entities with embeddings.

        Args:
            query_embedding: Query vector
            entity_type: Optional filter by entity type
            max_results: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of (entity, similarity_score) tuples, sorted descending
        """
        if not self._initialized:
            return []

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        import numpy as np

        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        scored_entities: List[Tuple[Entity, float]] = []

        for entity in entities_dict.values():
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
        context: Optional[TenantContext] = None,
    ) -> List[Tuple[Entity, float]]:
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
            context: Optional tenant context for multi-tenant isolation

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

        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)

        # Get candidate entities
        entities = list(entities_dict.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        if not entities:
            return []

        scored_entities: List[Tuple[Entity, float]] = []

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
        context: Optional[TenantContext] = None,
    ) -> List:
        """
        Optimized path finding using networkx algorithms

        Overrides default implementation to use networkx.all_simple_paths
        for better performance.

        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            max_depth: Maximum path length
            max_paths: Maximum number of paths to return
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of paths between source and target
        """
        from aiecs.domain.knowledge_graph.models.path import Path

        if not self._initialized:
            return []

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities_dict = self._get_entities_dict(tenant_id)

        if source_entity_id not in graph or target_entity_id not in graph:
            return []

        try:
            # Use networkx's optimized path finding
            paths = []
            for node_path in nx.all_simple_paths(
                graph,
                source_entity_id,
                target_entity_id,
                cutoff=max_depth,
            ):
                # Convert node IDs to Entity and Relation objects
                entities = [entities_dict[node_id] for node_id in node_path if node_id in entities_dict]

                # Get relations between consecutive nodes
                edges = []
                for i in range(len(node_path) - 1):
                    edge_data = graph.get_edge_data(node_path[i], node_path[i + 1])
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

    def get_stats(self, context: Optional[TenantContext] = None) -> Dict[str, int]:
        """
        Get graph statistics

        Args:
            context: Optional tenant context for tenant-scoped stats

        Returns:
            Dictionary with node count, edge count, etc.
        """
        if not self._initialized:
            return {"nodes": 0, "edges": 0, "entities": 0, "relations": 0, "tenant_count": 0}

        tenant_id = self._get_tenant_id(context)
        graph = self._get_graph(tenant_id)
        entities_dict = self._get_entities_dict(tenant_id)
        relations_dict = self._get_relations_dict(tenant_id)

        return {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
            "entities": len(entities_dict),
            "relations": len(relations_dict),
            "tenant_count": len(self._tenant_graphs),
        }

    async def clear(self, context: Optional[TenantContext] = None) -> None:
        """
        Clear data from the graph

        Args:
            context: Optional tenant context for multi-tenant isolation.
                    If provided, clears only data for the specified tenant.
                    If None, clears all data including global and all tenants.
        """
        if not self._initialized:
            return

        tenant_id = self._get_tenant_id(context)

        if tenant_id is None:
            # Clear all data (global + all tenants)
            if self._global_graph is not None:
                self._global_graph.clear()
            self._global_entities.clear()
            self._global_relations.clear()

            # Clear all tenant data
            for tid in list(self._tenant_graphs.keys()):
                self._tenant_graphs[tid].clear()
            self._tenant_graphs.clear()
            self._tenant_entities.clear()
            self._tenant_relations.clear()

            if self._property_optimizer is not None:
                self._property_optimizer.property_index.clear()
        else:
            # Clear only tenant-specific data
            if tenant_id in self._tenant_graphs:
                self._tenant_graphs[tenant_id].clear()
                del self._tenant_graphs[tenant_id]
            if tenant_id in self._tenant_entities:
                self._tenant_entities[tenant_id].clear()
                del self._tenant_entities[tenant_id]
            if tenant_id in self._tenant_relations:
                self._tenant_relations[tenant_id].clear()
                del self._tenant_relations[tenant_id]

    # =========================================================================
    # PROPERTY OPTIMIZATION METHODS
    # =========================================================================

    @property
    def property_optimizer(self) -> Optional[PropertyOptimizer]:
        """Get the property optimizer if configured"""
        return self._property_optimizer

    def lookup_by_property(self, property_name: str, value: Any, context: Optional[TenantContext] = None) -> Set[str]:
        """
        Look up entity IDs by property value using the property index.

        This is much faster than scanning all entities when the property is indexed.

        Args:
            property_name: Property name to search
            value: Property value to match
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Set of matching entity IDs
        """
        if self._property_optimizer is None:
            return set()

        # Get all matching IDs from the index
        all_ids = self._property_optimizer.lookup_by_property(property_name, value)

        # Filter by tenant
        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)
        return {eid for eid in all_ids if eid in entities_dict}

    async def get_entities_by_property(
        self,
        property_name: str,
        value: Any,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get entities by property value.

        Uses property index if available, otherwise scans all entities.

        Args:
            property_name: Property name to search
            value: Property value to match
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of matching entities
        """
        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)

        # Try indexed lookup first
        if self._property_optimizer is not None:
            entity_ids = self._property_optimizer.lookup_by_property(property_name, value)
            if entity_ids:
                return [entities_dict[eid] for eid in entity_ids if eid in entities_dict]

        # Fall back to scan
        return [
            entity for entity in entities_dict.values()
            if entity.properties.get(property_name) == value
        ]

    def add_indexed_property(self, property_name: str, context: Optional[TenantContext] = None) -> None:
        """
        Add a property to the index for fast lookups.

        Args:
            property_name: Property name to index
            context: Optional tenant context to index specific tenant's entities
        """
        if self._property_optimizer is None:
            self._property_optimizer = PropertyOptimizer()

        self._property_optimizer.add_indexed_property(property_name)

        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id)

        # Index existing entities
        for entity_id, entity in entities_dict.items():
            if property_name in entity.properties:
                self._property_optimizer.property_index.add_to_index(
                    entity_id, property_name, entity.properties[property_name]
                )

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get all entities in the graph store

        Efficient implementation for InMemoryGraphStore that iterates through
        the entities dictionary.

        Args:
            entity_type: Optional filter by entity type
            limit: Optional maximum number of entities to return
            offset: Number of entities to skip (for pagination)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of entities matching the criteria
        """
        tenant_id = self._get_tenant_id(context)
        entities_dict = self._get_entities_dict(tenant_id, update_lru=False)

        # Filter by entity type if specified
        entities = list(entities_dict.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]

        # Apply pagination
        if offset > 0:
            entities = entities[offset:]
        if limit is not None:
            entities = entities[:limit]

        return entities

    def __str__(self) -> str:
        stats = self.get_stats()
        return (
            f"InMemoryGraphStore(global_entities={stats['entities']}, "
            f"global_relations={stats['relations']}, tenant_count={stats['tenant_count']})"
        )

    def __repr__(self) -> str:
        return self.__str__()

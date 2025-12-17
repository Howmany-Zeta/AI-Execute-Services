"""
Graph Store Base Interface

Two-tier abstract interface for graph storage backends:
- Tier 1 (Basic): Must implement - core CRUD operations
- Tier 2 (Advanced): Has defaults, can optimize - complex queries

This design allows minimal adapters (Tier 1 only) to work immediately,
while backends can optimize Tier 2 methods for better performance.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from collections import deque

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.query import (
    GraphQuery,
    GraphResult,
    QueryType,
)
from aiecs.infrastructure.graph_storage.tenant import TenantContext


class GraphStore(ABC):
    """
    Abstract Graph Storage Interface

    Two-tier design:

    **Tier 1 - Basic Interface (MUST IMPLEMENT)**:
    - add_entity() - Add entity to graph
    - get_entity() - Get entity by ID
    - add_relation() - Add relation to graph
    - get_relation() - Get relation by ID
    - get_neighbors() - Get neighboring entities
    - initialize() - Initialize storage
    - close() - Close storage connection

    **Tier 2 - Advanced Interface (HAS DEFAULTS, CAN OPTIMIZE)**:
    - traverse() - Multi-hop graph traversal
    - find_paths() - Find paths between entities
    - subgraph_query() - Extract subgraph
    - vector_search() - Semantic vector search
    - execute_query() - Execute GraphQuery
    - clear() - Clear all data (tenant-scoped if context provided)

    **Multi-Tenancy Support**:
    All methods accept an optional `context: Optional[TenantContext]` parameter
    for multi-tenant data isolation. When provided, operations are scoped to
    the specified tenant. When None, operations work on the global namespace
    (backward compatible with single-tenant deployments).

    Implementations only need to provide Tier 1 methods. Tier 2 methods
    have default implementations using Tier 1, but can be overridden for
    performance optimization (e.g., using SQL recursive CTEs, Cypher queries).

    Example:
        ```python
        # Minimal implementation (Tier 1 only)
        class CustomGraphStore(GraphStore):
            async def add_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
                # Your implementation
                pass

            # ... implement other Tier 1 methods
            # Tier 2 methods work automatically!

        # Optimized implementation (override Tier 2)
        class OptimizedGraphStore(CustomGraphStore):
            async def traverse(self, ..., context: Optional[TenantContext] = None):
                # Use database-specific optimization
                pass

        # Multi-tenant usage
        context = TenantContext(tenant_id="acme-corp")
        await store.add_entity(entity, context=context)
        entities = await store.vector_search(embedding, context=context)
        ```
    """

    # =========================================================================
    # TIER 1: BASIC INTERFACE - MUST IMPLEMENT
    # =========================================================================

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the graph storage backend

        Called once before using the store. Use this to:
        - Create database connections
        - Initialize data structures
        - Create tables/indexes
        """

    @abstractmethod
    async def close(self) -> None:
        """
        Close the graph storage backend and cleanup resources

        Called when shutting down. Use this to:
        - Close database connections
        - Flush pending writes
        - Cleanup resources
        """

    @abstractmethod
    async def add_entity(self, entity: Entity, context: Optional[TenantContext] = None) -> None:
        """
        Add an entity to the graph

        Args:
            entity: Entity to add
            context: Optional tenant context for multi-tenant isolation

        Raises:
            ValueError: If entity with same ID already exists
        """

    @abstractmethod
    async def get_entity(self, entity_id: str, context: Optional[TenantContext] = None) -> Optional[Entity]:
        """
        Get an entity by ID

        Args:
            entity_id: Entity ID to retrieve
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Entity if found, None otherwise
        """

    @abstractmethod
    async def add_relation(self, relation: Relation, context: Optional[TenantContext] = None) -> None:
        """
        Add a relation to the graph

        Args:
            relation: Relation to add
            context: Optional tenant context for multi-tenant isolation

        Raises:
            ValueError: If relation with same ID already exists
            ValueError: If source or target entity doesn't exist
        """

    @abstractmethod
    async def get_relation(self, relation_id: str, context: Optional[TenantContext] = None) -> Optional[Relation]:
        """
        Get a relation by ID

        Args:
            relation_id: Relation ID to retrieve
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Relation if found, None otherwise
        """

    @abstractmethod
    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get neighboring entities connected by relations

        Args:
            entity_id: ID of entity to get neighbors for
            relation_type: Optional filter by relation type
            direction: "outgoing", "incoming", or "both"
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of neighboring entities
        """

    # =========================================================================
    # BULK OPERATIONS - Default implementations (can be optimized)
    # =========================================================================

    async def add_entities_bulk(self, entities: List[Entity]) -> int:
        """
        Add multiple entities in bulk.

        Default implementation calls add_entity() for each entity.
        Override for better performance with database-specific bulk inserts.

        Args:
            entities: List of entities to add

        Returns:
            Number of entities successfully added
        """
        added = 0
        for entity in entities:
            try:
                await self.add_entity(entity)
                added += 1
            except ValueError:
                # Entity already exists, skip
                pass
        return added

    async def add_relations_bulk(self, relations: List[Relation]) -> int:
        """
        Add multiple relations in bulk.

        Default implementation calls add_relation() for each relation.
        Override for better performance with database-specific bulk inserts.

        Args:
            relations: List of relations to add

        Returns:
            Number of relations successfully added
        """
        added = 0
        for relation in relations:
            try:
                await self.add_relation(relation)
                added += 1
            except ValueError:
                # Relation already exists or entities don't exist, skip
                pass
        return added

    # =========================================================================
    # TIER 2: ADVANCED INTERFACE - HAS DEFAULTS (Template Method Pattern)
    # =========================================================================

    async def traverse(
        self,
        start_entity_id: str,
        relation_type: Optional[str] = None,
        max_depth: int = 3,
        max_results: int = 100,
        context: Optional[TenantContext] = None,
    ) -> List[Path]:
        """
        Traverse the graph starting from an entity (BFS traversal)

        **DEFAULT IMPLEMENTATION**: Uses get_neighbors() in BFS pattern.
        Override for better performance (e.g., recursive CTEs in SQL).

        Args:
            start_entity_id: Starting entity ID
            relation_type: Optional filter by relation type
            max_depth: Maximum traversal depth
            max_results: Maximum number of paths to return
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of paths found during traversal
        """
        return await self._default_traverse_bfs(start_entity_id, relation_type, max_depth, max_results, context)

    async def find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int = 5,
        max_paths: int = 10,
        context: Optional[TenantContext] = None,
    ) -> List[Path]:
        """
        Find paths between two entities

        **DEFAULT IMPLEMENTATION**: Uses traverse() with early stopping.
        Override for better performance (e.g., bidirectional search).

        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            max_depth: Maximum path length
            max_paths: Maximum number of paths to return
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of paths between source and target
        """
        return await self._default_find_paths(source_entity_id, target_entity_id, max_depth, max_paths, context)

    async def subgraph_query(
        self,
        entity_ids: List[str],
        include_relations: bool = True,
        context: Optional[TenantContext] = None,
    ) -> tuple[List[Entity], List[Relation]]:
        """
        Extract a subgraph containing specified entities

        **DEFAULT IMPLEMENTATION**: Uses get_entity() and get_neighbors().
        Override for better performance (e.g., single JOIN query).

        Args:
            entity_ids: List of entity IDs to include
            include_relations: Whether to include relations between entities
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Tuple of (entities, relations)
        """
        return await self._default_subgraph_query(entity_ids, include_relations, context)

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        context: Optional[TenantContext] = None,
    ) -> List[Entity]:
        """
        Get all entities in the graph store

        **DEFAULT IMPLEMENTATION**: Uses entity enumeration.
        Override for better performance (e.g., database cursors, streaming).

        Args:
            entity_type: Optional filter by entity type
            limit: Optional maximum number of entities to return
            offset: Number of entities to skip (for pagination)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of entities matching the criteria

        Example:
            # Get all entities
            all_entities = await store.get_all_entities()

            # Get first 100 Person entities
            people = await store.get_all_entities(entity_type="Person", limit=100)

            # Get next page (pagination)
            next_page = await store.get_all_entities(entity_type="Person", limit=100, offset=100)
        """
        return await self._default_get_all_entities(entity_type, limit, offset, context)

    async def vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
        context: Optional[TenantContext] = None,
    ) -> List[tuple[Entity, float]]:
        """
        Semantic vector search over entities

        **DEFAULT IMPLEMENTATION**: Brute-force cosine similarity.
        Override for better performance (e.g., pgvector, FAISS, ANN indexes).

        Args:
            query_embedding: Query vector embedding
            entity_type: Optional filter by entity type
            max_results: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of (entity, score) tuples, sorted by score descending
        """
        return await self._default_vector_search(query_embedding, entity_type, max_results, score_threshold, context)

    async def text_search(
        self,
        query_text: str,
        entity_type: Optional[str] = None,
        max_results: int = 10,
        score_threshold: float = 0.0,
        method: str = "bm25",
        context: Optional[TenantContext] = None,
    ) -> List[tuple[Entity, float]]:
        """
        Text-based search over entities using text similarity

        **DEFAULT IMPLEMENTATION**: Uses text similarity utilities (BM25, Jaccard, etc.).
        Override for better performance (e.g., full-text search indexes).

        Args:
            query_text: Query text string
            entity_type: Optional filter by entity type
            max_results: Maximum number of results
            score_threshold: Minimum similarity score (0.0-1.0)
            method: Similarity method ("bm25", "jaccard", "cosine", "levenshtein")
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of (entity, score) tuples, sorted by score descending
        """
        return await self._default_text_search(query_text, entity_type, max_results, score_threshold, method, context)

    async def execute_query(self, query: GraphQuery, context: Optional[TenantContext] = None) -> GraphResult:
        """
        Execute a graph query

        **DEFAULT IMPLEMENTATION**: Routes to appropriate methods based on query type.
        Override for custom query execution logic.

        Args:
            query: Graph query to execute
            context: Optional tenant context for multi-tenant isolation

        Returns:
            Query results
        """
        return await self._default_execute_query(query, context)

    async def clear(self, context: Optional[TenantContext] = None) -> None:
        """
        Clear all data from the graph store

        **DEFAULT IMPLEMENTATION**: Not implemented in base class.
        Implementations should override this method to provide tenant-scoped clearing.

        Args:
            context: Optional tenant context for multi-tenant isolation.
                    If provided, clears only data for the specified tenant.
                    If None, clears all data (use with caution).
        """
        raise NotImplementedError("clear() must be implemented by subclasses")

    # =========================================================================
    # DEFAULT IMPLEMENTATIONS (Template Methods)
    # =========================================================================

    async def _default_traverse_bfs(
        self,
        start_entity_id: str,
        relation_type: Optional[str],
        max_depth: int,
        max_results: int,
        context: Optional[TenantContext],
    ) -> List[Path]:
        """
        Default BFS traversal implementation using get_neighbors()

        This provides a working traversal that any Tier 1 implementation gets for free.
        Backends can override traverse() with optimized versions.
        """
        start_entity = await self.get_entity(start_entity_id, context=context)
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
                nodes_path = [start_entity]
                for edge in edges_path:
                    target_entity = await self.get_entity(edge.target_id, context=context)
                    if target_entity:
                        nodes_path.append(target_entity)

                if len(nodes_path) == len(edges_path) + 1:
                    paths.append(Path(nodes=nodes_path, edges=edges_path))

            # Explore neighbors if not at max depth
            if current_depth < max_depth:
                neighbors = await self.get_neighbors(
                    current_entity.id,
                    relation_type=relation_type,
                    direction="outgoing",
                    context=context,
                )

                for neighbor in neighbors:
                    if neighbor.id not in visited:
                        # Find the relation connecting them
                        # (In a real implementation, get_neighbors should return relations too)
                        # For now, create a placeholder relation
                        edge = Relation(
                            id=f"rel_{current_entity.id}_{neighbor.id}",
                            relation_type=relation_type or "CONNECTED_TO",
                            source_id=current_entity.id,
                            target_id=neighbor.id,
                        )
                        queue.append((neighbor, edges_path + [edge]))

        return paths

    async def _default_find_paths(
        self,
        source_entity_id: str,
        target_entity_id: str,
        max_depth: int,
        max_paths: int,
        context: Optional[TenantContext],
    ) -> List[Path]:
        """
        Default path finding using BFS with target check
        """
        all_paths = await self.traverse(
            source_entity_id,
            max_depth=max_depth,
            max_results=max_paths * 10,  # Get more, filter later
            context=context,
        )

        # Filter paths that end at target
        target_paths = [path for path in all_paths if path.end_entity.id == target_entity_id]

        return target_paths[:max_paths]

    async def _default_subgraph_query(
        self,
        entity_ids: List[str],
        include_relations: bool,
        context: Optional[TenantContext],
    ) -> tuple[List[Entity], List[Relation]]:
        """
        Default subgraph extraction
        """
        entities = []
        relations = []

        # Fetch all entities
        for entity_id in entity_ids:
            entity = await self.get_entity(entity_id, context=context)
            if entity:
                entities.append(entity)

        # Fetch relations between entities (if requested)
        if include_relations:
            entity_id_set = set(entity_ids)
            for entity_id in entity_ids:
                neighbors = await self.get_neighbors(entity_id, direction="outgoing", context=context)
                for neighbor in neighbors:
                    if neighbor.id in entity_id_set:
                        # Fetch the relation (simplified - needs proper
                        # implementation)
                        rel = Relation(
                            id=f"rel_{entity_id}_{neighbor.id}",
                            relation_type="CONNECTED_TO",
                            source_id=entity_id,
                            target_id=neighbor.id,
                        )
                        relations.append(rel)

        return entities, relations

    async def _default_get_all_entities(
        self,
        entity_type: Optional[str],
        limit: Optional[int],
        offset: int,
        context: Optional[TenantContext],
    ) -> List[Entity]:
        """
        Default entity enumeration implementation

        This default raises NotImplementedError. Backends should override
        this method to provide efficient entity enumeration.

        Args:
            entity_type: Optional filter by entity type
            limit: Optional maximum number of entities to return
            offset: Number of entities to skip (for pagination)
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of entities matching the criteria

        Raises:
            NotImplementedError: If backend doesn't implement this method
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement get_all_entities() "
            "or override _default_get_all_entities()"
        )

    async def _default_vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str],
        max_results: int,
        score_threshold: float,
        context: Optional[TenantContext],
        ) -> List[tuple[Entity, float]]:
        """
        Default brute-force vector search using cosine similarity

        This implementation uses get_all_entities() to enumerate entities
        and computes cosine similarity. Backends should override with ANN indexes.
        """
        if not query_embedding:
            return []

        # Get all entities (or filtered by entity_type)
        entities = await self.get_all_entities(entity_type=entity_type, context=context)

        if not entities:
            return []

        # Compute cosine similarity for each entity with embedding
        scored_entities = []
        for entity in entities:
            if not entity.embedding:
                continue  # Skip entities without embeddings

            # Compute cosine similarity between vectors
            try:
                similarity = self._cosine_similarity_vectors(query_embedding, entity.embedding)
                if similarity >= score_threshold:
                    scored_entities.append((entity, float(similarity)))
            except Exception as e:
                # Skip entities with incompatible embedding dimensions
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Skipping entity {entity.id} due to embedding error: {e}")
                continue

        # Sort by score descending and return top results
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return scored_entities[:max_results]

    async def _default_text_search(
        self,
        query_text: str,
        entity_type: Optional[str],
        max_results: int,
        score_threshold: float,
        method: str,
        context: Optional[TenantContext],
    ) -> List[tuple[Entity, float]]:
        """
        Default text search using text similarity utilities

        This implementation requires get_all_entities() or similar method.
        Backends should override for better performance (e.g., full-text indexes).
        """
        # Try to get all entities - check if store has get_all_entities method
        if hasattr(self, "get_all_entities"):
            entities = await self.get_all_entities(entity_type=entity_type, context=context)
        else:
            # Fallback: return empty if no way to enumerate entities
            return []

        if not query_text:
            return []

        from aiecs.application.knowledge_graph.search.text_similarity import (
            BM25Scorer,
            jaccard_similarity_text,
            cosine_similarity_text,
            normalized_levenshtein_similarity,
        )

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

    def _cosine_similarity_vectors(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0.0-1.0)

        Raises:
            ValueError: If vectors have different dimensions or are empty
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vectors must have same dimension: {len(vec1)} != {len(vec2)}")
        if len(vec1) == 0:
            raise ValueError("Vectors cannot be empty")

        # Compute dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        # Compute magnitudes
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity
        similarity = dot_product / (magnitude1 * magnitude2)
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

    async def _default_execute_query(self, query: GraphQuery, context: Optional[TenantContext]) -> GraphResult:
        """
        Default query execution router with tenant filtering support.
        
        If query.tenant_id is provided, it takes precedence over the context parameter
        for tenant filtering. This ensures GraphQuery objects carry their own tenant scope.
        """
        import time

        start_time = time.time()

        # Apply tenant filtering: query.tenant_id takes precedence over context parameter
        # This allows GraphQuery to be self-contained with tenant scope
        effective_context = context
        if query.tenant_id is not None:
            # Create TenantContext from query.tenant_id if not already provided
            # If context was provided but has different tenant_id, query.tenant_id wins
            from aiecs.infrastructure.graph_storage.tenant import TenantIsolationMode
            effective_context = TenantContext(
                tenant_id=query.tenant_id,
                isolation_mode=context.isolation_mode if context else TenantIsolationMode.SHARED_SCHEMA,
            )

        if query.query_type == QueryType.ENTITY_LOOKUP:
            entity = await self.get_entity(query.entity_id, context=effective_context) if query.entity_id else None
            entities = [entity] if entity else []

        elif query.query_type == QueryType.VECTOR_SEARCH:
            if query.embedding:
                results = await self.vector_search(
                    query.embedding,
                    query.entity_type,
                    query.max_results,
                    query.score_threshold,
                    context=effective_context,
                )
                entities = [entity for entity, score in results]
            else:
                entities = []

        elif query.query_type == QueryType.TRAVERSAL:
            if query.entity_id:
                paths = await self.traverse(
                    query.entity_id,
                    query.relation_type,
                    query.max_depth,
                    query.max_results,
                    context=effective_context,
                )
                # Extract unique entities from paths
                entity_ids_seen = set()
                entities = []
                for path in paths:
                    for entity in path.nodes:
                        if entity.id not in entity_ids_seen:
                            entities.append(entity)
                            entity_ids_seen.add(entity.id)
            else:
                entities = []
                paths = []

        elif query.query_type == QueryType.PATH_FINDING:
            if query.source_entity_id and query.target_entity_id:
                paths = await self.find_paths(
                    query.source_entity_id,
                    query.target_entity_id,
                    query.max_depth,
                    query.max_results,
                    context=effective_context,
                )
                entities = []
            else:
                paths = []
                entities = []

        else:
            entities = []
            paths = []

        execution_time_ms = (time.time() - start_time) * 1000

        return GraphResult(
            query=query,
            entities=entities[: query.max_results],
            paths=paths[: query.max_results] if "paths" in locals() else [],
            scores=[],
            total_count=len(entities),
            execution_time_ms=execution_time_ms,
        )

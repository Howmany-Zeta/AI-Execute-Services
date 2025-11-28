"""
Hybrid Search Strategy

Combines vector similarity search with graph structure traversal
to provide enhanced search results.
"""

import logging
from typing import List, Optional, Dict, Tuple
from enum import Enum
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.infrastructure.graph_storage.base import GraphStore

logger = logging.getLogger(__name__)


class SearchMode(str, Enum):
    """Search mode for hybrid search"""

    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID = "hybrid"


class HybridSearchConfig(BaseModel):
    """
    Configuration for hybrid search

    Attributes:
        mode: Search mode (vector_only, graph_only, hybrid)
        vector_weight: Weight for vector similarity scores (0.0-1.0)
        graph_weight: Weight for graph structure scores (0.0-1.0)
        max_results: Maximum number of results to return
        vector_threshold: Minimum similarity threshold for vector search
        max_graph_depth: Maximum depth for graph traversal
        expand_results: Whether to expand vector results with graph neighbors
        min_combined_score: Minimum combined score threshold
    """

    mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")

    vector_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for vector similarity scores",
    )

    graph_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for graph structure scores",
    )

    max_results: int = Field(default=10, ge=1, description="Maximum number of results")

    vector_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for vector search",
    )

    max_graph_depth: int = Field(default=2, ge=1, le=5, description="Maximum depth for graph traversal")

    expand_results: bool = Field(
        default=True,
        description="Whether to expand vector results with graph neighbors",
    )

    min_combined_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum combined score threshold",
    )

    entity_type_filter: Optional[str] = Field(default=None, description="Optional entity type filter")

    class Config:
        use_enum_values = True


class HybridSearchStrategy:
    """
    Hybrid Search Strategy

    Combines vector similarity search with graph structure traversal
    to provide enhanced search results that leverage both semantic
    similarity and structural relationships.

    Search Modes:
    - VECTOR_ONLY: Pure vector similarity search
    - GRAPH_ONLY: Pure graph traversal from seed entities
    - HYBRID: Combines both approaches with weighted scoring

    Example:
        ```python
        strategy = HybridSearchStrategy(graph_store)

        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=0.6,
            graph_weight=0.4,
            max_results=10,
            expand_results=True
        )

        results = await strategy.search(
            query_embedding=[0.1, 0.2, ...],
            config=config
        )

        for entity, score in results:
            print(f"{entity.id}: {score:.3f}")
        ```
    """

    def __init__(self, graph_store: GraphStore):
        """
        Initialize hybrid search strategy

        Args:
            graph_store: Graph storage backend
        """
        self.graph_store = graph_store

    async def search(
        self,
        query_embedding: List[float],
        config: Optional[HybridSearchConfig] = None,
        seed_entity_ids: Optional[List[str]] = None,
    ) -> List[Tuple[Entity, float]]:
        """
        Perform hybrid search

        Args:
            query_embedding: Query vector embedding
            config: Search configuration (uses defaults if None)
            seed_entity_ids: Optional seed entities for graph traversal

        Returns:
            List of (entity, score) tuples sorted by score descending
        """
        if config is None:
            config = HybridSearchConfig()

        if config.mode == SearchMode.VECTOR_ONLY:
            return await self._vector_search(query_embedding, config)
        elif config.mode == SearchMode.GRAPH_ONLY:
            if not seed_entity_ids:
                # If no seeds provided, try vector search to find seeds
                if query_embedding:
                    try:
                        vector_results = await self._vector_search(query_embedding, config, max_results=5)
                        seed_entity_ids = [entity.id for entity, _ in vector_results]
                    except Exception as e:
                        logger.warning(f"Vector search failed while trying to find seed entities for graph search: {e}")
                        seed_entity_ids = []
                else:
                    logger.warning("No seed entities provided and no query embedding available for graph search")
                    seed_entity_ids = []
            
            if not seed_entity_ids:
                logger.warning("No seed entities available for graph-only search, returning empty results")
                return []
            
            return await self._graph_search(seed_entity_ids, config)
        else:  # HYBRID
            return await self._hybrid_search(query_embedding, config, seed_entity_ids)

    async def _vector_search(
        self,
        query_embedding: List[float],
        config: HybridSearchConfig,
        max_results: Optional[int] = None,
    ) -> List[Tuple[Entity, float]]:
        """
        Perform vector similarity search

        Args:
            query_embedding: Query vector
            config: Search configuration
            max_results: Optional override for max results

        Returns:
            List of (entity, score) tuples
        """
        results = await self.graph_store.vector_search(
            query_embedding=query_embedding,
            entity_type=config.entity_type_filter,
            max_results=max_results or config.max_results,
            score_threshold=config.vector_threshold,
        )

        return results

    async def _graph_search(self, seed_entity_ids: List[str], config: HybridSearchConfig) -> List[Tuple[Entity, float]]:
        """
        Perform graph structure search from seed entities

        Args:
            seed_entity_ids: Starting entities for traversal
            config: Search configuration

        Returns:
            List of (entity, score) tuples
        """
        # Collect entities from graph traversal
        entity_scores: Dict[str, float] = {}

        for seed_id in seed_entity_ids:
            # Get neighbors at different depths
            current_entities = {seed_id}
            visited = set()

            for depth in range(config.max_graph_depth):
                next_entities = set()

                for entity_id in current_entities:
                    if entity_id in visited:
                        continue

                    visited.add(entity_id)

                    # Score decreases with depth
                    depth_score = 1.0 / (depth + 1)

                    # Update score (take max if entity seen from multiple
                    # paths)
                    if entity_id not in entity_scores:
                        entity_scores[entity_id] = depth_score
                    else:
                        entity_scores[entity_id] = max(entity_scores[entity_id], depth_score)

                    # Get neighbors for next depth
                    neighbors = await self.graph_store.get_neighbors(entity_id, direction="outgoing")

                    for neighbor in neighbors:
                        if neighbor.id not in visited:
                            next_entities.add(neighbor.id)

                current_entities = next_entities

                if not current_entities:
                    break

        # Retrieve entities and create result list
        results = []
        for entity_id, score in entity_scores.items():
            entity = await self.graph_store.get_entity(entity_id)
            if entity:
                # Apply entity type filter if specified
                if config.entity_type_filter:
                    if entity.entity_type == config.entity_type_filter:
                        results.append((entity, score))
                else:
                    results.append((entity, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        return results[: config.max_results]

    async def _hybrid_search(
        self,
        query_embedding: List[float],
        config: HybridSearchConfig,
        seed_entity_ids: Optional[List[str]] = None,
    ) -> List[Tuple[Entity, float]]:
        """
        Perform hybrid search combining vector and graph

        Args:
            query_embedding: Query vector
            config: Search configuration
            seed_entity_ids: Optional seed entities

        Returns:
            List of (entity, score) tuples with combined scores
        """
        # Step 1: Vector search with fallback to graph-only
        vector_results = []
        vector_scores: Dict[str, float] = {}

        try:
            vector_results = await self._vector_search(
                query_embedding,
                config,
                max_results=config.max_results * 2,  # Get more for expansion
            )
            # Create score dictionaries
            vector_scores = {entity.id: score for entity, score in vector_results}

        except Exception as e:
            logger.warning(
                f"Vector search failed, falling back to graph-only search: {e}",
                exc_info=True
            )
            # Fallback to graph-only search if vector search fails
            if seed_entity_ids:
                logger.info("Using graph-only search with provided seed entities")
                return await self._graph_search(seed_entity_ids, config)
            else:
                logger.warning("No seed entities available for graph-only fallback, returning empty results")
                return []

        # Step 2: Graph expansion (if enabled)
        graph_scores: Dict[str, float] = {}

        if config.expand_results:
            try:
                # Use top vector results as seeds
                seeds = seed_entity_ids or [entity.id for entity, _ in vector_results[:5]]

                graph_results = await self._graph_search(seeds, config)
                graph_scores = {entity.id: score for entity, score in graph_results}

            except Exception as e:
                logger.warning(
                    f"Graph expansion failed, continuing with vector results only: {e}",
                    exc_info=True
                )
                # Continue with vector results only if graph expansion fails

        # Step 3: Combine scores
        combined_scores = await self._combine_scores(vector_scores, graph_scores, config)

        # Step 4: Retrieve entities and create results
        results = []
        for entity_id, combined_score in combined_scores.items():
            # Apply minimum score threshold
            if combined_score < config.min_combined_score:
                continue

            try:
                entity = await self.graph_store.get_entity(entity_id)
                if entity:
                    results.append((entity, combined_score))
            except Exception as e:
                logger.warning(f"Failed to retrieve entity {entity_id}: {e}")
                # Continue with other entities

        # Sort by combined score descending
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top results
        return results[: config.max_results]

    async def _combine_scores(
        self,
        vector_scores: Dict[str, float],
        graph_scores: Dict[str, float],
        config: HybridSearchConfig,
    ) -> Dict[str, float]:
        """
        Combine vector and graph scores with weighted averaging

        Args:
            vector_scores: Entity ID to vector similarity score
            graph_scores: Entity ID to graph structure score
            config: Search configuration

        Returns:
            Combined scores dictionary
        """
        # Normalize weights
        total_weight = config.vector_weight + config.graph_weight
        if total_weight == 0:
            total_weight = 1.0

        norm_vector_weight = config.vector_weight / total_weight
        norm_graph_weight = config.graph_weight / total_weight

        # Get all entity IDs
        all_entity_ids = set(vector_scores.keys()) | set(graph_scores.keys())

        # Combine scores
        combined: Dict[str, float] = {}

        for entity_id in all_entity_ids:
            v_score = vector_scores.get(entity_id, 0.0)
            g_score = graph_scores.get(entity_id, 0.0)

            # Weighted combination
            combined[entity_id] = v_score * norm_vector_weight + g_score * norm_graph_weight

        return combined

    async def search_with_expansion(
        self,
        query_embedding: List[float],
        config: Optional[HybridSearchConfig] = None,
        include_paths: bool = False,
    ) -> Tuple[List[Tuple[Entity, float]], Optional[List[Path]]]:
        """
        Search with result expansion and optional path tracking

        Args:
            query_embedding: Query vector
            config: Search configuration
            include_paths: Whether to include paths to results

        Returns:
            Tuple of (results, paths) where paths is None if not requested
        """
        if config is None:
            config = HybridSearchConfig()

        # Perform search
        results = await self.search(query_embedding, config)

        paths = None
        if include_paths and config.expand_results:
            # Find paths from top vector results to expanded results
            paths = await self._find_result_paths(results, config)

        return results, paths

    async def _find_result_paths(self, results: List[Tuple[Entity, float]], config: HybridSearchConfig) -> List[Path]:
        """
        Find paths between top results

        Args:
            results: Search results
            config: Search configuration

        Returns:
            List of paths connecting results
        """
        if len(results) < 2:
            return []

        paths = []

        # Find paths between top results
        for i in range(min(3, len(results))):
            source_id = results[i][0].id

            for j in range(i + 1, min(i + 4, len(results))):
                target_id = results[j][0].id

                # Find paths between these entities
                found_paths = await self.graph_store.find_paths(
                    source_entity_id=source_id,
                    target_entity_id=target_id,
                    max_depth=config.max_graph_depth,
                    max_paths=2,
                )

                paths.extend(found_paths)

        return paths

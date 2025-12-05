"""
Knowledge Graph Search Tool

AIECS tool for searching knowledge graphs with multiple search modes.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum

from aiecs.tools.base_tool import BaseTool
from aiecs.tools import register_tool
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.application.knowledge_graph.search.hybrid_search import (
    HybridSearchStrategy,
    HybridSearchConfig,
    SearchMode,
)
from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
    PersonalizedPageRank,
    MultiHopRetrieval,
    FilteredRetrieval,
    RetrievalCache,
)
from aiecs.application.knowledge_graph.traversal.enhanced_traversal import (
    EnhancedTraversal,
)
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern
from aiecs.application.knowledge_graph.search.reranker import (
    ResultReranker,
    ScoreCombinationMethod,
)
from aiecs.application.knowledge_graph.search.reranker_strategies import (
    TextSimilarityReranker,
    SemanticReranker,
    StructuralReranker,
    HybridReranker,
)
from aiecs.domain.knowledge_graph.models.entity import Entity


class SearchModeEnum(str, Enum):
    """Search mode enumeration"""

    VECTOR = "vector"
    GRAPH = "graph"
    HYBRID = "hybrid"
    PAGERANK = "pagerank"
    MULTIHOP = "multihop"
    FILTERED = "filtered"
    TRAVERSE = "traverse"


class GraphSearchInput(BaseModel):
    """Input schema for Graph Search Tool (legacy, for execute() method)"""

    mode: SearchModeEnum = Field(
        ...,
        description=(
            "Search mode: 'vector' (similarity), 'graph' (structure), "
            "'hybrid' (combined), 'pagerank' (importance), "
            "'multihop' (neighbors), 'filtered' (by properties), "
            "'traverse' (pattern-based)"
        ),
    )

    query: Optional[str] = Field(
        None,
        description="Natural language query (converted to embedding for vector/hybrid search)",
    )

    query_embedding: Optional[List[float]] = Field(None, description="Query vector embedding (for vector/hybrid search)")

    seed_entity_ids: Optional[List[str]] = Field(
        None,
        description="Starting entity IDs (for graph/pagerank/multihop/traverse modes)",
    )

    entity_type: Optional[str] = Field(
        None,
        description="Filter by entity type (e.g., 'Person', 'Company', 'Location')",
    )

    property_filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filter by properties (e.g., {'role': 'Engineer', 'level': 'Senior'})",
    )

    relation_types: Optional[List[str]] = Field(
        None,
        description="Filter by relation types (e.g., ['WORKS_FOR', 'LOCATED_IN'])",
    )

    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100)",
    )

    max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum traversal depth for graph/multihop/traverse modes (1-5)",
    )

    vector_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold for vector search (0.0-1.0)",
    )

    vector_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for vector similarity in hybrid mode (0.0-1.0)",
    )

    graph_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Weight for graph structure in hybrid mode (0.0-1.0)",
    )

    expand_results: bool = Field(
        default=True,
        description="Whether to expand results with graph neighbors (hybrid mode)",
    )

    use_cache: bool = Field(
        default=True,
        description="Whether to use result caching for performance",
    )

    # Reranking parameters
    enable_reranking: bool = Field(
        default=False,
        description="Whether to enable result reranking for improved relevance",
    )

    rerank_strategy: Optional[str] = Field(
        default="text",
        description=("Reranking strategy: 'text' (text similarity), 'semantic' (embeddings), " "'structural' (graph importance), 'hybrid' (all signals)"),
    )

    rerank_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=500,
        description=("Top-K results to fetch before reranking (for performance). " "If None, uses max_results. Should be >= max_results."),
    )


# Schemas for individual operations (used with run_async)
class VectorSearchSchema(BaseModel):
    """Schema for vector_search operation"""

    query: Optional[str] = Field(None, description="Natural language query")
    query_embedding: Optional[List[float]] = Field(None, description="Query vector embedding")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    vector_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity")
    enable_reranking: bool = Field(default=False, description="Enable result reranking")
    rerank_strategy: Optional[str] = Field(default="text", description="Reranking strategy")
    rerank_top_k: Optional[int] = Field(default=None, description="Top-K for reranking")


class GraphSearchSchema(BaseModel):
    """Schema for graph_search operation"""

    seed_entity_ids: List[str] = Field(..., description="Starting entity IDs")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum traversal depth")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")


class HybridSearchSchema(BaseModel):
    """Schema for hybrid_search operation"""

    query: Optional[str] = Field(None, description="Natural language query")
    query_embedding: Optional[List[float]] = Field(None, description="Query vector embedding")
    seed_entity_ids: Optional[List[str]] = Field(None, description="Starting entity IDs")
    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum graph depth")
    vector_weight: float = Field(default=0.6, ge=0.0, le=1.0, description="Vector weight")
    graph_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="Graph weight")
    expand_results: bool = Field(default=True, description="Expand with neighbors")
    vector_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity")
    enable_reranking: bool = Field(default=False, description="Enable result reranking")
    rerank_strategy: Optional[str] = Field(default="hybrid", description="Reranking strategy")
    rerank_top_k: Optional[int] = Field(default=None, description="Top-K for reranking")


class PagerankSearchSchema(BaseModel):
    """Schema for pagerank_search operation"""

    seed_entity_ids: List[str] = Field(..., description="Starting entity IDs")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")


class MultihopSearchSchema(BaseModel):
    """Schema for multihop_search operation"""

    seed_entity_ids: List[str] = Field(..., description="Starting entity IDs")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum hops")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")


class FilteredSearchSchema(BaseModel):
    """Schema for filtered_search operation"""

    entity_type: Optional[str] = Field(None, description="Filter by entity type")
    property_filters: Optional[Dict[str, Any]] = Field(None, description="Filter by properties")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")


class TraverseSearchSchema(BaseModel):
    """Schema for traverse_search operation"""

    seed_entity_ids: List[str] = Field(..., description="Starting entity IDs")
    relation_types: Optional[List[str]] = Field(None, description="Filter by relation types")
    max_depth: int = Field(default=2, ge=1, le=5, description="Maximum depth")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")


@register_tool("graph_search")
class GraphSearchTool(BaseTool):
    """
    Knowledge Graph Search Tool

    Powerful search tool for querying knowledge graphs with multiple search modes:

    1. **Vector Search** - Find semantically similar entities
    2. **Graph Search** - Explore graph structure from seed entities
    3. **Hybrid Search** - Combine vector similarity with graph structure
    4. **PageRank** - Find important/influential entities
    5. **Multi-Hop** - Find entities within N hops
    6. **Filtered** - Precise filtering by properties
    7. **Traverse** - Pattern-based graph traversal

    Example Usage:
        ```python
        # Vector search
        results = tool.execute({
            "mode": "vector",
            "query": "machine learning researchers",
            "max_results": 10
        })

        # Hybrid search
        results = tool.execute({
            "mode": "hybrid",
            "query": "AI research",
            "seed_entity_ids": ["person_1"],
            "vector_weight": 0.6,
            "graph_weight": 0.4
        })

        # PageRank
        results = tool.execute({
            "mode": "pagerank",
            "seed_entity_ids": ["important_node"],
            "max_results": 20
        })

        # Filtered search
        results = tool.execute({
            "mode": "filtered",
            "entity_type": "Person",
            "property_filters": {"role": "Engineer", "experience": "Senior"}
        })
        ```
    """

    name: str = "graph_search"
    description: str = """Search knowledge graphs with multiple powerful search modes.

    This tool enables sophisticated graph querying including:
    - Semantic similarity search (vector embeddings)
    - Graph structure exploration
    - Hybrid search combining both approaches
    - Importance ranking (PageRank)
    - Multi-hop neighbor discovery
    - Property-based filtering
    - Pattern-based traversal

    Use this tool when you need to:
    - Find entities similar to a query
    - Explore relationships in a knowledge graph
    - Find influential entities
    - Discover connections between entities
    - Filter entities by specific criteria
    """

    # Configuration schema
    class Config(BaseSettings):
        """Configuration for the Graph Search Tool
        
        Automatically reads from environment variables with GRAPH_SEARCH_ prefix.
        Example: GRAPH_SEARCH_CACHE_MAX_SIZE -> cache_max_size
        """

        model_config = SettingsConfigDict(env_prefix="GRAPH_SEARCH_")

        cache_max_size: int = Field(
            default=100,
            description="Maximum cache size for retrieval results",
        )
        cache_ttl: int = Field(
            default=300,
            description="Cache time-to-live in seconds",
        )
        default_max_results: int = Field(
            default=10,
            description="Default maximum number of search results",
        )
        default_max_depth: int = Field(
            default=2,
            description="Default maximum traversal depth",
        )

    input_schema: type[BaseModel] = GraphSearchInput

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize Graph Search Tool.

        Args:
            config (Dict, optional): Configuration overrides for Graph Search Tool.
            **kwargs: Additional arguments passed to BaseTool (e.g., tool_name)

        Configuration is automatically loaded by BaseTool from:
        1. Explicit config dict (highest priority)
        2. YAML config files (config/tools/graph_search.yaml)
        3. Environment variables (via dotenv from .env files)
        4. Tool defaults (lowest priority)
        """
        super().__init__(config, **kwargs)

        # Configuration is automatically loaded by BaseTool into self._config_obj
        # Access config via self._config_obj (BaseSettings instance)
        self.config = self._config_obj if self._config_obj else self.Config()

        # Graph store (shared with KG builder)
        self.graph_store = None

        # Search strategies (using _strategy suffix to avoid shadowing public
        # methods)
        self.hybrid_search_strategy = None
        self.pagerank_strategy = None
        self.multihop_strategy = None
        self.filtered_strategy = None
        self.traversal_strategy = None
        self.cache = None

        self._initialized = False

    async def _initialize(self):
        """Lazy initialization of components"""
        if self._initialized:
            return

        # Initialize graph store (use in-memory for now)
        # In production, this would be configurable
        self.graph_store = InMemoryGraphStore()
        await self.graph_store.initialize()

        # Initialize search strategies
        self.hybrid_search_strategy = HybridSearchStrategy(self.graph_store)
        self.pagerank_strategy = PersonalizedPageRank(self.graph_store)
        self.multihop_strategy = MultiHopRetrieval(self.graph_store)
        self.filtered_strategy = FilteredRetrieval(self.graph_store)
        self.traversal_strategy = EnhancedTraversal(self.graph_store)

        # Initialize cache
        self.cache = RetrievalCache(max_size=self.config.cache_max_size, ttl=self.config.cache_ttl)

        # Initialize reranking strategies
        self._rerankers = {
            "text": TextSimilarityReranker(),
            "semantic": SemanticReranker(),
            "structural": StructuralReranker(self.graph_store),
            "hybrid": HybridReranker(self.graph_store),
        }

        self._initialized = True

    async def _execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute graph search

        Args:
            **kwargs: Tool input parameters

        Returns:
            Dictionary with search results
        """
        # Initialize components
        await self._initialize()

        # Parse input
        mode = kwargs.get("mode")
        query = kwargs.get("query")
        query_embedding = kwargs.get("query_embedding")
        seed_entity_ids = kwargs.get("seed_entity_ids")
        entity_type = kwargs.get("entity_type")
        property_filters = kwargs.get("property_filters")
        relation_types = kwargs.get("relation_types")
        max_results = kwargs.get("max_results", 10)
        max_depth = kwargs.get("max_depth", 2)
        vector_threshold = kwargs.get("vector_threshold", 0.0)
        vector_weight = kwargs.get("vector_weight", 0.6)
        graph_weight = kwargs.get("graph_weight", 0.4)
        expand_results = kwargs.get("expand_results", True)
        # use_cache is available in kwargs but not currently used in
        # implementation

        # Reranking parameters
        enable_reranking = kwargs.get("enable_reranking", False)
        rerank_strategy = kwargs.get("rerank_strategy", "text")
        rerank_top_k = kwargs.get("rerank_top_k")

        # Generate query embedding if query provided but no embedding
        if query and not query_embedding:
            # In production, this would use an embedding model
            # For now, create a placeholder embedding
            query_embedding = [0.1] * 128

        try:
            # Adjust max_results for top-K limiting (fetch more, rerank, then
            # limit)
            initial_max_results = max_results
            if enable_reranking and rerank_top_k:
                initial_max_results = max(rerank_top_k, max_results)

            if mode == SearchModeEnum.VECTOR:
                if query_embedding is None:
                    raise ValueError("query_embedding is required for vector search mode")
                results = await self._vector_search(
                    query_embedding,
                    entity_type,
                    initial_max_results,
                    vector_threshold,
                )

            elif mode == SearchModeEnum.GRAPH:
                results = await self._graph_search(seed_entity_ids, max_depth, initial_max_results)

            elif mode == SearchModeEnum.HYBRID:
                results = await self._hybrid_search(
                    query_embedding,
                    seed_entity_ids,
                    entity_type,
                    initial_max_results,
                    max_depth,
                    vector_weight,
                    graph_weight,
                    expand_results,
                    vector_threshold,
                )

            elif mode == SearchModeEnum.PAGERANK:
                results = await self._pagerank_search(seed_entity_ids, initial_max_results)

            elif mode == SearchModeEnum.MULTIHOP:
                results = await self._multihop_search(seed_entity_ids, max_depth, initial_max_results)

            elif mode == SearchModeEnum.FILTERED:
                results = await self._filtered_search(entity_type, property_filters, initial_max_results)

            elif mode == SearchModeEnum.TRAVERSE:
                results = await self._traverse_search(
                    seed_entity_ids,
                    relation_types,
                    max_depth,
                    initial_max_results,
                )

            else:
                return {
                    "success": False,
                    "error": f"Unknown search mode: {mode}",
                }

            # Apply reranking if enabled
            if enable_reranking and results:
                results = await self._apply_reranking(
                    results=results,
                    query=query,
                    query_embedding=query_embedding,
                    strategy=rerank_strategy,
                    max_results=max_results,
                )

            return {
                "success": True,
                "mode": mode,
                "num_results": len(results),
                "results": results,
                "reranked": enable_reranking,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _vector_search(
        self,
        query_embedding: List[float],
        entity_type: Optional[str],
        max_results: int,
        vector_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        if not query_embedding:
            return []

        raw_results = await self.graph_store.vector_search(
            query_embedding=query_embedding,
            entity_type=entity_type,
            max_results=max_results,
            score_threshold=vector_threshold,
        )

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
            }
            for entity, score in raw_results
        ]

    async def _graph_search(
        self,
        seed_entity_ids: Optional[List[str]],
        max_depth: int,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Perform graph structure search"""
        if not seed_entity_ids:
            return []

        config = HybridSearchConfig(
            mode=SearchMode.GRAPH_ONLY,
            max_graph_depth=max_depth,
            max_results=max_results,
        )

        raw_results = await self.hybrid_search_strategy.search(
            query_embedding=[0.0],  # Placeholder
            config=config,
            seed_entity_ids=seed_entity_ids,
        )

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
            }
            for entity, score in raw_results
        ]

    async def _hybrid_search(
        self,
        query_embedding: Optional[List[float]],
        seed_entity_ids: Optional[List[str]],
        entity_type: Optional[str],
        max_results: int,
        max_depth: int,
        vector_weight: float,
        graph_weight: float,
        expand_results: bool,
        vector_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search"""
        if not query_embedding:
            return []

        config = HybridSearchConfig(
            mode=SearchMode.HYBRID,
            vector_weight=vector_weight,
            graph_weight=graph_weight,
            max_results=max_results,
            max_graph_depth=max_depth,
            expand_results=expand_results,
            vector_threshold=vector_threshold,
            entity_type_filter=entity_type,
        )

        raw_results = await self.hybrid_search_strategy.search(
            query_embedding=query_embedding,
            config=config,
            seed_entity_ids=seed_entity_ids,
        )

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
            }
            for entity, score in raw_results
        ]

    async def _pagerank_search(self, seed_entity_ids: Optional[List[str]], max_results: int) -> List[Dict[str, Any]]:
        """Perform PageRank search"""
        if not seed_entity_ids:
            return []

        raw_results = await self.pagerank_strategy.retrieve(seed_entity_ids=seed_entity_ids, max_results=max_results)

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
                "score_type": "pagerank",
            }
            for entity, score in raw_results
        ]

    async def _multihop_search(
        self,
        seed_entity_ids: Optional[List[str]],
        max_depth: int,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Perform multi-hop retrieval"""
        if not seed_entity_ids:
            return []

        raw_results = await self.multihop_strategy.retrieve(
            seed_entity_ids=seed_entity_ids,
            max_hops=max_depth,
            max_results=max_results,
        )

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
                "score_type": "hop_distance",
            }
            for entity, score in raw_results
        ]

    async def _filtered_search(
        self,
        entity_type: Optional[str],
        property_filters: Optional[Dict[str, Any]],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Perform filtered retrieval"""
        raw_results = await self.filtered_strategy.retrieve(
            entity_type=entity_type,
            property_filters=property_filters,
            max_results=max_results,
        )

        return [
            {
                "entity_id": entity.id,
                "entity_type": entity.entity_type,
                "properties": entity.properties,
                "score": score,
            }
            for entity, score in raw_results
        ]

    async def _traverse_search(
        self,
        seed_entity_ids: Optional[List[str]],
        relation_types: Optional[List[str]],
        max_depth: int,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Perform pattern-based traversal"""
        if not seed_entity_ids:
            return []

        pattern = PathPattern(
            relation_types=relation_types,
            max_depth=max_depth,
            allow_cycles=False,
        )

        # Get all paths from traversal
        all_entities = {}
        for seed_id in seed_entity_ids:
            paths = await self.traversal_strategy.traverse_with_pattern(
                start_entity_id=seed_id,
                pattern=pattern,
                max_results=max_results * 2,
            )

            # Extract unique entities
            for path in paths:
                for entity in path.nodes:
                    if entity.id not in all_entities:
                        # Score by path length (shorter is better)
                        all_entities[entity.id] = {
                            "entity": entity,
                            "score": 1.0 / (path.length + 1),
                        }

        # Sort by score and take top results
        sorted_entities = sorted(all_entities.values(), key=lambda x: x["score"], reverse=True)[:max_results]

        return [
            {
                "entity_id": item["entity"].id,
                "entity_type": item["entity"].entity_type,
                "properties": item["entity"].properties,
                "score": item["score"],
                "score_type": "path_length",
            }
            for item in sorted_entities
        ]

    async def _apply_reranking(
        self,
        results: List[Dict[str, Any]],
        query: Optional[str],
        query_embedding: Optional[List[float]],
        strategy: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Apply reranking to search results

        Args:
            results: Initial search results (list of dicts)
            query: Query text
            query_embedding: Query embedding vector
            strategy: Reranking strategy name
            max_results: Final number of results to return

        Returns:
            Reranked and limited results
        """
        if not results:
            return results

        # Convert result dicts to Entity objects
        entities = []
        for result in results:
            entity = Entity(
                id=result["entity_id"],
                entity_type=result["entity_type"],
                properties=result["properties"],
                embedding=result.get("embedding"),  # May be None
            )
            entities.append(entity)

        # Get reranker strategy
        reranker_strategy = self._rerankers.get(strategy)
        if not reranker_strategy:
            # Fall back to text similarity if strategy not found
            reranker_strategy = self._rerankers["text"]

        # Create result reranker with single strategy
        reranker = ResultReranker(
            strategies=[reranker_strategy],
            combination_method=ScoreCombinationMethod.WEIGHTED_AVERAGE,
            weights={reranker_strategy.name: 1.0},
        )

        # Rerank entities
        reranked = await reranker.rerank(
            query=query or "",
            entities=entities,
            top_k=max_results,
            query_embedding=query_embedding,
        )

        # Convert back to result dicts
        reranked_results = []
        for entity, rerank_score in reranked:
            # Find original result to preserve additional fields
            original_result = next((r for r in results if r["entity_id"] == entity.id), None)

            if original_result:
                result_dict = original_result.copy()
                # Update score with reranked score
                result_dict["original_score"] = result_dict.get("score", 0.0)
                result_dict["score"] = rerank_score
                result_dict["rerank_score"] = rerank_score
                reranked_results.append(result_dict)

        return reranked_results

    # Public methods for ToolExecutor integration
    async def vector_search(
        self,
        query: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        entity_type: Optional[str] = None,
        max_results: int = 10,
        vector_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """Vector similarity search (public method for ToolExecutor)"""
        await self._initialize()
        if query and not query_embedding:
            query_embedding = [0.1] * 128  # Placeholder
        if query_embedding is None:
            raise ValueError("query_embedding is required for vector search")
        results = await self._vector_search(query_embedding, entity_type, max_results, vector_threshold)
        return {
            "success": True,
            "mode": "vector",
            "num_results": len(results),
            "results": results,
        }

    async def graph_search(
        self,
        seed_entity_ids: List[str],
        max_depth: int = 2,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Graph structure search (public method for ToolExecutor)"""
        await self._initialize()
        results = await self._graph_search(seed_entity_ids, max_depth, max_results)
        return {
            "success": True,
            "mode": "graph",
            "num_results": len(results),
            "results": results,
        }

    async def hybrid_search(
        self,
        query: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        seed_entity_ids: Optional[List[str]] = None,
        entity_type: Optional[str] = None,
        max_results: int = 10,
        max_depth: int = 2,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        expand_results: bool = True,
        vector_threshold: float = 0.0,
    ) -> Dict[str, Any]:
        """Hybrid search (public method for ToolExecutor)"""
        await self._initialize()
        if query and not query_embedding:
            query_embedding = [0.1] * 128  # Placeholder
        results = await self._hybrid_search(
            query_embedding,
            seed_entity_ids,
            entity_type,
            max_results,
            max_depth,
            vector_weight,
            graph_weight,
            expand_results,
            vector_threshold,
        )
        return {
            "success": True,
            "mode": "hybrid",
            "num_results": len(results),
            "results": results,
        }

    async def pagerank_search(self, seed_entity_ids: List[str], max_results: int = 10) -> Dict[str, Any]:
        """PageRank search (public method for ToolExecutor)"""
        await self._initialize()
        results = await self._pagerank_search(seed_entity_ids, max_results)
        return {
            "success": True,
            "mode": "pagerank",
            "num_results": len(results),
            "results": results,
        }

    async def multihop_search(
        self,
        seed_entity_ids: List[str],
        max_depth: int = 2,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Multi-hop search (public method for ToolExecutor)"""
        await self._initialize()
        results = await self._multihop_search(seed_entity_ids, max_depth, max_results)
        return {
            "success": True,
            "mode": "multihop",
            "num_results": len(results),
            "results": results,
        }

    async def filtered_search(
        self,
        entity_type: Optional[str] = None,
        property_filters: Optional[Dict[str, Any]] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Filtered search (public method for ToolExecutor)"""
        await self._initialize()
        results = await self._filtered_search(entity_type, property_filters, max_results)
        return {
            "success": True,
            "mode": "filtered",
            "num_results": len(results),
            "results": results,
        }

    async def traverse_search(
        self,
        seed_entity_ids: List[str],
        relation_types: Optional[List[str]] = None,
        max_depth: int = 2,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """Pattern-based traversal (public method for ToolExecutor)"""
        await self._initialize()
        results = await self._traverse_search(seed_entity_ids, relation_types, max_depth, max_results)
        return {
            "success": True,
            "mode": "traverse",
            "num_results": len(results),
            "results": results,
        }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool (public interface)

        Args:
            **kwargs: Tool input parameters

        Returns:
            Dictionary with search results
        """
        return await self._execute(**kwargs)

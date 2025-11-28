"""
Reranking Strategy Implementations

Concrete implementations of reranking strategies for different signals:
- Text similarity (BM25, Jaccard)
- Semantic similarity (vector embeddings)
- Structural importance (PageRank, centrality)
- Hybrid combination
"""

from typing import List, Optional, Dict
import numpy as np

from aiecs.application.knowledge_graph.search.reranker import RerankerStrategy
from aiecs.application.knowledge_graph.search.text_similarity import (
    BM25Scorer,
    jaccard_similarity_text,
    cosine_similarity_text,
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.base import GraphStore


class TextSimilarityReranker(RerankerStrategy):
    """
    Text similarity reranker using BM25 and Jaccard similarity

    Combines BM25 (term-based relevance) and Jaccard (set overlap) scores
    to rerank entities based on text similarity to query.

    Example::

        reranker = TextSimilarityReranker(
            bm25_weight=0.7,
            jaccard_weight=0.3
        )
        scores = await reranker.score("machine learning", entities)
    """

    def __init__(
        self,
        bm25_weight: float = 0.7,
        jaccard_weight: float = 0.3,
        property_keys: Optional[List[str]] = None,
    ):
        """
        Initialize TextSimilarityReranker

        Args:
            bm25_weight: Weight for BM25 scores (0.0-1.0)
            jaccard_weight: Weight for Jaccard scores (0.0-1.0)
            property_keys: Optional list of property keys to search
                          (default: all string properties)
        """
        if abs(bm25_weight + jaccard_weight - 1.0) > 1e-6:
            raise ValueError("bm25_weight + jaccard_weight must equal 1.0")

        self.bm25_weight = bm25_weight
        self.jaccard_weight = jaccard_weight
        self.property_keys = property_keys

    @property
    def name(self) -> str:
        return "text_similarity"

    def _extract_text(self, entity: Entity) -> str:
        """Extract searchable text from entity properties"""
        text_parts = []

        if self.property_keys:
            # Use specified properties only
            for key in self.property_keys:
                value = entity.properties.get(key)
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, (list, tuple)):
                    text_parts.extend(str(v) for v in value if isinstance(v, str))
        else:
            # Use all string properties
            for key, value in entity.properties.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, (list, tuple)):
                    text_parts.extend(str(v) for v in value if isinstance(v, str))

        return " ".join(text_parts)

    async def score(self, query: str, entities: List[Entity], **kwargs) -> List[float]:
        """
        Compute text similarity scores

        Args:
            query: Query text
            entities: Entities to score
            **kwargs: Additional parameters (ignored)

        Returns:
            List of scores (0.0-1.0)
        """
        if not entities:
            return []

        if not query:
            return [0.0] * len(entities)

        # Extract text from entities
        entity_texts = [self._extract_text(entity) for entity in entities]

        # Compute BM25 scores
        corpus = entity_texts
        scorer = BM25Scorer(corpus)
        bm25_scores = scorer.score(query)

        # Normalize BM25 scores to [0, 1]
        if bm25_scores:
            min_bm25 = min(bm25_scores)
            max_bm25 = max(bm25_scores)
            if max_bm25 > min_bm25:
                bm25_normalized = [(s - min_bm25) / (max_bm25 - min_bm25) for s in bm25_scores]
            else:
                bm25_normalized = [1.0] * len(bm25_scores)
        else:
            bm25_normalized = [0.0] * len(entities)

        # Compute Jaccard scores
        jaccard_scores = [jaccard_similarity_text(query, text) for text in entity_texts]

        # Combine scores
        combined_scores = [self.bm25_weight * bm25 + self.jaccard_weight * jaccard for bm25, jaccard in zip(bm25_normalized, jaccard_scores)]

        return combined_scores


class SemanticReranker(RerankerStrategy):
    """
    Semantic reranker using vector cosine similarity

    Uses entity embeddings to compute semantic similarity to query embedding.

    Example::

        reranker = SemanticReranker()
        scores = await reranker.score(
            query="machine learning",
            entities=entities,
            query_embedding=[0.1, 0.2, ...]
        )
    """

    def __init__(self):
        """Initialize SemanticReranker"""

    @property
    def name(self) -> str:
        return "semantic"

    async def score(
        self,
        query: str,
        entities: List[Entity],
        query_embedding: Optional[List[float]] = None,
        **kwargs,
    ) -> List[float]:
        """
        Compute semantic similarity scores

        Args:
            query: Query text (used for fallback if no embedding)
            entities: Entities to score
            query_embedding: Optional query embedding vector
            **kwargs: Additional parameters

        Returns:
            List of scores (0.0-1.0)
        """
        if not entities:
            return []

        if query_embedding is None:
            # No embedding provided, return zero scores
            return [0.0] * len(entities)

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return [0.0] * len(entities)

        scores = []

        for entity in entities:
            if not entity.embedding:
                scores.append(0.0)
                continue

            entity_vec = np.array(entity.embedding, dtype=np.float32)

            # Check dimension compatibility
            if len(query_vec) != len(entity_vec):
                # Dimension mismatch - return zero score
                scores.append(0.0)
                continue

            entity_norm = np.linalg.norm(entity_vec)

            if entity_norm == 0:
                scores.append(0.0)
                continue

            # Cosine similarity
            similarity = np.dot(query_vec, entity_vec) / (query_norm * entity_norm)
            # Normalize to [0, 1] range
            normalized = (similarity + 1) / 2
            scores.append(float(normalized))

        return scores


class StructuralReranker(RerankerStrategy):
    """
    Structural reranker using graph centrality and PageRank

    Scores entities based on their structural importance in the graph.
    Uses PageRank scores and degree centrality.

    Example::

        reranker = StructuralReranker(graph_store)
        scores = await reranker.score("query", entities)
    """

    def __init__(
        self,
        graph_store: GraphStore,
        pagerank_weight: float = 0.7,
        degree_weight: float = 0.3,
        use_cached_scores: bool = True,
    ):
        """
        Initialize StructuralReranker

        Args:
            graph_store: Graph storage backend
            pagerank_weight: Weight for PageRank scores (0.0-1.0)
            degree_weight: Weight for degree centrality (0.0-1.0)
            use_cached_scores: Whether to cache PageRank scores
        """
        if abs(pagerank_weight + degree_weight - 1.0) > 1e-6:
            raise ValueError("pagerank_weight + degree_weight must equal 1.0")

        self.graph_store = graph_store
        self.pagerank_weight = pagerank_weight
        self.degree_weight = degree_weight
        self.use_cached_scores = use_cached_scores
        self._pagerank_cache: Dict[str, float] = {}
        self._degree_cache: Dict[str, int] = {}

    @property
    def name(self) -> str:
        return "structural"

    async def _compute_pagerank_scores(self, entity_ids: List[str]) -> Dict[str, float]:
        """Compute or retrieve cached PageRank scores"""
        # Check cache first
        if self.use_cached_scores:
            cached = {eid: self._pagerank_cache.get(eid, 0.0) for eid in entity_ids}
            if all(score > 0 for score in cached.values()):
                return cached

        # Compute PageRank using PersonalizedPageRank
        from aiecs.application.knowledge_graph.retrieval.retrieval_strategies import (
            PersonalizedPageRank,
        )

        ppr = PersonalizedPageRank(self.graph_store)

        # Use all entities as seeds for global PageRank
        # In practice, you might want to use seed entities from query context
        # get_all_entities is available via PaginationMixinProtocol
        all_entities = await self.graph_store.get_all_entities()  # type: ignore[attr-defined]
        seed_ids = [e.id for e in all_entities[: min(10, len(all_entities))]]

        if not seed_ids:
            return {eid: 0.0 for eid in entity_ids}

        ppr_results = await ppr.retrieve(
            seed_entity_ids=seed_ids,
            max_results=len(entity_ids) * 2,
            alpha=0.15,
        )

        # Create score dictionary
        pagerank_scores = {entity.id: score for entity, score in ppr_results}

        # Normalize to [0, 1]
        if pagerank_scores:
            max_score = max(pagerank_scores.values())
            if max_score > 0:
                pagerank_scores = {eid: score / max_score for eid, score in pagerank_scores.items()}

        # Update cache
        if self.use_cached_scores:
            self._pagerank_cache.update(pagerank_scores)

        return {eid: pagerank_scores.get(eid, 0.0) for eid in entity_ids}

    async def _compute_degree_scores(self, entity_ids: List[str]) -> Dict[str, float]:
        """Compute degree centrality scores"""
        # Check cache
        if self.use_cached_scores:
            cached = {eid: self._degree_cache.get(eid, 0) for eid in entity_ids}
            if all(deg >= 0 for deg in cached.values()):
                degrees = cached
            else:
                degrees = {}
        else:
            degrees = {}

        # Compute missing degrees
        for entity_id in entity_ids:
            if entity_id not in degrees:
                neighbors_out = await self.graph_store.get_neighbors(entity_id, direction="outgoing")
                neighbors_in = await self.graph_store.get_neighbors(entity_id, direction="incoming")
                degree = len(neighbors_out) + len(neighbors_in)
                degrees[entity_id] = degree
                if self.use_cached_scores:
                    self._degree_cache[entity_id] = degree

        # Normalize to [0, 1]
        if degrees:
            max_degree = max(degrees.values())
            if max_degree > 0:
                return {eid: deg / max_degree for eid, deg in degrees.items()}

        return {eid: 0.0 for eid in entity_ids}

    async def score(self, query: str, entities: List[Entity], **kwargs) -> List[float]:
        """
        Compute structural importance scores

        Args:
            query: Query text (not used, but required by interface)
            entities: Entities to score
            **kwargs: Additional parameters

        Returns:
            List of scores (0.0-1.0)
        """
        if not entities:
            return []

        entity_ids = [entity.id for entity in entities]

        # Compute PageRank scores
        pagerank_scores = await self._compute_pagerank_scores(entity_ids)

        # Compute degree centrality scores
        degree_scores = await self._compute_degree_scores(entity_ids)

        # Combine scores
        combined_scores = [self.pagerank_weight * pagerank_scores.get(entity.id, 0.0) + self.degree_weight * degree_scores.get(entity.id, 0.0) for entity in entities]

        return combined_scores


class HybridReranker(RerankerStrategy):
    """
    Hybrid reranker combining multiple signals

    Combines text similarity, semantic similarity, and structural importance
    into a single score.

    Example::

        reranker = HybridReranker(
            graph_store=store,
            text_weight=0.4,
            semantic_weight=0.4,
            structural_weight=0.2
        )
        scores = await reranker.score(
            query="machine learning",
            entities=entities,
            query_embedding=[0.1, 0.2, ...]
        )
    """

    def __init__(
        self,
        graph_store: GraphStore,
        text_weight: float = 0.4,
        semantic_weight: float = 0.4,
        structural_weight: float = 0.2,
    ):
        """
        Initialize HybridReranker

        Args:
            graph_store: Graph storage backend
            text_weight: Weight for text similarity (0.0-1.0)
            semantic_weight: Weight for semantic similarity (0.0-1.0)
            structural_weight: Weight for structural importance (0.0-1.0)
        """
        if abs(text_weight + semantic_weight + structural_weight - 1.0) > 1e-6:
            raise ValueError("Weights must sum to 1.0")

        self.graph_store = graph_store
        self.text_weight = text_weight
        self.semantic_weight = semantic_weight
        self.structural_weight = structural_weight

        # Initialize sub-strategies
        self.text_reranker = TextSimilarityReranker()
        self.semantic_reranker = SemanticReranker()
        self.structural_reranker = StructuralReranker(graph_store)

    @property
    def name(self) -> str:
        return "hybrid"

    async def score(
        self,
        query: str,
        entities: List[Entity],
        query_embedding: Optional[List[float]] = None,
        **kwargs,
    ) -> List[float]:
        """
        Compute hybrid scores combining all signals

        Args:
            query: Query text
            entities: Entities to score
            query_embedding: Optional query embedding vector
            **kwargs: Additional parameters

        Returns:
            List of scores (0.0-1.0)
        """
        if not entities:
            return []

        # Get scores from each strategy
        text_scores = await self.text_reranker.score(query, entities, **kwargs)
        semantic_scores = await self.semantic_reranker.score(query, entities, query_embedding=query_embedding, **kwargs)
        structural_scores = await self.structural_reranker.score(query, entities, **kwargs)

        # Combine scores
        combined_scores = [
            self.text_weight * text + self.semantic_weight * semantic + self.structural_weight * structural for text, semantic, structural in zip(text_scores, semantic_scores, structural_scores)
        ]

        return combined_scores


class CrossEncoderReranker(RerankerStrategy):
    """
    Cross-encoder reranker using transformer models (optional)

    Uses a cross-encoder model to compute semantic relevance between
    query and entity text. More accurate but slower than bi-encoder.

    Note: This is a placeholder implementation. For production use,
    integrate with a cross-encoder model library (e.g., sentence-transformers).

    Example::

        reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
        scores = await reranker.score("machine learning", entities)
    """

    def __init__(self, model_name: Optional[str] = None, use_gpu: bool = False):
        """
        Initialize CrossEncoderReranker

        Args:
            model_name: Optional model name (default: None, uses placeholder)
            use_gpu: Whether to use GPU (if available)
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self._model = None

    @property
    def name(self) -> str:
        return "cross_encoder"

    def _extract_text(self, entity: Entity) -> str:
        """Extract text from entity for encoding"""
        text_parts = []
        for key, value in entity.properties.items():
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, (list, tuple)):
                text_parts.extend(str(v) for v in value if isinstance(v, str))
        return " ".join(text_parts)

    async def score(self, query: str, entities: List[Entity], **kwargs) -> List[float]:
        """
        Compute cross-encoder scores

        Args:
            query: Query text
            entities: Entities to score
            **kwargs: Additional parameters

        Returns:
            List of scores (0.0-1.0)
        """
        if not entities:
            return []

        if not query:
            return [0.0] * len(entities)

        # Placeholder implementation
        # In production, this would use a cross-encoder model:
        #
        # if self._model is None:
        #     from sentence_transformers import CrossEncoder
        #     self._model = CrossEncoder(self.model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2")
        #
        # entity_texts = [self._extract_text(entity) for entity in entities]
        # pairs = [[query, text] for text in entity_texts]
        # scores = self._model.predict(pairs)
        #
        # # Normalize to [0, 1]
        # scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-10)
        # return scores.tolist()

        # Fallback: Use cosine similarity as placeholder
        entity_texts = [self._extract_text(entity) for entity in entities]
        scores = [cosine_similarity_text(query, text) for text in entity_texts]

        return scores

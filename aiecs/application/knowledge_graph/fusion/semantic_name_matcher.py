"""
Semantic Name Matcher for Knowledge Graph Entity Fusion.

Provides embedding-based semantic matching for entity names using LLM embeddings.
Supports configurable similarity thresholds and caching to minimize API calls.
"""

import asyncio
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import OrderedDict
import threading

from aiecs.llm import LLMClientFactory, AIProvider
from aiecs.llm.protocols import LLMClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class SemanticMatchResult:
    """Result of semantic name matching."""
    name1: str
    name2: str
    similarity: float
    is_match: bool
    embedding1: Optional[List[float]] = None
    embedding2: Optional[List[float]] = None


@dataclass
class EmbeddingCacheConfig:
    """Configuration for embedding cache."""
    max_size: int = 10000
    ttl_seconds: Optional[int] = None  # None = no TTL


@dataclass
class SemanticMatcherConfig:
    """Configuration for SemanticNameMatcher."""
    # Similarity threshold for match
    similarity_threshold: float = 0.85
    # LLM provider for embeddings
    embedding_provider: str = "OpenAI"
    # Embedding model name (optional, uses provider default)
    embedding_model: Optional[str] = None
    # Cache configuration
    cache_max_size: int = 10000
    # Batch size for embedding API calls
    batch_size: int = 100
    # Enable/disable semantic matching
    enabled: bool = True


class LRUEmbeddingCache:
    """
    Thread-safe LRU cache for name embeddings.

    Provides O(1) lookup and insertion with configurable max size.
    Uses OrderedDict for LRU ordering.
    """

    def __init__(self, max_size: int = 10000):
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[List[float]]:
        """Get embedding from cache. Returns None if not found."""
        normalized_key = key.lower().strip()
        with self._lock:
            if normalized_key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(normalized_key)
                self._hits += 1
                return self._cache[normalized_key]
            self._misses += 1
            return None

    def set(self, key: str, embedding: List[float]) -> None:
        """Set embedding in cache. Evicts LRU entry if full."""
        normalized_key = key.lower().strip()
        with self._lock:
            if normalized_key in self._cache:
                # Update the embedding value and move to end (most recently used)
                self._cache[normalized_key] = embedding
                self._cache.move_to_end(normalized_key)
            else:
                if len(self._cache) >= self._max_size:
                    # Evict least recently used
                    self._cache.popitem(last=False)
                self._cache[normalized_key] = embedding

    def invalidate(self, key: str) -> bool:
        """Remove entry from cache. Returns True if entry was removed."""
        normalized_key = key.lower().strip()
        with self._lock:
            if normalized_key in self._cache:
                del self._cache[normalized_key]
                return True
            return False

    def invalidate_many(self, keys: List[str]) -> int:
        """Remove multiple entries from cache. Returns count of removed."""
        removed = 0
        with self._lock:
            for key in keys:
                normalized_key = key.lower().strip()
                if normalized_key in self._cache:
                    del self._cache[normalized_key]
                    removed += 1
        return removed

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def size(self) -> int:
        """Return number of entries in cache."""
        with self._lock:
            return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
            }

    def contains(self, key: str) -> bool:
        """Check if key exists in cache."""
        normalized_key = key.lower().strip()
        with self._lock:
            return normalized_key in self._cache

    def get_all_keys(self) -> List[str]:
        """Get all keys in cache (for debugging/testing)."""
        with self._lock:
            return list(self._cache.keys())


class SemanticNameMatcher:
    """
    Semantic name matcher using LLM embeddings.

    Provides embedding-based entity name matching with:
    - Configurable similarity threshold
    - LRU embedding cache to minimize API calls
    - Batch embedding generation
    - Cosine similarity calculation

    Example:
        ```python
        config = SemanticMatcherConfig(similarity_threshold=0.85)
        matcher = SemanticNameMatcher(config)

        # Check if two names match semantically
        result = await matcher.match("Albert Einstein", "A. Einstein")
        if result.is_match:
            print(f"Match! Similarity: {result.similarity}")

        # Get embedding for a name (cached)
        embedding = await matcher.get_embedding("Albert Einstein")
        ```
    """

    def __init__(
        self,
        config: Optional[SemanticMatcherConfig] = None,
        llm_client: Optional[LLMClientProtocol] = None,
    ):
        """
        Initialize semantic name matcher.

        Args:
            config: Configuration for matching behavior
            llm_client: Optional LLM client for embeddings (uses factory if not provided)
        """
        self._config = config or SemanticMatcherConfig()
        self._cache = LRUEmbeddingCache(max_size=self._config.cache_max_size)
        self._llm_client = llm_client
        self._lock = asyncio.Lock()

    async def _get_llm_client(self) -> LLMClientProtocol:
        """Get or create LLM client for embeddings."""
        async with self._lock:
            if self._llm_client is None:
                try:
                    provider = AIProvider(self._config.embedding_provider)
                except ValueError:
                    # Try as custom provider
                    provider = self._config.embedding_provider
                self._llm_client = LLMClientFactory.get_client(provider)
            return self._llm_client

    async def get_embedding(self, name: str) -> List[float]:
        """
        Get embedding for a name.

        Uses cache to minimize API calls. Generates new embedding if not cached.

        Args:
            name: Name to embed

        Returns:
            Embedding vector
        """
        if not self._config.enabled:
            return []

        # Check cache first
        cached = self._cache.get(name)
        if cached is not None:
            return cached

        # Generate embedding
        client = await self._get_llm_client()
        try:
            embeddings = await client.get_embeddings(
                [name],
                model=self._config.embedding_model,
            )
            if embeddings and embeddings[0]:
                embedding = embeddings[0]
                self._cache.set(name, embedding)
                return embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding for '{name}': {e}")

        return []

    async def get_embeddings_batch(
        self, names: List[str]
    ) -> Dict[str, List[float]]:
        """
        Get embeddings for multiple names in batch.

        Uses cache for already-embedded names and batches API calls for new ones.

        Args:
            names: List of names to embed

        Returns:
            Dict mapping name to embedding
        """
        if not self._config.enabled:
            return {name: [] for name in names}

        results: Dict[str, List[float]] = {}
        names_to_embed: List[str] = []

        # Check cache for each name
        for name in names:
            cached = self._cache.get(name)
            if cached is not None:
                results[name] = cached
            else:
                names_to_embed.append(name)

        # Batch embed uncached names
        if names_to_embed:
            client = await self._get_llm_client()
            try:
                # Process in batches
                for i in range(0, len(names_to_embed), self._config.batch_size):
                    batch = names_to_embed[i:i + self._config.batch_size]
                    embeddings = await client.get_embeddings(
                        batch,
                        model=self._config.embedding_model,
                    )

                    for name, embedding in zip(batch, embeddings):
                        if embedding:
                            self._cache.set(name, embedding)
                            results[name] = embedding
                        else:
                            results[name] = []
            except Exception as e:
                logger.warning(f"Failed to generate batch embeddings: {e}")
                for name in names_to_embed:
                    results[name] = []

        return results

    def cosine_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        if not embedding1 or not embedding2:
            return 0.0

        if len(embedding1) != len(embedding2):
            logger.warning(
                f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}"
            )
            return 0.0

        # Calculate dot product and magnitudes
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    async def match(
        self,
        name1: str,
        name2: str,
        threshold: Optional[float] = None,
    ) -> SemanticMatchResult:
        """
        Check if two names match semantically.

        Args:
            name1: First name
            name2: Second name
            threshold: Override similarity threshold (uses config default if None)

        Returns:
            SemanticMatchResult with similarity score and match status
        """
        effective_threshold = threshold or self._config.similarity_threshold

        if not self._config.enabled:
            return SemanticMatchResult(
                name1=name1,
                name2=name2,
                similarity=0.0,
                is_match=False,
            )

        # Get embeddings
        embedding1 = await self.get_embedding(name1)
        embedding2 = await self.get_embedding(name2)

        # Calculate similarity
        similarity = self.cosine_similarity(embedding1, embedding2)
        is_match = similarity >= effective_threshold

        return SemanticMatchResult(
            name1=name1,
            name2=name2,
            similarity=similarity,
            is_match=is_match,
            embedding1=embedding1,
            embedding2=embedding2,
        )

    async def find_best_match(
        self,
        name: str,
        candidates: List[str],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, float]]:
        """
        Find the best semantic match for a name among candidates.

        Args:
            name: Name to match
            candidates: List of candidate names
            threshold: Minimum similarity threshold

        Returns:
            Tuple of (best_match_name, similarity) or None if no match above threshold
        """
        if not candidates or not self._config.enabled:
            return None

        effective_threshold = threshold or self._config.similarity_threshold

        # Get embedding for target name
        target_embedding = await self.get_embedding(name)
        if not target_embedding:
            return None

        # Get embeddings for all candidates in batch
        candidate_embeddings = await self.get_embeddings_batch(candidates)

        # Find best match
        best_match = None
        best_similarity = effective_threshold

        for candidate in candidates:
            candidate_embedding = candidate_embeddings.get(candidate, [])
            if candidate_embedding:
                similarity = self.cosine_similarity(target_embedding, candidate_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = candidate

        if best_match:
            return (best_match, best_similarity)
        return None

    def invalidate_cache(self, name: str) -> bool:
        """
        Invalidate cache entry for a name.

        Args:
            name: Name to invalidate

        Returns:
            True if entry was removed
        """
        return self._cache.invalidate(name)

    def invalidate_cache_many(self, names: List[str]) -> int:
        """
        Invalidate cache entries for multiple names.

        Args:
            names: Names to invalidate

        Returns:
            Number of entries removed
        """
        return self._cache.invalidate_many(names)

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()

    @property
    def cache(self) -> LRUEmbeddingCache:
        """Access to the embedding cache."""
        return self._cache

    @property
    def config(self) -> SemanticMatcherConfig:
        """Get current configuration."""
        return self._config





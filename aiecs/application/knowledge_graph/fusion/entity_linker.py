"""
Entity Linker

Links newly extracted entities to existing entities in the knowledge graph.
"""

from typing import List, Optional, TYPE_CHECKING
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.base import GraphStore
from aiecs.infrastructure.graph_storage.tenant import TenantContext

if TYPE_CHECKING:
    from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
        SimilarityPipeline,
    )


class EntityLinker:
    """
    Link new entities to existing entities in the graph

    When extracting entities from new documents, many entities may already exist
    in the knowledge graph. This class identifies such matches and links them,
    preventing duplication across the entire graph.

    Features:
    - Exact ID matching
    - Name-based fuzzy matching
    - Embedding-based similarity search
    - Type-aware linking
    - Confidence scoring

    Workflow:
    1. For each new entity, search graph for similar existing entities
    2. If match found, return existing entity ID (link)
    3. If no match, entity is new and should be added

    Example:
        ```python
        linker = EntityLinker(graph_store, similarity_threshold=0.85)

        new_entity = Entity(type="Person", properties={"name": "Alice Smith"})

        # Check if Alice already exists
        link_result = await linker.link_entity(new_entity)

        if link_result.linked:
            print(f"Linked to existing entity: {link_result.existing_entity.id}")
            # Use existing entity instead of creating new one
        else:
            print("New entity - add to graph")
            # Add new_entity to graph
        ```
    """

    def __init__(
        self,
        graph_store: GraphStore,
        similarity_threshold: float = 0.85,
        use_embeddings: bool = True,
        embedding_threshold: float = 0.90,
        similarity_pipeline: Optional["SimilarityPipeline"] = None,
    ):
        """
        Initialize entity linker

        Args:
            graph_store: Graph storage to search for existing entities
            similarity_threshold: Minimum similarity to link entities (0.0-1.0)
            use_embeddings: Use embedding similarity for matching
            embedding_threshold: Minimum embedding similarity for linking (0.0-1.0)
            similarity_pipeline: Optional SimilarityPipeline for enhanced matching
        """
        self.graph_store = graph_store
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings
        self.embedding_threshold = embedding_threshold
        self._similarity_pipeline = similarity_pipeline

    async def link_entity(
        self,
        new_entity: Entity,
        candidate_limit: int = 10,
        context: Optional[TenantContext] = None,
    ) -> "LinkResult":
        """
        Link a new entity to existing entity in graph (if match found)

        **Tenant Isolation**: When context is provided, linking only searches for
        matches within the specified tenant. Cross-tenant linking is prevented.

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum number of candidates to consider
            context: Optional tenant context for multi-tenant isolation

        Returns:
            LinkResult with linking decision and matched entity (if any)
        """
        # Try exact ID match first
        existing = await self.graph_store.get_entity(new_entity.id, context=context)
        if existing:
            # Validate tenant match if context provided
            if context and existing.tenant_id != context.tenant_id:
                # ID match but wrong tenant - treat as not linked
                pass
            else:
                return LinkResult(
                    linked=True,
                    existing_entity=existing,
                    new_entity=new_entity,
                    similarity=1.0,
                    link_type="exact_id",
                )

        # Try embedding-based search (fast, semantic)
        if self.use_embeddings and new_entity.embedding:
            link_result = await self._link_by_embedding(
                new_entity, candidate_limit, context
            )
            if link_result.linked:
                return link_result

        # Try name-based search (fallback)
        link_result = await self._link_by_name(new_entity, candidate_limit, context)

        return link_result

    async def link_entities(
        self,
        new_entities: List[Entity],
        candidate_limit: int = 10,
        context: Optional[TenantContext] = None,
    ) -> List["LinkResult"]:
        """
        Link multiple entities in batch

        **Tenant Isolation**: When context is provided, all linking operations
        are scoped to the specified tenant.

        Args:
            new_entities: List of entities to link
            candidate_limit: Maximum candidates per entity
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of LinkResult objects (one per input entity)
        """
        results = []
        for entity in new_entities:
            result = await self.link_entity(entity, candidate_limit, context)
            results.append(result)
        return results

    async def _link_by_embedding(
        self,
        new_entity: Entity,
        candidate_limit: int,
        context: Optional[TenantContext] = None,
    ) -> "LinkResult":
        """
        Link entity using embedding similarity search

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum candidates to consider
            context: Optional tenant context for scoping search

        Returns:
            LinkResult
        """
        if not new_entity.embedding:
            return LinkResult(linked=False, new_entity=new_entity)

        try:
            # Vector search in graph (with tenant context)
            candidates = await self.graph_store.vector_search(
                query_embedding=new_entity.embedding,
                entity_type=new_entity.entity_type,
                max_results=candidate_limit,
                score_threshold=self.embedding_threshold,
                context=context,
            )

            if not candidates:
                return LinkResult(linked=False, new_entity=new_entity)

            # Get best candidate
            best_entity, best_score = candidates[0]

            # Check if score meets threshold
            if best_score >= self.embedding_threshold:
                # Also verify name similarity (sanity check)
                name_match = self._check_name_similarity(new_entity, best_entity)

                if name_match or best_score >= 0.95:  # High embedding score = trust it
                    return LinkResult(
                        linked=True,
                        existing_entity=best_entity,
                        new_entity=new_entity,
                        similarity=best_score,
                        link_type="embedding",
                    )

        except NotImplementedError:
            # Graph store doesn't support vector search
            pass
        except Exception as e:
            # Log error but don't fail
            print(f"Warning: Embedding search failed: {e}")

        return LinkResult(linked=False, new_entity=new_entity)

    async def _link_by_name(
        self,
        new_entity: Entity,
        candidate_limit: int,
        context: Optional[TenantContext] = None,
    ) -> "LinkResult":
        """
        Link entity using name-based matching

        Uses text search when available for efficient name-based queries,
        otherwise falls back to candidate enumeration and fuzzy matching.

        Strategy:
        1. Try text_search if available (most efficient for name queries)
        2. Otherwise get candidate entities and compare names
        3. Return best match if above threshold

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum candidates to consider
            context: Optional tenant context for scoping search

        Returns:
            LinkResult
        """
        new_name = self._get_entity_name(new_entity)
        if not new_name:
            return LinkResult(linked=False, new_entity=new_entity)

        try:
            # Try text_search first if available (optimized for name-based queries)
            if hasattr(self.graph_store, "text_search"):
                try:
                    # Use text_search to find entities with similar names
                    # This is more efficient than enumerating all candidates
                    text_results = await self.graph_store.text_search(
                        query_text=new_name,
                        entity_type=new_entity.entity_type,
                        max_results=candidate_limit,
                        score_threshold=self.similarity_threshold,
                        method="levenshtein",  # Good for name matching
                        context=context,
                    )

                    if text_results:
                        # Get best match from text search results
                        best_entity, best_score = text_results[0]
                        
                        # Verify name similarity meets threshold (text_search may use different scoring)
                        candidate_name = self._get_entity_name(best_entity)
                        if candidate_name:
                            # Recompute similarity using our method for consistency
                            name_similarity = self._name_similarity(
                                new_name, candidate_name, entity_type=new_entity.entity_type
                            )
                            
                            if name_similarity >= self.similarity_threshold:
                                return LinkResult(
                                    linked=True,
                                    existing_entity=best_entity,
                                    new_entity=new_entity,
                                    similarity=name_similarity,
                                    link_type="name",
                                )
                except (ValueError, TypeError, NotImplementedError):
                    # text_search may not be available or may not support this pattern
                    # Fall through to candidate enumeration approach
                    pass

            # Fallback: Get candidate entities and compare names manually
            candidates = await self._get_candidate_entities(
                new_entity.entity_type, candidate_limit, context
            )

            if not candidates:
                return LinkResult(linked=False, new_entity=new_entity)

            # Find best match
            best_match = None
            best_score = 0.0

            for candidate in candidates:
                candidate_name = self._get_entity_name(candidate)
                if candidate_name:
                    score = self._name_similarity(
                        new_name, candidate_name, entity_type=new_entity.entity_type
                    )
                    if score > best_score:
                        best_score = score
                        best_match = candidate

            # Check threshold
            if best_score >= self.similarity_threshold and best_match:
                return LinkResult(
                    linked=True,
                    existing_entity=best_match,
                    new_entity=new_entity,
                    similarity=best_score,
                    link_type="name",
                )

        except Exception as e:
            print(f"Warning: Name-based linking failed: {e}")

        return LinkResult(linked=False, new_entity=new_entity)

    async def _get_candidate_entities(
        self, entity_type: str, limit: int, context: Optional[TenantContext] = None
    ) -> List[Entity]:
        """
        Get candidate entities for linking

        Retrieves candidate entities of the specified type for entity linking operations.
        Uses efficient methods when available (indexed search, text search) and falls
        back to enumeration when needed.

        Args:
            entity_type: Entity type to filter by
            limit: Maximum candidates to return
            context: Optional tenant context for scoping search

        Returns:
            List of candidate entities (filtered by tenant if context provided)
        """
        try:
            # Try to use get_all_entities() if available (most efficient for type filtering)
            if hasattr(self.graph_store, "get_all_entities"):
                candidates = await self.graph_store.get_all_entities(
                    entity_type=entity_type,
                    limit=limit,
                    context=context,
                )
                return candidates

            # Fallback: Try to use text_search with empty query to get entities by type
            # This works if text_search supports entity_type filtering
            if hasattr(self.graph_store, "text_search"):
                try:
                    # Use text_search with empty query to get entities by type
                    # Some implementations may support this pattern
                    results = await self.graph_store.text_search(
                        query_text="",  # Empty query to get all
                        entity_type=entity_type,
                        max_results=limit,
                        score_threshold=0.0,
                        method="bm25",
                        context=context,
                    )
                    # Extract entities from (entity, score) tuples
                    return [entity for entity, _ in results]
                except (ValueError, TypeError):
                    # text_search may not support empty queries, continue to next fallback
                    pass

            # Last resort: If store has a way to enumerate entities, we could iterate
            # but this is inefficient, so we return empty and rely on embedding search
            # In production backends (SQLite, PostgreSQL), get_all_entities should be implemented
            return []

        except Exception as e:
            # Log error but don't fail - entity linking can fall back to embedding search
            print(f"Warning: Candidate entity retrieval failed: {e}")
            return []

    def _check_name_similarity(self, entity1: Entity, entity2: Entity) -> bool:
        """
        Quick name similarity check

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            True if names are similar enough
        """
        name1 = self._get_entity_name(entity1)
        name2 = self._get_entity_name(entity2)

        if not name1 or not name2:
            return False

        return self._name_similarity(
            name1, name2, entity_type=entity1.entity_type
        ) >= self.similarity_threshold

    def _get_entity_name(self, entity: Entity) -> str:
        """Extract entity name from properties"""
        return entity.properties.get("name") or entity.properties.get("title") or entity.properties.get("text") or ""

    def _name_similarity(
        self, name1: str, name2: str, entity_type: Optional[str] = None
    ) -> float:
        """
        Compute name similarity using fuzzy matching or SimilarityPipeline.

        Args:
            name1: First name
            name2: Second name
            entity_type: Entity type for per-type configuration (optional)

        Returns:
            Similarity score (0.0-1.0)
        """
        # Use pipeline if available (synchronous version for compatibility)
        if self._similarity_pipeline is not None:
            return self._similarity_pipeline.compute_similarity_sync(
                name1=name1,
                name2=name2,
                entity_type=entity_type,
            )

        from difflib import SequenceMatcher

        # Normalize
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        # Exact match
        if n1 == n2:
            return 1.0

        # Substring match
        if n1 in n2 or n2 in n1:
            return 0.95

        # Fuzzy match
        return SequenceMatcher(None, n1, n2).ratio()

    async def _name_similarity_async(
        self, name1: str, name2: str, entity_type: Optional[str] = None
    ) -> float:
        """
        Compute name similarity using SimilarityPipeline (async version).

        Args:
            name1: First name
            name2: Second name
            entity_type: Entity type for per-type configuration (optional)

        Returns:
            Similarity score (0.0-1.0)
        """
        if self._similarity_pipeline is not None:
            result = await self._similarity_pipeline.compute_similarity(
                name1=name1,
                name2=name2,
                entity_type=entity_type,
            )
            return result.final_score

        # Fallback to sync version
        return self._name_similarity(name1, name2, entity_type)

    def set_similarity_pipeline(self, pipeline: "SimilarityPipeline") -> None:
        """
        Set the similarity pipeline for enhanced matching.

        Args:
            pipeline: SimilarityPipeline instance
        """
        self._similarity_pipeline = pipeline

    @property
    def similarity_pipeline(self) -> Optional["SimilarityPipeline"]:
        """Get the current similarity pipeline."""
        return self._similarity_pipeline


class LinkResult:
    """
    Result of entity linking operation

    Attributes:
        linked: Whether a link was found
        existing_entity: The existing entity (if linked)
        new_entity: The new entity being linked
        similarity: Similarity score (0.0-1.0)
        link_type: Type of link ("exact_id", "embedding", "name", "none")
    """

    def __init__(
        self,
        linked: bool,
        new_entity: Entity,
        existing_entity: Optional[Entity] = None,
        similarity: float = 0.0,
        link_type: str = "none",
    ):
        self.linked = linked
        self.existing_entity = existing_entity
        self.new_entity = new_entity
        self.similarity = similarity
        self.link_type = link_type

    def __repr__(self) -> str:
        if self.linked:
            return f"LinkResult(linked=True, type={self.link_type}, similarity={self.similarity:.2f})"
        return "LinkResult(linked=False)"

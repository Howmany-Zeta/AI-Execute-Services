"""
Entity Linker

Links newly extracted entities to existing entities in the knowledge graph.
"""

from typing import List, Optional
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.base import GraphStore


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
    ):
        """
        Initialize entity linker

        Args:
            graph_store: Graph storage to search for existing entities
            similarity_threshold: Minimum similarity to link entities (0.0-1.0)
            use_embeddings: Use embedding similarity for matching
            embedding_threshold: Minimum embedding similarity for linking (0.0-1.0)
        """
        self.graph_store = graph_store
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings
        self.embedding_threshold = embedding_threshold

    async def link_entity(self, new_entity: Entity, candidate_limit: int = 10) -> "LinkResult":
        """
        Link a new entity to existing entity in graph (if match found)

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum number of candidates to consider

        Returns:
            LinkResult with linking decision and matched entity (if any)
        """
        # Try exact ID match first
        existing = await self.graph_store.get_entity(new_entity.id)
        if existing:
            return LinkResult(
                linked=True,
                existing_entity=existing,
                new_entity=new_entity,
                similarity=1.0,
                link_type="exact_id",
            )

        # Try embedding-based search (fast, semantic)
        if self.use_embeddings and new_entity.embedding:
            link_result = await self._link_by_embedding(new_entity, candidate_limit)
            if link_result.linked:
                return link_result

        # Try name-based search (fallback)
        link_result = await self._link_by_name(new_entity, candidate_limit)

        return link_result

    async def link_entities(self, new_entities: List[Entity], candidate_limit: int = 10) -> List["LinkResult"]:
        """
        Link multiple entities in batch

        Args:
            new_entities: List of entities to link
            candidate_limit: Maximum candidates per entity

        Returns:
            List of LinkResult objects (one per input entity)
        """
        results = []
        for entity in new_entities:
            result = await self.link_entity(entity, candidate_limit)
            results.append(result)
        return results

    async def _link_by_embedding(self, new_entity: Entity, candidate_limit: int) -> "LinkResult":
        """
        Link entity using embedding similarity search

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum candidates to consider

        Returns:
            LinkResult
        """
        if not new_entity.embedding:
            return LinkResult(linked=False, new_entity=new_entity)

        try:
            # Vector search in graph
            candidates = await self.graph_store.vector_search(
                query_embedding=new_entity.embedding,
                entity_type=new_entity.entity_type,
                max_results=candidate_limit,
                score_threshold=self.embedding_threshold,
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

    async def _link_by_name(self, new_entity: Entity, candidate_limit: int) -> "LinkResult":
        """
        Link entity using name-based matching

        This is slower than embedding search but works without embeddings.

        Strategy:
        1. Get all entities of same type (if feasible)
        2. Compare names using fuzzy matching
        3. Return best match if above threshold

        Args:
            new_entity: Entity to link
            candidate_limit: Maximum candidates to consider

        Returns:
            LinkResult
        """
        new_name = self._get_entity_name(new_entity)
        if not new_name:
            return LinkResult(linked=False, new_entity=new_entity)

        try:
            # Get candidate entities of same type
            # Note: This is a simplified implementation
            # In production, you'd want an indexed search or LIKE query
            candidates = await self._get_candidate_entities(new_entity.entity_type, candidate_limit)

            if not candidates:
                return LinkResult(linked=False, new_entity=new_entity)

            # Find best match
            best_match = None
            best_score = 0.0

            for candidate in candidates:
                candidate_name = self._get_entity_name(candidate)
                if candidate_name:
                    score = self._name_similarity(new_name, candidate_name)
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

    async def _get_candidate_entities(self, entity_type: str, limit: int) -> List[Entity]:
        """
        Get candidate entities for linking

        This is a placeholder - in production, you'd want:
        - Indexed search by entity type
        - LIKE queries for name matching
        - Pagination for large result sets

        Args:
            entity_type: Entity type to filter by
            limit: Maximum candidates

        Returns:
            List of candidate entities
        """
        # TODO: Implement efficient candidate retrieval
        # For now, return empty list (will rely on embedding search primarily)
        # In Phase 3 (SQLite) and Phase 6 (PostgreSQL), we'll implement
        # efficient queries for this
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

        return self._name_similarity(name1, name2) >= self.similarity_threshold

    def _get_entity_name(self, entity: Entity) -> str:
        """Extract entity name from properties"""
        return entity.properties.get("name") or entity.properties.get("title") or entity.properties.get("text") or ""

    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Compute name similarity using fuzzy matching

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score (0.0-1.0)
        """
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

"""
Entity Deduplicator

Identifies and merges duplicate entities based on similarity matching.
"""

from typing import List, Dict, Optional, Tuple, Set, TYPE_CHECKING
from difflib import SequenceMatcher
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.infrastructure.graph_storage.tenant import (
    TenantContext,
    CrossTenantFusionError,
)

if TYPE_CHECKING:
    from aiecs.application.knowledge_graph.fusion.similarity_pipeline import (
        SimilarityPipeline,
    )


class EntityDeduplicator:
    """
    Deduplicate entities based on similarity

    When extracting entities from text, it's common to get duplicates:
    - "Apple Inc." vs "Apple" vs "Apple Incorporated"
    - "John Smith" vs "J. Smith" vs "Smith, John"
    - "New York" vs "New York City" vs "NYC"

    This class identifies such duplicates and merges them into canonical entities.

    Features:
    - Name-based fuzzy matching
    - Type-aware matching (only match entities of same type)
    - Property-based matching (use properties to improve matching)
    - Configurable similarity threshold
    - Embedding-based matching (when embeddings available)

    Example:
        ```python
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)

        entities = [
            Entity(type="Company", properties={"name": "Apple Inc."}),
            Entity(type="Company", properties={"name": "Apple"}),
            Entity(type="Company", properties={"name": "Microsoft"})
        ]

        deduplicated = await deduplicator.deduplicate(entities)
        # Returns: [
        #   Entity(type="Company", properties={"name": "Apple Inc.", "_aliases": ["Apple"]}),
        #   Entity(type="Company", properties={"name": "Microsoft"})
        # ]
        ```
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        use_embeddings: bool = True,
        embedding_threshold: float = 0.90,
        similarity_pipeline: Optional["SimilarityPipeline"] = None,
    ):
        """
        Initialize entity deduplicator

        Args:
            similarity_threshold: Minimum similarity score to consider entities as duplicates (0.0-1.0)
            use_embeddings: Whether to use embeddings for similarity (if available)
            embedding_threshold: Minimum embedding similarity for duplicates (0.0-1.0)
            similarity_pipeline: Optional SimilarityPipeline for enhanced matching
        """
        self.similarity_threshold = similarity_threshold
        self.use_embeddings = use_embeddings
        self.embedding_threshold = embedding_threshold
        self._similarity_pipeline = similarity_pipeline

    async def deduplicate(
        self, entities: List[Entity], context: Optional[TenantContext] = None
    ) -> List[Entity]:
        """
        Deduplicate a list of entities

        **Tenant Isolation**: When context is provided, deduplication only compares
        entities within the same tenant. Entities from other tenants are filtered out
        (defense-in-depth).

        Args:
            entities: List of entities to deduplicate
            context: Optional tenant context for multi-tenant isolation

        Returns:
            List of deduplicated entities (with merged properties and aliases)
        """
        if not entities:
            return []

        # Filter to only entities in the specified tenant (defense-in-depth)
        if context:
            entities = [e for e in entities if e.tenant_id == context.tenant_id]

        # Group entities by type (only match within same type)
        entities_by_type: Dict[str, List[Entity]] = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)

        # Deduplicate within each type
        deduplicated_entities = []
        for entity_type, type_entities in entities_by_type.items():
            deduped = await self._deduplicate_type_group(type_entities)
            deduplicated_entities.extend(deduped)

        return deduplicated_entities

    async def _deduplicate_type_group(self, entities: List[Entity]) -> List[Entity]:
        """
        Deduplicate entities of the same type

        Algorithm:
        1. Build similarity matrix between all pairs
        2. Find clusters of similar entities (connected components)
        3. Merge each cluster into a single canonical entity

        Note: Assumes all entities in the group are from the same tenant
        (validated by caller if in multi-tenant mode)

        Args:
            entities: List of entities (all same type and same tenant)

        Returns:
            List of deduplicated entities
        """
        if len(entities) <= 1:
            return entities

        # Build similarity graph
        n = len(entities)
        similar_pairs: Set[Tuple[int, int]] = set()

        for i in range(n):
            for j in range(i + 1, n):
                similarity = await self._compute_similarity(entities[i], entities[j])
                if similarity >= self.similarity_threshold:
                    similar_pairs.add((i, j))

        # Find connected components (clusters of similar entities)
        clusters = self._find_clusters(n, similar_pairs)

        # Merge each cluster into canonical entity
        deduplicated = []
        for cluster in clusters:
            cluster_entities = [entities[idx] for idx in cluster]
            merged_entity = self._merge_entities(cluster_entities)
            deduplicated.append(merged_entity)

        return deduplicated

    async def _compute_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """
        Compute similarity between two entities

        Uses multiple signals:
        1. Name similarity (via SimilarityPipeline if available, else fuzzy string matching)
        2. Property overlap
        3. Embedding similarity (if available)

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            Similarity score (0.0-1.0)
        """
        # Get entity names
        name1 = self._get_entity_name(entity1)
        name2 = self._get_entity_name(entity2)

        if not name1 or not name2:
            return 0.0

        # 1. Name-based similarity (use pipeline if available)
        if self._similarity_pipeline is not None:
            # Use enhanced similarity pipeline with per-entity-type configuration
            pipeline_result = await self._similarity_pipeline.compute_similarity(
                name1=name1,
                name2=name2,
                entity_type=entity1.entity_type,
            )
            name_similarity = pipeline_result.final_score
        else:
            # Fallback to basic string similarity
            name_similarity = self._string_similarity(name1, name2)

        # 2. Property overlap
        property_similarity = self._property_similarity(entity1.properties, entity2.properties)

        # 3. Embedding similarity (if available)
        embedding_similarity = 0.0
        if self.use_embeddings and entity1.embedding and entity2.embedding:
            embedding_similarity = self._cosine_similarity(entity1.embedding, entity2.embedding)

        # Weighted combination
        if entity1.embedding and entity2.embedding and self.use_embeddings:
            # If embeddings available, give them high weight
            return 0.3 * name_similarity + 0.2 * property_similarity + 0.5 * embedding_similarity
        else:
            # No embeddings, rely on name and properties
            return 0.7 * name_similarity + 0.3 * property_similarity

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

    def _get_entity_name(self, entity: Entity) -> str:
        """Extract entity name from properties"""
        return entity.properties.get("name") or entity.properties.get("title") or entity.properties.get("text") or ""

    def _string_similarity(self, str1: str, str2: str) -> float:
        """
        Compute string similarity using multiple methods

        Combines:
        - Exact match (normalized)
        - SequenceMatcher ratio
        - Token overlap (for multi-word entities)

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0-1.0)
        """
        # Normalize strings
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        # Exact match
        if s1 == s2:
            return 1.0

        # One is substring of other
        if s1 in s2 or s2 in s1:
            return 0.95

        # Sequence matcher
        seq_similarity = SequenceMatcher(None, s1, s2).ratio()

        # Token overlap (for multi-word names)
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        if tokens1 and tokens2:
            token_overlap = len(tokens1 & tokens2) / len(tokens1 | tokens2)
        else:
            token_overlap = 0.0

        # Combine
        return max(seq_similarity, token_overlap)

    def _property_similarity(self, props1: Dict, props2: Dict) -> float:
        """
        Compute similarity based on property overlap

        Args:
            props1: Properties of first entity
            props2: Properties of second entity

        Returns:
            Similarity score (0.0-1.0)
        """
        # Remove internal properties
        keys1 = {k for k in props1.keys() if not k.startswith("_")}
        keys2 = {k for k in props2.keys() if not k.startswith("_")}

        if not keys1 and not keys2:
            return 0.5  # No properties to compare

        # Key overlap
        common_keys = keys1 & keys2
        all_keys = keys1 | keys2

        if not all_keys:
            return 0.5

        key_overlap = len(common_keys) / len(all_keys)

        # Value similarity for common keys
        value_matches = 0
        for key in common_keys:
            val1 = str(props1[key]).lower()
            val2 = str(props2[key]).lower()
            if val1 == val2:
                value_matches += 1

        value_similarity = value_matches / len(common_keys) if common_keys else 0.0

        # Combine
        return 0.5 * key_overlap + 0.5 * value_similarity

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Compute cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0.0-1.0)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Cosine similarity ranges from -1 to 1, normalize to 0 to 1
        similarity = dot_product / (magnitude1 * magnitude2)
        return (similarity + 1) / 2

    def _find_clusters(self, n: int, edges: Set[Tuple[int, int]]) -> List[List[int]]:
        """
        Find connected components using Union-Find

        Args:
            n: Number of nodes
            edges: Set of edges (i, j) indicating similarity

        Returns:
            List of clusters, where each cluster is a list of node indices
        """
        # Union-Find data structure
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Build connected components
        for i, j in edges:
            union(i, j)

        # Group by root
        clusters_dict: Dict[int, List[int]] = {}
        for i in range(n):
            root = find(i)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(i)

        return list(clusters_dict.values())

    def _merge_entities(self, entities: List[Entity]) -> Entity:
        """
        Merge a cluster of similar entities into one canonical entity

        Strategy:
        - Use the first entity as base
        - Merge all properties (prefer non-empty values)
        - Store alternative names as aliases
        - Keep highest confidence score

        Args:
            entities: List of entities to merge

        Returns:
            Merged canonical entity
        """
        if len(entities) == 1:
            return entities[0]

        # Use first entity as base
        canonical = entities[0]

        # Collect all names as aliases
        aliases = set()
        for entity in entities:
            name = self._get_entity_name(entity)
            if name and name != self._get_entity_name(canonical):
                aliases.add(name)

        # Merge properties (prefer non-empty, non-None values)
        merged_properties = dict(canonical.properties)

        for entity in entities[1:]:
            for key, value in entity.properties.items():
                if key not in merged_properties or not merged_properties[key]:
                    merged_properties[key] = value

        # Add aliases
        if aliases:
            merged_properties["_aliases"] = list(aliases)

        # Take highest confidence
        confidences = [e.properties.get("_extraction_confidence", 0.5) for e in entities]
        merged_properties["_extraction_confidence"] = max(confidences)

        # Track merge count
        merged_properties["_merged_count"] = len(entities)

        # Create merged entity (preserve tenant_id from canonical entity)
        merged_entity = Entity(
            id=canonical.id,
            entity_type=canonical.entity_type,
            properties=merged_properties,
            embedding=canonical.embedding,
            source=canonical.source,
            tenant_id=canonical.tenant_id,
        )

        return merged_entity

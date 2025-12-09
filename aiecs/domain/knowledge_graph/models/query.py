"""
Query Domain Models

Models for specifying graph queries and their results.

Multi-Tenancy Support:
    GraphQuery now supports tenant_id field for filtering queries to a specific tenant.
    When tenant_id is provided, queries will only return entities and relations
    belonging to that tenant.
"""

from typing import Any, List, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.models.path import Path
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern


class QueryType(str, Enum):
    """Types of graph queries"""

    ENTITY_LOOKUP = "entity_lookup"
    VECTOR_SEARCH = "vector_search"
    TRAVERSAL = "traversal"
    PATH_FINDING = "path_finding"
    SUBGRAPH = "subgraph"
    CUSTOM = "custom"


class GraphQuery(BaseModel):
    """
    Graph Query Specification

    Specifies a query to execute against the knowledge graph.

    Attributes:
        query_type: Type of query to execute
        entity_id: Entity ID for entity lookup queries
        entity_type: Filter by entity type
        relation_type: Filter by relation type
        embedding: Query embedding for vector search
        properties: Property constraints for filtering
        max_results: Maximum number of results to return
        max_depth: Maximum traversal depth for path queries
        score_threshold: Minimum score threshold for results
        tenant_id: Tenant ID for multi-tenant filtering (None for global/single-tenant)

    Example:
        ```python
        # Vector search query
        query = GraphQuery(
            query_type=QueryType.VECTOR_SEARCH,
            embedding=[0.1, 0.2, ...],
            entity_type="Document",
            max_results=10,
            score_threshold=0.7
        )

        # Multi-tenant traversal query
        query = GraphQuery(
            query_type=QueryType.TRAVERSAL,
            entity_id="person_001",
            relation_type="KNOWS",
            max_depth=3,
            tenant_id="acme-corp"
        )
        ```
    """

    query_type: QueryType = Field(..., description="Type of query to execute")

    # Multi-tenancy support
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant ID for multi-tenant filtering (None for global/single-tenant mode)",
    )

    # Entity lookup
    entity_id: Optional[str] = Field(default=None, description="Entity ID for entity lookup queries")

    # Filtering
    entity_type: Optional[str] = Field(default=None, description="Filter results by entity type")

    relation_type: Optional[str] = Field(default=None, description="Filter by relation type (for traversal)")

    # Vector search
    embedding: Optional[List[float]] = Field(default=None, description="Query embedding for vector search")

    # Property constraints
    properties: Dict[str, Any] = Field(default_factory=dict, description="Property constraints for filtering")

    # Result constraints
    max_results: int = Field(default=10, ge=1, description="Maximum number of results to return")

    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum traversal depth for path queries",
    )

    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold for results",
    )

    # Source/target constraints for path finding
    source_entity_id: Optional[str] = Field(default=None, description="Source entity ID for path finding")

    target_entity_id: Optional[str] = Field(default=None, description="Target entity ID for path finding")

    # Custom query parameters
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="Additional custom query parameters")

    # Custom pattern matching (Task 3.3)
    pattern: Optional[PathPattern] = Field(
        default=None,
        description="Graph pattern for custom pattern matching queries",
    )

    patterns: Optional[List[PathPattern]] = Field(
        default=None,
        description="Multiple graph patterns for complex pattern matching",
    )

    optional_patterns: Optional[List[PathPattern]] = Field(default=None, description="Optional patterns that may or may not match")

    projection: Optional[List[str]] = Field(
        default=None,
        description="Fields to project in results (e.g., ['id', 'name', 'properties.age'])",
    )

    aggregations: Optional[Dict[str, str]] = Field(
        default=None,
        description="Aggregations to apply (e.g., {'count': 'COUNT', 'avg_age': 'AVG(properties.age)'})",
    )

    group_by: Optional[List[str]] = Field(default=None, description="Fields to group by for aggregations")

    class Config:
        use_enum_values = True

    def __str__(self) -> str:
        parts = [f"GraphQuery(type={self.query_type})"]
        if self.entity_id:
            parts.append(f"entity_id={self.entity_id}")
        if self.entity_type:
            parts.append(f"entity_type={self.entity_type}")
        if self.relation_type:
            parts.append(f"relation_type={self.relation_type}")
        return " ".join(parts)


class GraphResult(BaseModel):
    """
    Graph Query Result

    Contains the results of a graph query execution.

    Attributes:
        query: The original query that was executed
        entities: List of entity results
        relations: List of relation results (for traversal/subgraph queries)
        paths: List of path results (for path-finding queries)
        scores: Scores for each result (parallel to entities)
        total_count: Total number of matching results (before max_results limit)
        execution_time_ms: Query execution time in milliseconds

    Example:
        ```python
        result = GraphResult(
            query=query,
            entities=[entity1, entity2],
            scores=[0.95, 0.87],
            total_count=2,
            execution_time_ms=15.3
        )
        ```
    """

    query: GraphQuery = Field(..., description="The original query that was executed")

    entities: List[Entity] = Field(default_factory=list, description="List of entity results")

    relations: List[Relation] = Field(
        default_factory=list,
        description="List of relation results (for graph queries)",
    )

    paths: List[Path] = Field(
        default_factory=list,
        description="List of path results (for path-finding)",
    )

    scores: List[float] = Field(default_factory=list, description="Scores for each entity result")

    total_count: int = Field(default=0, ge=0, description="Total matching results (before limit)")

    execution_time_ms: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Query execution time in milliseconds",
    )

    class Config:
        arbitrary_types_allowed = True

    @property
    def has_results(self) -> bool:
        """Check if result contains any data"""
        return len(self.entities) > 0 or len(self.paths) > 0

    @property
    def entity_count(self) -> int:
        """Get number of entities in result"""
        return len(self.entities)

    @property
    def path_count(self) -> int:
        """Get number of paths in result"""
        return len(self.paths)

    def get_top_entities(self, n: int = 5) -> List[Entity]:
        """
        Get top N entities by score

        Args:
            n: Number of entities to return

        Returns:
            Top N entities
        """
        if not self.scores:
            return self.entities[:n]

        # Sort by score (descending)
        scored_entities = list(zip(self.entities, self.scores))
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        return [entity for entity, _ in scored_entities[:n]]

    def get_entity_ids(self) -> List[str]:
        """
        Get list of all entity IDs in result

        Returns:
            List of entity IDs
        """
        return [entity.id for entity in self.entities]

    def __str__(self) -> str:
        parts = [f"GraphResult(entities={self.entity_count}, paths={self.path_count})"]
        if self.execution_time_ms:
            parts.append(f"time={self.execution_time_ms:.2f}ms")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"GraphResult(" f"entities={self.entity_count}, " f"relations={len(self.relations)}, " f"paths={self.path_count}, " f"total_count={self.total_count})"

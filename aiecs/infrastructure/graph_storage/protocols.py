"""
Protocol definitions for graph storage mixins

These protocols define the interfaces that mixin classes expect from
the classes they're mixed into, allowing proper type checking.
"""

from typing import Protocol, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from aiecs.domain.knowledge_graph.models.entity import Entity
    from aiecs.domain.knowledge_graph.models.relation import Relation
    import asyncpg  # type: ignore[import-untyped]


class PaginationMixinProtocol(Protocol):
    """Protocol for classes that PaginationMixin expects"""

    async def get_all_entities(
        self, entity_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List["Entity"]:
        """Get all entities, optionally filtered by type and limited"""
        ...


class LazyLoadingMixinProtocol(Protocol):
    """Protocol for classes that LazyLoadingMixin expects"""

    async def get_entity(self, entity_id: str) -> Optional["Entity"]:
        """Get entity by ID"""
        ...

    async def get_all_entities(
        self, entity_type: Optional[str] = None, limit: Optional[int] = None
    ) -> List["Entity"]:
        """Get all entities, optionally filtered by type and limited"""
        ...

    async def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List["Entity"]:
        """Get neighboring entities"""
        ...


class BatchOperationsMixinProtocol(Protocol):
    """Protocol for classes that BatchOperationsMixin expects"""

    if TYPE_CHECKING:
        pool: Optional["asyncpg.Pool"]

    def _serialize_embedding(self, embedding: List[float]) -> Optional[bytes]:
        """Serialize embedding to bytes for storage"""
        ...


class GraphMemoryMixinProtocol(Protocol):
    """Protocol for classes that GraphMemoryMixin expects"""

    if TYPE_CHECKING:
        from aiecs.infrastructure.graph_storage.base import GraphStore

        graph_store: Optional["GraphStore"]


class GraphAwareAgentMixinProtocol(Protocol):
    """Protocol for classes that GraphAwareAgentMixin expects"""

    if TYPE_CHECKING:
        from aiecs.infrastructure.graph_storage.base import GraphStore

        graph_store: Optional["GraphStore"]


"""
Lazy Loading Support for Graph Storage

Provides lazy loading of entities and relations to reduce memory usage
and improve performance when working with large graphs.
"""

import logging
from typing import Optional, List, Dict, Any, AsyncIterator, TYPE_CHECKING
from dataclasses import dataclass, field

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

if TYPE_CHECKING:
    from aiecs.infrastructure.graph_storage.protocols import LazyLoadingMixinProtocol

logger = logging.getLogger(__name__)


@dataclass
class LazyEntity:
    """
    Lazy-loaded entity wrapper

    Only loads full entity data when accessed, reducing memory usage.

    Example:
        ```python
        lazy_entity = LazyEntity(id="person_1", store=store)

        # Entity not loaded yet
        print(lazy_entity.id)  # Just ID, no DB query

        # Load full entity when needed
        entity = await lazy_entity.load()
        print(entity.properties["name"])  # DB query executed
        ```
    """

    id: str
    entity_type: Optional[str] = None
    _store: Any = None
    _loaded_entity: Optional[Entity] = field(default=None, init=False, repr=False)
    _is_loaded: bool = field(default=False, init=False, repr=False)

    async def load(self, force: bool = False) -> Optional[Entity]:
        """
        Load the full entity from storage

        Args:
            force: Force reload even if already loaded

        Returns:
            Full Entity object or None if not found
        """
        if not force and self._is_loaded:
            return self._loaded_entity

        if not self._store:
            raise RuntimeError("No store provided for lazy loading")

        self._loaded_entity = await self._store.get_entity(self.id)
        self._is_loaded = True
        return self._loaded_entity

    async def get(self, property_name: str, default: Any = None) -> Any:
        """
        Get a specific property (loads entity if needed)

        Args:
            property_name: Property to retrieve
            default: Default value if property not found

        Returns:
            Property value or default
        """
        entity = await self.load()
        if not entity:
            return default
        return entity.properties.get(property_name, default)

    def is_loaded(self) -> bool:
        """Check if entity has been loaded"""
        return self._is_loaded

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (only includes loaded data)"""
        result: Dict[str, Any] = {"id": self.id}
        if self.entity_type:
            result["entity_type"] = self.entity_type
        if self._is_loaded and self._loaded_entity:
            result["properties"] = self._loaded_entity.properties
        return result


@dataclass
class LazyRelation:
    """
    Lazy-loaded relation wrapper

    Only loads full relation data when accessed.
    """

    id: str
    source_id: str
    target_id: str
    relation_type: Optional[str] = None
    _store: Any = None
    _loaded_relation: Optional[Relation] = field(default=None, init=False, repr=False)
    _is_loaded: bool = field(default=False, init=False, repr=False)

    async def load(self, force: bool = False) -> Optional[Relation]:
        """Load the full relation from storage"""
        if not force and self._is_loaded:
            return self._loaded_relation

        if not self._store:
            raise RuntimeError("No store provided for lazy loading")

        self._loaded_relation = await self._store.get_relation(self.id)
        self._is_loaded = True
        return self._loaded_relation

    async def get_source(self) -> Optional[Entity]:
        """Get source entity (lazy loaded)"""
        if not self._store:
            return None
        return await self._store.get_entity(self.source_id)

    async def get_target(self) -> Optional[Entity]:
        """Get target entity (lazy loaded)"""
        if not self._store:
            return None
        return await self._store.get_entity(self.target_id)

    def is_loaded(self) -> bool:
        """Check if relation has been loaded"""
        return self._is_loaded


class LazyLoadingMixin:
    """
    Mixin providing lazy loading capabilities for graph stores

    Enables deferred loading of entities and relations to reduce memory usage.

    This mixin expects the class it's mixed into to implement `LazyLoadingMixinProtocol`,
    specifically the `get_entity()`, `get_all_entities()`, and `get_neighbors()` methods.

    Example:
        ```python
        class MyGraphStore(GraphStore, LazyLoadingMixin):
            pass

        store = MyGraphStore()

        # Get lazy entities (no DB queries yet)
        lazy_entities = await store.get_lazy_entities(entity_type="Person")

        # Load specific entities as needed
        for lazy_entity in lazy_entities[:10]:
            entity = await lazy_entity.load()
            print(entity.properties["name"])
        ```
    """

    if TYPE_CHECKING:
        # Type hints for mypy: this mixin expects LazyLoadingMixinProtocol
        async def get_entity(self, entity_id: str) -> Optional[Entity]:
            """Expected method from LazyLoadingMixinProtocol"""
            ...

        async def get_all_entities(
            self, entity_type: Optional[str] = None, limit: Optional[int] = None
        ) -> List[Entity]:
            """Expected method from LazyLoadingMixinProtocol"""
            ...

        async def get_neighbors(
            self,
            entity_id: str,
            relation_type: Optional[str] = None,
            direction: str = "outgoing",
        ) -> List[Entity]:
            """Expected method from LazyLoadingMixinProtocol"""
            ...

    async def get_lazy_entity(self, entity_id: str) -> LazyEntity:
        """
        Get a lazy-loaded entity wrapper

        Args:
            entity_id: Entity ID

        Returns:
            LazyEntity wrapper (not yet loaded from DB)
        """
        return LazyEntity(id=entity_id, _store=self)

    async def get_lazy_entities(self, entity_type: Optional[str] = None, limit: Optional[int] = None) -> List[LazyEntity]:
        """
        Get lazy-loaded entity wrappers

        Only fetches IDs and types, not full entity data.

        Args:
            entity_type: Filter by entity type
            limit: Maximum number of entities

        Returns:
            List of LazyEntity wrappers
        """
        # Get lightweight entity list (IDs only)
        entities = await self._get_entity_ids(entity_type=entity_type, limit=limit)

        return [LazyEntity(id=eid, entity_type=etype, _store=self) for eid, etype in entities]

    async def _get_entity_ids(self, entity_type: Optional[str] = None, limit: Optional[int] = None) -> List[tuple[str, str]]:
        """
        Get entity IDs and types only (efficient query)

        Backends should override this for better performance.

        Returns:
            List of (entity_id, entity_type) tuples
        """
        # Default implementation - load full entities (inefficient)
        entities = await self.get_all_entities(entity_type=entity_type, limit=limit)
        return [(e.id, e.entity_type) for e in entities]

    async def get_lazy_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[LazyEntity]:
        """
        Get lazy-loaded neighbor entities

        Args:
            entity_id: Source entity ID
            relation_type: Filter by relation type
            direction: "outgoing", "incoming", or "both"

        Returns:
            List of LazyEntity wrappers for neighbors
        """
        # Get neighbor IDs without loading full entities
        neighbor_ids = await self._get_neighbor_ids(
            entity_id=entity_id,
            relation_type=relation_type,
            direction=direction,
        )

        return [LazyEntity(id=nid, _store=self) for nid in neighbor_ids]

    async def _get_neighbor_ids(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[str]:
        """
        Get neighbor entity IDs only (efficient query)

        Backends should override this for better performance.
        """
        # Default implementation - load full neighbors
        neighbors = await self.get_neighbors(
            entity_id=entity_id,
            relation_type=relation_type,
            direction=direction,
        )
        return [n.id for n in neighbors]


class EntityBatchLoader:
    """
    Batch loader for efficient loading of multiple entities

    Collects entity IDs and loads them in batches to reduce DB queries.
    Implements the DataLoader pattern for GraphQL-like efficiency.

    Example:
        ```python
        loader = EntityBatchLoader(store, batch_size=100)

        # Queue entities for loading
        e1_future = loader.load("entity_1")
        e2_future = loader.load("entity_2")
        # ... queue many more

        # Load all queued entities in batch
        await loader.dispatch()

        # Get results
        entity1 = await e1_future
        entity2 = await e2_future
        ```
    """

    def __init__(self, store: Any, batch_size: int = 100):
        """
        Initialize batch loader

        Args:
            store: Graph store instance
            batch_size: Maximum batch size
        """
        self.store = store
        self.batch_size = batch_size
        self._queue: List[str] = []
        self._cache: Dict[str, Optional[Entity]] = {}
        self._futures: Dict[str, Any] = {}

    async def load(self, entity_id: str) -> Optional[Entity]:
        """
        Load an entity (batched)

        Args:
            entity_id: Entity ID to load

        Returns:
            Entity or None if not found
        """
        # Check cache
        if entity_id in self._cache:
            return self._cache[entity_id]

        # Queue for batch loading
        if entity_id not in self._queue:
            self._queue.append(entity_id)

        # Dispatch if batch is full
        if len(self._queue) >= self.batch_size:
            await self.dispatch()

        return self._cache.get(entity_id)

    async def dispatch(self) -> None:
        """
        Dispatch all queued loads

        Loads all queued entities in batch and updates cache.
        """
        if not self._queue:
            return

        # Get unique IDs
        entity_ids = list(set(self._queue))
        self._queue.clear()

        # Batch load
        entities = await self._batch_fetch_entities(entity_ids)

        # Update cache
        entity_map = {e.id: e for e in entities}
        for eid in entity_ids:
            self._cache[eid] = entity_map.get(eid)

    async def _batch_fetch_entities(self, entity_ids: List[str]) -> List[Entity]:
        """
        Fetch multiple entities efficiently

        Backends should optimize this for batch retrieval.
        """
        entities = []
        for eid in entity_ids:
            entity = await self.store.get_entity(eid)
            if entity:
                entities.append(entity)
        return entities

    def clear_cache(self) -> None:
        """Clear the entity cache"""
        self._cache.clear()


async def lazy_traverse(store: Any, start_entity_id: str, max_depth: int = 3, batch_size: int = 100) -> AsyncIterator[LazyEntity]:
    """
    Lazy graph traversal with batch loading

    Traverses the graph lazily, yielding entities as they're discovered
    without loading the entire subgraph into memory.

    Args:
        store: Graph store instance
        start_entity_id: Starting entity ID
        max_depth: Maximum traversal depth
        batch_size: Batch size for loading

    Yields:
        LazyEntity instances as graph is traversed

    Example:
        ```python
        async for lazy_entity in lazy_traverse(store, "person_1", max_depth=3):
            entity = await lazy_entity.load()
            print(f"Found: {entity.id}")
        ```
    """
    visited = set()
    # loader = EntityBatchLoader(store, batch_size=batch_size)  # Reserved for
    # future use

    # BFS traversal
    current_level = [start_entity_id]
    depth = 0

    while current_level and depth <= max_depth:
        next_level = []

        for entity_id in current_level:
            if entity_id in visited:
                continue

            visited.add(entity_id)

            # Yield lazy entity
            lazy_entity = LazyEntity(id=entity_id, _store=store)
            yield lazy_entity

            # Get neighbors for next level
            neighbors = await store.get_neighbors(entity_id, direction="outgoing")
            for neighbor in neighbors:
                if neighbor.id not in visited:
                    next_level.append(neighbor.id)

        current_level = next_level
        depth += 1

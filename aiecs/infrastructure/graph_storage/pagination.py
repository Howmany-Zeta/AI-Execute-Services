"""
Pagination Support for Graph Storage

Provides cursor-based and offset-based pagination for large result sets,
enabling efficient navigation through millions of entities and relations.
"""

import base64
import json
import logging
from typing import Generic, TypeVar, List, Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation

if TYPE_CHECKING:
    from aiecs.infrastructure.graph_storage.protocols import PaginationMixinProtocol

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PaginationType(str, Enum):
    """Type of pagination strategy"""

    OFFSET = "offset"  # Traditional offset-based pagination
    # Cursor-based pagination (more efficient for large datasets)
    CURSOR = "cursor"


@dataclass
class PageInfo:
    """Metadata about pagination state"""

    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None
    total_count: Optional[int] = None  # Only available for offset pagination
    page_size: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "has_next_page": self.has_next_page,
            "has_previous_page": self.has_previous_page,
            "start_cursor": self.start_cursor,
            "end_cursor": self.end_cursor,
            "total_count": self.total_count,
            "page_size": self.page_size,
        }


@dataclass
class Page(Generic[T]):
    """
    Generic page of results

    Supports both cursor-based and offset-based pagination.

    Example:
        ```python
        page = await store.paginate_entities(page_size=100)

        for entity in page.items:
            print(entity.id)

        if page.page_info.has_next_page:
            next_page = await store.paginate_entities(
                page_size=100,
                cursor=page.page_info.end_cursor
            )
        ```
    """

    items: List[T]
    page_info: PageInfo

    def __len__(self) -> int:
        """Return number of items in page"""
        return len(self.items)

    def __iter__(self):
        """Allow iteration over items"""
        return iter(self.items)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "items": [item.model_dump() if hasattr(item, "model_dump") else item for item in self.items],
            "page_info": self.page_info.to_dict(),
        }


class PaginationCursor:
    """
    Cursor for efficient pagination

    Encodes pagination state (last seen ID, direction) into an opaque string.
    More efficient than offset pagination for large datasets.
    """

    @staticmethod
    def encode(last_id: str, direction: str = "forward") -> str:
        """
        Encode cursor from last seen ID

        Args:
            last_id: Last entity/relation ID seen
            direction: Pagination direction ("forward" or "backward")

        Returns:
            Encoded cursor string
        """
        cursor_data = {"id": last_id, "dir": direction}
        json_str = json.dumps(cursor_data)
        encoded = base64.b64encode(json_str.encode()).decode()
        return encoded

    @staticmethod
    def decode(cursor: str) -> Dict[str, str]:
        """
        Decode cursor to get last seen ID and direction

        Args:
            cursor: Encoded cursor string

        Returns:
            Dictionary with 'id' and 'dir' keys

        Raises:
            ValueError: If cursor is invalid
        """
        try:
            decoded = base64.b64decode(cursor.encode()).decode()
            cursor_data = json.loads(decoded)

            if "id" not in cursor_data:
                raise ValueError("Cursor missing 'id' field")

            return {
                "id": cursor_data["id"],
                "dir": cursor_data.get("dir", "forward"),
            }
        except Exception as e:
            raise ValueError(f"Invalid cursor: {e}")


class PaginationMixin:
    """
    Mixin providing pagination capabilities for graph stores

    Adds cursor-based and offset-based pagination methods for entities and relations.

    This mixin expects the class it's mixed into to implement `PaginationMixinProtocol`,
    specifically the `get_all_entities()` method.

    Example:
        ```python
        class MyGraphStore(GraphStore, PaginationMixin):
            pass

        store = MyGraphStore()

        # Cursor-based pagination (recommended for large datasets)
        page1 = await store.paginate_entities(page_size=100)
        page2 = await store.paginate_entities(
            page_size=100,
            cursor=page1.page_info.end_cursor
        )

        # Offset-based pagination
        page = await store.paginate_entities_offset(page=1, page_size=100)
        ```
    """

    if TYPE_CHECKING:
        # Type hint for mypy: this mixin expects PaginationMixinProtocol
        async def get_all_entities(
            self, entity_type: Optional[str] = None, limit: Optional[int] = None
        ) -> List[Entity]:
            """Expected method from PaginationMixinProtocol"""
            ...

    async def paginate_entities(
        self,
        entity_type: Optional[str] = None,
        page_size: int = 100,
        cursor: Optional[str] = None,
        order_by: str = "id",
    ) -> Page[Entity]:
        """
        Paginate entities using cursor-based pagination

        Args:
            entity_type: Filter by entity type
            page_size: Number of items per page
            cursor: Cursor for next page (None for first page)
            order_by: Field to order by (default: "id")

        Returns:
            Page of entities with pagination info

        Example:
            ```python
            # First page
            page1 = await store.paginate_entities(page_size=100)

            # Next page
            if page1.page_info.has_next_page:
                page2 = await store.paginate_entities(
                    page_size=100,
                    cursor=page1.page_info.end_cursor
                )
            ```
        """
        # Decode cursor if provided
        last_id = None
        if cursor:
            try:
                cursor_data = PaginationCursor.decode(cursor)
                last_id = cursor_data["id"]
            except ValueError as e:
                logger.warning(f"Invalid cursor: {e}")
                last_id = None

        # Fetch page_size + 1 to determine if there's a next page
        limit = page_size + 1

        # Query entities
        entities = await self._fetch_entities_page(
            entity_type=entity_type,
            last_id=last_id,
            limit=limit,
            order_by=order_by,
        )

        # Check if there's a next page
        has_next = len(entities) > page_size
        if has_next:
            entities = entities[:page_size]

        # Create cursors
        start_cursor = PaginationCursor.encode(entities[0].id) if entities else None
        end_cursor = PaginationCursor.encode(entities[-1].id) if entities else None

        # Create page info
        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=cursor is not None,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            page_size=page_size,
        )

        return Page(items=entities, page_info=page_info)

    async def _fetch_entities_page(
        self,
        entity_type: Optional[str],
        last_id: Optional[str],
        limit: int,
        order_by: str,
    ) -> List[Entity]:
        """
        Fetch a page of entities (backend-specific implementation)

        Args:
            entity_type: Filter by entity type
            last_id: Last entity ID from previous page (for cursor)
            limit: Maximum number of entities to fetch
            order_by: Field to order by

        Returns:
            List of entities
        """
        # This is a default implementation using get_all_entities
        # Backends should override this for better performance

        all_entities = await self.get_all_entities(entity_type=entity_type, limit=limit * 2)

        # Filter by cursor
        if last_id:
            start_index = 0
            for i, entity in enumerate(all_entities):
                if entity.id == last_id:
                    start_index = i + 1
                    break
            all_entities = all_entities[start_index:]

        # Sort
        if order_by == "id":
            all_entities.sort(key=lambda e: e.id)

        # Limit
        return all_entities[:limit]

    async def paginate_entities_offset(
        self,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        order_by: str = "id",
    ) -> Page[Entity]:
        """
        Paginate entities using offset-based pagination

        Args:
            entity_type: Filter by entity type
            page: Page number (1-indexed)
            page_size: Number of items per page
            order_by: Field to order by

        Returns:
            Page of entities with pagination info

        Note:
            Offset pagination is less efficient for large datasets.
            Consider using cursor-based pagination instead.

        Example:
            ```python
            # Get page 1
            page1 = await store.paginate_entities_offset(page=1, page_size=100)

            # Get page 2
            page2 = await store.paginate_entities_offset(page=2, page_size=100)
            ```
        """
        if page < 1:
            raise ValueError("Page number must be >= 1")

        # Calculate offset
        offset = (page - 1) * page_size

        # Fetch entities
        all_entities = await self.get_all_entities(entity_type=entity_type)

        # Sort
        if order_by == "id":
            all_entities.sort(key=lambda e: e.id)

        # Apply offset and limit
        total_count = len(all_entities)
        entities = all_entities[offset : offset + page_size]

        # Calculate pagination info
        has_next = offset + page_size < total_count
        has_previous = page > 1

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=has_previous,
            total_count=total_count,
            page_size=page_size,
        )

        return Page(items=entities, page_info=page_info)

    async def paginate_relations(
        self,
        relation_type: Optional[str] = None,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        page_size: int = 100,
        cursor: Optional[str] = None,
        order_by: str = "id",
    ) -> Page[Relation]:
        """
        Paginate relations using cursor-based pagination

        Args:
            relation_type: Filter by relation type
            source_id: Filter by source entity ID
            target_id: Filter by target entity ID
            page_size: Number of items per page
            cursor: Cursor for next page
            order_by: Field to order by

        Returns:
            Page of relations with pagination info
        """
        # Decode cursor
        last_id = None
        if cursor:
            try:
                cursor_data = PaginationCursor.decode(cursor)
                last_id = cursor_data["id"]
            except ValueError as e:
                logger.warning(f"Invalid cursor: {e}")

        # Fetch relations (limit + 1 to check for next page)
        limit = page_size + 1
        relations = await self._fetch_relations_page(
            relation_type=relation_type,
            source_id=source_id,
            target_id=target_id,
            last_id=last_id,
            limit=limit,
            order_by=order_by,
        )

        # Check for next page
        has_next = len(relations) > page_size
        if has_next:
            relations = relations[:page_size]

        # Create cursors
        start_cursor = PaginationCursor.encode(relations[0].id) if relations else None
        end_cursor = PaginationCursor.encode(relations[-1].id) if relations else None

        page_info = PageInfo(
            has_next_page=has_next,
            has_previous_page=cursor is not None,
            start_cursor=start_cursor,
            end_cursor=end_cursor,
            page_size=page_size,
        )

        return Page(items=relations, page_info=page_info)

    async def _fetch_relations_page(
        self,
        relation_type: Optional[str],
        source_id: Optional[str],
        target_id: Optional[str],
        last_id: Optional[str],
        limit: int,
        order_by: str,
    ) -> List[Relation]:
        """
        Fetch a page of relations (backend-specific implementation)

        Backends should override this for better performance.
        """
        # Default implementation - not efficient, should be overridden
        # This is just a placeholder
        relations: List[Any] = []

        # For now, return empty list
        # Backends should implement efficient relation pagination
        return relations


def paginate_list(items: List[T], page: int = 1, page_size: int = 100) -> Page[T]:
    """
    Paginate an in-memory list

    Utility function for paginating already-loaded data.

    Args:
        items: List of items to paginate
        page: Page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Page of items with pagination info

    Example:
        ```python
        all_entities = [...]  # 1000 entities
        page1 = paginate_list(all_entities, page=1, page_size=100)
        page2 = paginate_list(all_entities, page=2, page_size=100)
        ```
    """
    if page < 1:
        raise ValueError("Page number must be >= 1")

    offset = (page - 1) * page_size
    total_count = len(items)
    page_items = items[offset : offset + page_size]

    page_info = PageInfo(
        has_next_page=offset + page_size < total_count,
        has_previous_page=page > 1,
        total_count=total_count,
        page_size=page_size,
    )

    return Page(items=page_items, page_info=page_info)

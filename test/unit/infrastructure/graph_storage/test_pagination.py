"""
Unit tests for graph storage pagination module

Tests use real components (InMemoryGraphStore) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from aiecs.infrastructure.graph_storage import InMemoryGraphStore
from aiecs.infrastructure.graph_storage.pagination import (
    PaginationType,
    PageInfo,
    Page,
    PaginationCursor,
    PaginationMixin,
    paginate_list
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestPaginationType:
    """Test PaginationType enum"""
    
    def test_pagination_type_values(self):
        """Test PaginationType enum values"""
        assert PaginationType.OFFSET == "offset"
        assert PaginationType.CURSOR == "cursor"


class TestPageInfo:
    """Test PageInfo dataclass"""
    
    def test_page_info_defaults(self):
        """Test PageInfo with defaults"""
        info = PageInfo(has_next_page=True, has_previous_page=False)
        
        assert info.has_next_page is True
        assert info.has_previous_page is False
        assert info.start_cursor is None
        assert info.end_cursor is None
        assert info.total_count is None
        assert info.page_size == 100
    
    def test_page_info_custom(self):
        """Test PageInfo with custom values"""
        info = PageInfo(
            has_next_page=False,
            has_previous_page=True,
            start_cursor="cursor1",
            end_cursor="cursor2",
            total_count=500,
            page_size=50
        )
        
        assert info.has_next_page is False
        assert info.has_previous_page is True
        assert info.start_cursor == "cursor1"
        assert info.end_cursor == "cursor2"
        assert info.total_count == 500
        assert info.page_size == 50
    
    def test_page_info_to_dict(self):
        """Test PageInfo.to_dict()"""
        info = PageInfo(
            has_next_page=True,
            has_previous_page=False,
            start_cursor="start",
            end_cursor="end",
            total_count=100,
            page_size=25
        )
        
        result = info.to_dict()
        
        assert result["has_next_page"] is True
        assert result["has_previous_page"] is False
        assert result["start_cursor"] == "start"
        assert result["end_cursor"] == "end"
        assert result["total_count"] == 100
        assert result["page_size"] == 25


class TestPage:
    """Test Page generic class"""
    
    def test_page_len(self):
        """Test Page.__len__()"""
        items = [Entity(id=f"e{i}", entity_type="Person", properties={}) for i in range(5)]
        page_info = PageInfo(has_next_page=False, has_previous_page=False)
        page = Page(items=items, page_info=page_info)
        
        assert len(page) == 5
    
    def test_page_iter(self):
        """Test Page.__iter__()"""
        items = [Entity(id=f"e{i}", entity_type="Person", properties={}) for i in range(3)]
        page_info = PageInfo(has_next_page=False, has_previous_page=False)
        page = Page(items=items, page_info=page_info)
        
        assert list(page) == items
    
    def test_page_to_dict(self):
        """Test Page.to_dict()"""
        items = [Entity(id="e1", entity_type="Person", properties={"name": "Alice"})]
        page_info = PageInfo(has_next_page=False, has_previous_page=False)
        page = Page(items=items, page_info=page_info)
        
        result = page.to_dict()
        
        assert "items" in result
        assert "page_info" in result
        assert len(result["items"]) == 1


class TestPaginationCursor:
    """Test PaginationCursor"""
    
    def test_encode_forward(self):
        """Test encoding cursor with forward direction"""
        cursor = PaginationCursor.encode("entity_123", "forward")
        
        assert isinstance(cursor, str)
        assert len(cursor) > 0
    
    def test_encode_backward(self):
        """Test encoding cursor with backward direction"""
        cursor = PaginationCursor.encode("entity_123", "backward")
        
        assert isinstance(cursor, str)
    
    def test_decode_valid(self):
        """Test decoding valid cursor"""
        cursor = PaginationCursor.encode("entity_123", "forward")
        decoded = PaginationCursor.decode(cursor)
        
        assert decoded["id"] == "entity_123"
        assert decoded["dir"] == "forward"
    
    def test_decode_backward(self):
        """Test decoding backward cursor"""
        cursor = PaginationCursor.encode("entity_123", "backward")
        decoded = PaginationCursor.decode(cursor)
        
        assert decoded["id"] == "entity_123"
        assert decoded["dir"] == "backward"
    
    def test_decode_invalid(self):
        """Test decoding invalid cursor"""
        with pytest.raises(ValueError):
            PaginationCursor.decode("invalid_cursor")
    
    def test_decode_malformed(self):
        """Test decoding malformed cursor"""
        with pytest.raises(ValueError):
            PaginationCursor.decode("not_base64")
    
    def test_encode_decode_roundtrip(self):
        """Test encode/decode roundtrip"""
        original_id = "entity_123"
        original_dir = "forward"
        
        cursor = PaginationCursor.encode(original_id, original_dir)
        decoded = PaginationCursor.decode(cursor)
        
        assert decoded["id"] == original_id
        assert decoded["dir"] == original_dir


class TestPaginationMixin:
    """Test PaginationMixin"""
    
    @pytest.fixture
    async def store(self):
        """Create store with PaginationMixin"""
        class PaginatedStore(InMemoryGraphStore, PaginationMixin):
            async def get_all_entities(self, entity_type=None, limit=None):
                """Get all entities (for testing pagination)"""
                entities = list(self.entities.values())
                
                # Filter by type if specified
                if entity_type:
                    entities = [e for e in entities if e.entity_type == entity_type]
                
                # Apply limit if specified
                if limit:
                    entities = entities[:limit]
                
                return entities
        
        store = PaginatedStore()
        await store.initialize()
        
        # Add test entities
        for i in range(25):
            entity = Entity(
                id=f"e{i}",
                entity_type="Person" if i % 2 == 0 else "Company",
                properties={"index": i}
            )
            await store.add_entity(entity)
        
        yield store
        await store.close()
    
    @pytest.mark.asyncio
    async def test_paginate_entities_first_page(self, store):
        """Test paginating entities - first page"""
        page = await store.paginate_entities(page_size=10)
        
        assert isinstance(page, Page)
        assert len(page.items) == 10
        assert page.page_info.has_next_page is True
        assert page.page_info.has_previous_page is False
        assert page.page_info.start_cursor is not None
        assert page.page_info.end_cursor is not None
    
    @pytest.mark.asyncio
    async def test_paginate_entities_with_cursor(self, store):
        """Test paginating entities with cursor"""
        page1 = await store.paginate_entities(page_size=10)
        
        assert page1.page_info.has_next_page is True
        
        page2 = await store.paginate_entities(
            page_size=10,
            cursor=page1.page_info.end_cursor
        )
        
        assert len(page2.items) > 0  # May be less than 10 on last page
        assert page2.page_info.has_previous_page is True
        # Items should be different
        assert page1.items[0].id != page2.items[0].id
    
    @pytest.mark.asyncio
    async def test_paginate_entities_last_page(self, store):
        """Test paginating entities - last page"""
        # Get to last page
        cursor = None
        for _ in range(3):  # Should get us to last page
            page = await store.paginate_entities(page_size=10, cursor=cursor)
            if not page.page_info.has_next_page:
                break
            cursor = page.page_info.end_cursor
        
        assert page.page_info.has_next_page is False
    
    @pytest.mark.asyncio
    async def test_paginate_entities_with_type_filter(self, store):
        """Test paginating entities with type filter"""
        page = await store.paginate_entities(entity_type="Person", page_size=10)
        
        assert len(page.items) > 0
        # All items should be Person type
        for entity in page.items:
            assert entity.entity_type == "Person"
    
    @pytest.mark.asyncio
    async def test_paginate_entities_invalid_cursor(self, store):
        """Test paginating with invalid cursor"""
        page = await store.paginate_entities(page_size=10, cursor="invalid")
        
        # Should handle invalid cursor gracefully
        assert isinstance(page, Page)
    
    @pytest.mark.asyncio
    async def test_paginate_entities_offset_first_page(self, store):
        """Test offset pagination - first page"""
        page = await store.paginate_entities_offset(page=1, page_size=10)
        
        assert len(page.items) == 10
        assert page.page_info.has_next_page is True
        assert page.page_info.has_previous_page is False
        assert page.page_info.total_count == 25
    
    @pytest.mark.asyncio
    async def test_paginate_entities_offset_second_page(self, store):
        """Test offset pagination - second page"""
        page = await store.paginate_entities_offset(page=2, page_size=10)
        
        assert len(page.items) == 10
        assert page.page_info.has_previous_page is True
        assert page.page_info.total_count == 25
    
    @pytest.mark.asyncio
    async def test_paginate_entities_offset_invalid_page(self, store):
        """Test offset pagination with invalid page number"""
        with pytest.raises(ValueError):
            await store.paginate_entities_offset(page=0, page_size=10)
    
    @pytest.mark.asyncio
    async def test_paginate_entities_offset_last_page(self, store):
        """Test offset pagination - last page"""
        page = await store.paginate_entities_offset(page=3, page_size=10)
        
        assert len(page.items) == 5  # Remaining items
        assert page.page_info.has_next_page is False
        assert page.page_info.has_previous_page is True
    
    @pytest.mark.asyncio
    async def test_paginate_relations(self, store):
        """Test paginating relations"""
        # Add some relations
        for i in range(10):
            relation = Relation(
                id=f"r{i}",
                relation_type="KNOWS",
                source_id=f"e{i}",
                target_id=f"e{i+1}"
            )
            await store.add_relation(relation)
        
        page = await store.paginate_relations(page_size=5)
        
        assert isinstance(page, Page)
        # Note: _fetch_relations_page returns empty by default
        # This tests the pagination logic, not the actual fetching


class TestPaginateList:
    """Test paginate_list utility function"""
    
    def test_paginate_list_first_page(self):
        """Test paginating list - first page"""
        items = [f"item_{i}" for i in range(100)]
        page = paginate_list(items, page=1, page_size=10)
        
        assert len(page.items) == 10
        assert page.items[0] == "item_0"
        assert page.items[9] == "item_9"
        assert page.page_info.has_next_page is True
        assert page.page_info.has_previous_page is False
        assert page.page_info.total_count == 100
    
    def test_paginate_list_second_page(self):
        """Test paginating list - second page"""
        items = [f"item_{i}" for i in range(100)]
        page = paginate_list(items, page=2, page_size=10)
        
        assert len(page.items) == 10
        assert page.items[0] == "item_10"
        assert page.page_info.has_previous_page is True
    
    def test_paginate_list_last_page(self):
        """Test paginating list - last page"""
        items = [f"item_{i}" for i in range(25)]
        page = paginate_list(items, page=3, page_size=10)
        
        assert len(page.items) == 5  # Remaining items
        assert page.page_info.has_next_page is False
    
    def test_paginate_list_empty(self):
        """Test paginating empty list"""
        page = paginate_list([], page=1, page_size=10)
        
        assert len(page.items) == 0
        assert page.page_info.has_next_page is False
        assert page.page_info.total_count == 0
    
    def test_paginate_list_invalid_page(self):
        """Test paginating with invalid page number"""
        items = [f"item_{i}" for i in range(10)]
        
        with pytest.raises(ValueError):
            paginate_list(items, page=0, page_size=10)
    
    def test_paginate_list_page_beyond_range(self):
        """Test paginating beyond available pages"""
        items = [f"item_{i}" for i in range(10)]
        page = paginate_list(items, page=100, page_size=10)
        
        assert len(page.items) == 0
        assert page.page_info.has_next_page is False


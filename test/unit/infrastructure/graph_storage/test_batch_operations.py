"""
Unit tests for graph storage batch operations module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiecs.infrastructure.graph_storage.batch_operations import (
    BatchOperationsMixin,
    estimate_batch_size
)
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation


class TestBatchOperationsMixin:
    """Test BatchOperationsMixin"""
    
    @pytest.fixture
    def mock_store(self):
        """Create mock store with BatchOperationsMixin"""
        class TestStore(BatchOperationsMixin):
            def __init__(self):
                self.pool = None
            
            def _serialize_embedding(self, embedding):
                """Mock embedding serialization"""
                if embedding:
                    return b'\x00' * (len(embedding) * 4)  # Mock bytes
                return None
        
        store = TestStore()
        
        # Create mock pool
        pool = MagicMock()
        conn = AsyncMock()
        conn.copy_to_table = AsyncMock(return_value="COPY 5")
        conn.execute = AsyncMock(return_value="DELETE 3")
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        pool.acquire = MagicMock(return_value=async_context)
        
        store.pool = pool
        return store
    
    @pytest.mark.asyncio
    async def test_batch_add_entities_empty(self, mock_store):
        """Test batch_add_entities with empty list"""
        result = await mock_store.batch_add_entities([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_batch_add_entities_no_pool(self):
        """Test batch_add_entities without pool"""
        class TestStore(BatchOperationsMixin):
            pass
        
        store = TestStore()
        
        entities = [Entity(id="e1", entity_type="Person", properties={})]
        
        with pytest.raises(RuntimeError, match="GraphStore not initialized"):
            await store.batch_add_entities(entities)
    
    @pytest.mark.asyncio
    async def test_batch_add_entities_with_copy(self, mock_store):
        """Test batch_add_entities with COPY"""
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        ]
        
        result = await mock_store.batch_add_entities(entities, use_copy=True)
        
        assert result == 5  # Mock returns "COPY 5"
    
    @pytest.mark.asyncio
    async def test_batch_add_entities_with_insert(self, mock_store):
        """Test batch_add_entities with INSERT"""
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        ]
        
        result = await mock_store.batch_add_entities(entities, use_copy=False, batch_size=10)
        
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_batch_add_relations_empty(self, mock_store):
        """Test batch_add_relations with empty list"""
        result = await mock_store.batch_add_relations([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_batch_add_relations_no_pool(self):
        """Test batch_add_relations without pool"""
        class TestStore(BatchOperationsMixin):
            pass
        
        store = TestStore()
        
        relations = [Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2")]
        
        with pytest.raises(RuntimeError, match="GraphStore not initialized"):
            await store.batch_add_relations(relations)
    
    @pytest.mark.asyncio
    async def test_batch_add_relations_with_copy(self, mock_store):
        """Test batch_add_relations with COPY"""
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e3")
        ]
        
        result = await mock_store.batch_add_relations(relations, use_copy=True)
        
        assert result == 5  # Mock returns "COPY 5"
    
    @pytest.mark.asyncio
    async def test_batch_delete_entities_empty(self, mock_store):
        """Test batch_delete_entities with empty list"""
        result = await mock_store.batch_delete_entities([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_batch_delete_entities(self, mock_store):
        """Test batch_delete_entities"""
        entity_ids = ["e1", "e2", "e3"]
        
        result = await mock_store.batch_delete_entities(entity_ids)
        
        assert result == 3  # Mock returns "DELETE 3"
    
    @pytest.mark.asyncio
    async def test_batch_delete_relations_empty(self, mock_store):
        """Test batch_delete_relations with empty list"""
        result = await mock_store.batch_delete_relations([])
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_batch_delete_relations(self, mock_store):
        """Test batch_delete_relations"""
        relation_ids = ["r1", "r2"]
        
        result = await mock_store.batch_delete_relations(relation_ids)
        
        assert result == 3  # Mock returns "DELETE 3"


class TestEstimateBatchSize:
    """Test estimate_batch_size utility"""
    
    def test_estimate_batch_size_small_items(self):
        """Test estimating batch size for small items"""
        batch_size = estimate_batch_size(1024, target_batch_size_mb=10)
        
        # 10MB / 1KB = ~10,000 items
        assert batch_size >= 10000
        assert batch_size <= 11000
    
    def test_estimate_batch_size_large_items(self):
        """Test estimating batch size for large items"""
        batch_size = estimate_batch_size(1024 * 1024, target_batch_size_mb=10)
        
        # 10MB / 1MB = ~10 items, but minimum is 100
        assert batch_size >= 100  # Minimum enforced
    
    def test_estimate_batch_size_minimum(self):
        """Test that batch size has minimum of 100"""
        batch_size = estimate_batch_size(1024 * 1024 * 100, target_batch_size_mb=10)
        
        # Even if calculation would be < 100, should return at least 100
        assert batch_size >= 100


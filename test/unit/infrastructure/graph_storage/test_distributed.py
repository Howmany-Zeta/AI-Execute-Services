"""
Unit tests for graph storage distributed module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from aiecs.infrastructure.graph_storage.distributed import (
    PartitionStrategy,
    GraphPartition,
    DistributedGraphMixin,
    hash_partition_key,
    range_partition_key
)


class TestPartitionStrategy:
    """Test PartitionStrategy enum"""
    
    def test_partition_strategy_values(self):
        """Test PartitionStrategy enum values"""
        assert PartitionStrategy.HASH == "hash"
        assert PartitionStrategy.RANGE == "range"
        assert PartitionStrategy.COMMUNITY == "community"
        assert PartitionStrategy.CUSTOM == "custom"


class TestGraphPartition:
    """Test GraphPartition dataclass"""
    
    def test_graph_partition_defaults(self):
        """Test GraphPartition with defaults"""
        partition = GraphPartition(
            partition_id=0,
            node_count=100,
            edge_count=200
        )
        
        assert partition.partition_id == 0
        assert partition.node_count == 100
        assert partition.edge_count == 200
        assert partition.node_ids is None
    
    def test_graph_partition_with_node_ids(self):
        """Test GraphPartition with node IDs"""
        partition = GraphPartition(
            partition_id=1,
            node_count=50,
            edge_count=100,
            node_ids=["e1", "e2", "e3"]
        )
        
        assert partition.partition_id == 1
        assert partition.node_count == 50
        assert partition.edge_count == 100
        assert partition.node_ids == ["e1", "e2", "e3"]
    
    def test_graph_partition_to_dict(self):
        """Test GraphPartition.to_dict()"""
        partition = GraphPartition(
            partition_id=2,
            node_count=75,
            edge_count=150,
            node_ids=["e1", "e2"]
        )
        
        result = partition.to_dict()
        
        assert result["partition_id"] == 2
        assert result["node_count"] == 75
        assert result["edge_count"] == 150
        assert result["has_node_list"] is True
    
    def test_graph_partition_to_dict_no_node_ids(self):
        """Test GraphPartition.to_dict() without node IDs"""
        partition = GraphPartition(
            partition_id=0,
            node_count=100,
            edge_count=200
        )
        
        result = partition.to_dict()
        
        assert result["has_node_list"] is False


class TestDistributedGraphMixin:
    """Test DistributedGraphMixin"""
    
    @pytest.fixture
    def mixin_store(self):
        """Create a store with DistributedGraphMixin"""
        class TestStore(DistributedGraphMixin):
            pass
        
        return TestStore()
    
    @pytest.mark.asyncio
    async def test_partition_graph_hash(self, mixin_store):
        """Test partitioning graph with hash strategy"""
        partitions = await mixin_store.partition_graph(
            num_partitions=4,
            strategy=PartitionStrategy.HASH
        )
        
        assert len(partitions) == 4
        assert all(isinstance(p, GraphPartition) for p in partitions)
        assert all(p.partition_id == i for i, p in enumerate(partitions))
    
    @pytest.mark.asyncio
    async def test_partition_graph_range(self, mixin_store):
        """Test partitioning graph with range strategy"""
        partitions = await mixin_store.partition_graph(
            num_partitions=3,
            strategy=PartitionStrategy.RANGE
        )
        
        assert len(partitions) == 3
    
    @pytest.mark.asyncio
    async def test_partition_graph_community(self, mixin_store):
        """Test partitioning graph with community strategy"""
        partitions = await mixin_store.partition_graph(
            num_partitions=5,
            strategy=PartitionStrategy.COMMUNITY
        )
        
        assert len(partitions) == 5
    
    @pytest.mark.asyncio
    async def test_get_partition_info(self, mixin_store):
        """Test getting partition info"""
        info = await mixin_store.get_partition_info(partition_id=0)
        
        # Current implementation returns None (placeholder)
        assert info is None
    
    @pytest.mark.asyncio
    async def test_distributed_query(self, mixin_store):
        """Test distributed query execution"""
        result = await mixin_store.distributed_query(
            query="test query",
            partitions=[0, 1]
        )
        
        # Current implementation returns None (placeholder)
        assert result is None


class TestPartitionUtilities:
    """Test partition utility functions"""
    
    def test_hash_partition_key(self):
        """Test hash partition key function"""
        partition_id = hash_partition_key("entity_1", num_partitions=4)
        
        assert 0 <= partition_id < 4
        assert isinstance(partition_id, int)
    
    def test_hash_partition_key_consistent(self):
        """Test hash partition key is consistent"""
        key1 = hash_partition_key("entity_1", num_partitions=4)
        key2 = hash_partition_key("entity_1", num_partitions=4)
        
        assert key1 == key2
    
    def test_hash_partition_key_different_entities(self):
        """Test hash partition key for different entities"""
        key1 = hash_partition_key("entity_1", num_partitions=4)
        key2 = hash_partition_key("entity_2", num_partitions=4)
        
        # May or may not be different, but both should be valid
        assert 0 <= key1 < 4
        assert 0 <= key2 < 4
    
    def test_range_partition_key(self):
        """Test range partition key function"""
        ranges = [("a", "m"), ("m", "z")]
        
        partition_id = range_partition_key("entity_a", ranges)
        
        assert 0 <= partition_id < len(ranges)
    
    def test_range_partition_key_first_range(self):
        """Test range partition key in first range"""
        ranges = [("a", "m"), ("m", "z")]
        
        partition_id = range_partition_key("entity_b", ranges)
        
        assert partition_id == 0
    
    def test_range_partition_key_second_range(self):
        """Test range partition key in second range"""
        ranges = [("a", "m"), ("m", "z")]
        
        # Use entity ID that starts with 'n' which is >= 'm' and < 'z'
        # String comparison: 'n' > 'm', so 'n_entity' should match second range
        partition_id = range_partition_key("n_entity", ranges)
        
        # 'm' <= 'n_entity' < 'z' should be True
        assert partition_id == 1
    
    def test_range_partition_key_default(self):
        """Test range partition key defaults to last partition"""
        ranges = [("a", "m"), ("m", "z")]
        
        # Entity ID that doesn't match any range (starts with number)
        partition_id = range_partition_key("0_entity", ranges)
        
        # Should default to last partition
        assert partition_id == len(ranges) - 1


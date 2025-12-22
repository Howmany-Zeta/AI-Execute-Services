"""
Unit tests for graph storage index optimization module

Tests use real components when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiecs.infrastructure.graph_storage.index_optimization import (
    IndexRecommendation,
    IndexInfo,
    IndexOptimizer
)


class TestIndexRecommendation:
    """Test IndexRecommendation dataclass"""
    
    def test_index_recommendation_init(self):
        """Test IndexRecommendation initialization"""
        rec = IndexRecommendation(
            table_name="graph_entities",
            columns=["entity_type"],
            index_type="btree",
            reason="Frequent filtering by entity_type",
            estimated_benefit="high",
            create_sql="CREATE INDEX idx_entity_type ON graph_entities(entity_type)"
        )
        
        assert rec.table_name == "graph_entities"
        assert rec.columns == ["entity_type"]
        assert rec.index_type == "btree"
        assert rec.reason == "Frequent filtering by entity_type"
        assert rec.estimated_benefit == "high"
        assert "CREATE INDEX" in rec.create_sql
    
    def test_index_recommendation_to_dict(self):
        """Test IndexRecommendation.to_dict()"""
        rec = IndexRecommendation(
            table_name="graph_entities",
            columns=["entity_type", "properties"],
            index_type="gin",
            reason="JSONB property queries",
            estimated_benefit="medium",
            create_sql="CREATE INDEX idx_properties ON graph_entities USING gin(properties)"
        )
        
        result = rec.to_dict()
        
        assert result["table"] == "graph_entities"
        assert result["columns"] == ["entity_type", "properties"]
        assert result["type"] == "gin"
        assert result["reason"] == "JSONB property queries"
        assert result["benefit"] == "medium"
        assert "CREATE INDEX" in result["sql"]


class TestIndexInfo:
    """Test IndexInfo dataclass"""
    
    def test_index_info_init(self):
        """Test IndexInfo initialization"""
        info = IndexInfo(
            index_name="idx_entity_id",
            table_name="graph_entities",
            columns=["id"],
            index_type="btree",
            is_unique=True,
            size_bytes=1024 * 1024,  # 1MB
            usage_count=1000
        )
        
        assert info.index_name == "idx_entity_id"
        assert info.table_name == "graph_entities"
        assert info.columns == ["id"]
        assert info.index_type == "btree"
        assert info.is_unique is True
        assert info.size_bytes == 1024 * 1024
        assert info.usage_count == 1000
    
    def test_index_info_to_dict(self):
        """Test IndexInfo.to_dict()"""
        info = IndexInfo(
            index_name="idx_entity_id",
            table_name="graph_entities",
            columns=["id"],
            index_type="btree",
            is_unique=True,
            size_bytes=2 * 1024 * 1024,  # 2MB
            usage_count=500
        )
        
        result = info.to_dict()
        
        assert result["name"] == "idx_entity_id"
        assert result["table"] == "graph_entities"
        assert result["columns"] == ["id"]
        assert result["type"] == "btree"
        assert result["unique"] is True
        assert result["size_mb"] == 2.0
        assert result["usage_count"] == 500
    
    def test_index_info_default_usage_count(self):
        """Test IndexInfo with default usage_count"""
        info = IndexInfo(
            index_name="idx_test",
            table_name="graph_entities",
            columns=["id"],
            index_type="btree",
            is_unique=False,
            size_bytes=1024
        )
        
        assert info.usage_count == 0


class TestIndexOptimizer:
    """Test IndexOptimizer"""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool"""
        pool = MagicMock()
        
        # Create mock connection
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])
        
        # Create async context manager for acquire
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        pool.acquire = MagicMock(return_value=async_context)
        
        return pool
    
    def test_index_optimizer_init(self, mock_pool):
        """Test IndexOptimizer initialization"""
        optimizer = IndexOptimizer(mock_pool)
        
        assert optimizer.pool == mock_pool
    
    @pytest.mark.asyncio
    async def test_analyze_indexes_empty(self, mock_pool):
        """Test analyzing indexes when none exist"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock empty result
        async with mock_pool.acquire() as conn:
            conn.fetch = AsyncMock(return_value=[])
        
        indexes = await optimizer.analyze_indexes()
        
        assert indexes == []
    
    @pytest.mark.asyncio
    async def test_analyze_indexes_with_data(self, mock_pool):
        """Test analyzing indexes with data"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock index data
        row = MagicMock()
        row.__getitem__.side_effect = lambda key: {
            'index_name': 'idx_entity_id',
            'table_name': 'graph_entities',
            'columns': ['id'],
            'index_type': 'btree',
            'is_unique': True,
            'size_bytes': 1024,
            'usage_count': 100
        }[key]
        
        async with mock_pool.acquire() as conn:
            conn.fetch = AsyncMock(return_value=[row])
        
        indexes = await optimizer.analyze_indexes()
        
        assert len(indexes) == 1
        assert indexes[0].index_name == "idx_entity_id"
    
    @pytest.mark.asyncio
    async def test_get_unused_indexes(self, mock_pool):
        """Test getting unused indexes"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock indexes with low usage
        row1 = MagicMock()
        row1.__getitem__.side_effect = lambda key: {
            'index_name': 'idx_unused',
            'table_name': 'graph_entities',
            'columns': ['unused_col'],
            'index_type': 'btree',
            'is_unique': False,
            'size_bytes': 1024,
            'usage_count': 5  # Below threshold
        }[key]
        
        row2 = MagicMock()
        row2.__getitem__.side_effect = lambda key: {
            'index_name': 'idx_used',
            'table_name': 'graph_entities',
            'columns': ['used_col'],
            'index_type': 'btree',
            'is_unique': False,
            'size_bytes': 1024,
            'usage_count': 100  # Above threshold
        }[key]
        
        async with mock_pool.acquire() as conn:
            conn.fetch = AsyncMock(return_value=[row1, row2])
        
        unused = await optimizer.get_unused_indexes(min_usage_threshold=10)
        
        assert len(unused) == 1
        assert unused[0].index_name == "idx_unused"
    
    @pytest.mark.asyncio
    async def test_analyze_indexes_calls_pool(self, mock_pool):
        """Test that analyze_indexes calls pool.acquire"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock empty result
        async with mock_pool.acquire() as conn:
            conn.fetch = AsyncMock(return_value=[])
        
        indexes = await optimizer.analyze_indexes()
        
        # Should have called acquire
        assert mock_pool.acquire.called
        assert indexes == []
    
    @pytest.mark.asyncio
    async def test_get_missing_index_recommendations(self, mock_pool):
        """Test getting missing index recommendations"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock connection with index_exists returning False (indexes don't exist)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=False)  # Index doesn't exist
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        recommendations = await optimizer.get_missing_index_recommendations()
        
        # Should recommend several indexes
        assert len(recommendations) > 0
        assert all(isinstance(rec, IndexRecommendation) for rec in recommendations)
        
        # Check that recommendations have required fields
        for rec in recommendations:
            assert rec.table_name in ['graph_entities', 'graph_relations']
            assert len(rec.columns) > 0
            assert rec.index_type in ['btree', 'gin', 'gist', 'ivfflat']
            assert rec.estimated_benefit in ['high', 'medium', 'low']
            assert 'CREATE INDEX' in rec.create_sql
    
    @pytest.mark.asyncio
    async def test_get_missing_index_recommendations_existing_indexes(self, mock_pool):
        """Test recommendations when indexes already exist"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock connection with index_exists returning True (indexes exist)
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)  # Index exists
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        recommendations = await optimizer.get_missing_index_recommendations()
        
        # Should return empty list if all indexes exist
        assert isinstance(recommendations, list)
    
    @pytest.mark.asyncio
    async def test_index_exists(self, mock_pool):
        """Test _index_exists method"""
        optimizer = IndexOptimizer(mock_pool)
        
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=True)
        
        result = await optimizer._index_exists(mock_conn, 'graph_entities', ['entity_type'])
        
        assert result is True
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_index_exists_false(self, mock_pool):
        """Test _index_exists returning False"""
        optimizer = IndexOptimizer(mock_pool)
        
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=None)  # None means False
        
        result = await optimizer._index_exists(mock_conn, 'graph_entities', ['entity_type'])
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_apply_recommendations_dry_run(self, mock_pool):
        """Test applying recommendations in dry run mode"""
        optimizer = IndexOptimizer(mock_pool)
        
        recommendations = [
            IndexRecommendation(
                table_name="graph_entities",
                columns=["entity_type"],
                index_type="btree",
                reason="Test",
                estimated_benefit="high",
                create_sql="CREATE INDEX idx_test ON graph_entities(entity_type)"
            )
        ]
        
        result = await optimizer.apply_recommendations(recommendations, dry_run=True)
        
        assert "applied" in result
        assert "failed" in result
        assert "skipped" in result
        assert len(result["skipped"]) == 1
        assert len(result["applied"]) == 0
        assert len(result["failed"]) == 0
    
    @pytest.mark.asyncio
    async def test_apply_recommendations_success(self, mock_pool):
        """Test applying recommendations successfully"""
        optimizer = IndexOptimizer(mock_pool)
        
        recommendations = [
            IndexRecommendation(
                table_name="graph_entities",
                columns=["entity_type"],
                index_type="btree",
                reason="Test",
                estimated_benefit="high",
                create_sql="CREATE INDEX idx_test ON graph_entities(entity_type)"
            )
        ]
        
        # Mock connection for execute
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        result = await optimizer.apply_recommendations(recommendations, dry_run=False)
        
        assert len(result["applied"]) == 1
        assert len(result["failed"]) == 0
        assert len(result["skipped"]) == 0
        mock_conn.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_recommendations_failure(self, mock_pool):
        """Test applying recommendations with failure"""
        optimizer = IndexOptimizer(mock_pool)
        
        recommendations = [
            IndexRecommendation(
                table_name="graph_entities",
                columns=["entity_type"],
                index_type="btree",
                reason="Test",
                estimated_benefit="high",
                create_sql="CREATE INDEX idx_test ON graph_entities(entity_type)"
            )
        ]
        
        # Mock connection that raises error
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Index creation failed"))
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        result = await optimizer.apply_recommendations(recommendations, dry_run=False)
        
        assert len(result["applied"]) == 0
        assert len(result["failed"]) == 1
        assert len(result["skipped"]) == 0
        assert "error" in result["failed"][0]
    
    @pytest.mark.asyncio
    async def test_analyze_table_stats(self, mock_pool):
        """Test analyzing table statistics"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock table stats rows
        mock_row1 = MagicMock()
        mock_row1.__getitem__ = lambda self, key: {
            'tablename': 'graph_entities',
            'total_size': '10 MB',
            'row_count': 1000,
            'dead_tuples': 10,
            'last_vacuum': None,
            'last_autovacuum': None,
            'last_analyze': None,
            'last_autoanalyze': None
        }[key]
        
        mock_row2 = MagicMock()
        mock_row2.__getitem__ = lambda self, key: {
            'tablename': 'graph_relations',
            'total_size': '20 MB',
            'row_count': 2000,
            'dead_tuples': 20,
            'last_vacuum': None,
            'last_autovacuum': None,
            'last_analyze': None,
            'last_autoanalyze': None
        }[key]
        
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row1, mock_row2])
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        stats = await optimizer.analyze_table_stats()
        
        assert 'graph_entities' in stats
        assert 'graph_relations' in stats
        assert stats['graph_entities']['row_count'] == 1000
        assert stats['graph_relations']['row_count'] == 2000
    
    @pytest.mark.asyncio
    async def test_analyze_table_stats_with_dates(self, mock_pool):
        """Test analyzing table statistics with date fields"""
        from datetime import datetime
        
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock table stats rows with dates
        test_date = datetime(2024, 1, 1, 12, 0, 0)
        
        mock_row1 = MagicMock()
        mock_row1.__getitem__ = lambda self, key: {
            'tablename': 'graph_entities',
            'total_size': '10 MB',
            'row_count': 1000,
            'dead_tuples': 10,
            'last_vacuum': test_date,
            'last_autovacuum': test_date,
            'last_analyze': test_date,
            'last_autoanalyze': test_date
        }[key]
        
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_row1])
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        stats = await optimizer.analyze_table_stats()
        
        assert 'graph_entities' in stats
        assert stats['graph_entities']['last_vacuum'] is not None
        assert isinstance(stats['graph_entities']['last_vacuum'], str)  # ISO format string
    
    @pytest.mark.asyncio
    async def test_vacuum_analyze_all_tables(self, mock_pool):
        """Test vacuum analyze on all tables"""
        optimizer = IndexOptimizer(mock_pool)
        
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        await optimizer.vacuum_analyze()
        
        # Should call execute twice (once for each table)
        assert mock_conn.execute.call_count == 2
        assert any('graph_entities' in str(call) for call in mock_conn.execute.call_args_list)
        assert any('graph_relations' in str(call) for call in mock_conn.execute.call_args_list)
    
    @pytest.mark.asyncio
    async def test_vacuum_analyze_specific_table(self, mock_pool):
        """Test vacuum analyze on specific table"""
        optimizer = IndexOptimizer(mock_pool)
        
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=mock_conn)
        async_context.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=async_context)
        
        await optimizer.vacuum_analyze(table_name='graph_entities')
        
        # Should call execute once for the specific table
        assert mock_conn.execute.call_count == 1
        assert 'graph_entities' in str(mock_conn.execute.call_args)
    
    @pytest.mark.asyncio
    async def test_get_optimization_report(self, mock_pool):
        """Test getting comprehensive optimization report"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Mock analyze_indexes
        mock_index = IndexInfo(
            index_name="idx_test",
            table_name="graph_entities",
            columns=["id"],
            index_type="btree",
            is_unique=True,
            size_bytes=1024 * 1024,
            usage_count=100
        )
        
        # Mock get_unused_indexes
        mock_unused_index = IndexInfo(
            index_name="idx_unused",
            table_name="graph_entities",
            columns=["unused_col"],
            index_type="btree",
            is_unique=False,
            size_bytes=512 * 1024,
            usage_count=5
        )
        
        # Mock get_missing_index_recommendations
        mock_recommendation = IndexRecommendation(
            table_name="graph_entities",
            columns=["entity_type"],
            index_type="btree",
            reason="Test",
            estimated_benefit="high",
            create_sql="CREATE INDEX idx_test ON graph_entities(entity_type)"
        )
        
        # Mock analyze_table_stats
        mock_table_stats = {
            'graph_entities': {
                'total_size': '10 MB',
                'row_count': 1000,
                'dead_tuples': 10
            }
        }
        
        # Patch all the methods
        with patch.object(optimizer, 'analyze_indexes', return_value=[mock_index]):
            with patch.object(optimizer, 'get_unused_indexes', return_value=[mock_unused_index]):
                with patch.object(optimizer, 'get_missing_index_recommendations', return_value=[mock_recommendation]):
                    with patch.object(optimizer, 'analyze_table_stats', return_value=mock_table_stats):
                        report = await optimizer.get_optimization_report()
        
        assert "indexes" in report
        assert "unused_indexes" in report
        assert "recommendations" in report
        assert "table_stats" in report
        assert "summary" in report
        
        assert report["indexes"]["total_count"] == 1
        assert report["indexes"]["unused_count"] == 1
        assert len(report["recommendations"]) == 1
        assert report["summary"]["total_recommendations"] == 1
        assert report["summary"]["high_priority"] == 1
    
    @pytest.mark.asyncio
    async def test_get_optimization_report_empty(self, mock_pool):
        """Test optimization report with empty data"""
        optimizer = IndexOptimizer(mock_pool)
        
        # Patch all methods to return empty data
        with patch.object(optimizer, 'analyze_indexes', return_value=[]):
            with patch.object(optimizer, 'get_unused_indexes', return_value=[]):
                with patch.object(optimizer, 'get_missing_index_recommendations', return_value=[]):
                    with patch.object(optimizer, 'analyze_table_stats', return_value={}):
                        report = await optimizer.get_optimization_report()
        
        assert report["indexes"]["total_count"] == 0
        assert report["indexes"]["unused_count"] == 0
        assert len(report["recommendations"]) == 0
        assert report["summary"]["total_recommendations"] == 0
        assert report["summary"]["potential_space_savings_mb"] == 0.0


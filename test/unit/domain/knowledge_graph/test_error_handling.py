"""
Error Handling Tests for Knowledge Graph

Tests for error conditions, exception handling, and graceful degradation.
"""

import pytest
from typing import Dict, Any

from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion
from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline,
    SchemaMapping,
    EntityMapping
)
from aiecs.application.knowledge_graph.search.reranker import ResultReranker
from aiecs.application.knowledge_graph.search.reranker_strategies import TextSimilarityReranker
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity


class TestKnowledgeFusionErrorHandling:
    """Error handling for Knowledge Fusion"""
    
    @pytest.mark.asyncio
    async def test_fusion_with_corrupted_entity_data(self):
        """Test fusion handles corrupted entity data"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Add entity with unusual properties
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": None, "age": "invalid"}  # Invalid data
        )
        await store.add_entity(entity)
        
        fusion = KnowledgeFusion(store)
        
        # Should not crash
        try:
            stats = await fusion.fuse_cross_document_entities()
            assert stats is not None
        except Exception as e:
            pytest.fail(f"Fusion should handle corrupted data gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_fusion_with_missing_provenance(self):
        """Test fusion with entities missing provenance"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Entity without _provenance
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        await store.add_entity(entity)
        
        fusion = KnowledgeFusion(store)
        stats = await fusion.fuse_cross_document_entities()
        
        # Should complete successfully
        assert stats["success"] is True
    
    @pytest.mark.asyncio
    async def test_fusion_with_invalid_conflict_resolution_strategy(self):
        """Test fusion with invalid strategy"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Invalid strategy should fall back to default
        fusion = KnowledgeFusion(
            store,
            conflict_resolution_strategy="invalid_strategy"
        )
        
        # Should use default strategy
        assert fusion.conflict_resolution_strategy in [
            "most_complete", "most_recent", "most_confident", "longest", "keep_all"
        ]


class TestStructuredPipelineErrorHandling:
    """Error handling for Structured Data Pipeline"""
    
    @pytest.mark.asyncio
    async def test_pipeline_with_nonexistent_file(self):
        """Test pipeline with file that doesn't exist"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        mapping = SchemaMapping(
            entity_mappings=[
                EntityMapping(
                    entity_type="Person",
                    id_column="id",
                    property_mappings={"name": "name"}
                )
            ]
        )
        
        pipeline = StructuredDataPipeline(
            mapping=mapping,
            graph_store=store
        )
        
        # Should handle missing file gracefully
        result = await pipeline.import_from_csv("/nonexistent/file.csv")
        
        assert result.success is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_with_malformed_csv(self):
        """Test pipeline with malformed CSV data"""
        import tempfile
        import os
        
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create malformed CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,name\n")
            f.write("1,Alice\n")
            f.write("2,Bob,Extra,Columns\n")  # Malformed row
            f.write("3,Charlie\n")
            temp_path = f.name
        
        try:
            mapping = SchemaMapping(
                entity_mappings=[
                    EntityMapping(
                        entity_type="Person",
                        id_column="id",
                        property_mappings={"name": "name"}
                    )
                ]
            )
            
            pipeline = StructuredDataPipeline(
                mapping=mapping,
                graph_store=store,
                skip_errors=True
            )
            
            result = await pipeline.import_from_csv(temp_path)
            
            # Should process valid rows and skip malformed ones
            assert result.rows_processed >= 2  # At least Alice and Charlie
            
        finally:
            os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_pipeline_with_missing_columns(self):
        """Test pipeline when CSV is missing required columns"""
        import tempfile
        import os
        
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Create CSV without required column
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("id,age\n")  # Missing 'name' column
            f.write("1,30\n")
            temp_path = f.name
        
        try:
            mapping = SchemaMapping(
                entity_mappings=[
                    EntityMapping(
                        entity_type="Person",
                        id_column="id",
                        property_mappings={"name": "name"}  # Column doesn't exist
                    )
                ]
            )
            
            pipeline = StructuredDataPipeline(
                mapping=mapping,
                graph_store=store
            )
            
            result = await pipeline.import_from_csv(temp_path)
            
            # Should handle missing columns
            assert result is not None
            
        finally:
            os.unlink(temp_path)


class TestRerankerErrorHandling:
    """Error handling for Result Reranker"""
    
    @pytest.mark.asyncio
    async def test_reranker_with_none_query(self):
        """Test reranker with None query"""
        strategy = TextSimilarityReranker()
        reranker = ResultReranker(strategies=[strategy])
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        ]
        
        # Should handle None query
        results = await reranker.rerank(
            query=None,
            entities=entities,
            top_k=10
        )
        
        assert results is not None
    
    @pytest.mark.asyncio
    async def test_reranker_with_entities_missing_properties(self):
        """Test reranker with entities that have no properties"""
        strategy = TextSimilarityReranker()
        reranker = ResultReranker(strategies=[strategy])
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={}),
            Entity(id="e2", entity_type="Person", properties=None)
        ]
        
        # Should handle entities with missing properties
        try:
            results = await reranker.rerank(
                query="test",
                entities=entities,
                top_k=10
            )
            assert results is not None
        except Exception as e:
            pytest.fail(f"Reranker should handle missing properties: {e}")
    
    @pytest.mark.asyncio
    async def test_reranker_with_negative_top_k(self):
        """Test reranker with negative top_k"""
        reranker = ResultReranker(strategies=[])
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        ]
        
        # Should handle negative top_k gracefully
        results = await reranker.rerank(
            query="test",
            entities=entities,
            top_k=-1
        )
        
        # Should return empty or all results
        assert isinstance(results, list)


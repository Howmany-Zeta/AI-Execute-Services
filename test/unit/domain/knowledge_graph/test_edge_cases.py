"""
Edge Case Tests for Knowledge Graph

Tests for boundary conditions, empty data, invalid inputs, and error handling.
"""

import pytest
from typing import Dict, Any, List

from aiecs.application.knowledge_graph.fusion.knowledge_fusion import KnowledgeFusion
from aiecs.application.knowledge_graph.builder.structured_pipeline import (
    StructuredDataPipeline,
    SchemaMapping,
    EntityMapping,
    RelationMapping
)
from aiecs.application.knowledge_graph.search.reranker import ResultReranker
from aiecs.application.knowledge_graph.reasoning.logic_form_parser import LogicFormParser
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.models.entity import Entity


class TestKnowledgeFusionEdgeCases:
    """Edge cases for Knowledge Fusion"""
    
    @pytest.mark.asyncio
    async def test_fusion_with_empty_graph(self):
        """Test fusion with no entities"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        fusion = KnowledgeFusion(store)
        stats = await fusion.fuse_cross_document_entities()
        
        assert stats["entities_analyzed"] == 0
        assert stats["entities_merged"] == 0
        assert stats["merge_groups"] == 0
    
    @pytest.mark.asyncio
    async def test_fusion_with_single_entity(self):
        """Test fusion with only one entity"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        entity = Entity(
            id="e1",
            entity_type="Person",
            properties={"name": "Alice"}
        )
        await store.add_entity(entity)
        
        fusion = KnowledgeFusion(store)
        stats = await fusion.fuse_cross_document_entities()
        
        assert stats["entities_analyzed"] == 1
        assert stats["entities_merged"] == 0
    
    @pytest.mark.asyncio
    async def test_fusion_with_invalid_similarity_threshold(self):
        """Test fusion with invalid threshold"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Should handle invalid threshold gracefully
        fusion = KnowledgeFusion(store, similarity_threshold=1.5)
        # Threshold should be clamped to valid range
        assert fusion.similarity_threshold <= 1.0
    
    @pytest.mark.asyncio
    async def test_fusion_with_entities_missing_properties(self):
        """Test fusion with entities that have missing properties"""
        store = InMemoryGraphStore()
        await store.initialize()
        
        # Entity with minimal properties
        e1 = Entity(id="e1", entity_type="Person", properties={})
        e2 = Entity(id="e2", entity_type="Person", properties={"name": "Alice"})
        
        await store.add_entity(e1)
        await store.add_entity(e2)
        
        fusion = KnowledgeFusion(store)
        stats = await fusion.fuse_cross_document_entities()
        
        # Should complete without errors
        assert stats["success"] is True


class TestStructuredPipelineEdgeCases:
    """Edge cases for Structured Data Pipeline"""
    
    def test_schema_mapping_validation_empty_mappings(self):
        """Test schema mapping with no mappings"""
        mapping = SchemaMapping(
            entity_mappings=[],
            relation_mappings=[]
        )
        
        errors = mapping.validate()
        assert len(errors) > 0  # Should have validation errors
    
    def test_entity_mapping_missing_required_fields(self):
        """Test entity mapping with missing fields"""
        with pytest.raises((ValueError, TypeError)):
            EntityMapping(
                entity_type="Person",
                # Missing id_column
                property_mappings={}
            )
    
    def test_relation_mapping_invalid_types(self):
        """Test relation mapping with invalid entity types"""
        mapping = RelationMapping(
            relation_type="WORKS_FOR",
            source_column="person_id",
            target_column="company_id",
            source_type="",  # Empty type
            target_type=""   # Empty type
        )
        
        # Should handle gracefully
        assert mapping.source_type == ""


class TestRerankerEdgeCases:
    """Edge cases for Result Reranker"""
    
    @pytest.mark.asyncio
    async def test_rerank_empty_results(self):
        """Test reranking with no results"""
        reranker = ResultReranker(strategies=[])
        
        results = await reranker.rerank(
            query="test",
            entities=[],
            top_k=10
        )
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_rerank_with_top_k_larger_than_results(self):
        """Test reranking when top_k > number of results"""
        reranker = ResultReranker(strategies=[])
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"})
        ]
        
        results = await reranker.rerank(
            query="test",
            entities=entities,
            top_k=100  # Much larger than available
        )
        
        # Should return all available entities
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_rerank_with_zero_top_k(self):
        """Test reranking with top_k=0"""
        reranker = ResultReranker(strategies=[])
        
        entities = [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"})
        ]
        
        results = await reranker.rerank(
            query="test",
            entities=entities,
            top_k=0
        )
        
        # Should return empty list
        assert len(results) == 0


class TestLogicFormParserEdgeCases:
    """Edge cases for Logic Form Parser"""
    
    def test_parse_empty_query(self):
        """Test parsing empty query"""
        parser = LogicFormParser()
        
        result = parser.parse("")
        
        # Should return a valid LogicalQuery even for empty input
        assert result is not None
        assert result.raw_query == ""
    
    def test_parse_very_long_query(self):
        """Test parsing very long query"""
        parser = LogicFormParser()
        
        # Create a very long query
        long_query = "Find all " + "people " * 1000 + "who work for companies"
        
        result = parser.parse(long_query)
        
        # Should handle without crashing
        assert result is not None
    
    def test_parse_query_with_special_characters(self):
        """Test parsing query with special characters"""
        parser = LogicFormParser()
        
        query = "Find people with name = 'O'Brien' AND age > 30"
        
        result = parser.parse(query)
        
        # Should handle special characters
        assert result is not None
    
    def test_parse_query_with_unicode(self):
        """Test parsing query with unicode characters"""
        parser = LogicFormParser()
        
        query = "Find people named 北京 or München"
        
        result = parser.parse(query)
        
        # Should handle unicode
        assert result is not None
        assert result.raw_query == query


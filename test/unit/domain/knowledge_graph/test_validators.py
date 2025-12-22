"""
Unit tests for knowledge graph validators module

Tests use real components (GraphSchema, RelationType) when possible.
Only use mocks if pytest-cov limitations cause issues.
"""

import pytest
from typing import List, Tuple

from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.application.knowledge_graph.validators.relation_validator import RelationValidator


class TestRelationValidator:
    """Test RelationValidator"""
    
    @pytest.fixture
    def empty_schema(self):
        """Create empty schema"""
        return GraphSchema()
    
    @pytest.fixture
    def sample_schema(self):
        """Create sample schema with relation types"""
        schema = GraphSchema()
        
        # Add WORKS_FOR relation type
        works_for = RelationType(
            name="WORKS_FOR",
            description="Employment relationship",
            source_entity_types=["Person"],
            target_entity_types=["Company"]
        )
        schema.add_relation_type(works_for)
        
        # Add KNOWS relation type (any entity types allowed)
        knows = RelationType(
            name="KNOWS",
            description="Social relationship",
            source_entity_types=None,  # Any source type
            target_entity_types=None   # Any target type
        )
        schema.add_relation_type(knows)
        
        # Add LOCATED_IN relation type with specific types
        located_in = RelationType(
            name="LOCATED_IN",
            description="Location relationship",
            source_entity_types=["Person", "Company"],
            target_entity_types=["Location"]
        )
        schema.add_relation_type(located_in)
        
        return schema
    
    @pytest.fixture
    def sample_entities(self):
        """Create sample entities"""
        return [
            Entity(id="e1", entity_type="Person", properties={"name": "Alice"}),
            Entity(id="e2", entity_type="Person", properties={"name": "Bob"}),
            Entity(id="e3", entity_type="Company", properties={"name": "Tech Corp"}),
            Entity(id="e4", entity_type="Location", properties={"name": "San Francisco"})
        ]
    
    def test_init_no_schema(self):
        """Test initialization without schema"""
        validator = RelationValidator()
        
        assert validator.schema is None
        assert validator.strict is False
    
    def test_init_with_schema(self, sample_schema):
        """Test initialization with schema"""
        validator = RelationValidator(schema=sample_schema)
        
        assert validator.schema == sample_schema
        assert validator.strict is False
    
    def test_init_strict_mode(self, sample_schema):
        """Test initialization with strict mode"""
        validator = RelationValidator(schema=sample_schema, strict=True)
        
        assert validator.schema == sample_schema
        assert validator.strict is True
    
    def test_validate_relation_basic_valid(self, sample_entities):
        """Test basic validation with valid relation"""
        validator = RelationValidator()
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # e1
            sample_entities[1]   # e2
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_missing_source_id(self, sample_entities):
        """Test validation with missing source_id"""
        validator = RelationValidator()
        
        # Create relation with None source_id (bypassing Pydantic validation)
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        # Manually set to None to test validator logic
        relation.source_id = None
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        assert is_valid is False
        assert "missing source_id" in errors[0].lower()
    
    def test_validate_relation_missing_target_id(self, sample_entities):
        """Test validation with missing target_id"""
        validator = RelationValidator()
        
        # Create relation with None target_id (bypassing Pydantic validation)
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        # Manually set to None to test validator logic
        relation.target_id = None
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        assert is_valid is False
        assert "missing target_id" in errors[0].lower()
    
    def test_validate_relation_missing_relation_type(self, sample_entities):
        """Test validation with missing relation_type"""
        validator = RelationValidator()
        
        relation = Relation(
            id="r1",
            relation_type="",  # Empty
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        assert is_valid is False
        assert "missing relation_type" in errors[0].lower()
    
    def test_validate_relation_source_id_mismatch(self, sample_entities):
        """Test validation with source_id mismatch"""
        validator = RelationValidator()
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="wrong_id",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # e1
            sample_entities[1]   # e2
        )
        
        assert is_valid is False
        assert "does not match" in errors[0]
        assert "source" in errors[0].lower()
    
    def test_validate_relation_target_id_mismatch(self, sample_entities):
        """Test validation with target_id mismatch"""
        validator = RelationValidator()
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="wrong_id"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # e1
            sample_entities[1]   # e2
        )
        
        assert is_valid is False
        assert "does not match" in errors[0]
        assert "target" in errors[0].lower()
    
    def test_validate_relation_multiple_errors(self, sample_entities):
        """Test validation with multiple errors"""
        validator = RelationValidator()
        
        # Create relation and manually set to None/empty to test validator logic
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        relation.relation_type = None
        relation.source_id = None
        relation.target_id = None
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        assert is_valid is False
        assert len(errors) >= 3
    
    def test_validate_relation_with_schema_valid(self, sample_schema, sample_entities):
        """Test validation with schema - valid relation"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e3"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # Person
            sample_entities[2]    # Company
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_with_schema_invalid_source_type(self, sample_schema, sample_entities):
        """Test validation with schema - invalid source entity type"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e3",
            target_id="e1"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[2],  # Company (wrong - should be Person)
            sample_entities[0]   # Person
        )
        
        assert is_valid is False
        assert any("source entity type" in error.lower() for error in errors)
    
    def test_validate_relation_with_schema_invalid_target_type(self, sample_schema, sample_entities):
        """Test validation with schema - invalid target entity type"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="WORKS_FOR",
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # Person (correct)
            sample_entities[1]   # Person (wrong - should be Company)
        )
        
        assert is_valid is False
        assert any("target entity type" in error.lower() for error in errors)
    
    def test_validate_relation_with_schema_unknown_type_non_strict(self, sample_schema, sample_entities):
        """Test validation with unknown relation type in non-strict mode"""
        validator = RelationValidator(schema=sample_schema, strict=False)
        
        relation = Relation(
            id="r1",
            relation_type="UNKNOWN_TYPE",
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        # Should be valid (unknown types allowed in non-strict mode)
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_with_schema_unknown_type_strict(self, sample_schema, sample_entities):
        """Test validation with unknown relation type in strict mode"""
        validator = RelationValidator(schema=sample_schema, strict=True)
        
        relation = Relation(
            id="r1",
            relation_type="UNKNOWN_TYPE",
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],
            sample_entities[1]
        )
        
        # Should be invalid (unknown types rejected in strict mode)
        assert is_valid is False
        assert any("not found in schema" in error.lower() for error in errors)
    
    def test_validate_relation_with_schema_any_source_type(self, sample_schema, sample_entities):
        """Test validation with relation type that allows any source type"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e2"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # Person
            sample_entities[1]   # Person
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_with_schema_any_target_type(self, sample_schema, sample_entities):
        """Test validation with relation type that allows any target type"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e3",
            target_id="e4"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[2],  # Company
            sample_entities[3]    # Location
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_with_schema_multiple_allowed_types(self, sample_schema, sample_entities):
        """Test validation with relation type that allows multiple entity types"""
        validator = RelationValidator(schema=sample_schema)
        
        # LOCATED_IN allows Person or Company as source
        relation = Relation(
            id="r1",
            relation_type="LOCATED_IN",
            source_id="e1",
            target_id="e4"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # Person (allowed)
            sample_entities[3]   # Location (allowed)
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_with_schema_company_source(self, sample_schema, sample_entities):
        """Test validation with Company as source for LOCATED_IN"""
        validator = RelationValidator(schema=sample_schema)
        
        relation = Relation(
            id="r1",
            relation_type="LOCATED_IN",
            source_id="e3",
            target_id="e4"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[2],  # Company (allowed)
            sample_entities[3]   # Location (allowed)
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relations_empty_list(self):
        """Test validating empty relation list"""
        validator = RelationValidator()
        
        results = validator.validate_relations([], [])
        
        assert results == []
    
    def test_validate_relations_single_valid(self, sample_entities):
        """Test validating single valid relation"""
        validator = RelationValidator()
        
        relations = [
            Relation(
                id="r1",
                relation_type="KNOWS",
                source_id="e1",
                target_id="e2"
            )
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 1
        relation, is_valid, errors = results[0]
        assert relation.id == "r1"
        assert is_valid is True
        assert errors == []
    
    def test_validate_relations_multiple_valid(self, sample_entities):
        """Test validating multiple valid relations"""
        validator = RelationValidator()
        
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e1")
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 2
        for relation, is_valid, errors in results:
            assert is_valid is True
            assert errors == []
    
    def test_validate_relations_missing_entity(self, sample_entities):
        """Test validating relations with missing entities"""
        validator = RelationValidator()
        
        relations = [
            Relation(
                id="r1",
                relation_type="KNOWS",
                source_id="e1",
                target_id="nonexistent"
            )
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 1
        relation, is_valid, errors = results[0]
        assert is_valid is False
        assert any("not found" in error.lower() for error in errors)
    
    def test_validate_relations_missing_source(self, sample_entities):
        """Test validating relations with missing source entity"""
        validator = RelationValidator()
        
        relations = [
            Relation(
                id="r1",
                relation_type="KNOWS",
                source_id="nonexistent",
                target_id="e2"
            )
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 1
        relation, is_valid, errors = results[0]
        assert is_valid is False
    
    def test_validate_relations_mixed_valid_invalid(self, sample_entities):
        """Test validating mix of valid and invalid relations"""
        validator = RelationValidator()
        
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),  # Valid
            Relation(id="r2", relation_type="", source_id="e2", target_id="e1")        # Invalid
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 2
        assert results[0][1] is True   # First is valid
        assert results[1][1] is False  # Second is invalid
    
    def test_validate_relations_with_schema(self, sample_schema, sample_entities):
        """Test validating relations with schema"""
        validator = RelationValidator(schema=sample_schema)
        
        relations = [
            Relation(id="r1", relation_type="WORKS_FOR", source_id="e1", target_id="e3"),  # Valid
            Relation(id="r2", relation_type="WORKS_FOR", source_id="e1", target_id="e2")     # Invalid target
        ]
        
        results = validator.validate_relations(relations, sample_entities)
        
        assert len(results) == 2
        assert results[0][1] is True   # First is valid
        assert results[1][1] is False  # Second is invalid
    
    def test_filter_valid_relations_empty(self):
        """Test filtering empty relation list"""
        validator = RelationValidator()
        
        filtered = validator.filter_valid_relations([], [])
        
        assert filtered == []
    
    def test_filter_valid_relations_all_valid(self, sample_entities):
        """Test filtering when all relations are valid"""
        validator = RelationValidator()
        
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="KNOWS", source_id="e2", target_id="e1")
        ]
        
        filtered = validator.filter_valid_relations(relations, sample_entities)
        
        assert len(filtered) == 2
        assert filtered[0].id == "r1"
        assert filtered[1].id == "r2"
    
    def test_filter_valid_relations_some_invalid(self, sample_entities):
        """Test filtering when some relations are invalid"""
        validator = RelationValidator()
        
        relations = [
            Relation(id="r1", relation_type="KNOWS", source_id="e1", target_id="e2"),  # Valid
            Relation(id="r2", relation_type="", source_id="e2", target_id="e1")        # Invalid
        ]
        
        filtered = validator.filter_valid_relations(relations, sample_entities)
        
        assert len(filtered) == 1
        assert filtered[0].id == "r1"
    
    def test_filter_valid_relations_all_invalid(self, sample_entities):
        """Test filtering when all relations are invalid"""
        validator = RelationValidator()
        
        relations = [
            Relation(id="r1", relation_type="", source_id="e1", target_id="e2"),
            Relation(id="r2", relation_type="", source_id="e2", target_id="e1")
        ]
        
        filtered = validator.filter_valid_relations(relations, sample_entities)
        
        assert len(filtered) == 0
    
    def test_filter_valid_relations_with_schema(self, sample_schema, sample_entities):
        """Test filtering with schema validation"""
        validator = RelationValidator(schema=sample_schema, strict=True)
        
        relations = [
            Relation(id="r1", relation_type="WORKS_FOR", source_id="e1", target_id="e3"),  # Valid
            Relation(id="r2", relation_type="UNKNOWN", source_id="e1", target_id="e2")      # Invalid (strict mode)
        ]
        
        filtered = validator.filter_valid_relations(relations, sample_entities)
        
        assert len(filtered) == 1
        assert filtered[0].id == "r1"
    
    def test_validate_relation_schema_source_types_none(self, sample_schema, sample_entities):
        """Test validation when source_entity_types is None (any allowed)"""
        validator = RelationValidator(schema=sample_schema)
        
        # KNOWS allows any source/target types
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e3",
            target_id="e4"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[2],  # Company
            sample_entities[3]    # Location
        )
        
        assert is_valid is True
        assert errors == []
    
    def test_validate_relation_schema_target_types_none(self, sample_schema, sample_entities):
        """Test validation when target_entity_types is None (any allowed)"""
        validator = RelationValidator(schema=sample_schema)
        
        # KNOWS allows any source/target types
        relation = Relation(
            id="r1",
            relation_type="KNOWS",
            source_id="e1",
            target_id="e3"
        )
        
        is_valid, errors = validator.validate_relation(
            relation,
            sample_entities[0],  # Person
            sample_entities[2]    # Company
        )
        
        assert is_valid is True
        assert errors == []


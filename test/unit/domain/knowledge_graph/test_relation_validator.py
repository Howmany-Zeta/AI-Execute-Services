"""
Unit tests for RelationValidator property validation

Tests property validation functionality including:
- Required properties validation
- Property type validation
- Property value range/allowed values validation
- Helpful error messages
"""

import pytest
from datetime import datetime
from aiecs.application.knowledge_graph.validators.relation_validator import RelationValidator
from aiecs.domain.knowledge_graph.models.entity import Entity
from aiecs.domain.knowledge_graph.models.relation import Relation
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType


@pytest.fixture
def sample_schema():
    """Create a sample schema with relation types and properties"""
    schema = GraphSchema(version="1.0")
    
    # Create relation type with properties
    works_for_type = RelationType(
        name="WORKS_FOR",
        description="Employment relationship",
        source_entity_types=["Person"],
        target_entity_types=["Company"],
        properties={
            "since": PropertySchema(
                name="since",
                property_type=PropertyType.STRING,
                required=True,
                description="Start date of employment"
            ),
            "role": PropertySchema(
                name="role",
                property_type=PropertyType.STRING,
                required=False,
                description="Job role"
            ),
            "salary": PropertySchema(
                name="salary",
                property_type=PropertyType.INTEGER,
                required=False,
                min_value=0,
                max_value=1000000,
                description="Annual salary"
            ),
            "status": PropertySchema(
                name="status",
                property_type=PropertyType.STRING,
                required=False,
                allowed_values=["active", "inactive", "terminated"],
                description="Employment status"
            )
        }
    )
    
    schema.add_relation_type(works_for_type)
    return schema


@pytest.fixture
def sample_entities():
    """Create sample entities"""
    person = Entity(
        id="person_001",
        entity_type="Person",
        properties={"name": "Alice"}
    )
    company = Entity(
        id="company_001",
        entity_type="Company",
        properties={"name": "Acme Corp"}
    )
    return person, company


class TestRelationPropertyValidation:
    """Test relation property validation against schema"""
    
    def test_valid_relation_with_all_properties(self, sample_schema, sample_entities):
        """Test validation passes when all properties are valid"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "role": "Engineer",
                "salary": 100000,
                "status": "active"
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_valid_relation_with_required_properties_only(self, sample_schema, sample_entities):
        """Test validation passes when only required properties are present"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01"
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_missing_required_property(self, sample_schema, sample_entities):
        """Test validation fails when required property is missing"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "role": "Engineer"  # Missing required "since"
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Required property 'since' missing" in error for error in errors)
        assert any("Available properties" in error for error in errors)
    
    def test_invalid_property_type_string(self, sample_schema, sample_entities):
        """Test validation fails when property type doesn't match (string expected)"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": 2020,  # Should be string, not integer
                "role": "Engineer"
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Property 'since'" in error and "must be string" in error for error in errors)
    
    def test_invalid_property_type_integer(self, sample_schema, sample_entities):
        """Test validation fails when property type doesn't match (integer expected)"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "salary": "100000"  # Should be integer, not string
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Property 'salary'" in error and "must be integer" in error for error in errors)
    
    def test_property_value_below_min_range(self, sample_schema, sample_entities):
        """Test validation fails when numeric property value is below minimum"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "salary": -1000  # Below minimum of 0
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Property 'salary'" in error and ">=" in error for error in errors)
    
    def test_property_value_above_max_range(self, sample_schema, sample_entities):
        """Test validation fails when numeric property value is above maximum"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "salary": 2000000  # Above maximum of 1000000
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Property 'salary'" in error and "<=" in error for error in errors)
    
    def test_property_value_not_in_allowed_values(self, sample_schema, sample_entities):
        """Test validation fails when property value is not in allowed values"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "status": "pending"  # Not in allowed values: ["active", "inactive", "terminated"]
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Property 'status'" in error and "must be one of" in error for error in errors)
    
    def test_multiple_property_validation_errors(self, sample_schema, sample_entities):
        """Test that multiple property errors are all reported"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                # Missing required "since"
                "salary": "invalid",  # Wrong type
                "status": "invalid_status"  # Not in allowed values
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        # Should have multiple errors
        assert len(errors) >= 3
        assert any("Required property 'since' missing" in error for error in errors)
        assert any("Property 'salary'" in error for error in errors)
        assert any("Property 'status'" in error for error in errors)
    
    def test_unknown_property_in_strict_mode(self, sample_schema, sample_entities):
        """Test that unknown properties are rejected in strict mode"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "unknown_prop": "value"  # Not in schema
            }
        )
        
        validator = RelationValidator(schema=sample_schema, strict=True)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("Unknown property 'unknown_prop'" in error for error in errors)
        assert any("Available properties" in error for error in errors)
    
    def test_unknown_property_in_non_strict_mode(self, sample_schema, sample_entities):
        """Test that unknown properties are allowed in non-strict mode"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "unknown_prop": "value"  # Not in schema, but allowed in non-strict mode
            }
        )
        
        validator = RelationValidator(schema=sample_schema, strict=False)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        # Should be valid - unknown properties are allowed in non-strict mode
        assert is_valid is True
        assert len(errors) == 0
    
    def test_empty_properties_dict(self, sample_schema, sample_entities):
        """Test validation with empty properties dict"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={}  # Empty dict, missing required "since"
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        assert any("Required property 'since' missing" in error for error in errors)
    
    def test_none_properties(self, sample_schema, sample_entities):
        """Test validation when properties is not provided (defaults to empty dict)"""
        person, company = sample_entities
        
        # Pydantic doesn't allow None for properties field, so we test with empty dict
        # which is what happens when properties is not provided
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001"
            # properties not provided - defaults to empty dict
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        # Should handle empty properties gracefully
        assert is_valid is False
        assert any("Required property 'since' missing" in error for error in errors)
    
    def test_error_message_includes_relation_type(self, sample_schema, sample_entities):
        """Test that error messages include relation type context"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": 2020  # Wrong type
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        assert is_valid is False
        # Error message should mention relation type (check for "WORKS_FOR" in any case)
        assert any("WORKS_FOR" in error or "works_for" in error.lower() for error in errors)
    
    def test_relation_without_schema(self, sample_entities):
        """Test validation without schema (should skip property validation)"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "any": "property"  # Without schema, can't validate
            }
        )
        
        validator = RelationValidator(schema=None)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        # Should pass basic validation (IDs match, etc.)
        # Property validation skipped when no schema
        assert is_valid is True
        assert len(errors) == 0
    
    def test_relation_type_not_in_schema(self, sample_schema, sample_entities):
        """Test validation when relation type doesn't exist in schema"""
        person, company = sample_entities
        
        relation = Relation(
            id="rel_001",
            relation_type="UNKNOWN_TYPE",
            source_id="person_001",
            target_id="company_001",
            properties={
                "any": "property"
            }
        )
        
        validator = RelationValidator(schema=sample_schema, strict=True)
        is_valid, errors = validator.validate_relation(relation, person, company)
        
        # Should fail because relation type not in schema
        assert is_valid is False
        assert any("Relation type 'UNKNOWN_TYPE' not found" in error for error in errors)
    
    def test_boolean_property_validation(self, sample_schema, sample_entities):
        """Test boolean property type validation"""
        person, company = sample_entities
        
        # Add a boolean property to the schema
        works_for_type = sample_schema.get_relation_type("WORKS_FOR")
        works_for_type.add_property(
            PropertySchema(
                name="is_full_time",
                property_type=PropertyType.BOOLEAN,
                required=False
            )
        )
        
        # Valid boolean
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "is_full_time": True
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        assert is_valid is True
        
        # Invalid boolean (string instead)
        relation.properties["is_full_time"] = "yes"
        is_valid, errors = validator.validate_relation(relation, person, company)
        assert is_valid is False
        assert any("Property 'is_full_time'" in error and "must be boolean" in error for error in errors)
    
    def test_list_property_validation(self, sample_schema, sample_entities):
        """Test list property type validation"""
        person, company = sample_entities
        
        # Add a list property to the schema
        works_for_type = sample_schema.get_relation_type("WORKS_FOR")
        works_for_type.add_property(
            PropertySchema(
                name="skills",
                property_type=PropertyType.LIST,
                required=False
            )
        )
        
        # Valid list
        relation = Relation(
            id="rel_001",
            relation_type="WORKS_FOR",
            source_id="person_001",
            target_id="company_001",
            properties={
                "since": "2020-01-01",
                "skills": ["Python", "JavaScript"]
            }
        )
        
        validator = RelationValidator(schema=sample_schema)
        is_valid, errors = validator.validate_relation(relation, person, company)
        assert is_valid is True
        
        # Invalid list (string instead)
        relation.properties["skills"] = "Python, JavaScript"
        is_valid, errors = validator.validate_relation(relation, person, company)
        assert is_valid is False
        assert any("Property 'skills'" in error and "must be list" in error for error in errors)

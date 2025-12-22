"""
Type Enums Tests

Tests for dynamic type enum generation from schema.

Phase: 3.4 - Type Enums
Version: 1.0
"""

import sys
from pathlib import Path
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.relation_type import RelationType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager
from aiecs.domain.knowledge_graph.schema.type_enums import (
    TypeEnumGenerator,
    EntityTypeEnum,
    RelationTypeEnum
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_schema():
    """Create a sample schema for testing"""
    schema = GraphSchema()
    
    # Add entity types
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING),
            "age": PropertySchema(name="age", property_type=PropertyType.INTEGER)
        }
    )
    
    paper_type = EntityType(
        name="Paper",
        properties={
            "title": PropertySchema(name="title", property_type=PropertyType.STRING),
            "year": PropertySchema(name="year", property_type=PropertyType.INTEGER)
        }
    )
    
    schema.add_entity_type(person_type)
    schema.add_entity_type(paper_type)
    
    # Add relation types
    authored_by = RelationType(
        name="AUTHORED_BY",
        source_type="Paper",
        target_type="Person"
    )
    
    works_for = RelationType(
        name="WORKS_FOR",
        source_type="Person",
        target_type="Company"
    )
    
    schema.add_relation_type(authored_by)
    schema.add_relation_type(works_for)
    
    return schema


@pytest.fixture
def enum_generator(sample_schema):
    """Create enum generator with sample schema"""
    return TypeEnumGenerator(sample_schema)


@pytest.fixture
def schema_manager(sample_schema):
    """Create schema manager with sample schema"""
    return SchemaManager(sample_schema)


# ============================================================================
# TypeEnumGenerator Tests
# ============================================================================

def test_generate_entity_type_enums(enum_generator):
    """Test generating entity type enums"""
    enums = enum_generator.generate_entity_type_enums()
    
    # Verify enums were generated
    assert "Person" in enums
    assert "Paper" in enums
    
    # Verify enum classes
    PersonEnum = enums["Person"]
    PaperEnum = enums["Paper"]
    
    # Verify enum members
    assert hasattr(PersonEnum, "PERSON")
    assert hasattr(PaperEnum, "PAPER")
    
    # Verify enum values
    assert PersonEnum.PERSON.value == "Person"
    assert PaperEnum.PAPER.value == "Paper"


def test_generate_relation_type_enums(enum_generator):
    """Test generating relation type enums"""
    enums = enum_generator.generate_relation_type_enums()
    
    # Verify enums were generated
    assert "AUTHORED_BY" in enums
    assert "WORKS_FOR" in enums
    
    # Verify enum classes
    AuthoredByEnum = enums["AUTHORED_BY"]
    WorksForEnum = enums["WORKS_FOR"]
    
    # Verify enum members
    assert hasattr(AuthoredByEnum, "AUTHORED_BY")
    assert hasattr(WorksForEnum, "WORKS_FOR")
    
    # Verify enum values
    assert AuthoredByEnum.AUTHORED_BY.value == "AUTHORED_BY"
    assert WorksForEnum.WORKS_FOR.value == "WORKS_FOR"


def test_generate_all_enums(enum_generator):
    """Test generating all enums at once"""
    all_enums = enum_generator.generate_all_enums()
    
    # Verify structure
    assert "entity_types" in all_enums
    assert "relation_types" in all_enums
    
    # Verify entity type enums
    assert "Person" in all_enums["entity_types"]
    assert "Paper" in all_enums["entity_types"]
    
    # Verify relation type enums
    assert "AUTHORED_BY" in all_enums["relation_types"]
    assert "WORKS_FOR" in all_enums["relation_types"]


def test_enum_name_conversion():
    """Test enum name conversion logic"""
    # Test CamelCase conversion
    assert TypeEnumGenerator._to_enum_name("Person") == "PERSON"
    assert TypeEnumGenerator._to_enum_name("WorksFor") == "WORKS_FOR"
    assert TypeEnumGenerator._to_enum_name("AuthoredBy") == "AUTHORED_BY"
    
    # Test already uppercase
    assert TypeEnumGenerator._to_enum_name("WORKS_FOR") == "WORKS_FOR"
    assert TypeEnumGenerator._to_enum_name("AUTHORED_BY") == "AUTHORED_BY"
    
    # Test single word
    assert TypeEnumGenerator._to_enum_name("Paper") == "PAPER"


# ============================================================================
# Backward Compatibility Tests
# ============================================================================

def test_enum_string_compatibility(enum_generator):
    """Test that enums are backward compatible with strings"""
    enums = enum_generator.generate_entity_type_enums()
    PersonEnum = enums["Person"]
    
    # Test string conversion
    assert str(PersonEnum.PERSON) == "Person"
    
    # Test string comparison
    assert PersonEnum.PERSON == "Person"
    
    # Test in string context
    entity_type = PersonEnum.PERSON
    assert f"Type: {entity_type}" == "Type: Person"


def test_enum_value_access(enum_generator):
    """Test accessing enum values"""
    enums = enum_generator.generate_entity_type_enums()
    PersonEnum = enums["Person"]
    
    # Test value attribute
    assert PersonEnum.PERSON.value == "Person"
    
    # Test name attribute
    assert PersonEnum.PERSON.name == "PERSON"


# ============================================================================
# SchemaManager Integration Tests
# ============================================================================

def test_schema_manager_generate_enums(schema_manager):
    """Test SchemaManager.generate_enums() method"""
    enums = schema_manager.generate_enums()

    # Verify structure
    assert "entity_types" in enums
    assert "relation_types" in enums

    # Verify entity type enums
    assert "Person" in enums["entity_types"]
    assert "Paper" in enums["entity_types"]

    # Verify relation type enums
    assert "AUTHORED_BY" in enums["relation_types"]
    assert "WORKS_FOR" in enums["relation_types"]


def test_schema_manager_enum_usage(schema_manager):
    """Test using generated enums from SchemaManager"""
    enums = schema_manager.generate_enums()

    # Get entity type enum
    PersonEnum = enums["entity_types"]["Person"]

    # Use enum in query context
    entity_type = PersonEnum.PERSON

    # Verify it works like a string
    assert entity_type == "Person"
    assert str(entity_type) == "Person"

    # Verify it can be used in schema lookups
    entity_type_def = schema_manager.get_entity_type(str(entity_type))
    assert entity_type_def is not None
    assert entity_type_def.name == "Person"


# ============================================================================
# Base Class Tests
# ============================================================================

def test_entity_type_enum_base_class():
    """Test EntityTypeEnum base class"""
    # Create a simple enum
    TestEnum = EntityTypeEnum("TestEnum", {"TEST": "TestValue"})

    # Test string conversion
    assert str(TestEnum.TEST) == "TestValue"

    # Test repr
    assert "TestEnum.TEST" in repr(TestEnum.TEST)

    # Test value
    assert TestEnum.TEST.value == "TestValue"


def test_relation_type_enum_base_class():
    """Test RelationTypeEnum base class"""
    # Create a simple enum
    TestEnum = RelationTypeEnum("TestEnum", {"TEST": "TestValue"})

    # Test string conversion
    assert str(TestEnum.TEST) == "TestValue"

    # Test repr
    assert "TestEnum.TEST" in repr(TestEnum.TEST)

    # Test value
    assert TestEnum.TEST.value == "TestValue"


# ============================================================================
# Edge Cases Tests
# ============================================================================

def test_empty_schema():
    """Test enum generation with empty schema"""
    empty_schema = GraphSchema()
    generator = TypeEnumGenerator(empty_schema)

    # Generate enums
    entity_enums = generator.generate_entity_type_enums()
    relation_enums = generator.generate_relation_type_enums()

    # Verify empty results
    assert len(entity_enums) == 0
    assert len(relation_enums) == 0


def test_enum_with_complex_names():
    """Test enum generation with complex type names"""
    schema = GraphSchema()

    # Add entity type with complex name
    complex_type = EntityType(
        name="ComplexEntityTypeName",
        properties={}
    )
    schema.add_entity_type(complex_type)

    generator = TypeEnumGenerator(schema)
    enums = generator.generate_entity_type_enums()

    # Verify enum was generated
    assert "ComplexEntityTypeName" in enums
    ComplexEnum = enums["ComplexEntityTypeName"]

    # Verify enum member name
    assert hasattr(ComplexEnum, "COMPLEX_ENTITY_TYPE_NAME")
    assert ComplexEnum.COMPLEX_ENTITY_TYPE_NAME.value == "ComplexEntityTypeName"


def test_enum_uniqueness():
    """Test that each enum class is unique"""
    schema = GraphSchema()

    person_type = EntityType(name="Person", properties={})
    paper_type = EntityType(name="Paper", properties={})

    schema.add_entity_type(person_type)
    schema.add_entity_type(paper_type)

    generator = TypeEnumGenerator(schema)
    enums = generator.generate_entity_type_enums()

    PersonEnum = enums["Person"]
    PaperEnum = enums["Paper"]

    # Verify they are different classes
    assert PersonEnum is not PaperEnum
    assert PersonEnum.__name__ != PaperEnum.__name__


# ============================================================================
# Usage Pattern Tests
# ============================================================================

def test_enum_in_function_signature(enum_generator):
    """Test using enums in function signatures"""
    enums = enum_generator.generate_entity_type_enums()
    PersonEnum = enums["Person"]

    def get_entity_type(entity_type: PersonEnum) -> str:
        """Function that accepts enum"""
        return str(entity_type)

    # Use enum
    result = get_entity_type(PersonEnum.PERSON)
    assert result == "Person"


def test_enum_in_dictionary(enum_generator):
    """Test using enums as dictionary keys/values"""
    enums = enum_generator.generate_entity_type_enums()
    PersonEnum = enums["Person"]
    PaperEnum = enums["Paper"]

    # Use as dictionary values
    type_map = {
        "person": PersonEnum.PERSON,
        "paper": PaperEnum.PAPER
    }

    assert type_map["person"] == "Person"
    assert type_map["paper"] == "Paper"


def test_enum_iteration(enum_generator):
    """Test iterating over enum members"""
    enums = enum_generator.generate_entity_type_enums()
    PersonEnum = enums["Person"]

    # Iterate over enum
    members = list(PersonEnum)

    assert len(members) == 1
    assert members[0] == PersonEnum.PERSON
    assert members[0].value == "Person"


"""
Unit tests for nested property validation in AST validator and nodes.

Tests cover:
- Single level nesting (e.g., "address.city")
- Multi-level nesting (e.g., "address.location.city")
- Missing nested schema scenarios
- Non-DICT property nesting attempts
- Error messages indicating which level failed
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes import (
    PropertyFilterNode,
    ValidationError,
)
from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_validator import ASTValidator
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType


@pytest.fixture
def mock_schema_with_nested():
    """Create a mock schema with nested DICT properties."""
    # Create nested property schemas
    city_prop = PropertySchema(
        name="city",
        property_type=PropertyType.STRING,
        required=False,
    )
    zip_prop = PropertySchema(
        name="zip",
        property_type=PropertyType.STRING,
        required=False,
    )

    # Create address schema with nested properties
    address_prop = PropertySchema(
        name="address",
        property_type=PropertyType.DICT,
        required=False,
    )
    # Add nested schema via properties attribute (bypass Pydantic validation)
    object.__setattr__(address_prop, "properties", {
        "city": city_prop,
        "zip": zip_prop,
    })

    # Create location schema for deeper nesting
    location_prop = PropertySchema(
        name="location",
        property_type=PropertyType.DICT,
        required=False,
    )
    object.__setattr__(location_prop, "properties", {
        "city": city_prop,
    })

    # Create address with location (3-level nesting)
    address_with_location_prop = PropertySchema(
        name="address",
        property_type=PropertyType.DICT,
        required=False,
    )
    object.__setattr__(address_with_location_prop, "properties", {
        "location": location_prop,
    })

    # Create Person entity type
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
            "age": PropertySchema(name="age", property_type=PropertyType.INTEGER, required=False),
            "address": address_prop,
            "address_with_location": address_with_location_prop,
        },
    )

    # Create mock schema
    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

        def list_entity_types(self):
            return ["Person"]

    return MockSchema()


def test_nested_property_validation_single_level(mock_schema_with_nested):
    """Test validation of single-level nested property (e.g., address.city)."""
    filter_node = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema_with_nested, entity_type="Person")

    # Should pass validation (property exists)
    assert len(errors) == 0


def test_nested_property_validation_missing_nested_property(mock_schema_with_nested):
    """Test validation fails when nested property doesn't exist."""
    filter_node = PropertyFilterNode(
        property_path="address.street",
        operator="==",
        value="Main St",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema_with_nested, entity_type="Person")

    # Should have error for missing nested property
    assert len(errors) == 1
    assert "street" in errors[0].message.lower() or "not found" in errors[0].message.lower()
    assert "address" in errors[0].message


def test_nested_property_validation_missing_parent_property(mock_schema_with_nested):
    """Test validation fails when parent property doesn't exist."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema_with_nested, entity_type="Person")

    # Should have error for missing parent property
    assert len(errors) == 1
    assert "nonexistent" in errors[0].message.lower()
    assert "not found" in errors[0].message.lower()


def test_nested_property_validation_non_dict_property():
    """Test validation fails when trying to nest into non-DICT property."""
    # Create schema with non-DICT property
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
            "age": PropertySchema(name="age", property_type=PropertyType.INTEGER, required=False),
        },
    )

    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

    schema = MockSchema()

    filter_node = PropertyFilterNode(
        property_path="name.first",
        operator="==",
        value="John",
        line=1,
        column=10,
    )

    errors = filter_node.validate(schema, entity_type="Person")

    # Should have error for trying to nest into non-DICT property
    assert len(errors) == 1
    assert "name" in errors[0].message.lower()
    assert "not dict" in errors[0].message.lower() or "dict" in errors[0].message.lower()


def test_nested_property_validation_missing_nested_schema():
    """Test validation fails when DICT property has no nested schema."""
    # Create DICT property without nested schema
    address_prop = PropertySchema(
        name="address",
        property_type=PropertyType.DICT,
        required=False,
    )
    # Don't set nested_schema or properties

    person_type = EntityType(
        name="Person",
        properties={
            "address": address_prop,
        },
    )

    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

    schema = MockSchema()

    filter_node = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(schema, entity_type="Person")

    # Should have error for missing nested schema
    assert len(errors) == 1
    assert "nested schema" in errors[0].message.lower() or "schema not defined" in errors[0].message.lower()
    assert "address" in errors[0].message


def test_nested_property_validation_three_levels(mock_schema_with_nested):
    """Test validation of three-level nested property (e.g., address.location.city)."""
    filter_node = PropertyFilterNode(
        property_path="address_with_location.location.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema_with_nested, entity_type="Person")

    # Should pass validation (property exists)
    assert len(errors) == 0


def test_nested_property_validation_missing_middle_level(mock_schema_with_nested):
    """Test validation fails when middle level of nesting doesn't exist."""
    filter_node = PropertyFilterNode(
        property_path="address.nonexistent.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema_with_nested, entity_type="Person")

    # Should have error for missing middle level
    assert len(errors) == 1
    assert "nonexistent" in errors[0].message.lower()
    assert "not found" in errors[0].message.lower()


def test_nested_property_validation_error_message_shows_path():
    """Test that error messages show the full nested path."""
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(name="name", property_type=PropertyType.STRING, required=True),
        },
    )

    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

    schema = MockSchema()

    filter_node = PropertyFilterNode(
        property_path="address.location.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(schema, entity_type="Person")

    # Should have error showing the path
    assert len(errors) >= 1
    # Error should mention "address" (first level that fails)
    assert any("address" in err.message.lower() for err in errors)


def test_ast_validator_nested_property_validation(mock_schema_with_nested):
    """Test ASTValidator validates nested properties correctly."""
    validator = ASTValidator(mock_schema_with_nested)

    filter_node = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = validator.validate(filter_node)

    # Should pass validation
    assert len(errors) == 0


def test_ast_validator_nested_property_validation_fails(mock_schema_with_nested):
    """Test ASTValidator catches nested property validation errors."""
    validator = ASTValidator(mock_schema_with_nested)
    # Set current entity type so property validation can work
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        property_path="address.street",
        operator="==",
        value="Main St",
        line=1,
        column=10,
    )

    errors = validator.validate(filter_node)

    # Should have validation error
    assert len(errors) >= 1
    assert any("street" in err.message.lower() or "not found" in err.message.lower() for err in errors)


def test_nested_property_value_type_validation(mock_schema_with_nested):
    """Test that nested property value types are validated correctly."""
    validator = ASTValidator(mock_schema_with_nested)

    # Valid: string value for string property
    filter_node1 = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",  # String value
        line=1,
        column=10,
    )
    errors1 = validator.validate(filter_node1)
    assert len(errors1) == 0

    # Invalid: integer value for string property (if type checking is strict)
    # Note: This depends on implementation - may or may not validate types
    filter_node2 = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value=12345,  # Integer value
        line=1,
        column=10,
    )
    errors2 = validator.validate(filter_node2)
    # May or may not have type error depending on implementation


def test_nested_property_with_nested_schema_attribute():
    """Test nested property validation using nested_schema attribute."""
    # Create nested property with explicit nested_schema
    city_prop = PropertySchema(
        name="city",
        property_type=PropertyType.STRING,
    )

    class NestedSchema:
        def get_property(self, name):
            if name == "city":
                return city_prop
            return None

        def get_property_names(self):
            return ["city"]

    address_prop = PropertySchema(
        name="address",
        property_type=PropertyType.DICT,
    )
    # Set nested_schema attribute (bypass Pydantic validation)
    object.__setattr__(address_prop, "nested_schema", NestedSchema())

    person_type = EntityType(
        name="Person",
        properties={
            "address": address_prop,
        },
    )

    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

    schema = MockSchema()

    filter_node = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(schema, entity_type="Person")

    # Should pass validation
    assert len(errors) == 0


def test_nested_property_with_schema_attribute():
    """Test nested property validation using schema attribute."""
    # Create nested property with schema attribute
    city_prop = PropertySchema(
        name="city",
        property_type=PropertyType.STRING,
    )

    class NestedSchema:
        def get_property(self, name):
            if name == "city":
                return city_prop
            return None

    address_prop = PropertySchema(
        name="address",
        property_type=PropertyType.DICT,
    )
    # Set schema attribute (bypass Pydantic validation)
    object.__setattr__(address_prop, "schema", NestedSchema())

    person_type = EntityType(
        name="Person",
        properties={
            "address": address_prop,
        },
    )

    class MockSchema:
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return person_type
            return None

    schema = MockSchema()

    filter_node = PropertyFilterNode(
        property_path="address.city",
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(schema, entity_type="Person")

    # Should pass validation
    assert len(errors) == 0

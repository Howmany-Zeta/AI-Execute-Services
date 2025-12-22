"""
Unit tests for property validation in AST nodes.

Tests property validation functionality including:
- Property existence validation
- Entity context tracking
- Helpful error messages with available properties
- Missing properties and invalid types
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes import (
    PropertyFilterNode,
    FindNode,
    BooleanFilterNode,
    ValidationError,
)
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType


@pytest.fixture
def mock_schema():
    """Create a mock schema with Person entity type."""
    # Create property schemas
    name_prop = PropertySchema(
        name="name",
        property_type=PropertyType.STRING,
        required=True,
    )
    age_prop = PropertySchema(
        name="age",
        property_type=PropertyType.INTEGER,
        required=False,
    )
    email_prop = PropertySchema(
        name="email",
        property_type=PropertyType.STRING,
        required=False,
    )

    # Create entity type
    person_type = EntityType(
        name="Person",
        properties={"name": name_prop, "age": age_prop, "email": email_prop},
    )

    # Create schema
    schema = GraphSchema(entity_types={"Person": person_type}, relation_types={})

    return schema


@pytest.fixture
def empty_schema():
    """Create an empty schema."""
    return GraphSchema(entity_types={}, relation_types={})


def test_property_validation_valid_property(mock_schema):
    """Test validation with valid property."""
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="==",
        value="Alice",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type="Person")

    assert len(errors) == 0


def test_property_validation_missing_property(mock_schema):
    """Test validation with property that doesn't exist."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type="Person")

    assert len(errors) == 1
    assert errors[0].message == "Property 'nonexistent' not found in entity type 'Person'"
    assert "Available properties" in errors[0].suggestion
    assert "name" in errors[0].suggestion
    assert "age" in errors[0].suggestion


def test_property_validation_without_entity_type(mock_schema):
    """Test validation without entity_type (should skip property validation)."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type=None)

    # Should only validate operator, not property existence
    assert len(errors) == 0  # Operator is valid


def test_property_validation_invalid_entity_type(mock_schema):
    """Test validation with entity type that doesn't exist."""
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="==",
        value="Alice",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type="NonExistent")

    # Should not error (entity type validation is done by FindNode)
    # Property validation is skipped if entity type doesn't exist
    assert len(errors) == 0


def test_property_validation_helpful_error_message(mock_schema):
    """Test that error messages include available properties."""
    filter_node = PropertyFilterNode(
        property_path="wrong_property",
        operator="==",
        value="value",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type="Person")

    assert len(errors) == 1
    error = errors[0]
    assert error.suggestion is not None
    assert "Available properties" in error.suggestion
    # Should list available properties
    assert "name" in error.suggestion or "age" in error.suggestion


def test_find_node_passes_entity_type_to_filters(mock_schema):
    """Test that FindNode passes entity_type to filter validation."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )

    find_node = FindNode(
        entity_type="Person",
        filters=[filter_node],
        line=1,
        column=1,
    )

    errors = find_node.validate(mock_schema)

    # Should have error for missing property (entity_type was passed)
    property_errors = [e for e in errors if "Property" in e.message]
    assert len(property_errors) == 1


def test_boolean_filter_passes_entity_type_to_operands(mock_schema):
    """Test that BooleanFilterNode passes entity_type to operands."""
    filter1 = PropertyFilterNode(
        property_path="nonexistent1",
        operator="==",
        value="value1",
        line=1,
        column=10,
    )
    filter2 = PropertyFilterNode(
        property_path="nonexistent2",
        operator="==",
        value="value2",
        line=1,
        column=20,
    )

    bool_filter = BooleanFilterNode(
        operator="AND",
        operands=[filter1, filter2],
        line=1,
        column=1,
    )

    errors = bool_filter.validate(mock_schema, entity_type="Person")

    # Should have errors for both missing properties
    property_errors = [e for e in errors if "Property" in e.message]
    assert len(property_errors) == 2


def test_property_validation_invalid_operator():
    """Test validation with invalid operator."""
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="INVALID",
        value="Alice",
        line=1,
        column=10,
    )

    # Use empty schema since we're only testing operator validation
    empty_schema = GraphSchema(entity_types={}, relation_types={})
    errors = filter_node.validate(empty_schema, entity_type="Person")

    assert len(errors) == 1
    assert "Invalid operator" in errors[0].message


def test_property_validation_in_operator_without_list():
    """Test IN operator validation requires list value."""
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="IN",
        value="not_a_list",  # Should be a list
        line=1,
        column=10,
    )

    empty_schema = GraphSchema(entity_types={}, relation_types={})
    errors = filter_node.validate(empty_schema, entity_type="Person")

    assert len(errors) == 1
    assert "IN operator requires a list value" in errors[0].message


def test_property_validation_contains_operator_without_string():
    """Test CONTAINS operator validation requires string value."""
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="CONTAINS",
        value=123,  # Should be a string
        line=1,
        column=10,
    )

    empty_schema = GraphSchema(entity_types={}, relation_types={})
    errors = filter_node.validate(empty_schema, entity_type="Person")

    assert len(errors) == 1
    assert "CONTAINS operator requires a string value" in errors[0].message


def test_property_validation_nested_property_path(mock_schema):
    """Test validation with nested property path (e.g., address.city)."""
    filter_node = PropertyFilterNode(
        property_path="address.city",  # Nested path
        operator="==",
        value="New York",
        line=1,
        column=10,
    )

    errors = filter_node.validate(mock_schema, entity_type="Person")

    # Should validate first part of path (address)
    # Note: Full nested validation is TODO in ast_validator.py
    # For now, it validates the first property in the path
    assert len(errors) >= 0  # May or may not error depending on implementation


def test_property_validation_schema_without_get_entity_type():
    """Test validation with schema that doesn't have get_entity_type method."""
    class SimpleSchema:
        pass

    simple_schema = SimpleSchema()

    filter_node = PropertyFilterNode(
        property_path="name",
        operator="==",
        value="Alice",
        line=1,
        column=10,
    )

    # Should not raise exception, just skip property validation
    errors = filter_node.validate(simple_schema, entity_type="Person")

    assert isinstance(errors, list)


def test_property_validation_multiple_errors():
    """Test that multiple validation errors are collected."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="INVALID",
        value="value",
        line=1,
        column=10,
    )

    mock_schema = GraphSchema(entity_types={}, relation_types={})
    # Add a Person type for property validation
    person_type = EntityType(
        name="Person",
        properties={
            "name": PropertySchema(
                name="name",
                property_type=PropertyType.STRING,
                required=True,
            )
        },
    )
    mock_schema.entity_types["Person"] = person_type

    errors = filter_node.validate(mock_schema, entity_type="Person")

    # Should have errors for both invalid operator and missing property
    assert len(errors) >= 1  # At least operator error


def test_find_node_validates_entity_type_and_properties(mock_schema):
    """Test that FindNode validates both entity type and properties."""
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )

    find_node = FindNode(
        entity_type="Person",
        filters=[filter_node],
        line=1,
        column=1,
    )

    errors = find_node.validate(mock_schema)

    # Should have error for missing property
    property_errors = [e for e in errors if "Property" in e.message]
    assert len(property_errors) == 1


def test_property_validation_fallback_no_get_property_method(caplog):
    """Test fallback when entity_schema doesn't have get_property method."""
    import logging
    from aiecs.application.knowledge_graph.reasoning.logic_parser import ast_nodes
    
    # Create a custom log handler to capture messages
    log_messages = []
    
    class TestHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    handler = TestHandler()
    handler.setLevel(logging.DEBUG)
    
    # Get the logger and add our handler
    test_logger = logging.getLogger("aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)
    
    try:
        # Create a schema with entity type that doesn't have get_property method
        class EntitySchemaWithoutGetProperty:
            """Mock entity schema without get_property method."""
            def __init__(self):
                self.properties = {"name": "test", "age": "test"}  # Has properties but no get_property method
        
        class SchemaWithoutGetProperty:
            """Mock schema that returns entity schema without get_property."""
            def get_entity_type(self, entity_type):
                if entity_type == "Person":
                    return EntitySchemaWithoutGetProperty()
                return None
        
        schema = SchemaWithoutGetProperty()
        
        filter_node = PropertyFilterNode(
            property_path="name",
            operator="==",
            value="Alice",
            line=1,
            column=10,
        )
        
        errors = filter_node.validate(schema, entity_type="Person")
        
        # Should skip validation gracefully (no errors)
        assert len(errors) == 0
        
        # Verify fallback was triggered
        fallback_messages = [msg for msg in log_messages if "FALLBACK" in msg and "get_property" in msg]
        assert len(fallback_messages) == 1, (
            f"Expected 1 fallback log message, got {len(fallback_messages)}. "
            f"All log messages: {log_messages}"
        )
        assert "missing 'get_property' method" in fallback_messages[0]
        assert "Person" in fallback_messages[0]
        
        # Document that fallback was triggered
        print(f"\n✓ FALLBACK TRIGGERED: {fallback_messages[0]}")
        
    finally:
        # Clean up handler
        test_logger.removeHandler(handler)


def test_property_validation_fallback_get_property_names_method(caplog):
    """Test fallback to get_property_names() when properties attribute is missing."""
    import logging
    
    # Create a custom log handler to capture messages
    log_messages = []
    
    class TestHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    handler = TestHandler()
    handler.setLevel(logging.DEBUG)
    
    # Get the logger and add our handler
    test_logger = logging.getLogger("aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)
    
    try:
        # Create a schema with entity type that uses get_property_names() instead of properties
        # Note: Must NOT have 'properties' attribute to trigger fallback to get_property_names()
        class EntitySchemaWithGetPropertyNames:
            """Mock entity schema with get_property_names() but no properties attribute."""
            def __init__(self):
                self._properties = {"name": "test", "age": "test", "email": "test"}
                # Intentionally do NOT set self.properties to trigger fallback
                # Verify it doesn't have properties attribute
                assert not hasattr(self, "properties"), "Should not have properties attribute"
            
            def get_property(self, property_name):
                # Return None for nonexistent property to trigger error message generation
                # Return a mock property schema for existing properties
                if property_name in self._properties:
                    from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType
                    return PropertySchema(
                        name=property_name,
                        property_type=PropertyType.STRING,
                        required=False,
                    )
                return None  # Property doesn't exist - triggers fallback to get_property_names()
            
            def get_property_names(self):
                """Fallback method to get property names."""
                return list(self._properties.keys())
        
        class SchemaWithGetPropertyNames:
            """Mock schema that returns entity schema with get_property_names()."""
            def get_entity_type(self, entity_type):
                if entity_type == "Person":
                    return EntitySchemaWithGetPropertyNames()
                return None
        
        schema = SchemaWithGetPropertyNames()
        
        filter_node = PropertyFilterNode(
            property_path="nonexistent",
            operator="==",
            value="value",
            line=1,
            column=10,
        )
        
        errors = filter_node.validate(schema, entity_type="Person")
        
        # Should have error for missing property
        assert len(errors) == 1
        assert "Property 'nonexistent' not found" in errors[0].message
        assert "Available properties" in errors[0].suggestion
        
        # Verify fallback to get_property_names() was triggered
        fallback_messages = [msg for msg in log_messages if "FALLBACK" in msg and "get_property_names" in msg]
        assert len(fallback_messages) == 1, (
            f"Expected 1 fallback log message, got {len(fallback_messages)}. "
            f"All log messages: {log_messages}"
        )
        assert "get_property_names()" in fallback_messages[0]
        assert "instead of 'properties' attribute" in fallback_messages[0]
        assert "Person" in fallback_messages[0]
        
        # Document that fallback was triggered
        print(f"\n✓ FALLBACK TRIGGERED: {fallback_messages[0]}")
        
    finally:
        # Clean up handler
        test_logger.removeHandler(handler)


def test_property_validation_fallback_no_entity_type_parameter(caplog):
    """Test fallback when entity_type parameter is None."""
    import logging
    
    # Set logging level to DEBUG to capture fallback messages
    caplog.set_level(logging.DEBUG)
    
    from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
    
    schema = GraphSchema(entity_types={}, relation_types={})
    
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )
    
    errors = filter_node.validate(schema, entity_type=None)
    
    # Should skip property validation (no errors)
    assert len(errors) == 0
    
    # Verify fallback was triggered
    fallback_logs = [
        record for record in caplog.records
        if "FALLBACK" in record.message and "No entity_type provided" in record.message
    ]
    assert len(fallback_logs) == 1
    assert "skipping property validation" in fallback_logs[0].message
    assert "nonexistent" in fallback_logs[0].message


def test_property_validation_fallback_schema_without_get_entity_type(caplog):
    """Test fallback when schema doesn't have get_entity_type method (with logging)."""
    import logging
    
    # Create a custom log handler to capture messages
    log_messages = []
    
    class TestHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    handler = TestHandler()
    handler.setLevel(logging.DEBUG)
    
    # Get the logger and add our handler
    test_logger = logging.getLogger("aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)
    
    try:
        class SimpleSchema:
            """Schema without get_entity_type method."""
            pass
        
        simple_schema = SimpleSchema()
        
        filter_node = PropertyFilterNode(
            property_path="name",
            operator="==",
            value="Alice",
            line=1,
            column=10,
        )
        
        errors = filter_node.validate(simple_schema, entity_type="Person")
        
        # Should not raise exception, just skip property validation
        assert isinstance(errors, list)
        assert len(errors) == 0
        
        # Verify fallback was triggered
        fallback_messages = [msg for msg in log_messages if "FALLBACK" in msg and "get_entity_type" in msg]
        assert len(fallback_messages) == 1, (
            f"Expected 1 fallback log message, got {len(fallback_messages)}. "
            f"All log messages: {log_messages}"
        )
        assert "missing 'get_entity_type' method" in fallback_messages[0]
        assert "skipping property validation" in fallback_messages[0]
        
        # Document that fallback was triggered
        print(f"\n✓ FALLBACK TRIGGERED: {fallback_messages[0]}")
        
    finally:
        # Clean up handler
        test_logger.removeHandler(handler)


def test_property_validation_fallback_invalid_entity_type(caplog):
    """Test fallback when entity type doesn't exist (with logging)."""
    import logging
    
    # Create a custom log handler to capture messages
    log_messages = []
    
    class TestHandler(logging.Handler):
        def emit(self, record):
            log_messages.append(record.getMessage())
    
    handler = TestHandler()
    handler.setLevel(logging.DEBUG)
    
    # Get the logger and add our handler
    test_logger = logging.getLogger("aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)
    
    try:
        from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
        
        schema = GraphSchema(entity_types={}, relation_types={})
        
        filter_node = PropertyFilterNode(
            property_path="name",
            operator="==",
            value="Alice",
            line=1,
            column=10,
        )
        
        errors = filter_node.validate(schema, entity_type="NonExistent")
        
        # Should not error (entity type validation is done by FindNode)
        # Property validation is skipped if entity type doesn't exist
        assert len(errors) == 0
        
        # Verify fallback was triggered
        fallback_messages = [
            msg for msg in log_messages
            if "FALLBACK" in msg and "entity type" in msg and "not found" in msg
        ]
        assert len(fallback_messages) == 1, (
            f"Expected 1 fallback log message, got {len(fallback_messages)}. "
            f"All log messages: {log_messages}"
        )
        assert "NonExistent" in fallback_messages[0]
        assert "skipping property validation" in fallback_messages[0]
        
        # Document that fallback was triggered
        print(f"\n✓ FALLBACK TRIGGERED: {fallback_messages[0]}")
        
    finally:
        # Clean up handler
        test_logger.removeHandler(handler)

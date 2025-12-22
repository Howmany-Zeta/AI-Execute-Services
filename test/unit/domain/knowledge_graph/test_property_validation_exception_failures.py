"""
Tests for main method failures (exceptions) in property validation.

These tests verify that when main methods exist but raise exceptions,
the code handles them gracefully or falls back appropriately.
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes import (
    PropertyFilterNode,
    FindNode,
    ValidationError,
)
from aiecs.domain.knowledge_graph.schema.graph_schema import GraphSchema
from aiecs.domain.knowledge_graph.schema.entity_type import EntityType
from aiecs.domain.knowledge_graph.schema.property_schema import PropertySchema, PropertyType


def test_property_validation_get_entity_type_raises_exception():
    """Test when get_entity_type() method exists but raises exception."""
    class SchemaWithFailingGetEntityType:
        """Schema where get_entity_type raises exception."""
        def get_entity_type(self, entity_type):
            raise RuntimeError("Database connection failed")
    
    schema = SchemaWithFailingGetEntityType()
    
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="==",
        value="Alice",
        line=1,
        column=10,
    )
    
    # Should raise exception (no exception handling in current implementation)
    with pytest.raises(RuntimeError, match="Database connection failed"):
        filter_node.validate(schema, entity_type="Person")


def test_property_validation_get_property_raises_exception():
    """Test when get_property() method exists but raises exception."""
    class EntitySchemaWithFailingGetProperty:
        """Entity schema where get_property raises exception."""
        def __init__(self):
            self.properties = {"name": "test"}
        
        def get_property(self, property_name):
            raise ValueError(f"Property '{property_name}' access denied")
    
    class SchemaWithFailingGetProperty:
        """Schema that returns entity schema with failing get_property."""
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return EntitySchemaWithFailingGetProperty()
            return None
    
    schema = SchemaWithFailingGetProperty()
    
    filter_node = PropertyFilterNode(
        property_path="name",
        operator="==",
        value="Alice",
        line=1,
        column=10,
    )
    
    # Should raise exception (no exception handling in current implementation)
    with pytest.raises(ValueError, match="Property 'name' access denied"):
        filter_node.validate(schema, entity_type="Person")


def test_property_validation_get_property_names_raises_exception():
    """Test when get_property_names() method exists but raises exception."""
    class EntitySchemaWithFailingGetPropertyNames:
        """Entity schema where get_property_names raises exception."""
        def __init__(self):
            self._properties = {"name": "test"}
        
        def get_property(self, property_name):
            return None  # Property doesn't exist
        
        def get_property_names(self):
            raise RuntimeError("Cannot enumerate properties")
    
    class SchemaWithFailingGetPropertyNames:
        """Schema that returns entity schema with failing get_property_names."""
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return EntitySchemaWithFailingGetPropertyNames()
            return None
    
    schema = SchemaWithFailingGetPropertyNames()
    
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )
    
    # Should raise exception (no exception handling in current implementation)
    with pytest.raises(RuntimeError, match="Cannot enumerate properties"):
        filter_node.validate(schema, entity_type="Person")


def test_property_validation_properties_attribute_access_fails():
    """Test when properties attribute exists but accessing it raises exception."""
    class EntitySchemaWithFailingProperties:
        """Entity schema where properties attribute access raises exception."""
        def __init__(self):
            self._properties = {"name": "test"}
        
        @property
        def properties(self):
            raise RuntimeError("Properties access denied")
        
        def get_property(self, property_name):
            return None  # Property doesn't exist
    
    class SchemaWithFailingProperties:
        """Schema that returns entity schema with failing properties access."""
        def get_entity_type(self, entity_type):
            if entity_type == "Person":
                return EntitySchemaWithFailingProperties()
            return None
    
    schema = SchemaWithFailingProperties()
    
    filter_node = PropertyFilterNode(
        property_path="nonexistent",
        operator="==",
        value="value",
        line=1,
        column=10,
    )
    
    # Should raise exception when accessing properties.keys()
    with pytest.raises(RuntimeError, match="Properties access denied"):
        filter_node.validate(schema, entity_type="Person")

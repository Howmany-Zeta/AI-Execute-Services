"""
Unit Tests for AST Nodes

Tests for AST node creation, validation, and conversion.

Run with: python -m pytest test_ast_nodes.py -v
"""

import pytest
from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes import (
    ASTNode,
    QueryNode,
    FindNode,
    TraversalNode,
    FilterNode,
    PropertyFilterNode,
    BooleanFilterNode,
    ValidationError
)


# Mock schema for testing
class MockSchema:
    """Mock schema manager for testing"""
    
    def __init__(self):
        self.entity_types = {"Person", "Paper", "Company"}
        self.relation_types = {"AuthoredBy", "WorksAt", "PublishedIn"}
    
    def has_entity_type(self, entity_type: str) -> bool:
        return entity_type in self.entity_types
    
    def has_relation_type(self, relation_type: str) -> bool:
        return relation_type in self.relation_types
    
    def get_entity_types(self):
        return sorted(self.entity_types)


# Mock QueryContext for testing
class MockQueryContext:
    """Mock query context for testing"""
    
    def __init__(self, schema=None):
        self.schema = schema or MockSchema()
        self.variables = {}


class TestFindNode:
    """Tests for FindNode"""
    
    def test_create_simple_find_node(self):
        """Test creating a simple FindNode"""
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person"
        )
        assert node.entity_type == "Person"
        assert node.entity_name is None
        assert node.filters == []
    
    def test_create_find_node_with_name(self):
        """Test creating FindNode with entity name"""
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person",
            entity_name="Alice"
        )
        assert node.entity_type == "Person"
        assert node.entity_name == "Alice"
    
    def test_create_find_node_with_filters(self):
        """Test creating FindNode with filters"""
        filter_node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="age",
            operator=">",
            value=30
        )
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person",
            filters=[filter_node]
        )
        assert len(node.filters) == 1
        assert node.filters[0].property_path == "age"
    
    def test_find_node_validate_valid_entity(self):
        """Test validation with valid entity type"""
        schema = MockSchema()
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person"
        )
        errors = node.validate(schema)
        assert len(errors) == 0
    
    def test_find_node_validate_invalid_entity(self):
        """Test validation with invalid entity type"""
        schema = MockSchema()
        node = FindNode(
            line=1,
            column=1,
            entity_type="InvalidType"
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "InvalidType" in errors[0].message
    
    def test_find_node_repr(self):
        """Test string representation"""
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person",
            entity_name="Alice"
        )
        repr_str = repr(node)
        assert "Person" in repr_str
        assert "Alice" in repr_str
    
    def test_find_node_immutable(self):
        """Test that FindNode is immutable"""
        node = FindNode(
            line=1,
            column=1,
            entity_type="Person"
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            node.entity_type = "Paper"


class TestTraversalNode:
    """Tests for TraversalNode"""
    
    def test_create_traversal_node(self):
        """Test creating a TraversalNode"""
        node = TraversalNode(
            line=1,
            column=10,
            relation_type="AuthoredBy"
        )
        assert node.relation_type == "AuthoredBy"
        assert node.direction == "outgoing"
    
    def test_create_traversal_node_with_direction(self):
        """Test creating TraversalNode with direction"""
        node = TraversalNode(
            line=1,
            column=10,
            relation_type="AuthoredBy",
            direction="incoming"
        )
        assert node.direction == "incoming"
    
    def test_traversal_node_validate_valid_relation(self):
        """Test validation with valid relation type"""
        schema = MockSchema()
        node = TraversalNode(
            line=1,
            column=10,
            relation_type="AuthoredBy"
        )
        errors = node.validate(schema)
        assert len(errors) == 0
    
    def test_traversal_node_validate_invalid_relation(self):
        """Test validation with invalid relation type"""
        schema = MockSchema()
        node = TraversalNode(
            line=1,
            column=10,
            relation_type="InvalidRelation"
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "InvalidRelation" in errors[0].message
    
    def test_traversal_node_validate_invalid_direction(self):
        """Test validation with invalid direction"""
        schema = MockSchema()
        node = TraversalNode(
            line=1,
            column=10,
            relation_type="AuthoredBy",
            direction="invalid"
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "direction" in errors[0].message.lower()


class TestPropertyFilterNode:
    """Tests for PropertyFilterNode"""

    def test_create_property_filter_node(self):
        """Test creating a PropertyFilterNode"""
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="age",
            operator=">",
            value=30
        )
        assert node.property_path == "age"
        assert node.operator == ">"
        assert node.value == 30

    def test_property_filter_to_dict_eq(self):
        """Test conversion to filter dict with == operator"""
        context = MockQueryContext()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="name",
            operator="==",
            value="Alice"
        )
        filter_dict = node.to_filter_dict(context)
        assert filter_dict == {"name": {"$eq": "Alice"}}

    def test_property_filter_to_dict_gt(self):
        """Test conversion to filter dict with > operator"""
        context = MockQueryContext()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="age",
            operator=">",
            value=30
        )
        filter_dict = node.to_filter_dict(context)
        assert filter_dict == {"age": {"$gt": 30}}

    def test_property_filter_to_dict_in(self):
        """Test conversion to filter dict with IN operator"""
        context = MockQueryContext()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="status",
            operator="IN",
            value=["active", "pending"]
        )
        filter_dict = node.to_filter_dict(context)
        assert filter_dict == {"status": {"$in": ["active", "pending"]}}

    def test_property_filter_to_dict_contains(self):
        """Test conversion to filter dict with CONTAINS operator"""
        context = MockQueryContext()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="title",
            operator="CONTAINS",
            value="machine learning"
        )
        filter_dict = node.to_filter_dict(context)
        assert filter_dict == {"title": {"$regex": "machine learning"}}

    def test_property_filter_validate_valid(self):
        """Test validation with valid filter"""
        schema = MockSchema()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="age",
            operator=">",
            value=30
        )
        errors = node.validate(schema)
        assert len(errors) == 0

    def test_property_filter_validate_invalid_operator(self):
        """Test validation with invalid operator"""
        schema = MockSchema()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="age",
            operator="INVALID",
            value=30
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "operator" in errors[0].message.lower()

    def test_property_filter_validate_in_with_non_list(self):
        """Test validation with IN operator and non-list value"""
        schema = MockSchema()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="status",
            operator="IN",
            value="active"  # Should be a list
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "list" in errors[0].message.lower()

    def test_property_filter_validate_contains_with_non_string(self):
        """Test validation with CONTAINS operator and non-string value"""
        schema = MockSchema()
        node = PropertyFilterNode(
            line=1,
            column=20,
            property_path="title",
            operator="CONTAINS",
            value=123  # Should be a string
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "string" in errors[0].message.lower()


class TestBooleanFilterNode:
    """Tests for BooleanFilterNode"""

    def test_create_boolean_filter_node(self):
        """Test creating a BooleanFilterNode"""
        operand1 = PropertyFilterNode(
            line=1, column=20,
            property_path="age", operator=">", value=30
        )
        operand2 = PropertyFilterNode(
            line=1, column=30,
            property_path="status", operator="==", value="active"
        )
        node = BooleanFilterNode(
            line=1,
            column=20,
            operator="AND",
            operands=[operand1, operand2]
        )
        assert node.operator == "AND"
        assert len(node.operands) == 2

    def test_boolean_filter_to_dict_and(self):
        """Test conversion to filter dict with AND operator"""
        context = MockQueryContext()
        operand1 = PropertyFilterNode(
            line=1, column=20,
            property_path="age", operator=">", value=30
        )
        operand2 = PropertyFilterNode(
            line=1, column=30,
            property_path="status", operator="==", value="active"
        )
        node = BooleanFilterNode(
            line=1, column=20,
            operator="AND",
            operands=[operand1, operand2]
        )
        filter_dict = node.to_filter_dict(context)
        assert "$and" in filter_dict
        assert len(filter_dict["$and"]) == 2

    def test_boolean_filter_to_dict_or(self):
        """Test conversion to filter dict with OR operator"""
        context = MockQueryContext()
        operand1 = PropertyFilterNode(
            line=1, column=20,
            property_path="name", operator="==", value="Alice"
        )
        operand2 = PropertyFilterNode(
            line=1, column=30,
            property_path="name", operator="==", value="Bob"
        )
        node = BooleanFilterNode(
            line=1, column=20,
            operator="OR",
            operands=[operand1, operand2]
        )
        filter_dict = node.to_filter_dict(context)
        assert "$or" in filter_dict
        assert len(filter_dict["$or"]) == 2

    def test_boolean_filter_to_dict_not(self):
        """Test conversion to filter dict with NOT operator"""
        context = MockQueryContext()
        operand = PropertyFilterNode(
            line=1, column=20,
            property_path="age", operator="<", value=18
        )
        node = BooleanFilterNode(
            line=1, column=20,
            operator="NOT",
            operands=[operand]
        )
        filter_dict = node.to_filter_dict(context)
        assert "$not" in filter_dict

    def test_boolean_filter_validate_valid(self):
        """Test validation with valid boolean filter"""
        schema = MockSchema()
        operand1 = PropertyFilterNode(
            line=1, column=20,
            property_path="age", operator=">", value=30
        )
        operand2 = PropertyFilterNode(
            line=1, column=30,
            property_path="status", operator="==", value="active"
        )
        node = BooleanFilterNode(
            line=1, column=20,
            operator="AND",
            operands=[operand1, operand2]
        )
        errors = node.validate(schema)
        assert len(errors) == 0

    def test_boolean_filter_validate_invalid_operator(self):
        """Test validation with invalid boolean operator"""
        schema = MockSchema()
        operand = PropertyFilterNode(
            line=1, column=20,
            property_path="age", operator=">", value=30
        )
        node = BooleanFilterNode(
            line=1, column=20,
            operator="INVALID",
            operands=[operand]
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "operator" in errors[0].message.lower()

    def test_boolean_filter_validate_no_operands(self):
        """Test validation with no operands"""
        schema = MockSchema()
        node = BooleanFilterNode(
            line=1, column=20,
            operator="AND",
            operands=[]
        )
        errors = node.validate(schema)
        assert len(errors) == 1
        assert "operand" in errors[0].message.lower()


class TestQueryNode:
    """Tests for QueryNode"""

    def test_create_query_node(self):
        """Test creating a QueryNode"""
        find = FindNode(
            line=1, column=1,
            entity_type="Person"
        )
        node = QueryNode(
            line=1, column=1,
            find=find
        )
        assert node.find.entity_type == "Person"
        assert node.traversals == []

    def test_create_query_node_with_traversals(self):
        """Test creating QueryNode with traversals"""
        find = FindNode(
            line=1, column=1,
            entity_type="Person"
        )
        traversal = TraversalNode(
            line=1, column=10,
            relation_type="AuthoredBy"
        )
        node = QueryNode(
            line=1, column=1,
            find=find,
            traversals=[traversal]
        )
        assert len(node.traversals) == 1
        assert node.traversals[0].relation_type == "AuthoredBy"

    def test_query_node_validate(self):
        """Test validation of complete query"""
        schema = MockSchema()
        find = FindNode(
            line=1, column=1,
            entity_type="Person"
        )
        traversal = TraversalNode(
            line=1, column=10,
            relation_type="AuthoredBy"
        )
        node = QueryNode(
            line=1, column=1,
            find=find,
            traversals=[traversal]
        )
        errors = node.validate(schema)
        assert len(errors) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


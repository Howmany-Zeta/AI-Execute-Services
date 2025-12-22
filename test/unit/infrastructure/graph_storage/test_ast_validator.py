"""
Unit Tests for AST Validator

Tests validation of AST nodes against schema including entity types,
properties, relation types, property types, and relation endpoints.

Phase: 2.4 - Logic Query Parser
Task: 3.1 - Implement AST Validator
Version: 1.0
"""

import sys
from pathlib import Path
from typing import Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.application.knowledge_graph.reasoning.logic_parser import (
    ASTValidator,
    QueryNode,
    FindNode,
    TraversalNode,
    PropertyFilterNode,
    BooleanFilterNode,
    ValidationError,
)


# ============================================================================
# Mock Schema for Testing
# ============================================================================

class MockPropertySchema:
    """Mock property schema for testing"""
    def __init__(self, name: str, property_type: str, required: bool = False):
        self.name = name
        self.property_type = MockPropertyType(property_type)
        self.required = required


class MockPropertyType:
    """Mock property type for testing"""
    def __init__(self, type_name: str):
        self.value = type_name
        self.name = type_name


class MockEntityType:
    """Mock entity type for testing"""
    def __init__(self, name: str, properties: dict):
        self.name = name
        self.properties = properties
    
    def get_property(self, property_name: str) -> Optional[MockPropertySchema]:
        return self.properties.get(property_name)


class MockRelationType:
    """Mock relation type for testing"""
    def __init__(self, name: str, source_types: List[str], target_types: List[str]):
        self.name = name
        self.source_entity_types = source_types
        self.target_entity_types = target_types


class MockSchema:
    """Mock schema manager for testing"""
    def __init__(self):
        # Define entity types
        self.entity_types = {
            "Person": MockEntityType("Person", {
                "name": MockPropertySchema("name", "STRING", required=True),
                "age": MockPropertySchema("age", "INTEGER"),
                "email": MockPropertySchema("email", "STRING"),
                "active": MockPropertySchema("active", "BOOLEAN"),
            }),
            "Paper": MockEntityType("Paper", {
                "title": MockPropertySchema("title", "STRING", required=True),
                "year": MockPropertySchema("year", "INTEGER"),
                "citations": MockPropertySchema("citations", "INTEGER"),
            }),
            "Company": MockEntityType("Company", {
                "name": MockPropertySchema("name", "STRING", required=True),
                "founded": MockPropertySchema("founded", "INTEGER"),
            }),
        }
        
        # Define relation types
        self.relation_types = {
            "AuthoredBy": MockRelationType("AuthoredBy", ["Paper"], ["Person"]),
            "WorksFor": MockRelationType("WorksFor", ["Person"], ["Company"]),
            "Knows": MockRelationType("Knows", ["Person"], ["Person"]),
        }
    
    def get_entity_type(self, type_name: str) -> Optional[MockEntityType]:
        return self.entity_types.get(type_name)
    
    def list_entity_types(self) -> List[str]:
        return list(self.entity_types.keys())
    
    def get_relation_type(self, type_name: str) -> Optional[MockRelationType]:
        return self.relation_types.get(type_name)
    
    def list_relation_types(self) -> List[str]:
        return list(self.relation_types.keys())


# ============================================================================
# Test Functions
# ============================================================================

def test_validator_initialization():
    """Test validator can be initialized with schema"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    assert validator is not None
    assert validator.schema is schema
    print("✓ Validator initialization works")


def test_valid_entity_type():
    """Test validation of valid entity type"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    
    find_node = FindNode(
        line=1,
        column=1,
        entity_type="Person",
        filters=[]
    )
    
    errors = validator.validate_find_node(find_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Valid entity type validation works")


def test_invalid_entity_type():
    """Test validation of invalid entity type"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    
    find_node = FindNode(
        line=1,
        column=1,
        entity_type="InvalidType",
        filters=[]
    )
    
    errors = validator.validate_find_node(find_node)
    assert len(errors) > 0, "Expected validation error"
    assert "InvalidType" in errors[0].message
    assert "not found" in errors[0].message
    print("✓ Invalid entity type validation works")


def test_valid_property():
    """Test validation of valid property"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="age",
        operator=">",
        value=30
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Valid property validation works")


def test_invalid_property():
    """Test validation of invalid property"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="invalid_property",
        operator="==",
        value="test"
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) > 0, "Expected validation error"
    assert "invalid_property" in errors[0].message
    assert "not found" in errors[0].message
    print("✓ Invalid property validation works")


def test_valid_relation_type():
    """Test validation of valid relation type"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    traversal_node = TraversalNode(
        line=1,
        column=1,
        relation_type="AuthoredBy",
        direction="outgoing"
    )

    errors = validator.validate_relation_type("AuthoredBy", 1, 1)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Valid relation type validation works")


def test_invalid_relation_type():
    """Test validation of invalid relation type"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    errors = validator.validate_relation_type("InvalidRelation", 1, 1)
    assert len(errors) > 0, "Expected validation error"
    assert "InvalidRelation" in errors[0].message
    assert "not found" in errors[0].message
    print("✓ Invalid relation type validation works")


def test_property_type_mismatch():
    """Test validation of property type mismatch"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="age",
        operator=">",
        value="not_a_number"  # Should be integer
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) > 0, "Expected validation error"
    # Check for type mismatch error
    type_errors = [e for e in errors if "expects" in e.message.lower()]
    assert len(type_errors) > 0, f"Expected type mismatch error, got {errors}"
    print("✓ Property type mismatch validation works")


def test_relation_endpoint_validation_outgoing():
    """Test validation of relation endpoints (outgoing)"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Paper"

    # Paper -> AuthoredBy -> Person (valid)
    errors = validator.validate_relation_endpoints("AuthoredBy", "Paper", "outgoing", 1, 1)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Relation endpoint validation (outgoing) works")


def test_relation_endpoint_validation_invalid():
    """Test validation of invalid relation endpoints"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    # Person -> AuthoredBy -> ? (invalid: Person cannot be source of AuthoredBy)
    errors = validator.validate_relation_endpoints("AuthoredBy", "Person", "outgoing", 1, 1)
    assert len(errors) > 0, "Expected validation error"
    assert "cannot be source" in errors[0].message
    print("✓ Invalid relation endpoint validation works")


def test_in_operator_with_list():
    """Test IN operator with list value"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="name",
        operator="IN",
        value=["Alice", "Bob"]
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ IN operator with list validation works")


def test_in_operator_without_list():
    """Test IN operator without list value"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="name",
        operator="IN",
        value="not_a_list"
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) > 0, "Expected validation error"
    assert "requires a list" in errors[0].message
    print("✓ IN operator without list validation works")


def test_contains_operator_with_string():
    """Test CONTAINS operator with string value"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type="Paper"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="title",
        operator="CONTAINS",
        value="machine learning"
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ CONTAINS operator with string validation works")


def test_contains_operator_without_string():
    """Test CONTAINS operator without string value"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Paper"

    filter_node = PropertyFilterNode(
        line=1,
        column=1,
        property_path="title",
        operator="CONTAINS",
        value=123
    )

    errors = validator.validate_property_filter_node(filter_node)
    assert len(errors) > 0, f"Expected validation error, got {len(errors)} errors: {errors}"
    # Check for CONTAINS string requirement error
    contains_errors = [e for e in errors if "requires a string" in e.message.lower()]
    assert len(contains_errors) > 0, f"Expected 'requires a string' error, got: {[e.message for e in errors]}"
    print("✓ CONTAINS operator without string validation works")


def test_boolean_filter_validation():
    """Test validation of boolean filter node"""
    schema = MockSchema()
    validator = ASTValidator(schema)
    validator.current_entity_type = "Person"

    filter1 = PropertyFilterNode(line=1, column=1, property_path="age", operator=">", value=30)
    filter2 = PropertyFilterNode(line=1, column=1, property_path="active", operator="==", value=True)

    boolean_filter = BooleanFilterNode(
        line=1,
        column=1,
        operator="AND",
        operands=[filter1, filter2]
    )

    errors = validator.validate_boolean_filter_node(boolean_filter)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Boolean filter validation works")


def test_invalid_boolean_operator():
    """Test validation of invalid boolean operator"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    boolean_filter = BooleanFilterNode(
        line=1,
        column=1,
        operator="INVALID",
        operands=[]
    )

    errors = validator.validate_boolean_filter_node(boolean_filter)
    assert len(errors) > 0, "Expected validation error"
    assert "INVALID" in errors[0].message
    print("✓ Invalid boolean operator validation works")


def test_query_node_validation():
    """Test validation of complete query node"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    find_node = FindNode(
        line=1,
        column=1,
        entity_type="Person",
        filters=[
            PropertyFilterNode(line=1, column=1, property_path="age", operator=">", value=30)
        ]
    )

    query_node = QueryNode(
        line=1,
        column=1,
        find=find_node,
        traversals=[]
    )

    errors = validator.validate_query_node(query_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Query node validation works")


def test_error_accumulation():
    """Test that validator accumulates multiple errors"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    # Create a query with multiple errors
    find_node = FindNode(
        line=1,
        column=1,
        entity_type="InvalidType",  # Error 1: invalid entity type
        filters=[
            PropertyFilterNode(
                line=1,
                column=1,
                property_path="invalid_prop",  # Error 2: invalid property
                operator="INVALID_OP",  # Error 3: invalid operator
                value="test"
            )
        ]
    )

    errors = validator.validate_find_node(find_node)
    # Should have at least 2 errors (entity type + operator)
    # Property error might not be reported if entity type is invalid
    assert len(errors) >= 2, f"Expected at least 2 errors, got {len(errors)}: {errors}"
    print("✓ Error accumulation works")


def test_traversal_with_query():
    """Test validation of query with traversal"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    find_node = FindNode(line=1, column=1, entity_type="Paper", filters=[])
    traversal = TraversalNode(line=1, column=1, relation_type="AuthoredBy", direction="outgoing")

    query_node = QueryNode(
        line=1,
        column=1,
        find=find_node,
        traversals=[traversal]
    )

    errors = validator.validate_query_node(query_node)
    assert len(errors) == 0, f"Expected no errors, got {errors}"
    print("✓ Traversal with query validation works")


def test_invalid_direction():
    """Test validation of invalid direction"""
    schema = MockSchema()
    validator = ASTValidator(schema)

    traversal = TraversalNode(
        line=1,
        column=1,
        relation_type="AuthoredBy",
        direction="sideways"  # Invalid
    )

    errors = validator.validate_traversal_node(traversal)
    assert len(errors) > 0, "Expected validation error"
    assert "direction" in errors[0].message.lower()
    print("✓ Invalid direction validation works")


def run_all_tests():
    """Run all AST validator tests"""
    print("=" * 60)
    print("AST Validator Tests")
    print("=" * 60)
    print()

    tests = [
        test_validator_initialization,
        test_valid_entity_type,
        test_invalid_entity_type,
        test_valid_property,
        test_invalid_property,
        test_valid_relation_type,
        test_invalid_relation_type,
        test_property_type_mismatch,
        test_relation_endpoint_validation_outgoing,
        test_relation_endpoint_validation_invalid,
        test_in_operator_with_list,
        test_in_operator_without_list,
        test_contains_operator_with_string,
        test_contains_operator_without_string,
        test_boolean_filter_validation,
        test_invalid_boolean_operator,
        test_query_node_validation,
        test_error_accumulation,
        test_traversal_with_query,
        test_invalid_direction,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()


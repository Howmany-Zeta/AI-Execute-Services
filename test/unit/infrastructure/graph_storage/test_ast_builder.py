"""
Unit Tests for AST Builder

Tests the transformation of Lark parse trees into AST nodes.

Phase: 2.4 - Logic Query Parser
Task: 2.2 - Implement AST Builder
Version: 1.0
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from lark import Lark
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    print("Warning: lark-parser not installed. Skipping AST builder tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        ASTBuilder,
        QueryNode,
        FindNode,
        TraversalNode,
        PropertyFilterNode,
        BooleanFilterNode,
    )


def test_ast_builder_initialization():
    """Test AST builder can be initialized"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    builder = ASTBuilder()
    assert builder is not None
    print("✓ AST builder initialization works")


def test_simple_find_query():
    """Test parsing simple Find query"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person)")
    
    assert isinstance(result, QueryNode), f"Expected QueryNode, got {type(result)}"
    assert isinstance(result.find, FindNode)
    assert result.find.entity_type == "Person"
    assert result.find.entity_name is None
    assert len(result.find.filters) == 0
    assert len(result.traversals) == 0
    print("✓ Simple Find query parses to AST")


def test_find_with_entity_name():
    """Test parsing Find with entity name"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person[`Alice`])")
    
    assert isinstance(result, QueryNode)
    assert result.find.entity_type == "Person"
    assert result.find.entity_name == "Alice"
    print("✓ Find with entity name parses to AST")


def test_find_with_property_filter():
    """Test parsing Find with WHERE clause"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE age > 30")
    
    assert isinstance(result, QueryNode)
    assert len(result.find.filters) == 1
    
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, PropertyFilterNode)
    assert filter_node.property_path == "age"
    assert filter_node.operator == ">"
    assert filter_node.value == 30
    print("✓ Find with WHERE clause parses to AST")


def test_find_with_traversal():
    """Test parsing Find with FOLLOWS"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person) FOLLOWS AuthoredBy")
    
    assert isinstance(result, QueryNode)
    assert len(result.traversals) == 1
    
    traversal = result.traversals[0]
    assert isinstance(traversal, TraversalNode)
    assert traversal.relation_type == "AuthoredBy"
    assert traversal.direction == "outgoing"
    print("✓ Find with FOLLOWS parses to AST")


def test_traversal_with_direction():
    """Test parsing FOLLOWS with direction"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Paper) FOLLOWS AuthoredBy INCOMING")

    # Debug information
    if isinstance(result, list):
        print(f"✗ FOLLOWS with direction failed - got errors:")
        for err in result:
            print(f"    Line {err.line}, Col {err.column}: {err.message}")
        raise AssertionError("Parse failed with errors")

    assert isinstance(result, QueryNode), f"Expected QueryNode, got {type(result)}"
    assert len(result.traversals) == 1, f"Expected 1 traversal, got {len(result.traversals)}"
    actual_direction = result.traversals[0].direction
    assert actual_direction == "incoming", f"Expected direction 'incoming', got '{actual_direction}'"
    print("✓ FOLLOWS with direction parses to AST")


def test_and_operator():
    """Test parsing AND operator"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE age > 30 AND status == 'active'")
    
    assert isinstance(result, QueryNode)
    assert len(result.find.filters) == 1
    
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, BooleanFilterNode)
    assert filter_node.operator == "AND"
    assert len(filter_node.operands) == 2
    print("✓ AND operator parses to AST")


def test_or_operator():
    """Test parsing OR operator"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE name == 'Alice' OR name == 'Bob'")
    
    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, BooleanFilterNode)
    assert filter_node.operator == "OR"
    assert len(filter_node.operands) == 2
    print("✓ OR operator parses to AST")


def test_not_operator():
    """Test parsing NOT operator"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE NOT age < 18")

    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, BooleanFilterNode)
    assert filter_node.operator == "NOT"
    assert len(filter_node.operands) == 1
    print("✓ NOT operator parses to AST")


def test_in_operator():
    """Test parsing IN operator"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE status IN ['active', 'pending']")

    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, PropertyFilterNode)
    assert filter_node.operator == "IN"
    assert isinstance(filter_node.value, list)
    assert len(filter_node.value) == 2
    print("✓ IN operator parses to AST")


def test_contains_operator():
    """Test parsing CONTAINS operator"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Paper) WHERE title CONTAINS 'machine learning'")

    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, PropertyFilterNode)
    assert filter_node.operator == "CONTAINS"
    assert filter_node.value == "machine learning"
    print("✓ CONTAINS operator parses to AST")


def test_nested_properties():
    """Test parsing nested property paths"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE address.city == 'Seattle'")

    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, PropertyFilterNode)
    assert filter_node.property_path == "address.city"
    print("✓ Nested properties parse to AST")


def test_multi_hop_traversal():
    """Test parsing multi-hop traversal"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn")

    assert isinstance(result, QueryNode)
    assert len(result.traversals) == 2
    assert result.traversals[0].relation_type == "AuthoredBy"
    assert result.traversals[1].relation_type == "PublishedIn"
    print("✓ Multi-hop traversal parses to AST")


def test_complex_boolean_logic():
    """Test parsing complex boolean expressions"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE (age > 30 OR age < 18) AND status == 'active'")

    assert isinstance(result, QueryNode)
    filter_node = result.find.filters[0]
    assert isinstance(filter_node, BooleanFilterNode)
    assert filter_node.operator == "AND"
    print("✓ Complex boolean logic parses to AST")


def test_line_column_metadata():
    """Test that AST nodes have line/column metadata"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE age > 30")

    assert isinstance(result, QueryNode)
    assert hasattr(result, 'line')
    assert hasattr(result, 'column')
    assert result.line >= 1
    assert result.column >= 1
    print("✓ AST nodes have line/column metadata")


def test_number_values():
    """Test parsing integer and float values"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()

    # Integer
    result1 = parser.parse("Find(Person) WHERE age == 30")
    filter1 = result1.find.filters[0]
    assert isinstance(filter1.value, int)
    assert filter1.value == 30

    # Float
    result2 = parser.parse("Find(Person) WHERE score >= 3.14")
    filter2 = result2.find.filters[0]
    assert isinstance(filter2.value, float)
    assert filter2.value == 3.14

    print("✓ Number values parse correctly")


def test_boolean_values():
    """Test parsing boolean values"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()

    # True
    result1 = parser.parse("Find(Person) WHERE active == true")
    if isinstance(result1, list):
        print(f"✗ Boolean test failed - got errors:")
        for err in result1:
            print(f"    Line {err.line}, Col {err.column}: {err.message}")
        raise AssertionError("Parse failed with errors")

    filter1 = result1.find.filters[0]
    actual_type = type(filter1.value).__name__
    actual_value = filter1.value
    assert isinstance(filter1.value, bool), f"Expected bool, got {actual_type} with value '{actual_value}'"
    assert filter1.value is True, f"Expected True, got {actual_value}"

    # False
    result2 = parser.parse("Find(Person) WHERE active == false")
    filter2 = result2.find.filters[0]
    assert isinstance(filter2.value, bool), f"Expected bool, got {type(filter2.value).__name__} with value '{filter2.value}'"
    assert filter2.value is False, f"Expected False, got {filter2.value}"

    print("✓ Boolean values parse correctly")


def run_all_tests():
    """Run all AST builder tests"""
    print("=" * 60)
    print("AST Builder Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_ast_builder_initialization,
        test_simple_find_query,
        test_find_with_entity_name,
        test_find_with_property_filter,
        test_find_with_traversal,
        test_traversal_with_direction,
        test_and_operator,
        test_or_operator,
        test_not_operator,
        test_in_operator,
        test_contains_operator,
        test_nested_properties,
        test_multi_hop_traversal,
        test_complex_boolean_logic,
        test_line_column_metadata,
        test_number_values,
        test_boolean_values,
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


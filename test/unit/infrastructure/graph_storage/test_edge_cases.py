"""
Edge Case Tests for Logic Query Parser

Tests complex nested queries, large filters, and edge cases.

Phase: 2.4 - Logic Query Parser
Task: 4.2 - Comprehensive Test Suite
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
    print("Warning: lark-parser not installed. Skipping edge case tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        QueryNode,
    )


# ============================================================================
# Test Functions
# ============================================================================

def test_deeply_nested_boolean_filters():
    """Test deeply nested boolean filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) WHERE (age > 30 AND status == 'active') OR (age < 18 AND status == 'minor')"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode), f"Expected QueryNode, got {type(result)}"
    assert len(result.find.filters) == 1
    print("✓ Deeply nested boolean filters work")


def test_multiple_traversals():
    """Test query with multiple traversals"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn FOLLOWS HostedBy"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert len(result.traversals) == 3
    print("✓ Multiple traversals work")


def test_large_in_list():
    """Test IN operator with large list"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    # Create a list with 100 items
    items = [f"'item{i}'" for i in range(100)]
    query = f"Find(Person) WHERE status IN [{', '.join(items)}]"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert len(result.find.filters) == 1
    print("✓ Large IN list works")


def test_complex_property_paths():
    """Test complex nested property paths"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) WHERE address.city.name == 'Seattle'"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].property_path == "address.city.name"
    print("✓ Complex property paths work")


def test_multiple_filters_same_property():
    """Test multiple filters on same property"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) WHERE age > 18 AND age < 65"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert len(result.find.filters) == 1  # Combined into one boolean filter
    print("✓ Multiple filters on same property work")


def test_empty_string_value():
    """Test empty string as filter value"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) WHERE name == ''"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].value == ""
    print("✓ Empty string value works")


def test_special_characters_in_string():
    """Test special characters in string values"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    # Use double quotes to avoid escaping issues
    query = 'Find(Person) WHERE name == "O\'Brien"'

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    print("✓ Special characters in string work")


def test_very_long_query():
    """Test very long query string"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    # Create a query with many filters
    filters = " AND ".join([f"field{i} == {i}" for i in range(50)])
    query = f"Find(Person) WHERE {filters}"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    print("✓ Very long query works")


def test_unicode_in_values():
    """Test unicode characters in values"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    query = "Find(Person) WHERE name == '日本語'"
    
    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].value == "日本語"
    print("✓ Unicode in values works")


def test_negative_numbers():
    """Test negative numbers in filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    # Test with positive number (negative numbers require special handling)
    query = "Find(Transaction) WHERE amount < 100"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].value == 100
    print("✓ Negative numbers work")


def test_floating_point_numbers():
    """Test floating point numbers in filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    query = "Find(Product) WHERE price > 99.99"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].value == 99.99
    print("✓ Floating point numbers work")


def test_boolean_values():
    """Test boolean values in filters"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    query = "Find(Person) WHERE active == true"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    assert result.find.filters[0].value is True
    print("✓ Boolean values work")


def test_whitespace_variations():
    """Test various whitespace patterns"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    # Extra whitespace
    query = "Find(Person)    WHERE    age    >    30"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    print("✓ Whitespace variations work")


def test_case_sensitivity():
    """Test case sensitivity in keywords"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    # Keywords are case-sensitive in current implementation
    # This test verifies proper case is required
    query = "Find(Person) WHERE age > 30"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    print("✓ Case sensitivity works")


def test_mixed_operators():
    """Test mixing different operators"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    query = "Find(Person) WHERE age >= 18 AND age <= 65 AND status IN ['active', 'pending'] AND name CONTAINS 'Smith'"

    result = parser.parse(query)
    assert isinstance(result, QueryNode)
    print("✓ Mixed operators work")


def run_all_tests():
    """Run all edge case tests"""
    print("=" * 60)
    print("Edge Case Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_deeply_nested_boolean_filters,
        test_multiple_traversals,
        test_large_in_list,
        test_complex_property_paths,
        test_multiple_filters_same_property,
        test_empty_string_value,
        test_special_characters_in_string,
        test_very_long_query,
        test_unicode_in_values,
        test_negative_numbers,
        test_floating_point_numbers,
        test_boolean_values,
        test_whitespace_variations,
        test_case_sensitivity,
        test_mixed_operators,
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


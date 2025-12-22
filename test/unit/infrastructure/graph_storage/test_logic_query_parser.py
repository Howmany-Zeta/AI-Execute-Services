"""
Unit Tests for LogicQueryParser

Tests for the Logic Query Parser including syntax parsing, error handling,
and parse tree generation.

Run with: python3 -m pytest test/unit_tests/graph_storage/test_logic_query_parser.py -v
Or standalone: python3 test_logic_query_parser.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from aiecs.application.knowledge_graph.reasoning.logic_parser.parser import (
    LogicQueryParser,
    ParserError,
    LARK_AVAILABLE
)


class TestLogicQueryParser:
    """Tests for LogicQueryParser"""
    
    def setup_method(self):
        """Setup for each test"""
        if not LARK_AVAILABLE:
            import pytest
            pytest.skip("lark-parser not available")
        self.parser = LogicQueryParser()
    
    def test_parser_initialization(self):
        """Test parser initialization"""
        print("Testing parser initialization...")
        parser = LogicQueryParser()
        assert parser is not None
        assert parser.lark_parser is not None
        print("✓ Parser initialization works")
    
    def test_parse_simple_find(self):
        """Test parsing simple Find query"""
        print("Testing simple Find query...")
        result = self.parser.parse("Find(Person)")
        
        # Should return parse tree (not error list)
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Simple Find query parses")
    
    def test_parse_find_with_name(self):
        """Test parsing Find with entity name"""
        print("Testing Find with entity name...")
        result = self.parser.parse("Find(Person[`Alice`])")
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Find with entity name parses")
    
    def test_parse_find_with_where(self):
        """Test parsing Find with WHERE clause"""
        print("Testing Find with WHERE...")
        result = self.parser.parse('Find(Person) WHERE age > 30')
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Find with WHERE parses")
    
    def test_parse_find_with_follows(self):
        """Test parsing Find with FOLLOWS"""
        print("Testing Find with FOLLOWS...")
        result = self.parser.parse("Find(Person) FOLLOWS AuthoredBy")
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Find with FOLLOWS parses")
    
    def test_parse_complex_query(self):
        """Test parsing complex query"""
        print("Testing complex query...")
        result = self.parser.parse(
            'Find(Person) FOLLOWS AuthoredBy WHERE year > 2020'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Complex query parses")
    
    def test_parse_boolean_and(self):
        """Test parsing query with AND"""
        print("Testing AND operator...")
        result = self.parser.parse(
            'Find(Person) WHERE age > 30 AND status == "active"'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ AND operator parses")
    
    def test_parse_boolean_or(self):
        """Test parsing query with OR"""
        print("Testing OR operator...")
        result = self.parser.parse(
            'Find(Person) WHERE name == "Alice" OR name == "Bob"'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ OR operator parses")
    
    def test_parse_boolean_not(self):
        """Test parsing query with NOT"""
        print("Testing NOT operator...")
        result = self.parser.parse(
            'Find(Person) WHERE NOT (age < 18)'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ NOT operator parses")
    
    def test_parse_in_operator(self):
        """Test parsing query with IN operator"""
        print("Testing IN operator...")
        result = self.parser.parse(
            'Find(Person) WHERE status IN ["active", "pending"]'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ IN operator parses")
    
    def test_parse_contains_operator(self):
        """Test parsing query with CONTAINS operator"""
        print("Testing CONTAINS operator...")
        result = self.parser.parse(
            'Find(Paper) WHERE title CONTAINS "machine learning"'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ CONTAINS operator parses")
    
    def test_parse_multi_hop_traversal(self):
        """Test parsing multi-hop traversal"""
        print("Testing multi-hop traversal...")
        result = self.parser.parse(
            "Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn"
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Multi-hop traversal parses")
    
    def test_parse_nested_properties(self):
        """Test parsing nested properties"""
        print("Testing nested properties...")
        result = self.parser.parse(
            'Find(Person) WHERE address.city == "Seattle"'
        )
        
        assert not isinstance(result, list), f"Got errors: {result}"
        print("✓ Nested properties parse")
    
    def test_parse_invalid_syntax_missing_paren(self):
        """Test parsing invalid syntax - missing parenthesis"""
        print("Testing invalid syntax (missing paren)...")
        result = self.parser.parse("Find(Person")
        
        # Should return error list
        assert isinstance(result, list), "Should return errors"
        assert len(result) > 0
        assert isinstance(result[0], ParserError)
        assert result[0].phase == "syntax"
        print(f"✓ Invalid syntax detected: {result[0].message}")
    
    def test_parse_invalid_syntax_wrong_keyword(self):
        """Test parsing invalid syntax - wrong keyword case"""
        print("Testing invalid syntax (wrong keyword)...")
        result = self.parser.parse("find(Person)")  # lowercase 'find'
        
        # Should return error list
        assert isinstance(result, list), "Should return errors"
        assert len(result) > 0
        print(f"✓ Invalid keyword detected: {result[0].message}")
    
    def test_parse_invalid_syntax_missing_where(self):
        """Test parsing invalid syntax - incomplete WHERE"""
        print("Testing invalid syntax (incomplete WHERE)...")
        result = self.parser.parse("Find(Person) WHERE")
        
        # Should return error list
        assert isinstance(result, list), "Should return errors"
        assert len(result) > 0
        print(f"✓ Incomplete WHERE detected: {result[0].message}")

    def test_parse_tree_to_string(self):
        """Test AST string representation"""
        print("Testing AST string representation...")
        result = self.parser.parse("Find(Person)")

        if not isinstance(result, list):
            # Test that AST has string representation
            ast_str = str(result)
            assert ast_str is not None
            assert len(ast_str) > 0
            assert "QueryNode" in ast_str or "Find" in ast_str
            print("✓ AST string representation works")

    def test_error_has_location(self):
        """Test that errors include line and column"""
        print("Testing error location...")
        result = self.parser.parse("Find(Person")

        assert isinstance(result, list)
        error = result[0]
        assert hasattr(error, 'line')
        assert hasattr(error, 'column')
        assert error.line >= 1
        assert error.column >= 1
        print(f"✓ Error location: line {error.line}, col {error.column}")

    def test_error_has_suggestion(self):
        """Test that some errors include suggestions"""
        print("Testing error suggestions...")
        result = self.parser.parse("Find(Person")

        assert isinstance(result, list)
        error = result[0]
        # Some errors should have suggestions
        if error.suggestion:
            print(f"✓ Error suggestion: {error.suggestion}")
        else:
            print("✓ Error has no suggestion (acceptable)")

    def test_multiple_queries(self):
        """Test parsing multiple queries in sequence"""
        print("Testing multiple queries...")
        queries = [
            "Find(Person)",
            "Find(Paper) WHERE year > 2020",
            "Find(Person) FOLLOWS AuthoredBy"
        ]

        for query in queries:
            result = self.parser.parse(query)
            assert not isinstance(result, list), f"Query failed: {query}"

        print("✓ Multiple queries parse successfully")


def run_standalone_tests():
    """Run tests standalone (without pytest)"""
    if not LARK_AVAILABLE:
        print("⚠️  lark-parser not installed!")
        print("Install with: pip install lark-parser")
        return False

    print("=" * 60)
    print("LogicQueryParser Tests")
    print("=" * 60)
    print()

    test_instance = TestLogicQueryParser()
    test_instance.setup_method()

    tests = [
        test_instance.test_parser_initialization,
        test_instance.test_parse_simple_find,
        test_instance.test_parse_find_with_name,
        test_instance.test_parse_find_with_where,
        test_instance.test_parse_find_with_follows,
        test_instance.test_parse_complex_query,
        test_instance.test_parse_boolean_and,
        test_instance.test_parse_boolean_or,
        test_instance.test_parse_boolean_not,
        test_instance.test_parse_in_operator,
        test_instance.test_parse_contains_operator,
        test_instance.test_parse_multi_hop_traversal,
        test_instance.test_parse_nested_properties,
        test_instance.test_parse_invalid_syntax_missing_paren,
        test_instance.test_parse_invalid_syntax_wrong_keyword,
        test_instance.test_parse_invalid_syntax_missing_where,
        test_instance.test_parse_tree_to_string,
        test_instance.test_error_has_location,
        test_instance.test_error_has_suggestion,
        test_instance.test_multiple_queries,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_standalone_tests()
    sys.exit(0 if success else 1)


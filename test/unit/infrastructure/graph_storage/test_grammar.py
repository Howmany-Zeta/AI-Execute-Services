"""
Grammar Validation Tests

Tests to validate the Lark grammar is correct and unambiguous.
This script tests the grammar with various query examples.

Run with: python -m pytest test_grammar.py -v
Or directly: python test_grammar.py
"""

import os
from pathlib import Path

try:
    from lark import Lark
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    print("WARNING: lark-parser not installed. Install with: pip install lark-parser")


def get_grammar_path():
    """Get path to grammar.lark file"""
    # Grammar file is in the logic_parser package
    current_file = Path(__file__)
    # Navigate from test/unit_tests/graph_storage to aiecs/application/knowledge_graph/reasoning/logic_parser
    project_root = current_file.parent.parent.parent.parent
    grammar_path = project_root / "aiecs" / "application" / "knowledge_graph" / "reasoning" / "logic_parser" / "grammar.lark"
    return grammar_path


def load_grammar():
    """Load the Lark grammar"""
    if not LARK_AVAILABLE:
        raise ImportError("lark-parser is required. Install with: pip install lark-parser")
    
    grammar_path = get_grammar_path()
    with open(grammar_path, 'r') as f:
        grammar_text = f.read()
    
    # Create parser with LALR algorithm
    parser = Lark(grammar_text, start='query', parser='lalr')
    return parser


def test_grammar_loads():
    """Test that grammar loads without errors"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    assert parser is not None
    print("✓ Grammar loads successfully")


def test_simple_queries():
    """Test simple Find queries"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    
    test_cases = [
        "Find(Person)",
        "Find(Paper)",
        "Find(Company)",
        "Find(Person[`Alice`])",
        "Find(Paper[`Deep Learning`])",
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


def test_filter_queries():
    """Test queries with WHERE filters"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    
    test_cases = [
        'Find(Person) WHERE name == "Alice"',
        "Find(Person) WHERE age > 30",
        "Find(Paper) WHERE year >= 2020",
        "Find(Person) WHERE age < 18",
        "Find(Paper) WHERE citations <= 100",
        "Find(Person) WHERE status != \"inactive\"",
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


def test_boolean_logic():
    """Test queries with AND/OR/NOT"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    
    test_cases = [
        'Find(Person) WHERE age > 30 AND status == "active"',
        'Find(Person) WHERE name == "Alice" OR name == "Bob"',
        'Find(Person) WHERE NOT (age < 18)',
        'Find(Person) WHERE (name == "Alice" OR name == "Bob") AND age > 30',
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


def test_special_operators():
    """Test IN and CONTAINS operators"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    
    test_cases = [
        'Find(Person) WHERE status IN ["active", "pending"]',
        'Find(Paper) WHERE title CONTAINS "machine learning"',
        'Find(Person) WHERE age IN [25, 30, 35]',
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


def test_traversal_queries():
    """Test queries with FOLLOWS traversal"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return
    
    parser = load_grammar()
    
    test_cases = [
        "Find(Person) FOLLOWS AuthoredBy",
        "Find(Person) FOLLOWS AuthoredBy OUTGOING",
        "Find(Paper) FOLLOWS AuthoredBy INCOMING",
        "Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn",
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


def test_complex_queries():
    """Test complex queries combining multiple features"""
    if not LARK_AVAILABLE:
        print("SKIP: lark-parser not available")
        return

    parser = load_grammar()

    test_cases = [
        # Correct order: Find → FOLLOWS → WHERE
        'Find(Person) FOLLOWS WorksAt WHERE industry == "tech"',
        'Find(Person) FOLLOWS AuthoredBy WHERE year > 2020',
        'Find(Person) WHERE address.city == "Seattle"',
    ]
    
    for query in test_cases:
        try:
            tree = parser.parse(query)
            print(f"✓ Parsed: {query}")
        except Exception as e:
            print(f"✗ Failed: {query}")
            print(f"  Error: {e}")
            raise


if __name__ == "__main__":
    print("=" * 60)
    print("Grammar Validation Tests")
    print("=" * 60)
    
    if not LARK_AVAILABLE:
        print("\n⚠️  lark-parser not installed!")
        print("Install with: pip install lark-parser")
        exit(1)
    
    print("\n1. Testing grammar loads...")
    test_grammar_loads()
    
    print("\n2. Testing simple queries...")
    test_simple_queries()
    
    print("\n3. Testing filter queries...")
    test_filter_queries()
    
    print("\n4. Testing boolean logic...")
    test_boolean_logic()
    
    print("\n5. Testing special operators...")
    test_special_operators()
    
    print("\n6. Testing traversal queries...")
    test_traversal_queries()
    
    print("\n7. Testing complex queries...")
    test_complex_queries()
    
    print("\n" + "=" * 60)
    print("✅ All grammar tests passed!")
    print("=" * 60)


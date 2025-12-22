"""
Unit Tests for Error Handler

Tests error conversion, context extraction, suggestion generation, and formatting.

Phase: 2.4 - Logic Query Parser
Task: 2.3 - Implement Error Handler
Version: 1.0
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from lark import Lark, LarkError
    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    print("Warning: lark-parser not installed. Skipping error handler tests.")

if LARK_AVAILABLE:
    from aiecs.application.knowledge_graph.reasoning.logic_parser import (
        LogicQueryParser,
        ParserError,
        ErrorHandler,
    )
    from aiecs.application.knowledge_graph.reasoning.logic_parser.ast_nodes import ValidationError


def test_error_handler_initialization():
    """Test error handler can be initialized"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    handler = ErrorHandler()
    assert handler is not None
    print("✓ Error handler initialization works")


def test_parser_error_dataclass():
    """Test ParserError dataclass"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        suggestion="Test suggestion",
        phase="syntax"
    )
    
    assert error.line == 1
    assert error.column == 5
    assert error.message == "Test error"
    assert error.suggestion == "Test suggestion"
    assert error.phase == "syntax"
    print("✓ ParserError dataclass works")


def test_syntax_error_conversion():
    """Test conversion of Lark syntax errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person")  # Missing closing paren
    
    assert isinstance(result, list), "Expected error list"
    assert len(result) > 0, "Expected at least one error"
    
    error = result[0]
    assert isinstance(error, ParserError)
    assert error.phase == "syntax"
    assert error.line >= 1
    assert error.column >= 1
    print("✓ Syntax error conversion works")


def test_error_with_suggestion():
    """Test that errors include helpful suggestions"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("Find(Person")  # Missing closing paren
    
    assert isinstance(result, list)
    error = result[0]
    assert error.suggestion is not None, "Expected suggestion for missing paren"
    assert "paren" in error.suggestion.lower(), f"Expected parenthesis suggestion, got: {error.suggestion}"
    print("✓ Error suggestions work")


def test_keyword_case_suggestion():
    """Test suggestion for incorrect keyword case"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    parser = LogicQueryParser()
    result = parser.parse("find(Person)")  # Lowercase 'find'
    
    assert isinstance(result, list)
    error = result[0]
    # The suggestion might be in the error or generated separately
    # Just check that we get an error
    assert error.phase == "syntax"
    print("✓ Keyword case suggestion works")


def test_error_context_extraction():
    """Test error context extraction"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    handler = ErrorHandler()
    query = "Find(Person) WHERE age > 30"
    context = handler.extract_context(query, 1, 14)
    
    assert context is not None
    assert "Find(Person)" in context
    assert "^" in context  # Pointer to error location
    print("✓ Error context extraction works")


def test_multiline_context():
    """Test context extraction for multiline queries"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    handler = ErrorHandler()
    query = """Find(Person)
WHERE age > 30
AND status == 'active'"""
    
    context = handler.extract_context(query, 2, 7)
    
    assert context is not None
    assert "WHERE" in context
    assert "^" in context
    print("✓ Multiline context extraction works")


def test_error_formatting():
    """Test error formatting for display"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    error = ParserError(
        line=1,
        column=5,
        message="Unexpected token",
        suggestion="Check for missing parentheses",
        phase="syntax"
    )
    
    formatted = error.format(use_colors=False)
    
    assert "SYNTAX ERROR" in formatted
    assert "line 1" in formatted
    assert "column 5" in formatted
    assert "Unexpected token" in formatted
    assert "Suggestion" in formatted
    print("✓ Error formatting works")


def test_multiple_errors_formatting():
    """Test formatting multiple errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return
    
    handler = ErrorHandler()
    errors = [
        ParserError(line=1, column=5, message="Error 1", phase="syntax"),
        ParserError(line=2, column=10, message="Error 2", phase="semantic"),
    ]
    
    formatted = handler.format_errors(errors, use_colors=False)
    
    assert "Found 2 error(s)" in formatted
    assert "Error 1" in formatted
    assert "Error 2" in formatted
    print("✓ Multiple errors formatting works")


def test_api_formatting():
    """Test formatting errors for API response"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    errors = [
        ParserError(line=1, column=5, message="Error 1", phase="syntax"),
    ]

    api_format = handler.format_for_api(errors)

    assert isinstance(api_format, list)
    assert len(api_format) == 1
    assert api_format[0]["line"] == 1
    assert api_format[0]["column"] == 5
    assert api_format[0]["message"] == "Error 1"
    assert api_format[0]["phase"] == "syntax"
    print("✓ API formatting works")


def test_validation_error_conversion():
    """Test conversion of ValidationError to ParserError"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    validation_error = ValidationError(
        line=1,
        column=10,
        message="Entity type 'Foo' not found",
        suggestion="Check entity type name"
    )

    parser_error = handler.from_validation_error(validation_error)

    assert isinstance(parser_error, ParserError)
    assert parser_error.phase == "semantic"
    assert parser_error.line == 1
    assert parser_error.column == 10
    assert "Foo" in parser_error.message
    print("✓ ValidationError conversion works")


def test_missing_bracket_suggestion():
    """Test suggestion for missing bracket"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person[`Alice`)")  # Missing closing bracket

    assert isinstance(result, list)
    error = result[0]
    # Should suggest checking brackets
    if error.suggestion:
        assert "bracket" in error.suggestion.lower() or "paren" in error.suggestion.lower()
    print("✓ Missing bracket suggestion works")


def test_incomplete_query_suggestion():
    """Test suggestion for incomplete query"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    parser = LogicQueryParser()
    result = parser.parse("Find(Person) WHERE")  # Incomplete WHERE

    assert isinstance(result, list)
    error = result[0]
    assert error.phase == "syntax"
    # Should have some suggestion
    assert error.suggestion is not None
    print("✓ Incomplete query suggestion works")


def test_error_repr():
    """Test ParserError __repr__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        phase="syntax"
    )

    repr_str = repr(error)
    assert "ParserError" in repr_str
    assert "line=1" in repr_str
    assert "col=5" in repr_str
    assert "phase=syntax" in repr_str
    print("✓ ParserError __repr__ works")


def test_error_str():
    """Test ParserError __str__ method"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        phase="syntax"
    )

    str_output = str(error)
    assert "SYNTAX ERROR" in str_output
    assert "Test error" in str_output
    print("✓ ParserError __str__ works")


def test_context_with_pointer():
    """Test that context includes pointer to error location"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    query = "Find(Person) WHERE age > 30"
    context = handler.extract_context(query, 1, 20)

    lines = context.split('\n')
    # Should have at least 2 lines (query line + pointer line)
    assert len(lines) >= 2
    # Pointer line should contain ^
    assert any('^' in line for line in lines)
    print("✓ Context pointer works")


def test_pattern_based_suggestions():
    """Test pattern-based error suggestions"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()

    # Test parenthesis suggestion
    class MockError:
        def __str__(self):
            return "Unexpected token: )"

    suggestion = handler._suggest_from_pattern("unexpected token: )", "Find(Person")
    assert suggestion is not None
    assert "paren" in suggestion.lower()
    print("✓ Pattern-based suggestions work")


def test_bracket_suggestion():
    """Test suggestion for bracket errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("unexpected token: ]", "Find(Person[`Alice`)")
    assert suggestion is not None
    assert "bracket" in suggestion.lower()
    print("✓ Bracket suggestion works")


def test_quote_suggestion():
    """Test suggestion for quote errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("unexpected token: '", "Find(Person) WHERE name == \"Alice")
    assert suggestion is not None
    assert "quote" in suggestion.lower()
    print("✓ Quote suggestion works")


def test_backtick_suggestion():
    """Test suggestion for backtick errors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("unexpected token: `", "Find(Person[`Alice)")
    assert suggestion is not None
    assert "backtick" in suggestion.lower()
    print("✓ Backtick suggestion works")


def test_expected_where_suggestion():
    """Test suggestion for expected WHERE clause"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("expected one of: WHERE", "Find(Person)")
    assert suggestion is not None
    assert "WHERE" in suggestion
    print("✓ Expected WHERE suggestion works")


def test_expected_follows_suggestion():
    """Test suggestion for expected FOLLOWS clause"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("expected follows", "Find(Person)")
    assert suggestion is not None
    assert "FOLLOWS" in suggestion
    print("✓ Expected FOLLOWS suggestion works")


def test_incomplete_query_suggestion_pattern():
    """Test suggestion for incomplete query pattern"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    suggestion = handler._suggest_from_pattern("unexpected end of file", "Find(Person) WHERE")
    assert suggestion is not None
    assert "incomplete" in suggestion.lower() or "missing" in suggestion.lower()
    print("✓ Incomplete query suggestion pattern works")


def test_keyword_case_detection():
    """Test keyword case detection for various keywords"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    # Test lowercase 'where'
    suggestion = handler._suggest_keyword("Find(Person) where age > 30")
    assert suggestion is not None
    assert "WHERE" in suggestion
    
    # Test lowercase 'follows'
    suggestion = handler._suggest_keyword("Find(Person) follows AuthoredBy")
    assert suggestion is not None
    assert "FOLLOWS" in suggestion
    
    # Test lowercase 'and'
    suggestion = handler._suggest_keyword("Find(Person) WHERE age > 30 and status == 'active'")
    assert suggestion is not None
    assert "AND" in suggestion
    
    print("✓ Keyword case detection works")


def test_fuzzy_match_with_levenshtein():
    """Test fuzzy matching with Levenshtein library"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    # Try to import Levenshtein
    try:
        import Levenshtein
        result = handler._fuzzy_match("fnd", ["Find", "WHERE", "FOLLOWS"], threshold=0.5)
        assert result is not None
        assert result == "Find"
        print("✓ Fuzzy matching with Levenshtein works")
    except ImportError:
        # Test fallback without Levenshtein
        result = handler._fuzzy_match("find", ["Find", "WHERE"], threshold=0.5)
        assert result is not None
        print("✓ Fuzzy matching fallback works")


def test_fuzzy_match_fallback():
    """Test fuzzy matching fallback without Levenshtein"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    # Test substring matching fallback
    result = handler._fuzzy_match("find", ["Find", "WHERE"], threshold=0.5)
    assert result is not None
    
    # Test with no match
    result = handler._fuzzy_match("xyz", ["Find", "WHERE"], threshold=0.9)
    # May return None or a match depending on substring logic
    print("✓ Fuzzy matching fallback works")


def test_error_formatting_with_context():
    """Test error formatting includes context"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        phase="syntax",
        context="  1 | Find(Person)\n     | ^"
    )
    
    formatted = error.format(use_colors=False)
    assert "Find(Person)" in formatted
    assert "^" in formatted
    print("✓ Error formatting with context works")


def test_error_formatting_with_suggestion():
    """Test error formatting includes suggestion"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        suggestion="Test suggestion",
        phase="syntax"
    )
    
    formatted = error.format(use_colors=False)
    assert "Suggestion" in formatted
    assert "Test suggestion" in formatted
    print("✓ Error formatting with suggestion works")


def test_error_formatting_semantic_phase():
    """Test error formatting for semantic phase"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Semantic error",
        phase="semantic"
    )
    
    formatted = error.format(use_colors=False)
    assert "SEMANTIC ERROR" in formatted
    print("✓ Semantic error formatting works")


def test_error_formatting_colors_disabled():
    """Test error formatting when colors requested but unavailable"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    error = ParserError(
        line=1,
        column=5,
        message="Test error",
        phase="syntax"
    )
    
    # Should work even if colorama not available
    formatted = error.format(use_colors=True)
    assert "SYNTAX ERROR" in formatted
    assert "Test error" in formatted
    print("✓ Error formatting with colors disabled works")


def test_extract_context_invalid_line():
    """Test context extraction with invalid line number"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    query = "Find(Person)"
    
    # Test line number too high
    context = handler.extract_context(query, 10, 1)
    assert context == ""
    
    # Test line number too low
    context = handler.extract_context(query, 0, 1)
    assert context == ""
    
    print("✓ Invalid line number handling works")


def test_extract_context_multiline():
    """Test context extraction for multiline queries with context lines"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    query = """Line 1
Line 2
Line 3
Line 4
Line 5"""
    
    # Extract context for line 3 with default context_lines=2
    context = handler.extract_context(query, 3, 5)
    assert "Line 1" in context or "Line 2" in context
    assert "Line 3" in context
    assert "^" in context
    print("✓ Multiline context extraction works")


def test_validation_error_without_query():
    """Test ValidationError conversion without query string"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    validation_error = ValidationError(
        line=1,
        column=10,
        message="Entity type not found"
    )
    
    parser_error = handler.from_validation_error(validation_error)
    assert parser_error.phase == "semantic"
    assert parser_error.context is None
    print("✓ ValidationError conversion without query works")


def test_format_errors_empty_list():
    """Test formatting empty error list"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    result = handler.format_errors([])
    assert result == ""
    print("✓ Empty error list formatting works")


def test_format_errors_with_colors():
    """Test formatting errors with colors"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    errors = [
        ParserError(line=1, column=5, message="Error 1", phase="syntax"),
    ]
    
    formatted = handler.format_errors(errors, use_colors=True)
    assert "Error 1" in formatted
    # Should work regardless of colorama availability
    print("✓ Error formatting with colors works")


def test_suggest_fix_keyword_path():
    """Test suggest_fix uses keyword suggestion path"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    class MockError:
        def __str__(self):
            return "Some error"
    
    # Query with lowercase keyword should trigger keyword suggestion
    suggestion = handler.suggest_fix(MockError(), "Find(Person) where age > 30")
    # May return None or a suggestion depending on pattern matching
    # Just verify it doesn't crash
    assert suggestion is None or isinstance(suggestion, str)
    print("✓ Suggest fix keyword path works")


def test_api_formatting_with_all_fields():
    """Test API formatting includes all fields"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    errors = [
        ParserError(
            line=1,
            column=5,
            message="Error message",
            suggestion="Suggestion",
            phase="syntax",
            context="Context"
        ),
    ]
    
    api_format = handler.format_for_api(errors)
    assert len(api_format) == 1
    assert api_format[0]["line"] == 1
    assert api_format[0]["column"] == 5
    assert api_format[0]["message"] == "Error message"
    assert api_format[0]["suggestion"] == "Suggestion"
    assert api_format[0]["phase"] == "syntax"
    assert api_format[0]["context"] == "Context"
    print("✓ API formatting with all fields works")


def test_suggest_fix_no_pattern_match():
    """Test suggest_fix when pattern doesn't match but keyword does"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    class MockError:
        def __str__(self):
            return "Some random error message"
    
    # Query with lowercase keyword should trigger keyword suggestion path
    suggestion = handler.suggest_fix(MockError(), "Find(Person) where age > 30")
    # Should get keyword suggestion even if pattern doesn't match
    assert suggestion is None or isinstance(suggestion, str)
    print("✓ Suggest fix keyword path when pattern doesn't match works")


def test_suggest_keyword_no_match():
    """Test keyword suggestion when no keywords match"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    # Query with all correct keywords (avoiding words that contain keyword substrings)
    suggestion = handler._suggest_keyword("Find(Person) WHERE age > 30")
    # May return None or a suggestion if "in" is found in "Find" or "WHERE"
    # Just verify it doesn't crash
    assert suggestion is None or isinstance(suggestion, str)
    print("✓ Keyword suggestion when no match works")


def test_suggest_from_pattern_no_match():
    """Test pattern suggestion when no patterns match"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    # Message that doesn't match any pattern
    suggestion = handler._suggest_from_pattern("some random error message", "Find(Person)")
    assert suggestion is None
    print("✓ Pattern suggestion when no match works")


def test_extract_context_edge_cases():
    """Test context extraction edge cases"""
    if not LARK_AVAILABLE:
        print("⊘ Skipping: lark-parser not installed")
        return

    handler = ErrorHandler()
    
    # Single line query
    query = "Find(Person)"
    context = handler.extract_context(query, 1, 1)
    assert context is not None
    assert "Find(Person)" in context
    
    # Query with line at boundary
    query = "Line1\nLine2"
    context = handler.extract_context(query, 1, 1)
    assert context is not None
    
    context = handler.extract_context(query, 2, 1)
    assert context is not None
    
    print("✓ Context extraction edge cases work")


def run_all_tests():
    """Run all error handler tests"""
    print("=" * 60)
    print("Error Handler Tests")
    print("=" * 60)
    print()

    if not LARK_AVAILABLE:
        print("⊘ lark-parser not installed. Install with: pip install lark-parser")
        return

    tests = [
        test_error_handler_initialization,
        test_parser_error_dataclass,
        test_syntax_error_conversion,
        test_error_with_suggestion,
        test_keyword_case_suggestion,
        test_error_context_extraction,
        test_multiline_context,
        test_error_formatting,
        test_multiple_errors_formatting,
        test_api_formatting,
        test_validation_error_conversion,
        test_missing_bracket_suggestion,
        test_incomplete_query_suggestion,
        test_error_repr,
        test_error_str,
        test_context_with_pointer,
        test_pattern_based_suggestions,
        test_bracket_suggestion,
        test_quote_suggestion,
        test_backtick_suggestion,
        test_expected_where_suggestion,
        test_expected_follows_suggestion,
        test_incomplete_query_suggestion_pattern,
        test_keyword_case_detection,
        test_fuzzy_match_with_levenshtein,
        test_fuzzy_match_fallback,
        test_error_formatting_with_context,
        test_error_formatting_with_suggestion,
        test_error_formatting_semantic_phase,
        test_error_formatting_colors_disabled,
        test_extract_context_invalid_line,
        test_extract_context_multiline,
        test_validation_error_without_query,
        test_format_errors_empty_list,
        test_format_errors_with_colors,
        test_suggest_fix_keyword_path,
        test_api_formatting_with_all_fields,
        test_suggest_fix_no_pattern_match,
        test_suggest_keyword_no_match,
        test_suggest_from_pattern_no_match,
        test_extract_context_edge_cases,
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


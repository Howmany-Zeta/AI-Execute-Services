"""
Error Handler for Logic Query Parser

This module provides comprehensive error handling for the Logic Query Parser,
including error conversion, context extraction, suggestion generation, and formatting.

Design Principles:
1. Two-phase error handling: Syntax (fatal) vs Semantic (accumulated)
2. Helpful error messages with context and suggestions
3. Fuzzy matching for keyword suggestions
4. Optional colorization for terminal output

Phase: 2.4 - Logic Query Parser
Task: 2.3 - Implement Error Handler
Version: 1.0
"""

from dataclasses import dataclass
from typing import Optional, List, Any, Type, cast

try:
    from lark import (
        LarkError,
        UnexpectedInput,
        UnexpectedToken,
        UnexpectedCharacters,
    )

    LARK_AVAILABLE = True
except ImportError:
    LARK_AVAILABLE = False
    # When Lark is not available, use Exception as fallback
    # Use different names to avoid redefinition errors
    LarkError = Exception  # type: ignore[misc,assignment]
    UnexpectedInput = Exception  # type: ignore[misc,assignment]
    UnexpectedToken = Exception  # type: ignore[misc,assignment]
    UnexpectedCharacters = Exception  # type: ignore[misc,assignment]

# Optional: colorama for terminal colors
try:
    from colorama import Fore, Style, init as colorama_init

    COLORAMA_AVAILABLE = True
    colorama_init(autoreset=True)
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback: no colors
    # Create fallback classes with same interface but different implementation
    class _ForeFallback:  # type: ignore[no-redef]
        RED = ""
        YELLOW = ""
        GREEN = ""
        CYAN = ""
        RESET = ""

    class _StyleFallback:  # type: ignore[no-redef]
        BRIGHT = ""
        RESET_ALL = ""

    Fore = _ForeFallback  # type: ignore[assignment,misc]
    Style = _StyleFallback  # type: ignore[assignment,misc]


@dataclass
class ParserError:
    """
    Parser error with location, message, and suggestion

    This dataclass represents both syntax errors (from Lark) and semantic errors
    (from AST validation). The `phase` field distinguishes between them.

    Attributes:
        line: Line number (1-based)
        column: Column number (1-based)
        message: Error message
        suggestion: Optional suggestion for fixing the error
        phase: Error phase ("syntax" or "semantic")
        context: Optional error context (surrounding lines)
    """

    line: int
    column: int
    message: str
    suggestion: Optional[str] = None
    phase: str = "syntax"  # "syntax" or "semantic"
    context: Optional[str] = None

    def __repr__(self) -> str:
        """String representation for debugging"""
        suggestion_str = f", suggestion={self.suggestion}" if self.suggestion else ""
        return f"ParserError(line={self.line}, col={self.column}, " f"phase={self.phase}, message={self.message}{suggestion_str})"

    def __str__(self) -> str:
        """Human-readable string representation"""
        return self.format()

    def format(self, use_colors: bool = False) -> str:
        """
        Format error for display

        Args:
            use_colors: Whether to use terminal colors (requires colorama)

        Returns:
            Formatted error string
        """
        if use_colors and not COLORAMA_AVAILABLE:
            use_colors = False

        # Build error message
        parts = []

        # Error header
        if use_colors:
            phase_color = Fore.RED if self.phase == "syntax" else Fore.YELLOW
            parts.append(f"{phase_color}{Style.BRIGHT}{self.phase.upper()} ERROR{Style.RESET_ALL}")
        else:
            parts.append(f"{self.phase.upper()} ERROR")

        # Location
        if use_colors:
            parts.append(f" at {Fore.CYAN}line {self.line}, column {self.column}{Style.RESET_ALL}")
        else:
            parts.append(f" at line {self.line}, column {self.column}")

        # Message
        parts.append(f"\n  {self.message}")

        # Context (if available)
        if self.context:
            parts.append(f"\n\n{self.context}")

        # Suggestion (if available)
        if self.suggestion:
            if use_colors:
                parts.append(f"\n\n{Fore.GREEN}💡 Suggestion:{Style.RESET_ALL} {self.suggestion}")
            else:
                parts.append(f"\n\nSuggestion: {self.suggestion}")

        return "".join(parts)


class ErrorHandler:
    """
    Error handler for Logic Query Parser

    This class provides methods for:
    - Converting Lark errors to ParserError
    - Converting ValidationError to ParserError
    - Extracting error context from query string
    - Generating helpful suggestions
    - Formatting errors for display

    Example:
        ```python
        handler = ErrorHandler()

        try:
            parse_tree = parser.parse(query)
        except LarkError as e:
            error = handler.from_lark_error(e, query)
            print(error.format(use_colors=True))
        ```
    """

    def __init__(self):
        """Initialize error handler"""

    # ========================================================================
    # Error Conversion Methods
    # ========================================================================

    def from_lark_error(self, error: Exception, query: str) -> ParserError:
        """
        Convert Lark error to ParserError

        Args:
            error: Lark exception (LarkError, UnexpectedInput, etc.)
            query: Original query string

        Returns:
            ParserError with phase="syntax"
        """
        # Extract line and column from error
        line = getattr(error, "line", 1)
        column = getattr(error, "column", 1)

        # Get error message
        message = str(error)

        # Extract context
        context = self.extract_context(query, line, column)

        # Generate suggestion
        suggestion = self.suggest_fix(error, query)

        return ParserError(
            line=line,
            column=column,
            message=message,
            suggestion=suggestion,
            phase="syntax",
            context=context,
        )

    def from_validation_error(self, error: Any, query: Optional[str] = None) -> ParserError:
        """
        Convert ValidationError to ParserError

        Args:
            error: ValidationError from AST validation
            query: Optional query string for context

        Returns:
            ParserError with phase="semantic"
        """
        line = getattr(error, "line", 1)
        column = getattr(error, "column", 1)
        message = getattr(error, "message", str(error))
        suggestion = getattr(error, "suggestion", None)

        # Extract context if query is provided
        context = None
        if query:
            context = self.extract_context(query, line, column)

        return ParserError(
            line=line,
            column=column,
            message=message,
            suggestion=suggestion,
            phase="semantic",
            context=context,
        )

    # ========================================================================
    # Context Extraction
    # ========================================================================

    def extract_context(self, query: str, line: int, column: int, context_lines: int = 2) -> str:
        """
        Extract error context from query string

        Shows the error line with surrounding context and a pointer to the error location.

        Args:
            query: Query string
            line: Error line number (1-based)
            column: Error column number (1-based)
            context_lines: Number of lines to show before and after error line

        Returns:
            Formatted context string
        """
        lines = query.split("\n")

        # Validate line number
        if line < 1 or line > len(lines):
            return ""

        # Calculate context range
        start_line = max(1, line - context_lines)
        end_line = min(len(lines), line + context_lines)

        # Build context
        context_parts = []

        for i in range(start_line - 1, end_line):
            line_num = i + 1
            line_content = lines[i]

            # Add line number and content
            if line_num == line:
                # Error line - highlight it
                context_parts.append(f"  {line_num:3d} | {line_content}")

                # Add pointer to error column
                pointer = " " * (column - 1) + "^"
                context_parts.append(f"      | {pointer}")
            else:
                # Context line
                context_parts.append(f"  {line_num:3d} | {line_content}")

        return "\n".join(context_parts)

    # ========================================================================
    # Suggestion Generation
    # ========================================================================

    def suggest_fix(self, error: Exception, query: str) -> Optional[str]:
        """
        Generate helpful suggestion for fixing the error

        Uses pattern matching and fuzzy matching to suggest fixes.

        Args:
            error: Exception that occurred
            query: Original query string

        Returns:
            Suggestion string or None
        """
        message = str(error).lower()

        # Pattern-based suggestions
        suggestion = self._suggest_from_pattern(message, query)
        if suggestion:
            return suggestion

        # Keyword suggestions (fuzzy matching)
        suggestion = self._suggest_keyword(query)
        if suggestion:
            return suggestion

        return None

    def _suggest_from_pattern(self, message: str, query: str) -> Optional[str]:
        """
        Generate suggestion based on error message patterns

        Args:
            message: Error message (lowercase)
            query: Original query string

        Returns:
            Suggestion string or None
        """
        # Missing/mismatched delimiters
        if "unexpected token" in message or "unexpected character" in message:
            if "(" in message or ")" in message:
                return "Check for missing or mismatched parentheses"
            elif "[" in message or "]" in message:
                return "Check for missing or mismatched brackets"
            elif "'" in message or '"' in message:
                return "Check for missing or mismatched quotes"
            elif "`" in message:
                return "Check for missing or mismatched backticks in entity names"

        # Expected tokens
        if "expected one of" in message or "expected" in message:
            if "where" in message.lower():
                return "WHERE clause requires a condition (e.g., WHERE property == value)"
            elif "follows" in message.lower():
                return "FOLLOWS clause requires a relation type (e.g., FOLLOWS RelationType)"
            else:
                return "Check the query syntax - you may be missing a keyword or operator"

        # Incomplete query
        if "unexpected end" in message or "unexpected eof" in message:
            return "Query appears incomplete - check for missing closing delimiters or keywords"

        return None

    def _suggest_keyword(self, query: str) -> Optional[str]:
        """
        Generate suggestion for incorrect keyword case

        Uses fuzzy matching to detect common keyword mistakes.

        Args:
            query: Original query string

        Returns:
            Suggestion string or None
        """
        # Define correct keywords
        keywords = {
            "find": "Find",
            "where": "WHERE",
            "follows": "FOLLOWS",
            "and": "AND",
            "or": "OR",
            "not": "NOT",
            "in": "IN",
            "contains": "CONTAINS",
            "incoming": "INCOMING",
            "outgoing": "OUTGOING",
        }

        # Check for lowercase keywords
        query_lower = query.lower()
        for wrong, correct in keywords.items():
            if wrong in query_lower and correct not in query:
                return f"Keywords are case-sensitive. Use '{correct}' instead of '{wrong}'"

        return None

    def _fuzzy_match(self, word: str, candidates: List[str], threshold: float = 0.7) -> Optional[str]:
        """
        Find closest match using fuzzy string matching

        Args:
            word: Word to match
            candidates: List of candidate words
            threshold: Minimum similarity threshold (0.0 to 1.0)

        Returns:
            Best match or None
        """
        try:
            # Try to use python-Levenshtein if available
            import Levenshtein  # type: ignore[import-not-found]

            best_match = None
            best_ratio = 0.0

            for candidate in candidates:
                ratio = Levenshtein.ratio(word.lower(), candidate.lower())
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = candidate

            return best_match
        except ImportError:
            # Fallback: simple substring matching
            word_lower = word.lower()
            for candidate in candidates:
                if word_lower in candidate.lower() or candidate.lower() in word_lower:
                    return candidate
            return None

    # ========================================================================
    # Formatting Methods
    # ========================================================================

    def format_errors(self, errors: List[ParserError], use_colors: bool = False) -> str:
        """
        Format multiple errors for display

        Args:
            errors: List of ParserError objects
            use_colors: Whether to use terminal colors

        Returns:
            Formatted error string
        """
        if not errors:
            return ""

        parts = []

        # Header
        error_count = len(errors)
        if use_colors and COLORAMA_AVAILABLE:
            parts.append(f"{Fore.RED}{Style.BRIGHT}Found {error_count} error(s):{Style.RESET_ALL}\n")
        else:
            parts.append(f"Found {error_count} error(s):\n")

        # Format each error
        for i, error in enumerate(errors, 1):
            parts.append(f"\n{i}. {error.format(use_colors=use_colors)}")

        return "\n".join(parts)

    def format_for_api(self, errors: List[ParserError]) -> List[dict]:
        """
        Format errors for API response (JSON-serializable)

        Args:
            errors: List of ParserError objects

        Returns:
            List of error dictionaries
        """
        return [
            {
                "line": error.line,
                "column": error.column,
                "message": error.message,
                "suggestion": error.suggestion,
                "phase": error.phase,
                "context": error.context,
            }
            for error in errors
        ]

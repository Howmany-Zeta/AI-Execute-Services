# Logic Query Parser Documentation

## Overview

The Logic Query Parser is a declarative query language parser for knowledge graph reasoning. It parses human-readable query strings into Abstract Syntax Trees (AST) that can be executed against a knowledge graph.

**Phase**: 2.4 - Logic Query Parser  
**Version**: 1.0  
**Status**: Phase 2 - Parser Implementation Complete

## Features

- **Declarative Syntax**: Write queries in a natural, SQL-like language
- **Type-Safe Parsing**: Full type hints and immutable AST nodes
- **Two-Phase Error Handling**: Syntax errors (fatal) and semantic errors (accumulated)
- **Comprehensive Error Messages**: Line/column information with helpful suggestions
- **Thread-Safe**: Each parse creates a fresh context
- **LALR Parser**: Fast, deterministic parsing with Lark

## Quick Start

### Installation

The parser requires `lark-parser`:

```bash
pip install lark-parser
# or with poetry
poetry add lark-parser
```

### Basic Usage

```python
from aiecs.application.knowledge_graph.reasoning.logic_parser import LogicQueryParser

# Create parser
parser = LogicQueryParser()

# Parse a query
result = parser.parse("Find(Person) WHERE age > 30")

if isinstance(result, list):
    # Errors occurred
    for error in result:
        print(f"Error at line {error.line}, col {error.column}: {error.message}")
        if error.suggestion:
            print(f"  Suggestion: {error.suggestion}")
else:
    # Success - got parse tree
    print("Parse tree:", result.pretty())
```

## Query Syntax

### Find Clause

Select entities by type or name:

```
Find(Person)                    # All persons
Find(Person[`Alice`])           # Specific person named "Alice"
Find(Paper[`Deep Learning`])    # Specific paper
```

### WHERE Clause

Filter entities by properties:

```
Find(Person) WHERE age > 30
Find(Paper) WHERE year >= 2020 AND citations > 100
Find(Person) WHERE name == "Alice" OR name == "Bob"
Find(Person) WHERE NOT (age < 18)
```

**Supported Operators**:
- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Boolean: `AND`, `OR`, `NOT`
- Special: `IN`, `CONTAINS`

**Operator Precedence** (highest to lowest):
1. `NOT` (unary)
2. `AND` (binary)
3. `OR` (binary)

### FOLLOWS Clause

Navigate graph relationships:

```
Find(Person) FOLLOWS AuthoredBy                    # Outgoing (default)
Find(Paper) FOLLOWS AuthoredBy INCOMING            # Incoming
Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn  # Multi-hop
```

### Complex Queries

Combine all features:

```
Find(Person) FOLLOWS WorksAt WHERE industry == "tech"
Find(Person) WHERE age > 25 FOLLOWS AuthoredBy WHERE year > 2020
Find(Paper) WHERE title CONTAINS "machine learning" AND year >= 2020
```

## API Reference

### LogicQueryParser

Main parser class for parsing Logic Query DSL.

```python
class LogicQueryParser:
    def __init__(self, schema: Any = None)
    def parse(self, query: str) -> Union[ParseTree, List[ParserError]]
    def parse_tree_to_string(self, parse_tree: Any) -> str
```

**Methods**:

#### `__init__(schema=None)`

Initialize the parser.

**Parameters**:
- `schema` (optional): SchemaManager instance for validation

**Raises**:
- `ImportError`: If lark-parser is not installed

#### `parse(query: str)`

Parse a query string into a parse tree.

**Parameters**:
- `query`: Query string to parse

**Returns**:
- Parse tree if successful
- List of `ParserError` if errors occurred

**Example**:
```python
result = parser.parse("Find(Person) WHERE age > 30")
if isinstance(result, list):
    # Handle errors
    for error in result:
        print(error.message)
else:
    # Use parse tree
    print(result.pretty())
```

#### `parse_tree_to_string(parse_tree)`

Convert parse tree to string representation.

**Parameters**:
- `parse_tree`: Lark parse tree

**Returns**:
- String representation of the parse tree

### ParserError

Error class for parsing errors.

```python
class ParserError:
    line: int           # Line number (1-based)
    column: int         # Column number (1-based)
    message: str        # Error message
    suggestion: str     # Optional suggestion
    phase: str          # "syntax" or "semantic"
```

**Example**:
```python
error = ParserError(
    line=1,
    column=10,
    message="Unexpected token",
    suggestion="Check for missing parentheses",
    phase="syntax"
)
```

## Error Handling

The parser implements two-phase error handling:

### Phase 1: Syntax Errors (Fatal)

Syntax errors stop parsing immediately and return a single error.

**Common Syntax Errors**:
- Missing parentheses: `Find(Person`
- Wrong keyword case: `find(Person)` (should be `Find`)
- Invalid operators: `age = 30` (should be `==`)
- Incomplete WHERE: `Find(Person) WHERE`

**Example**:
```python
result = parser.parse("Find(Person")
# Returns: [ParserError(line=1, col=6, message="Unexpected token...")]
```

### Phase 2: Semantic Errors (Accumulated)

Semantic errors are accumulated during validation (to be implemented in Task 3.1).

**Example** (future):
```python
result = parser.parse("Find(InvalidType) WHERE unknown_field > 30")
# Returns: [
#   ParserError(line=1, col=6, message="Entity type 'InvalidType' not found"),
#   ParserError(line=1, col=25, message="Property 'unknown_field' not found")
# ]
```

## Error Messages with Suggestions

The parser provides helpful suggestions for common errors:

```python
# Missing parenthesis
result = parser.parse("Find(Person")
# Error: "Unexpected token..."
# Suggestion: "Check for missing or mismatched parentheses"

# Wrong keyword case
result = parser.parse("find(Person)")
# Error: "Unexpected token 'find'..."
# Suggestion: "Keywords are case-sensitive. Use 'Find' instead of 'find'"
```

## Thread Safety

The parser is thread-safe. Each `parse()` call is independent.

```python
# ✅ SAFE: Concurrent parsing
from concurrent.futures import ThreadPoolExecutor

parser = LogicQueryParser()

def parse_query(query):
    return parser.parse(query)

with ThreadPoolExecutor() as executor:
    results = executor.map(parse_query, [
        "Find(Person)",
        "Find(Paper) WHERE year > 2020",
        "Find(Company)"
    ])
```

## Performance

### Parser Caching

The parser can be cached for better performance:

```python
from aiecs.application.knowledge_graph.reasoning.logic_parser.parser import get_cached_parser

# Get cached parser (reuses Lark instance)
parser = get_cached_parser()
result = parser.parse("Find(Person)")
```

**Note**: The cache is based on schema ID. If schema changes, use a different ID.

## Examples

### Example 1: Simple Entity Lookup
```python
result = parser.parse("Find(Person)")
# Returns parse tree for all persons
```

### Example 2: Filter by Age
```python
result = parser.parse("Find(Person) WHERE age > 30")
# Returns parse tree for persons older than 30
```

### Example 3: Boolean Logic
```python
result = parser.parse(
    'Find(Person) WHERE (name == "Alice" OR name == "Bob") AND age > 30'
)
# Returns parse tree for Alice or Bob, both over 30
```

### Example 4: Graph Traversal
```python
result = parser.parse("Find(Person) FOLLOWS AuthoredBy WHERE year > 2020")
# Returns parse tree for persons → papers authored after 2020
```

### Example 5: Error Handling
```python
result = parser.parse("Find(Person")

if isinstance(result, list):
    error = result[0]
    print(f"Syntax error at line {error.line}, column {error.column}")
    print(f"Message: {error.message}")
    if error.suggestion:
        print(f"Suggestion: {error.suggestion}")
```

## Grammar Reference

See [grammar-docs.md](../../../aiecs/application/knowledge_graph/reasoning/logic_parser/grammar-docs.md) for complete grammar specification.

## Next Steps

- **Task 2.2**: AST Builder - Transform parse trees to AST nodes
- **Task 2.3**: Error Handler - Enhanced error messages and recovery
- **Task 3.1**: AST Validator - Semantic validation against schema
- **Task 3.2**: QueryPlan Conversion - Convert AST to executable query plans

## Related Documentation

- [Grammar Documentation](../../../aiecs/application/knowledge_graph/reasoning/logic_parser/grammar-docs.md)
- [AST Node Reference](../../../aiecs/application/knowledge_graph/reasoning/logic_parser/ast_nodes.py)
- [Query Context](../../../aiecs/application/knowledge_graph/reasoning/logic_parser/query_context.py)

## Support

For issues or questions, refer to:
- Design Document: `openspec/changes/phase-2-4-logic-enhanced/design.md`
- Proposal: `openspec/changes/phase-2-4-logic-enhanced/proposal.md`
- Tasks: `openspec/changes/phase-2-4-logic-enhanced/tasks.md`


# Logic Query DSL Grammar Documentation

## Overview

This document describes the complete EBNF grammar for the Logic Query DSL, a declarative language for querying knowledge graphs. The grammar is designed to be unambiguous, LALR-parseable, and extensible.

**Grammar File**: `grammar.lark`  
**Parser**: Lark (LALR algorithm)  
**Version**: 1.0  
**Phase**: 2.4 - Logic Query Parser

## Grammar Structure

### Top-Level Query

```ebnf
query ::= find_clause traversal_clause* where_clause?
```

A query consists of:
1. **Required**: A `Find` clause to select entities
2. **Optional**: Zero or more `FOLLOWS` clauses for graph traversal
3. **Optional**: A `WHERE` clause for filtering

**Examples**:
```
Find(Person)
Find(Person) WHERE age > 30
Find(Person) FOLLOWS AuthoredBy FIND(Paper)
Find(Person) FOLLOWS AuthoredBy WHERE year > 2020
```

### Find Clause - Entity Selection

```ebnf
find_clause ::= "Find" "(" entity_spec ")"
entity_spec ::= IDENTIFIER ("[" entity_name "]")?
entity_name ::= BACKTICK_STRING
```

**Purpose**: Select entities by type or by specific name.

**Examples**:
```
Find(Person)                    # All entities of type Person
Find(Person[`Alice`])           # Specific entity named "Alice"
Find(Paper[`Deep Learning`])    # Specific paper
Find(Company)                   # All companies
```

**Notes**:
- Entity type is an IDENTIFIER (alphanumeric + underscore)
- Entity name uses backticks to allow spaces and special characters
- Entity name is optional (omit for all entities of that type)

### Traversal Clause - Graph Navigation

```ebnf
traversal_clause ::= "FOLLOWS" relation_spec direction?
relation_spec ::= IDENTIFIER
direction ::= "INCOMING" | "OUTGOING"
```

**Purpose**: Navigate graph relationships.

**Examples**:
```
FOLLOWS AuthoredBy              # Follow AuthoredBy relation (default: outgoing)
FOLLOWS AuthoredBy OUTGOING     # Explicit outgoing direction
FOLLOWS AuthoredBy INCOMING     # Reverse direction
FOLLOWS WorksAt                 # Follow WorksAt relation
```

**Notes**:
- Direction defaults to OUTGOING if not specified
- INCOMING reverses the relation direction
- Multiple FOLLOWS clauses create multi-hop traversals

### Where Clause - Filtering

```ebnf
where_clause ::= "WHERE" condition
condition ::= simple_condition | compound_condition | "(" condition ")"
simple_condition ::= property_path operator value
compound_condition ::= condition ("AND" | "OR") condition | "NOT" condition
```

**Purpose**: Filter entities based on property values.

**Examples**:
```
WHERE name == "Alice"
WHERE age > 30
WHERE year >= 2020 AND citations > 100
WHERE (name == "Alice" OR name == "Bob") AND age > 30
WHERE NOT (status == "inactive")
WHERE title CONTAINS "machine learning"
WHERE status IN ["active", "pending"]
```

**Operator Precedence** (highest to lowest):
1. `NOT` (unary)
2. `AND` (binary)
3. `OR` (binary)

**Notes**:
- Use parentheses to override precedence
- Operators are case-sensitive (use uppercase: AND, OR, NOT)

### Property Paths

```ebnf
property_path ::= IDENTIFIER ("." IDENTIFIER)*
```

**Purpose**: Access nested properties.

**Examples**:
```
name                    # Top-level property
age                     # Top-level property
address.city            # Nested property
metadata.created_at     # Nested property
```

**Notes**:
- Dot notation for nested properties
- No limit on nesting depth (implementation-dependent)

### Operators

```ebnf
operator ::= "==" | "!=" | ">" | "<" | ">=" | "<=" | "IN" | "CONTAINS"
```

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equality | `age == 30` |
| `!=` | Inequality | `status != "inactive"` |
| `>` | Greater than | `year > 2020` |
| `<` | Less than | `age < 18` |
| `>=` | Greater or equal | `citations >= 100` |
| `<=` | Less or equal | `score <= 0.5` |
| `IN` | Membership | `status IN ["active", "pending"]` |
| `CONTAINS` | Substring | `title CONTAINS "learning"` |

**Notes**:
- All operators are case-sensitive
- `IN` requires a list value
- `CONTAINS` is for string matching (case-sensitive)

### Values and Literals

```ebnf
value ::= STRING | NUMBER | BOOLEAN | list | IDENTIFIER
list ::= "[" [value ("," value)*] "]"
```

**String Literals**:
```
"Alice"                 # Double-quoted
'Bob'                   # Single-quoted
"Hello, World!"         # With punctuation
```

**Number Literals**:
```
42                      # Integer
3.14                    # Float
0.001                   # Small float
```

**Boolean Literals**:
```
true                    # Lowercase
false                   # Lowercase
True                    # Capitalized (also valid)
False                   # Capitalized (also valid)
```

**List Literals**:
```
[1, 2, 3]              # Number list
["active", "pending"]   # String list
[true, false]          # Boolean list
[]                     # Empty list
```

**Identifier Values**:
```
variable_name          # Reference to variable (future use)
```

## Complete Examples

### Example 1: Simple Entity Lookup
```
Find(Person)
```
**Meaning**: Find all entities of type Person.

### Example 2: Entity with Name
```
Find(Person[`Alice Smith`])
```
**Meaning**: Find the specific person named "Alice Smith".

### Example 3: Filter by Property
```
Find(Person) WHERE age > 30
```
**Meaning**: Find all persons older than 30.

### Example 4: Multiple Filters with AND
```
Find(Paper) WHERE year > 2020 AND citations >= 100
```
**Meaning**: Find papers published after 2020 with at least 100 citations.

### Example 5: Multiple Filters with OR
```
Find(Person) WHERE name == "Alice" OR name == "Bob"
```
**Meaning**: Find persons named Alice or Bob.

### Example 6: Complex Boolean Logic
```
Find(Person) WHERE (name == "Alice" OR name == "Bob") AND age > 30
```
**Meaning**: Find persons named Alice or Bob who are older than 30.

### Example 7: NOT Operator
```
Find(Person) WHERE NOT (age < 18)
```
**Meaning**: Find persons who are NOT under 18 (i.e., 18 or older).

### Example 8: IN Operator
```
Find(Person) WHERE status IN ["active", "pending"]
```
**Meaning**: Find persons with status "active" or "pending".

### Example 9: CONTAINS Operator
```
Find(Paper) WHERE title CONTAINS "machine learning"
```
**Meaning**: Find papers whose title contains "machine learning".

### Example 10: Single-Hop Traversal
```
Find(Person[`Alice`]) FOLLOWS AuthoredBy
```
**Meaning**: Find entities that Alice authored (follow AuthoredBy relation).

### Example 11: Multi-Hop Traversal
```
Find(Person) FOLLOWS AuthoredBy FOLLOWS PublishedIn
```
**Meaning**: Find persons → papers they authored → venues where published.

### Example 12: Traversal with Direction
```
Find(Paper) FOLLOWS AuthoredBy INCOMING
```
**Meaning**: Find papers ← authors (reverse direction).

### Example 13: Traversal with Filter
```
Find(Person) FOLLOWS AuthoredBy WHERE year > 2020
```
**Meaning**: Find persons → papers authored after 2020.

### Example 14: Nested Properties
```
Find(Person) WHERE address.city == "Seattle"
```
**Meaning**: Find persons living in Seattle (nested property).

### Example 15: Complex Query
```
Find(Person) WHERE age > 25 FOLLOWS WorksAt WHERE industry == "tech"
```
**Meaning**: Find persons over 25 → companies they work at in tech industry.

## Grammar Validation

The grammar has been validated to be:
- ✅ **Unambiguous**: No shift/reduce or reduce/reduce conflicts
- ✅ **LALR-parseable**: Compatible with Lark's LALR(1) parser
- ✅ **Deterministic**: Each input has exactly one parse tree
- ✅ **Complete**: Covers all DSL constructs from design spec

## Operator Precedence Table

| Precedence | Operator | Associativity | Example |
|------------|----------|---------------|---------|
| 1 (highest) | `NOT` | Right | `NOT a AND b` = `(NOT a) AND b` |
| 2 | `AND` | Left | `a AND b AND c` = `(a AND b) AND c` |
| 3 (lowest) | `OR` | Left | `a OR b OR c` = `(a OR b) OR c` |

**Comparison operators** (`==`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `CONTAINS`) have no precedence among themselves (cannot chain).

## Reserved Keywords

The following keywords are reserved and cannot be used as identifiers:

- `Find`
- `WHERE`
- `FOLLOWS`
- `INCOMING`
- `OUTGOING`
- `AND`
- `OR`
- `NOT`
- `IN`
- `CONTAINS`
- `true`, `false`, `True`, `False`

## Terminal Symbols

| Terminal | Pattern | Description |
|----------|---------|-------------|
| `IDENTIFIER` | `[a-zA-Z_][a-zA-Z0-9_]*` | Variable/type names |
| `STRING` | `"..."` or `'...'` | String literals |
| `BACKTICK_STRING` | `` `...` `` | Entity names |
| `NUMBER` | `[0-9]+(\.[0-9]+)?` | Numeric literals |
| `BOOLEAN` | `true\|false` (case-insensitive) | Boolean literals |

## Future Extensions

The grammar is designed to support future extensions:

1. **Aggregations**: `AGGREGATE COUNT(*)`, `SUM(citations)`
2. **Subqueries**: `WHERE id IN (Find(...))`
3. **Query Macros**: `DEFINE macro_name AS ...`
4. **Qualified Relations**: `FOLLOWS Person.MEMBER_OF`
5. **Query Hints**: `/*+ INDEX(name_idx) */`

These extensions can be added without breaking existing queries.

## References

- **EBNF Standard**: ISO/IEC 14977
- **Lark Documentation**: https://lark-parser.readthedocs.io/
- **Design Document**: `openspec/changes/phase-2-4-logic-enhanced/design.md`
- **Proposal**: `openspec/changes/phase-2-4-logic-enhanced/proposal.md`


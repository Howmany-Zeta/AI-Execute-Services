# Type Enum Usage Guide

**Version**: 1.0  
**Date**: 2025-11-14  
**Phase**: 3.5 - Documentation and Benchmarks

## Overview

This guide explains how to use dynamically generated type enums for entity and relation types. Type enums provide type safety, IDE autocomplete, and compile-time validation while maintaining backward compatibility with string literals.

## Generating Type Enums

### Basic Usage

Generate enums from your schema:

```python
from aiecs.domain.knowledge_graph.schema.schema_manager import SchemaManager

# Load schema
schema_manager = SchemaManager.load_from_file("schema.json")

# Generate enums
enums = schema_manager.generate_enums()

# Access entity type enums
PersonEnum = enums["entity_types"]["Person"]
PaperEnum = enums["entity_types"]["Paper"]
CompanyEnum = enums["entity_types"]["Company"]

# Access relation type enums
WorksForEnum = enums["relation_types"]["WORKS_FOR"]
AuthoredByEnum = enums["relation_types"]["AUTHORED_BY"]
```

### Enum Structure

Generated enums have the following structure:

```python
# Entity type enum
PersonEnum.PERSON  # "Person"
PersonEnum.PERSON.value  # "Person"
PersonEnum.PERSON.name  # "PERSON"

# Relation type enum
WorksForEnum.WORKS_FOR  # "WORKS_FOR"
WorksForEnum.WORKS_FOR.value  # "WORKS_FOR"
WorksForEnum.WORKS_FOR.name  # "WORKS_FOR"
```

## Using Type Enums

### In Queries

Use enums in query construction:

```python
from aiecs.domain.knowledge_graph.models.query import GraphQuery

# Generate enums
enums = schema_manager.generate_enums()
PersonEnum = enums["entity_types"]["Person"]

# Use enum in query
query = GraphQuery(
    entity_type=PersonEnum.PERSON,  # Type-safe!
    max_results=100
)

# Backward compatible - still works as string
assert str(PersonEnum.PERSON) == "Person"
assert PersonEnum.PERSON == "Person"
```

### In Function Signatures

Use enums for type hints:

```python
from typing import Union
from aiecs.domain.knowledge_graph.schema.type_enums import EntityTypeEnum

def get_entities(
    entity_type: Union[str, EntityTypeEnum],
    max_results: int = 100
) -> List[Entity]:
    """
    Get entities by type
    
    Args:
        entity_type: Entity type (string or enum)
        max_results: Maximum number of results
        
    Returns:
        List of entities
    """
    # Convert to string (works for both)
    type_str = str(entity_type)
    return graph_store.get_entities_by_type(type_str, max_results)

# Use with enum
PersonEnum = enums["entity_types"]["Person"]
entities = get_entities(PersonEnum.PERSON)

# Still works with string
entities = get_entities("Person")
```

### In Validation

Use enums for validation:

```python
def validate_entity_type(entity_type: str) -> bool:
    """Validate entity type exists in schema"""
    enums = schema_manager.generate_enums()
    valid_types = enums["entity_types"].keys()
    return entity_type in valid_types

# Validate
if validate_entity_type("Person"):
    print("Valid entity type")
else:
    print("Invalid entity type")
```

### In Pattern Matching

Use enums in pattern matching:

```python
from aiecs.domain.knowledge_graph.models.path_pattern import PathPattern

# Generate enums
enums = schema_manager.generate_enums()
PersonEnum = enums["entity_types"]["Person"]
WorksForEnum = enums["relation_types"]["WORKS_FOR"]

# Use in pattern
pattern = PathPattern(
    entity_types=[PersonEnum.PERSON],  # Type-safe
    relation_types=[WorksForEnum.WORKS_FOR],
    max_depth=2
)
```

## Backward Compatibility

### String Compatibility

Enums are fully backward compatible with strings:

```python
PersonEnum = enums["entity_types"]["Person"]

# String conversion
assert str(PersonEnum.PERSON) == "Person"

# String comparison
assert PersonEnum.PERSON == "Person"

# String formatting
print(f"Entity type: {PersonEnum.PERSON}")  # "Entity type: Person"

# In dictionaries
type_map = {"person": PersonEnum.PERSON}
assert type_map["person"] == "Person"
```

### Existing Code

Existing code using strings continues to work:

```python
# Old code (still works)
query = GraphQuery(
    entity_type="Person",  # String literal
    max_results=100
)

# New code (type-safe)
PersonEnum = enums["entity_types"]["Person"]
query = GraphQuery(
    entity_type=PersonEnum.PERSON,  # Enum
    max_results=100
)

# Both produce the same result
```

## Benefits of Type Enums

### 1. Type Safety

Catch errors at compile time:

```python
# With enum - IDE catches typo
PersonEnum.PERSN  # AttributeError at compile time

# With string - error at runtime
entity_type = "Persn"  # Typo not caught until runtime
```

### 2. IDE Autocomplete

Get autocomplete suggestions:

```python
# Type "PersonEnum." and IDE shows:
# - PERSON
# - value
# - name

# Type "enums['entity_types'][" and IDE shows all entity types
```

### 3. Refactoring Support

Rename types safely:

```python
# If you rename "Person" to "Individual" in schema:
# - Enum automatically updates
# - IDE finds all usages
# - Refactoring is safe

# With strings:
# - Must find/replace manually
# - Easy to miss occurrences
# - Risky refactoring
```

### 4. Documentation

Self-documenting code:

```python
# Clear what types are expected
def process_person(person_type: PersonEnum):
    """Process person (type is clear from signature)"""
    pass

# Less clear with strings
def process_person(person_type: str):
    """Process person (what strings are valid?)"""
    pass
```

## Advanced Usage

### Iterating Over Enums

Iterate over all enum members:

```python
PersonEnum = enums["entity_types"]["Person"]

# Iterate over members
for member in PersonEnum:
    print(f"{member.name} = {member.value}")

# Output:
# PERSON = Person
```

### Enum Comparison

Compare enums:

```python
PersonEnum = enums["entity_types"]["Person"]
PaperEnum = enums["entity_types"]["Paper"]

# Compare enum members
assert PersonEnum.PERSON != PaperEnum.PAPER

# Compare with strings
assert PersonEnum.PERSON == "Person"
assert PaperEnum.PAPER == "Paper"
```

### Dynamic Enum Access

Access enums dynamically:

```python
# Get enum by name
entity_type_name = "Person"
EntityEnum = enums["entity_types"][entity_type_name]

# Get enum member
enum_member = EntityEnum.PERSON

# Or use getattr
enum_member = getattr(EntityEnum, "PERSON")
```

## Best Practices

### 1. Generate Enums Once

Generate enums once at startup:

```python
# At application startup
schema_manager = SchemaManager.load_from_file("schema.json")
TYPE_ENUMS = schema_manager.generate_enums()

# Use throughout application
def get_person_entities():
    PersonEnum = TYPE_ENUMS["entity_types"]["Person"]
    return get_entities(PersonEnum.PERSON)
```

### 2. Use Type Hints

Add type hints for better IDE support:

```python
from typing import Union
from aiecs.domain.knowledge_graph.schema.type_enums import EntityTypeEnum

def get_entities(
    entity_type: Union[str, EntityTypeEnum]
) -> List[Entity]:
    """Get entities (accepts string or enum)"""
    return graph_store.get_entities_by_type(str(entity_type))
```

### 3. Prefer Enums in New Code

Use enums in new code for type safety:

```python
# New code - use enums
PersonEnum = TYPE_ENUMS["entity_types"]["Person"]
query = GraphQuery(entity_type=PersonEnum.PERSON)

# Old code - keep strings for backward compatibility
query = GraphQuery(entity_type="Person")
```

### 4. Document Enum Usage

Document when enums are expected:

```python
def create_entity(
    entity_type: Union[str, EntityTypeEnum],
    properties: Dict[str, Any]
) -> Entity:
    """
    Create entity
    
    Args:
        entity_type: Entity type (string or enum)
            Use TYPE_ENUMS["entity_types"]["Person"].PERSON for type safety
        properties: Entity properties
        
    Returns:
        Created entity
    """
    pass
```

## Migration Guide

### Migrating Existing Code

Gradually migrate to enums:

```python
# Step 1: Generate enums
TYPE_ENUMS = schema_manager.generate_enums()

# Step 2: Update function signatures (optional)
def get_entities(
    entity_type: Union[str, EntityTypeEnum]  # Accept both
) -> List[Entity]:
    return graph_store.get_entities_by_type(str(entity_type))

# Step 3: Update call sites (gradually)
# Old
entities = get_entities("Person")

# New
PersonEnum = TYPE_ENUMS["entity_types"]["Person"]
entities = get_entities(PersonEnum.PERSON)
```

### No Breaking Changes

Migration is optional - strings still work:

```python
# All of these work:
query1 = GraphQuery(entity_type="Person")  # String
query2 = GraphQuery(entity_type=PersonEnum.PERSON)  # Enum
query3 = GraphQuery(entity_type=str(PersonEnum.PERSON))  # Explicit conversion

# All produce the same result
```

## Conclusion

Type enums provide type safety and better developer experience while maintaining full backward compatibility. Use them in new code for better IDE support and compile-time validation.

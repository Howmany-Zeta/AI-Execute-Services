# Schema Mapping Configuration Guide

This guide explains how to configure schema mappings for importing structured data (CSV, JSON) into knowledge graphs.

## Table of Contents

1. [Overview](#overview)
2. [Basic Concepts](#basic-concepts)
3. [Entity Mapping](#entity-mapping)
4. [Relation Mapping](#relation-mapping)
5. [Property Transformations](#property-transformations)
6. [Complete Examples](#complete-examples)
7. [Best Practices](#best-practices)

## Overview

Schema mapping allows you to declaratively map structured data columns to knowledge graph entities and relations. This eliminates the need for custom code for each data source.

**Key Benefits:**
- **Declarative**: Define mappings in configuration, not code
- **Flexible**: Support complex transformations (rename, type cast, compute)
- **Reusable**: Same mapping works across multiple data sources
- **Type-safe**: Validation ensures data consistency

## Basic Concepts

### SchemaMapping

The `SchemaMapping` class is the container for all mappings:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import SchemaMapping

mapping = SchemaMapping(
    entity_mappings=[...],  # How to create entities
    relation_mappings=[...],  # How to create relations
    description="My data mapping"
)
```

### EntityMapping

Maps source columns to entity types:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import EntityMapping

entity_mapping = EntityMapping(
    source_columns=["id", "name", "age"],
    entity_type="Person",
    property_mapping={"id": "id", "name": "name", "age": "age"},
    id_column="id"
)
```

### RelationMapping

Maps source columns to relations between entities:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import RelationMapping

relation_mapping = RelationMapping(
    source_columns=["emp_id", "dept_id"],
    relation_type="WORKS_IN",
    source_entity_column="emp_id",
    target_entity_column="dept_id"
)
```

## Entity Mapping

### Simple Entity Mapping

Map columns directly to entity properties:

```python
EntityMapping(
    source_columns=["id", "name", "email"],
    entity_type="Person",
    property_mapping={
        "id": "id",
        "name": "name",
        "email": "email"
    },
    id_column="id"
)
```

### Entity Mapping with ID Column

Specify which column to use as entity ID:

```python
EntityMapping(
    source_columns=["employee_id", "full_name", "department"],
    entity_type="Employee",
    property_mapping={
        "employee_id": "id",
        "full_name": "name",
        "department": "dept"
    },
    id_column="employee_id"  # Use employee_id as entity ID
)
```

### Multiple Entity Types from Same Row

You can create multiple entities from a single row:

```python
mapping = SchemaMapping(
    entity_mappings=[
        # Create Employee entity
        EntityMapping(
            source_columns=["emp_id", "emp_name"],
            entity_type="Employee",
            property_mapping={"emp_id": "id", "emp_name": "name"},
            id_column="emp_id"
        ),
        # Create Department entity from same row
        EntityMapping(
            source_columns=["dept_id", "dept_name"],
            entity_type="Department",
            property_mapping={"dept_id": "id", "dept_name": "name"},
            id_column="dept_id"
        )
    ]
)
```

## Relation Mapping

### Basic Relation Mapping

Create relations between entities:

```python
RelationMapping(
    source_columns=["person_id", "company_id"],
    relation_type="WORKS_FOR",
    source_entity_column="person_id",
    target_entity_column="company_id"
)
```

### Relation with Properties

Add properties to relations:

```python
RelationMapping(
    source_columns=["person_id", "company_id", "role", "since"],
    relation_type="WORKS_FOR",
    source_entity_column="person_id",
    target_entity_column="company_id",
    property_mapping={
        "role": "position",
        "since": "start_date"
    }
)
```

## Property Transformations

Transformations allow you to modify values during import.

### Transformation Types

1. **RENAME**: Rename a column to a property
2. **TYPE_CAST**: Convert value to different type
3. **COMPUTE**: Compute value from multiple columns
4. **CONSTANT**: Use a constant value
5. **SKIP**: Skip this column

### RENAME Transformation

Simply rename a column:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    PropertyTransformation,
    TransformationType
)

transformation = PropertyTransformation(
    transformation_type=TransformationType.RENAME,
    source_column="full_name",
    target_property="name"
)
```

### TYPE_CAST Transformation

Convert string to integer, float, boolean, etc.:

```python
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

transformation = PropertyTransformation(
    transformation_type=TransformationType.TYPE_CAST,
    source_column="age_str",
    target_property="age",
    target_type=PropertyType.INTEGER
)
```

**Supported Types:**
- `PropertyType.STRING`
- `PropertyType.INTEGER`
- `PropertyType.FLOAT`
- `PropertyType.BOOLEAN`
- `PropertyType.LIST` (from JSON string or comma-separated)
- `PropertyType.DICT` (from JSON string)
- `PropertyType.ANY`

### COMPUTE Transformation

Compute values from multiple columns:

```python
# Concatenate first and last name
transformation = PropertyTransformation(
    transformation_type=TransformationType.COMPUTE,
    source_column="first_name",
    target_property="full_name",
    compute_function="concat_space",
    compute_args=["last_name"]
)

# Sum multiple columns
transformation = PropertyTransformation(
    transformation_type=TransformationType.COMPUTE,
    source_column="price1",
    target_property="total_price",
    compute_function="sum",
    compute_args=["price2", "price3"]
)
```

**Available Compute Functions:**
- `concat`: Concatenate strings
- `concat_space`: Concatenate with space separator
- `concat_comma`: Concatenate with comma separator
- `sum`: Sum numeric values
- `avg` / `average`: Average numeric values
- `max`: Maximum value
- `min`: Minimum value

### CONSTANT Transformation

Use a constant value:

```python
transformation = PropertyTransformation(
    transformation_type=TransformationType.CONSTANT,
    target_property="status",
    constant_value="active"
)
```

### SKIP Transformation

Skip a column (don't import it):

```python
transformation = PropertyTransformation(
    transformation_type=TransformationType.SKIP,
    target_property="internal_id"
)
```

## Complete Examples

### Example 1: Employee Data

**CSV Structure:**
```csv
emp_id,name,email,dept_id,dept_name,role,salary
E001,Alice Smith,alice@example.com,D001,Engineering,Engineer,100000
E002,Bob Jones,bob@example.com,D001,Engineering,Manager,120000
```

**Mapping:**
```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

mapping = SchemaMapping(
    entity_mappings=[
        # Employee entity
        EntityMapping(
            source_columns=["emp_id", "name", "email", "salary"],
            entity_type="Employee",
            property_mapping={
                "emp_id": "id",
                "name": "name",
                "email": "email"
            },
            transformations=[
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="salary",
                    target_property="salary",
                    target_type=PropertyType.INTEGER
                )
            ],
            id_column="emp_id"
        ),
        # Department entity
        EntityMapping(
            source_columns=["dept_id", "dept_name"],
            entity_type="Department",
            property_mapping={"dept_id": "id", "dept_name": "name"},
            id_column="dept_id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_columns=["emp_id", "dept_id", "role"],
            relation_type="WORKS_IN",
            source_entity_column="emp_id",
            target_entity_column="dept_id",
            property_mapping={"role": "position"}
        )
    ]
)
```

### Example 2: Product Catalog

**JSON Structure:**
```json
[
  {
    "product_id": "P001",
    "product_name": "Laptop",
    "category": "Electronics",
    "price": "999.99",
    "in_stock": "true"
  }
]
```

**Mapping:**
```python
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["product_id", "product_name", "category", "price", "in_stock"],
            entity_type="Product",
            property_mapping={"product_id": "id", "product_name": "name"},
            transformations=[
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="price",
                    target_property="price",
                    target_type=PropertyType.FLOAT
                ),
                PropertyTransformation(
                    transformation_type=TransformationType.TYPE_CAST,
                    source_column="in_stock",
                    target_property="available",
                    target_type=PropertyType.BOOLEAN
                ),
                PropertyTransformation(
                    transformation_type=TransformationType.RENAME,
                    source_column="category",
                    target_property="category"
                )
            ],
            id_column="product_id"
        )
    ]
)
```

### Example 3: Complex Transformations

**CSV with computed fields:**
```csv
first_name,last_name,birth_year,score1,score2,score3
John,Doe,1990,85,90,88
Jane,Smith,1985,92,88,95
```

**Mapping with computed full name and average score:**
```python
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["first_name", "last_name", "birth_year", "score1", "score2", "score3"],
            entity_type="Student",
            transformations=[
                # Compute full name
                PropertyTransformation(
                    transformation_type=TransformationType.COMPUTE,
                    source_column="first_name",
                    target_property="full_name",
                    compute_function="concat_space",
                    compute_args=["last_name"]
                ),
                # Compute average score
                PropertyTransformation(
                    transformation_type=TransformationType.COMPUTE,
                    source_column="score1",
                    target_property="avg_score",
                    compute_function="avg",
                    compute_args=["score2", "score3"]
                ),
                # Calculate age from birth year
                PropertyTransformation(
                    transformation_type=TransformationType.COMPUTE,
                    source_column="birth_year",
                    target_property="age",
                    compute_function="subtract",  # Would need to implement
                    compute_args=["2024"]  # Current year
                )
            ],
            id_column="first_name"  # Use first_name as ID (not recommended for production)
        )
    ]
)
```

## Best Practices

### 1. Always Specify ID Columns

```python
# ✅ Good
EntityMapping(
    source_columns=["id", "name"],
    entity_type="Person",
    id_column="id"  # Explicit ID column
)

# ❌ Avoid (uses first column as ID, less clear)
EntityMapping(
    source_columns=["id", "name"],
    entity_type="Person"
)
```

### 2. Use Type Casting for Numeric Data

```python
# ✅ Good - CSV reads as string, cast to integer
PropertyTransformation(
    transformation_type=TransformationType.TYPE_CAST,
    source_column="age_str",
    target_property="age",
    target_type=PropertyType.INTEGER
)

# ❌ Avoid - Leaves as string
property_mapping={"age_str": "age"}
```

### 3. Validate Mappings Before Use

```python
mapping = SchemaMapping(...)

# Validate before importing
errors = mapping.validate()
if errors:
    print(f"Mapping errors: {errors}")
    # Fix errors before proceeding
else:
    # Safe to use
    pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)
```

### 4. Handle Missing Columns Gracefully

The pipeline will skip missing columns, but you can add validation:

```python
# Check required columns exist
required_columns = set()
for entity_mapping in mapping.entity_mappings:
    required_columns.update(entity_mapping.source_columns)
for relation_mapping in mapping.relation_mappings:
    required_columns.update(relation_mapping.source_columns)

# Validate CSV has all required columns
csv_columns = set(df.columns)
missing = required_columns - csv_columns
if missing:
    raise ValueError(f"Missing required columns: {missing}")
```

### 5. Use Transformations for Data Cleaning

```python
# Clean phone numbers
PropertyTransformation(
    transformation_type=TransformationType.COMPUTE,
    source_column="phone_raw",
    target_property="phone",
    compute_function="clean_phone"  # Custom function
)

# Normalize text
PropertyTransformation(
    transformation_type=TransformationType.TYPE_CAST,
    source_column="name_raw",
    target_property="name",
    target_type=PropertyType.STRING
)
# Then apply lowercase normalization in post-processing
```

### 6. Document Your Mappings

```python
mapping = SchemaMapping(
    entity_mappings=[...],
    relation_mappings=[...],
    description="Employee and department mapping for HR system import"
)
```

## Common Patterns

### Pattern 1: One Entity Per Row

```python
# Simple 1:1 mapping
EntityMapping(
    source_columns=["id", "name"],
    entity_type="Person",
    property_mapping={"id": "id", "name": "name"},
    id_column="id"
)
```

### Pattern 2: Multiple Entities Per Row

```python
# Create both Employee and Department from same row
EntityMapping(
    source_columns=["emp_id", "emp_name", "dept_id", "dept_name"],
    entity_type="Employee",
    ...
),
EntityMapping(
    source_columns=["emp_id", "emp_name", "dept_id", "dept_name"],
    entity_type="Department",
    ...
)
```

### Pattern 3: Relations from Same Row

```python
# Create relation between entities created in same row
RelationMapping(
    source_columns=["emp_id", "dept_id"],
    relation_type="WORKS_IN",
    source_entity_column="emp_id",
    target_entity_column="dept_id"
)
```

### Pattern 4: Nested JSON

For nested JSON structures, flatten first or use multiple mappings:

```json
{
  "employee": {
    "id": "E001",
    "name": "Alice"
  },
  "department": {
    "id": "D001",
    "name": "Engineering"
  }
}
```

Flatten to:
```python
# Flatten in preprocessing or use JSON path extraction
EntityMapping(
    source_columns=["employee_id", "employee_name", "dept_id", "dept_name"],
    ...
)
```

## Troubleshooting

### Issue: Entities Not Created

**Check:**
1. Are source columns present in data?
2. Is `id_column` specified and present?
3. Are transformations failing silently? (Check warnings in ImportResult)

### Issue: Relations Not Created

**Check:**
1. Are source and target entity columns present?
2. Do the entity IDs exist in the graph?
3. Are entity mappings creating entities before relations?

### Issue: Type Casting Fails

**Check:**
1. Are values in correct format? (e.g., "123" not "abc" for INTEGER)
2. Use `skip_errors=False` to see detailed errors
3. Add data validation before import

### Issue: Computed Values Wrong

**Check:**
1. Are all source columns present?
2. Are values numeric for sum/avg/max/min?
3. Check compute function name spelling

## Next Steps

- See [StructuredDataPipeline Usage Examples](./STRUCTURED_DATA_PIPELINE.md) for how to use mappings
- See [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) for complete CSV example
- See [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for complete JSON example


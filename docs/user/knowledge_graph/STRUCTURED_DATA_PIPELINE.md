# StructuredDataPipeline Usage Guide

This guide explains how to use the `StructuredDataPipeline` to import structured data (CSV, JSON) into knowledge graphs.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Basic Usage](#basic-usage)
3. [CSV Import](#csv-import)
4. [JSON Import](#json-import)
5. [Batch Processing](#batch-processing)
6. [Error Handling](#error-handling)
7. [Advanced Features](#advanced-features)
8. [Performance Tips](#performance-tips)

## Quick Start

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

# 1. Create schema mapping
mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name"},
            id_column="id"
        )
    ]
)

# 2. Initialize graph store
store = InMemoryGraphStore()
await store.initialize()

# 3. Create pipeline
pipeline = StructuredDataPipeline(mapping=mapping, graph_store=store)

# 4. Import CSV
result = await pipeline.import_from_csv("data.csv")
print(f"Added {result.entities_added} entities, {result.relations_added} relations")
```

## Basic Usage

### Step 1: Define Schema Mapping

First, define how your data maps to the knowledge graph:

```python
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping
)

mapping = SchemaMapping(
    entity_mappings=[
        EntityMapping(
            source_columns=["id", "name", "email"],
            entity_type="Person",
            property_mapping={"id": "id", "name": "name", "email": "email"},
            id_column="id"
        )
    ],
    relation_mappings=[
        RelationMapping(
            source_columns=["person_id", "company_id"],
            relation_type="WORKS_FOR",
            source_entity_column="person_id",
            target_entity_column="company_id"
        )
    ]
)
```

### Step 2: Initialize Graph Store

```python
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore

store = InMemoryGraphStore()
await store.initialize()
```

### Step 3: Create Pipeline

```python
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=100,  # Optional: process in batches
    skip_errors=True  # Optional: continue on errors
)
```

### Step 4: Import Data

```python
# Import CSV
result = await pipeline.import_from_csv("data.csv")

# Or import JSON
result = await pipeline.import_from_json("data.json")
```

### Step 5: Check Results

```python
print(f"Entities added: {result.entities_added}")
print(f"Relations added: {result.relations_added}")
print(f"Rows processed: {result.rows_processed}")
print(f"Errors: {len(result.errors)}")
print(f"Warnings: {len(result.warnings)}")

# Check for errors
if result.errors:
    for error in result.errors:
        print(f"Error: {error}")
```

## CSV Import

### Basic CSV Import

```python
result = await pipeline.import_from_csv(
    file_path="employees.csv",
    delimiter=",",  # Optional: default is ","
    encoding="utf-8"  # Optional: default is "utf-8"
)
```

### CSV with Custom Delimiter

```python
# Tab-separated values
result = await pipeline.import_from_csv(
    file_path="data.tsv",
    delimiter="\t"
)

# Semicolon-separated values
result = await pipeline.import_from_csv(
    file_path="data.csv",
    delimiter=";"
)
```

### CSV with Headers

The pipeline automatically detects headers. If your CSV doesn't have headers, specify column names:

```python
# CSV without headers
result = await pipeline.import_from_csv(
    file_path="data_no_headers.csv",
    has_headers=False,
    column_names=["id", "name", "email"]  # Specify column names
)
```

### CSV with Different Encoding

```python
# Handle non-UTF-8 files
result = await pipeline.import_from_csv(
    file_path="data_latin1.csv",
    encoding="latin-1"
)
```

## JSON Import

### JSON Array Import

Import from a JSON array:

```json
[
  {"id": "1", "name": "Alice", "email": "alice@example.com"},
  {"id": "2", "name": "Bob", "email": "bob@example.com"}
]
```

```python
result = await pipeline.import_from_json("data.json")
```

### JSON Lines (NDJSON) Import

Import from newline-delimited JSON:

```jsonl
{"id": "1", "name": "Alice"}
{"id": "2", "name": "Bob"}
```

```python
result = await pipeline.import_from_json(
    file_path="data.jsonl",
    json_format="jsonl"  # Specify format
)
```

### JSON Object with Array Property

Import from a JSON object containing an array:

```json
{
  "employees": [
    {"id": "1", "name": "Alice"},
    {"id": "2", "name": "Bob"}
  ]
}
```

```python
result = await pipeline.import_from_json(
    file_path="data.json",
    json_format="object_array",
    array_key="employees"  # Key containing the array
)
```

### JSON from String

Import directly from a JSON string:

```python
json_string = '[{"id": "1", "name": "Alice"}]'
result = await pipeline.import_from_json(
    file_path=None,
    json_data=json_string
)
```

## Batch Processing

For large files, process in batches to manage memory:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000  # Process 1000 rows at a time
)

result = await pipeline.import_from_csv("large_file.csv")
```

**Benefits:**
- Lower memory usage
- Progress tracking
- Better error recovery

## Error Handling

### Skip Errors (Default)

By default, the pipeline skips rows with errors and continues:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    skip_errors=True  # Default
)

result = await pipeline.import_from_csv("data.csv")

# Check errors
if result.errors:
    print(f"Skipped {len(result.errors)} rows with errors")
    for error in result.errors[:5]:  # Show first 5
        print(f"  - {error}")
```

### Fail on First Error

Stop processing on first error:

```python
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    skip_errors=False  # Stop on first error
)

try:
    result = await pipeline.import_from_csv("data.csv")
except Exception as e:
    print(f"Import failed: {e}")
```

### Validate Before Import

Validate mapping and data before importing:

```python
# Validate mapping
mapping_errors = mapping.validate()
if mapping_errors:
    print(f"Mapping errors: {mapping_errors}")
    return

# Validate CSV columns
import pandas as pd
df = pd.read_csv("data.csv", nrows=1)  # Read first row only
required_columns = set()
for entity_mapping in mapping.entity_mappings:
    required_columns.update(entity_mapping.source_columns)

missing = required_columns - set(df.columns)
if missing:
    print(f"Missing columns: {missing}")
    return

# Safe to import
result = await pipeline.import_from_csv("data.csv")
```

## Advanced Features

### Progress Callback

Track import progress:

```python
async def progress_callback(current: int, total: int):
    percentage = (current / total) * 100
    print(f"Progress: {current}/{total} ({percentage:.1f}%)")

pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    progress_callback=progress_callback
)

result = await pipeline.import_from_csv("large_file.csv")
```

### Custom Metadata

Add metadata to imported entities and relations:

```python
# Metadata is automatically added:
# {
#     "source": "structured_data_import",
#     "imported_at": "2024-01-15T10:30:00"
# }

# You can add custom metadata by modifying the pipeline
# (requires extending StructuredDataPipeline)
```

### Multiple Imports

Import multiple files:

```python
files = ["employees.csv", "departments.csv", "projects.csv"]

for file_path in files:
    result = await pipeline.import_from_csv(file_path)
    print(f"{file_path}: {result.entities_added} entities, {result.relations_added} relations")
```

### Incremental Import

Add new data without duplicates:

```python
# First import
result1 = await pipeline.import_from_csv("initial_data.csv")
print(f"Initial: {result1.entities_added} entities")

# Later, import updates (duplicates are handled by GraphStore)
result2 = await pipeline.import_from_csv("updates.csv")
print(f"Updates: {result2.entities_added} entities")
```

## Performance Tips

### 1. Use Batch Processing

```python
# ✅ Good: Process in batches
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=1000
)

# ❌ Avoid: Process entire file at once (for large files)
pipeline = StructuredDataPipeline(
    mapping=mapping,
    graph_store=store,
    batch_size=None  # Processes entire file
)
```

### 2. Optimize Schema Mapping

```python
# ✅ Good: Only include needed columns
EntityMapping(
    source_columns=["id", "name"],  # Only needed columns
    entity_type="Person",
    ...
)

# ❌ Avoid: Include unnecessary columns
EntityMapping(
    source_columns=["id", "name", "unused1", "unused2"],  # Extra columns
    entity_type="Person",
    ...
)
```

### 3. Use Appropriate Storage Backend

```python
# ✅ For development/testing: InMemoryGraphStore
store = InMemoryGraphStore()

# ✅ For production: SQLiteGraphStore or PostgreSQLGraphStore
from aiecs.infrastructure.graph_storage.sqlite import SQLiteGraphStore
store = SQLiteGraphStore(db_path="kg.db")
await store.initialize()
```

### 4. Pre-process Large Files

For very large files, consider preprocessing:

```python
# Split large CSV into smaller files
import pandas as pd

df = pd.read_csv("large_file.csv")
chunk_size = 10000

for i, chunk in enumerate(pd.read_csv("large_file.csv", chunksize=chunk_size)):
    chunk_file = f"chunk_{i}.csv"
    chunk.to_csv(chunk_file, index=False)
    
    result = await pipeline.import_from_csv(chunk_file)
    print(f"Chunk {i}: {result.entities_added} entities")
```

### 5. Validate Before Import

Validate data structure before importing:

```python
# Quick validation
import pandas as pd

df = pd.read_csv("data.csv", nrows=10)  # Sample first 10 rows
print(f"Columns: {df.columns.tolist()}")
print(f"Sample data:\n{df.head()}")

# Check for required columns
required = ["id", "name"]
missing = set(required) - set(df.columns)
if missing:
    raise ValueError(f"Missing columns: {missing}")

# Now import full file
result = await pipeline.import_from_csv("data.csv")
```

## Complete Example

```python
import asyncio
from aiecs.application.knowledge_graph.builder.schema_mapping import (
    SchemaMapping,
    EntityMapping,
    RelationMapping,
    PropertyTransformation,
    TransformationType
)
from aiecs.application.knowledge_graph.builder.structured_pipeline import StructuredDataPipeline
from aiecs.infrastructure.graph_storage.in_memory import InMemoryGraphStore
from aiecs.domain.knowledge_graph.schema.property_schema import PropertyType

async def main():
    # 1. Define mapping
    mapping = SchemaMapping(
        entity_mappings=[
            EntityMapping(
                source_columns=["emp_id", "name", "email", "salary"],
                entity_type="Employee",
                property_mapping={"emp_id": "id", "name": "name", "email": "email"},
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
            EntityMapping(
                source_columns=["dept_id", "dept_name"],
                entity_type="Department",
                property_mapping={"dept_id": "id", "dept_name": "name"},
                id_column="dept_id"
            )
        ],
        relation_mappings=[
            RelationMapping(
                source_columns=["emp_id", "dept_id"],
                relation_type="WORKS_IN",
                source_entity_column="emp_id",
                target_entity_column="dept_id"
            )
        ]
    )
    
    # 2. Initialize store
    store = InMemoryGraphStore()
    await store.initialize()
    
    # 3. Create pipeline
    pipeline = StructuredDataPipeline(
        mapping=mapping,
        graph_store=store,
        batch_size=100
    )
    
    # 4. Import CSV
    result = await pipeline.import_from_csv("employees.csv")
    
    # 5. Check results
    print(f"✅ Import complete!")
    print(f"   Entities added: {result.entities_added}")
    print(f"   Relations added: {result.relations_added}")
    print(f"   Rows processed: {result.rows_processed}")
    
    if result.errors:
        print(f"⚠️  Errors: {len(result.errors)}")
        for error in result.errors[:5]:
            print(f"   - {error}")
    
    if result.warnings:
        print(f"⚠️  Warnings: {len(result.warnings)}")
        for warning in result.warnings[:5]:
            print(f"   - {warning}")
    
    # 6. Query graph
    employees = await store.get_entities_by_type("Employee")
    print(f"\n📊 Found {len(employees)} employees in graph")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- See [Schema Mapping Guide](./SCHEMA_MAPPING_GUIDE.md) for detailed mapping configuration
- See [CSV-to-Graph Tutorial](./examples/csv_to_graph_tutorial.md) for complete CSV example
- See [JSON-to-Graph Tutorial](./examples/json_to_graph_tutorial.md) for complete JSON example

